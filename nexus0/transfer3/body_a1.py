"""Plan A1 body: integer movement costs with a non-conservative turn term.

The evaluator charges `base[a] + turn` when the executed action differs from the
previous one. Per-action costs alone are conservative — the route-dependent part
reduces to wasted back-and-forth pairs — so they cannot distinguish two routes of
minimum length. The turn term depends on the order of actions, not their counts.

Physically: a body with horizontal momentum pays to decelerate and re-accelerate
when it changes heading. The agent never imports this module.
"""
from echoai.nexus0.compose1.space import DIRECTIONS
from .rehearsal_v2 import Space

PLANAR = 4
BASE_RANGE = (2, 6)
TURN_RANGE = (0, 8)
WAIT_COST = 1
# Declared worst case per move, shared by every arm's reserve gate.
RESERVE_COST = BASE_RANGE[1]+TURN_RANGE[1]

CONDITIONS = {
    'flat': dict(base=(4, 4, 4, 4), turn=0),
    'turn4': dict(base=(4, 4, 4, 4), turn=4),
    'turn8': dict(base=(4, 4, 4, 4), turn=8),
    'skew_turn6': dict(base=(3, 5, 4, 4), turn=6),
}


class CostBody:
    def __init__(self, base, turn):
        base = tuple(int(v) for v in base)
        if len(base) != PLANAR or any(not BASE_RANGE[0] <= v <= BASE_RANGE[1] for v in base):
            raise ValueError('base costs out of declared range')
        if type(turn) is not int or not TURN_RANGE[0] <= turn <= TURN_RANGE[1]:
            raise ValueError('turn cost out of declared range')
        self.base, self.turn = base, turn

    @classmethod
    def named(cls, name):
        if name not in CONDITIONS:
            raise ValueError('undeclared condition')
        return cls(**CONDITIONS[name])

    def step_cost(self, last, action):
        if type(action) is not int or not 0 <= action < PLANAR:
            raise ValueError('planar action')
        return self.base[action]+(self.turn if last is not None and last != action else 0)

    def route_cost(self, actions):
        total, last = 0, None
        for action in actions:
            total += self.step_cost(last, action)
            last = action
        return total

    def as_dict(self):
        return dict(base=list(self.base), turn=self.turn)


def min_cost_between(world, start, goal, heading):
    """Evaluator-side cheapest true cost, heading included. Never shown to the agent."""
    import heapq
    cells = {p for p in world.domain if p not in world.solids}
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
        for action in range(PLANAR):
            nxt = tuple(x+y for x, y in zip(pos, DIRECTIONS[action]))
            if nxt not in cells:
                continue
            step = world.body.step_cost(None if last < 0 else last, action)
            if cost+step < seen.get((nxt, action), 1 << 60):
                seen[(nxt, action)] = cost+step
                heapq.heappush(frontier, (cost+step, nxt, action))
    return None


class CostSpace(Space):
    """Same geometry and sensors as the public rooms; only charging changes."""
    def __init__(self, seed, body):
        super().__init__(seed)
        self.body = body
        self.last_action = None
        self.turns = 0

    def step(self, action):
        if type(action) is not int or not 0 <= action < 7:
            raise ValueError('action')
        if action == 6:
            cost = WAIT_COST
        else:
            cost = self.body.step_cost(self.last_action, action)
            self.turns += self.last_action is not None and self.last_action != action
        before, energy = self.pos, self.energy
        target = tuple(x+y for x, y in zip(before, DIRECTIONS[action]))
        blocked = target not in self.domain or target in self.solids
        self.collisions += blocked
        if not blocked:
            self.pos = target
        self.steps += 1
        self.energy -= cost
        if action != 6:
            # A blocked attempt still spends the move and still sets heading.
            self.last_action = action
        return dict(before=list(before), after=list(self.pos),
                    delta=[b-a for a, b in zip(before, self.pos)],
                    blocked=blocked, cost=cost, energy=self.energy,
                    energy_before=energy)
