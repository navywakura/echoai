"""Fresh reserved bank after a narrow auditor correction; runtime remains v1."""
import argparse
import copy
import json
import subprocess
import sys
from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.px41.bench import seal
from echoai.nexus0.px41.evaluate import digest
from echoai.nexus0.power1.bench import wilson
from echoai.nexus0.safe1 import bench as v1
from echoai.nexus0.safe1.session import CONDITIONS, run
from echoai.nexus0.safe1.functional import bank
from echoai.nexus0.safe1.controls import mutants, corruptions
from .evaluate import audit

ROOT = ECHOAI/'lab/safe1-v2'
REPORT = ECHOAI/'lab/echo3_safe1_v2_report.json'
PROTOCOL = dict(version=2, development_reference='lab/safe1/development',
                validation=list(range(20263701, 20263733)), confirmation=list(range(20263801, 20263833)),
                flight_seeds=dict(validation=20263701, confirmation=20263802), conditions=list(CONDITIONS),
                correction='normal rejected arming retries only; runtime and containment criteria unchanged')


def parents():
    lock = v1.require_lock()
    b = v1.evaluate('validation')
    if b['green'] or (v1.ROOT/'confirmation').exists() or v1.REPORT.exists():
        raise ValueError('v1 must remain B red / C sealed')
    if any(set(r['findings'])-{'forced_arm_or_disarm'} for r in b['flights'].values()):
        raise ValueError('v1 has a failure beyond the declared auditor defect')
    if json.loads((v1.ROOT/'validation/evaluation.json').read_text()) != b:
        raise ValueError('v1 B evidence changed')
    return dict(v1_lock=lock['sha256'], v1_B_sha256=seal(b), v1_B_red=True, v1_C_sealed=True,
                power=v1.parents())


def inventory():
    value = v1.inventory()
    for name in ('tests/test_safe1_v2.py', 'docs/SAFE1-V2-DESIGN.md'):
        value[name] = digest(ECHOAI/name)
    return value


def development():
    old = v1.evaluate('development')
    flights = {c: audit(v1.ROOT/'development'/c) for c in CONDITIONS}
    return dict(reference=PROTOCOL['development_reference'], original_sha256=seal(old), flights=flights,
                functional=old['functional'], green=old['green'] and all(r['valid'] for r in flights.values()))


def run_stage(stage):
    directory = ROOT/stage
    directory.mkdir(exist_ok=False)
    save(directory/'functional.json', bank(v1.model(), PROTOCOL[stage]))
    for condition in CONDITIONS:
        run(directory/condition, PROTOCOL['flight_seeds'][stage], condition)
    value = evaluate(stage)
    save(directory/'evaluation.json', value)
    print(stage, json.dumps(dict(green=value['green'], passed=value['passed'],
                findings={c: r['findings'] for c, r in value['flights'].items()})), flush=True)
    return value


def evaluate(stage):
    directory = ROOT/stage
    actual = json.loads((directory/'functional.json').read_text())
    expected = bank(v1.model(), PROTOCOL[stage])
    functional_ok = actual == expected and expected['passed'] == expected['total']
    flights = {}
    for condition in CONDITIONS:
        path = directory/condition
        result = audit(path)
        cfg = json.loads((path/'configuration.json').read_text())
        if cfg['condition'] != condition or cfg['seed'] != PROTOCOL['flight_seeds'][stage]:
            result['valid'] = False
            result['findings'].append('schedule_identity')
        result['artifacts'] = {str(p.relative_to(path)): digest(p) for p in sorted(path.rglob('*')) if p.is_file()}
        flights[condition] = result
    passed = sum(r['valid'] for r in flights.values())
    return dict(stage=stage, green=functional_ok and passed == len(CONDITIONS), flights=flights,
                functional=dict(valid=functional_ok, passed=expected['passed'], total=expected['total'],
                    sha256=digest(directory/'functional.json'), unguarded_fault_forwards=expected['unguarded_fault_forwards'],
                    wilson95=wilson(expected['passed'], expected['total'])),
                passed=passed, total=len(CONDITIONS), wilson95=wilson(passed, len(CONDITIONS)))


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    if seal({k: v for k, v in lock.items() if k != 'sha256'}) != lock['sha256'] or lock['protocol'] != PROTOCOL:
        raise ValueError('v2 lock/protocol')
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('v2 frozen source '+name)
    if lock['parents'] != parents() or lock['development'] != development():
        raise ValueError('v2 parent/development')
    return lock


def reconstruct():
    lock = require_lock()
    b, c = evaluate('validation'), evaluate('confirmation')
    value = dict(milestone='SAFE-1', version=2, scope='bounded functional faults and PX4/Gazebo SITL; normal arm retries audited',
                 green=b['green'] and c['green'], lock_sha256=lock['sha256'], validation=b, confirmation=c,
                 parents=parents(), controls=lock['controls'], hardware=False, physical_energy_validated=False)
    value['certificate_sha256'] = seal(value)
    return value


def verify_report(value):
    return value == reconstruct()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('freeze', 'accept', 'audit'))
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    if args.command == 'freeze':
        if (ROOT/'lock.json').exists():
            raise ValueError('already frozen')
        parent = parents()
        dev = development()
        regression = v1.regression()
        extra = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_safe1_v2'],
                               cwd=ECHOAI.parent, capture_output=True, text=True)
        tests = dict(ok=regression['ok'] and extra.returncode == 0, base=regression,
                     arming=extra.stdout+extra.stderr)
        controls = dict(mutants=mutants(v1.model()), non_arming_corruptions=corruptions(v1.ROOT/'development/nominal'))
        if not (dev['green'] and tests['ok'] and all(controls['mutants'].values()) and all(controls['non_arming_corruptions'].values())):
            raise ValueError('v2 freeze prerequisites')
        lock = dict(protocol=PROTOCOL, inventory=inventory(), parents=parent, development=dev, tests=tests, controls=controls)
        lock['sha256'] = seal(lock)
        save(ROOT/'lock.json', lock)
        print('frozen', lock['sha256'], flush=True)
    elif args.command == 'accept':
        require_lock()
        if REPORT.exists():
            raise ValueError('report exists')
        if not run_stage('validation')['green']:
            raise SystemExit('B v2 red; C v2 stays sealed')
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
