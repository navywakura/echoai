"""FLIGHT-1S v4: red closure of the interrupted validation chain.

No flights, no retries, no edits to v4 evidence. The frozen v4 coordinator
cannot resume (stage immutable) and its lock forbids editing it, so this
module lives outside nexus0/flight1s_v4 and outside every frozen inventory.
Group arithmetic is the frozen v4 contract applied to the flights that exist.
"""
import json
import math
from pathlib import Path

from echoai.nexus0.flight1s_v4 import campaign as v, contract as k
from echoai.nexus0.flight1s.v3 import certificate as legacy
from echoai.nexus0.sim3.canon import sha256_bytes

LOG_SOURCE = Path('/tmp/echoai-flight1s-v4.log')
LOG = v.ROOT/'run.log'
STAGE = 'validation'
# Observed by the operator, not derivable from the evidence files.
INTERRUPTION = dict(
    observed_local='2026-09-11T07:09:37+02:00',
    cause='parent agent session terminated; campaign process died with it',
    traceback=False, kernel_oom=False, automatic_retries=0,
    orphan_containers='exited on their own; output stayed in /tmp, never entered lab')


def log_state():
    raw = LOG.read_bytes()
    started, done = [], set()
    for line in raw.decode().splitlines():
        if line.startswith('start '): started.append(line[6:].strip())
        elif line.startswith('done '): done.add(line[5:].split(':')[0])
    return dict(path=v.relative(LOG), sha256=sha256_bytes(raw),
                in_flight=[x for x in started if x not in done],
                last_line=raw.decode().rstrip().splitlines()[-1])


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


def complete_world_contrast(rows, p):
    """Diagnostic only: the v4 separation gate needs all 4 world blocks."""
    pairs = {}
    for m in rows:
        pairs.setdefault((m['package_id'], m['repeat']), {})[m['condition']] = m['disturb_excursion_mm']
    worlds = {}
    for (pid, _), pair in sorted(pairs.items()):
        if set(pair) == {'nominal', 'perturbed'}:
            worlds.setdefault(pid, []).append(pair['perturbed']-pair['nominal'])
    n = p['stages'][STAGE]['repeats']
    return {pid: dict(pairs=len(d), mean_difference_mm=math.fsum(d)/len(d),
                      min_difference_mm=min(d), complete_block=len(d) == n)
            for pid, d in worlds.items()}


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
    expected = p['stages'][STAGE]['worlds']*p['stages'][STAGE]['repeats']*2
    try:
        gs = k.verdict(rows, STAGE, p, packages)
    except Exception as exc:
        gs = dict(verdict_error=k.group([dict(name=type(exc).__name__+': '+str(exc), ok=False)]))
    gs['negative_controls'] = k.group([dict(label='negative-'+g.package_id, ok=False,
                                            status='not_flown') for g in packages])
    gs['execution_interrupted'] = k.group([dict(ok=False, completed=len(rows), expected=expected,
                                                missing=missing)])
    gs['frozen'] = frozen
    failed_recovery = [m['recovery_verdict'] for m in rows
                       if m['condition'] == 'perturbed' and m['recovery']['status'] != 'recovered']
    evidence_valid = not findings and frozen['status'] == 'pass'
    return v.seal(dict(
        version=4, kind='interrupted_closure', stage=STAGE, lock_sha256=lock['sha256'],
        scope='flight_software_in_the_loop', legacy_precision_guarantee=False,
        agent_in_gazebo=False, cortex_calls=0, wsp_writes=0, new_flights=0,
        hardware_status='not_available', dataset_kind='rehearsal',
        interruption=dict(INTERRUPTION, log=log_state()),
        partial_audit=dict(evidence_valid=evidence_valid, checks=checks, findings=findings,
                           recomputed_episodes=len(rows)),
        groups=gs, group_status={name: g['status'] for name, g in gs.items()},
        failed_recovery=failed_recovery,
        diagnostics=dict(world_contrast=complete_world_contrast(rows, p),
                         nominal_above_250mm=[m['label'] for m in rows if m['condition'] == 'nominal'
                                              and m['disturb_excursion_mm'] > 250]),
        validation_passed=False, bench='not_authorised', stage_mutation_tests='not_run_no_stage_report',
        evidence_valid=evidence_valid, flight1s_green=False))


def close():
    if v.REPORT.exists():
        raise FileExistsError('Closure already written: '+str(v.REPORT))
    if not LOG.exists():
        LOG.write_bytes(LOG_SOURCE.read_bytes())
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
                              failed_recovery=[x['label'] for x in result['failed_recovery']]), indent=1))
    else:
        print(json.dumps(result, indent=1))
    ok = result['evidence_valid'] if args.command == 'close' else result['report_hash'] and result['rebuilt']
    raise SystemExit(0 if ok else 1)
