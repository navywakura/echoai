"""FLIGHT-1S v5: red closure of the validation chain that stopped before its report.

No flights, no retries, no edits to v5 evidence. The frozen coordinator flew
all 64 A flights, then its inherited repetition aggregator raised KeyError on
an infrastructure-failed episode, so neither report.json nor the negative
controls exist. This module lives outside every frozen inventory. The frozen
verdict is re-run to record that failure; the groups beside it reuse the same
frozen pieces, with only the crashing aggregator caught.
"""
import json
from pathlib import Path

from echoai.nexus0.flight1s_v5 import campaign as v, contract as k
from echoai.nexus0.flight1s_v4_close import complete_world_contrast
from echoai.nexus0.flight1s.v2.bench import Bench
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.sim3.canon import sha256_bytes

LOG = c.ECHOAI/'lab/flight1s-v5-run.log'
STAGE = 'validation'


def log_state():
    raw = LOG.read_bytes(); text = raw.decode()
    started = [x[6:].strip() for x in text.splitlines() if x.startswith('start ')]
    done = {x[5:].split(':')[0] for x in text.splitlines() if x.startswith('done ')}
    tb = text[text.find('Traceback'):] if 'Traceback' in text else ''
    return dict(path=v.relative(LOG), sha256=sha256_bytes(raw),
                started=len(started), done=len(done),
                in_flight=[x for x in started if x not in done],
                traceback_last_line=tb.rstrip().splitlines()[-1] if tb else None)


def rebuild(lock):
    p = lock['protocol']; root = v.ROOT/STAGE
    findings = []; checks = 0
    def check(name, ok):
        nonlocal checks
        checks += 1
        if not ok: findings.append(name)
    tmp, packages = legacy.generate_suite_unique()
    try:
        packages = packages[:p['stages'][STAGE]['worlds']]
        rows, missing = [], []
        for g, cond, repeat, slot in v.jobs(packages, STAGE, p):
            meta = v.metadata(g, cond, repeat, slot, lock, root)
            path = root/'completed'/(meta['label']+'.json')
            if not path.exists():
                missing.append(meta['label']); continue
            m = v.read(path)
            check('assignment/'+meta['label'], all(m.get(x) == y for x, y in meta.items()))
            v.reconstruct(m, g, meta, lock, check)
            rows.append(m)
        known = {m['label'] for m in rows} | set(missing)
        for d in ('completed', 'episodes', 'metrics', 'ulogs'):
            for f in (root/d).iterdir():
                check('unexpected_file/'+d+'/'+f.name, f.name.rsplit('.', 1)[0] in known)
        check('no_stage_report', not (root/'report.json').exists())
        check('no_negatives_flown', not any(root.glob('*/negative-*')))
        return packages, rows, missing, checks, findings
    finally:
        tmp.cleanup()


def groups(rows, packages, p):
    """k.verdict step by step; only the aggregator that raised is caught."""
    cfg = p['configuration']
    gs = c.groups(rows, cfg)
    gs.pop('challenge')
    gs['challenge_perturbed'] = k.group([m['challenge'] for m in rows if m['condition'] == 'perturbed'])
    gs['physical_envelope'] = k.group([dict(label=m['label'], **m['v4_displacement']) for m in rows])
    gs['separation'] = k.separation(rows, STAGE, p)
    expected = p['stages'][STAGE]['worlds']*p['stages'][STAGE]['repeats']*2
    gs['denominator'] = k.group([dict(ok=len(rows) == expected, observed=len(rows), expected=expected)])
    b = Bench(report_path=Path('/unused'), protocol_path=None, verbose=False)
    try:
        b._group_repetition({(m['package_id'], m['repeat'], m['condition']): m
                             for m in rows if m['repeat'] <= 2}, cfg)
    except KeyError as exc:
        b.group('repetition', 'fail', cases=[dict(ok=False, why='frozen aggregator raised KeyError '
                                                  +str(exc)+' on an episode without measurement')])
    b._group_envelope(packages, cfg)
    gs.update(b.groups)
    return gs


def closure():
    lock = v.read(v.ROOT/'lock.json'); p = lock['protocol']
    k.validate(p)
    frozen = k.group([
        dict(name='lock_seal', ok=lock == v.seal(lock)),
        dict(name='protocol_file', ok=v.read(v.ROOT/'protocol.json') == lock['protocol']),
        dict(name='code', ok=v.inventory() == lock['inventory']),
        dict(name='history', ok=v.history()['sha256'] == lock['history_sha256']),
        dict(name='regression', ok=lock['regression'] == v.read(v.ROOT/'regression.json')
             and lock['regression']['status'] == 'pass')])
    packages, rows, missing, checks, findings = rebuild(lock)
    try:
        k.verdict(rows, STAGE, p, packages)
        frozen_verdict = dict(raised=None)
    except Exception as exc:
        frozen_verdict = dict(raised=type(exc).__name__+': '+str(exc))
    gs = groups(rows, packages, p)
    gs['negative_controls'] = k.group([dict(label='negative-'+g.package_id, ok=False,
                                            status='not_flown') for g in packages])
    gs['stage_report'] = k.group([dict(ok=False, why='coordinator stopped before report.json',
                                       frozen_verdict=frozen_verdict)])
    gs['frozen'] = frozen
    failed = [dict(label=m['label'], cause=m.get('cause'), status=m.get('status'))
              for m in rows if not m['ok']]
    clean = [m for m in rows if m['ok']]
    evidence_valid = not findings and frozen['status'] == 'pass'
    failed_labels = {x['label'] for x in failed}
    red_cases = {name: [x.get('label', x.get('package_id', x.get('name', x.get('why'))))
                        for x in g['cases'] if not x.get('ok', True)]
                 for name, g in gs.items() if g['status'] == 'fail'}
    return v.seal(dict(
        version=5, kind='stopped_before_report_closure', stage=STAGE, lock_sha256=lock['sha256'],
        scope='flight_software_in_the_loop', legacy_precision_guarantee=False,
        agent_in_gazebo=False, cortex_calls=0, wsp_writes=0, new_flights=0,
        hardware_status='not_available', dataset_kind='rehearsal',
        log=log_state(), frozen_verdict=frozen_verdict, missing=missing,
        partial_audit=dict(evidence_valid=evidence_valid, checks=checks, findings=findings,
                           recomputed_episodes=len(rows),
                           findings_on_failed_episodes_only=bool(findings) and all(
                               f.split('/', 1)[-1] in failed_labels for f in findings)),
        groups=gs, group_status={name: g['status'] for name, g in gs.items()},
        red_cases=red_cases,
        failed_episodes=failed,
        diagnostics=dict(
            note='excludes failed episodes; not a gate, not the preregistered denominator',
            world_contrast=complete_world_contrast(clean, p),
            perturbed_not_recovered=[m['label'] for m in clean if m['condition'] == 'perturbed'
                                     and m['recovery']['status'] != 'recovered'],
            nominal_above_250mm=[m['label'] for m in clean if m['condition'] == 'nominal'
                                 and m['disturb_excursion_mm'] > 250]),
        validation_passed=False, bench='not_authorised', stage_mutation_tests='not_run_no_stage_report',
        evidence_valid=evidence_valid, flight1s_green=False))


def close():
    if v.REPORT.exists():
        raise FileExistsError('Closure already written: '+str(v.REPORT))
    result = closure()
    v.save(v.REPORT, result)
    return result


def audit():
    saved = v.read(v.REPORT)
    return dict(report_hash=saved == v.seal(saved), rebuilt=saved == closure(),
                flight1s_green=saved['flight1s_green'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['close', 'audit'])
    args = parser.parse_args()
    result = close() if args.command == 'close' else audit()
    if args.command == 'close':
        print(json.dumps(dict(result['group_status'], evidence_valid=result['evidence_valid'],
                              failed=result['failed_episodes'],
                              frozen_verdict=result['frozen_verdict']), indent=1))
    else:
        print(json.dumps(result, indent=1))
    ok = result['evidence_valid'] if args.command == 'close' else result['report_hash'] and result['rebuilt']
    raise SystemExit(0 if ok else 1)
