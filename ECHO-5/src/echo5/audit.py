"""Recalculate experiment evidence in a fresh process, without trusting flags."""

import hashlib
import json
from pathlib import Path
import zipfile

from .budget import Budget
from .cases import make_case, public_task
from .evaluation import audit_grid_rows, check_sources, digest, exact_success, paired
from .distribution import CORE_FILES
from .trace import verify_journal

ROOT = Path(__file__).resolve().parents[2]


def _ledger(receipt):
    counts = receipt['counts']
    if type(receipt['used']) is not int or type(receipt['limit']) is not int:
        raise ValueError('work and ceiling must be integers')
    if any(type(n) is not int or n < 0 for n in counts.values()):
        raise ValueError('invalid logical work counts')
    if sum(counts.values()) != receipt['used'] or not 0 <= receipt['used'] <= receipt['limit']:
        raise ValueError('work accounting mismatch')


def enforce_grid_contract(rows, config):
    expected = [(arm, family, config['confirmation_seed'] + fi*100 + index)
                for arm in config['conditions'] for fi, family in enumerate(config['families'])
                for index in range(config['confirmation_cases_per_family'])]
    actual = [(r['condition'], r['family'], r['seed']) for r in rows]
    if actual != expected or any(r['work']['limit'] != config['work_per_case'] for r in rows):
        raise ValueError('grid cases, controls or budgets differ from frozen contract')


def audit_bundle(folder, *, replay=False):
    folder = Path(folder).resolve()
    read = lambda name: json.loads((folder / name).read_text())
    manifest = read('manifest.json')
    for name, claimed in manifest.items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder) or hashlib.sha256(path.read_bytes()).hexdigest() != claimed:
            raise ValueError('artifact manifest mismatch: ' + name)
    expected_files = {'contract.json', 'sources.json', 'legacy-sources.json', 'host-sources.json', 'grid.json',
                      'curriculum.json', 'interaction.json', 'robotics.json', 'result.json', 'thought.jsonl',
                      'sources.zip'}
    if not expected_files.issubset(manifest):
        raise ValueError('incomplete experiment manifest')
    config, result = read('contract.json'), read('result.json')
    if result['contract_sha256'] != digest(config):
        raise ValueError('contract differs from result')
    original = check_sources(ROOT.parent, read('legacy-sources.json'))
    own = check_sources(ROOT, read('sources.json'))
    host_receipt = read('host-sources.json')
    if set(host_receipt['files']) != set(CORE_FILES):
        raise ValueError('This distribution requires the complete flattened core snapshot')
    host = check_sources(ROOT.parent, host_receipt)
    if not (original['unchanged'] and own['unchanged'] and host['unchanged']):
        raise ValueError('live sources differ from frozen experiment')
    with zipfile.ZipFile(folder / 'sources.zip') as archive:
        expected_names = set()
        for prefix, receipt in (('ECHO-5', read('sources.json')), ('echoai', read('legacy-sources.json')),
                                ('host', read('host-sources.json'))):
            for name, sha in receipt['files'].items():
                key = f'{prefix}/{name}'
                expected_names.add(key)
                if hashlib.sha256(archive.read(key)).hexdigest() != sha:
                    raise ValueError('archived source differs from frozen hash')
        if set(archive.namelist()) != expected_names or len(archive.namelist()) != len(expected_names):
            raise ValueError('source archive entries differ from manifest')
    trace = verify_journal(folder / 'thought.jsonl')
    if trace != result['journal']:
        raise ValueError('journal receipt mismatch')
    grid = read('grid.json')
    enforce_grid_contract(grid['rows'], config['grid'])
    if set(grid['arms']) != set(config['grid']['conditions']):
        raise ValueError('grid controls differ from frozen contract')
    if digest(grid['frozen_library']) != grid['frozen_library_sha256']:
        raise ValueError('learned-state digest mismatch')
    counts = audit_grid_rows(grid['rows'])
    for condition in config['grid']['conditions']:
        rows = [r for r in grid['rows'] if r['condition'] == condition]
        expected_n = len(config['grid']['families']) * config['grid']['confirmation_cases_per_family']
        if len(rows) != expected_n or counts.get(condition, 0) != grid['arms'][condition]['successes']:
            raise ValueError('grid denominator or aggregate mismatch')
        for row in rows:
            _ledger(row['work'])
            regenerated = make_case(row['seed'], row['family'], split='confirmation')
            if (row['id'] != regenerated['id'] or row['expected'] != regenerated['expected'] or
                    row['task'] != public_task(regenerated)):
                raise ValueError('grid task or oracle differs from independent regeneration')
        if sum(r['work']['used'] for r in rows) != grid['arms'][condition]['evaluation_work']:
            raise ValueError('grid evaluation cost mismatch')
    for row in grid['acquisition']:
        _ledger(row['work'])
        if row['work']['limit'] != config['grid']['work_per_case']:
            raise ValueError('acquisition work ceiling differs from contract')
    acquisition_cost = sum(r['work']['used'] for r in grid['acquisition'])
    for name, arm in grid['arms'].items():
        expected_acquisition = acquisition_cost if name == 'new_memory' else 0
        if (arm['acquisition_work'] != expected_acquisition or
                arm['total_work'] != arm['evaluation_work'] + expected_acquisition):
            raise ValueError('grid total cost differs from independent sum')
    if result['grid'] != grid['arms'] or result['grid_comparisons'] != grid['comparisons']:
        raise ValueError('grid summary disagrees with raw evidence')
    for control, treatment in (('legacy_relations', 'new_empty'), ('no_hierarchy', 'new_empty'),
                               ('new_empty', 'new_memory')):
        a = [r['success'] for r in grid['rows'] if r['condition'] == control]
        b = [r['success'] for r in grid['rows'] if r['condition'] == treatment]
        comparison = paired(a, b)
        comparison['equal_accuracy_less_total_work'] = (
            a == b and grid['arms'][treatment]['total_work'] < grid['arms'][control]['total_work'])
        comparison['total_work_delta'] = grid['arms'][treatment]['total_work'] - grid['arms'][control]['total_work']
        if comparison != grid['comparisons'][f'{treatment}_vs_{control}']:
            raise ValueError('grid comparison differs from independently recomputed pairs')
    curriculum = read('curriculum.json')
    if set(curriculum['runs']) != set(config['curriculum']['conditions']):
        raise ValueError('curriculum controls differ from contract')
    counterexample_rows = 0
    for mode, runs in curriculum['runs'].items():
        good, cost = 0, 0
        if len(runs) != config['curriculum']['paired_runs']:
            raise ValueError('curriculum run denominator mismatch')
        for run_index, run in enumerate(runs):
            _ledger(run['acquisition'])
            if (run['seed'] != config['curriculum']['seed'] + 1000*run_index or
                    run['family'] != ('right_recolor', 'above_recolor')[run_index % 2] or
                    run['acquisition']['limit'] != config['curriculum']['work_per_arm']):
                raise ValueError('curriculum case or budget differs from contract')
            cost += run['acquisition']['used']
            if digest(run['hypotheses']) != run['hypotheses_sha256']:
                raise ValueError('frozen hypotheses changed')
            if len(run['rows']) != config['curriculum']['confirmation_cases_per_run']:
                raise ValueError('curriculum confirmation denominator mismatch')
            for index, row in enumerate(run['rows']):
                _ledger(row['work'])
                if row['work']['limit'] != config['curriculum']['query_work_per_case']:
                    raise ValueError('curriculum query work ceiling differs from contract')
                regenerated = make_case(run['seed'] + 500 + index, run['family'], split='confirmation')
                if row['id'] != regenerated['id'] or row['expected'] != regenerated['expected']:
                    raise ValueError('curriculum oracle differs from independent regeneration')
                actual = exact_success(row['result'], row['expected'])
                if actual != row['success']:
                    raise ValueError('curriculum exact comparison mismatch')
                good += actual
                cost += row['work']['used']
                counterexample_rows += 1
        if good != curriculum['totals'][mode]['successes'] or cost != curriculum['totals'][mode]['total_work']:
            raise ValueError('curriculum aggregate or cost mismatch')
    for control in ('reference', 'random'):
        expected = paired([r['success'] for run in curriculum['runs'][control] for r in run['rows']],
                          [r['success'] for run in curriculum['runs']['adaptive'] for r in run['rows']])
        expected['total_work_delta'] = curriculum['totals']['adaptive']['total_work'] - curriculum['totals'][control]['total_work']
        if expected != curriculum['comparisons']['adaptive_vs_' + control]:
            raise ValueError('curriculum comparison differs from independently recomputed pairs')
    if result['curriculum'] != curriculum['totals'] or result['curriculum_comparisons'] != curriculum['comparisons']:
        raise ValueError('curriculum summary differs from raw evidence')
    robot = read('robotics.json')
    from .robotics import CONDITIONS as ROBOT_CONDITIONS
    if set(robot['controls']) != {'one_step', 'conventional'} or robot['seed'] != config['robotics']['seed']:
        raise ValueError('robotics controls or seed differ from contract')
    robot_rows = []
    for arm in [robot, *robot['controls'].values()]:
        rows = arm['cases']
        if len(rows) != config['robotics']['cases']:
            raise ValueError('robotics denominator mismatch')
        for index, row in enumerate(rows):
            if (row['seed'] != config['robotics']['seed'] + index or
                    row['condition'] != ROBOT_CONDITIONS[index % len(ROBOT_CONDITIONS)] or
                    row['budget_limit'] != config['robotics']['budget']):
                raise ValueError('robotics case or ceiling differs from contract')
            actual = (row['status'] == 'reached' and row['final_position'] == row['goal']
                      and row['station_observed'] is True and row['collisions'] == 0
                      and row['reserve_violations'] == 0)
            if actual != row['success']:
                raise ValueError('robotics success disagrees with independent arrival check')
            if sum(row['costs'].values()) != row['cost'] or row['cost'] > row['budget_limit']:
                raise ValueError('robotics work mismatch')
        if sum(r['success'] for r in rows) != arm['successes']:
            raise ValueError('robotics aggregate mismatch')
        robot_rows.extend(rows)
    for control in robot['controls'].values():
        expected = paired([r['success'] for r in control['cases']], [r['success'] for r in robot['cases']])
        if any(control[key] != expected[key] for key in ('wins', 'losses', 'ties')):
            raise ValueError('robotics pair counts mismatch')
    interaction = read('interaction.json')
    if (interaction['seed'] != config['interaction']['seed'] or
            set(interaction['aggregate']) != {'passive', 'active', 'no_planning'}):
        raise ValueError('interaction controls or seed differ from contract')
    if len(interaction['cases']) != config['interaction']['cases']:
        raise ValueError('interaction denominator mismatch')
    for mode, aggregate in interaction['aggregate'].items():
        correct, work, actions = 0, 0, 0
        for index, case in enumerate(interaction['cases']):
            if (case['case_id'] != f'interaction-{index:04d}' or
                    case['split'] != ('novel_layout', 'novel_goal', 'changed_dynamics')[index % 3] or
                    set(case['arms']) != {'passive', 'active', 'no_planning'}):
                raise ValueError('interaction case or arms differ from contract')
            row = case['arms'][mode]
            _ledger(row['work'])
            if row['work']['limit'] != config['interaction']['budget']:
                raise ValueError('interaction work ceiling differs from contract')
            if sum(row['costs'].values()) != row['work']['used']:
                raise ValueError('interaction phase accounting mismatch')
            final = row['audit'].get('final')
            actual = (row['audit']['verified'] is True and final is not None and
                      final['position'] == final['goal'])
            if actual != row['success']:
                raise ValueError('interaction arrival mismatch')
            if row['actions'] != len(row['transcript']) or row['actions'] > 64:
                raise ValueError('interaction action count mismatch')
            correct += actual
            actions += row['actions']
            work += row['work']['used']
        if (correct != aggregate['successes'] or work != aggregate['total_work'] or
                actions != aggregate['actions']):
            raise ValueError('interaction aggregate mismatch')
    for control, comparison in interaction['paired'].items():
        expected = paired([r['arms'][control]['success'] for r in interaction['cases']],
                          [r['arms']['active']['success'] for r in interaction['cases']])
        if any(comparison['success_' + key] != expected[key] for key in ('wins', 'losses', 'ties')):
            raise ValueError('interaction pair counts mismatch')
    # The interaction module supplies complete public transcripts; the replay
    # below verifies dynamics and outcomes again from the independent simulator.
    replays = []
    if replay:
        from .concepts import Library
        from .solver import solve
        from .robotics import run_benchmark as robotics_run
        from .interaction import run_benchmark as interaction_run
        from .adversarial import run_benchmark as curriculum_run
        library = Library.restore(grid['frozen_library'])
        # One case of each family in each arm, selected before reading results.
        selected = set()
        for row in grid['rows']:
            key = row['condition'], row['family']
            if key in selected:
                continue
            selected.add(key)
            fresh = solve(row['task'], budget=Budget(config['grid']['work_per_case']),
                          library=library if row['condition'] == 'new_memory' else None,
                          relational=row['condition'] != 'legacy_relations',
                          hierarchical=row['condition'] != 'no_hierarchy', learn=False)
            if digest(fresh) != digest(row['result']):
                raise ValueError('determinism failure in grid replay')
            replays.append({'domain': 'grid', 'id': row['id'], 'condition': row['condition']})
        fresh_robot = robotics_run(**config['robotics'])
        if digest(fresh_robot) != digest(robot):
            raise ValueError('robotics deterministic replay mismatch')
        fresh_interaction = interaction_run(**config['interaction'])
        if digest(fresh_interaction) != digest(interaction):
            raise ValueError('interaction deterministic replay mismatch')
        fresh_curriculum = curriculum_run(config['curriculum'])
        if digest(fresh_curriculum) != digest(curriculum):
            raise ValueError('curriculum deterministic replay mismatch')
        replays.extend([{'domain': 'robotics', 'cases': len(robot_rows)},
                        {'domain': 'interaction', 'paired_cases': config['interaction']['cases']},
                        {'domain': 'curriculum', 'rows': counterexample_rows}])
    return {'schema': 'echo5.integration-audit.v1', 'valid': bool(replay),
            'arithmetic_valid': True,
            'status': 'valid_with_replay' if replay else 'arithmetic_only_pending_replay',
            'manifest_files': len(manifest), 'legacy_files_unchanged': original['files'],
            'host_files_unchanged': host['files'],
            'journal_events': trace['events'], 'grid_rows': len(grid['rows']),
            'curriculum_rows': counterexample_rows, 'robotics_rows': len(robot_rows),
            'replay_performed': replay, 'replays': replays,
            'scope': 'integrity, arithmetic and selected deterministic replay; not a sealed capability exam',
            's6_green': False}
