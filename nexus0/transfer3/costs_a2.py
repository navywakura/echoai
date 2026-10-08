"""Agent-safe movement-cost vocabulary. Contains nothing the evaluator knows.

Plan A1 put these constants next to `CostSpace` in `body_a1`, so an isolated
consumer could not import the planner without also importing the simulator. That
is an isolation defect, not a style one: this module exists so the cage ships
cost arithmetic and calibration without shipping a world.

Nothing here reads geometry, seeds, maps or the evaluator's true cost table.
"""
PLANAR = 4
BASE_RANGE = (2, 6)
TURN_RANGE = (0, 8)
WAIT_COST = 1
NOMINAL_BASE = 4
NOMINAL_TURN = 0
RESERVE_DEFAULT = 4

SCHEMA = 'transfer3-motion-calibration-v1'


def step_cost(base, turn, last, action):
    if type(action) is not int or not 0 <= action < PLANAR:
        raise ValueError('planar action')
    return base[action]+(turn if last is not None and last != action else 0)


def route_cost(base, turn, actions):
    total, last = 0, None
    for action in actions:
        total += step_cost(base, turn, last, action)
        last = action
    return total


def validate(payload):
    if type(payload) is not dict or set(payload) != {'schema', 'base', 'turn', 'samples'}:
        raise ValueError('calibration fields: no map, geometry or episode channel')
    if payload['schema'] != SCHEMA:
        raise ValueError('calibration schema')
    base, turn, samples = payload['base'], payload['turn'], payload['samples']
    if (type(base) is not list or len(base) != PLANAR or
            any(type(v) is not int or not BASE_RANGE[0] <= v <= BASE_RANGE[1] for v in base)):
        raise ValueError('base costs out of declared range')
    if type(turn) is not int or not TURN_RANGE[0] <= turn <= TURN_RANGE[1]:
        raise ValueError('turn cost out of declared range')
    if (type(samples) is not dict or set(samples) != {'straight', 'turning'} or
            any(type(v) is not list or len(v) != PLANAR or
                any(type(n) is not int or n < 0 for n in v) for v in samples.values())):
        raise ValueError('sample coverage fields')
    return payload


def median(values):
    return sorted(values)[len(values)//2]


class Calibration:
    """Estimates cost parameters from the energy scalar the frame already reports."""
    def __init__(self, base=None, turn=None):
        self.base = list(base) if base else [NOMINAL_BASE]*PLANAR
        self.turn = NOMINAL_TURN if turn is None else int(turn)
        self.straight = [[] for _ in range(PLANAR)]
        self.turning = [[] for _ in range(PLANAR)]

    def observe(self, last, action, spent):
        if type(action) is not int or not 0 <= action < PLANAR:
            raise ValueError('planar action')
        if type(spent) is not int or spent <= 0:
            raise ValueError('observed cost must be a positive integer')
        (self.straight if last is None or last == action else self.turning)[action].append(spent)

    def resolve(self):
        base = [median(self.straight[a]) if self.straight[a] else NOMINAL_BASE
                for a in range(PLANAR)]
        gaps = [median(self.turning[a])-base[a] for a in range(PLANAR) if self.turning[a]]
        turn = median(gaps) if gaps else NOMINAL_TURN
        clamp = lambda v, lo, hi: min(max(v, lo), hi)
        return ([clamp(v, *BASE_RANGE) for v in base], clamp(turn, *TURN_RANGE))

    def export(self):
        base, turn = self.resolve()
        return validate(dict(schema=SCHEMA, base=base, turn=turn,
                             samples=dict(straight=[len(v) for v in self.straight],
                                          turning=[len(v) for v in self.turning])))


def nominal():
    return dict(schema=SCHEMA, base=[NOMINAL_BASE]*PLANAR, turn=NOMINAL_TURN,
                samples=dict(straight=[0]*PLANAR, turning=[0]*PLANAR))


def restore(payload):
    validate(payload)
    return Calibration(payload['base'], payload['turn'])


def turn_only(payload):
    """The candidate frozen after A1 v2: learn the turn, keep the nominal base.

    A1 v2 measured that the base term is what harms a myopic planner, monotonically
    in its asymmetry, while the turn term is what transfers.
    """
    validate(payload)
    return validate(dict(payload, base=[NOMINAL_BASE]*PLANAR))


def turn_ablated(payload):
    validate(payload)
    return validate(dict(payload, turn=NOMINAL_TURN))
