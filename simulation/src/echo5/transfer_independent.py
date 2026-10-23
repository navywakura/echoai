"""Independent, stdlib-only development generator and transfer instrument.

Construction records supply truth, never the actor's segmentation/interpreter.
Only run_benchmark imports the solver and old template comparator. Importing or
generating cases does not run search, read campaigns, or write artifacts.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import platform
import random

from .budget import Budget

SCHEMA = 'echo5.transfer_independent.v1'
SUPPORTED_FAMILIES = ('outline_extract_scale', 'fill_extract_tile',
                      'inside_erase_crop', 'right_erase_crop_rotate',
                      'below_recolor_reflect', 'pack_reflect')
CONTROL_FAMILIES = ('ambiguous_reflection', 'unsupported_new_color')
FAMILIES = SUPPORTED_FAMILIES + CONTROL_FAMILIES
COMPARABLE_FAMILIES = SUPPORTED_FAMILIES[:3]
PREPARATION_LIMIT = 20_000_000
ABSTENTIONS = ('unsolved', 'ambiguous', 'budget_exhausted', 'search_exhausted')


def _ledger(ledger):
    return Budget(PREPARATION_LIMIT) if ledger is None else ledger


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _digest(value, ledger):
    raw = _json(value).encode('utf-8')
    ledger.consume('json_encode_and_hash_bytes', 2 * len(raw))
    return hashlib.sha256(raw).hexdigest()


def _integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in {low}..{high}')


def _pick(rng, values, ledger):
    ledger.consume('random_draws')
    return values[rng.randrange(len(values))]


def _neighbors(cell):
    y, x = cell
    return ((y-1, x), (y+1, x), (y, x-1), (y, x+1))


def _box(cells, ledger):
    ledger.consume('bounds_cells', len(cells))
    ys, xs = zip(*cells)
    return min(ys), min(xs), max(ys), max(xs)


def _connected(cells, ledger):
    unseen = set(cells)
    queue = [min(unseen)]
    unseen.remove(queue[0])
    while queue:
        ledger.consume('connectivity_neighbors', 4)
        for point in _neighbors(queue.pop()):
            if point in unseen:
                unseen.remove(point)
                queue.append(point)
    return not unseen


def _boundary(cells, ledger):
    cells = set(cells)
    ledger.consume('boundary_neighbors', 4 * len(cells))
    return {p for p in cells if any(q not in cells for q in _neighbors(p))}


def _polyomino(rng, area, height, width, ledger, *, outline=False):
    """Frontier growth, rejecting rectangles and disconnected outlines.

    Rejections enforce geometric preconditions only; no solver is consulted.
    Sorted frontiers make draws independent of Python's hash seed.
    """
    for _ in range(256):
        ledger.consume('shape_attempts')
        cells = {(height // 2, width // 2)}
        while len(cells) < area:
            ledger.consume('growth_neighbor_visits', 4 * len(cells))
            frontier = {p for cell in cells for p in _neighbors(cell)
                        if 0 <= p[0] < height and 0 <= p[1] < width and p not in cells}
            ledger.consume('frontier_order_items', len(frontier) * max(1, len(frontier).bit_length()))
            cells.add(_pick(rng, sorted(frontier), ledger))
        y0, x0, y1, x1 = _box(cells, ledger)
        if len(cells) == (y1-y0+1) * (x1-x0+1):
            continue
        if outline:
            boundary = _boundary(cells, ledger)
            if boundary == cells or not _connected(boundary, ledger):
                continue
        ledger.consume('shape_normalize_cells', len(cells))
        return sorted((y-y0, x-x0) for y, x in cells)
    raise RuntimeError('polyomino construction exhausted; instrument failure')


def _put(scene, shape, color, occupied, rng, ledger, *, region=None, outside=None):
    _, _, bottom, right = _box(shape, ledger)
    ymin, ymax, xmin, xmax = region or (1, scene['height']-bottom-2,
                                       1, scene['width']-right-2)
    if ymin > ymax or xmin > xmax:
        raise RuntimeError('empty placement region')
    for _ in range(512):
        ledger.consume('placement_attempts')
        y = _pick(rng, range(ymin, ymax+1), ledger)
        x = _pick(rng, range(xmin, xmax+1), ledger)
        if outside is not None:
            a, b, c, d = outside
            if not (y+bottom < a or y > c or x+right < b or x > d):
                continue
        ledger.consume('placement_cells', 5 * len(shape))
        cells = {(y+dy, x+dx) for dy, dx in shape}
        halo = cells | {q for p in cells for q in _neighbors(p)}
        if halo & occupied:
            continue
        occupied.update(cells)
        obj = {'color': color, 'cells': [list(p) for p in sorted(cells)]}
        scene['objects'].append(obj)
        return obj
    raise RuntimeError('scene placement exhausted; instrument failure')


def _symmetric_scene(rng, count, ledger):
    scene = {'height': 23, 'width': 23, 'objects': []}
    occupied = set()
    for index in range(count // 2):
        shape = _polyomino(rng, _pick(rng, range(3, 7), ledger), 3, 3, ledger)
        obj = _put(scene, shape, index+1, occupied, rng, ledger,
                   region=(1, 19, 1, 6))
        ledger.consume('symmetry_cells', len(shape))
        mirror = sorted((y, 22-x) for y, x in obj['cells'])
        scene['objects'].append({'color': obj['color'], 'cells': [list(p) for p in mirror]})
    if count % 2:
        scene['objects'].append({'color': 7, 'cells': [[10, 11], [11, 10], [11, 11],
                                                     [11, 12], [12, 11]]})
        ledger.consume('symmetric_center_cells', 5)
    return scene


def _generate_scene(rng, family, count, demonstration, ledger):
    if family == 'ambiguous_reflection' and demonstration:
        return _symmetric_scene(rng, count, ledger)
    scene = {'height': _pick(rng, range(22, 26), ledger),
             'width': _pick(rng, range(22, 26), ledger), 'objects': []}
    palette = list(range(1, 9 if family == 'unsupported_new_color' else 10))
    colors = []
    for _ in range(count):
        color = _pick(rng, palette, ledger)
        palette.remove(color)
        colors.append(color)
    occupied = set()
    if family == 'pack_reflect':
        sizes = list(range(3, 12))
        for color in colors:
            area = _pick(rng, sizes, ledger)
            sizes.remove(area)
            shape = _polyomino(rng, area, 4, 3, ledger)
            _put(scene, shape, color, occupied, rng, ledger)
        return scene

    if family == 'inside_erase_crop':
        h, w = _pick(rng, range(9, 12), ledger), _pick(rng, range(9, 12), ledger)
        ledger.consume('container_construct_cells', h*w)
        # Two-cell walls, clipped corners; optionally open a two-cell gate.
        # This changes topology, while "inside" retains strict box semantics.
        shape = {(y, x) for y in range(h) for x in range(w)
                 if y < 2 or x < 2 or y >= h-2 or x >= w-2}
        shape.difference_update(((0, 0), (h-1, w-1)))
        if _pick(rng, (False, True), ledger):
            shape.difference_update((y, x) for y in (0, 1) for x in (w//2, w//2+1))
        source = _put(scene, sorted(shape), colors[0], occupied, rng, ledger)
        a, b, c, d = _box(source['cells'], ledger)
        inner = _polyomino(rng, _pick(rng, range(3, 7), ledger), 3, 3, ledger)
        _, _, ih, iw = _box(inner, ledger)
        _put(scene, inner, colors[1], occupied, rng, ledger,
             region=(a+3, c-3-ih, b+3, d-3-iw))
        for color in colors[2:]:
            shape = _polyomino(rng, _pick(rng, range(3, 7), ledger), 3, 3, ledger)
            _put(scene, shape, color, occupied, rng, ledger, outside=(a, b, c, d))
        return scene

    shape = _polyomino(rng, _pick(rng, range(17, 23), ledger), 5, 5, ledger,
                       outline=family == 'outline_extract_scale')
    region = None
    if family == 'right_erase_crop_rotate':
        region = (1, scene['height']-6, 7, 10)
    elif family == 'below_recolor_reflect':
        region = (7, 10, 1, scene['width']-6)
    source = _put(scene, shape, colors[0], occupied, rng, ledger, region=region)
    a, b, c, d = _box(source['cells'], ledger)
    for index, color in enumerate(colors[1:]):
        shape = _polyomino(rng, _pick(rng, range(3, 7), ledger), 3, 3, ledger)
        _, _, sh, sw = _box(shape, ledger)
        region = None
        if family == 'right_erase_crop_rotate' and index < 2:
            region = (1, scene['height']-sh-2, d+2, scene['width']-sw-2) if index == 0 else (
                1, scene['height']-sh-2, 1, b-sw-2)
        elif family == 'below_recolor_reflect' and index < 2:
            region = (c+2, scene['height']-sh-2, 1, scene['width']-sw-2) if index == 0 else (
                1, a-sh-2, 1, scene['width']-sw-2)
        _put(scene, shape, color, occupied, rng, ledger, region=region)
    return scene


def _canvas(height, width, ledger):
    if not 1 <= height <= 30 or not 1 <= width <= 30:
        raise RuntimeError('constructed output exceeds grid contract')
    ledger.consume('canvas_cells', height * width)
    return [[0 for _ in range(width)] for _ in range(height)]


def _render(scene, ledger):
    rows = _canvas(scene['height'], scene['width'], ledger)
    for obj in scene['objects']:
        ledger.consume('render_object_cells', len(obj['cells']))
        for y, x in obj['cells']:
            if not (0 <= y < len(rows) and 0 <= x < len(rows[0])) or rows[y][x]:
                raise RuntimeError('invalid construction: overlap or bounds')
            rows[y][x] = obj['color']
    return rows


def oracle_output(scene, family, *, ledger=None):
    """Direct coordinate reference, independent of all actor operations.

    Scene records are evaluator data, never an alternative actor perception.
    This function does not interpret the witness programs declared below.
    """
    if family not in FAMILIES:
        raise ValueError('unknown independent family')
    ledger = _ledger(ledger)
    objects = scene['objects']
    ledger.consume('oracle_object_visits', len(objects))
    if family == 'ambiguous_reflection':
        rows = _render(scene, ledger)
        ledger.consume('reflect_cells', len(rows)*len(rows[0]))
        return [row[::-1] for row in rows]
    if family == 'pack_reflect':
        sizes = [len(o['cells']) for o in objects]
        if len(set(sizes)) != len(sizes):
            raise ValueError('oracle packing requires unequal areas')
        ledger.consume('pack_order_items', len(objects) * len(objects).bit_length())
        ordered = sorted(objects, key=lambda o: -len(o['cells']))
        boxes = [_box(o['cells'], ledger) for o in ordered]
        h = max(c-a+1 for a, b, c, d in boxes)
        w = sum(d-b+1 for a, b, c, d in boxes) + len(objects)-1
        out, offset = _canvas(h, w, ledger), 0
        for obj, (a, b, c, d) in zip(ordered, boxes):
            ledger.consume('pack_copy_cells', len(obj['cells']))
            for y, x in obj['cells']:
                out[y-a][w-1-(offset+x-b)] = obj['color']
            offset += d-b+2
        return out
    largest = max(len(o['cells']) for o in objects)
    choices = [o for o in objects if len(o['cells']) == largest]
    if len(choices) != 1:
        raise ValueError('oracle source requires a unique largest object')
    source = choices[0]
    a, b, c, d = _box(source['cells'], ledger)
    color = source['color']
    if family == 'outline_extract_scale':
        cells = _boundary(map(tuple, source['cells']), ledger)
        # Valid constructions preserve the source's extent and connectedness.
        out = _canvas(2*(c-a+1), 2*(d-b+1), ledger)
        ledger.consume('outline_scale_writes', 4 * len(cells))
        for y, x in cells:
            for dy in (0, 1):
                for dx in (0, 1):
                    out[2*(y-a)+dy][2*(x-b)+dx] = color
        return out
    if family == 'fill_extract_tile':
        out = _canvas(c-a+1, 2*(d-b+1), ledger)
        ledger.consume('fill_tile_writes', len(out)*len(out[0]))
        return [[color for _ in row] for row in out]

    pixels = {}
    for obj in objects:
        y0, x0, y1, x1 = _box(obj['cells'], ledger)
        inside = a < y0 and b < x0 and y1 < c and x1 < d
        right, below = x0 > d, y0 > c
        erase = obj is not source and ((family == 'inside_erase_crop' and inside)
                                       or (family == 'right_erase_crop_rotate' and right))
        paint = color if family == 'below_recolor_reflect' and below else obj['color']
        if family == 'unsupported_new_color' and obj is source:
            paint = 9
        ledger.consume('oracle_pixel_visits', len(obj['cells']))
        if not erase:
            pixels.update((tuple(p), paint) for p in obj['cells'])
    if family in ('inside_erase_crop', 'right_erase_crop_rotate'):
        y0, x0, y1, x1 = _box(pixels, ledger)
        h, w = y1-y0+1, x1-x0+1
        rotate = family == 'right_erase_crop_rotate'
        out = _canvas(w if rotate else h, h if rotate else w, ledger)
        ledger.consume('crop_transform_writes', len(pixels))
        for (y, x), paint in pixels.items():
            if rotate:
                out[x-x0][y1-y] = paint
            else:
                out[y-y0][x1-x] = paint
        return out
    out = _canvas(scene['height'], scene['width'], ledger)
    ledger.consume('oracle_output_writes', len(pixels))
    for (y, x), paint in pixels.items():
        out[y][scene['width']-1-x if family == 'below_recolor_reflect' else x] = paint
    return out


def witness_program(family):
    """Evaluator-only declarations: not executed by generation or benchmarking."""
    def relation(name, effect):
        return {'op': 'relate', 'role': 'largest', 'relation': name, 'effect': effect}
    programs = {
        'outline_extract_scale': [{'op': 'object', 'role': 'largest', 'effect': 'outline'},
                                  relation('all', 'extract'), {'op': 'up2'}],
        'fill_extract_tile': [{'op': 'object', 'role': 'largest', 'effect': 'fill_box'},
                             relation('all', 'extract'), {'op': 'tile1x2'}],
        'inside_erase_crop': [relation('inside', 'erase'), {'op': 'crop'}, {'op': 'fliplr'}],
        'right_erase_crop_rotate': [relation('right', 'erase'), {'op': 'crop'}, {'op': 'rot90'}],
        'below_recolor_reflect': [relation('below', 'recolor'), {'op': 'fliplr'}],
        'pack_reflect': [{'op': 'pack', 'axis': 'row'}, {'op': 'fliplr'}],
    }
    return {'steps': programs[family]} if family in programs else None


def _category(family):
    if family == 'ambiguous_reflection':
        return 'ambiguous_control'
    if family == 'unsupported_new_color':
        return 'unsupported_control'
    return 'supported'


def make_case(seed, family, *, demonstrations=3, queries=2):
    """Deterministic JSON case, independent truth, scenes and stage ledgers."""
    _integer(seed, 'seed', 0, 2**63-1)
    _integer(demonstrations, 'demonstrations', 2, 10)
    _integer(queries, 'queries', 1, 10)
    if family not in FAMILIES:
        raise ValueError('unknown independent family')
    generation, oracle, receipt = (_ledger(None) for _ in range(3))
    generation.consume('rng_initializations')
    rng, scenes, pairs, seen = random.Random(seed), [], [], set()
    for index in range(demonstrations + queries):
        count = 3 + (seed + index) % 4
        for _ in range(64):
            scene = _generate_scene(rng, family, count, index < demonstrations, generation)
            inp = _render(scene, generation)
            key = _digest(inp, generation)
            if key not in seen:
                break
            generation.consume('duplicate_example_rejections')
        else:
            raise RuntimeError('duplicate example exhaustion')
        seen.add(key)
        scenes.append(scene)
        pairs.append({'input': inp, 'output': oracle_output(scene, family, ledger=oracle)})
    task = {'train': pairs[:demonstrations],
            'test': [{'input': p['input']} for p in pairs[demonstrations:]]}
    case = {'id': f'independent-v1:{family}:{seed}', 'seed': seed, 'family': family,
            'category': _category(family), 'task': task, 'scenes': scenes,
            'expected': [p['output'] for p in pairs[demonstrations:]],
            'witness': witness_program(family)}
    if family == 'ambiguous_reflection':
        case['control_evidence'] = {'consistent_rules': ['identity', 'fliplr'],
                                    'reference_convention': 'fliplr; not uniquely inferable'}
    elif family == 'unsupported_new_color':
        case['control_evidence'] = {'absent_input_color': 9,
                                    'reason': 'closed DSL cannot introduce an absent color'}
    case['public_sha256'] = _digest(task, receipt)
    case['sha256'] = _digest(case, receipt)
    case['costs'] = {'generation': generation.snapshot(), 'oracle': oracle.snapshot(),
                     'receipt': receipt.snapshot()}
    return case


def public_task(case, *, ledger=None):
    """Copy only demonstrations and query inputs; no labels, ids or witnesses."""
    ledger = _ledger(ledger)
    task = case['task']
    ledger.consume('public_copy_cells', sum(sum(map(len, p[k])) for p in task['train']
                                         for k in ('input', 'output'))
                   + sum(sum(map(len, p['input'])) for p in task['test']))
    return {'train': [{'input': deepcopy(p['input']), 'output': deepcopy(p['output'])}
                      for p in task['train']],
            'test': [{'input': deepcopy(p['input'])} for p in task['test']]}


def score_result(case, result, *, ledger=None):
    """Score whole cases, with independent exactness and control recognition."""
    ledger = _ledger(ledger)
    status = result['status']
    if status not in ('solved', *ABSTENTIONS):
        raise RuntimeError('solver instrument error: ' + str(status))
    predictions = result.get('predictions')
    if status != 'solved':
        if predictions != []:
            raise RuntimeError('abstention emitted predictions')
        outcome = 'abstention'
    else:
        if result.get('test_verified') is not False:
            raise RuntimeError('solver claimed query verification')
        ledger.consume('judge_reference_cells', sum(sum(map(len, g)) for g in case['expected']))
        valid = (type(predictions) is list and len(predictions) == len(case['expected'])
                 and all(type(g) is list and all(type(r) is list and
                         all(type(c) is int and 0 <= c <= 9 for c in r) for r in g)
                         for g in predictions))
        outcome = 'exact' if valid and predictions == case['expected'] else 'wrong'
    category = case['category']
    control = category != 'supported'
    return {'outcome': outcome, 'false_commitment': control and status == 'solved',
            'control_pass': ((category == 'ambiguous_control' and status == 'ambiguous')
                             or (category == 'unsupported_control' and status == 'unsolved'))
                            if control else None}


def _source_identity(ledger):
    root = Path(__file__).resolve().parents[3]
    paths = [f'simulation/src/echo5/{name}.py' for name in (
        '__init__', 'budget', 'concepts', 'grounding', 'legacy', 'programs', 'solver',
        'trace', 'transfer', 'transfer_independent')]
    paths += ['__init__.py', 'seed/__init__.py', 'seed/dsl.py', 'seed/learn.py',
              'seed/refinement.py', 'seed/relational_dsl.py']
    files = {}
    for path in sorted(paths):
        raw = (root / path).read_bytes()
        ledger.consume('source_read_hash_bytes', 2*len(raw))
        files[path] = hashlib.sha256(raw).hexdigest()
    return {'files': files, 'sha256': _digest(files, ledger)}


def _seed(base, arm, family, index, ledger):
    key = _digest(['transfer-independent-v1', base, arm, family, index], ledger)
    return int(key[:16], 16) % 2**63


def _sum_costs(receipts):
    stages = ('generation', 'oracle', 'template_generation_and_oracle',
              'receipt', 'solve', 'evaluation')
    result = {}
    for stage in stages:
        values = [r['costs'][stage] for r in receipts if r['costs'].get(stage) is not None]
        if not values:
            result[stage] = None
            continue
        counts = Counter()
        for value in values:
            counts.update(value['counts'])
        result[stage] = {'used': sum(v['used'] for v in values), 'counts': dict(sorted(counts.items()))}
    return result


def _summary(receipts):
    n = len(receipts)
    counts = Counter(r['outcome'] for r in receipts)
    return {'cases': n, **{key: counts[key] for key in ('exact', 'abstention', 'wrong')},
            'exact_rate': counts['exact']/n if n else None,
            'coverage': (counts['exact']+counts['wrong'])/n if n else None,
            'statuses': dict(sorted(Counter(r['result']['status'] for r in receipts).items())),
            'control_pass': sum(r['control_pass'] is True for r in receipts),
            'false_commitment': sum(r['false_commitment'] for r in receipts),
            'costs': _sum_costs(receipts)}


def run_benchmark(*, seed=2400000, cases_per_family=3, budget=2000000, journal=None):
    """Return a JSON-serializable research report, without artifact writes.

    ``budget`` is per solve; setup/oracle/evaluation are separately metered.
    An optional existing Recorder receives factual solver events. No campaign,
    historical contract, learned library, or witness is supplied to the actor.
    """
    _integer(seed, 'seed', 0, 2**63-1)
    _integer(cases_per_family, 'cases_per_family', 1, 64)
    _integer(budget, 'budget', 0, 100_000_000)
    from . import solver, transfer

    preparation = _ledger(None)
    sources = _source_identity(preparation)
    settings = {'relational': True, 'hierarchical': True, 'learn': False,
                'library': None, 'cache_policy': 'interned',
                'synthesis': {'max_depth': 4, 'beam_width': 24, 'max_candidates': 12000,
                              'grammar': None}}
    report = {'schema': SCHEMA, 'mode': 'development_research',
              'config': {'seed': seed, 'cases_per_family': cases_per_family, 'budget': budget,
                         'demonstrations': 3, 'queries': 2},
              'runtime': {'python': platform.python_version(), 'implementation': platform.python_implementation()},
              'sources': sources,
              'comparison': {'design': 'independent_samples_not_paired',
                             'families': list(COMPARABLE_FAMILIES), 'deltas': {}},
              'cost_contract': 'logical counters, not CPU time, FLOPs or energy; stage units differ'}
    for arm, families in (('independent', FAMILIES), ('template', COMPARABLE_FAMILIES)):
        receipts = []
        for family in families:
            for index in range(cases_per_family):
                case_seed = _seed(seed, arm, family, index, preparation)
                if arm == 'independent':
                    case = make_case(case_seed, family)
                    costs = deepcopy(case['costs'])
                    costs['template_generation_and_oracle'] = None
                else:
                    # This API constructs labels directly. Do not call its
                    # validate_witness, run_benchmark, contract or acquisition.
                    combined = _ledger(None)
                    case = transfer.make_case(case_seed, family, split='development',
                                              budget=combined, demonstrations=3, queries=2)
                    costs = {'generation': None, 'oracle': None, 'receipt': None,
                             'template_generation_and_oracle': combined.snapshot()}
                evaluation, work = _ledger(None), Budget(budget)
                task = public_task(case, ledger=evaluation)
                if _digest(task, evaluation) != case['public_sha256']:
                    raise RuntimeError('public task differs from generator receipt')
                if journal is not None:
                    journal.write(kind='transfer_case', arm=arm, family=family,
                                  seed=case_seed, public_sha256=case['public_sha256'])
                result = solver.solve(task, budget=work, **deepcopy(settings), journal=journal)
                if (result['metrics']['used'] != work.used
                        or result['metrics']['counts'] != work.counts
                        or sum(work.counts.values()) != work.used):
                    raise RuntimeError('solver work receipt mismatch')
                score = score_result({'category': _category(family), 'expected': case['expected']},
                                     result, ledger=evaluation)
                costs.update(solve=work.snapshot(), evaluation=evaluation.snapshot())
                receipts.append({'case': case, 'result': result, **score, 'costs': costs})
                if journal is not None:
                    journal.write(kind='transfer_evaluation', arm=arm, family=family,
                                  seed=case_seed, **score, solve_used=work.used)
        report[arm] = {'solver_settings': {**deepcopy(settings), 'budget': budget},
                       'families': {f: _summary([r for r in receipts if r['case']['family'] == f])
                                    for f in families},
                       'by_category': {category: _summary([r for r in receipts
                                        if _category(r['case']['family']) == category])
                                       for category in ('supported', 'ambiguous_control', 'unsupported_control')},
                       'receipts': receipts}
    for family in COMPARABLE_FAMILIES:
        a, b = (report[arm]['families'][family]['exact_rate'] for arm in ('independent', 'template'))
        report['comparison']['deltas'][family] = {'independent_minus_template_exact_rate': a-b,
                                                'cases_per_arm': cases_per_family}
    if _source_identity(preparation) != sources:
        raise RuntimeError('source changed during benchmark; discard partial run')
    report['preparation_cost'] = preparation.snapshot()
    report['instrument_valid'] = True
    return report
