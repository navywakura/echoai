"""ECHO-SEED · the starting primitives: small, typed Grid -> Grid operations.

A grid is a tuple of tuples of ints 0-9 (hashable, immutable). Colour 0 is background unless an
operation says otherwise. Every primitive either returns a new grid or raises ValueError; the
search treats an error as "this step does not apply". Learned concepts are built only from these.
"""
from collections import Counter, deque

MAX_SIDE = 30


def G(rows):
    g = tuple(tuple(int(v) for v in r) for r in rows)
    if not g or not g[0] or len(g) > MAX_SIDE or len(g[0]) > MAX_SIDE or any(len(r) != len(g[0]) for r in g):
        raise ValueError("bad grid")
    return g


def palette(g):
    return {v for r in g for v in r}


def majority(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


# ---------------------------------------------------------------- geometry

def rot90(g): return G(zip(*g[::-1]))
def rot180(g): return G(r[::-1] for r in g[::-1])
def rot270(g): return G(list(zip(*g))[::-1])
def flipud(g): return G(g[::-1])
def fliplr(g): return G(r[::-1] for r in g)
def transpose(g): return G(zip(*g))


def crop(g):
    bg = majority(g)
    rows = [i for i, r in enumerate(g) if any(v != bg for v in r)]
    cols = [j for j in range(len(g[0])) if any(r[j] != bg for r in g)]
    if not rows:
        raise ValueError("empty")
    return G(r[cols[0]:cols[-1] + 1] for r in g[rows[0]:rows[-1] + 1])


def _scale(g, k): return G([v for v in r for _ in range(k)] for r in g for _ in range(k))


def _down(g, k):
    if len(g) % k or len(g[0]) % k:
        raise ValueError("not divisible")
    return G(r[::k] for r in g[::k])


def up2(g): return _scale(g, 2)
def up3(g): return _scale(g, 3)
def down2(g): return _down(g, 2)
def down3(g): return _down(g, 3)
def tile2x2(g): return G([r * 2 for r in g] * 2)
def tile1x2(g): return G(r * 2 for r in g)
def tile2x1(g): return G(list(g) * 2)
def mirror_h(g): return G(r + r[::-1] for r in g)
def mirror_v(g): return G(list(g) + list(g[::-1]))


def _halves(g, axis):
    if axis == "h":
        w = len(g[0])
        if w % 2 == 0:
            return G(r[: w // 2] for r in g), G(r[w // 2:] for r in g)
        return G(r[: w // 2] for r in g), G(r[w // 2 + 1:] for r in g)        # odd: drop the divider column
    h = len(g)
    if h % 2 == 0:
        return G(g[: h // 2]), G(g[h // 2:])
    return G(g[: h // 2]), G(g[h // 2 + 1:])


def left_half(g): return _halves(g, "h")[0]
def right_half(g): return _halves(g, "h")[1]
def top_half(g): return _halves(g, "v")[0]
def bottom_half(g): return _halves(g, "v")[1]


def sym_h(g):
    """Complete left-right symmetry: a background cell takes its mirror's colour."""
    return G([v if v else m for v, m in zip(r, r[::-1])] for r in g)


def sym_v(g):
    return G([v if v else m for v, m in zip(r, rm)] for r, rm in zip(g, g[::-1]))


def dedupe_rows(g):
    out = [g[0]] + [r for p, r in zip(g, g[1:]) if r != p]
    return G(out)


def dedupe_cols(g): return transpose(dedupe_rows(transpose(g)))


# ---------------------------------------------------------------- objects and physics

def objects(g, bg=0, diagonal=False):
    """Connected components of non-background cells (same colour): list of (colour, cells)."""
    h, w = len(g), len(g[0])
    seen, out = set(), []
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1)) + (((1, 1), (1, -1), (-1, 1), (-1, -1)) if diagonal else ())
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or g[y][x] == bg:
                continue
            c, cells, q = g[y][x], [], deque([(y, x)])
            seen.add((y, x))
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx))
                for dy, dx in steps:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and g[ny][nx] == c:
                        seen.add((ny, nx))
                        q.append((ny, nx))
            out.append((c, cells))
    return out


def _extract(g, cells):
    ys, xs = [y for y, _ in cells], [x for _, x in cells]
    y0, x0 = min(ys), min(xs)
    sub = [[0] * (max(xs) - x0 + 1) for _ in range(max(ys) - y0 + 1)]
    for y, x in cells:
        sub[y - y0][x - x0] = g[y][x]
    return G(sub)


def largest_object(g):
    objs = objects(g)
    if not objs:
        raise ValueError("no objects")
    return _extract(g, max(objs, key=lambda o: len(o[1]))[1])


def smallest_object(g):
    objs = objects(g)
    if not objs:
        raise ValueError("no objects")
    return _extract(g, min(objs, key=lambda o: len(o[1]))[1])


def _gravity(g):                                              # everything non-zero falls down
    h, w = len(g), len(g[0])
    cols = []
    for x in range(w):
        col = [g[y][x] for y in range(h) if g[y][x]]
        cols.append([0] * (h - len(col)) + col)
    return G(zip(*cols))


def gravity_down(g): return _gravity(g)
def gravity_up(g): return flipud(_gravity(flipud(g)))
def gravity_right(g): return rot90(_gravity(rot270(g)))
def gravity_left(g): return rot270(_gravity(rot90(g)))


# ---------------------------------------------------------------- logic between halves (colour out)

def _logic(g, axis, op, c):
    a, b = _halves(g, axis)
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise ValueError("halves differ")
    return G([c if op(bool(x), bool(y)) else 0 for x, y in zip(ra, rb)] for ra, rb in zip(a, b))


# ---------------------------------------------------------------- colour operations

def keep_color(g, c):
    if c not in palette(g):
        raise ValueError("absent")
    return G([v if v == c else 0 for v in r] for r in g)


def remove_color(g, c):
    if c not in palette(g):
        raise ValueError("absent")
    return G([0 if v == c else v for v in r] for r in g)


def fill_bg(g, c): return G([c if v == 0 else v for v in r] for r in g)


def fill_enclosed(g, c):
    """Background cells that cannot reach the border through background become colour c."""
    h, w = len(g), len(g[0])
    q = deque((y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and g[y][x] == 0)
    seen = set(q)
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and g[ny][nx] == 0:
                seen.add((ny, nx))
                q.append((ny, nx))
    out = G([c if (v == 0 and (y, x) not in seen) else v for x, v in enumerate(r)] for y, r in enumerate(g))
    if out == g:
        raise ValueError("nothing enclosed")
    return out


def recolor(g, a, b):
    if a not in palette(g) or a == b:
        raise ValueError("absent")
    return G([b if v == a else v for v in r] for r in g)


def swap(g, a, b):
    if a >= b or a not in palette(g) or b not in palette(g):
        raise ValueError("absent")
    return G([b if v == a else a if v == b else v for v in r] for r in g)


# ---------------------------------------------------------------- S1 · objects (added 2026-09-25)

def _objects_any(g):
    """Multi-colour objects: non-background cells connected in 8 directions, whatever their colour."""
    h, w = len(g), len(g[0])
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if (y, x) in seen or g[y][x] == 0:
                continue
            cells, q = [], deque([(y, x)])
            seen.add((y, x))
            while q:
                cy, cx = q.popleft()
                cells.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and g[ny][nx] != 0:
                            seen.add((ny, nx))
                            q.append((ny, nx))
            out.append(cells)
    return out


def _bbox(cells):
    ys, xs = [y for y, _ in cells], [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


def _crop_box(g, box):
    y0, x0, y1, x1 = box
    return G(r[x0:x1 + 1] for r in g[y0:y1 + 1])


def crop_largest_any(g):
    objs = _objects_any(g)
    if not objs:
        raise ValueError("no objects")
    return _crop_box(g, _bbox(max(objs, key=len)))


def crop_smallest_any(g):
    objs = _objects_any(g)
    if len(objs) < 2:
        raise ValueError("need 2 objects")
    return _crop_box(g, _bbox(min(objs, key=len)))


def crop_unique_color_object(g):
    """The object whose colour appears in exactly one object (the odd one out)."""
    objs = objects(g)
    by_color = Counter(c for c, _ in objs)
    single = [cells for c, cells in objs if by_color[c] == 1]
    if len(single) != 1 or len(objs) < 3:
        raise ValueError("no unique")
    return _crop_box(g, _bbox(single[0]))


def crop_odd_shape(g):
    """The object whose shape (normalised cells) differs from all others."""
    objs = _objects_any(g)
    shapes = []
    for cells in objs:
        y0, x0, _, _ = _bbox(cells)
        shapes.append(tuple(sorted((y - y0, x - x0) for y, x in cells)))
    count = Counter(shapes)
    odd = [cells for cells, sh in zip(objs, shapes) if count[sh] == 1]
    if len(odd) != 1 or len(objs) < 3:
        raise ValueError("no odd shape")
    return _crop_box(g, _bbox(odd[0]))


def _keep(g, cells_keep):
    keep = set(cells_keep)
    return G([v if (y, x) in keep else 0 for x, v in enumerate(r)] for y, r in enumerate(g))


def keep_largest(g):
    objs = _objects_any(g)
    if len(objs) < 2:
        raise ValueError("need 2 objects")
    return _keep(g, max(objs, key=len))


def remove_largest(g):
    objs = _objects_any(g)
    if len(objs) < 2:
        raise ValueError("need 2 objects")
    big = max(objs, key=len)
    return _keep(g, [c for o in objs if o is not big for c in o])


def denoise(g):
    """Remove isolated single cells (noise) in 8-connectivity."""
    objs = _objects_any(g)
    out = _keep(g, [c for o in objs if len(o) > 1 for c in o])
    if out == g:
        raise ValueError("no noise")
    return out


def recolor_largest(g, c):
    objs = objects(g)
    if len(objs) < 2:
        raise ValueError("need 2 objects")
    big = set(max(objs, key=lambda o: len(o[1]))[1])
    return G([c if (y, x) in big else v for x, v in enumerate(r)] for y, r in enumerate(g))


def recolor_smallest(g, c):
    objs = objects(g)
    if len(objs) < 2:
        raise ValueError("need 2 objects")
    small = set(min(objs, key=lambda o: len(o[1]))[1])
    return G([c if (y, x) in small else v for x, v in enumerate(r)] for y, r in enumerate(g))


def fill_object_boxes(g, c):
    """Background cells inside each object's bounding box become colour c."""
    out = [list(r) for r in g]
    changed = False
    for cells in _objects_any(g):
        y0, x0, y1, x1 = _bbox(cells)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if out[y][x] == 0:
                    out[y][x] = c
                    changed = True
    if not changed:
        raise ValueError("nothing to fill")
    return G(out)


def halo(g, c):
    """Background cells touching an object (8 directions) become colour c."""
    h, w = len(g), len(g[0])
    out = [list(r) for r in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] == 0 and any(0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] != 0
                                    for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                out[y][x] = c
    return G(out)


def connect_pairs(g):
    """Two cells of the same colour on the same row or column: fill the background between them."""
    h, w = len(g), len(g[0])
    out = [list(r) for r in g]
    changed = False
    for y in range(h):
        for c in palette(g) - {0}:
            xs = [x for x in range(w) if g[y][x] == c]
            if len(xs) == 2:
                for x in range(xs[0] + 1, xs[1]):
                    if out[y][x] == 0:
                        out[y][x] = c
                        changed = True
    for x in range(w):
        for c in palette(g) - {0}:
            ys = [y for y in range(h) if g[y][x] == c]
            if len(ys) == 2:
                for y in range(ys[0] + 1, ys[1]):
                    if out[y][x] == 0:
                        out[y][x] = c
                        changed = True
    if not changed:
        raise ValueError("no pairs")
    return G(out)


def _rays(g, dirs):
    h, w = len(g), len(g[0])
    out = [list(r) for r in g]
    singles = [cells[0] for c, cells in objects(g) if len(cells) == 1]
    if not singles:
        raise ValueError("no points")
    for y, x in singles:
        c = g[y][x]
        for dy, dx in dirs:
            ny, nx = y + dy, x + dx
            while 0 <= ny < h and 0 <= nx < w and g[ny][nx] == 0:
                out[ny][nx] = c
                ny, nx = ny + dy, nx + dx
    return G(out)


def rays_h(g): return _rays(g, ((0, 1), (0, -1)))
def rays_v(g): return _rays(g, ((1, 0), (-1, 0)))
def rays_cross(g): return _rays(g, ((0, 1), (0, -1), (1, 0), (-1, 0)))
def rays_diag(g): return _rays(g, ((1, 1), (1, -1), (-1, 1), (-1, -1)))


def fill_periodic(g):
    """Holes (colour 0) in a periodic pattern are filled with the pattern (smallest period that fits)."""
    h, w = len(g), len(g[0])
    if all(v for r in g for v in r):
        raise ValueError("no holes")
    for ph in range(1, h + 1):
        for pw in range(1, w + 1):
            if ph * pw >= h * w // 2 + 1:
                continue
            tile, ok = {}, True
            for y in range(h):
                for x in range(w):
                    v = g[y][x]
                    if v:
                        k = (y % ph, x % pw)
                        if tile.setdefault(k, v) != v:
                            ok = False
                            break
                if not ok:
                    break
            if ok and len(tile) == ph * pw:
                return G([tile[(y % ph, x % pw)] for x in range(w)] for y in range(h))
    raise ValueError("not periodic")


def sym_rot180(g):
    return G([v if v else m for v, m in zip(r, rm[::-1])] for r, rm in zip(g, g[::-1]))


def sym_diag(g):
    if len(g) != len(g[0]):
        raise ValueError("not square")
    t = transpose(g)
    return G([v if v else m for v, m in zip(r, rt)] for r, rt in zip(g, t))


def self_kron(g):
    """Each non-background cell becomes a copy of the whole grid; background cells become empty."""
    h, w = len(g), len(g[0])
    if h * h > MAX_SIDE or w * w > MAX_SIDE:
        raise ValueError("too big")
    return G([g[y2][x2] if g[y1][x1] else 0 for x1 in range(w) for x2 in range(w)]
             for y1 in range(h) for y2 in range(h))


def majority_recolor(g):
    """Every non-background cell takes the most common non-background colour."""
    cnt = Counter(v for r in g for v in r if v)
    if len(cnt) < 2:
        raise ValueError("single colour")
    c = cnt.most_common(1)[0][0]
    return G([c if v else 0 for v in r] for r in g)


S1_NO_ARG = (crop_largest_any, crop_smallest_any, crop_unique_color_object, crop_odd_shape, keep_largest,
             remove_largest, denoise, connect_pairs, rays_h, rays_v, rays_cross, rays_diag, fill_periodic,
             sym_rot180, sym_diag, self_kron, majority_recolor)
S1_ONE_COLOR = (recolor_largest, recolor_smallest, fill_object_boxes, halo)


# ---------------------------------------------------------------- S1b · relations between objects

def _slide(g, dy, dx):
    """Rigid multi-colour objects slide in (dy, dx) until they touch the border or another object."""
    h, w = len(g), len(g[0])
    objs = _objects_any(g)
    if not objs:
        raise ValueError("no objects")
    key = (lambda o: -max(y for y, _ in o)) if dy > 0 else (lambda o: min(y for y, _ in o)) if dy < 0 else \
          (lambda o: -max(x for _, x in o)) if dx > 0 else (lambda o: min(x for _, x in o))
    grid = [list(r) for r in g]
    for o in sorted(objs, key=key):
        cells = set(o)
        colours = {(y, x): grid[y][x] for y, x in o}
        for y, x in o:
            grid[y][x] = 0
        shift = 0
        while True:
            nxt = [(y + dy * (shift + 1), x + dx * (shift + 1)) for y, x in o]
            if all(0 <= y < h and 0 <= x < w and grid[y][x] == 0 for y, x in nxt):
                shift += 1
            else:
                break
        for (y, x), c in colours.items():
            grid[y + dy * shift][x + dx * shift] = c
    out = G(grid)
    if out == g:
        raise ValueError("nothing moved")
    return out


def slide_down(g): return _slide(g, 1, 0)
def slide_up(g): return _slide(g, -1, 0)
def slide_left(g): return _slide(g, 0, -1)
def slide_right(g): return _slide(g, 0, 1)


def stamp_template(g):
    """The largest multi-colour object is a template; each single-cell marker gets a copy centred on it."""
    objs = _objects_any(g)
    if len(objs) < 2:
        raise ValueError("need template and markers")
    tpl = max(objs, key=len)
    markers = [o[0] for o in objs if len(o) == 1]
    if not markers or len(tpl) < 3:
        raise ValueError("no markers")
    y0, x0, y1, x1 = _bbox(tpl)
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    h, w = len(g), len(g[0])
    grid = [list(r) for r in g]
    for my, mx in markers:
        for y, x in tpl:
            ny, nx = my + y - cy, mx + x - cx
            if 0 <= ny < h and 0 <= nx < w and grid[ny][nx] == 0:
                grid[ny][nx] = g[y][x]
    return G(grid)


def _flip_each(g, lr):
    grid = [list(r) for r in g]
    for o in _objects_any(g):
        y0, x0, y1, x1 = _bbox(o)
        vals = {(y, x): g[y][x] for y, x in o}
        for y, x in o:
            grid[y][x] = 0
        for (y, x), c in vals.items():
            ny, nx = (y, x0 + x1 - x) if lr else (y0 + y1 - y, x)
            grid[ny][nx] = c
    out = G(grid)
    if out == g:
        raise ValueError("symmetric")
    return out


def flip_each_lr(g): return _flip_each(g, True)
def flip_each_ud(g): return _flip_each(g, False)


def frame(g, c):
    h, w = len(g), len(g[0])
    return G([c if y in (0, h - 1) or x in (0, w - 1) else v for x, v in enumerate(r)] for y, r in enumerate(g))


S1B_NO_ARG = (slide_down, slide_up, slide_left, slide_right, stamp_template, flip_each_lr, flip_each_ud)
S1B_ONE_COLOR = (frame,)


# ---------------------------------------------------------------- S2v · wider vocabulary (made usable by the intuition)

def invert(g, c):
    """Background becomes colour c and everything else becomes background."""
    return G([c if v == 0 else 0 for v in r] for r in g)


def outline(g, c):
    """Cells of an object that touch the background (4 directions) become colour c."""
    h, w = len(g), len(g[0])
    out = [list(r) for r in g]
    for y in range(h):
        for x in range(w):
            if g[y][x] and any(not (0 <= y + dy < h and 0 <= x + dx < w) or g[y + dy][x + dx] == 0
                               for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = c
    out = G(out)
    if out == g:
        raise ValueError("no outline")
    return out


def fill_holes_same(g):
    """Enclosed background inside each object takes that object's colour."""
    h, w = len(g), len(g[0])
    q = deque((y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and g[y][x] == 0)
    seen = set(q)
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in seen and g[ny][nx] == 0:
                seen.add((ny, nx))
                q.append((ny, nx))
    out = [list(r) for r in g]
    changed = False
    for y in range(h):
        for x in range(w):
            if g[y][x] == 0 and (y, x) not in seen:
                for dx in range(1, w):                          # colour of the nearest wall to the left
                    if x - dx >= 0 and g[y][x - dx]:
                        out[y][x] = g[y][x - dx]
                        changed = True
                        break
    if not changed:
        raise ValueError("no holes")
    return G(out)


def count_to_row(g):
    """A 1 x N row, N = number of objects, in the most common object colour."""
    objs = objects(g)
    if not objs or len(objs) > MAX_SIDE:
        raise ValueError("count")
    c = Counter(col for col, _ in objs).most_common(1)[0][0]
    return G([[c] * len(objs)])


def crop_common_shape(g):
    """The shape that appears most often (ties: the first), cropped."""
    objs = _objects_any(g)
    shapes = []
    for cells in objs:
        y0, x0, _, _ = _bbox(cells)
        shapes.append(tuple(sorted((y - y0, x - x0) for y, x in cells)))
    if len(objs) < 3:
        raise ValueError("few objects")
    best, n = Counter(shapes).most_common(1)[0]
    if n < 2:
        raise ValueError("no repeated shape")
    return _crop_box(g, _bbox(objs[shapes.index(best)]))


def _sections(g):
    """Split by full separator lines (one non-zero colour across a whole row / column)."""
    h, w = len(g), len(g[0])
    rows = [y for y in range(h) if len(set(g[y])) == 1 and g[y][0] != 0]
    cols = [x for x in range(w) if len({g[y][x] for y in range(h)}) == 1 and g[0][x] != 0]
    if not rows and not cols:
        raise ValueError("no separators")
    ys = [-1] + rows + [h]
    xs = [-1] + cols + [w]
    secs = []
    for a, b in zip(ys, ys[1:]):
        for c, d in zip(xs, xs[1:]):
            if b - a > 1 and d - c > 1:
                secs.append(G(r[c + 1:d] for r in g[a + 1:b]))
    shapes = {(len(s), len(s[0])) for s in secs}
    if len(secs) < 2 or len(shapes) != 1:
        raise ValueError("uneven sections")
    return secs


def _overlay(secs, op, c):
    h, w = len(secs[0]), len(secs[0][0])
    return G([c if op([bool(s[y][x]) for s in secs]) else 0 for x in range(w)] for y in range(h))


def sections_or(g, c): return _overlay(_sections(g), any, c)
def sections_and(g, c): return _overlay(_sections(g), all, c)
def sections_xor(g, c): return _overlay(_sections(g), lambda v: sum(v) == 1, c)


def sections_stack(g):
    """Overlay sections keeping colours: later non-zero cells paint over earlier ones."""
    secs = _sections(g)
    out = [list(r) for r in secs[0]]
    for s in secs[1:]:
        for y, r in enumerate(s):
            for x, v in enumerate(r):
                if v:
                    out[y][x] = v
    return G(out)


def crop_densest_section(g):
    secs = _sections(g)
    return max(secs, key=lambda s: sum(1 for r in s for v in r if v))


def crop_odd_section(g):
    secs = _sections(g)
    count = Counter(secs)
    odd = [s for s in secs if count[s] == 1]
    if len(odd) != 1:
        raise ValueError("no odd section")
    return odd[0]


S2V_NO_ARG = (fill_holes_same, count_to_row, crop_common_shape, sections_stack, crop_densest_section, crop_odd_section)
S2V_ONE_COLOR = (invert, outline, sections_or, sections_and, sections_xor)


# ---------------------------------------------------------------- the registry

NO_ARG = {f.__name__: f for f in (
    rot90, rot180, rot270, flipud, fliplr, transpose, crop, up2, up3, down2, down3, tile2x2, tile1x2,
    tile2x1, mirror_h, mirror_v, left_half, right_half, top_half, bottom_half, sym_h, sym_v, dedupe_rows,
    dedupe_cols, largest_object, smallest_object, gravity_down, gravity_up, gravity_left, gravity_right)}
ONE_COLOR = {f.__name__: f for f in (keep_color, remove_color, fill_bg, fill_enclosed)}
for _axis in ("h", "v"):
    for _name, _op in (("and", lambda x, y: x and y), ("or", lambda x, y: x or y), ("xor", lambda x, y: x != y),
                       ("nor", lambda x, y: not x and not y)):
        ONE_COLOR["%s_halves_%s" % (_name, _axis)] = (lambda a, o: lambda g, c: _logic(g, a, o, c))(_axis, _op)
TWO_COLOR = {"recolor": recolor, "swap": swap}
LEVEL = "S0"


def enable_s1():
    """Turn on the S1 object vocabulary (a sandbox born with S1 records it in its manifest)."""
    global LEVEL
    for f in S1_NO_ARG:
        NO_ARG[f.__name__] = f
    for f in S1_ONE_COLOR:
        ONE_COLOR[f.__name__] = f
    LEVEL = "S1"


def enable_s1b():
    """S1 plus relations between objects (sliding, stamping, per-object flips, frame)."""
    global LEVEL
    enable_s1()
    for f in S1B_NO_ARG:
        NO_ARG[f.__name__] = f
    for f in S1B_ONE_COLOR:
        ONE_COLOR[f.__name__] = f
    LEVEL = "S1b"


def enable_s2v():
    """S1b plus the wider S2 vocabulary (sections, outlines, holes, counting, inversion)."""
    global LEVEL
    enable_s1b()
    for f in S2V_NO_ARG:
        NO_ARG[f.__name__] = f
    for f in S2V_ONE_COLOR:
        ONE_COLOR[f.__name__] = f
    LEVEL = "S2v"


def apply_step(g, step):
    name, args = step[0], tuple(step[1:])
    if name in NO_ARG:
        return NO_ARG[name](g)
    if name in ONE_COLOR:
        return ONE_COLOR[name](g, *args)
    return TWO_COLOR[name](g, *args)


def primitive_count():
    return len(NO_ARG) + len(ONE_COLOR) + len(TWO_COLOR)
