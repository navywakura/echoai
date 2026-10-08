"""Prospective PX4-1 campaign. No retuning after freeze; red B seals C."""
import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from echoai.nexus0.compose1.bench import ECHOAI, save
from .session import ROOT, CONDITIONS, run
from .evaluate import audit, digest
from .controls import mutants, corruptions

REPORT = ECHOAI/'lab/echo3_px41_report.json'
PROTOCOL = dict(version=1, development=[20262801, 20262802], validation=[20262901, 20262902],
                confirmation=[20263001, 20263002], conditions=list(CONDITIONS))


def seal(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def inventory():
    files = list((ECHOAI/'nexus0').rglob('*.py')) + list(ECHOAI.parent.glob('navi10_*.py'))
    files += [ECHOAI/'docs/PX41-DESIGN.md', ECHOAI/'tests/test_px41.py', ECHOAI/'tests/test_cause1.py', ECHOAI/'tests/test_nexus0.py',
              ECHOAI/'lab/flight1s-v6/lock.json', ECHOAI/'lab/cause1/lock.json', ECHOAI/'lab/echo3_cause1_report.json']
    return {str(p.relative_to(ECHOAI) if p.is_relative_to(ECHOAI) else Path('..')/p.name): digest(p) for p in sorted(files)}


def parents():
    lock = json.loads((ECHOAI/'lab/cause1/lock.json').read_text())
    # Saved entries only: adding a new milestone does not alter an old source.
    entries = lock['inventory']
    bad = [p for p, expected in entries.items() if digest(ECHOAI/p) != expected]
    if bad:
        raise RuntimeError('changed frozen CAUSE sources '+str(bad))
    return dict(cause_lock=digest(ECHOAI/'lab/cause1/lock.json'), cause_report=digest(ECHOAI/'lab/echo3_cause1_report.json'), checked=len(entries))


def tests():
    result = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_px41',
                             'echoai.tests.test_cause1', 'echoai.tests.test_nexus0.TestGate',
                             'echoai.tests.test_nexus0.TestBench'],
                            cwd=ECHOAI.parent, capture_output=True, text=True)
    return dict(ok=result.returncode == 0, returncode=result.returncode, output=result.stdout+result.stderr)


def stage(name):
    rows = []
    for seed in PROTOCOL[name]:
        for condition in CONDITIONS:
            path = ROOT/name/f'{seed}-{condition}'
            value = audit(path)
            if value['valid']:
                cfg = json.loads((path/'configuration.json').read_text())
                if (cfg['seed'], cfg['condition']) != (seed, condition):
                    value.update(valid=False, findings=value['findings']+['denominator_identity'])
            rows.append(dict(seed=seed, condition=condition, audit=value,
                             hashes=hashes(path) if path.exists() else {}))
    n = len(rows)
    k = sum(r['audit']['valid'] for r in rows)
    z = 1.959963984540054
    p = k/n
    c = (p+z*z/(2*n))/(1+z*z/n)
    d = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    per_condition = {condition: dict(n=sum(r['condition'] == condition for r in rows),
        passed=sum(r['condition'] == condition and r['audit']['valid'] for r in rows)) for condition in CONDITIONS}
    return dict(n=n, passed=k, wilson95=[max(0, c-d), min(1, c+d)], green=k == n, rows=rows,
                per_condition=per_condition)


def fly(name):
    for seed in PROTOCOL[name]:
        for condition in CONDITIONS:
            path = ROOT/name/f'{seed}-{condition}'
            if not path.exists():
                run(path, seed, condition)
            result = audit(path)
            print(name, seed, condition, json.dumps(result), flush=True)
            if not result['valid']:
                return False
    return True


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    expected = lock.pop('lock_sha256')
    if seal(lock) != expected or lock['protocol'] != PROTOCOL:
        raise RuntimeError('lock/protocol changed')
    for name, value in lock['inventory'].items():
        if digest(ECHOAI/name) != value:
            raise RuntimeError('frozen source changed '+name)
    if lock['parents'] != parents() or lock['development'] != stage('development'):
        raise RuntimeError('parent/development changed')
    lock['lock_sha256'] = expected
    return lock


def reconstruct():
    lock = require_lock()
    validation, confirmation = stage('validation'), stage('confirmation')
    report = dict(milestone='PX4-1', scope='SITL bounded north/south/hold; one transaction per supervised session',
                  lock_sha256=lock['lock_sha256'], validation=validation, confirmation=confirmation,
                  green=validation['green'] and confirmation['green'], hardware=False,
                  parents=parents(), controls=lock['controls'])
    report['certificate_sha256'] = seal(report)
    return report


def verify_report(report):
    return report == reconstruct()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['development', 'freeze', 'accept', 'audit'])
    args = parser.parse_args()
    if args.command == 'development':
        if (ROOT/'lock.json').exists():
            raise RuntimeError('already frozen')
        if not fly('development'):
            raise SystemExit(1)
        save(ROOT/'development-report.json', stage('development'))
    elif args.command == 'freeze':
        if (ROOT/'lock.json').exists():
            raise RuntimeError('lock exists')
        dev = stage('development')
        regression = tests()
        controls = dict(mutants=mutants(), traces=corruptions(ROOT/'development/20262801-nominal'))
        if not (dev['green'] and regression['ok'] and all(v['detected'] for group in controls.values() for v in group.values())):
            save(ROOT/'freeze-failure.json', dict(development=dev, tests=regression, controls=controls))
            raise RuntimeError('freeze prerequisites red')
        lock = dict(protocol=PROTOCOL, inventory=inventory(), parents=parents(), development=dev,
                    tests=regression, controls=controls)
        lock['lock_sha256'] = seal(lock)
        save(ROOT/'lock.json', lock)
        print('frozen', lock['lock_sha256'])
    elif args.command == 'accept':
        require_lock()
        if REPORT.exists():
            raise RuntimeError('report exists; use audit')
        if not fly('validation'):
            save(ROOT/'validation-red.json', stage('validation'))
            raise SystemExit('B red; C not opened')
        fly('confirmation')
        report = reconstruct()
        save(REPORT, report)
        print('green', report['green'], report['certificate_sha256'])
        if not report['green']:
            raise SystemExit(1)
    else:
        report = json.loads(REPORT.read_text())
        if not verify_report(report):
            raise SystemExit('report mismatch')
        mutated = copy.deepcopy(report)
        mutated['validation']['passed'] += 1
        value = {k: v for k, v in mutated.items() if k != 'certificate_sha256'}
        mutated['certificate_sha256'] = seal(value)
        rejected = not verify_report(mutated)
        save(ROOT/'audit-receipt.json', dict(valid=True, report_mutation_rejected=rejected,
            certificate_sha256=report['certificate_sha256'], report_sha256=digest(REPORT)))
        print('audit', rejected, report['certificate_sha256'])
        if not report['green'] or not rejected:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
