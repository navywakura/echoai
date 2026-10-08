"""Frozen two-gate acceptance; evidence validity is separate from advantage."""
import argparse
import copy
import hashlib
import json
import math
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

from echoai.nexus0.compose1 import bench as old
from echoai.nexus0.fusion1.bench import seal
from echoai.nexus0.fusion1.replay import file_hash
from echoai.nexus0.sim3.sandbox import self_test
from echoai.nexus0.sim3.runtime import Runtime
from .development import ROOT
from .functional import mission
from .school import learn
from .session import run
from .evaluate import audit_session
from .controls import software

ECHOAI = old.ECHOAI
HERE = Path(__file__).resolve().parent
REPORT = ECHOAI/'lab/echo3_compose1_v2_report.json'
MODES = old.MODES
PROTOCOL = dict(version=2, functional_validation=list(range(202619101, 202619229)),
    functional_confirmation=list(range(202620101, 202620229)), modes=list(MODES),
    conditions=list(old.CONDITIONS), depth=4, budgets=[8, 32], max_movements=64,
    cell_mm=3000, body_radius_mm=400, clearance_mm=900, altitude_mm=2500,
    waypoint_tolerance_mm=400, arrival_truth_tolerance_mm=1000,
    max_horizontal_speed_mm_s=3000, physical_modes=['echo32', 'one_step', 'q', 'conventional'],
    sitl_validation=[202619301, 202619303, 202619304, 202619305],
    sitl_confirmation=[202619403, 202619404, 202619407, 202619408],
    sitl_conditions=['static', 'static', 'dynamic', 'low_energy'],
    sitl_min_reached=5, sitl_reachable_missions=6, confirmation_transfer3=False,
    bootstrap_samples=10000, bootstrap_seed=20261999,
    contrast_interval_percent=97.5, sign_test_max_p=.025)


def inventory():
    paths = set(HERE.rglob('*.py'))
    paths.update(ECHOAI/p for p in old.inventory())
    paths.update([ECHOAI/'tests/test_compose1_v2.py', ECHOAI/'docs/COMPOSE1-V2-DESIGN.md',
                  ECHOAI/'nexus0/pattern1r_v4/assets/flightrunner_survey.py'])
    # Include the loaded local dependency graph, including configuration helpers.
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            p = Path(name).resolve()
            if p.suffix == '.py' and p.is_relative_to(ECHOAI.parent) and not p.is_relative_to(ECHOAI/'lab'):
                paths.add(p)
    return {str(p.relative_to(ECHOAI) if p.is_relative_to(ECHOAI) else Path('..')/p.relative_to(ECHOAI.parent)):
            file_hash(p) for p in sorted(paths) if p.is_file()}


def saved_inventory_valid(expected):
    return all((ECHOAI/p).is_file() and file_hash(ECHOAI/p) == sha for p, sha in expected.items())


def interval(values):
    if not values:
        return [0, 0]
    rng = random.Random(PROTOCOL['bootstrap_seed'])
    means = sorted(sum(rng.choices(values, k=len(values)))/len(values)
                   for _ in range(PROTOCOL['bootstrap_samples']))
    return [means[len(means)*125//10000], means[len(means)*9875//10000]]


def sign_test(values):
    wins = sum(v > 0 for v in values)
    losses = sum(v < 0 for v in values)
    n = wins+losses
    p = sum(math.comb(n, k) for k in range(wins, n+1))/2**n if n else 1
    return dict(wins=wins, losses=losses, ties=len(values)-n, one_sided_p=p)


def metrics(rows):
    out = old.metrics(rows)
    full = [r for r in rows if r['mode'] == 'echo32' and r['oracle_static_feasible']]
    rates, costs = [], []
    for row in full:
        control = next(r for r in rows if r['seed'] == row['seed'] and r['mode'] == 'one_step')
        rates.append(int(row['reached'])-int(control['reached']))
        if row['reached'] and control['reached']:
            costs.append(control['steps']-row['steps'])
    rate_ci, cost_ci = interval(rates), interval(costs)
    rate_sign, cost_sign = sign_test(rates), sign_test(costs)
    rate_gain = rate_ci[0] > 0 and rate_sign['one_sided_p'] < .025
    cost_gain = cost_ci[0] > 0 and sum(rates) >= 0 and cost_sign['one_sided_p'] < .025
    out['horizon_contrast'] = dict(reachable_pairs=len(rates), paired_success_gain=sum(rates),
        success_mean_interval_975=rate_ci, success_sign_test=rate_sign,
        jointly_reached_pairs=len(costs), moves_saved=sum(costs),
        moves_saved_mean_interval_975=cost_ci, moves_sign_test=cost_sign,
        causal_advantage=rate_gain or cost_gain)
    out['functional_green'] &= rate_gain or cost_gain
    return out


def tree_hashes(root, *, exclude=()):
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.name not in exclude and '__pycache__' not in p.parts}


def freeze(development_label, controls_label):
    if (ROOT/'lock.json').exists():
        raise FileExistsError('lock is immutable')
    devroot = ROOT/'sitl-development'/development_label
    development = json.loads((devroot/'summary.json').read_text())
    if not development['development_green']:
        raise ValueError('SITL development did not pass')
    for record in development['records']:
        replay = audit_session(devroot/f"{record['seed']}-{record['mode']}")
        if not replay['evidence_valid'] or not replay['execution_green']:
            raise ValueError('development does not pass current physical auditor')
    controls_root = ROOT/'controls'/controls_label
    controls = json.loads((controls_root/'report.json').read_text())
    if not controls['controls_green']:
        raise ValueError('negative controls failed')
    school = json.loads((ROOT/'physical-school.json').read_text())
    if school != learn(ROOT/school['source']):
        raise ValueError('physical learning does not reconstruct')
    regression = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_compose1_v2',
        'echoai.tests.test_compose1', 'echoai.tests.test_fusion1', '-q'], capture_output=True, text=True)
    old.save(ROOT/'regression.json', dict(returncode=regression.returncode,
                                         output=regression.stdout+regression.stderr))
    if regression.returncode:
        raise RuntimeError('regression failure')
    cage = self_test(Runtime(available=True, lock=json.loads((ECHOAI/'lab/pattern1r-v4/lock.json').read_text())['cage']))
    if not cage['ok']:
        raise RuntimeError('consumer isolation failed')
    protected = {f'lab/{name}/lock.json': file_hash(ECHOAI/f'lab/{name}/lock.json') for name in ('compose1', 'fusion1')}
    runtime = json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container']
    lock = seal(dict(protocol=PROTOCOL, inventory=inventory(), cage=cage, parent_locks=protected,
        physical_school_sha256=file_hash(ROOT/'physical-school.json'),
        physical_school_inputs=tree_hashes(ROOT/school['source']),
        development_label=development_label, development_files=tree_hashes(devroot),
        controls_label=controls_label, controls_files=tree_hashes(controls_root),
        regression_sha256=file_hash(ROOT/'regression.json'), runtime=runtime,
        host_python=platform.python_version(), phase='COMPOSE-1', created_before_evaluation=True))
    old.save(ROOT/'lock.json', lock)
    print(json.dumps(dict(lock_sha256=lock['sha256']), sort_keys=True), flush=True)


def require_lock():
    lock = json.loads((ROOT/'lock.json').read_text())
    if lock != seal(lock) or lock['protocol'] != PROTOCOL or not saved_inventory_valid(lock['inventory']):
        raise ValueError('protocol/source lock changed')
    return lock


def functional_stage(stage):
    lock = require_lock()
    root = ROOT/stage
    root.mkdir(exist_ok=False)
    school = json.loads((ROOT/'physical-school.json').read_text())
    rows = []
    for i, seed in enumerate(PROTOCOL[stage]):
        condition = old.CONDITIONS[i % 4]
        for mode in MODES:
            label = f'{seed}-{mode}'
            row = mission(school['model'], seed, condition, mode, isolated=True,
                          trace_path=root/(label+'.jsonl'))
            old.save(root/(label+'.json'), seal(row))
            rows.append(row)
        print(stage, seed, condition, 'complete', rows[1-len(MODES)]['reached'], flush=True)
    result = seal(dict(metrics=metrics(rows), missions=len(rows), files=tree_hashes(root),
                       lock_sha256=lock['sha256']))
    old.save(root/'report.json', result)
    print(json.dumps(result['metrics']['horizon_contrast'], sort_keys=True), flush=True)
    return result['metrics']['functional_green']


def sitl_stage(stage):
    lock = require_lock()
    root = ROOT/stage
    root.mkdir(exist_ok=False)
    school = json.loads((ROOT/'physical-school.json').read_text())
    records = []
    for seed, condition in zip(PROTOCOL[stage], PROTOCOL['sitl_conditions']):
        for mode in PROTOCOL['physical_modes']:
            if not saved_inventory_valid(lock['inventory']):
                raise ValueError('code changed during bank')
            case = root/f'{seed}-{mode}'
            run(case, seed, mode, condition=condition, snapshot=school['model'])
            try:
                audit = audit_session(case)
            except Exception as exc:
                audit = dict(evidence_valid=False, findings=[repr(exc)])
            old.save(case/'audit.json', seal(audit))
            records.append(dict(seed=seed, condition=condition, mode=mode, audit=audit))
            print(stage, case.name, json.dumps(audit, sort_keys=True), flush=True)
    result = seal(dict(records=records, missions=len(records), files=tree_hashes(root),
                       lock_sha256=lock['sha256']))
    old.save(root/'report.json', result)
    return all(r['audit']['evidence_valid'] for r in records)


def audit_functional(stage):
    root = ROOT/stage
    result = json.loads((root/'report.json').read_text())
    school = json.loads((ROOT/'physical-school.json').read_text())
    issues, rows = [], []
    if result['lock_sha256'] != require_lock()['sha256']:
        issues.append('stage_lock')
    if result != seal(result) or result['files'] != tree_hashes(root, exclude=('report.json',)):
        issues.append('stage_files')
    for i, seed in enumerate(PROTOCOL[stage]):
        for mode in MODES:
            label = f'{seed}-{mode}'
            saved = json.loads((root/(label+'.json')).read_text())
            replay = mission(school['model'], seed, old.CONDITIONS[i % 4], mode)
            if saved != seal(saved) or old.compare_record(saved, replay):
                issues.append(label+'/replay')
            expected = []
            for step in replay['records']:
                expected.append(dict(kind='before_action', observation=step['observation'], prediction=step['prediction']))
                if step['consequence'] is not None:
                    expected.append(dict(kind='after_action', consequence=step['consequence']))
            stream = [json.loads(line) for line in (root/(label+'.jsonl')).read_text().splitlines()]
            if stream != expected:
                issues.append(label+'/publication_order')
            rows.append(replay)
    computed = metrics(rows)
    if result['metrics'] != computed or result['missions'] != len(rows):
        issues.append('metrics/denominator')
    return dict(evidence_valid=not issues, findings=issues, metrics=computed, missions=len(rows))


def certificate(write=False):
    lock = require_lock()
    issues, stages = [], {}
    if not saved_inventory_valid(lock['parent_locks']):
        issues.append('parent_locks')
    if tree_hashes(ROOT/'sitl-development'/lock['development_label']) != lock['development_files']:
        issues.append('development_files')
    if tree_hashes(ROOT/'controls'/lock['controls_label']) != lock['controls_files']:
        issues.append('control_files')
    control_root = ROOT/'controls'/lock['controls_label']
    controls = json.loads((control_root/'report.json').read_text())
    if not all(software().values()):
        issues.append('software_controls')
    for name, expected in controls['mutations'].items():
        actual = audit_session(control_root/name)
        if actual != expected or (actual['evidence_valid'] and actual['execution_green']):
            issues.append('mutation/'+name)
    if file_hash(ROOT/'regression.json') != lock['regression_sha256']:
        issues.append('regressions')
    if file_hash(ROOT/'physical-school.json') != lock['physical_school_sha256']:
        issues.append('physical_model')
    school = json.loads((ROOT/'physical-school.json').read_text())
    if tree_hashes(ROOT/school['source']) != lock['physical_school_inputs']:
        issues.append('physical_training_inputs')
    for stage in ('functional_validation', 'functional_confirmation'):
        stages[stage] = audit_functional(stage)
        if not stages[stage]['evidence_valid']:
            issues.append(stage)
    physical = []
    for stage in ('sitl_validation', 'sitl_confirmation'):
        root = ROOT/stage
        report = json.loads((root/'report.json').read_text())
        if report['lock_sha256'] != lock['sha256']:
            issues.append(stage+'/lock')
        if report != seal(report) or report['files'] != tree_hashes(root, exclude=('report.json',)):
            issues.append(stage+'/files')
        recomputed = []
        for seed, condition in zip(PROTOCOL[stage], PROTOCOL['sitl_conditions']):
            for mode in PROTOCOL['physical_modes']:
                case = root/f'{seed}-{mode}'
                cfg = json.loads((case/'configuration.json').read_text())
                if any(cfg[key] != value for key, value in dict(seed=seed, condition=condition, mode=mode,
                    image_id=lock['runtime']['image_id'], px4_binary_sha256=lock['runtime']['px4_binary_sha256']).items()):
                    issues.append(stage+'/'+case.name+'/configuration')
                if json.loads((case/'training.json').read_text()) != school['model']:
                    issues.append(stage+'/'+case.name+'/model')
                audit = audit_session(case)
                recomputed.append(dict(seed=seed, condition=condition, mode=mode, audit=audit))
        if recomputed != report['records'] or len(recomputed) != report['missions']:
            issues.append(stage+'/replay')
        physical += recomputed
    complete = [r for r in physical if r['mode'] == 'echo32']
    evidence_valid = all(r['audit']['evidence_valid'] for r in physical)
    safe = all(r['audit']['execution_green'] for r in physical)
    reached = sum(r['audit']['reached'] for r in complete)
    q_reached = sum(r['audit']['reached'] for r in physical if r['mode'] == 'q')
    sitl_green = safe and len(complete) == 8 and reached >= PROTOCOL['sitl_min_reached'] and reached > q_reached
    functional_green = all(stages[s]['metrics']['functional_green'] for s in stages)
    valid = not issues and evidence_valid and saved_inventory_valid(lock['inventory'])
    result = seal(dict(evidence_valid=valid, findings=issues, lock_sha256=lock['sha256'],
        functional_green=functional_green, sitl_green=sitl_green,
        compose1_green=valid and functional_green and sitl_green,
        functional=stages, physical=physical, physical_reached=reached,
        scope='bounded composition and Gazebo/PX4 execution; extruded rooms, local PC, no hardware'))
    if write:
        old.save(REPORT, result)
    elif REPORT.exists() and result != json.loads(REPORT.read_text()):
        raise ValueError('certificate does not reconstruct')
    print(json.dumps({k: result[k] for k in ('evidence_valid', 'findings', 'functional_green', 'sitl_green', 'compose1_green')}, sort_keys=True))
    return result['compose1_green']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('freeze', 'functional_validation', 'functional_confirmation',
        'sitl_validation', 'sitl_confirmation', 'certificate', 'audit', 'finish'))
    parser.add_argument('--development', default='round-2')
    parser.add_argument('--controls', default='round-3')
    parser.add_argument('--wait-development', action='store_true')
    args = parser.parse_args()
    if args.command == 'finish':
        if args.wait_development:
            deadline = time.monotonic()+3600
            path = ROOT/'sitl-development'/args.development/'summary.json'
            print('Waiting for complete development; evaluation remains unopened.', flush=True)
            while not path.exists():
                if time.monotonic() > deadline:
                    raise TimeoutError('development not completed within one hour')
                time.sleep(10)
        freeze(args.development, args.controls)
        for stage in ('functional_validation', 'functional_confirmation', 'sitl_validation', 'sitl_confirmation'):
            ok = functional_stage(stage) if stage.startswith('functional_') else sitl_stage(stage)
            if not ok:
                print('Stage failed; preserved without rerun:', stage, flush=True)
                raise SystemExit(1)
        if not certificate(write=True):
            raise SystemExit(1)
        audit = subprocess.run([sys.executable, '-m', 'echoai.nexus0.compose1_v2.bench', 'audit'])
        raise SystemExit(audit.returncode)
    if args.command == 'freeze':
        freeze(args.development, args.controls)
        return
    if args.command.startswith('functional_'):
        ok = functional_stage(args.command)
    elif args.command.startswith('sitl_'):
        ok = sitl_stage(args.command)
    else:
        ok = certificate(write=args.command == 'certificate')
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    main()
