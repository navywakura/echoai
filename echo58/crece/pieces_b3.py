"""The five reference rules, using only the integer external plug interface."""
from .runtime import (DECIDE, OUTCOME, DROP, IDLE, ENTER, PICK, TOGGLE,
                      DROP_ACTION, UNKNOWN, PASS, PICKED, OPEN, HAND, ANY,
                      BAN, BAN_UNTIL_PROGRESS, DROP_AT, GOTO, NOTE, Plug, DIRS)


def commit(moment, v, c):
    if moment != DECIDE or not c.intent or c.intent[0] != DROP_ACTION or not c.drop_for:
        return ()
    if not v.picked(c.drop_for):
        return ()
    for ident in v.ids_near():
        if (ident != v.hand and ident != v.wall and v.belief(ident, ENTER, 0) != PASS
                and v.belief(ident, TOGGLE, v.hand) in (UNKNOWN, OPEN)):
            return (BAN(c.drop_for, PICK, HAND),)
    return ()


def no_retoggle(moment, v, c):
    if moment == DECIDE and c.intent and c.intent[0] == TOGGLE and v.opened(c.intent[1]):
        return (BAN(c.intent[2], TOGGLE, ANY),)
    return ()


def clear(moment, v, c):
    if moment != DROP or v.absolute:
        return ()
    before = v.reach()
    height, width = len(v.grid), len(v.grid[0])
    for dx, dy in DIRS:
        cell = (v.pos[0] + dx, v.pos[1] + dy)
        if (cell != c.avoid and 0 <= cell[0] < width and 0 <= cell[1] < height
                and v.grid[cell[1]][cell[0]] == v.floor):
            if len(v.reach(blocked=cell)) == len(before) - 1:
                return (DROP_AT(cell),)
    note = NOTE(0, HAND)
    if v.note(0, HAND) + 1 > 8:
        return (note,)
    for cell in sorted(before, key=lambda p: (abs(p[0]-v.pos[0]) + abs(p[1]-v.pos[1]), p)):
        if cell == v.pos:
            continue
        for dx, dy in DIRS:
            near = (cell[0] + dx, cell[1] + dy)
            if (near != c.avoid and near != v.pos and 0 <= near[0] < width
                    and 0 <= near[1] < height and v.grid[near[1]][near[0]] == v.floor):
                if len(v.reach(cell, near)) == len(v.reach(cell)) - 1:
                    return (note, GOTO(cell))
    return (note,)


def wander(moment, v, c):
    if moment != IDLE or v.absolute or v.idle < 3:
        return ()
    cells = tuple(cell for cell in v.reach() if cell != v.pos)
    if not cells:
        return ()
    target = min(cells, key=lambda p: (v.visits(p), abs(p[0]-v.pos[0]) + abs(p[1]-v.pos[1]), p))
    return (GOTO(target),)


def no_repick(moment, v, c):
    if (moment == OUTCOME and c.intent and c.intent[0] == PICK and c.out == PICKED
            and c.dropped_here == (c.intent[2], v.progress)):
        return (BAN_UNTIL_PROGRESS(c.intent[2], PICK),)
    return ()


PLUGS = (Plug('commit', commit, frozenset({DECIDE})),
         Plug('no_retoggle', no_retoggle, frozenset({DECIDE})),
         Plug('clear', clear, frozenset({DROP})),
         Plug('wander', wander, frozenset({IDLE})),
         Plug('no_repick', no_repick, frozenset({OUTCOME})))
