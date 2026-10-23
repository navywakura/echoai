"""Independent result accounting and development experiment custody.

Expected outputs stay here, outside solver calls. All confirmation runs are
descriptive synthetic tests; they do not grant release or S6 authority.
"""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from .budget import Budget
from .cases import FAMILIES, make_case, public_task, validate_witness


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def exact_success(result, expected):
    if result.get('status') not in ('SOLVED', 'solved'):
        return False
    predictions = result.get('predictions')
    if not isinstance(predictions, (tuple, list)) or len(predictions) != len(expected):
        return False
    for actual, truth in zip(predictions, expected):
        if not isinstance(actual, (tuple, list)) or len(actual) != len(truth):
            return False
        for row, reference in zip(actual, truth):
            if (not isinstance(row, (tuple, list)) or len(row) != len(reference) or
                    any(type(cell) is not int or cell < 0 or cell > 9 for cell in row) or
                    list(row) != list(reference)):
                return False
    return True


def paired(control, treatment):
    if len(control) != len(treatment):
        raise ValueError('paired samples have different sizes')
    wins = sum(bool(b) and not a for a, b in zip(control, treatment))
    losses = sum(bool(a) and not b for a, b in zip(control, treatment))
    return {'cases': len(control), 'wins': wins, 'losses': losses, 'delta': wins - losses,
            'ties': len(control) - wins - losses,
            'accuracy_advantage_without_regression': wins > 0 and losses == 0}


def wilson(successes, total):
    if not total:
        return [0.0, 1.0]
    z, p = 1.959963984540054, successes / total
    denominator = 1 + z*z / total
    midpoint = (p + z*z / (2*total)) / denominator
    radius = z * math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return [max(0, midpoint-radius), min(1, midpoint+radius)]


def source_snapshot(root, folders, *, suffixes=('.py',)):
    root = Path(root).resolve()
    files = {}
    for folder in folders:
        base = root / folder
        if not base.exists():
            raise FileNotFoundError(base)
        paths = [base] if base.is_file() else sorted(base.rglob('*'))
        for path in paths:
            if path.is_file() and path.suffix in suffixes and '__pycache__' not in path.parts:
                files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'folders': list(folders), 'suffixes': list(suffixes), 'files': files,
            'sha256': digest(files)}


def check_sources(root, receipt):
    actual = source_snapshot(root, receipt['folders'], suffixes=tuple(receipt['suffixes']))
    paths = sorted(set(actual['files']) | set(receipt['files']))
    changed = [p for p in paths if actual['files'].get(p) != receipt['files'].get(p)]
    return {'unchanged': not changed, 'changed': changed, 'sha256': actual['sha256'],
            'files': len(actual['files'])}


def audit_grid_rows(rows):
    keys, counts = set(), Counter()
    for row in rows:
        key = row['condition'], row['id']
        if key in keys:
            raise ValueError('duplicate scored case')
        keys.add(key)
        actual = exact_success(row['result'], row['expected'])
        if type(row.get('success')) is not bool or actual != row['success']:
            raise ValueError('claimed success disagrees with independent exact comparison')
        counts[row['condition']] += actual
    return dict(counts)


def grid_benchmark(config, *, journal=None):
    from .concepts import Library
    from .solver import solve
    learned = Library()
    acquisition = []
    for fi, family in enumerate(config['families']):
        for index in range(config['acquisition_cases_per_family']):
            ledger = Budget(config['work_per_case'])
            case = make_case(config['acquisition_seed'] + fi*100 + index, family,
                             split='acquisition', budget=ledger)
            if not validate_witness(case, ledger):
                raise RuntimeError('invalid acquisition witness; instrument failure')
            result = solve(public_task(case), budget=ledger, library=learned,
                           learn=True, journal=journal)
            acquisition.append({'id': case['id'], 'family': family, 'result': result,
                                'work': ledger.snapshot()})
    state = learned.state()
    frozen_library_sha = digest(state)
    rows, generation_work = [], 0
    cases = []
    for fi, family in enumerate(config['families']):
        for index in range(config['confirmation_cases_per_family']):
            ledger = Budget(config['work_per_case'])
            case = make_case(config['confirmation_seed'] + fi*100 + index, family,
                             split='confirmation', budget=ledger)
            if not validate_witness(case, ledger):
                raise RuntimeError('invalid confirmation witness; instrument failure')
            generation_work += ledger.used
            cases.append(case)
    if set(c['id'] for c in cases) & set(c['id'] for c in acquisition):
        raise RuntimeError('acquisition/confirmation overlap')
    for condition in config['conditions']:
        for case in cases:
            ledger = Budget(config['work_per_case'])
            result = solve(public_task(case), budget=ledger,
                           library=learned if condition == 'new_memory' else None,
                           relational=condition != 'legacy_relations',
                           hierarchical=condition != 'no_hierarchy', learn=False, journal=journal)
            rows.append({'id': case['id'], 'family': case['family'], 'seed': case['seed'],
                         'condition': condition, 'task': public_task(case), 'expected': case['expected'],
                         'result': result, 'success': exact_success(result, case['expected']),
                         'work': ledger.snapshot()})
            if journal:
                journal.write(kind='independent_grid_result', case_id=case['id'], condition=condition,
                              success=rows[-1]['success'], work=ledger.used)
    if digest(learned.state()) != frozen_library_sha:
        raise RuntimeError('confirmation mutated learned state')
    audit_grid_rows(rows)
    acquisition_cost = sum(r['work']['used'] for r in acquisition)
    arms = {}
    for condition in config['conditions']:
        current = [r for r in rows if r['condition'] == condition]
        successes = sum(r['success'] for r in current)
        cost = sum(r['work']['used'] for r in current)
        training = acquisition_cost if condition == 'new_memory' else 0
        arms[condition] = {'successes': successes, 'cases': len(current),
                           'wilson95_descriptive': wilson(successes, len(current)),
                           'evaluation_work': cost, 'acquisition_work': training,
                           'total_work': cost + training,
                           'statuses': dict(Counter(r['result']['status'] for r in current)),
                           'families': {f: sum(r['success'] for r in current if r['family'] == f)
                                        for f in config['families']}}
    comparisons = {}
    for control, treatment in (('legacy_relations', 'new_empty'), ('no_hierarchy', 'new_empty'),
                               ('new_empty', 'new_memory')):
        a = [r['success'] for r in rows if r['condition'] == control]
        b = [r['success'] for r in rows if r['condition'] == treatment]
        comparison = paired(a, b)
        comparison['equal_accuracy_less_total_work'] = (
            a == b and arms[treatment]['total_work'] < arms[control]['total_work'])
        comparison['total_work_delta'] = arms[treatment]['total_work'] - arms[control]['total_work']
        comparisons[f'{treatment}_vs_{control}'] = comparison
    return {'scope': 'new layouts and colors within four synthetic families',
            'arms': arms, 'comparisons': comparisons, 'rows': rows,
            'acquisition': acquisition, 'frozen_library': state,
            'frozen_library_sha256': frozen_library_sha,
            'common_generator_work': generation_work,
            'official_arc_score': None, 's6_green': False}
