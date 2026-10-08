"""REL-DSL-1: bounded typed object programs; no task identifiers or test labels."""
from __future__ import annotations

from dataclasses import dataclass, field
from collections import Counter

from echoai.seed import dsl
from echoai.seed.refinement import RefinementLibrary, grid


class Exhausted(Exception):
    pass


@dataclass
class Work:
    limit: int = 500_000
    used: int = 0
    counts: dict = field(default_factory=dict)

    def add(self, kind, n=1):
        if type(n) is not int or n < 0:
            raise ValueError('nonnegative integer work required')
        if self.used + n > self.limit:
            raise Exhausted('logical work budget exhausted')
        self.used += n
        self.counts[kind] = self.counts.get(kind, 0) + n


@dataclass(frozen=True)
class Object:
    color: int
    cells: tuple

    @property
    def anchor(self):
        return min(y for y, x in self.cells), min(x for y, x in self.cells)

    @property
    def shape(self):
        y, x = self.anchor
        return tuple(sorted((a-y, b-x) for a, b in self.cells))


@dataclass(frozen=True)
class Scene:
    grid: tuple
    background: int
    objects: tuple


@dataclass(frozen=True)
class Relations:
    scene: Scene
    name: str
    edges: tuple


@dataclass(frozen=True)
class Binding:
    scene: Scene
    source: Object
    targets: tuple


@dataclass(frozen=True)
class Edits:
    scene: Scene
    pixels: tuple
    source: Object


SELECTORS = ('largest', 'smallest', 'topmost')
RELATIONS = ('all', 'same_shape', 'same_color', 'same_row', 'same_col')
EFFECTS = ('paint', 'stamp', 'erase')


def objects(g, work, *, background='border', connectivity=4):
    g = grid(g)
    if background not in ('border', 'zero') or connectivity not in (4, 8):
        raise ValueError('unknown segmentation')
    work.add('segment_cells', len(g)*len(g[0]))
    if background == 'zero':
        bg = 0
    else:
        border = list(g[0]) + list(g[-1]) + [r[0] for r in g[1:-1]] + [r[-1] for r in g[1:-1]]
        counts = Counter(border)
        winners = [c for c, n in counts.items() if n == max(counts.values())]
        if len(winners) != 1:
            raise ValueError('ambiguous background')
        bg = winners[0]
    found = tuple(Object(c, tuple(sorted(cells))) for c, cells in dsl.objects(g, bg, connectivity == 8))
    if not found or len(found) > 32:
        raise ValueError('need one to 32 objects')
    return Scene(g, bg, found)


def relate(scene, name, work):
    if not isinstance(scene, Scene) or name not in RELATIONS:
        raise ValueError('typed Scene and known relation required')
    work.add('object_pairs', len(scene.objects)**2)
    edges = []
    for a in scene.objects:
        for b in scene.objects:
            if a == b:
                continue
            same = (name == 'all' or name == 'same_shape' and a.shape == b.shape or
                    name == 'same_color' and a.color == b.color or
                    name == 'same_row' and a.anchor[0] == b.anchor[0] or
                    name == 'same_col' and a.anchor[1] == b.anchor[1])
            if same:
                edges.append((a, b))
    return Relations(scene, name, tuple(edges))


def bind(scene, relations, selector, work):
    if not isinstance(scene, Scene) or not isinstance(relations, Relations) or relations.scene != scene:
        raise ValueError('relations belong to another scene')
    if selector not in SELECTORS:
        raise ValueError('unknown selector')
    work.add('bind_objects', len(scene.objects))
    key = (lambda o: -len(o.cells)) if selector == 'largest' else (lambda o: len(o.cells)) if selector == 'smallest' else (lambda o: o.anchor[0])
    value = min(map(key, scene.objects))
    selected = [o for o in scene.objects if key(o) == value]
    if len(selected) != 1:
        raise ValueError('source role is ambiguous')
    source = selected[0]
    return Binding(scene, source, tuple(b for a, b in relations.edges if a == source))


def map_objects(binding, effect, work):
    if not isinstance(binding, Binding) or effect not in (*EFFECTS, 'extract'):
        raise ValueError('typed binding and known effect required')
    if effect != 'extract' and not binding.targets:
        raise ValueError('no target binding')
    edits = {}
    for obj in binding.targets if effect != 'extract' else ():
        work.add('map_cells', len(obj.cells))
        for p in obj.cells:
            edits[p] = binding.source.color if effect == 'paint' else binding.scene.background
    if effect == 'stamp':
        occupied = {p for obj in binding.scene.objects if obj not in binding.targets for p in obj.cells}
        stamps = {}
        for target in binding.targets:
            y, x = target.anchor
            for dy, dx in binding.source.shape:
                work.add('stamp_cells')
                p = y+dy, x+dx
                if p in occupied or p in stamps:
                    raise ValueError('overlapping stamp')
                stamps[p] = binding.source.color
        edits.update(stamps)
    return Edits(binding.scene, tuple(sorted((y, x, c) for (y, x), c in edits.items())), binding.source)


def render(scene, edits, frame, work):
    if not isinstance(edits, Edits) or edits.scene != scene or frame not in ('original', 'source'):
        raise ValueError('invalid scene/edit/frame')
    if frame == 'source':
        obj = edits.source
        height, width = max(y for y, x in obj.shape)+1, max(x for y, x in obj.shape)+1
        work.add('render_cells', height*width)
        cells = set(obj.shape)
        return tuple(tuple(obj.color if (y, x) in cells else scene.background for x in range(width)) for y in range(height))
    work.add('render_cells', len(scene.grid)*len(scene.grid[0]))
    result = [list(r) for r in scene.grid]
    for y, x, c in edits.pixels:
        if not (0 <= y < len(result) and 0 <= x < len(result[0])):
            raise ValueError('edit outside grid')
        result[y][x] = c
    return grid(result)


def steps():
    return tuple(('rel', selector, relation, effect) for effect in EFFECTS for selector in SELECTORS for relation in RELATIONS) + tuple(('rel', selector, 'all', 'extract') for selector in SELECTORS)


class RelationalLibrary(RefinementLibrary):
    def __init__(self, work=None):
        super().__init__()
        self.work = work or Work(10**12)

    def apply(self, g, item):
        if isinstance(item, (tuple, list)) and item and item[0] == 'rel':
            if len(item) != 4 or tuple(item) not in steps():
                raise ValueError('illegal relational program')
            _, selector, relation, effect = item
            scene = objects(g, self.work)
            relations = relate(scene, relation, self.work)
            binding = bind(scene, relations, selector, self.work)
            edits = map_objects(binding, effect, self.work)
            return render(scene, edits, 'source' if effect == 'extract' else 'original', self.work)
        self.work.add('primitive_cells', len(g)*len(g[0]))
        return super().apply(g, item)
