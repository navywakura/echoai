"""Grounded roles on the canonical SEED objects; no learned coordinates/colors."""
from collections import Counter

from .legacy import module

_rel = module('seed.relational_dsl')
Object, Scene = _rel.Object, _rel.Scene

ROLES = ('largest', 'smallest', 'topmost', 'bottommost', 'leftmost',
         'rightmost', 'unique_shape', 'unique_color')
BASE_ROLES = ('largest', 'smallest', 'topmost')
RELATIONS = ('all', 'same_shape', 'same_color', 'same_row', 'same_col',
             'left', 'right', 'above', 'below')
BASE_RELATIONS = ('all', 'same_shape', 'same_color', 'same_row', 'same_col')
# Opt-in search additions. Keep the original candidate vocabulary unchanged.
EXTENDED_RELATIONS = ('inside', 'contains', 'same_size')
ALL_RELATIONS = RELATIONS + EXTENDED_RELATIONS
EFFECTS = ('recolor', 'erase', 'stamp', 'extract')
OBJECT_EFFECTS = ('outline', 'fill_box')
PACK_AXES = ('row', 'column')


def grid(rows, budget):
    """Bounded strict input validation (unlike dsl.G, never coerce colors)."""
    budget.consume('grid_validation')
    if type(rows) not in (list, tuple) or not 1 <= len(rows) <= 30:
        raise ValueError('grid needs one to 30 rows')
    if any(type(row) not in (list, tuple) or not 1 <= len(row) <= 30 for row in rows):
        raise ValueError('grid needs one to 30 columns')
    budget.consume('validate_cells', sum(map(len, rows)))
    if any(len(row) != len(rows[0]) for row in rows):
        raise ValueError('ragged grid')
    if any(type(v) is not int or not 0 <= v <= 9 for row in rows for v in row):
        raise ValueError('integer colors 0..9 required')
    return tuple(tuple(row) for row in rows)


def ground(rows, budget):
    """Border-majority background, four-connected monochrome objects (1..32)."""
    return _rel.objects(grid(rows, budget), budget)


def _features(scene, budget):
    if not isinstance(scene, Scene):
        raise ValueError('typed Scene required')
    budget.consume('role_objects', len(scene.objects))
    budget.consume('feature_cells', sum(len(o.cells) for o in scene.objects))
    return {o: (min(y for y, x in o.cells), min(x for y, x in o.cells),
                max(y for y, x in o.cells), max(x for y, x in o.cells))
            for o in scene.objects}


def select(scene, role, budget):
    """Bind one role, refusing every tie, including multiple singletons."""
    budget.consume('role_attempts')
    if role not in ROLES:
        raise ValueError('unknown role')
    boxes = _features(scene, budget)
    if role.startswith('unique_'):
        values = {o: o.shape if role == 'unique_shape' else o.color for o in scene.objects}
        counts = Counter(values.values())
        selected = [o for o in scene.objects if counts[values[o]] == 1]
    else:
        scores = {
            'largest': lambda o: -len(o.cells), 'smallest': lambda o: len(o.cells),
            'topmost': lambda o: boxes[o][0], 'bottommost': lambda o: -boxes[o][2],
            'leftmost': lambda o: boxes[o][1], 'rightmost': lambda o: -boxes[o][3],
        }
        key = scores[role]
        best = min(map(key, scene.objects))
        selected = [o for o in scene.objects if key(o) == best]
    if len(selected) != 1:
        raise ValueError('source role is ambiguous')
    return selected[0]


def targets(scene, source, relation, budget):
    """Directions locate targets relative to source using strict bounding boxes."""
    budget.consume('relation_attempts')
    if not isinstance(scene, Scene) or source not in scene.objects or relation not in ALL_RELATIONS:
        raise ValueError('scene object and known relation required')
    if relation in BASE_RELATIONS:
        edges = _rel.relate(scene, relation, budget).edges
        return tuple(b for a, b in edges if a == source)
    boxes = _features(scene, budget)
    budget.consume('object_pairs', len(scene.objects))
    a = boxes[source]
    def matches(obj):
        b = boxes[obj]
        if relation == 'same_size':
            return len(source.cells) == len(obj.cells)
        if relation == 'inside':
            return a[0] < b[0] and a[1] < b[1] and b[2] < a[2] and b[3] < a[3]
        if relation == 'contains':
            return b[0] < a[0] and b[1] < a[1] and a[2] < b[2] and a[3] < b[3]
        return {'left': b[3] < a[1], 'right': b[1] > a[3],
                'above': b[2] < a[0], 'below': b[0] > a[2]}[relation]
    return tuple(o for o in scene.objects if o != source and matches(o))


def apply_relation(rows, *, role, relation, effect, budget):
    """Grid -> Scene -> unique Binding -> canonical Edits -> Grid."""
    budget.consume('relational_attempts')
    if effect not in EFFECTS or relation not in ALL_RELATIONS:
        raise ValueError('unknown relation/effect')
    if effect == 'extract' and relation != 'all':
        raise ValueError('extract uses the source and relation all')
    scene = ground(rows, budget)
    source = select(scene, role, budget)
    selected = () if effect == 'extract' else targets(scene, source, relation, budget)
    binding = _rel.Binding(scene, source, selected)
    edits = _rel.map_objects(binding, 'paint' if effect == 'recolor' else effect, budget)
    return _rel.render(scene, edits, 'source' if effect == 'extract' else 'original', budget)


def transform_object(rows, *, role, effect, budget):
    """Morphology of one unambiguous canonical object, preserving other objects.

    Outline removes cells having all four neighbours in the same object.
    Fill covers the object's bounding rectangle, rejecting any foreign cell.
    Neither operation infers hidden surfaces or coerces ambiguous roles.
    """
    budget.consume('object_transform_attempts')
    if effect not in OBJECT_EFFECTS:
        raise ValueError('unknown object effect')
    scene = ground(rows, budget)
    source = select(scene, role, budget)
    budget.consume('object_cell_index', len(source.cells))
    cells = set(source.cells)
    edits = []
    if effect == 'outline':
        budget.consume('outline_neighbours', 4 * len(cells))
        for y, x in source.cells:
            if all(p in cells for p in ((y-1, x), (y+1, x), (y, x-1), (y, x+1))):
                edits.append((y, x, scene.background))
    else:
        top, left, bottom, right = _features(scene, budget)[source]
        budget.consume('fill_box_cells', (bottom-top+1) * (right-left+1))
        for y in range(top, bottom+1):
            for x in range(left, right+1):
                if (y, x) not in cells and scene.grid[y][x] != scene.background:
                    raise ValueError('fill would overwrite another object')
                edits.append((y, x, source.color))
    return _rel.render(scene, _rel.Edits(scene, tuple(edits), source), 'original', budget)


def pack_objects(rows, *, axis, budget):
    """Pack objects in descending area order with a one-cell background gap.

    Equal areas abstain instead of smuggling in coordinate/color tie breakers.
    Objects retain shape and color. All objects share the output's top/left
    baseline; no stretching or overlapping bounding boxes is allowed.
    """
    budget.consume('pack_attempts')
    if axis not in PACK_AXES:
        raise ValueError('unknown packing axis')
    scene = ground(rows, budget)
    boxes = _features(scene, budget)
    budget.consume('pack_order_work', len(scene.objects) * max(1, len(scene.objects).bit_length()))
    sizes = [len(o.cells) for o in scene.objects]
    if len(set(sizes)) != len(sizes):
        raise ValueError('packing order is ambiguous')
    ordered = sorted(scene.objects, key=lambda o: -len(o.cells))
    heights = [boxes[o][2] - boxes[o][0] + 1 for o in ordered]
    widths = [boxes[o][3] - boxes[o][1] + 1 for o in ordered]
    height = max(heights) if axis == 'row' else sum(heights) + len(ordered)-1
    width = max(widths) if axis == 'column' else sum(widths) + len(ordered)-1
    if height > 30 or width > 30:
        raise ValueError('packed output exceeds grid bounds')
    budget.consume('pack_render_cells', height * width)
    result = [[scene.background] * width for _ in range(height)]
    offset = 0
    for obj, h, w in zip(ordered, heights, widths):
        budget.consume('pack_copy_cells', len(obj.cells))
        top, left, _, _ = boxes[obj]
        for y, x in obj.cells:
            yy, xx = y-top, x-left
            result[yy + (offset if axis == 'column' else 0)][xx + (offset if axis == 'row' else 0)] = obj.color
        offset += (h if axis == 'column' else w) + 1
    return tuple(tuple(row) for row in result)
