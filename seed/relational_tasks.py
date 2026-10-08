"""Private synthetic judges independent of REL-DSL executor. Never passed to actor."""
from copy import deepcopy
import random


FAMILIES = ('rotate', 'paint', 'stamp', 'compose', 'view', 'compose_view')


def rotate(g):
    return [list(r) for r in zip(*g[::-1])]


def example(family, rng, index):
    size = 12 + 2*(index % 2)
    colors = rng.sample(range(1, 10), 4)
    if family == 'rotate':
        h, w = 5+index % 2, 7+index % 2
        g = [[0]*w for _ in range(h)]
        for y, x in ((1, 1), (1, 2), (2, 1), (3, 1)):
            g[y][x] = colors[0]
        return {'input': g, 'output': rotate(rotate(g))}
    k = 3 + index % 2
    shape = [(i, 0) for i in range(k)] + [(k-1, j) for j in range(1, k)]
    origin = (1, 1 + rng.randrange(2))
    source = [(origin[0]+y, origin[1]+x) for y, x in shape]
    if family in ('view', 'compose_view'):
        source = [(1, 6), (1, 7), (2, 6)]
        targets = [[(6+y, 1+x) for y, x in shape], [(8, 8)]]
    else:
        targets = [[(size-4, size-4)], [(size-4, 1)]]
    if index >= 3:
        # Query scenes contain one more target than the acquisition examples.
        targets.append([(4, size-4)] if family in ('view','compose_view') else [(1, size-4)])
    g = [[0]*size for _ in range(size)]
    for y, x in source:
        g[y][x] = colors[0]
    for i, target in enumerate(targets):
        for y, x in target:
            g[y][x] = colors[i+1]
    out = deepcopy(g)
    if family in ('paint', 'view', 'compose_view'):
        for target in targets:
            for y, x in target:
                out[y][x] = colors[0]
    elif family == 'stamp':
        for target in targets:
            for y, x in target:
                out[y][x] = 0
            oy, ox = target[0]
            for dy, dx in shape:
                if oy+dy >= size or ox+dx >= size:
                    raise ValueError('generator frame too small')
                out[oy+dy][ox+dx] = colors[0]
    elif family == 'compose':
        out = [[colors[0] if (y, x) in shape else 0 for x in range(k)] for y in range(k)]
        out = rotate(out)
    else:
        raise ValueError('unknown generator family')
    if family in ('view', 'compose_view'):
        # Development and confirmation both cover directions; the memorized
        # schema must bind its roles again after color/size/location changes.
        turns = 1 if family == 'view' else 3
        for _ in range(turns):
            g, out = rotate(g), rotate(out)
        if family == 'compose_view':
            out = rotate(out)
    return {'input': g, 'output': out}


def task(family, seed):
    rng = random.Random(str(seed)+'/'+family)
    pairs = [example(family, rng, i) for i in range(5)]
    return {'train': pairs[:3], 'test': pairs[3:]}


def ambiguous(seed):
    rng = random.Random(seed)
    colors = rng.sample(range(1, 10), 3)
    train = [{'input': [[c]*n for _ in range(n)], 'output': [[c]*n for _ in range(n)]}
             for c, n in zip(colors, (2, 3, 4))]
    g = [[0, colors[0], 0], [colors[0], colors[0], 0], [0, 0, 0]]
    out = rotate(rotate(g)) if seed % 2 else g
    return {'train': train, 'test': [{'input': g, 'output': out}]}


def correct(result, private):
    value = result['predictions']
    expected = tuple(tuple(tuple(row) for row in p['output']) for p in private['test'])
    return value is not None and tuple(tuple(tuple(r) for r in g) for g in value) == expected
