"""Frozen machine-source bank, caged consumer, reconstructive audit."""
import argparse
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.px41.bench import seal
from echoai.nexus0.px41.evaluate import digest
from echoai.nexus0.power1.bench import wilson
from .world import episode, audit_episode
from .transport import Caged
from .probes import communication
from .controls import mutants, corruptions
from .replay import replay

ROOT = ECHOAI/'lab/host1'
REPORT = ECHOAI/'lab/echo3_host1_report.json'
PROTOCOL = dict(version=1, development=list(range(20263901, 20263917)),
                validation=list(range(20264001, 20264065)), confirmation=list(range(20264101, 20264165)),
                policies=['consequence', 'button'], window=8, minimum=4, threshold_percent=75,
                phases=3, observations_per_session=384, decisions_per_session=24,
                alpha=.025, domain='integer kinematics and three existing nominal flight replays')


def parents():
    lock = json.loads((ECHOAI/'lab/safe1-v2/lock.json').read_text())
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('SAFE-1 dependency changed '+name)
    return dict(safe1_lock=digest(ECHOAI/'lab/safe1-v2/lock.json'),
                safe1_report=digest(ECHOAI/'lab/echo3_safe1_v2_report.json'))


def inventory():
    paths = list((ECHOAI/'nexus0').rglob('*.py'))
    paths += [ECHOAI.parent/'core/wsp.py', ECHOAI.parent/'core/qn.py', ECHOAI/'tests/test_host1.py',
              ECHOAI/'docs/HOST1-DESIGN.md']
    return {str(p.relative_to(ECHOAI) if p.is_relative_to(ECHOAI) else Path('..')/p.name): digest(p) for p in sorted(paths)}


def run_stage(stage):
    consumer = Caged()
    try:
        consumer.call(dict(op='init', policy='consequence'))
        directory = ROOT/stage
        directory.mkdir(exist_ok=False)
        save(directory/'communication.json', communication(consumer))
        with open(directory/'episodes.jsonl', 'x') as output:
            for index, seed in enumerate(PROTOCOL[stage]):
                for policy in PROTOCOL['policies']:
                    row = episode(seed, policy, consumer)
                    output.write(json.dumps(row, sort_keys=True)+'\n')
                    output.flush()
                if (index+1) % 16 == 0:
                    print(stage, index+1, '/', len(PROTOCOL[stage]), 'seeds', flush=True)
    finally:
        consumer.close()
    result = evaluate(stage)
    save(directory/'evaluation.json', result)
    print(stage, json.dumps(result), flush=True)
    return result


def evaluate(stage):
    directory = ROOT/stage
    records = [json.loads(line) for line in (directory/'episodes.jsonl').read_text().splitlines()]
    identities = [(r['seed'], r['policy']) for r in records]
    expected = [(s, p) for s in PROTOCOL[stage] for p in PROTOCOL['policies']]
    bad = [i for i, row in enumerate(records) if not audit_episode(row)]
    communication_actual = json.loads((directory/'communication.json').read_text())
    communication_valid = communication_actual == communication() and all(r['ok'] for r in communication_actual)
    stats = {}
    for policy in PROTOCOL['policies']:
        rows = [r for r in records if r['policy'] == policy]
        useful, total = sum(r['useful'] for r in rows), sum(r['total'] for r in rows)
        stats[policy] = dict(sessions=len(rows), observations=sum(len(r['trace']) for r in rows),
                            useful=useful, total=total, dropped=sum(r['dropped'] for r in rows),
                            recovered=sum(r['recovered'] for r in rows),
                            no_button_updates=all(r['no_button_updates'] for r in rows), wilson95=wilson(useful, total))
    wins = losses = 0
    for seed in PROTOCOL[stage]:
        pair = {r['policy']: r for r in records if r['seed'] == seed}
        wins += pair['consequence']['useful'] > pair['button']['useful']
        losses += pair['consequence']['useful'] < pair['button']['useful']
    n = wins+losses
    p = sum(math.comb(n, k) for k in range(wins, n+1))/2**n if n else 1.
    full, baseline = stats['consequence'], stats['button']
    green = (identities == expected and not bad and communication_valid and full['no_button_updates']
             and full['useful']*100 >= full['total']*95 and full['useful'] > baseline['useful'] and p < .025
             and full['dropped'] == full['recovered'] == len(PROTOCOL[stage])*16)
    return dict(stage=stage, green=green, identities_valid=identities == expected, bad_records=bad,
                communication_valid=communication_valid, communication_cases=len(communication_actual),
                episodes_sha256=digest(directory/'episodes.jsonl'),
                communication_sha256=digest(directory/'communication.json'), policies=stats,
                paired_by_seed=dict(wins=wins, losses=losses, sign_p=p))


def regression():
    result = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_host1',
                            'echoai.tests.test_safe1', 'echoai.tests.test_safe1_v2', 'echoai.tests.test_power1',
                            'echoai.tests.test_px41', 'echoai.tests.test_cause1',
                            'echoai.tests.test_nexus0.TestGate', 'echoai.tests.test_nexus0.TestBench'],
                            cwd=ECHOAI.parent, capture_output=True, text=True)
    return dict(ok=result.returncode == 0, output=result.stdout+result.stderr, returncode=result.returncode)


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    if seal({k: v for k, v in lock.items() if k != 'sha256'}) != lock['sha256'] or lock['protocol'] != PROTOCOL:
        raise ValueError('lock/protocol')
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('frozen source '+name)
    if lock['parents'] != parents() or lock['development'] != evaluate('development') or lock['physical_replay'] != replay():
        raise ValueError('parent/development/replay changed')
    return lock


def reconstruct():
    lock = require_lock()
    b, c = evaluate('validation'), evaluate('confirmation')
    value = dict(milestone='HOST-1', scope=PROTOCOL['domain'], lock_sha256=lock['sha256'],
                 green=b['green'] and c['green'], validation=b, confirmation=c, parents=parents(),
                 controls=lock['controls'], physical_replay=lock['physical_replay'],
                 new_flights=0, hardware=False, human_operator=False)
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
            raise SystemExit('A red')
    elif args.command == 'freeze':
        if (ROOT/'lock.json').exists():
            raise ValueError('already frozen')
        from echoai.nexus0.safe1_v2.bench import verify_report as verify_safe
        from echoai.nexus0.sim3.sandbox import self_test
        from echoai.nexus0.sim3.runtime import Runtime
        if not verify_safe(json.loads((ECHOAI/'lab/echo3_safe1_v2_report.json').read_text())):
            raise ValueError('SAFE-1 parent audit')
        cage_lock = json.loads((ECHOAI/'lab/pattern1r-v4/lock.json').read_text())['cage']
        cage = self_test(Runtime(available=True, lock=cage_lock))
        dev, tests, physical = evaluate('development'), regression(), replay()
        controls = dict(mutants=mutants(), corruptions=corruptions())
        if not (dev['green'] and tests['ok'] and cage['ok'] and physical['valid']
                and all(controls['mutants'].values()) and all(controls['corruptions'].values())):
            save(ROOT/'freeze-failure.json', dict(development=dev, tests=tests, cage=cage, controls=controls, replay=physical))
            raise ValueError('freeze prerequisites')
        lock = dict(protocol=PROTOCOL, inventory=inventory(), parents=parents(), development=dev,
                    tests=tests, cage=cage, controls=controls, physical_replay=physical)
        lock['sha256'] = seal(lock)
        save(ROOT/'lock.json', lock)
        print('frozen', lock['sha256'], flush=True)
    elif args.command == 'accept':
        require_lock()
        if REPORT.exists():
            raise ValueError('report exists')
        if not run_stage('validation')['green']:
            raise SystemExit('B red; C stays sealed')
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
                bad['validation']['policies']['consequence']['useful'] += 1
            elif name == 'trace_hash':
                bad['validation']['episodes_sha256'] = '0'*64
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
