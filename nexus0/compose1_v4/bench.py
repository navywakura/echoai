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
from echoai.nexus0.compose1_v3 import bench as parent
from .power import design_power
from echoai.nexus0.compose1_v3.functional import mission
from echoai.nexus0.compose1_v3.school import learn
from echoai.nexus0.compose1_v3.session import run
from echoai.nexus0.compose1_v3.evaluate import audit_session
from echoai.nexus0.compose1_v3.controls import software

ECHOAI = old.ECHOAI
HERE = Path(__file__).resolve().parent
ROOT = ECHOAI/'lab/compose1-v4'
PREVIOUS_ROOT = parent.ROOT
REPORT = ECHOAI/'lab/echo3_compose1_v4_report.json'
MODES = old.MODES
PROTOCOL = copy.deepcopy(parent.PROTOCOL)
PROTOCOL.update(version=4, functional_validation=list(range(202623101, 202623613)),
                functional_confirmation=list(range(202624101, 202624613)))


def inventory():
    paths = set(HERE.rglob('*.py'))
    paths.update(ECHOAI/p for p in parent.inventory())
    paths.update([ECHOAI/'tests/test_compose1_v4.py', ECHOAI/'docs/COMPOSE1-V4-DESIGN.md',
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


interval = parent.interval
sign_test = parent.sign_test
metrics = parent.metrics


def tree_hashes(root, *, exclude=()):
    return {str(p.relative_to(root)): file_hash(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.name not in exclude and '__pycache__' not in p.parts}


def freeze(development_label, controls_label):
    if (ROOT/'lock.json').exists():
        raise FileExistsError('lock is immutable')
    previous = parent.require_lock()
    if development_label != previous['development_label'] or controls_label != previous['controls_label']:
        raise ValueError('reuse only the frozen V3 development, not selected alternatives')
    devroot = PREVIOUS_ROOT/'sitl-development'/development_label
    controls_root = PREVIOUS_ROOT/'controls'/controls_label
    if tree_hashes(devroot) != previous['development_files'] or tree_hashes(controls_root) != previous['controls_files']:
        raise ValueError('V3 development/control evidence changed')
    if not json.loads((devroot/'summary.json').read_text())['development_green']:
        raise ValueError('V3 development failed')
    school = json.loads((PREVIOUS_ROOT/'physical-school.json').read_text())
    if school != learn(PREVIOUS_ROOT/school['source']):
        raise ValueError('unchanged physical school does not reconstruct')
    print('Reconstructing V3 red before new sampling.', flush=True)
    prior_audit = parent.audit_functional('functional_validation')
    if not prior_audit['evidence_valid'] or prior_audit['metrics']['functional_green']:
        raise ValueError('V3 premise did not reconstruct as valid red')
    observed = prior_audit['metrics']['horizon_contrast']['moves_sign_test']
    if [observed[k] for k in ('wins', 'losses', 'ties')] != [22, 10, 32]:
        raise ValueError('sample-size planning source differs from the declared observation')
    prior_result = seal(dict(lock_sha256=previous['sha256'], evidence_valid=True, compose1_green=False,
        completed_stages=['functional_validation'], confirmation_opened=(PREVIOUS_ROOT/'functional_confirmation').exists(),
        sitl_bank_opened=(PREVIOUS_ROOT/'sitl_validation').exists(),
        reason='preregistered_horizon_contrast_failed', audit=prior_audit))
    history = PREVIOUS_ROOT/'early-stop.json'
    if history.exists():
        if json.loads(history.read_text()) != prior_result:
            raise ValueError('historical result changed')
    else:
        old.save(history, prior_result)
    power = design_power()
    old.save(ROOT/'power.json', seal(power))
    old.save(ROOT/'physical-school.json', school)
    regression = subprocess.run([sys.executable, '-m', 'unittest', 'echoai.tests.test_compose1_v4',
        'echoai.tests.test_compose1_v3', 'echoai.tests.test_compose1', 'echoai.tests.test_fusion1', '-q'],
        capture_output=True, text=True)
    old.save(ROOT/'regression.json', dict(returncode=regression.returncode, output=regression.stdout+regression.stderr))
    if regression.returncode:
        raise RuntimeError('regression failure')
    cage = self_test(Runtime(available=True, lock=json.loads((ECHOAI/'lab/pattern1r-v4/lock.json').read_text())['cage']))
    if not cage['ok']:
        raise RuntimeError('consumer isolation failed')
    protected = dict(previous['parent_locks'], **{'lab/compose1-v3/lock.json': file_hash(PREVIOUS_ROOT/'lock.json')})
    histories = {str(p.relative_to(ECHOAI)): file_hash(p) for p in (
        ECHOAI/'lab/echo3_compose1_report.json', ECHOAI/'lab/compose1-v2/early-stop.json', history)}
    lock = seal(dict(protocol=PROTOCOL, inventory=inventory(), cage=cage, parent_locks=protected,
        implementation='compose1_v3', previous_lock_sha256=previous['sha256'], history_reports=histories,
        previous_validation_files=tree_hashes(PREVIOUS_ROOT/'functional_validation'),
        physical_school_sha256=file_hash(ROOT/'physical-school.json'),
        physical_school_inputs=tree_hashes(ROOT/school['source']),
        development_root=str(devroot.relative_to(ECHOAI)), development_files=previous['development_files'],
        controls_root=str(controls_root.relative_to(ECHOAI)), controls_files=previous['controls_files'],
        power_sha256=file_hash(ROOT/'power.json'), regression_sha256=file_hash(ROOT/'regression.json'),
        runtime=previous['runtime'], host_python=platform.python_version(), phase='COMPOSE-1',
        created_before_evaluation=True))
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
    if not saved_inventory_valid(lock['history_reports']):
        issues.append('historical_reds')
    if file_hash(ROOT/'power.json') != lock['power_sha256']:
        issues.append('power_design')
    if tree_hashes(PREVIOUS_ROOT/'functional_validation') != lock['previous_validation_files']:
        issues.append('previous_validation')
    if not saved_inventory_valid(lock['parent_locks']):
        issues.append('parent_locks')
    if tree_hashes(ECHOAI/lock['development_root']) != lock['development_files']:
        issues.append('development_files')
    if tree_hashes(ECHOAI/lock['controls_root']) != lock['controls_files']:
        issues.append('control_files')
    control_root = ECHOAI/lock['controls_root']
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
    parser.add_argument('--development', default='round-1')
    parser.add_argument('--controls', default='round-1')
    args = parser.parse_args()
    if args.command == 'finish':
        freeze(args.development, args.controls)
        for stage in ('functional_validation', 'functional_confirmation', 'sitl_validation', 'sitl_confirmation'):
            ok = functional_stage(stage) if stage.startswith('functional_') else sitl_stage(stage)
            if not ok:
                print('Stage failed; preserved without rerun:', stage, flush=True)
                raise SystemExit(1)
        if not certificate(write=True):
            raise SystemExit(1)
        audit = subprocess.run([sys.executable, '-m', 'echoai.nexus0.compose1_v4.bench', 'audit'])
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
