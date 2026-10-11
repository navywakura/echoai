"""Structural transfer instrument. Importing this module never runs a campaign.

Generators/oracles live here, outside the solver. Public actor inputs contain
only demonstrations and query inputs. Historical exact32 is not used here.
See docs/TRANSFER-CONTRACT.json for the preregistered domain and limits.

V2 is the coordinator's measurement amendment after development and before
confirmation. The fixed manual knowledge oracle remains a reported comparison;
closure requires accuracy/cost noninferiority, not superiority to that oracle.
All-in and semantic savings against empty/irrelevant remain required. The
explicit gate policy and metadata partition are frozen in the V2 contract.
Archived V1 results remain negative under V1 and require their archived auditor.
Search, acquisition, libraries, generators and evidence replay are unchanged.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import sys
import time

from .budget import Budget
from .concepts import Library, digest
from .programs import Program, execute, expand
from .solver import solve, validate_synthesis

SCHEMA = 'echo5.transfer.v2'
ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / 'docs' / 'TRANSFER-CONTRACT.json'
SUPPORTED_FAMILIES = ('outline_extract_scale', 'fill_extract_tile',
                      'pack_rotate_scale', 'inside_erase_crop')
CONTROL_FAMILIES = ('ambiguous_rotation', 'unsupported_color')
TRAINING_FAMILIES = ('outline', 'fill', 'pack', 'inside_erase',
                     'outline_extract', 'fill_extract')
CONDITIONS = ('learned', 'fixed', 'irrelevant', 'empty', 'empty_uncached',
              'empty_shallow', 'old_representation')


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding='utf-8'))


def default_config(phase='development'):
    """Return JSON config for run_benchmark; do not pass the whole contract."""
    contract = load_contract()
    if phase not in ('development', 'confirmation'):
        raise ValueError('development or confirmation phase required')
    return {**deepcopy(contract['defaults']), 'phase': phase,
            'seeds': list(contract['seeds'][phase]), 'families': list(contract['families']),
            'conditions': list(contract['conditions'])}


def normalize_config(config):
    if type(config) is not dict:
        raise ValueError('JSON config object required')
    phase = config.get('phase', 'development')
    defaults = default_config(phase)
    if set(config) - set(defaults):
        raise ValueError('unknown transfer config keys; use default_config(phase)')
    actual = {**defaults, **deepcopy(config)}
    if phase == 'confirmation' and actual != defaults:
        raise ValueError('confirmation settings are frozen by TRANSFER-CONTRACT.json')
    for key in ('work_per_case', 'training_work_per_case', 'preparation_work', 'generator_work_per_case'):
        if type(actual[key]) is not int or not 1 <= actual[key] <= 100_000_000:
            raise ValueError('invalid work ceiling: ' + key)
    for key, minimum, maximum in (('demonstrations', 2, 10), ('queries', 1, 10)):
        if type(actual[key]) is not int or not minimum <= actual[key] <= maximum:
            raise ValueError('invalid example count: ' + key)
    for key, domain in (('families', SUPPORTED_FAMILIES + CONTROL_FAMILIES), ('conditions', CONDITIONS)):
        values = actual[key]
        if (type(values) is not list or not values or any(type(v) is not str or v not in domain for v in values)
                or len(set(values)) != len(values)):
            raise ValueError('invalid ' + key)
    seeds = actual['seeds']
    if (type(seeds) is not list or not 1 <= len(seeds) <= 64
            or any(type(seed) is not int or not 0 <= seed < 2**31 for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ValueError('invalid or duplicate seeds')
    contract = load_contract()
    reserved = set(contract['training_seeds'])
    if phase == 'development':
        reserved.update(contract['seeds']['confirmation'])
    if set(seeds) & reserved:
        raise ValueError('development/acquisition/confirmation seed overlap')
    # Check actual derived seeds as well as the base seeds.
    derived = [seed + (SUPPORTED_FAMILIES + CONTROL_FAMILIES).index(family) * contract['seeds']['family_offset']
               for family in actual['families'] for seed in seeds]
    if len(set(derived)) != len(derived) or set(derived) & set(contract['training_seeds']):
        raise ValueError('derived case seed collision')
    if phase == 'development':
        confirmation = {seed + i * contract['seeds']['family_offset']
                        for i in range(len(SUPPORTED_FAMILIES + CONTROL_FAMILIES))
                        for seed in contract['seeds']['confirmation']}
        if set(derived) & confirmation:
            raise ValueError('derived development seed enters confirmation')
    validate_synthesis(actual['synthesis'])
    return actual


class _Random:
    def __init__(self, seed, budget):
        budget.consume('generator_initializations')
        self.rng, self.budget = random.Random(seed), budget

    def integer(self, lo, hi):
        self.budget.consume('generator_draws')
        return self.rng.randint(lo, hi)

    def sample(self, values, n):
        self.budget.consume('generator_draws', n)
        return self.rng.sample(values, n)


def _blank(h, w, budget):
    budget.consume('generator_render_cells', h*w)
    return [[0]*w for _ in range(h)]


def _draw(rows, cells, color, budget):
    budget.consume('generator_draw_cells', len(cells))
    for y, x in cells:
        if rows[y][x] != 0:
            raise RuntimeError('generator overlap')
        rows[y][x] = color


def _crop_oracle(rows, budget):
    budget.consume('generator_crop_cells', len(rows)*len(rows[0]))
    occupied = [(y, x) for y, row in enumerate(rows) for x, color in enumerate(row) if color]
    top, bottom = min(y for y, x in occupied), max(y for y, x in occupied)
    left, right = min(x for y, x in occupied), max(x for y, x in occupied)
    return [row[left:right+1] for row in rows[top:bottom+1]]


def _rotate_oracle(rows, budget):
    budget.consume('generator_rotate_cells', len(rows)*len(rows[0]))
    return [[rows[len(rows)-1-x][y] for x in range(len(rows))] for y in range(len(rows[0]))]


def _double_oracle(rows, budget):
    result = _blank(len(rows)*2, len(rows[0])*2, budget)
    for y, row in enumerate(rows):
        for x, color in enumerate(row):
            for yy in (2*y, 2*y+1):
                for xx in (2*x, 2*x+1):
                    result[yy][xx] = color
    return result


def _rel(effect, relation='all'):
    return {'op': 'relate', 'role': 'largest', 'relation': relation, 'effect': effect}


def witness_program(family):
    """Evaluator-only witness declarations, never included in public_task."""
    outline = {'op': 'object', 'role': 'largest', 'effect': 'outline'}
    fill = {'op': 'object', 'role': 'largest', 'effect': 'fill_box'}
    programs = {
        'outline': [outline], 'fill': [fill], 'pack': [{'op': 'pack', 'axis': 'row'}],
        'inside_erase': [_rel('erase', 'inside')],
        'outline_extract': [outline, _rel('extract')],
        'fill_extract': [fill, _rel('extract')],
        'outline_extract_scale': [outline, _rel('extract'), {'op': 'up2'}],
        'fill_extract_tile': [fill, _rel('extract'), {'op': 'tile1x2'}],
        'pack_rotate_scale': [{'op': 'pack', 'axis': 'row'}, {'op': 'rot90'}, {'op': 'up2'}],
        'inside_erase_crop': [_rel('erase', 'inside'), {'op': 'crop'}, {'op': 'fliplr'}],
    }
    return {'steps': deepcopy(programs[family])} if family in programs else None


def _morphology_example(rng, family, split, budget):
    novel = split == 'confirmation'
    height, width = (rng.integer(15, 18), rng.integer(16, 19)) if novel else (13, 15)
    colors = rng.sample([5, 6, 7, 8, 9] if novel else [1, 2, 3, 4], 3)
    top, left = rng.integer(2, 4), rng.integer(2, 4)
    h, w = rng.integer(3, 5), rng.integer(3, 5)
    shape = {(y, x) for y in range(h) for x in range(w)}
    if family.startswith('outline'):
        # A clipped corner changes boundary topology, not only color/layout.
        if rng.integer(0, 1):
            shape.remove((0, w-1))
        target = {(y, x) for y, x in shape if not all(p in shape for p in
                  ((y-1, x), (y+1, x), (y, x-1), (y, x+1)))}
    else:
        shape = {(y, x) for y, x in shape if x in (0, w-1) or y == h-1}
        target = {(y, x) for y in range(h) for x in range(w)}
    inp = _blank(height, width, budget)
    _draw(inp, {(top+y, left+x) for y, x in shape}, colors[0], budget)
    _draw(inp, {(1, width-3)}, colors[1], budget)
    _draw(inp, {(height-3, 1)}, colors[2], budget)
    if family in ('outline', 'fill'):
        budget.consume('generator_copy_cells', height*width)
        out = deepcopy(inp)
        for y in range(h):
            for x in range(w):
                out[top+y][left+x] = colors[0] if (y, x) in target else 0
    else:
        out = _blank(h, w, budget)
        _draw(out, target, colors[0], budget)
        if family == 'outline_extract_scale':
            out = _double_oracle(out, budget)
        elif family == 'fill_extract_tile':
            budget.consume('generator_tile_cells', 2*h*w)
            out = [row+row for row in out]
    return {'input': inp, 'output': out}


def _packing_example(rng, family, split, budget):
    height, width = (16, 18) if split == 'confirmation' else (13, 15)
    colors = rng.sample(list(range(1, 10)), 3)
    tall = rng.integer(3, 5)
    # Three distinct areas; asymmetric shapes make orientation observable.
    shapes = [{(y, 0) for y in range(tall)} | {(tall-1, 1)},
              {(0, 0), (0, 1), (1, 0)}, {(0, 0)}]
    positions = rng.sample([(2, 2), (2, width-5), (height-5, 3)], 3)
    inp = _blank(height, width, budget)
    for cells, (top, left), color in zip(shapes, positions, colors):
        _draw(inp, {(top+y, left+x) for y, x in cells}, color, budget)
    # Construction order already is descending area; no actor segmentation,
    # binding, packing or sorting implementation is used to build this oracle.
    out = _blank(tall, 7, budget)
    for cells, offset, color in zip(shapes, (0, 3, 6), colors):
        _draw(out, {(y, x+offset) for y, x in cells}, color, budget)
    if family == 'pack_rotate_scale':
        out = _double_oracle(_rotate_oracle(out, budget), budget)
    return {'input': inp, 'output': out}


def _containment_example(rng, family, split, budget):
    height, width = (17, 19) if split == 'confirmation' else (13, 15)
    h, w = rng.integer(5, 7), rng.integer(5, 7)
    top, left = rng.integer(2, 3), rng.integer(2, 3)
    colors = rng.sample(list(range(1, 10)), 3)
    ring = {(top+y, left+x) for y in range(h) for x in range(w)
            if y in (0, h-1) or x in (0, w-1)}
    inside = (top+h//2, left+w//2)
    inp = _blank(height, width, budget)
    _draw(inp, ring, colors[0], budget)
    _draw(inp, {inside}, colors[1], budget)
    _draw(inp, {(1, width-3)}, colors[2], budget)
    budget.consume('generator_copy_cells', height*width)
    out = deepcopy(inp)
    out[inside[0]][inside[1]] = 0
    if family == 'inside_erase_crop':
        out = _crop_oracle(out, budget)
        budget.consume('generator_reflect_cells', len(out)*len(out[0]))
        out = [row[::-1] for row in out]
    return {'input': inp, 'output': out}


def _control_example(rng, family, query, budget):
    if family == 'unsupported_color':
        inp = _blank(rng.integer(5, 9), rng.integer(5, 9), budget)
        y, x = rng.integer(1, len(inp)-3), rng.integer(1, len(inp[0])-3)
        _draw(inp, {(y, x), (y+1, x), (y+1, x+1)}, 9, budget)
        budget.consume('generator_relabel_cells', len(inp)*len(inp[0]))
        # No actor primitive introduces the absent color 8, at any depth.
        out = [[8 if cell == 9 else 0 for cell in row] for row in inp]
    elif not query:
        side = rng.integer(3, 7)
        color = rng.integer(1, 9)
        inp = _blank(side, side, budget)
        for i in range(side):
            inp[i][side//2] = inp[side//2][i] = color
        # Even-sized crosses are not invariant under quarter-turns.
        if side % 2 == 0:
            for i in range(side):
                inp[i][side//2-1] = inp[side//2-1][i] = color
        out = deepcopy(inp)
        budget.consume('generator_copy_cells', side*side)
    else:
        inp = _blank(4, 7, budget)
        colors = rng.sample(list(range(1, 10)), 3)
        _draw(inp, {(1, 1), (2, 1)}, colors[0], budget)
        _draw(inp, {(1, 4)}, colors[1], budget)
        _draw(inp, {(2, 5)}, colors[2], budget)
        out = _rotate_oracle(inp, budget)
    return {'input': inp, 'output': out}


def make_case(seed, family, *, split='development', budget=None, demonstrations=3, queries=2):
    """Independent, deterministic oracle with metadata kept outside the actor."""
    budget = Budget(1_000_000) if budget is None else budget
    if (type(seed) is not int or seed < 0 or family not in
            SUPPORTED_FAMILIES + CONTROL_FAMILIES + TRAINING_FAMILIES
            or split not in ('acquisition', 'development', 'confirmation')
            or type(demonstrations) is not int or not 2 <= demonstrations <= 10
            or type(queries) is not int or not 1 <= queries <= 10):
        raise ValueError('invalid generator contract')
    rng = _Random(seed, budget)
    examples = []
    for index in range(demonstrations + queries):
        if family.startswith(('outline', 'fill')):
            pair = _morphology_example(rng, family, split, budget)
        elif family.startswith('pack'):
            pair = _packing_example(rng, family, split, budget)
        elif family.startswith('inside'):
            pair = _containment_example(rng, family, split, budget)
        else:
            pair = _control_example(rng, family, index >= demonstrations, budget)
        examples.append(pair)
    task = {'train': examples[:demonstrations],
            'test': [{'input': row['input']} for row in examples[demonstrations:]]}
    case = {'id': f'transfer-v1:{split}:{family}:{seed}', 'seed': seed, 'family': family,
            'split': split, 'task': task,
            'expected': [row['output'] for row in examples[demonstrations:]],
            'witness': witness_program(family), 'supported': family not in CONTROL_FAMILIES}
    case['public_sha256'] = digest(task, budget)
    case['sha256'] = digest(case, budget)
    return case


def public_task(case, *, budget=None):
    if budget is not None:
        budget.consume('public_task_copy_cells', sum(sum(map(len, row[key]))
                       for row in case['task']['train'] for key in ('input', 'output'))
                       + sum(sum(map(len, row['input'])) for row in case['task']['test']))
    return {'train': deepcopy(case['task']['train']),
            'test': [{'input': deepcopy(row['input'])} for row in case['task']['test']]}


def validate_witness(case, budget):
    """Compare executable witness against the separately constructed oracle."""
    if case['witness'] is None:
        return False
    pairs = list(case['task']['train']) + [
        {'input': row['input'], 'output': expected}
        for row, expected in zip(case['task']['test'], case['expected'])]
    for pair in pairs:
        actual = execute(case['witness'], pair['input'], budget=budget)
        budget.consume('witness_compare_cells', sum(map(len, pair['output'])))
        if [list(row) for row in actual] != pair['output']:
            return False
    return True


def exact_success(result, expected):
    if result.get('status') != 'solved' or result.get('test_verified') is not False:
        return False
    predictions = result.get('predictions')
    if type(predictions) is not list or len(predictions) != len(expected):
        return False
    for actual, truth in zip(predictions, expected):
        if type(actual) is not list or len(actual) != len(truth):
            return False
        for row, reference in zip(actual, truth):
            if (type(row) is not list or len(row) != len(reference)
                    or any(type(v) is not int or not 0 <= v <= 9 for v in row) or row != reference):
                return False
    return True


def source_identity(budget=None):
    """Fixed source closure for this instrument, including legacy execution bases.

    The parent also archives its whole run. No discovered report path is opened.
    """
    paths = [f'ECHO-5/src/echo5/{name}.py' for name in
             ('__init__', 'grounding', 'programs', 'concepts', 'solver', 'transfer', 'budget', 'legacy', 'trace')]
    paths += ['__init__.py', 'seed/__init__.py', 'seed/dsl.py', 'seed/learn.py',
              'seed/refinement.py', 'seed/relational_dsl.py', 'echo_arc/__init__.py',
              'echo_arc/observe.py', 'ECHO-5/docs/TRANSFER-CONTRACT.json']
    files = {}
    for relative in sorted(paths):
        raw = (ROOT.parent / relative).read_bytes()
        if budget is not None:
            budget.consume('source_read_hash_bytes', 2*len(raw))
        files[relative] = hashlib.sha256(raw).hexdigest()
    return {'files': files, 'sha256': digest(files, budget)}


def _schedule(config):
    contract = load_contract()
    for family in config['families']:
        offset = (SUPPORTED_FAMILIES + CONTROL_FAMILIES).index(family) * contract['seeds']['family_offset']
        for seed in config['seeds']:
            yield family, seed + offset


def _generated_case(seed, family, split, config):
    ledger = Budget(config['generator_work_per_case'])
    case = make_case(seed, family, split=split, budget=ledger,
                     demonstrations=config['demonstrations'], queries=config['queries'])
    if case['witness'] is not None and not validate_witness(case, ledger):
        raise RuntimeError('independent generator/witness disagreement: ' + case['id'])
    return case, ledger.snapshot()


def _emit(journal, **facts):
    if journal is not None:
        journal.write(**facts)


def _fixed_program(family):
    if family in ('outline_extract', 'fill_extract'):
        return {'steps': [{'op': 'call', 'name': 'fixed_' + family.split('_')[0]}, _rel('extract')]}
    return witness_program(family)


def _prepare_libraries(config, journal, frozen_training=None):
    """All acquisition precedes evaluation; failed attempts remain in receipts."""
    contract = load_contract()
    libraries = {name: Library() for name in ('learned', 'fixed', 'irrelevant', 'empty')}
    ledgers = {name: Budget(config['preparation_work']) for name in libraries}
    training = []
    for index, (family, seed) in enumerate(zip(contract['training_families'], contract['training_seeds'])):
        if frozen_training is None:
            case, generation = _generated_case(seed, family, 'acquisition', config)
        else:
            case = deepcopy(frozen_training[index]['case'])
            generation = deepcopy(frozen_training[index]['generator_work'])
        ledger = Budget(config['training_work_per_case'])
        start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
        _emit(journal, kind='transfer_acquisition', case_id=case['id'], family=family)
        result = solve(public_task(case, budget=ledger), budget=ledger, library=libraries['learned'],
                       learn=True, synthesis=config['synthesis'], cache_policy='interned', journal=journal)
        after = libraries['learned'].state(budget=ledgers['learned'])
        training.append({'id': case['id'], 'family': family, 'seed': seed,
                         'case': case, 'generator_work': generation, 'result': result,
                         'work': ledger.snapshot(), 'library_after': after['checksum'],
                         'wall_ns': time.perf_counter_ns()-start_wall,
                         'process_ns': time.process_time_ns()-start_cpu})
        libraries['fixed'].acquire('fixed_' + family, _fixed_program(family),
                                    case['task']['train'], budget=ledgers['fixed'],
                                    provenance={'source': 'preregistered fixed structural library', 'task_id': case['id']})
    learned_state = libraries['learned'].state(budget=ledgers['learned'])
    for index, record in enumerate(learned_state['concepts']):
        # Functionally identity, with exactly the matched expanded node count.
        # Supports use acquisition inputs only. These cannot teach a target rule.
        steps = [{'op': 'identity'} for _ in record['expanded']['steps']]
        evidence = [{'input': deepcopy(pair['input']), 'output': deepcopy(pair['input'])}
                    for pair in record['demonstrations']]
        ledgers['irrelevant'].consume('control_evidence_copy_cells',
                                     2 * sum(sum(map(len, p['input'])) for p in evidence))
        libraries['irrelevant'].acquire(f'irrelevant_{index}', {'steps': steps}, evidence,
                                       budget=ledgers['irrelevant'],
                                       provenance={'source': 'size-matched identity control on acquisition inputs'})
    states = {name: lib.state(budget=ledgers[name]) for name, lib in libraries.items()}
    preparation = {name: ledger.snapshot() for name, ledger in ledgers.items()}
    return libraries, states, training, preparation


def _library_arm(condition):
    return condition if condition in ('learned', 'fixed', 'irrelevant') else 'empty'


def _execute_row(config, case, condition, library, journal=None):
    ledger, judge = Budget(config['work_per_case']), Budget(config['generator_work_per_case'])
    synthesis = deepcopy(config['synthesis'])
    if condition == 'empty_shallow':
        synthesis['max_depth'] = 2
    start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
    _emit(journal, kind='transfer_case', case_id=case['id'], condition=condition,
          library_condition=_library_arm(condition))
    result = solve(public_task(case, budget=ledger), budget=ledger, library=library,
                   relational=condition != 'old_representation',
                   hierarchical=condition != 'empty_uncached', synthesis=synthesis,
                   cache_policy='interned', learn=False, journal=journal)
    judge.consume('external_comparison_cells', sum(sum(map(len, grid)) for grid in case['expected']))
    success = exact_success(result, case['expected'])
    row = {'id': case['id'], 'case_sha256': case['sha256'], 'family': case['family'],
           'seed': case['seed'], 'condition': condition, 'supported': case['supported'],
           'task': public_task(case, budget=judge), 'expected': deepcopy(case['expected']),
           'result': result, 'success': success, 'work': ledger.snapshot(),
           'judge_work': judge.snapshot(), 'wall_ns': time.perf_counter_ns()-start_wall,
           'process_ns': time.process_time_ns()-start_cpu}
    _emit(journal, kind='independent_transfer_result', case_id=case['id'], condition=condition,
          success=success, status=result['status'], work=ledger.used,
          evaluator_work=judge.used, test_verified=False)
    return row


def _check_work(work, *, limit=None):
    if (type(work) is not dict or set(work) != {'limit', 'used', 'remaining', 'counts'}
            or any(type(work.get(key)) is not int or work[key] < 0 for key in ('limit', 'used', 'remaining'))
            or type(work['counts']) is not dict
            or any(type(k) is not str or type(v) is not int or v < 0 for k, v in work['counts'].items())
            or sum(work['counts'].values()) != work['used']
            or work['used'] + work['remaining'] != work['limit']
            or limit is not None and work['limit'] != limit):
        raise ValueError('invalid work ledger')
    return work['used']


def _pair(rows, control, treatment, arms):
    a = {row['id']: row for row in rows if row['condition'] == control and row['supported']}
    b = {row['id']: row for row in rows if row['condition'] == treatment and row['supported']}
    available = control in arms and treatment in arms and bool(a) and set(a) == set(b)
    wins = sum(b[key]['success'] and not a[key]['success'] for key in a) if available else 0
    losses = sum(a[key]['success'] and not b[key]['success'] for key in a) if available else 0
    return {'available': available, 'cases': len(a) if available else 0, 'wins': wins, 'losses': losses,
            'control_total_work': arms.get(control, {}).get('total_work', 0),
            'treatment_total_work': arms.get(treatment, {}).get('total_work', 0),
            'control_semantic_work': arms.get(control, {}).get('semantic_work', 0),
            'treatment_semantic_work': arms.get(treatment, {}).get('semantic_work', 0)}


def _partition_work(ledgers, metadata_categories):
    """Partition recorded costs without deleting any work from total accounting.

    Semantic means the complement of the contract's exact metadata categories.
    In particular, search-state hashing, prefix indexes and evidence execution
    are retained. This is not an estimate of wall time or abstract reasoning.
    """
    total = metadata = 0
    for ledger in ledgers:
        total += ledger['used']
        metadata += sum(ledger['counts'].get(name, 0) for name in metadata_categories)
    return {'semantic_work': total - metadata, 'metadata_work': metadata, 'total_work': total}


def _metametric_difference(arms, control, available):
    difference = {'available': available, 'sign': 'treatment_minus_control',
                  'evaluation': None, 'total': None, 'evaluation_saving_is_metadata_only': False}
    if not available:
        return difference
    learned, reference = arms['learned'], arms[control]
    fields = ('semantic_work', 'metadata_work', 'total_work')
    difference['evaluation'] = {
        key: learned['cost_breakdown']['evaluation'][key] - reference['cost_breakdown']['evaluation'][key]
        for key in fields}
    difference['total'] = {key: learned[key] - reference[key] for key in fields}
    evaluation = difference['evaluation']
    difference['evaluation_saving_is_metadata_only'] = (
        evaluation['total_work'] < 0 and evaluation['semantic_work'] == 0)
    return difference


def _required_gates_pass(gates, required):
    """Fail closed on missing/non-Boolean gates; descriptive gates do not vote."""
    if type(required) is not list or not required or any(type(name) is not str for name in required):
        return False
    return len(set(required)) == len(required) and all(gates.get(name) is True for name in required)


def recompute_summary(config, rows, training, libraries, preparation, cases, custody_work):
    """Pure arithmetic primitive for the parent; audit_benchmark validates inputs.

    Paired comparisons use supported tasks only for accuracy; total work includes
    every row, including ambiguous/unsupported cases and failed acquisition.
    Semantic/metadata partitions use those same ledgers, including acquisition.
    This V2 policy never reclassifies an archived V1 receipt as a V2 result.
    """
    contract = load_contract()
    metadata_categories = contract['metadata_work_categories']
    acquisition = sum(row['work']['used'] for row in training)
    acquisition_generation = sum(row['generator_work']['used'] for row in training)
    common = sum(row['generator_work']['used'] for row in cases) + custody_work['used']
    arms = {}
    for condition in config['conditions']:
        current = [row for row in rows if row['condition'] == condition]
        supported = [row for row in current if row['supported']]
        controls = [row for row in current if not row['supported']]
        lib = _library_arm(condition)
        training_work = acquisition + acquisition_generation if lib in ('learned', 'irrelevant') else (
            acquisition_generation if lib == 'fixed' else 0)
        evaluation = sum(row['work']['used'] + row['judge_work']['used'] for row in current)
        training_ledgers = [row['generator_work'] for row in training] if lib != 'empty' else []
        if lib in ('learned', 'irrelevant'):
            training_ledgers += [row['work'] for row in training]
        cost_breakdown = {
            'training': _partition_work(training_ledgers, metadata_categories),
            'preparation': _partition_work([preparation[lib]], metadata_categories),
            'evaluation': _partition_work(
                [row[key] for row in current for key in ('work', 'judge_work')], metadata_categories),
            'common': _partition_work(
                [entry['generator_work'] for entry in cases] + [custody_work], metadata_categories)}
        state = libraries[lib]
        arms[condition] = {'cases': len(current), 'supported_cases': len(supported),
                           'successes': sum(row['success'] for row in current),
                           'supported_successes': sum(row['success'] for row in supported),
                           'control_cases': len(controls),
                           'control_predictions': sum(bool(row['result']['predictions']) or row['result']['status'] == 'solved'
                                                      for row in controls),
                           'training_work': training_work, 'preparation_work': preparation[lib]['used'],
                           'evaluation_work': evaluation, 'common_work': common,
                           'total_work': training_work + preparation[lib]['used'] + evaluation + common,
                           'semantic_work': sum(part['semantic_work'] for part in cost_breakdown.values()),
                           'metadata_work': sum(part['metadata_work'] for part in cost_breakdown.values()),
                           'cost_breakdown': cost_breakdown,
                           'library_records': len(state['concepts']),
                           'library_expanded_steps': sum(len(r['expanded']['steps']) for r in state['concepts']),
                           'library_serialized_bytes': len(json.dumps(state, sort_keys=True, separators=(',', ':')).encode()),
                           'statuses': dict(sorted(Counter(row['result']['status'] for row in current).items())),
                           'families': {family: {'cases': sum(row['family'] == family for row in current),
                                               'successes': sum(row['success'] for row in current if row['family'] == family)}
                                        for family in config['families']}}
    comparisons = {f'learned_vs_{control}': _pair(rows, control, 'learned', arms)
                   for control in ('empty', 'fixed', 'irrelevant')}
    comparisons['hierarchy'] = _pair(rows, 'empty_shallow', 'empty', arms)
    comparisons['representation'] = _pair(rows, 'old_representation', 'empty', arms)
    comparisons['prefix'] = _pair(rows, 'empty_uncached', 'empty', arms)
    raw = {condition: {row['id']: row for row in rows if row['condition'] == condition}
           for condition in config['conditions']}
    cache_pairs = bool(raw.get('empty')) and set(raw.get('empty', {})) == set(raw.get('empty_uncached', {}))
    comparisons['prefix']['identical_search_results'] = bool(cache_pairs and all(
        all(raw['empty'][key]['result'].get(field) == raw['empty_uncached'][key]['result'].get(field)
            for field in ('status', 'predictions', 'program', 'hypothesis'))
        and all(raw['empty'][key]['result']['metrics'].get(field) == raw['empty_uncached'][key]['result']['metrics'].get(field)
                for field in ('candidates', 'complete', 'tier', 'beam_pruned', 'semantic_duplicates'))
        for key in raw['empty']))
    thresholds = contract['gates']
    def gain(comparison, minimum=1):
        return (comparison['available'] and comparison['wins'] >= minimum
                and comparison['losses'] <= thresholds['maximum_paired_losses'])
    def saving(comparison, percent, metric='total_work'):
        return (comparison['available'] and comparison['losses'] <= thresholds['maximum_paired_losses']
                and (metric == 'total_work' or comparison['control_' + metric] > 0)
                and 100*comparison['treatment_' + metric] <= (100-percent)*comparison['control_' + metric])
    learned, irrelevant = arms.get('learned', {}), arms.get('irrelevant', {})
    gates = {
        'supported_accuracy': bool(learned.get('supported_cases', 0) and
            100*learned['supported_successes'] >= thresholds['minimum_supported_success_percent']*learned['supported_cases']),
        'abstention_controls': bool(set(CONTROL_FAMILIES) <= set(config['families']) and all(
            arm['control_cases'] > 0 and arm['control_predictions'] <= thresholds['maximum_false_predictions_on_controls']
            for arm in arms.values())),
        'library_size_control': bool(learned.get('library_records', 0) > 0
            and learned['library_records'] == irrelevant.get('library_records')
            and learned['library_expanded_steps'] == irrelevant.get('library_expanded_steps')),
        'prefix_correctness': comparisons['prefix']['identical_search_results'],
        'prefix_efficiency': bool(comparisons['prefix']['identical_search_results']
            and saving(comparisons['prefix'], thresholds['minimum_prefix_saving_percent'])),
        'hierarchy_benefit': bool(gain(comparisons['hierarchy'], thresholds['minimum_hierarchy_wins'])),
        'representation_benefit': bool(gain(comparisons['representation'], thresholds['minimum_representation_wins'])),
        'no_invalid_actor_results': all(row['result']['status'] in
            ('solved', 'ambiguous', 'unsolved', 'budget_exhausted', 'search_exhausted') for row in rows),
    }
    for control in ('empty', 'fixed', 'irrelevant'):
        comparison = comparisons[f'learned_vs_{control}']
        gates[f'learned_vs_{control}'] = bool(saving(comparison, thresholds['minimum_memory_saving_percent']))
    # Keep the V1 strict fixed-oracle comparison visible, but descriptive.
    # Metadata savings cannot supply the required memory improvement on their own.
    for control in ('empty', 'irrelevant'):
        gates[f'learned_vs_{control}_semantic'] = bool(saving(
            comparisons[f'learned_vs_{control}'], thresholds['minimum_memory_saving_percent'], 'semantic_work'))
    fixed = comparisons['learned_vs_fixed']
    gates['fixed_accuracy_noninferiority'] = bool(fixed['available'] and fixed['losses'] == 0)
    gates['fixed_total_cost_noninferiority'] = bool(fixed['available'] and
        100 * fixed['treatment_total_work'] <=
        (100 + thresholds['maximum_fixed_total_cost_overhead_percent']) * fixed['control_total_work'])
    gates['confirmatory_config'] = config['phase'] == 'confirmation' and config == default_config('confirmation')
    gates['closure_candidate'] = _required_gates_pass(gates, contract['required_gates'])
    physical = (acquisition + acquisition_generation + sum(v['used'] for v in preparation.values())
                + sum(row['work']['used'] + row['judge_work']['used'] for row in rows) + common)
    summary = {'scope': 'bounded synthetic structural transfer; no ARC score or general statistical independence',
               'phase': config['phase'], 'arms': arms, 'comparisons': comparisons,
               'condition_roles': deepcopy(contract['condition_roles']),
               'required_gates': list(contract['required_gates']),
               'descriptive_gates': list(contract['descriptive_gates']),
               'metadata_work_categories': list(metadata_categories),
               'metametric_differences': {
                   'learned_vs_' + control: _metametric_difference(
                       arms, control, comparisons['learned_vs_' + control]['available'])
                   for control in ('empty', 'fixed', 'irrelevant')},
               'closure_meaning': contract['methodology_v2']['closure_meaning'],
               'prior_development': deepcopy(contract['prior_development']),
               'training_cases': len(training), 'distinct_evaluation_cases': len(cases),
               'distinct_public_tasks': len({row['case']['public_sha256'] for row in cases}),
               'condition_rows': len(rows), 'physical_run_work': physical,
               'common_work': common, 'acquisition_search_work': acquisition,
               'acquisition_generator_work': acquisition_generation,
               'irrelevant_matching_includes_acquisition': True,
               'official_arc_score': None, 's6_green': False,
               'verification': 'pending_independent_replay'}
    return summary, gates


def run_benchmark(config, journal=None):
    """Run the frozen transfer domain; caller owns background execution/artifacts.

    Config accepts default_config(phase) or {'phase': phase}, not the complete
    contract document. Development permits explicit reduced runs. Confirmation
    rejects all overrides. No CLI, process, observer or file write is launched.
    """
    config = normalize_config(config)
    start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
    custody = Budget(config['preparation_work'])
    sources = source_identity(custody)
    contract = load_contract()
    contract_sha = digest(contract, custody)
    _emit(journal, kind='transfer_contract', phase=config['phase'], config=config,
          contract_sha256=contract_sha, source_sha256=sources['sha256'])
    libraries, states, training, preparation = _prepare_libraries(config, journal)
    _emit(journal, kind='transfer_libraries_frozen',
          libraries={name: state['checksum'] for name, state in states.items()})
    cases = []
    for family, seed in _schedule(config):
        case, generation = _generated_case(seed, family, config['phase'], config)
        cases.append({'case': case, 'generator_work': generation})
    if {row['case']['public_sha256'] for row in training} & {row['case']['public_sha256'] for row in cases}:
        raise RuntimeError('acquisition and evaluation contain an identical public task')
    rows = []
    # Fixed rotation of arm order avoids confounding every timing with first/last.
    conditions = config['conditions']
    for index, entry in enumerate(cases):
        order = conditions[index % len(conditions):] + conditions[:index % len(conditions)]
        for condition in order:
            row = _execute_row(config, entry['case'], condition,
                               libraries[_library_arm(condition)], journal)
            row['library_checksum'] = states[_library_arm(condition)]['checksum']
            row['source_sha256'] = sources['sha256']
            rows.append(row)
    for name, library in libraries.items():
        if library.state(budget=custody) != states[name]:
            raise RuntimeError('evaluation mutated a frozen library')
    if source_identity(custody) != sources:
        raise RuntimeError('sources changed during transfer measurement')
    summary, gates = recompute_summary(config, rows, training, states, preparation, cases, custody.snapshot())
    report = {'schema': SCHEMA, 'config': config, 'rows': rows, 'summary': summary, 'gates': gates,
              'contract': contract, 'contract_sha256': contract_sha, 'sources': sources,
              'libraries': states, 'training': training, 'preparation_work': preparation,
              'cases': cases, 'custody_work': custody.snapshot(),
              'runtime': {'python': sys.version, 'implementation': sys.implementation.name,
                          'wall_ns': time.perf_counter_ns()-start_wall,
                          'process_ns': time.process_time_ns()-start_cpu},
              'limits': ['Shared generator/grammar priors; these are not independent capability domains.',
                         'Beam pruning and first-tier consensus are not proof over the entire language.',
                         'R1 pack_rotate_scale was 1/2; pack_beam_limitation remains an open work item.',
                         'V2 closure does not establish superiority to the fixed manual knowledge oracle.',
                         'All logical costs are instrumented work units, not FLOPs, joules or a timing guarantee.',
                         'No holdout labels, witnesses, seeds or family names enter solve.',
                         'Source ZIP, fresh-process replay and publication are owned by the parent.']}
    _emit(journal, kind='transfer_report', summary=summary, gates=gates,
          source_sha256=sources['sha256'], contract_sha256=contract_sha)
    return report


def _same(actual, expected, label):
    """Type-sensitive JSON equality (True must not be accepted as the integer 1)."""
    options = {'sort_keys': True, 'separators': (',', ':'), 'allow_nan': False}
    if json.dumps(actual, **options) != json.dumps(expected, **options):
        raise ValueError('receipt mismatch: ' + label)


def _actor_evidence(result, work, case, library, budget):
    """Re-execute every claimed solved program, without trusting its verdict."""
    if type(result) is not dict or result.get('test_verified') is not False:
        raise ValueError('actor cannot certify query truth')
    if result.get('status') not in ('solved', 'unsolved', 'ambiguous', 'budget_exhausted',
                                   'search_exhausted', 'invalid_task', 'invalid_library', 'invalid_search'):
        raise ValueError('unknown actor status')
    metrics = result['metrics']
    _same({key: metrics[key] for key in ('limit', 'used', 'remaining', 'counts')}, work, 'actor work')
    if (type(metrics.get('task_used')) is not int or not 0 <= metrics['task_used'] <= work['used']
            or metrics.get('cortex_calls') != 0 or type(metrics.get('complete')) is not bool):
        raise ValueError('invalid actor metrics')
    if result['status'] in ('budget_exhausted', 'search_exhausted') and metrics['complete']:
        raise ValueError('exhausted search cannot be complete')
    if result['status'] != 'solved':
        if result.get('predictions') != [] or result.get('program') is not None or result.get('hypothesis') is not None:
            raise ValueError('abstention contains a prediction')
        return
    if not metrics['complete']:
        raise ValueError('partial tier emitted a prediction')
    expanded = Program(expand(result['hypothesis'], library=library, budget=budget)).to_dict()
    _same(expanded, result['program'], 'symbolic/expanded program')
    for pair in case['task']['train']:
        actual = execute(result['program'], pair['input'], budget=budget)
        budget.consume('audit_compare_cells', sum(map(len, pair['output'])))
        _same([list(row) for row in actual], pair['output'], 'claimed demonstration fit')
    predicted = [[list(row) for row in execute(result['program'], query['input'], budget=budget)]
                 for query in case['task']['test']]
    _same(predicted, result['predictions'], 'claimed executable prediction')


def _audit_libraries(report, budget):
    """Reconstruct acquisition from recorded programs and original support.

    This verifies evidence, not the solver's search decisions or work count.
    Full replay below is necessary to certify those separate claims.
    """
    learned, fixed, irrelevant = Library(), Library(), Library()
    for row in report['training']:
        result, case = row['result'], row['case']
        _actor_evidence(result, row['work'], case, learned, budget)
        if result['metrics'].get('learning') == 'acquired':
            if result['status'] != 'solved':
                raise ValueError('learning requires a completed consensus')
            program = result['hypothesis']
            name = 'c_' + digest(program, budget)[:24]
            learned.acquire(name, program, case['task']['train'], budget=budget,
                            provenance={'source': 'bounded synthesis demonstrations'})
        _same(learned.state(budget=budget)['checksum'], row['library_after'], 'training library transition')
        fixed.acquire('fixed_' + row['family'], _fixed_program(row['family']),
                      case['task']['train'], budget=budget,
                      provenance={'source': 'preregistered fixed structural library', 'task_id': case['id']})
    for index, record in enumerate(learned.state(budget=budget)['concepts']):
        program = {'steps': [{'op': 'identity'} for _ in record['expanded']['steps']]}
        evidence = [{'input': pair['input'], 'output': pair['input']} for pair in record['demonstrations']]
        irrelevant.acquire(f'irrelevant_{index}', program, evidence, budget=budget,
                           provenance={'source': 'size-matched identity control on acquisition inputs'})
    rebuilt = {'learned': learned, 'fixed': fixed, 'irrelevant': irrelevant, 'empty': Library()}
    if set(report['libraries']) != set(rebuilt):
        raise ValueError('missing or unexpected library condition')
    for name, lib in rebuilt.items():
        # Restore additionally checks the complete record/receipt/dependency schema.
        restored = Library.restore(report['libraries'][name], budget=budget)
        _same(lib.state(budget=budget), restored.state(budget=budget), 'acquired ' + name + ' library')
    return rebuilt


def audit_benchmark(report, replay=False):
    """Audit frozen JSON receipts; replay uses the recorded public inputs.

    Returns an explicit ``valid`` boolean. Arithmetic/evidence-only checking
    leaves valid=False; replay=True additionally rebuilds acquisition and all
    actor results/work from the same inputs. Raise ValueError on any mismatch.
    Run from a fresh process with the parent's archived sources for closure.
    """
    start_wall, start_cpu = time.perf_counter_ns(), time.process_time_ns()
    budget = Budget(100_000_000)
    regeneration_work = 0
    if type(report) is not dict or report.get('schema') != SCHEMA or type(replay) is not bool:
        raise ValueError('unknown transfer report or replay option')
    contract = load_contract()
    _same(report['contract'], contract, 'frozen contract')
    _same(report['contract_sha256'], digest(contract, budget), 'contract identity')
    config = normalize_config(report['config'])
    _same(config, report['config'], 'normalized config')
    _same(report['sources'], source_identity(budget), 'frozen source identity')
    _check_work(report['custody_work'], limit=config['preparation_work'])
    if set(report['preparation_work']) != {'learned', 'fixed', 'irrelevant', 'empty'}:
        raise ValueError('missing preparation ledger')
    for value in report['preparation_work'].values():
        _check_work(value, limit=config['preparation_work'])
    if type(report['training']) is not list or len(report['training']) != len(TRAINING_FAMILIES):
        raise ValueError('incomplete acquisition')
    for row, family, seed in zip(report['training'], contract['training_families'], contract['training_seeds']):
        expected, work = _generated_case(seed, family, 'acquisition', config)
        regeneration_work += work['used']
        _same(row['case'], expected, 'frozen acquisition input/oracle')
        _same(row['generator_work'], work, 'acquisition generator work')
        _same([row['id'], row['family'], row['seed']], [expected['id'], family, seed], 'acquisition identity')
        _check_work(row['work'], limit=config['training_work_per_case'])
    schedule = list(_schedule(config))
    if type(report['cases']) is not list or len(report['cases']) != len(schedule):
        raise ValueError('missing scheduled case')
    cases = {}
    for entry, (family, seed) in zip(report['cases'], schedule):
        expected, work = _generated_case(seed, family, config['phase'], config)
        regeneration_work += work['used']
        _same(entry, {'case': expected, 'generator_work': work}, 'frozen evaluation input/oracle')
        if expected['id'] in cases:
            raise ValueError('duplicate case')
        cases[expected['id']] = entry['case']
    if {r['case']['public_sha256'] for r in report['training']} & {c['public_sha256'] for c in cases.values()}:
        raise ValueError('acquisition/evaluation content overlap')
    libraries = _audit_libraries(report, budget)
    expected_pairs = {(case_id, condition) for case_id in cases for condition in config['conditions']}
    observed = set()
    for row in report['rows']:
        key = row['id'], row['condition']
        if key not in expected_pairs or key in observed:
            raise ValueError('duplicate or unexpected scored row')
        observed.add(key)
        case = cases[row['id']]
        arm = _library_arm(row['condition'])
        _same([row['case_sha256'], row['family'], row['seed'], row['supported'], row['task'], row['expected']],
              [case['sha256'], case['family'], case['seed'], case['supported'], case['task'], case['expected']],
              'scored case identity and truth')
        _same(row['library_checksum'], report['libraries'][arm]['checksum'], 'row library')
        _same(row['source_sha256'], report['sources']['sha256'], 'row sources')
        _check_work(row['work'], limit=config['work_per_case'])
        _check_work(row['judge_work'], limit=config['generator_work_per_case'])
        # External comparison and detached task copy are deterministic work too.
        judge = Budget(config['generator_work_per_case'])
        judge.consume('external_comparison_cells', sum(sum(map(len, grid)) for grid in case['expected']))
        public_task(case, budget=judge)
        _same(row['judge_work'], judge.snapshot(), 'external comparison work')
        _actor_evidence(row['result'], row['work'], case, libraries[arm], budget)
        if type(row['success']) is not bool or row['success'] != exact_success(row['result'], case['expected']):
            raise ValueError('forged exact success')
    if observed != expected_pairs:
        raise ValueError('incomplete scored matrix')
    summary, gates = recompute_summary(config, report['rows'], report['training'], report['libraries'],
                                      report['preparation_work'], report['cases'], report['custody_work'])
    _same(report['summary'], summary, 'summary')
    _same(report['gates'], gates, 'gates')
    replayed_work, replayed_rows, replayed_training = 0, 0, 0
    if replay:
        # Generation was checked above; actual search consumes recorded inputs.
        replay_libs, replay_states, training, preparation = _prepare_libraries(config, None, report['training'])
        _same(replay_states, report['libraries'], 'replayed libraries')
        _same(preparation, report['preparation_work'], 'replayed preparation work')
        for actual, expected in zip(training, report['training']):
            for field in ('result', 'work', 'library_after'):
                _same(actual[field], expected[field], 'replayed training ' + field)
            replayed_work += actual['work']['used']
            replayed_training += 1
        replayed_work += sum(row['used'] for row in preparation.values())
        for row in report['rows']:
            actual = _execute_row(config, cases[row['id']], row['condition'],
                                  replay_libs[_library_arm(row['condition'])])
            for field in ('result', 'work', 'judge_work', 'success'):
                _same(actual[field], row[field], 'replayed row ' + field)
            replayed_work += actual['work']['used'] + actual['judge_work']['used']
            replayed_rows += 1
        # Recompute custodial scans, end-state freezes and contract hashing too.
        custody = Budget(config['preparation_work'])
        _same(source_identity(custody), report['sources'], 'replay starting sources')
        digest(contract, custody)
        for name, lib in replay_libs.items():
            _same(lib.state(budget=custody), report['libraries'][name], 'post-replay frozen library')
        _same(source_identity(custody), report['sources'], 'replay ending sources')
        _same(custody.snapshot(), report['custody_work'], 'custody work')
        replayed_work += custody.used
    _same(source_identity(budget), report['sources'], 'audit ending sources')
    return {'schema': 'echo5.transfer.audit.v2', 'valid': replay,
            'arithmetic_valid': True, 'evidence_valid': True, 'sources_match': True,
            'status': 'replayed' if replay else 'evidence_checked_pending_replay',
            'rows_checked': len(observed), 'training_checked': len(report['training']),
            'replayed_rows': replayed_rows, 'replayed_training': replayed_training,
            'replayed_work': replayed_work, 'regeneration_work': regeneration_work,
            'audit_work': budget.snapshot(),
            'total_audit_work': budget.used + regeneration_work + replayed_work,
            'summary': summary, 'gates': gates, 'source_sha256': report['sources']['sha256'],
            'wall_ns': time.perf_counter_ns()-start_wall,
            'process_ns': time.process_time_ns()-start_cpu}


def audit_report(report):
    """Parent orchestration hook: always perform the full recorded-input replay."""
    return audit_benchmark(report, replay=True)
