"""Fresh-process reconstruction from sensor provenance and the duplex wire."""
from collections import Counter
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

from echoai.nexus0.pattern1r_v4 import evaluate as old
from echoai.nexus0.pattern1r_v4 import contract
from echoai.nexus0.sim3.pkg import load_package, load_protocol
from echoai.nexus0.flight1s.v3.campaign import WORLD_PROTOCOL
from echoai.nexus0.sensor1s import contract as sensor_contract
from .online import Online
from .protocol import unpack, TICK, RECEIPT, INSPECT, FREEZE, family_key
from echoai.echo58.memx.memory import Memory

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT/'lab/echo58/percibex/20261023-r1'


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, value):
    with Path(path).open('x') as f: json.dump(value, f, sort_keys=True, indent=2); f.write('\n')


def check_sources(plan, *, root=None):
    root = ROOT if root is None else Path(root)
    return {p:(root/p).exists() and sha(root/p)==h for p,h in plan['source_inventory'].items()}


def report_schema_ok(report):
    return (type(report) is dict and set(report)=={'transport','wsp','sightings','online'}
            and type(report['transport']) is dict and set(report['transport'])=={
                'frames','schema_errors','invalid','header_digest'})


def replay(records, bridge, arm, factory=Online):
    ground, online, cursor = old.G.Ground(''), factory(arm), 0
    for index, r in enumerate(records, 1):
        online.now = max(online.now, r['capture_ns'])
        before = len(ground.sightings)
        old.feed(ground, r)
        for capture, sig in ground.sightings[before:]: online.sighting(capture, sig, index)
        while cursor < len(bridge) and bridge[cursor]['after_frames'] == index:
            b = bridge[cursor]
            reply = online.control(bytes.fromhex(b['input']))
            if reply.hex() != b['output']: raise ValueError('action differs at '+str(cursor))
            cursor += 1
    if cursor != len(bridge): raise ValueError('control outside received frames')
    ground.close()
    return ground, online


class DelayedLearning(Online):
    def sighting(self, capture_ns, signature, frame=0):
        mode = self.mode
        if mode == 'school': self.mode = 'idle'
        try: super().sighting(capture_ns, signature, frame)
        finally: self.mode = mode


class FrozenWriting(Online):
    def control(self, raw):
        result = super().control(raw)
        if unpack(raw)[0] == FREEZE: self.pattern.observe(0,0)
        return result


def adverse_controls(path):
    """Mutate only in-memory copies of new data. Never repeat a flight."""
    path = Path(path)
    sensors, meta = read(path/'sensors.json'), read(path/'meta.json')
    T = old.load_transcript(ROOT/sensors['transcript'])
    P = old.load_private(ROOT/sensors['private'])
    records, bridge = old.rebuild(T,P), read(path/'bridge.json')
    expected = sensors['consumer']
    def accepts(*, rs=records, bs=bridge, report=expected, factory=Online):
        try:
            g, o = replay(rs,bs,meta['arm'],factory)
            return report_schema_ok(report) and g.sightings == report['sightings'] and g.packets == report['wsp'] and o.report() == report['online']
        except (ValueError, IndexError, KeyError): return False
    cases = []
    cases.append(dict(name='honest_reconstruction', detected=accepts()))
    cases.append(dict(name='learning_delayed_to_eof', detected=not accepts(factory=DelayedLearning)))
    cases.append(dict(name='write_after_freeze', detected=not accepts(factory=FrozenWriting)))
    receipts = [i for i,b in enumerate(bridge) if unpack(bytes.fromhex(b['input']))[0] == RECEIPT]
    if receipts:
        changed = copy.deepcopy(bridge); del changed[receipts[0]]
        cases.append(dict(name='omit_physical_receipt', detected=not accepts(bs=changed)))
        changed = copy.deepcopy(bridge); raw = bytearray.fromhex(changed[receipts[0]]['input']); raw[14] ^= 1
        changed[receipts[0]]['input'] = raw.hex()
        cases.append(dict(name='alter_physical_receipt', detected=not accepts(bs=changed)))
    else:
        cases.append(dict(name='physical_receipt_controls', detected=False, reason='no physical receipt'))
    tick = next((i for i,b in enumerate(bridge) if unpack(bytes.fromhex(b['input']))[0] == TICK), None)
    if tick is not None:
        changed = copy.deepcopy(bridge); raw = bytearray.fromhex(changed[tick]['output']); raw[14] ^= 1
        changed[tick]['output'] = raw.hex()
        cases.append(dict(name='alter_action', detected=not accepts(bs=changed)))
    changed = copy.deepcopy(expected); changed['online']['memory_head'] = 'f'*64
    cases.append(dict(name='alter_declared_state', detected=not accepts(report=changed)))
    changed = dict(expected, debug='undeclared channel')
    cases.append(dict(name='extra_report_channel', detected=not accepts(report=changed)))
    first_capture = expected['sightings'][0][0] if expected['sightings'] else None
    lidar = next((i for i,r in enumerate(records) if r['source']=='lidar' and r['valid'] and
                  r['capture_ns']==first_capture), None)
    if lidar is not None:
        changed = list(records); changed[lidar] = dict(records[lidar], values=(float('inf'),)*360)
        cases.append(dict(name='alter_current_lidar', detected=not accepts(rs=changed)))
    trace = read(path/'episode.json')
    changed = copy.deepcopy(trace)
    inspection = next((e for e in changed['events'] if e.get('ev')=='percibex_inspection' and e['success']), None)
    if inspection is not None:
        for sample in inspection['samples']: sample[6] = inspection['baseline_yaw_urad']
        _, online = replay(records,bridge,meta['arm'])
        package = load_package(Path(meta['package_path']),load_protocol(WORLD_PROTOCOL))
        try:
            p = physical(changed,online,bridge,package,P)
            detected = not p['green']
        except ValueError: detected = True
        cases.append(dict(name='erase_observed_yaw', detected=detected))
    return dict(cases=cases, all_detected=all(c['detected'] for c in cases))


def recognition(records, package, online, trace):
    _, annotations = old.annotated_sightings(records, package)
    if len(annotations) != len(online.events): raise ValueError('annotation alignment')
    model = online.pattern
    school, exam = [], []
    legs = old.legs(trace)
    for a, e in zip(annotations, online.events):
        if [a['capture'], a['signature']] != [e['capture'], e['signature']]: raise ValueError('signature alignment')
        if a['who'] is None: continue
        if e['trained']: school.append((a['who'], e['signature']))
        elif (leg := old.leg_of(a['capture'], legs)) is not None and not leg['school']:
            exam.append((a['who'], e['signature']))
    fam = {}
    for who, sig in school:
        p = model.predict(sig)
        fam.setdefault(who, Counter())[p[0] if p else None] += 1
    home = {who: c.most_common(1)[0][0] for who,c in fam.items()}
    purity = min((c.most_common(1)[0][1]/sum(c.values()) for c in fam.values()), default=0)
    same = confused = unknown = 0
    for who,sig in exam:
        p = model.predict(sig)
        if p is None: unknown += 1
        elif p[0] == home.get(who): same += 1
        else: confused += 1
    sc, ec = Counter(w for w,s in school), Counter(w for w,s in exam)
    expected = {i for i,name in enumerate(sorted(package.roles)) if package.roles[name] == 'barrier'}
    n = len(exam)
    result = dict(school=len(school), exam=n, same=same, confused=confused, unknown=unknown,
                  accuracy=same/n if n else 0, confusion=confused/n if n else 1, purity=purity,
                  home={str(k):v for k,v in home.items()}, school_counts=dict(sc), exam_counts=dict(ec))
    result['green'] = (n > 0 and same/n >= .75 and confused/n <= .15 and purity >= .6
                       and set(home) == expected and None not in home.values()
                       and len(set(home.values())) == len(expected) == 2
                       and all(sc[w] >= 20 and ec[w] >= 20 for w in expected))
    return result


def identity_behavior(records, package, online, bridge, physical_):
    """Judge real-object coverage and a pooled-key shadow on observed history.

    Private identities are scoring data only. The pooled shadow asks for a
    decision on this same prior history; it is not another physical flight.
    """
    _, annotations = old.annotated_sightings(records, package)
    expected = {i for i,name in enumerate(sorted(package.roles)) if package.roles[name] == 'barrier'}
    actual_success, premature, pooled_witnesses, targets = Counter(), [], [], []
    pooled = Memory()
    max_times, previous = [], 0
    for record in records:
        previous = max(previous,record['capture_ns']); max_times.append(previous)
    decision_index = inspection_index = 0
    for b, c in zip(bridge, online.controls):
        op, seq, value = unpack(bytes.fromhex(b['input']))
        if op != TICK: continue
        d = online.decisions[decision_index]; decision_index += 1
        now = max_times[b['after_frames']-1]
        who = None
        for e,a in reversed(list(zip(online.events[:c['events']], annotations[:c['events']]))):
            if e['capture'] < now-1_000_000_000: break
            if e['family'] == d['family'] and d['family'] is not None and a['who'] in expected:
                who = a['who']; break
        targets.append(dict(seq=seq, family=d['family'], actual_object=who,
                            actual_prior_successes=actual_success[who] if who is not None else None))
        pooled_recall = pooled.recall(1,0,'TOGGLE',0)
        if who is not None and actual_success[who] < 3:
            witness = dict(seq=seq, actual_object=who, successes=actual_success[who], family=d['family'])
            if d['action'] == 0 and d['family'] is not None: premature.append(witness)
            if pooled_recall == 'PASS': pooled_witnesses.append(witness)
        if d['action']:
            row = physical_['rows'][inspection_index]; inspection_index += 1
            if d['mode'] == 'school':
                if row['success'] and who is not None: actual_success[who] += 1
                pooled.observe(1,0,'TOGGLE',0,'PASS' if row['success'] else 'NOOP')
    return dict(actual_school_successes=dict(actual_success), premature_exemptions=premature,
                pooled_key_premature_exemptions=pooled_witnesses, targets=targets,
                collapsed_control_kind='conditional shadow on actual observed history; no counterfactual flight',
                coverage_green=all(actual_success[w] >= 3 for w in expected),
                specificity_green=not premature and bool(pooled_witnesses))


def physical(trace, online, bridge, package, private):
    events = trace.get('events', [])
    actions = [e for e in events if e.get('ev') == 'percibex_action']
    inspections = [e for e in events if e.get('ev') == 'percibex_inspection']
    if len(actions) != len(online.decisions): raise ValueError('missing physical action')
    cursor, success, family_success, samples = 0, 0, Counter(), []
    phases = {'school': dict(decisions=0, inspect=0, skip=0, unknown=0, successes=0),
              'exam': dict(decisions=0, inspect=0, skip=0, unknown=0, successes=0)}
    receipt_controls = [b for b in bridge if unpack(bytes.fromhex(b['input']))[0] == RECEIPT]
    rows = []
    private_poses = [e['body'] for s in ('lidar','depth') for e in private['raw'][s].values() if e.get('body')]
    for action, decision in zip(actions, online.decisions):
        if action['seq'] != decision['seq'] or action['action'] != decision['action']:
            raise ValueError('wire/physical action mismatch')
        if (action['view'] < 32) != (decision['mode'] == 'school'): raise ValueError('physical phase mismatch')
        p = phases[decision['mode']]; p['decisions'] += 1
        if decision['family'] is None: p['unknown'] += 1
        if not decision['action']:
            p['skip'] += 1; continue
        p['inspect'] += 1
        if cursor >= len(inspections) or cursor >= len(receipt_controls): raise ValueError('missing inspection/receipt')
        e, b = inspections[cursor], receipt_controls[cursor]
        if e['view'] != action['view']: raise ValueError('inspection wrong view')
        samples += e['samples']
        outward = [s for s in e['samples'] if e['out_begin_ns'] <= s[0] <= e['turn_ns']]
        returned = [s for s in e['samples'] if s[0] > e['turn_ns']]
        # Microradians: these are measurements from Gazebo's body stream.
        baseline = (e['baseline_yaw_urad'] or 0)/1000000
        def delta(angle):
            return abs(math.atan2(math.sin(angle-baseline),math.cos(angle-baseline)))
        yaw_max = max((round(delta(s[6]/1000000)*1000000) for s in outward), default=0)
        yaw_end = round(delta(returned[-1][6]/1000000)*1000000) if returned else 10**9
        command_delta = (math.atan2(math.sin((e.get('target_ned_urad',0)-(e['baseline_ned_urad'] or 0))/1000000),
                                   math.cos((e.get('target_ned_urad',0)-(e['baseline_ned_urad'] or 0))/1000000)))
        ok = bool(e['ack_baseline'] and e['baseline_stable'] and e['ack_out'] and e['ack_back'] and e['outward'] and e['returned']
                  and 280000 <= yaw_max <= 520000 and yaw_end <= 120000 and abs(command_delta-.4)<=.000002)
        raw_out = max((delta(p[6]) for p in private_poses if e['out_begin_ns'] <= p[0] <= e['turn_ns']), default=0)
        raw_return = min((delta(p[6]) for p in private_poses if e['turn_ns'] < p[0] <= e['end_ns']), default=10)
        if e['success'] != ok or unpack(bytes.fromhex(b['input']))[2] != int(ok):
            raise ValueError('receipt differs from physical outcome')
        success += ok; p['successes'] += ok
        if decision['mode'] == 'school' and ok: family_success[decision['family']] += 1
        rows.append(dict(view=e['view'], family=decision['family'], mode=decision['mode'], success=ok,
                         yaw_max_urad=yaw_max, yaw_end_urad=yaw_end,
                         private_out_yaw_urad=round(raw_out*1000000), private_return_yaw_urad=round(raw_return*1000000),
                         private_pose_witness=.28 <= raw_out <= .52 and raw_return <= .12,
                         begin_ns=e['begin_ns'], end_ns=e['end_ns']))
        cursor += 1
    if cursor != len(inspections) or cursor != len(receipt_controls): raise ValueError('extra inspection/receipt')
    boxes = contract.barriers(package)
    clearance = min((contract.point_box_distance([s[k]/1000 for k in (1,2,3)], b)
                     for s in samples for b in boxes), default=0)
    return dict(phases=phases, inspections=len(inspections), successes=success,
                school_family_success=dict(family_success), rows=rows,
                inspection_clearance_mm=round(clearance, 3),
                green=len(actions) == 48 and success == len(inspections) and clearance >= 400
                      and all(r['private_pose_witness'] for r in rows))


def inspect(path):
    path = Path(path)
    trace, sensors, meta = read(path/'episode.json'), read(path/'sensors.json'), read(path/'meta.json')
    package = load_package(Path(meta['package_path']), load_protocol(WORLD_PROTOCOL))
    T = old.load_transcript(ROOT/sensors['transcript'])
    P = old.load_private(ROOT/sensors['private'])
    records = old.rebuild(T, P)
    bridge = read(path/'bridge.json')
    ground, online = replay(records, bridge, meta['arm'])
    report = sensors['consumer']
    checks = dict(execution=trace['ok'] and sensors['consumer_returncode'] == 0,
                  report_schema=report_schema_ok(report),
                  raw_reconstruction=len(records) == len(T) == report['transport']['frames'] == sensors['forwarder']['frames'],
                  control_reconstruction=online.report() == report['online'],
                  sensor_reconstruction=ground.sightings == report['sightings'] and ground.packets == report['wsp'],
                  no_private_canary=not sensors['forwarder']['canary_hits'],
                  no_stream_error=sensors['forwarder']['error'] is None and report['transport']['schema_errors'] == 0,
                  frozen=online.frozen_pattern == online.pattern.snapshot_hash() and online.frozen_memory == online.memory.head,
                  completed=online.pending is None and online.mode == 'exam',
                  single_report=sensors['cable']['stderr_lines'] == 1 and sensors['cable']['back_bytes'] == 0,
                  sensor_bytes=sha(ROOT/sensors['transcript']) == sensors['transcript_sha256'],
                  private_bytes=sha(ROOT/sensors['private']) == sensors['private_sha256'],
                  bridge_bytes=sha(path/'bridge.json') == sensors['bridge_sha256'],
                  no_llm_no_destruction=online.memory.destroyed == 0 and report['online']['cortex_calls'] == 0)
    digest = hashlib.sha256()
    for t in T:
        hb = t['h'].encode(); digest.update(len(hb).to_bytes(4,'big')+hb)
    checks['headers'] = digest.hexdigest() == report['transport']['header_digest'] == sensors['forwarder']['header_digest']
    checks['raw_payload_provenance'] = len(records) == len(T) and all(
        r['raw'] is not None and r['valid'] and r['raw']['sha'] == t['wire'] == json.loads(t['h'])['payload_sha256']
        for r,t in zip(records,T))
    checks['public_sensor_schema'] = all(
        all(h[k] == v for k,v in sensor_contract.EXPECTED[h['source']].items()) and
        h['noise_ref'] == sensor_contract.SOURCES[h['source']]['noise_ref']
        for h in (json.loads(t['h']) for t in T))
    checks['canonical_report'] = hashlib.sha256((json.dumps(report, sort_keys=True)+'\n').encode()).hexdigest() == sensors['cable']['stderr_sha256']
    checks['live_before_eof'] = bool(bridge) and all(0 < b['after_frames'] < len(T) and
        b['sent_monotonic_ns'] <= b['received_monotonic_ns'] for b in bridge)
    checks['live_updates'] = any(d['observations'] >= 32 and d['family'] is not None for d in online.decisions)
    marks = trace['stage_marks'].get('survey', [])
    checks['survey'] = len(marks) == 48 and sum(bool(m['settled_ns']) for m in marks) >= .9*48
    expected = [p+[1500] for p in contract.arc_viewpoints(package)]
    checks['prescribed_route'] = [m['target_mm'] for m in marks] == expected
    recognition_ = recognition(records, package, online, trace)
    physical_ = physical(trace, online, bridge, package, P)
    behavior_ = identity_behavior(records, package, online, bridge, physical_)
    # All memory writes must have come from verified, currently pending receipts.
    checks['memory_records_from_physical_receipts'] = len(online.memory.records) == physical_['phases']['school']['inspect']
    checks['bounded_body'] = contract.route_check(package)['ok'] and physical_['inspection_clearance_mm'] >= 400
    return dict(label=meta['label'], arm=meta['arm'], world=meta['world'], evidence_valid=all(checks.values()),
                checks=checks, recognition=recognition_, physical=physical_,
                identity_behavior=behavior_,
                pattern_hash=online.pattern.snapshot_hash(), memory_head=online.memory.head,
                memory_records=len(online.memory.records), frames=len(T), controls=len(bridge),
                wall_s=trace['metrics']['wall_s'], source_sha256=trace['source_sha256'])


def main():
    stage = sys.argv[1] if len(sys.argv)>1 else 'validation'
    plan = read(LAB/(stage+'-plan.json'))
    results, errors = [], []
    for item in plan['flights']:
        try: results.append(inspect(LAB/stage/item['label']))
        except Exception as exc: errors.append(dict(label=item['label'], error=type(exc).__name__+': '+str(exc)))
    source_checks = check_sources(plan)
    summary_path = LAB/(stage+'-summary.json')
    summary = read(summary_path) if summary_path.exists() else {}
    artifact_checks = {p:Path(p).exists() and sha(p)==h for p,h in summary.get('artifact_inventory',{}).items()}
    result = dict(kind='fresh-process-audit', stage=stage, results=results, errors=errors,
                  source_checks=source_checks, artifact_checks=artifact_checks,
                  evidence_valid=not errors and len(results)==len(plan['flights']) and all(r['evidence_valid'] for r in results)
                    and all(source_checks.values()) and bool(artifact_checks) and all(artifact_checks.values()))
    result['recognition_green'] = bool(results) and all(r['recognition']['green'] for r in results)
    result['physical_green'] = bool(results) and all(r['physical']['green'] for r in results)
    memx = [r for r in results if r['arm']=='MEMX']
    result['identity_behavior_green'] = bool(memx) and all(
        r['identity_behavior']['coverage_green'] and r['identity_behavior']['specificity_green'] for r in memx)
    comparison = []
    for r in memx:
        others = {a['arm']:a for a in results if a['world']==r['world']}
        if 'EMPTY' not in others or 'VISITS' not in others: continue
        counts = {k:v['physical']['phases']['exam']['inspect'] for k,v in others.items()}
        comparison.append(dict(world=r['world'], exam_inspections=counts,
            fewer_than_empty=counts['MEMX'] < counts['EMPTY'], tied_with_visits=counts['MEMX']==counts['VISITS']))
    result['comparison'] = comparison
    result['behavioral_effect_green'] = len(comparison)==len(memx)>0 and all(c['fewer_than_empty'] for c in comparison)
    controls = []
    for f in plan['flights']:
        if f['arm']=='MEMX':
            try: controls.append(dict(label=f['label'], **adverse_controls(LAB/stage/f['label'])))
            except Exception as exc: controls.append(dict(label=f['label'], all_detected=False, error=str(exc)))
    result['adverse_controls'] = controls
    result['adverse_controls_green'] = bool(controls) and all(c['all_detected'] for c in controls)
    result['percibex_narrow_green'] = all(result[k] for k in ('evidence_valid','recognition_green','physical_green',
        'identity_behavior_green','behavioral_effect_green','adverse_controls_green'))
    output = LAB/(stage+'-audit.json')
    save(output, result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','source_checks','artifact_checks','adverse_controls')}, sort_keys=True), flush=True)
    return 0 if result['evidence_valid'] else 1


if __name__ == '__main__': raise SystemExit(main())
