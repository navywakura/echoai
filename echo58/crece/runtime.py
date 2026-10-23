"""Integer plug boundary. F0 trusted functions; hostile code needs F1's interpreter."""
from __future__ import annotations

from collections import Counter
from copy import copy
from dataclasses import dataclass
import hashlib
import inspect

from ..acumula.agent import XAgent
from ..b3.policy import PAgent, reach
from ..memx.agent import DIRS

DECIDE, OUTCOME, DROP, IDLE = range(4)
ENTER, PICK, TOGGLE, DROP_ACTION = range(4)
UNKNOWN, PASS, NOOP, HURT, PICKED, OPEN, GOAL = range(7)
EPISODE, HAND, ANY = range(3)
ACTS = ('ENTER', 'PICK', 'TOGGLE', 'DROP')
ANSWERS = (None, 'PASS', 'NOOP', 'HURT', 'PICK', 'OPEN', 'GOAL')
E_BAN, E_UNTIL, E_DROP, E_GOTO, E_NOTE = range(10, 15)


def BAN(ident, act, scope):
    return (E_BAN, ident, act, scope)


def BAN_UNTIL_PROGRESS(ident, act):
    return (E_UNTIL, ident, act)


def DROP_AT(cell):
    return (E_DROP, cell)


def GOTO(cell):
    return (E_GOTO, cell)


def NOTE(key, scope=EPISODE):
    return (E_NOTE, key, scope)


@dataclass(frozen=True, slots=True)
class Context:
    intent: tuple = ()
    drop_for: int = 0
    out: int = UNKNOWN
    dropped_here: tuple = ()
    avoid: tuple = ()


def intent_code(intent):
    return (ACTS.index(intent[0]), *intent[1:]) if intent else ()


@dataclass(frozen=True, slots=True)
class Plug:
    name: str
    function: object
    hooks: frozenset = frozenset({DECIDE, OUTCOME, DROP, IDLE})

    def digest(self):
        code = getattr(self.function, 'source', None)
        if code is None:
            code = inspect.getsource(self.function)
        return hashlib.sha256(code.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class View:
    pos: tuple
    dir: int
    hand: int
    absolute: int
    grid: tuple
    progress: int
    idle: int
    steps: int
    wall: int
    floor: int
    _picked: tuple
    _opened: tuple
    _visits: tuple
    _notes: tuple
    _beliefs: tuple

    def picked(self, ident):
        return dict(self._picked).get(ident, 0)

    def opened(self, cell):
        return dict(self._opened).get(cell, 0)

    def visits(self, cell):
        return dict(self._visits).get(cell, 0)

    def note(self, key, scope=EPISODE):
        return dict(self._notes).get((key, self.hand if scope == HAND else 0), 0)

    def belief(self, ident, act, hand):
        return dict(self._beliefs).get((ident, act, hand), UNKNOWN)

    def reach(self, start=None, blocked=None):
        beliefs = dict(self._beliefs)
        return frozenset(reach(self.pos if start is None else start, self.grid,
                              lambda x, y: beliefs.get((self.grid[y][x], ENTER, 0), UNKNOWN) == PASS,
                              blocked))

    def ids_near(self, start=None):
        h, w = len(self.grid), len(self.grid[0])
        return frozenset(self.grid[y + dy][x + dx]
                         for x, y in self.reach(start) for dx, dy in DIRS
                         if 0 <= x + dx < w and 0 <= y + dy < h)


class DecisionBridge(XAgent):
    """PAgent's super-call lands here; PAgent owns episode accounting once."""
    def _decide(self, obs, world):
        for _ in range(8):
            self._drop_for = None
            self._turned = False
            prim, intent = super()._decide(obs, world)
            target = obs.grid[self._drop_for[1]][self._drop_for[0]] if self._drop_for is not None else 0
            effect = self._dispatch(DECIDE, obs, world, Context(intent_code(intent), target))
            if effect is None:
                return prim, intent
            self.belief_cache = {}
        self._drop_for = None
        self._turned = False
        return super()._decide(obs, world)


class HAgent(PAgent, DecisionBridge):
    @property
    def pieces(self):
        return frozenset()

    @pieces.setter
    def pieces(self, value):
        if frozenset(value):
            raise ValueError('native pieces must remain disabled')

    def __init__(self, source=None, learn=None, *, plugs=(), pieces=frozenset()):
        if frozenset(pieces):
            raise ValueError('native pieces must remain disabled')
        self.plugs = tuple(plugs)
        if len({p.name for p in self.plugs}) != len(self.plugs):
            raise ValueError('duplicate plug name')
        super().__init__(source=source, learn=learn, pieces=frozenset())

    def run(self, world, max_steps=100000, frames=None):
        self._active_world = world
        self._notes = {}
        self._temporary_bans = {}
        self._additional_hand_bans = {}
        self.plug_errors = []
        self.plug_actions = Counter()
        self.plug_events = []
        result = super().run(world, max_steps, frames)
        result['plug_errors'] = list(self.plug_errors)
        result['plug_actions'] = dict(self.plug_actions)
        return result

    def belief(self, ident, act, hand):
        if self.cur_hand in self._additional_hand_bans.get((ident, act), ()):
            return 'NOOP'
        if self._temporary_bans.get((ident, act), -1) == self.progress:
            return 'NOOP'
        return super().belief(ident, act, hand)

    def _view(self, obs, world, plug):
        # Evaluate on a disposable reader. No live belief-cache, provenance,
        # memory query counters, or source.last changes are visible to pieces.
        reader = copy(self)
        for key in ('belief_cache', 'sig_cache', 'recalled', 'answers', 'why'):
            setattr(reader, key, dict(getattr(self, key)))
        reader.source = copy(self.source) if self.source is not None else None
        ids = set(self.counts) | {obs.hand}
        beliefs = {(i, a, h): ANSWERS.index(reader.belief(i, ACTS[a], h))
                   for i in ids for a in (ENTER, PICK, TOGGLE) for h in ids | {0}}
        wall = max(self.border, key=lambda i: (self.border[i], -i), default=0)
        floor = max((i for i in self.counts if beliefs[(i, ENTER, 0)] == PASS),
                    key=lambda i: (self.counts[i], -i), default=0)
        return View(obs.pos, obs.dir, obs.hand, int(world.absolute), tuple(tuple(row) for row in obs.grid),
                    self.progress, self.idle, self.steps_n, wall, floor,
                    tuple(self.picked.items()), tuple(self.opened.items()), tuple(self.visits.items()),
                    tuple(self._notes.get(plug.name, {}).items()), tuple(beliefs.items()))

    def _validate(self, effects, moment, obs, world, ctx, view):
        if type(effects) is not tuple or len(effects) > 2:
            raise ValueError('effects must be a tuple of at most two')
        allowed = {DECIDE: {E_BAN, E_NOTE}, OUTCOME: {E_UNTIL, E_NOTE},
                   DROP: {E_DROP, E_GOTO, E_NOTE}, IDLE: {E_GOTO, E_NOTE}}[moment]
        actions = notes = 0
        for effect in effects:
            if type(effect) is not tuple or not effect or type(effect[0]) is not int or effect[0] not in allowed:
                raise ValueError('effect not allowed at this hook')
            kind = effect[0]
            notes += kind == E_NOTE
            actions += kind != E_NOTE
            if notes > 1 or actions > 1:
                raise ValueError('duplicate effect kind')
            if kind in (E_BAN, E_UNTIL):
                if len(effect) != (4 if kind == E_BAN else 3):
                    raise ValueError('invalid ban shape')
                ident, act = effect[1:3]
                if type(ident) is not int or ident not in {i for row in obs.grid for i in row}:
                    raise ValueError('unknown id')
                if type(act) is not int or act not in (ENTER, PICK, TOGGLE) or ACTS[act] not in world.acts:
                    raise ValueError('invalid action')
                if kind == E_BAN and (type(effect[3]) is not int or effect[3] not in (HAND, ANY)
                                      or (effect[3] == HAND and not obs.hand)):
                    raise ValueError('invalid ban scope')
            elif kind == E_NOTE:
                if (len(effect) != 3 or type(effect[1]) is not int or not 0 <= effect[1] <= 15
                        or type(effect[2]) is not int or effect[2] not in (EPISODE, HAND)
                        or (effect[2] == HAND and not obs.hand)):
                    raise ValueError('invalid note')
            else:
                if len(effect) != 2 or type(effect[1]) is not tuple or len(effect[1]) != 2:
                    raise ValueError('invalid coordinate')
                cell = effect[1]
                if any(type(n) is not int for n in cell):
                    raise ValueError('invalid coordinate')
                x, y = cell
                if not (0 <= y < len(obs.grid) and 0 <= x < len(obs.grid[0])):
                    raise ValueError('coordinate outside board')
                if kind == E_DROP:
                    if not obs.hand or cell == ctx.avoid or abs(x-obs.pos[0]) + abs(y-obs.pos[1]) != 1:
                        raise ValueError('invalid drop')
                elif cell == obs.pos or cell not in view.reach():
                    raise ValueError('unreachable destination')

    def _dispatch(self, moment, obs, world, ctx):
        for plug in self.plugs:
            if moment not in plug.hooks:
                continue
            view = self._view(obs, world, plug)
            try:
                effects = plug.function(moment, view, ctx)
                self._validate(effects, moment, obs, world, ctx, view)
            except Exception as exc:
                self.plug_errors.append((plug.name, moment, type(exc).__name__))
                continue
            action = None
            for effect in effects:
                kind = effect[0]
                if kind == E_NOTE:
                    key = (effect[1], obs.hand if effect[2] == HAND else 0)
                    notes = self._notes.setdefault(plug.name, {})
                    notes[key] = notes.get(key, 0) + 1
                else:
                    action = effect
                    if kind == E_BAN:
                        key = (effect[1], ACTS[effect[2]])
                        prior = self.ban.get(key, 0)
                        if prior is not None:
                            if prior:
                                self._additional_hand_bans.setdefault(key, set()).add(prior)
                            self.ban[key] = obs.hand if effect[3] == HAND else None
                    elif kind == E_UNTIL:
                        self._temporary_bans[(effect[1], ACTS[effect[2]])] = self.progress
                    self.plug_actions[plug.name] += 1
                self.plug_events.append((self.steps_n, plug.name, moment, effect))
            if action is not None:
                return action
        return None

    def _motion(self, effect, obs, world):
        kind, cell = effect
        if kind == E_DROP:
            return self._face(obs, cell, ('D', ('DROP', cell, obs.grid[cell[1]][cell[0]], obs.hand, 0)))
        tree = reach(obs.pos, obs.grid, lambda x, y: self.belief(obs.grid[y][x], 'ENTER', 0) == 'PASS')
        step = cell
        while tree[step] != obs.pos:
            step = tree[step]
        return self._toward(obs, world, step, 'ENTER')

    def _drop(self, obs, world, grid, ok, passable, avoid=None):
        self._drop_for = avoid
        if not world.absolute:
            effect = self._dispatch(DROP, obs, world, Context(avoid=avoid or ()))
            if effect is not None:
                return self._motion(effect, obs, world)
        return super()._drop(obs, world, grid, ok, passable, avoid)

    def _outcome(self, old, new, intent):
        dropped = self.dropped.get(intent[1], ())
        out = super()._outcome(old, new, intent)
        # The id acted on belongs to the pre-action observation, even after PICK.
        self._dispatch(OUTCOME, old, self._active_world,
                       Context(intent=intent_code(intent), out=ANSWERS.index(out), dropped_here=dropped))
        return out

    def _decide(self, obs, world):
        answer = super()._decide(obs, world)
        if not world.absolute:
            effect = self._dispatch(IDLE, obs, world, Context())
            if effect is not None:
                return self._motion(effect, obs, world)
        return answer
