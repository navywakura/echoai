"""Evaluator-owned synthetic scenes, rendered without using the actor's DSL.

The witness is private to the evaluator. A solver sees only public_task(case).
These families measure transfer inside this generator, not official ARC.
"""

import copy
import hashlib
import json
import random

FAMILIES = ('right_recolor', 'above_recolor', 'extract_rotate', 'rotate')


def _rotate(rows):
    return [[rows[len(rows) - 1 - x][y] for x in range(len(rows))]
            for y in range(len(rows[0]))]


def _example(rng, family, split, easy=False):
    novel = split == 'confirmation'
    height, width = (rng.randrange(15, 19), rng.randrange(16, 21)) if novel else (12, 14)
    colors = rng.sample([5, 6, 7, 8, 9] if novel else [1, 2, 3, 4], 3)
    y, x = rng.randrange(4, height - 5), rng.randrange(4, width - 6)
    shapes = (((0, 0), (1, 0), (1, 1)), ((0, 0), (0, 1), (1, 1), (2, 1)))
    shape = shapes[rng.randrange(len(shapes))]
    rows = [[0 for _ in range(width)] for _ in range(height)]
    for dy, dx in shape:
        rows[y + dy][x + dx] = colors[0]
    positions = [(y + rng.randrange(-1, 2), x + 4)]
    if easy and family == 'above_recolor':
        positions = [(y - 3, x + rng.randrange(-1, 2))]
    if not easy:
        positions += [(y - 3, x), (y + 4, x), (y, x - 3)]
    for i, (oy, ox) in enumerate(positions):
        rows[oy][ox] = colors[1 + i % 2]
    expected = copy.deepcopy(rows)
    if family == 'right_recolor':
        for oy, ox in positions:
            if ox > x + max(dx for _, dx in shape):
                expected[oy][ox] = colors[0]
    elif family == 'above_recolor':
        for oy, ox in positions:
            if oy < y:
                expected[oy][ox] = colors[0]
    elif family == 'extract_rotate':
        crop = [[0] * (1 + max(dx for _, dx in shape)) for _ in range(1 + max(dy for dy, _ in shape))]
        for dy, dx in shape:
            crop[dy][dx] = colors[0]
        expected = _rotate(crop)
    elif family == 'rotate':
        expected = _rotate(rows)
    else:
        raise ValueError('unknown family')
    return {'input': rows, 'output': expected}


def make_case(seed, family, *, split='development', budget=None, easy=False):
    if family not in FAMILIES or split not in ('development', 'acquisition', 'confirmation'):
        raise ValueError('unknown family or split')
    if type(seed) is not int or type(easy) is not bool:
        raise ValueError('integer seed and boolean difficulty required')
    if budget:
        # Upper bound covers all four rendered examples, including discarded cases.
        budget.consume('generate_cells', 4 * 2 * 19 * 21)
    rng = random.Random(seed)
    train = [_example(rng, family, split, easy) for _ in range(3)]
    query = _example(rng, family, split, easy)
    if family in ('right_recolor', 'above_recolor'):
        witness = {'steps': [{'op': 'relate', 'role': 'largest',
                             'relation': family.split('_')[0], 'effect': 'recolor'}]}
    elif family == 'extract_rotate':
        witness = {'steps': [{'op': 'relate', 'role': 'largest', 'relation': 'all', 'effect': 'extract'},
                             {'op': 'rot90'}]}
    else:
        witness = {'steps': [{'op': 'rot90'}]}
    task = {'train': train, 'test': [{'input': query['input']}]}
    raw = json.dumps(task, sort_keys=True, separators=(',', ':'))
    return {'id': hashlib.sha256(raw.encode()).hexdigest(), 'family': family,
            'split': split, 'seed': seed, 'task': task, 'expected': [query['output']],
            'witness': witness}


def public_task(case):
    return copy.deepcopy({'train': case['task']['train'],
                          'test': [{'input': ex['input']} for ex in case['task']['test']]})


def validate_witness(case, budget):
    from .programs import execute
    if len(case['expected']) != len(case['task']['test']):
        return False
    pairs = case['task']['train'] + [dict(input=ex['input'], output=expected)
                                    for ex, expected in zip(case['task']['test'], case['expected'])]
    try:
        for pair in pairs:
            prediction = execute(case['witness'], pair['input'], budget=budget)
            if [list(row) for row in prediction] != pair['output']:
                return False
    except (ValueError, TypeError):
        return False
    return True
