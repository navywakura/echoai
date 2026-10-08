"""SENSOR-1S v2: v1's coordinator, copied; only namespace, seeds, channel
fields and history change. Criteria, evaluator and limits are v1's.

SENSOR-1S: one prospective chain, raw evidence, an audit that rebuilds it.

Same discipline as FLIGHT-1S v6: protocol, code, history and regression
are locked before validation A; A opens the bench only if it passes and
its evidence audits clean; every planned episode is flown; a PX4 that
never answers is relaunched once before anything reaches the vehicle; no
aggregator can stop the chain; the report is always written.
"""
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

from echoai.nexus0.flight1s.runtime import Runtime
from echoai.nexus0.flight1s.session import Episode
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.flight1s_v6 import contract as v6
from echoai.nexus0.flight1s_v6.campaign import patched_runtime
from echoai.nexus0.sim3 import runtime as sim3runtime, sandbox
from echoai.nexus0.sim3.canon import dump_report, report_sha256, sha256_bytes
from echoai.nexus0.sensor1s import contract, evaluate, model
from echoai.nexus0.sensor1s import campaign as v1
from . import session

HERE = Path(__file__).resolve().parent
ROOT = c.ECHOAI/'lab/sensor1s-v2'
REPORT = c.ECHOAI/'lab/echo3_sensor1s_v2_report.json'
LOG = c.ECHOAI/'lab/sensor1s-v2-run.log'
MODULES = ('test_sensor1s_v2', 'test_sensor1s', 'test_flight1s_v6', 'test_sim3', 'test_nexus0')
TARGET = v1.TARGET
SOURCE_NAMES = v1.SOURCE_NAMES
mutant_caught = v1.mutant_caught
GROUPS = ('execution', 'schema', 'isolation', 'source', 'time', 'validity', 'loss', 'latency', 'noise')


def jsonable(x):
    return json.loads(json.dumps(x))


def protocol():
    return jsonable(dict(
        version=2, slice='SENSOR-1S', configuration=contract.configuration(),
        channel='separate_process', pipe_bytes=1 << 20,
        sources=contract.SOURCES, expected_fields=contract.EXPECTED, noise=contract.NOISE,
        faults=contract.FAULTS,
        fault_times_s=contract.FAULT_TIMES_S, mutants=contract.MUTANTS, mutant_targets=TARGET,
        limits=evaluate.LIMITS, latency_p99_bound_ns=contract.LATENCY_P99_BOUND_NS,
        pooled=dict(n_min_stage=1000), boot=v6.BOOT, workers=2, automatic_retries=0,
        stages={'validation': dict(worlds=4, repeats=2, seed=20261011, controls=4),
                'bench': dict(worlds=12, repeats=1, seed=20261012, mutants=len(contract.MUTANTS))}))


def validate(p):
    if p != protocol():
        raise ValueError('SENSOR-1S protocol differs from preregistration')


def group(cases):
    return dict(status='pass' if cases and all(x['ok'] for x in cases) else 'fail', cases=cases)


def read(path):
    return json.loads(Path(path).read_text())


def relative(path):
    return str(Path(path).relative_to(c.ECHOAI))


def seal(d):
    d = {k: v for k, v in d.items() if k != 'sha256'}
    return dict(d, sha256=report_sha256(d))


def save(path, d):
    if path.exists():
        raise FileExistsError('Immutable evidence already exists: '+str(path))
    dump_report(path, d)


def fingerprint(paths):
    return seal(dict(files={relative(p): sha256_bytes(p.read_bytes()) for p in sorted(set(paths))}))


def history():
    paths = [p for p in (ROOT/'dev').rglob('*') if p.is_file()] if (ROOT/'dev').exists() else []
    paths += [p for p in (c.ECHOAI/'lab').glob('echo3_flight1s*.json')]
    paths += [c.ECHOAI/'lab/flight1s-v6/lock.json', c.ECHOAI/'docs/FLIGHT1S-V6-RESULTS.md']
    paths += [p for p in (c.ECHOAI/'lab/sensor1s').rglob('*') if p.is_file()]
    paths += [c.ECHOAI/'lab/echo3_sensor1s_report.json', c.ECHOAI/'lab/sensor1s-run.log',
              c.ECHOAI/'docs/SENSOR1S-RESULTS.md']
    return fingerprint(paths)


def inventory():
    paths = [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    for name in ('sensor1s', 'flight1s_v6', 'flight1s_v5', 'flight1s_v4', 'sim3', 'flight1s'):
        paths += [p for p in (c.ECHOAI/'nexus0'/name).rglob('*.py')]
    paths += [c.ECHOAI/'docs/SENSOR1S-DESIGN.md', c.ECHOAI/'docs/SENSOR1S-V2-DESIGN.md']
    paths += [p for p in (c.ECHOAI/'nexus0/sensor1s/assets').rglob('*') if p.is_file()
              and '__pycache__' not in p.parts]
    paths += [c.ECHOAI/'tests'/(m+'.py') for m in MODULES]
    return fingerprint(paths)


def regression():
    cases = []
    for mod in MODULES:
        print('regression '+mod, flush=True)
        pr = subprocess.run([sys.executable, '-m', 'echoai.tests.'+mod, '-q'],
                            env=dict(os.environ, PYTHONPATH=str(c.ECHOAI.parent)),
                            cwd=c.ECHOAI, capture_output=True, timeout=2400)
        log = ROOT/'regression'/(mod+'.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(pr.stdout+pr.stderr)
        cases.append(dict(name=mod, ok=pr.returncode == 0, returncode=pr.returncode,
                          path=relative(log), sha256=sha256_bytes(log.read_bytes())))
    return group(cases)


def freeze():
    if (ROOT/'lock.json').exists() or REPORT.exists():
        raise FileExistsError('SENSOR-1S v2 already frozen')
    ROOT.mkdir(parents=True, exist_ok=True)
    p = protocol()
    if not model.check()['ok']:
        raise RuntimeError('rig model does not derive from the pinned stock SDFs')
    inv = inventory()
    reg = regression()
    save(ROOT/'regression.json', reg)
    if reg['status'] != 'pass' or inv != inventory():
        raise RuntimeError('Regression failed or code changed; no flights authorised')
    flight = c.preflight(write=False)
    flight.require()
    flight.lock = patched_runtime(flight.lock)
    flight.lock['container']['image'] = flight.lock['container']['image_id']
    flight.lock['lock_sha256'] = report_sha256({k: v for k, v in flight.lock.items() if k != 'lock_sha256'})
    cage = sim3runtime.preflight(write=False)
    hist = history()
    save(ROOT/'history.json', hist)
    lock = seal(dict(version=2, created_utc=datetime.now(timezone.utc).isoformat(),
                     protocol=p, protocol_sha256=report_sha256(p), inventory=inv,
                     runtime=flight.lock, cage=cage.lock, model=model.check(),
                     history_sha256=hist['sha256'], regression=reg))
    save(ROOT/'lock.json', lock)
    save(ROOT/'protocol.json', p)
    print('FROZEN '+lock['sha256'], flush=True)
    return lock


def packages(stage, p):
    tmp, pk = legacy.generate_suite_unique()
    return tmp, pk[:p['stages'][stage]['worlds']]


def job_seed(stage_seed, label):
    return int(hashlib.sha256(f'{stage_seed}:{label}'.encode()).hexdigest()[:8], 16)


def jobs(pk, stage, p):
    """(label, package, arm, condition, faulted, mutant, seed), in flight order."""
    spec = p['stages'][stage]
    order = c.condition_order(spec['seed'], len(pk)*spec['repeats'])
    out = []
    for i, g in enumerate(pk):
        for repeat in range(1, spec['repeats']+1):
            slot = i*spec['repeats'] + repeat - 1
            for cond in order[2*slot:2*slot+2]:
                arm = 'faulted' if cond == 'perturbed' else 'clean'
                label = f'{arm}-{g.package_id}-r{repeat}'
                out.append((label, i, arm, 'perturbed', arm == 'faulted', None,
                            job_seed(spec['seed'], label)))
    for i in range(spec.get('controls', 0)):
        label = f'control-{pk[i].package_id}'
        out.append((label, i, 'control', 'nominal', False, None, job_seed(spec['seed'], label)))
    for k, name in enumerate(contract.MUTANTS[:spec.get('mutants', 0)]):
        label = f'mutant-{name}-{pk[k].package_id}'
        out.append((label, k, 'mutant', 'perturbed', True, name, job_seed(spec['seed'], label)))
    return out


def set_aside(root, label, n):
    moved = {}
    for sub, ext in (('private', 'jsonl'), ('transcript', 'jsonl'), ('ulogs', 'ulg')):
        src = root/sub/f'{label}.{ext}'
        if src.exists():
            dst = root/'boots'/f'{label}-boot{n}.{sub}.{ext}'
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            moved[sub] = dict(path=relative(dst), sha256=sha256_bytes(dst.read_bytes()))
    return moved


def fly(flight, cage, g, job, root, p):
    label, _, arm, cond, faulted, mutant, seed = job
    spec = contract.spec(contract.schedule(seed, faulted), mutant)
    print('start '+label, flush=True)
    restarts = []
    for n in range(1, p['boot']['restarts']+2):
        ep, sensors = session.run_episode(flight, cage, g, p['configuration'], spec,
                                          condition=cond, label=label, root=root)
        if n > p['boot']['restarts'] or not v6.boot_hung(ep.trace()):
            break
        print(f'boot_restart {label}: attempt {n} {ep.cause}', flush=True)
        trace = root/'boots'/f'{label}-boot{n}.episode.json'
        trace.parent.mkdir(parents=True, exist_ok=True)
        dump_report(trace, ep.trace())
        restarts.append(dict(attempt=n, trace=relative(trace), trace_sha256=sha256_bytes(trace.read_bytes()),
                             moved=set_aside(root, label, n), cause=ep.cause))
    dump_report(root/'episodes'/(label+'.json'), ep.trace())
    record = dict(sensors, label=label, arm=arm, condition=cond, faulted=faulted, mutant=mutant,
                  seed=seed, spec=spec, package_id=g.package_id, boot_restarts=restarts,
                  trace=relative(root/'episodes'/(label+'.json')),
                  trace_sha256=sha256_bytes((root/'episodes'/(label+'.json')).read_bytes()),
                  ulog_sha256=ep.ulog_sha256)
    save(root/'sensors'/(label+'.json'), record)
    print(f"done {label}: ok={ep.ok} frames={sensors['forwarder']['frames']} restarts={len(restarts)}",
          flush=True)
    return record


def evaluate_record(record, g, p):
    """Rebuild one episode's evaluation from files on disk. Never raises."""
    try:
        trace = read(c.ECHOAI/record['trace'])
        P = evaluate.load_private(c.ECHOAI/record['private'])
        T = evaluate.load_transcript(c.ECHOAI/record['transcript'])
        lim = dict(evaluate.LIMITS, **{k: tuple(v) if isinstance(v, list) else v
                                       for k, v in p['limits'].items()})
        return evaluate.episode(trace, P, T, record['consumer'], record['forwarder'], g.package,
                                record['spec'], condition=record['condition'],
                                bounds=p['latency_p99_bound_ns'], lim=lim)
    except Exception as exc:
        return {'execution': [evaluate.case('evaluator', False,
                                            error=type(exc).__name__+': '+str(exc)[:300])]}


def stage_groups(records, evals, stage, p, planned, cage_test):
    gs = {}
    normal = [(r, e) for r, e in zip(records, evals) if r['arm'] != 'mutant']
    for name in GROUPS:
        cases = []
        for r, e in normal:
            ep = e.get(name)
            cases.append(dict(label=r['label'], ok=bool(ep) and all(x['ok'] for x in ep)))
        gs[name] = group(cases)
    pooled = []
    for source in ('lidar', 'depth'):
        acc, want = dict(ss=0.0, df=0, bias_sum=0.0, bias_n=0), set()
        for r, e in normal:
            for x in e.get('noise', []):
                if x['name'] == source:
                    for k in acc:
                        acc[k] += x.get(k) or 0
                    want.add(x.get('declared'))
        ok, st = evaluate.noise_verdict(acc, next(iter(want)) if len(want) == 1 else None,
                                        p['limits'], p['pooled']['n_min_stage'])
        pooled.append(dict(name=source, ok=ok is True, declared=sorted(want, key=str), **st))
    gs['noise_pooled'] = group(pooled)
    gs['denominator'] = group([dict(ok=len(records) == planned, observed=len(records), expected=planned)])
    gs['cage'] = group([dict(name='self_test', ok=bool(cage_test.get('ok')))])
    gs['model'] = group([dict(name='derivation', ok=model.check()['ok'])])
    if stage == 'bench':
        mut = []
        by_label = {r['label']: e for r, e in zip(records, evals)}
        for r, e in zip(records, evals):
            if r['arm'] != 'mutant':
                continue
            target = TARGET[r['mutant']]
            flew = any(x['name'] == 'flight' and x['ok'] for x in e.get('execution', []))
            caught = mutant_caught(r['mutant'], e.get(target, []))
            twin = by_label.get(f"faulted-{r['package_id']}-r1", {})
            twin_ok = bool(twin.get(target)) and all(x['ok'] for x in twin[target])
            mut.append(dict(name=r['mutant'], label=r['label'], target=target, flew=flew,
                            caught=caught, honest_twin_passes=twin_ok, ok=flew and caught and twin_ok))
        gs['mutants'] = group(mut)
    return gs


def slim(evals):
    return [evaluate.summarize(e) for e in evals]


def run_stage(lock, stage):
    root = ROOT/stage
    if root.exists():
        raise FileExistsError('Stage is immutable: '+stage)
    p = lock['protocol']
    if stage == 'bench':
        a = read(ROOT/'validation/report.json')
        audited = audit_stage(a, lock)
        save(ROOT/'validation/audit.json', audited)
        if not a['passed'] or not audited['evidence_valid']:
            raise RuntimeError('Validation A failed; bench not authorised')
    root.mkdir()
    if inventory() != lock['inventory'] or history()['sha256'] != lock['history_sha256']:
        raise RuntimeError('Frozen code/history changed')
    flight = Runtime(available=True, lock=lock['runtime'])
    cage = sim3runtime.Runtime(available=True, lock=lock['cage'])
    cage_test = sandbox.self_test(cage)
    save(root/'cage_self_test.json', cage_test)
    tmp, pk = packages(stage, p)
    try:
        schedule = jobs(pk, stage, p)
        start = time.monotonic()
        def one(job):
            try:
                return fly(flight, cage, pk[job[1]], job, root, p)
            except Exception as exc:
                print('exception '+job[0]+': '+repr(exc)[:300], flush=True)
                record = dict(label=job[0], arm=job[2], condition=job[3], faulted=job[4], mutant=job[5],
                              seed=job[6], package_id=pk[job[1]].package_id,
                              error=type(exc).__name__+': '+str(exc)[:300])
                save(root/'sensors'/(job[0]+'.json'), record)
                return record
        with ThreadPoolExecutor(max_workers=p['workers']) as ex:
            records = list(ex.map(one, schedule))
        evals = [evaluate_record(r, pk[j[1]], p) if 'error' not in r else
                 {'execution': [evaluate.case('coordinator', False, error=r['error'])]}
                 for r, j in zip(records, schedule)]
        gs = stage_groups(records, evals, stage, p, len(schedule), cage_test)
        gs['frozen'] = group([dict(name='code', ok=inventory() == lock['inventory']),
                              dict(name='history', ok=history()['sha256'] == lock['history_sha256'])])
        result = seal(dict(version=2, stage=stage, lock_sha256=lock['sha256'], simulated_sensors=True,
                           agent_in_gazebo=False, cortex_calls=0, wsp_writes=0,
                           hardware_status='not_available', dataset_kind='rehearsal',
                           records=records, evaluations=slim(evals), groups=gs, cage_self_test=cage_test,
                           passed=all(x['status'] == 'pass' for x in gs.values()),
                           wall_s=round(time.monotonic()-start, 2)))
        save(root/'report.json', result)
        print(json.dumps(dict(stage=stage, passed=result['passed'],
                              groups={k: v['status'] for k, v in gs.items()})), flush=True)
        return result
    finally:
        tmp.cleanup()


def audit_stage(r, lock):
    findings, checks = [], 0
    def check(name, ok):
        nonlocal checks
        checks += 1
        if not ok:
            findings.append(name)
    try:
        p = lock['protocol']
        validate(p)
        check('report_hash', r == seal(r))
        check('lock_hash', lock == seal(lock) and r['lock_sha256'] == lock['sha256'])
        check('code', inventory() == lock['inventory'])
        check('isolation_flags', r['agent_in_gazebo'] is False and r['cortex_calls'] == 0
              and r['wsp_writes'] == 0 and r['simulated_sensors'] is True)
        stage = r['stage']
        check('cage_file', read(ROOT/stage/'cage_self_test.json') == r['cage_self_test'])
        tmp, pk = packages(stage, p)
        try:
            schedule = jobs(pk, stage, p)
            check('denominator', len(r['records']) == len(schedule))
            evals = []
            for rec, job in zip(r['records'], schedule):
                label = job[0]
                check('assignment/'+label, rec['label'] == label and rec['seed'] == job[6]
                      and rec['mutant'] == job[5] and rec['condition'] == job[3]
                      and rec['package_id'] == pk[job[1]].package_id)
                check('record_file/'+label, read(ROOT/stage/'sensors'/(label+'.json')) == rec)
                if 'error' in rec:
                    evals.append({'execution': [evaluate.case('coordinator', False, error=rec['error'])]})
                    continue
                check('spec/'+label, rec['spec'] == contract.spec(contract.schedule(job[6], job[4]), job[5]))
                for key in ('trace', 'private', 'transcript'):
                    path = rec.get(key)
                    want = rec.get(key+'_sha256')
                    check(f'{key}_hash/'+label, path is not None and
                          sha256_bytes((c.ECHOAI/path).read_bytes()) == want)
                ulog = ROOT/stage/'ulogs'/(label+'.ulg')
                check('ulog/'+label, (ulog.exists() and sha256_bytes(ulog.read_bytes()) == rec['ulog_sha256'])
                      or (not ulog.exists() and rec['ulog_sha256'] is None))
                marks = session.canaries(pk[job[1]])
                heads = [t['h'] for t in evaluate.load_transcript(c.ECHOAI/rec['transcript'])]
                check('canary_rescan/'+label, not [m for m in marks if any(m in h for h in heads)])
                for b in rec.get('boot_restarts', []):
                    t = read(c.ECHOAI/b['trace'])
                    check('boot/'+label, v6.boot_hung(t) and sha256_bytes((c.ECHOAI/b['trace']).read_bytes())
                          == b['trace_sha256'] and len(rec['boot_restarts']) <= p['boot']['restarts'])
                evals.append(evaluate_record(rec, pk[job[1]], p))
            check('evaluations', r['evaluations'] == slim(evals))
            gs = stage_groups(r['records'], evals, stage, p, len(schedule), r['cage_self_test'])
            gs['frozen'] = group([dict(name='code', ok=inventory() == lock['inventory']),
                                  dict(name='history', ok=history()['sha256'] == lock['history_sha256'])])
            check('groups', r['groups'] == gs)
            check('passed', r['passed'] == all(x['status'] == 'pass' for x in gs.values()))
        finally:
            tmp.cleanup()
    except Exception as exc:
        check('malformed_evidence/'+type(exc).__name__+': '+str(exc)[:200], False)
    return dict(evidence_valid=not findings, checks=checks, findings=findings,
                passed=r.get('passed', False), episodes=len(r.get('records', [])))


def audit():
    lock = read(ROOT/'lock.json')
    findings = []
    if lock != seal(lock) or read(ROOT/'protocol.json') != lock['protocol']:
        findings.append('lock_or_protocol_file')
    if history() != read(ROOT/'history.json'):
        findings.append('history_changed')
    reg = lock['regression']
    if reg != read(ROOT/'regression.json') or reg['status'] != 'pass' \
            or [x['name'] for x in reg['cases']] != list(MODULES):
        findings.append('regression')
    stages = {s: audit_stage(read(ROOT/s/'report.json'), lock)
              for s in ('validation', 'bench') if (ROOT/s/'report.json').exists()}
    valid = not findings and bool(stages) and all(x['evidence_valid'] for x in stages.values())
    green = valid and set(stages) == {'validation', 'bench'} and all(x['passed'] for x in stages.values())
    return dict(evidence_valid=valid, findings=findings, stages=stages, sensor1s_green=green)


def mutations(r, lock):
    cases = []
    def flip(x):
        g = next(iter(x['groups']))
        x['groups'][g]['status'] = 'pass' if x['groups'][g]['status'] == 'fail' else 'fail'
    changes = {
        'omit_record': lambda x: x['records'].pop(),
        'fake_green': lambda x: x.update(passed=not x['passed']),
        'flip_group': flip,
        'forge_consumer_tally': lambda x: x['records'][0]['consumer'].update(frames=0),
        'activate_agent': lambda x: x.update(agent_in_gazebo=True),
    }
    for name, fn in changes.items():
        m = copy.deepcopy(r)
        try:
            fn(m)
        except Exception as exc:
            cases.append(dict(name=name, ok=False, why='not_applicable: '+repr(exc)[:100]))
            continue
        res = audit_stage(seal(m), lock)
        cases.append(dict(name=name, ok=not res['evidence_valid'], findings=res['findings'][:5]))
    return group(cases)


def run():
    """Every path ends in a sealed report, including a stage that raised."""
    lock = freeze() if not (ROOT/'lock.json').exists() else read(ROOT/'lock.json')
    validate(lock['protocol'])
    errors, a = {}, None
    a_path, b_path = ROOT/'validation/report.json', ROOT/'bench/report.json'
    try:
        a = read(a_path) if a_path.exists() else run_stage(lock, 'validation')
    except Exception as exc:
        errors['validation'] = type(exc).__name__+': '+str(exc)[:300]
    if a is not None and a.get('passed'):
        try:
            run_stage(lock, 'bench')
        except Exception as exc:
            errors['bench'] = type(exc).__name__+': '+str(exc)[:300]
    result = audit() if (a_path.exists() or b_path.exists()) else dict(
        evidence_valid=False, findings=['no_stage_report'], stages={}, sensor1s_green=False)
    target = read(b_path) if b_path.exists() else (read(a_path) if a_path.exists() else None)
    result['mutation_tests'] = mutations(target, lock) if target else group([])
    result['sensor1s_green'] &= result['mutation_tests']['status'] == 'pass' and not errors
    result.update(version=2, lock_sha256=lock['sha256'], scope='simulated_sensors_sitl',
                  stage_errors=errors)
    save(REPORT, seal(result))
    print(json.dumps(result, indent=2), flush=True)
    return result['sensor1s_green']


def start():
    """Launch `run` in its own session so the chain outlives the shell."""
    if (ROOT/'lock.json').exists() or REPORT.exists() or LOG.exists():
        raise FileExistsError('SENSOR-1S v2 already started')
    with open(LOG, 'xb') as out:
        proc = subprocess.Popen([sys.executable, '-u', '-m', 'echoai.nexus0.sensor1s_v2.campaign', 'run'],
                                cwd=c.ECHOAI, env=dict(os.environ, PYTHONPATH=str(c.ECHOAI.parent)),
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    print(json.dumps(dict(pid=proc.pid, log=relative(LOG))), flush=True)
    return proc.pid


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['start', 'run', 'audit'])
    a = ap.parse_args()
    if a.command == 'start':
        start()
        raise SystemExit(0)
    if a.command == 'run':
        raise SystemExit(0 if run() else 1)
    res = audit()
    print(json.dumps(res, indent=2))
    raise SystemExit(0 if res['evidence_valid'] and res['sensor1s_green'] else 1)
