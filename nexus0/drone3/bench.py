"""DRONE-3 bench: A develops and calibrates, the lock freezes, B validates once,
only a green B opens C once, and the certificate is rebuilt from raw evidence
in a new process. Flights are never overwritten; a red B seals C.

HIL and the physical cage need hardware this laboratory does not have: their
flags stay false and `drone3_green` stays false whatever SITL shows.
"""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from echoai.nexus0.power1.core import Guard, Model, RESERVE
from echoai.nexus0.transfer3.bench_c1 import dependency_paths
from . import controls, probes
from .calibration import canonical_sha, provenance
from .energy import battery_sample, fit
from .evaluate import audit, expected_world, file_sha, lines, school
from .gateway import CellGateway
from .protocol import (BATTERY, CONDITIONS, ROOMS_PER_STAGE, STAGE_BASE, flights, geometry, handover,
                       rooms)
from .session import ASSETS, RUNNER_MODULES, RUNNER_PARENT, digest, run
from .supervisor import MissionSupervisor

HERE = Path(__file__).resolve().parent
ECHOAI = HERE.parents[1]
LAB = ECHOAI/'lab/drone3'
LOCK = LAB/'lock.json'
POWER = LAB/'power-model.json'
REPORT = ECHOAI/'lab/echo3_drone3_report.json'
DESIGN = ECHOAI/'docs/DRONE3-DESIGN.md'
TESTS = ECHOAI/'tests/test_drone3.py'
COMPOSE_LOCK = ECHOAI/'lab/compose1-v4/lock.json'
COMPOSE_SCHOOL = ECHOAI/'lab/compose1-v4/physical-school.json'
COMPOSE_CERTIFICATE = 'b5974a9e18bf56fd3c94aea74f54eeecf93843498c1eb5ca25c5c9e6733d7073'
PROVISIONAL = {'unit': 'sim_u', 'costs': {
    '0': {'n': 8, 'nominal': 12, 'maximum': 15, 'upper': 19},
    '1': {'n': 8, 'nominal': 12, 'maximum': 15, 'upper': 19},
    'land': {'n': 8, 'nominal': 24, 'maximum': 27, 'upper': 34}}}
FOLDERS = dict(development='development', development2='development2',
               validation='validation', confirmation='confirmation')
Z95 = 1.959963984540054


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'x') as f:
        json.dump(value, f, sort_keys=True, indent=1)


def load(path):
    return json.loads(Path(path).read_text())


def wilson(k, n):
    if not n:
        return None
    p = k/n
    centre = (p+Z95*Z95/(2*n))/(1+Z95*Z95/n)
    half = Z95*math.sqrt(p*(1-p)/n+Z95*Z95/(4*n*n))/(1+Z95*Z95/n)
    return [round(max(0, centre-half), 4), round(min(1, centre+half), 4)]


def quantiles(values):
    if not values:
        return None
    v = sorted(values)
    pick = lambda q: v[min(len(v)-1, math.ceil(q*len(v))-1)]
    return dict(n=len(v), p50=pick(.50), p95=pick(.95), p99=pick(.99), max=v[-1])


def tree(root):
    root = Path(root)
    return {str(p.relative_to(root)): file_sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


# -- code inventory --------------------------------------------------------------
def inventory():
    entries = sorted(HERE.rglob('*.py'))+[TESTS]+list(ASSETS.values())
    paths = dependency_paths([p for p in entries if p.suffix == '.py'])+[DESIGN]
    rel = lambda p: str(p.relative_to(ECHOAI)) if p.is_relative_to(ECHOAI) else '../'+p.name
    return {rel(Path(p)): file_sha(p) for p in sorted(set(map(Path, paths)))}


def case_code():
    """sha256 each flight folder must carry for its container code."""
    inv = inventory()
    out = {name: inv[str(src.relative_to(ECHOAI))] for name, src in ASSETS.items()}
    out.update({'echoai/nexus0/'+m: inv['nexus0/'+m] for m in RUNNER_MODULES})
    out.update({m: inv['../'+m] for m in RUNNER_PARENT})
    return out


# -- flying ---------------------------------------------------------------------
def fly(folder, plan, lock_sha256=None):
    for label, spec in plan:
        path = LAB/folder/label
        if path.exists():
            flown = load(path/'configuration.json').get('lock_sha256') if (path/'configuration.json').exists() else None
            if flown != lock_sha256:
                raise SystemExit(f'{folder}/{label} exists and was not flown under this lock')
            print('kept', folder, label, flush=True)   # never overwrite; resume after it
            continue
        print('fly', folder, label, flush=True)
        run(path, spec, school(), lock_sha256=lock_sha256)


def a1_plan():
    return flights('development', PROVISIONAL, provenance()['offset'])


def calibrated():
    return load(POWER)['model']


def a2_plan():
    return flights('development', calibrated(), provenance()['offset'])


def flown_geometries():
    """Every room geometry any DRONE-3 flight has used before the lock (pilots included)."""
    seen = set()
    for folder in sorted(p for p in LAB.iterdir() if p.is_dir() and p.name not in ('validation', 'confirmation')):
        for cfg in sorted(folder.glob('*/configuration.json')):
            seen.add(geometry(load(cfg)['spec']['seed']))
    return seen | {geometry(s) for s in rooms('development')}


def excluded_for(stage, lock=None):
    if lock is not None:
        return {tuple(g) for g in lock['excluded_geometries'][stage]}
    a = flown_geometries()
    if stage == 'validation':
        return a
    return a | {geometry(s) for s in rooms('validation', excluded=a)}


def stage_plan(stage, lock=None):
    model = lock['power_model'] if lock else calibrated()
    offset = lock['transfer3_c1']['offset'] if lock else provenance()['offset']
    return flights(stage, model, offset, excluded=excluded_for(stage, lock))


# -- POWER calibration from A receipts ---------------------------------------------
def receipts(case):
    rows = lines(Path(case)/'out/trace.jsonl')
    journal = lines(Path(case)/'journal.jsonl')
    status = {r['epoch']: r['response']['status'] for r in journal if r.get('side') == 'agent' and 'epoch' in r}
    obs = {r['epoch']: r for r in rows if r['kind'] == 'observation'}
    allowed = {r['epoch']: r for r in rows if r['kind'] == 'proposal' and r['decision']['allowed']}
    arrived = {r['epoch'] for r in rows if r['kind'] == 'arrival'}
    out = []
    for e, proposal in sorted(allowed.items()):
        if e not in arrived or e+1 not in obs:
            continue
        before = battery_sample(obs[e]['raw']['battery'])
        after = battery_sample(obs[e+1]['raw']['battery'])
        elapsed = (obs[e+1]['now_ns']-obs[e]['now_ns'])//1_000_000
        if before and after and before['remaining'] > after['remaining']:
            out.append(dict(phase='1' if status.get(e) == 'returning' else '0', before=before['remaining'],
                            after=after['remaining'], elapsed_ms=elapsed, source=f'{Path(case).name}#{e}'))
    land = [r for r in rows if r['kind'] == 'land_request']
    disarm = [r for r in rows if r['kind'] == 'disarmed']
    if land and disarm and land[0].get('battery'):
        armed = [r for r in rows if r['kind'] == 'sample' and r.get('battery')
                 and land[0]['now_ns'] <= r['now_ns'] < disarm[0]['now_ns']]
        before = battery_sample(land[0]['battery'])
        # The pack refills on disarm before the heartbeat shows it: touchdown is the minimum.
        lowest = min(armed, key=lambda r: battery_sample(r['battery'])['remaining']) if armed else None
        after = battery_sample(lowest['battery']) if lowest else None
        if before and after and before['remaining'] > after['remaining']:
            out.append(dict(phase='land', before=before['remaining'], after=after['remaining'],
                            elapsed_ms=(lowest['now_ns']-land[0]['now_ns'])//1_000_000,
                            source=f'{Path(case).name}#land'))
    return out


def calibrate():
    cases = [LAB/FOLDERS['development']/label for label, _ in a1_plan()]
    rows = [r for case in cases for r in receipts(case)]
    model = fit([{k: v for k, v in r.items() if k != 'source'} for r in rows])
    value = dict(model=model, receipts=rows, sources={c.name: tree(c) for c in cases},
                 unit='sim_u: per-mille of PX4 SITL simulated pack between 20 % and 100 %',
                 rule='POWER-1 Model.fit: nominal = ceiling mean, upper = ceiling(1.25*max), n>=8 per phase')
    save(POWER, value)
    print(json.dumps(model, sort_keys=True))
    return value


# -- evaluation of a stage -------------------------------------------------------------
def summary(folder, plan, *, code=None, lock=None):
    rows = []
    for label, spec in plan:
        path = LAB/folder/label
        if not path.exists():
            rows.append(dict(case=label, condition=spec['condition'], missing=True, passed=False))
            continue
        a = audit(path, code=code, lock=lock)
        cfg = load(path/'configuration.json')
        identity = cfg['spec'] == spec and (lock is None or cfg.get('lock_sha256') == lock['sha256'])
        rows.append(dict(case=label, condition=spec['condition'], passed=a['passed'] and identity,
                         evidence_valid=a['evidence_valid'] and identity,
                         findings=a['findings']+([] if identity else ['plan_identity']),
                         failures=a['failures'], metrics=a['metrics'], files=tree(path)))
    n = len(rows)
    k = sum(r['passed'] for r in rows)
    per = {cnd: dict(n=sum(r['condition'] == cnd for r in rows),
                     passed=sum(r['condition'] == cnd and r['passed'] for r in rows)) for cnd in CONDITIONS}
    for v in per.values():
        v['wilson95'] = wilson(v['passed'], v['n'])
    m = [r.get('metrics', {}) for r in rows]
    latencies = [x for r in m for x in r.get('agent_latency_ms', [])]
    aggregate = dict(
        flights=n, passed=k, wilson95=wilson(k, n), per_condition=per,
        missions_reached=sum(bool(r.get('reached')) for r in m),
        feasible_missions=sum(r['condition'] in ('access', 'contradiction') for r in rows),
        correct_aborts=sum(r['condition'] == 'low_reserve' and r['passed'] for r in rows),
        incorrect_aborts=sum(r['condition'] in ('access', 'contradiction') and not r.get('metrics', {}).get('reached')
                             for r in rows),
        faults_contained=sum(r['condition'] == 'fault' and r['passed'] for r in rows),
        collisions=sum(r.get('clearance', {}).get('unsafe_samples', 0) for r in m),
        min_clearance_mm=min((r['clearance']['min_clearance_mm'] for r in m if r.get('clearance')), default=None),
        final_reserve_min=min((r['final_remaining'] for r in m
                               if r.get('final_remaining') is not None and not r.get('vetoed')), default=None),
        failsafe_samples_supervised_nonfault=sum(r.get('failsafe_samples_supervised', 0) for r, row in zip(m, rows)
                                                  if row['condition'] != 'fault'),
        arrival_true_error_mm=quantiles([x for r in m for x in r.get('arrival_true_error_mm', [])]),
        landing_true_error_mm=quantiles([r['home_error_mm'] for r, row in zip(m, rows)
                                         if r.get('home_error_mm') is not None and row['condition'] != 'fault']),
        agent_latency_ms=quantiles(latencies),
        chain_ms={key: quantiles([x for r in m for x in r.get('timing', {}).get(key, [])])
                  for key in ('observation_to_send_ms', 'send_to_ack_ms', 'ack_to_arrival_ms')},
        veto_latency_ms=[r.get('veto_latency_ms') for r, row in zip(m, rows) if row['condition'] == 'fault'],
        disarm_after_veto_ms=[r.get('disarm_after_veto_ms') for r, row in zip(m, rows) if row['condition'] == 'fault'],
        agent_peak_rss_kb=max((r.get('agent_peak_rss_kb', 0) for r in m), default=None),
        spatial_cells_max=max((r.get('spatial_cells') or 0 for r in m), default=None),
        movements=sum(r.get('movements') or 0 for r in m), inspections=sum(r.get('inspections') or 0 for r in m),
        hard={key: sum(r.get('hard', {}).get(key, 0) for r in m) for key in
              ('false_facts', 'imagined_cam_writes', 'oracle_leaks', 'gate_bypasses',
               'px4_failsafe_bypasses', 'unsafe_setpoints_accepted')})
    return dict(green=k == n and n > 0, rows=rows, aggregate=aggregate)


def probe_counts(value):
    """From the audits, which recompute every probe from its recorded inputs."""
    counts = [r.get('metrics', {}).get('probes') or dict(total=0, blocked=0) for r in value['rows']]
    return dict(blocked=sum(p['blocked'] for p in counts), total=sum(p['total'] for p in counts),
                flights_all_blocked=sum(p['total'] == p['blocked'] == len(probes.NAMES) for p in counts),
                flights=len(counts))


# -- controls, mutants and manipulations -----------------------------------------------
def control_report(folder, plan):
    out = []
    for label, spec in plan:
        path = LAB/folder/label
        row = dict(case=label, condition=spec['condition'])
        if spec['condition'] != 'fault':
            row['horizon'] = controls.horizon(path)
            row['fixed_battery'] = controls.fixed_battery(path)
            row['evidence_ablation'] = controls.evidence_ablation(path)
        row['ack_as_arrival'] = controls.ack_as_arrival(path)
        row['calibration'] = controls.calibration(path)
        if spec['condition'] == 'fault':
            row['safe_ablation'] = controls.safe_ablation(path)
        out.append(row)
    twins = {spec['seed']: controls.twin(spec['seed'], 'access') for label, spec in plan
             if spec['condition'] == 'access'}
    return dict(flights=out, twins={str(k): v for k, v in twins.items()})


MUTANTS = {
    'gateway_no_ttl': dict(gateway=lambda s, c: CellGateway(s, c, mutant='no_ttl')),
    'gateway_no_geofence': dict(gateway=lambda s, c: CellGateway(s, c, mutant='no_geofence')),
    'gateway_ack_is_arrival': dict(gateway=lambda s, c: CellGateway(s, c, mutant='ack_is_arrival')),
    'gateway_no_sequence': dict(gateway=lambda s, c: CellGateway(s, c, mutant='no_sequence')),
    'gate_admit_unknown': dict(epistemic=lambda *a, **k: controls.gates.epistemic(*a, mutant='admit_unknown')),
    'gate_no_reserve': dict(energy=lambda *a, **k: controls.gates.energy(*a, mutant='no_reserve')),
    'supervisor_no_epistemic': dict(supervisor=lambda *a: MissionSupervisor(*a, mutant='no_epistemic')),
    'supervisor_no_energy': dict(supervisor=lambda *a: MissionSupervisor(*a, mutant='no_energy')),
}


def mutant_report(folder, plan):
    cases = [LAB/folder/label for label, _ in plan]
    out = {}
    for name, override in MUTANTS.items():
        detected = 0
        for case in cases:
            cfg = load(case/'configuration.json')['spec']
            for r in [x for x in lines(case/'out/trace.jsonl') if x['kind'] == 'probes']:
                again = probes.run(r['frame'], r['probe_now'], r['system'], model=cfg['power_model'],
                                   offset=cfg['offset'], **override)
                detected += any(x['allowed'] for x in again)
        out[name] = dict(flights=len(cases), detected_in=detected)
    faults = [LAB/folder/label for label, spec in plan if spec['condition'] == 'fault']
    for mutant in ('no_liveness', 'no_latch'):
        hits = 0
        for case in faults:
            s = controls.safe_ablation(case)[mutant]
            hits += (s['vetoes'] is False) or s['resumes'] > 0
        out['supervisor_'+mutant] = dict(flights=len(faults), detected_in=hits)
    # A different agent (reactive Q), declared consistently, is caught only by the
    # exact replay of the recorded decisions: replay with that agent must diverge.
    feasible = [LAB/folder/label for label, spec in plan if spec['condition'] in ('access', 'contradiction')]
    hits = 0
    for case in feasible:
        cfg = load(case/'configuration.json')
        space = expected_world(cfg['spec'])[0]
        init = dict(model=school(), goal=list(space.goal), offset=cfg['spec']['offset'],
                    power_model=cfg['spec']['power_model'], mode='q', power_policy='cost')
        agent = controls.MissionAgent(**init)
        journal = {r['epoch']: r['response'] for r in lines(case/'journal.jsonl')
                   if r.get('side') == 'agent' and 'epoch' in r}
        for obs in [r for r in lines(case/'out/trace.jsonl') if r['kind'] == 'observation']:
            if obs['epoch'] in journal and agent.decide(obs['raw']) != journal[obs['epoch']]:
                hits += 1
                break
    out['agent_reactive_q'] = dict(flights=len(feasible), detected_in=hits)
    return out


def manipulate(path, how):
    trace = path/'out/trace.jsonl'
    rows = trace.read_text().splitlines()
    if how == 'wsp':
        i = next(i for i, r in enumerate(rows) if '"kind": "intention"' in r)
        row = json.loads(rows[i])
        row['wsp'] = row['wsp'][:-2]+('01' if row['wsp'][-2:] != '01' else '02')
        rows[i] = json.dumps(row, sort_keys=True)
    elif how == 'ack':
        i = next(i for i, r in enumerate(rows) if '"kind": "ack"' in r)
        row = json.loads(rows[i])
        row['ack']['result'] = 4
        rows[i] = json.dumps(row, sort_keys=True)
    elif how == 'omit_observation':
        i = [i for i, r in enumerate(rows) if '"kind": "observation"' in r][1]
        del rows[i]
    elif how == 'duplicate_proposal':
        i = next(i for i, r in enumerate(rows) if '"kind": "proposal"' in r)
        rows.insert(i, rows[i])
    elif how == 'battery':
        # Consistent forgery: the host journal's digest is recomputed too.
        i = next(i for i, r in enumerate(rows) if '"kind": "observation"' in r)
        row = json.loads(rows[i])
        row['raw']['battery']['voltage_mv'] += 200
        rows[i] = json.dumps(row, sort_keys=True)
        journal = path/'journal.jsonl'
        notes = [json.loads(r) for r in journal.read_text().splitlines()]
        for note in notes:
            if note.get('side') == 'backend' and note.get('kind') == 'observation' and note['epoch'] == row['epoch']:
                note['raw_sha256'] = digest(row['raw'])
        journal.write_text('\n'.join(json.dumps(n, sort_keys=True) for n in notes)+'\n')
    elif how == 'proposal_substituted':
        # The runner sends its own move, with a matching target and prediction.
        i = next(i for i, r in enumerate(rows) if '"kind": "proposal"' in r)
        row = json.loads(rows[i])
        w = bytearray.fromhex(row['request']['wsp'])
        w[14] ^= 0x01
        row['request']['wsp'] = w.hex()
        rows[i] = json.dumps(row, sort_keys=True)
    elif how == 'ulog':
        ulog = next((path/'out/wd').rglob('*.ulg'))
        data = bytearray(ulog.read_bytes())
        data[len(data)//2] ^= 0xFF
        ulog.write_bytes(bytes(data))
        return
    elif how == 'private_pose':
        p = path/'out/private.jsonl'
        body = [json.loads(r) for r in p.read_text().splitlines()]
        for r in body[len(body)//2:]:
            if 'body' in r:
                r['body'][1] += 2.5
        p.write_text('\n'.join(json.dumps(r) for r in body)+'\n')
        return
    trace.write_text('\n'.join(rows)+'\n')


def manipulation_report(folder, plan, recorded, *, code, lock):
    """Each manipulated copy must be rejected: by the audit or by the frozen file hashes."""
    label = next(label for label, spec in plan if spec['condition'] == 'access')
    source = LAB/folder/label
    out = {}
    for how in ('wsp', 'ack', 'omit_observation', 'duplicate_proposal', 'battery', 'proposal_substituted',
                'ulog', 'private_pose'):
        with tempfile.TemporaryDirectory(prefix='drone3-manipulation-') as tmp:
            copy = Path(tmp)/label
            # PX4 leaves dangling symlinks in out/wd; copy links as links.
            shutil.copytree(source, copy, symlinks=True)
            manipulate(copy, how)
            a = audit(copy, code=code, lock=lock)
            out[how] = dict(audit_rejected=not a['passed'], findings=a['findings'][:6], failures=a['failures'][:6],
                            stage_hash_rejected=canonical_sha(tree(copy)) != recorded[label],
                            rejected=not a['passed'])
    return out


# -- stages ------------------------------------------------------------------------------
def tests():
    result = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_drone3'],
                            cwd=ECHOAI.parent, capture_output=True, text=True)
    return dict(ok=result.returncode == 0, output=(result.stdout+result.stderr)[-2000:])


def locked_data():
    """Everything the flights and the audit consume besides code, by hash."""
    compose = load(COMPOSE_LOCK)
    if file_sha(COMPOSE_SCHOOL) != compose['physical_school_sha256']:
        raise SystemExit('COMPOSE physical school does not match its lock')
    return dict(power_model=calibrated(), power_model_sha256=file_sha(POWER),
                compose=dict(lock_sha256=file_sha(COMPOSE_LOCK), physical_school_sha256=file_sha(COMPOSE_SCHOOL),
                             certificate=COMPOSE_CERTIFICATE, model_sha256=canonical_sha(school())),
                transfer3_c1=provenance(), battery=BATTERY, conditions=list(CONDITIONS),
                runtime=load(ECHOAI/'lab/flight1s-v6/lock.json')['runtime']['container'])


def freeze(a2_folder):
    if LOCK.exists():
        raise SystemExit('lock exists: B/C evidence would lose its reference')
    a2 = summary(a2_folder, a2_plan())
    if not a2['green']:
        raise SystemExit('A2 is not green: '+json.dumps(
            [(r['case'], r.get('findings'), r.get('failures')) for r in a2['rows'] if not r['passed']]))
    t = tests()
    if not t['ok']:
        raise SystemExit('tests red\n'+t['output'])
    flown = sorted(flown_geometries())
    excluded_b = set(flown)
    b_rooms = rooms('validation', excluded=excluded_b)
    excluded_c = excluded_b | {geometry(s) for s in b_rooms}
    c_rooms = rooms('confirmation', excluded=excluded_c)
    lock = dict(
        version='drone3-sitl-1', created='2026-09-19', inventory=inventory(), **locked_data(),
        flown_geometries=[list(g) for g in flown],
        excluded_geometries=dict(validation=sorted(list(g) for g in excluded_b),
                                 confirmation=sorted(list(g) for g in excluded_c)),
        rooms=dict(development=rooms('development'), validation=b_rooms, confirmation=c_rooms),
        geometries=dict(validation=[list(geometry(s)) for s in b_rooms],
                        confirmation=[list(geometry(s)) for s in c_rooms]),
        handovers={str(s): handover(s, calibrated()) for s in b_rooms+c_rooms},
        development=dict(a1=[l for l, _ in a1_plan()], a2_folder=a2_folder,
                         a2_summary_sha256=canonical_sha(a2),
                         a2_files={r['case']: canonical_sha(r['files']) for r in a2['rows']}),
        tests=dict(ok=True), preflight=load(LAB/'preflight/summary.json'),
        criteria='docs/DRONE3-DESIGN.md#criterios')
    lock['sha256'] = canonical_sha(lock)
    save(LOCK, lock)
    print(json.dumps(dict(lock_sha256=lock['sha256'], validation=b_rooms, confirmation=c_rooms)), flush=True)


def amendments():
    """Recorded, scoped replacements of locked files after the lock.

    An amendment may only touch code that neither flew nor judged: the flights
    and their evidence stay as flown, and the auditor's rules stay as locked.
    Each entry carries the reason, the file, its sha256 before and after, and
    the sha256 of the unified diff. They are published in the report.
    """
    path = LAB/'amendments.json'
    return load(path) if path.exists() else []


def require_lock():
    lock = load(LOCK)
    if canonical_sha({k: v for k, v in lock.items() if k != 'sha256'}) != lock['sha256']:
        raise SystemExit('lock self-hash')
    now = inventory()
    expected = dict(lock['inventory'])
    for entry in amendments():
        if expected.get(entry['path']) != entry['before']:
            raise SystemExit('amendment does not apply to the locked file: '+entry['path'])
        expected[entry['path']] = entry['after']
    if now != expected:
        changed = sorted(k for k in set(now) | set(expected) if now.get(k) != expected.get(k))
        raise SystemExit('code changed after freeze: '+str(changed))
    data = locked_data()
    for key, value in data.items():
        if lock[key] != value:
            raise SystemExit('locked data changed after freeze: '+key)
    for name in ('validation', 'confirmation'):
        excluded = {tuple(g) for g in lock['excluded_geometries'][name]}
        if rooms(name, excluded=excluded) != lock['rooms'][name]:
            raise SystemExit('room rule does not reproduce the locked rooms')
    if {str(s): handover(s, lock['power_model']) for s in lock['rooms']['validation']+lock['rooms']['confirmation']} \
            != lock['handovers']:
        raise SystemExit('handover rule does not reproduce the lock')
    return lock


def closed(name, lock):
    """A stage summary as stored at close, checked against a fresh recomputation."""
    stored = load(LAB/f'{name}-summary.json')
    again = summary(FOLDERS[name], stage_plan(name, lock), code=case_code(), lock=lock)
    same = {k: stored[k] for k in ('green', 'rows', 'aggregate')} == {k: again[k] for k in ('green', 'rows', 'aggregate')}
    return stored, again, same


def stage(name):
    lock = require_lock()
    plan = stage_plan(name, lock)
    if [spec['seed'] for _, spec in plan][::len(CONDITIONS)] != lock['rooms'][name]:
        raise SystemExit('room plan differs from the lock')
    if (LAB/f'{name}-summary.json').exists():
        raise SystemExit(name+' already closed')
    extra = {}
    if name == 'confirmation':
        b, _, same = closed('validation', lock)
        if not (b['green'] and b['lock_sha256'] == lock['sha256'] and same):
            raise SystemExit('C stays sealed: B is not green under this lock or changed after closing')
        extra['validation_summary_sha256'] = file_sha(LAB/'validation-summary.json')
    fly(FOLDERS[name], plan, lock['sha256'])
    value = summary(FOLDERS[name], plan, code=case_code(), lock=lock)
    value.update(lock_sha256=lock['sha256'], **extra)
    save(LAB/f'{name}-summary.json', value)
    print(json.dumps(dict(stage=name, green=value['green'], passed=value['aggregate']['passed'],
                          flights=value['aggregate']['flights'])), flush=True)


def certificate():
    """The whole report, rebuilt from raw evidence under the lock. Deterministic."""
    lock = require_lock()
    code = case_code()
    stages, custody = {}, {}
    for name in ('validation', 'confirmation'):
        stored, value, same = closed(name, lock)
        value['probes'] = probe_counts(value)
        stages[name] = value
        custody[name] = dict(summary_sha256=file_sha(LAB/f'{name}-summary.json'), unchanged_since_close=same,
                             lock=stored['lock_sha256'] == lock['sha256'])
    c_summary = load(LAB/'confirmation-summary.json')
    custody['confirmation']['opened_after_green_b'] = (
        c_summary.get('validation_summary_sha256') == custody['validation']['summary_sha256']
        and stages['validation']['green'])
    recorded = {r['case']: canonical_sha(r['files']) for r in load(LAB/'validation-summary.json')['rows']}
    plan_b, plan_c = stage_plan('validation', lock), stage_plan('confirmation', lock)
    controls_b = control_report(FOLDERS['validation'], plan_b)
    controls_c = control_report(FOLDERS['confirmation'], plan_c)
    mutants = mutant_report(FOLDERS['validation'], plan_b)
    manipulations = manipulation_report(FOLDERS['validation'], plan_b, recorded, code=code, lock=lock)
    b, cc = stages['validation'], stages['confirmation']
    evidence = all(r['evidence_valid'] for s in stages.values() for r in s['rows'])
    all_mutants = all(v['detected_in'] > 0 for v in mutants.values())
    all_manip = all(v['rejected'] for v in manipulations.values())
    hard_zero = all(not any(s['aggregate']['hard'].values()) for s in stages.values())
    probes_ok = all(s['probes']['flights_all_blocked'] == s['probes']['flights'] > 0 for s in stages.values())
    custody_ok = all(v['unchanged_since_close'] and v['lock'] for v in custody.values()) \
        and custody['confirmation']['opened_after_green_b']
    sitl = (b['green'] and cc['green'] and evidence and all_mutants and all_manip and hard_zero and probes_ok
            and custody_ok)
    report = dict(
        milestone='DRONE-3', scope='PX4 v1.15.4 + Gazebo Harmonic SITL on one host; simulated sensors and '
        'battery; no hardware, HIL or physical cage', lock_sha256=lock['sha256'], custody=custody,
        amendments=amendments(),
        stages={k: dict(green=v['green'], aggregate=v['aggregate'], probes=v['probes'],
                        rows=[{kk: vv for kk, vv in r.items() if kk != 'files'} for r in v['rows']],
                        files={r['case']: canonical_sha(r['files']) for r in v['rows']})
                for k, v in stages.items()},
        controls=dict(validation=controls_b, confirmation=controls_c), mutants=mutants,
        manipulations=manipulations,
        flags=dict(evidence_valid=evidence, mutants_detected=all_mutants, manipulations_rejected=all_manip,
                   hard_constraints_zero=hard_zero, probes_blocked=probes_ok, custody=custody_ok,
                   drone3_sitl_green=sitl, drone3_hil_green=False, drone3_cage_green=False,
                   drone3_green=False),
        not_integrated=dict(HOST='no preregistered condition requires a source',
                            DYNAMIC='not declared integrated: no measurable role in this mission',
                            PATTERN='not declared integrated: no measurable role in this mission'),
        limits='HIL and cage need hardware (docs/DRONE3-HARDWARE-HANDOFF.md). Energy is PX4 SITL simulated '
               'charge, never measured joules.')
    report['certificate_sha256'] = canonical_sha(report)
    return report


def certify():
    if REPORT.exists():
        raise SystemExit('report exists; use audit')
    report = certificate()
    save(REPORT, report)
    print(json.dumps(dict(certificate_sha256=report['certificate_sha256'], flags=report['flags']),
                     sort_keys=True), flush=True)


def audit_report():
    stored = load(REPORT)
    again = certificate()
    same = again == stored
    print(json.dumps(dict(reproduced=same, certificate_sha256=again['certificate_sha256'],
                          stored_sha256=stored['certificate_sha256'], flags=again['flags']),
                     sort_keys=True), flush=True)
    return same


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('a1', 'calibrate', 'a2', 'a2-summary', 'freeze', 'validation',
                                       'confirmation', 'certify', 'audit', 'plan'))
    p.add_argument('--folder', default='development2', help='A2 folder (a fresh one per A2 round)')
    args = p.parse_args()
    if args.command == 'a1':
        fly(FOLDERS['development'], a1_plan())
    elif args.command == 'calibrate':
        calibrate()
    elif args.command == 'a2':
        fly(args.folder, a2_plan())
    elif args.command == 'a2-summary':
        s = summary(args.folder, a2_plan())
        print(json.dumps(dict(green=s['green'], aggregate=s['aggregate'],
                              rows=[(r['case'], r['passed'], r.get('findings'), r.get('failures')) for r in s['rows']]),
                         indent=1, default=str))
    elif args.command == 'freeze':
        freeze(args.folder)
    elif args.command in ('validation', 'confirmation'):
        stage(args.command)
    elif args.command == 'certify':
        certify()
    elif args.command == 'audit':
        raise SystemExit(0 if audit_report() else 1)
    else:
        print(json.dumps(dict(a1=[l for l, _ in a1_plan()], rooms_a=rooms('development')), indent=1))


if __name__ == '__main__':
    main()
