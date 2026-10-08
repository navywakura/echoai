"""Prospective factorial campaign and reconstructing acceptance certificate."""
import argparse
import copy
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path

from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.fusion1.bench import seal
from echoai.nexus0.sim3.sandbox import self_test
from echoai.nexus0.sim3.runtime import Runtime
from .core import attribute
from .session import ROOT, CONDITIONS, run
from .evaluate import audit_session
from .controls import mutations

REPORT = ECHOAI/'lab/echo3_cause1_report.json'
PROTOCOL = dict(version=1, development=list(range(20262501, 20262505)),
                validation=list(range(20262601, 20262605)), confirmation=list(range(20262701, 20262705)),
                conditions=list(CONDITIONS), minimum_correct=15, minimum_per_condition=3,
                residual_limit_mm=300, maximum_false_self=0, one_sided_p=.025)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory():
    paths = set((ECHOAI/'nexus0').rglob('*.py'))
    paths.update(ECHOAI.parent.glob('navi10_*.py'))
    paths.update((ECHOAI/'tests/test_cause1.py', ECHOAI/'docs/CAUSE1-DESIGN.md'))
    return {str(p.relative_to(ECHOAI) if p.is_relative_to(ECHOAI) else Path('..')/p.name): file_hash(p)
            for p in sorted(paths)}


def tree_hashes(root):
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def schedule(stage):
    out = []
    for seed in PROTOCOL[stage]:
        order = list(CONDITIONS)
        random.Random(seed).shuffle(order)
        out.extend((seed, c) for c in order)
    return out


def metrics(rows):
    groups = {c: [r for r in rows if r['condition'] == c] for c in CONDITIONS}
    wins = sum(r.get('correct', False) and not r.get('baseline_correct', False) for r in rows)
    losses = sum(not r.get('correct', False) and r.get('baseline_correct', False) for r in rows)
    n = wins+losses
    p = sum(math.comb(n, k) for k in range(wins, n+1))/2**n if n else 1.0
    correct = sum(r.get('correct', False) for r in rows)
    residual_ok = sum(r.get('residual_error_mm') is not None and r['residual_error_mm'] <= 300 for r in rows)
    per_condition = {c: dict(n=len(g), correct=sum(r.get('correct', False) for r in g)) for c, g in groups.items()}
    identities = {(r['seed'], r['condition']) for r in rows}
    seeds = {r['seed'] for r in rows}
    valid = (len(rows) == len(identities) == 16 and len(seeds) == 4
             and identities == {(s, c) for s in seeds for c in CONDITIONS}
             and all(r['evidence_valid'] for r in rows))
    execution = len(rows) == 16 and all(r['execution_green'] for r in rows)
    false_self = sum(r.get('false_self', False) for r in rows)
    # Wilson 95% interval over this finite bank's marginal proportion.
    total = len(rows)
    z = 1.959963984540054
    q = correct/total if total else 0
    denom = 1+z*z/total if total else 1
    centre = (q+z*z/(2*total))/denom if total else 0
    radius = z*math.sqrt(q*(1-q)/total+z*z/(4*total*total))/denom if total else 0
    green = (valid and execution and correct >= 15 and residual_ok >= 15 and false_self == 0
             and all(g['n'] == 4 and g['correct'] >= 3 for g in per_condition.values()) and p < .025)
    latencies = sorted(t for r in rows for t in r.get('consumer_latency_ns', []) if type(t) is int and t >= 0)
    return dict(n=total, correct=correct, correct_wilson95=[max(0, centre-radius), min(1, centre+radius)],
                per_condition=per_condition, baseline_correct=sum(r.get('baseline_correct', False) for r in rows),
                wins=wins, losses=losses, ties=total-n, sign_p=p, residual_ok=residual_ok,
                consumer_calls_measured=len(latencies),
                consumer_roundtrip_p99_ns=latencies[math.ceil(.99*len(latencies))-1] if latencies else None,
                false_self=false_self, evidence_valid=valid, execution_green=execution, stage_green=green)


def audit_stage(stage):
    rows = []
    for seed, condition in schedule(stage):
        path = ROOT/stage/f'{seed}-{condition}'
        if not path.is_dir():
            rows.append(dict(seed=seed, condition=condition, evidence_valid=False,
                             execution_green=False, findings=['missing_flight']))
            continue
        try:
            row = audit_session(path)
            cfg = json.loads((path/'configuration.json').read_text())
            if stage != 'development' and cfg.get('physics_seed') != seed*10+CONDITIONS.index(condition):
                row.update(evidence_valid=False, findings=row['findings']+['physics_seed'])
            if stage != 'development':
                copies = {'runner.py': 'nexus0/cause1/assets/runner.py',
                          'cause_core.py': 'nexus0/cause1/core.py',
                          'live_runner.py': 'nexus0/compose1_v3/assets/live_runner.py',
                          'flightrunner_survey.py': 'nexus0/pattern1r_v4/assets/flightrunner_survey.py'}
                for target, origin in copies.items():
                    if file_hash(path/target) != file_hash(ECHOAI/origin):
                        row.update(evidence_valid=False, findings=row['findings']+['copied_code:'+target])
            if row['seed'] != seed or row['condition'] != condition:
                row.update(evidence_valid=False, findings=row['findings']+['denominator_identity'])
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            row = dict(seed=seed, condition=condition, evidence_valid=False,
                       execution_green=False, findings=[type(exc).__name__+':'+str(exc)[:200]])
        rows.append(row)
    return dict(stage=stage, rows=rows, metrics=metrics(rows))


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    if seal({k: v for k, v in lock.items() if k != 'sha256'}) != lock:
        raise ValueError('invalid lock hash')
    if lock['protocol'] != PROTOCOL or lock['inventory'] != inventory():
        raise ValueError('frozen implementation changed')
    if lock['development_files'] != tree_hashes(ROOT/'development'):
        raise ValueError('development evidence changed')
    for name, sha in lock['parents'].items():
        if file_hash(ECHOAI/name) != sha:
            raise ValueError('parent evidence changed: '+name)
    return lock


def campaign(stage):
    if stage != 'development':
        require_lock()
        if stage == 'confirmation' and not audit_stage('validation')['metrics']['stage_green']:
            raise ValueError('red B cannot open C')
    for seed, condition in schedule(stage):
        if stage != 'development':
            require_lock()
        path = ROOT/stage/f'{seed}-{condition}'
        if path.exists():
            print('preserved', path.name, flush=True)
            continue
        run(path, seed, condition, physics_seed=(None if stage == 'development' else seed*10+CONDITIONS.index(condition)))
    report = audit_stage(stage)
    save(ROOT/(stage+'-summary.json'), seal(report))
    print(json.dumps(report['metrics'], sort_keys=True), flush=True)
    return report


def controls():
    from echoai.tests.test_cause1 import trial
    cases = []
    args = trial(); args[3]['accepted'] = False
    cases.append(('no_ack', args, 'unknown'))
    cases.append(('no_confirmation', trial(0, 0, -1000), 'unknown'))
    cases.append(('no_odometry', trial(), 'self'))
    args = trial()
    args[4].update(capture_ns=11_000_000_000, delivered_ns=11_000_000_000, odometry_ns=11_000_000_000)
    cases.append(('no_expiry', args, 'unknown'))
    result = {name: attribute(*args)['label'] == expected and
              attribute(*args, mutant=name)['label'] != expected for name, args, expected in cases}
    return dict(mutants=result, green=all(result.values()))


def freeze():
    if (ROOT/'lock.json').exists():
        raise FileExistsError('lock is immutable')
    dev = audit_stage('development')
    if not dev['metrics']['stage_green']:
        raise ValueError('development is not green')
    regression = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_cause1',
        'echoai.tests.test_qtable', 'echoai.tests.test_compose1_v3',
        'echoai.tests.test_nexus0.TestBench', 'echoai.tests.test_nexus0.TestGate',
        'echoai.tests.test_nexus0.TestAttend', '-q'], capture_output=True, text=True)
    save(ROOT/'regression.json', dict(returncode=regression.returncode, output=regression.stdout+regression.stderr))
    if regression.returncode:
        raise ValueError('regression failed')
    cage = self_test(Runtime(available=True,
        lock=json.loads((ECHOAI/'lab/pattern1r-v4/lock.json').read_text())['cage']))
    if not cage['ok'] or not controls()['green']:
        raise ValueError('isolation/controls failed')
    mutation_report = mutations(ROOT/'development'/f'{PROTOCOL["development"][0]}-self')
    save(ROOT/'mutations.json', mutation_report)
    if not mutation_report['green']:
        raise ValueError('evidence mutations escaped')
    parents = ('lab/echo3_compose1_v4_report.json', 'lab/compose1-v4/lock.json',
               'lab/flight1s-v6/lock.json', 'lab/nexus0_report.json')
    lock = seal(dict(protocol=PROTOCOL, inventory=inventory(), development_files=tree_hashes(ROOT/'development'),
                     parents={p: file_hash(ECHOAI/p) for p in parents}, cage=cage, controls=controls(),
                     mutations=mutation_report,
                     regression_sha256=file_hash(ROOT/'regression.json'), created_before_evaluation=True))
    save(ROOT/'lock.json', lock)
    print('lock', lock['sha256'], flush=True)


def reconstruct():
    lock = require_lock()
    b, c = audit_stage('validation'), audit_stage('confirmation')
    attacks = mutations(ROOT/'development'/f'{PROTOCOL["development"][0]}-self')
    if attacks != lock['mutations']:
        raise ValueError('mutation controls changed')
    return seal(dict(phase='CAUSE-1', lock_sha256=lock['sha256'], validation=b, confirmation=c,
                     mutations=attacks,
                     controls=controls(), evidence_valid=b['metrics']['evidence_valid'] and c['metrics']['evidence_valid'],
                     cause1_green=b['metrics']['stage_green'] and c['metrics']['stage_green'] and controls()['green'],
                     validation_files=tree_hashes(ROOT/'validation'), confirmation_files=tree_hashes(ROOT/'confirmation'),
                     scope='SITL planar normal, no unmeasured body forces, attribution hypothesis, no CAM writes'))


def verify_report(report, rebuilt):
    if report != rebuilt or seal({k: v for k, v in report.items() if k != 'sha256'}) != report:
        raise ValueError('report does not reconstruct from physical evidence')


def report_attacks(rebuilt):
    out = {}
    for name in ('false_green', 'omitted_flight', 'duplicate_seed', 'false_ack',
                 'false_label', 'false_residual', 'false_denominator'):
        trial = copy.deepcopy(rebuilt)
        rows = trial['validation']['rows']
        if name == 'false_green':
            trial['cause1_green'] = not trial['cause1_green']
        elif name == 'omitted_flight':
            rows.pop()
        elif name == 'duplicate_seed':
            rows[-1] = copy.deepcopy(rows[0])
        elif name == 'false_ack':
            rows[0]['execution_green'] = not rows[0]['execution_green']
        elif name == 'false_label':
            rows[0]['label'] = 'invented'
        elif name == 'false_residual':
            rows[0]['residual_error_mm'] = 99999
        else:
            trial['validation']['metrics']['n'] += 1
        trial = seal({k: v for k, v in trial.items() if k != 'sha256'})
        try:
            verify_report(trial, rebuilt)
            out[name] = False
        except ValueError:
            out[name] = True
    return dict(rejected=out, green=all(out.values()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('development', 'freeze', 'accept', 'audit', 'inspect'))
    parser.add_argument('--stage', choices=('development', 'validation', 'confirmation'), default='development')
    args = parser.parse_args()
    if args.command == 'development':
        if not campaign('development')['metrics']['stage_green']:
            raise SystemExit(1)
    elif args.command == 'freeze':
        freeze()
    elif args.command == 'accept':
        b = campaign('validation')
        if b['metrics']['stage_green']:
            campaign('confirmation')
        report = reconstruct()
        if REPORT.exists():
            raise FileExistsError('certificate already exists; audit instead')
        save(REPORT, report)
        save(ROOT/'report-mutations.json', report_attacks(report))
        print(json.dumps(dict(cause1_green=report['cause1_green'], sha256=report['sha256'])), flush=True)
        if not report['cause1_green']:
            raise SystemExit(1)
    elif args.command == 'audit':
        report = reconstruct()
        verify_report(json.loads(REPORT.read_text()), report)
        if not report_attacks(report)['green']:
            raise ValueError('report mutation escaped')
        print(json.dumps(dict(cause1_green=report['cause1_green'], sha256=report['sha256'])), flush=True)
        if not report['cause1_green']:
            raise SystemExit(1)
    else:
        print(json.dumps(audit_stage(args.stage), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
