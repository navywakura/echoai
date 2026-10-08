"""Prospective functional bank, isolated consumer, reconstructing certificate."""
import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from echoai.nexus0.compose1.bench import ECHOAI, save
from echoai.nexus0.px41.bench import seal
from echoai.nexus0.px41.evaluate import digest
from .core import Model
from .world import calibration, episode, audit_episode, CONDITIONS, POLICIES
from .transport import Caged
from .telemetry import replay_px4
from .controls import mutants, trace_mutations

ROOT = ECHOAI/'lab/power1'
REPORT = ECHOAI/'lab/echo3_power1_report.json'
PROTOCOL = dict(version=1, calibration=20263100, development=list(range(20263101, 20263117)),
    validation=list(range(20263201, 20263265)), confirmation=list(range(20263301, 20263365)),
    conditions=list(CONDITIONS), policies=list(POLICIES), reserve=40, alpha=.025)


def schedule(stage):
    return [(s, c, p) for s in PROTOCOL[stage] for c in CONDITIONS for p in POLICIES]


def model():
    receipts = json.loads((ROOT/'calibration.json').read_text())
    snapshot = json.loads((ROOT/'model.json').read_text())
    if receipts != calibration() or snapshot != Model.fit(receipts).snapshot():
        raise ValueError('calibration/model mismatch')
    return snapshot


def parents():
    lock = json.loads((ECHOAI/'lab/px41/lock.json').read_text())
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('PX4-1 frozen dependency changed '+name)
    return dict(px41_lock=digest(ECHOAI/'lab/px41/lock.json'),
                px41_report=digest(ECHOAI/'lab/echo3_px41_report.json'),
                dependencies=len(lock['inventory']))


def inventory():
    paths = list((ECHOAI/'nexus0').rglob('*.py'))+list(ECHOAI.parent.glob('navi10_*.py'))
    paths += [ECHOAI/'tests/test_power1.py', ECHOAI/'tests/test_px41.py',
              ECHOAI/'tests/test_cause1.py', ECHOAI/'tests/test_nexus0.py', ECHOAI/'docs/POWER1-DESIGN.md']
    return {str(p.relative_to(ECHOAI) if p.is_relative_to(ECHOAI) else Path('..')/p.name): digest(p) for p in sorted(paths)}


def run_stage(stage):
    directory = ROOT/stage
    directory.mkdir(exist_ok=False)
    snapshot = model()
    consumer = Caged()
    try:
        with open(directory/'episodes.jsonl', 'x') as output:
            for index, (seed, condition, policy) in enumerate(schedule(stage)):
                record = episode(seed, condition, policy, snapshot, consumer)
                output.write(json.dumps(record, sort_keys=True)+'\n')
                output.flush()
                if (index+1) % 120 == 0:
                    print(stage, index+1, '/', len(schedule(stage)), flush=True)
    finally:
        consumer.close()


def wilson(k, n):
    if not n:
        return [0, 1]
    z = 1.959963984540054
    centre = (k/n+z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0, centre-radius), min(1, centre+radius)]


def statistics(records, stage):
    expected = schedule(stage)
    identities = [(r['seed'], r['condition'], r['policy']) for r in records]
    valid = identities == expected
    grouped = {policy: [r for r in records if r['policy'] == policy] for policy in POLICIES}
    fields = ('successful', 'safe', 'dead', 'correct_initial', 'false_abort', 'correct_abort',
              'returned', 'mission_permission_violations', 'reserve_violations', 'consumed', 'moves')
    stats = {}
    for policy, rows in grouped.items():
        values = {key: sum(r['result'][key] for r in rows) for key in fields}
        latency = sorted(t for r in rows for t in r['latency_ns'])
        values.update(n=len(rows), feasible=sum(r['result']['initial_feasible'] for r in rows),
            reserve_min=min((r['result']['remaining'] for r in rows), default=None),
            successful_wilson95=wilson(values['successful'], len(rows)),
            per_condition={c: dict(n=sum(r['condition'] == c for r in rows),
                successful=sum(r['condition'] == c and r['result']['successful'] for r in rows),
                correct_initial=sum(r['condition'] == c and r['result']['correct_initial'] for r in rows)) for c in CONDITIONS},
            decision_latency_ns={str(q): latency[min(len(latency)-1, math.ceil(q*len(latency))-1)]
                                 for q in (.5, .95, .99)} if latency else {})
        stats[policy] = values
    wins = losses = 0
    for seed in PROTOCOL[stage]:
        a = sum(r['result']['successful'] for r in grouped['cost'] if r['seed'] == seed)
        b = sum(r['result']['successful'] for r in grouped['fixed'] if r['seed'] == seed)
        wins += a > b
        losses += b > a
    n = wins+losses
    p = sum(math.comb(n, k) for k in range(wins, n+1))/2**n if n else 1.
    full, oracle = stats['cost'], stats['oracle']
    expected_n = len(PROTOCOL[stage])*len(CONDITIONS)
    green = (valid and full['n'] == full['safe'] == expected_n and full['dead'] == 0
             and full['mission_permission_violations'] == full['reserve_violations'] == 0
             and full['correct_initial']*100 >= expected_n*95
             and full['successful']*100 >= oracle['successful']*95 and p < .025)
    return dict(green=green, identities_valid=valid, policies=stats,
                paired_by_seed=dict(wins=wins, losses=losses, ties=len(PROTOCOL[stage])-n, sign_p=p))


def evaluate(stage):
    path = ROOT/stage/'episodes.jsonl'
    records = [json.loads(line) for line in path.read_text().splitlines()]
    snapshot = model()
    bad = []
    for index, record in enumerate(records):
        if not audit_episode(record, snapshot):
            bad.append(index)
        if record['isolated'] is not (record['policy'] != 'oracle'):
            bad.append(index)
        if (len(record['latency_ns']) != len(record['trace'])
                or any(type(v) is not int or v < 0 for v in record['latency_ns'])):
            bad.append(index)
    values = statistics(records, stage)
    return dict(stage=stage, trace_sha256=digest(path), audit_valid=not bad,
                bad_records=sorted(set(bad)), metrics=values, green=not bad and values['green'])


def regression():
    args = [sys.executable, '-m', 'unittest', 'echoai.tests.test_power1', 'echoai.tests.test_px41',
            'echoai.tests.test_cause1', 'echoai.tests.test_nexus0.TestGate', 'echoai.tests.test_nexus0.TestBench']
    result = subprocess.run(args, cwd=ECHOAI.parent, capture_output=True, text=True)
    return dict(ok=result.returncode == 0, output=result.stdout+result.stderr, returncode=result.returncode)


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    plain = {k: v for k, v in lock.items() if k != 'sha256'}
    if seal(plain) != lock['sha256'] or lock['protocol'] != PROTOCOL:
        raise ValueError('lock hash/protocol')
    for name, sha in lock['inventory'].items():
        if digest(ECHOAI/name) != sha:
            raise ValueError('frozen source changed '+name)
    if lock['model'] != model() or lock['parents'] != parents() or lock['development'] != evaluate('development'):
        raise ValueError('frozen model, parents or development changed')
    if lock['telemetry_replay'] != replay_px4():
        raise ValueError('parent battery replay changed')
    return lock


def reconstruct():
    lock = require_lock()
    b, c = evaluate('validation'), evaluate('confirmation')
    value = dict(milestone='POWER-1', scope='functional energy model, sim_u; no physical energy certification',
                 lock_sha256=lock['sha256'], validation=b, confirmation=c, green=b['green'] and c['green'],
                 controls=lock['controls'], telemetry_replay=lock['telemetry_replay'], parents=parents(),
                 physical_energy_validated=False, hardware=False)
    value['certificate_sha256'] = seal(value)
    return value


def verify_report(value):
    return value == reconstruct()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['development', 'freeze', 'accept', 'audit'])
    args = parser.parse_args()
    if args.command == 'development':
        ROOT.mkdir(parents=True, exist_ok=True)
        if (ROOT/'lock.json').exists():
            raise RuntimeError('already frozen')
        if not (ROOT/'calibration.json').exists():
            save(ROOT/'calibration.json', calibration())
            save(ROOT/'model.json', Model.fit(calibration()).snapshot())
        run_stage('development')
        result = evaluate('development')
        save(ROOT/'development-report.json', result)
        print(json.dumps(result['metrics'], sort_keys=True), flush=True)
        if not result['green']:
            raise SystemExit(1)
    elif args.command == 'freeze':
        if (ROOT/'lock.json').exists():
            raise RuntimeError('lock exists')
        from echoai.nexus0.sim3.sandbox import self_test
        from echoai.nexus0.sim3.runtime import Runtime
        from echoai.nexus0.px41.bench import verify_report as verify_px4
        parent = json.loads((ECHOAI/'lab/echo3_px41_report.json').read_text())
        if not verify_px4(parent):
            raise ValueError('PX4 parent audit')
        cage_lock = json.loads((ECHOAI/'lab/pattern1r-v4/lock.json').read_text())['cage']
        cage = self_test(Runtime(available=True, lock=cage_lock))
        dev = evaluate('development')
        tests = regression()
        sample = episode(20263101, 'comfortable', 'cost', model())
        controls = dict(mutants=mutants(), traces=trace_mutations(sample, model()))
        replay = replay_px4()
        if not (dev['green'] and tests['ok'] and cage['ok']
                and all(r['detected'] for r in controls['mutants'].values()) and all(controls['traces'].values())
                and replay['flights'] == 12 and replay['samples'] == replay['unknown'] > 0):
            save(ROOT/'freeze-failure.json', dict(development=dev, tests=tests, controls=controls, cage=cage, replay=replay))
            raise ValueError('freeze prerequisites')
        lock = dict(protocol=PROTOCOL, inventory=inventory(), model=model(), parents=parents(),
                    development=dev, tests=tests, controls=controls, cage=cage, telemetry_replay=replay)
        lock['sha256'] = seal(lock)
        save(ROOT/'lock.json', lock)
        print('frozen', lock['sha256'])
    elif args.command == 'accept':
        require_lock()
        if REPORT.exists():
            raise RuntimeError('report exists')
        run_stage('validation')
        if not evaluate('validation')['green']:
            save(ROOT/'validation-red.json', evaluate('validation'))
            raise SystemExit('B red; C remains sealed')
        run_stage('confirmation')
        report = reconstruct()
        save(REPORT, report)
        print('green', report['green'], report['certificate_sha256'])
        if not report['green']:
            raise SystemExit(1)
    else:
        report = json.loads(REPORT.read_text())
        if not verify_report(report):
            raise SystemExit('report mismatch')
        controls = {}
        for name in ('numerator', 'trace_hash', 'model_hash'):
            bad = copy.deepcopy(report)
            if name == 'numerator':
                bad['validation']['metrics']['policies']['cost']['successful'] += 1
            elif name == 'trace_hash':
                bad['validation']['trace_sha256'] = '0'*64
            else:
                bad['lock_sha256'] = '0'*64
            bad['certificate_sha256'] = seal({k: v for k, v in bad.items() if k != 'certificate_sha256'})
            controls[name] = not verify_report(bad)
        receipt = dict(valid=True, certificate_sha256=report['certificate_sha256'],
                       report_sha256=digest(REPORT), report_mutations_rejected=controls)
        path = ROOT/'audit-receipt.json'
        if path.exists():
            if json.loads(path.read_text()) != receipt:
                raise SystemExit('existing receipt mismatch')
        else:
            save(path, receipt)
        print(json.dumps(receipt, sort_keys=True))
        if not report['green'] or not all(controls.values()):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
