"""Plan A2 generator: two-wall extruded rooms. Evaluator side, never caged.

Same ontology as every public room in this line — static planar cells, one start
at the origin, one station, geometry PRNG independent of any policy — with a
second wall and a second gap. Measured before use: 11.638 canonical shapes under
translation and D4, with **zero** overlap against the 92 public shapes already
spent, so every room here is structurally new rather than merely unseen.

Richer topology was chosen because the ontology allows it and because one wall
with one gap had exhausted its family, not to suit any candidate. The
confirmation carries a `flat` negative control precisely so that a generator
that flattered the candidate would show it.
"""
import random

from echoai.nexus0.compose1.space import DIRECTIONS
from . import costs_a2
from .rehearsal_v2 import Space as Previous, shape

WIDTH_RANGE = (7, 14)
HEIGHT_RANGE = (3, 7)
WALL_GAP_MIN = 2
MAX_ATTEMPTS = 200
MAX_CELLS = 256
ENERGY = 240


class Body:
    """Evaluator-side cost table. The agent never receives it."""
    def __init__(self, base, turn):
        base = tuple(int(v) for v in base)
        if len(base) != costs_a2.PLANAR or any(
                not costs_a2.BASE_RANGE[0] <= v <= costs_a2.BASE_RANGE[1] for v in base):
            raise ValueError('base costs out of declared range')
        if type(turn) is not int or not costs_a2.TURN_RANGE[0] <= turn <= costs_a2.TURN_RANGE[1]:
            raise ValueError('turn cost out of declared range')
        self.base, self.turn = base, turn

    def step_cost(self, last, action):
        return costs_a2.step_cost(self.base, self.turn, last, action)

    def as_dict(self):
        return dict(base=list(self.base), turn=self.turn)


class Room(Previous):
    """Two walls, one gap each. Inherited sensors, transitions and scan contract."""
    def __init__(self, seed, body):
        super(Previous, self).__init__(seed, 'static')
        rng = random.Random(seed)
        self.rotation = rng.randrange(4)
        width = rng.randrange(*WIDTH_RANGE)
        height = rng.randrange(*HEIGHT_RANGE)
        columns = range(1, width-1)
        first = rng.choice([c for c in columns if c+WALL_GAP_MIN <= max(columns)])
        second = rng.choice([c for c in columns if c-first >= WALL_GAP_MIN])
        gaps = {first: rng.randrange(-height+1, height),
                second: rng.randrange(-height+1, height)}
        self.walls = dict(gaps)
        self.domain = {self.rotate((x, y, 0)) for x in range(-1, width+1)
                       for y in range(-height, height+1)}
        self.solids = {self.rotate((x, y, 0)) for x in range(-1, width+1)
                       for y in range(-height, height+1)
                       if x in (-1, width) or y in (-height, height)
                       or (x in gaps and y != gaps[x])}
        self.goal = self.rotate((width-1, 0, 0))
        self.camera_solids = set(self.solids)
        self.body = body
        self.last_action = None
        self.turns = 0

    def step(self, action):
        if type(action) is not int or not 0 <= action < 7:
            raise ValueError('action')
        if action == 6:
            cost = costs_a2.WAIT_COST
        else:
            cost = self.body.step_cost(self.last_action, action)
            self.turns += self.last_action is not None and self.last_action != action
        before = self.pos
        target = tuple(x+y for x, y in zip(before, DIRECTIONS[action]))
        blocked = target not in self.domain or target in self.solids
        self.collisions += blocked
        if not blocked:
            self.pos = target
        self.steps += 1
        self.energy -= cost
        if action != 6:
            self.last_action = action
        return dict(before=list(before), after=list(self.pos),
                    delta=[b-a for a, b in zip(before, self.pos)],
                    blocked=blocked, cost=cost, energy=self.energy)


def min_cost_between(room, start, goal, heading):
    """Evaluator-side cheapest true cost, heading included. Never shown to the agent."""
    import heapq
    cells = {p for p in room.domain if p not in room.solids}
    if start not in cells:
        return None
    frontier = [(0, start, -1 if heading is None else heading)]
    seen = {}
    while frontier:
        cost, pos, last = heapq.heappop(frontier)
        if pos == goal:
            return cost
        if seen.get((pos, last), 1 << 60) < cost:
            continue
        for action in range(costs_a2.PLANAR):
            nxt = tuple(x+y for x, y in zip(pos, DIRECTIONS[action]))
            if nxt not in cells:
                continue
            step = room.body.step_cost(None if last < 0 else last, action)
            if cost+step < seen.get((nxt, action), 1 << 60):
                seen[(nxt, action)] = cost+step
                heapq.heappush(frontier, (cost+step, nxt, action))
    return None


def feasible(room, reserve=costs_a2.RESERVE_DEFAULT):
    """Arm-independent: reachable, inside spatial capacity, inside the budget."""
    if len(room.domain) > MAX_CELLS:
        return 'domain_capacity'
    distance = room.oracle_distance()
    if distance is None:
        return 'unreachable'
    if ENERGY < 2*distance*reserve+10:
        return 'outside_energy_budget'
    return None


def suite(start, count, forbidden=(), body=None):
    """Shape-disjoint rooms, with every rejection recorded in the ledger."""
    body = body or Body((costs_a2.NOMINAL_BASE,)*costs_a2.PLANAR, 0)
    seen = set(forbidden)
    accepted, ledger = [], []
    index = 0
    for case in range(count):
        for _ in range(MAX_ATTEMPTS):
            seed = start+index
            index += 1
            room = Room(seed, body)
            fingerprint = shape(room)
            reason = feasible(room) or ('duplicate' if fingerprint in seen else 'accepted')
            ledger.append(dict(case=case, index=index-1, seed=seed,
                               shape=fingerprint, reason=reason))
            if reason == 'accepted':
                seen.add(fingerprint)
                accepted.append(dict(seed=seed, shape=fingerprint,
                                     oracle_distance=room.oracle_distance(),
                                     cells=len(room.domain)))
                break
        else:
            raise ValueError('geometry sampling exhausted; no policy-dependent fallback')
    return accepted, ledger
