"""A -> freeze -> B -> C. Every scheduled fault flight is mandatory."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.px41.bench import seal
from echoai.nexus0.px41.evaluate import digest
from echoai.nexus0.power1.bench import wilson
from .session import ROOT, CONDITIONS, run
from .functional import bank, CONDITIONS as FUNCTIONAL
from .evaluate import audit
from .controls import mutants, corruptions

REPORT = ECHOAI/'lab/echo3_safe1_report.json'
PROTOCOL = dict(version=1, development=list(range(20263401, 20263409)),
                validation=list(range(20263501, 20263533)), confirmation=list(range(20263601, 20263633)),
                flight_seeds=dict(development=20263401, validation=20263501, confirmation=20263602),
                conditions=list(CONDITIONS), functional=list(FUNCTIONAL))


def model():
    return json.loads((ECHOAI/'lab/power1/model.json').read_text())


def parents():
    lock = json.loads((ECHOAI/'lab/power1/lock.json').read_text())
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('POWER-1 dependency changed '+name)
    return dict(power1_lock=digest(ECHOAI/'lab/power1/lock.json'),
                power1_report=digest(ECHOAI/'lab/echo3_power1_report.json'), model=digest(ECHOAI/'lab/power1/model.json'))


def inventory():
    paths = list((ECHOAI/'nexus0').rglob('*.py'))
    paths += [ECHOAI/'tests/test_safe1.py', ECHOAI/'docs/SAFE1-DESIGN.md']
    return {str(p.relative_to(ECHOAI)): digest(p) for p in sorted(paths)}


def history():
    """Bind excluded pilot/development attempts explicitly; never erase a red."""
    paths = []
    for name in ('pilot', 'development-attempt-1'):
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}


def run_stage(stage):
    directory = ROOT/stage
    directory.mkdir(exist_ok=False)
    save(directory/'functional.json', bank(model(), PROTOCOL[stage]))
    # Isolated containers are sequential to avoid sensor/CPU timing interference.
    for condition in CONDITIONS:
        run(directory/condition, PROTOCOL['flight_seeds'][stage], condition)
    value = evaluate(stage)
    save(directory/'evaluation.json', value)
    print(stage, json.dumps(dict(green=value['green'], passed=value['passed'], total=value['total'],
                                 findings={c: r['findings'] for c, r in value['flights'].items()})), flush=True)
    return value


def evaluate(stage):
    directory = ROOT/stage
    functional = json.loads((directory/'functional.json').read_text())
    expected = bank(model(), PROTOCOL[stage])
    functional_ok = functional == expected and expected['passed'] == expected['total']
    flights = {}
    for condition in CONDITIONS:
        path = directory/condition
        result = audit(path)
        cfg = json.loads((path/'configuration.json').read_text())
        if cfg['condition'] != condition or cfg['seed'] != PROTOCOL['flight_seeds'][stage]:
            result['valid'] = False
            result['findings'].append('schedule_identity')
        # Bind every persisted session input and output, not just claimed runtime metrics.
        result['artifacts'] = {str(p.relative_to(path)): digest(p) for p in sorted(path.rglob('*')) if p.is_file()}
        flights[condition] = result
    passed = sum(r['valid'] for r in flights.values())
    return dict(stage=stage, green=functional_ok and passed == len(CONDITIONS),
                functional=dict(valid=functional_ok, total=expected['total'], passed=expected['passed'],
                    sha256=digest(directory/'functional.json'), unguarded_fault_forwards=expected['unguarded_fault_forwards'],
                    wilson95=wilson(expected['passed'], expected['total'])),
                flights=flights, passed=passed, total=len(CONDITIONS), wilson95=wilson(passed, len(CONDITIONS)))


def regression():
    result = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_safe1',
                            'echoai.tests.test_power1', 'echoai.tests.test_px41', 'echoai.tests.test_cause1',
                            'echoai.tests.test_nexus0.TestGate', 'echoai.tests.test_nexus0.TestBench'],
                            cwd=ECHOAI.parent, capture_output=True, text=True)
    return dict(ok=result.returncode == 0, output=result.stdout+result.stderr, returncode=result.returncode)


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    if seal({k: v for k, v in lock.items() if k != 'sha256'}) != lock['sha256'] or lock['protocol'] != PROTOCOL:
        raise ValueError('lock/protocol')
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('frozen source changed '+name)
    if lock['parents'] != parents() or lock['development'] != evaluate('development') or lock['history'] != history():
        raise ValueError('parent/development changed')
    return lock


def reconstruct():
    lock = require_lock()
    b, c = evaluate('validation'), evaluate('confirmation')
    value = dict(milestone='SAFE-1', scope='bounded fault containment in functional fixtures and PX4/Gazebo SITL',
                 green=b['green'] and c['green'], lock_sha256=lock['sha256'], validation=b, confirmation=c,
                 parents=parents(), controls=lock['controls'], history_sha256=seal(lock['history']),
                 hardware=False, physical_energy_validated=False)
    value['certificate_sha256'] = seal(value)
    return value


def verify_report(value):
    return value == reconstruct()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('development', 'freeze', 'accept', 'audit'))
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    if args.command == 'development':
        if (ROOT/'lock.json').exists():
            raise ValueError('already frozen')
        if not run_stage('development')['green']:
            raise SystemExit('development red')
    elif args.command == 'freeze':
        if (ROOT/'lock.json').exists():
            raise ValueError('already frozen')
        from echoai.nexus0.power1.bench import verify_report as verify_power
        if not verify_power(json.loads((ECHOAI/'lab/echo3_power1_report.json').read_text())):
            raise ValueError('POWER-1 parent audit')
        dev = evaluate('development')
        tests = regression()
        controls = dict(mutants=mutants(model()), corruptions=corruptions(ROOT/'development/nominal'))
        if not (dev['green'] and tests['ok'] and all(controls['mutants'].values()) and all(controls['corruptions'].values())):
            save(ROOT/'freeze-failure.json', dict(development=dev, tests=tests, controls=controls))
            raise ValueError('freeze prerequisites')
        lock = dict(protocol=PROTOCOL, inventory=inventory(), parents=parents(), development=dev, tests=tests,
                    controls=controls, history=history())
        lock['sha256'] = seal(lock)
        save(ROOT/'lock.json', lock)
        print('frozen', lock['sha256'], flush=True)
    elif args.command == 'accept':
        require_lock()
        if REPORT.exists():
            raise ValueError('report exists')
        if not run_stage('validation')['green']:
            raise SystemExit('B red; C remains sealed')
        run_stage('confirmation')
        report = reconstruct()
        save(REPORT, report)
        print('green', report['green'], report['certificate_sha256'], flush=True)
        if not report['green']:
            raise SystemExit(1)
    else:
        report = json.loads(REPORT.read_text())
        expected = reconstruct()
        if report != expected:
            raise SystemExit('report mismatch')
        controls = {}
        for name in ('numerator', 'trace_hash', 'lock_hash'):
            bad = copy.deepcopy(report)
            if name == 'numerator':
                bad['validation']['passed'] += 1
            elif name == 'trace_hash':
                bad['validation']['functional']['sha256'] = '0'*64
            else:
                bad['lock_sha256'] = '0'*64
            bad['certificate_sha256'] = seal({k: v for k, v in bad.items() if k != 'certificate_sha256'})
            controls[name] = bad != expected
        receipt = dict(valid=True, certificate_sha256=report['certificate_sha256'], report_sha256=digest(REPORT),
                       report_mutations_rejected=controls)
        path = ROOT/'audit-receipt.json'
        if path.exists():
            if json.loads(path.read_text()) != receipt:
                raise SystemExit('receipt mismatch')
        else:
            save(path, receipt)
        print(json.dumps(receipt, sort_keys=True))
        if not report['green'] or not all(controls.values()):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
