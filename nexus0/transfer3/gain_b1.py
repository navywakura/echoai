"""Plan B1 body: per-action actuation gain. Evaluator side, never caged.

A commanded burst advances up to `gain[action]` cells for one actuation's energy
and stops before the first occupied cell, so a miscalibrated agent mispredicts
but never collides. Physically: a stronger actuator on one axis.

Measured before use: gain above one on more than a single action destroys goal
reachability, because it preserves parity along that axis — with (2,2,1,1) only
10 of 24 rooms stay solvable and with (2,2,2,2) only 2. The declared family
therefore carries gain on one action at a time.
"""
from echoai.nexus0.compose1.space import DIRECTIONS, add
from . import costs_a2
from .space_a2 import Body, Room

GAIN_RANGE = (1, 4)
PLANAR = costs_a2.PLANAR

CONDITIONS = {
    'flat': (1, 1, 1, 1),
    'gain2': (2, 1, 1, 1),
    'gain3': (3, 1, 1, 1),
}


def validate_gains(gains):
    gains = tuple(int(g) for g in gains)
    if len(gains) != PLANAR or any(not GAIN_RANGE[0] <= g <= GAIN_RANGE[1] for g in gains):
        raise ValueError('gain out of declared range')
    if sum(g > 1 for g in gains) > 1:
        raise ValueError('gain above one on more than one action destroys reachability')
    return gains


class GainRoom(Room):
    """`aligned` forces rotation zero so the gain action lies on the mission axis.

    Actions here are world-frame, so a gain fixed on action 0 is only exercised
    in rooms whose rotation happens to make +x useful — about a quarter of them.
    A filter that asks whether a mechanism works must exercise it; a campaign
    that asks how often it pays must not. Hence the flag, declared per use.
    """
    def __init__(self, seed, body, gains, aligned=False):
        super().__init__(seed, body)
        self.gains = validate_gains(gains)
        self.aligned = bool(aligned)
        if aligned and self.rotation:
            self.realign(seed)

    def realign(self, seed):
        """Rebuild the same room at rotation zero, replaying the generator's draws.

        `space_a2` is frozen into the A2 and A3 artifacts, so alignment is done
        here instead of by adding a parameter there.
        """
        import random
        from .space_a2 import HEIGHT_RANGE, WALL_GAP_MIN, WIDTH_RANGE
        rng = random.Random(seed)
        rng.randrange(4)
        width = rng.randrange(*WIDTH_RANGE)
        height = rng.randrange(*HEIGHT_RANGE)
        columns = range(1, width-1)
        first = rng.choice([c for c in columns if c+WALL_GAP_MIN <= max(columns)])
        second = rng.choice([c for c in columns if c-first >= WALL_GAP_MIN])
        gaps = {first: rng.randrange(-height+1, height),
                second: rng.randrange(-height+1, height)}
        self.rotation = 0
        self.walls = dict(gaps)
        self.domain = {(x, y, 0) for x in range(-1, width+1)
                       for y in range(-height, height+1)}
        self.solids = {(x, y, 0) for x in range(-1, width+1)
                       for y in range(-height, height+1)
                       if x in (-1, width) or y in (-height, height)
                       or (x in gaps and y != gaps[x])}
        self.goal = (width-1, 0, 0)
        self.pos = self.start
        self.camera_solids = set(self.solids)

    def step(self, action):
        if type(action) is not int or not 0 <= action < 7:
            raise ValueError('action')
        cost = costs_a2.WAIT_COST if action == 6 else self.body.step_cost(self.last_action, action)
        before, moved = self.pos, 0
        if action != 6:
            self.turns += self.last_action is not None and self.last_action != action
            for _ in range(self.gains[action]):
                nxt = add(self.pos, DIRECTIONS[action])
                if nxt not in self.domain or nxt in self.solids:
                    break
                self.pos = nxt
                moved += 1
            self.last_action = action
        blocked = action != 6 and moved == 0
        self.collisions += blocked
        self.steps += 1
        self.energy -= cost
        return dict(before=list(before), after=list(self.pos),
                    delta=[b-a for a, b in zip(before, self.pos)], cells=moved,
                    blocked=blocked, cost=cost, energy=self.energy)


def programmed(gains):
    """Evaluator-side helper: the model an agent would hold if it knew `gains`."""
    from echoai.nexus0.compose1.model import Effects
    validate_gains(gains)
    model = Effects()
    for action in range(PLANAR):
        delta = tuple(gains[action]*v for v in DIRECTIONS[action])
        for _ in range(2):
            model.observe_effect(True, action, delta)
    return model.snapshot()


def declared_body():
    return Body((costs_a2.NOMINAL_BASE,)*PLANAR, 0)
