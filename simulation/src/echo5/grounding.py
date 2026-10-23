"""Grounded roles on the canonical SEED objects; no learned coordinates/colors."""
from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType

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


@dataclass(frozen=True)
class _Failure:
    # Never retain an exception/traceback (which could retain an entire solve).
    args: tuple


class AnalysisCache:
    """Optional analysis reuse for one solve and one Budget; no query answers.

    Identity keys retain their exact owners. Only strictly validated immutable
    grids and canonical scenes produced here are eligible; mutable public rows
    are validated anew. Equal but distinct grids may miss, never alias by hash.

    Both limits cover all entries, including scene identity aliases. Cell units
    count retained input/output cells, feature coordinates, relation references,
    binding target keys, and one owner reference per entry. There is no eviction:
    new entries that exceed either cap run uncached. Key hashing, lookups, writes and retention
    are charged before the corresponding work/mutation. Discard after a solve.
    """
    def __init__(self, budget, *, max_entries=4096, max_cells=250_000):
        if any(type(n) is not int or n < 0 for n in (max_entries, max_cells)):
            raise ValueError('analysis limits must be nonnegative integers')
        self.budget = budget
        self.max_entries, self.max_cells = max_entries, max_cells
        self._entries = {}
        self._retained_cells = 0

    @property
    def entry_count(self):
        return len(self._entries)

    @property
    def retained_cells(self):
        return self._retained_cells

    def _check_budget(self, budget):
        if budget is not self.budget:
            raise ValueError('analysis belongs to another budget')

    def _lookup(self, key, owner):
        # Include the nested ordered target IDs in a binding key's hash work.
        # No key hashes grids or dataclasses by traversing their cells.
        self.budget.consume('analysis_key_units', len(key) + self._target_key_size(key))
        self.budget.consume('analysis_lookups')
        entry = self._entries.get(key)
        return entry if entry is not None and entry[0] is owner else None

    def _remember(self, key, owner, value, cells=0):
        target_keys = self._target_key_size(key)
        cells += 1 + target_keys  # Owner reference and variable-size target ID storage.
        if self.entry_count >= self.max_entries or self.retained_cells + cells > self.max_cells:
            return False
        self.budget.consume('analysis_key_units', len(key) + target_keys)
        self.budget.consume('analysis_writes')
        self.budget.consume('analysis_retained_cells', cells)
        self._entries[key] = (owner, value)
        self._retained_cells += cells
        return True

    @staticmethod
    def _target_key_size(key):
        return sum(len(part) for part in key if type(part) is tuple)

    @staticmethod
    def _value(entry):
        value = entry[1]
        if isinstance(value, _Failure):
            raise ValueError(*value.args)
        return value

    def _memo(self, key, owner, compute, size=lambda value: 0):
        entry = self._lookup(key, owner)
        if entry is not None:
            return self._value(entry)
        if self.entry_count >= self.max_entries or self.retained_cells >= self.max_cells:
            return compute()
        try:
            value = compute()
        except ValueError as exc:
            self._remember(key, owner, _Failure(exc.args))
            raise
        self._remember(key, owner, value, size(value))
        return value

    def _immutable_error_input(self, rows):
        # Failed validation may still be memoized, but never retain nested
        # mutable values, subclasses, or unbounded malformed input graphs.
        if type(rows) is not tuple or len(rows) > 30:
            return False
        self.budget.consume('analysis_row_checks', len(rows))
        if any(type(row) is not tuple or len(row) > 30 for row in rows):
            return False
        self.budget.consume('analysis_cell_checks', sum(map(len, rows)))
        return all(type(v) in (int, bool, float) for row in rows for v in row)

    def _grid(self, rows, budget):
        self._check_budget(budget)
        key = ('grid', id(rows))
        entry = self._lookup(key, rows)
        if entry is not None:
            return self._value(entry)
        try:
            value = grid(rows, budget)
        except ValueError as exc:
            if self._immutable_error_input(rows):
                self._remember(key, rows, _Failure(exc.args), sum(map(len, rows)))
            raise
        if type(rows) is tuple:
            budget.consume('analysis_row_checks', len(rows))
            if all(type(row) is tuple for row in rows):
                self._remember(key, rows, rows, len(rows) * len(rows[0]))
                return rows
        return value

    def _ground(self, rows, budget):
        validated = self._grid(rows, budget)
        # Only registered grids may own further retained analysis. This also
        # makes zero/tiny caps and mutable inputs use the canonical fallback.
        if self._lookup(('grid', id(validated)), validated) is None:
            return _rel.objects(validated, budget)
        def size(scene):
            budget.consume('analysis_size_objects', len(scene.objects))
            return len(scene.grid) * len(scene.grid[0]) + sum(len(o.cells) for o in scene.objects)
        scene = self._memo(('ground', id(validated)), validated,
                           lambda: _rel.objects(validated, budget), size)
        # An alias is an entry too; it keeps the exact scene alive, and only
        # scenes from our canonical segmentation get this trusted identity.
        key = ('scene', id(scene))
        if self._lookup(key, scene) is None:
            # A saturated ground write must not leave an unaccounted scene.
            if self._lookup(('ground', id(validated)), validated) is not None:
                self._remember(key, scene, scene)
        return scene

    def _scene(self, scene, kind, args, compute, size=lambda value: 0):
        if self._lookup(('scene', id(scene)), scene) is None:
            return compute()
        return self._memo((kind, id(scene), *args), scene, compute, size)


def grid(rows, budget, *, analysis=None):
    """Bounded strict input validation (unlike dsl.G, never coerce colors)."""
    if analysis is not None:
        return analysis._grid(rows, budget)
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


def ground(rows, budget, *, analysis=None):
    """Border-majority background, four-connected monochrome objects (1..32)."""
    if analysis is not None:
        return analysis._ground(rows, budget)
    return _rel.objects(grid(rows, budget), budget)


def _features(scene, budget, *, analysis=None):
    if analysis is not None:
        analysis._check_budget(budget)
        return analysis._scene(scene, 'features', (),
                               lambda: MappingProxyType(_features(scene, budget)),
                               lambda boxes: 5 * len(boxes))
    if not isinstance(scene, Scene):
        raise ValueError('typed Scene required')
    budget.consume('role_objects', len(scene.objects))
    budget.consume('feature_cells', sum(len(o.cells) for o in scene.objects))
    return {o: (min(y for y, x in o.cells), min(x for y, x in o.cells),
                max(y for y, x in o.cells), max(x for y, x in o.cells))
            for o in scene.objects}


def select(scene, role, budget, *, analysis=None):
    """Bind one role, refusing every tie, including multiple singletons."""
    budget.consume('role_attempts')
    if role not in ROLES:
        raise ValueError('unknown role')
    if analysis is not None:
        analysis._check_budget(budget)
        if type(role) is str:
            return analysis._scene(scene, 'role', (role,),
                                   lambda: _select(scene, role, budget, analysis), lambda obj: 1)
    return _select(scene, role, budget, analysis)


def _select(scene, role, budget, analysis):
    boxes = _features(scene, budget, analysis=analysis)
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


def targets(scene, source, relation, budget, *, analysis=None):
    """Directions locate targets relative to source using strict bounding boxes."""
    budget.consume('relation_attempts')
    if not isinstance(scene, Scene) or source not in scene.objects or relation not in ALL_RELATIONS:
        raise ValueError('scene object and known relation required')
    if analysis is not None:
        analysis._check_budget(budget)
        budget.consume('analysis_source_refs', len(scene.objects))
        if type(relation) is str and any(source is obj for obj in scene.objects):
            return analysis._scene(scene, 'targets', (id(source), relation),
                                   lambda: _targets(scene, source, relation, budget, analysis), len)
    return _targets(scene, source, relation, budget, analysis)


def _targets(scene, source, relation, budget, analysis):
    if relation in BASE_RELATIONS:
        if analysis is None or type(relation) is not str:
            edges = _rel.relate(scene, relation, budget).edges
        else:
            edges = analysis._scene(scene, 'relations', (relation,),
                                    lambda: _rel.relate(scene, relation, budget).edges,
                                    lambda edges: 2 * len(edges))
        return tuple(b for a, b in edges if a == source)
    boxes = _features(scene, budget, analysis=analysis)
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


def apply_relation(rows, *, role, relation, effect, budget, analysis=None):
    """Grid -> Scene -> unique Binding -> canonical Edits -> Grid."""
    budget.consume('relational_attempts')
    if effect not in EFFECTS or relation not in ALL_RELATIONS:
        raise ValueError('unknown relation/effect')
    if effect == 'extract' and relation != 'all':
        raise ValueError('extract uses the source and relation all')
    scene = ground(rows, budget, analysis=analysis)
    source = select(scene, role, budget, analysis=analysis)
    selected = () if effect == 'extract' else targets(scene, source, relation, budget, analysis=analysis)
    if analysis is not None and type(effect) is str:
        budget.consume('analysis_binding_refs', 1 + len(selected))
        key = (id(source), tuple(id(obj) for obj in selected), effect)
        return analysis._scene(scene, 'binding_output', key,
                               lambda: _render_relation(scene, source, selected, effect, budget),
                               lambda result: len(result) * len(result[0]))
    return _render_relation(scene, source, selected, effect, budget)


def _render_relation(scene, source, selected, effect, budget):
    # Roles and relation names may alias, but this canonical binding determines
    # every edit and frame. Mapping/rendering stay shared with the uncached path.
    binding = _rel.Binding(scene, source, selected)
    edits = _rel.map_objects(binding, 'paint' if effect == 'recolor' else effect, budget)
    return _rel.render(scene, edits, 'source' if effect == 'extract' else 'original', budget)


def transform_object(rows, *, role, effect, budget, analysis=None):
    """Morphology of one unambiguous canonical object, preserving other objects.

    Outline removes cells having all four neighbours in the same object.
    Fill covers the object's bounding rectangle, rejecting any foreign cell.
    Neither operation infers hidden surfaces or coerces ambiguous roles.
    """
    budget.consume('object_transform_attempts')
    if effect not in OBJECT_EFFECTS:
        raise ValueError('unknown object effect')
    scene = ground(rows, budget, analysis=analysis)
    source = select(scene, role, budget, analysis=analysis)
    if analysis is not None and type(effect) is str:
        budget.consume('analysis_binding_refs')
        return analysis._scene(scene, 'object_output', (id(source), effect),
                               lambda: _transform_object(scene, source, effect, budget, analysis),
                               lambda result: len(result) * len(result[0]))
    return _transform_object(scene, source, effect, budget, analysis)


def _transform_object(scene, source, effect, budget, analysis):
    budget.consume('object_cell_index', len(source.cells))
    cells = set(source.cells)
    edits = []
    if effect == 'outline':
        budget.consume('outline_neighbours', 4 * len(cells))
        for y, x in source.cells:
            if all(p in cells for p in ((y-1, x), (y+1, x), (y, x-1), (y, x+1))):
                edits.append((y, x, scene.background))
    else:
        top, left, bottom, right = _features(scene, budget, analysis=analysis)[source]
        budget.consume('fill_box_cells', (bottom-top+1) * (right-left+1))
        for y in range(top, bottom+1):
            for x in range(left, right+1):
                if (y, x) not in cells and scene.grid[y][x] != scene.background:
                    raise ValueError('fill would overwrite another object')
                edits.append((y, x, source.color))
    return _rel.render(scene, _rel.Edits(scene, tuple(edits), source), 'original', budget)


def pack_objects(rows, *, axis, budget, analysis=None):
    """Pack objects in descending area order with a one-cell background gap.

    Equal areas abstain instead of smuggling in coordinate/color tie breakers.
    Objects retain shape and color. All objects share the output's top/left
    baseline; no stretching or overlapping bounding boxes is allowed.
    """
    budget.consume('pack_attempts')
    if axis not in PACK_AXES:
        raise ValueError('unknown packing axis')
    scene = ground(rows, budget, analysis=analysis)
    boxes = _features(scene, budget, analysis=analysis)
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
