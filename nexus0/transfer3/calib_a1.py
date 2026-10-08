"""Movement-cost calibration learned from observed energy. No map, no geometry.

The only inputs are the agent's own executed action, the action before it, and
the change in the `energy` scalar the sensor frame already reports. A straight
step identifies `base[a]`; a turning step identifies `base[a] + turn`. Parameters
never observed fall back to the declared nominal prior, so an arm is never
crippled by missing evidence.
"""
from .body_a1 import BASE_RANGE, TURN_RANGE, PLANAR

SCHEMA = 'transfer3-motion-calibration-v1'
NOMINAL_BASE = 4
NOMINAL_TURN = 0


def median(values):
    ordered = sorted(values)
    return ordered[len(ordered)//2]


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


class Calibration:
    def __init__(self, base=None, turn=None):
        self.base = list(base) if base else [NOMINAL_BASE]*PLANAR
        self.turn = NOMINAL_TURN if turn is None else int(turn)
        self.straight = [[] for _ in range(PLANAR)]
        self.turning = [[] for _ in range(PLANAR)]

    def observe(self, last, action, delta):
        """One executed planar move and the energy it actually cost."""
        if type(action) is not int or not 0 <= action < PLANAR:
            raise ValueError('planar action')
        if type(delta) is not int or delta <= 0:
            raise ValueError('observed cost must be a positive integer')
        if last is None or last == action:
            self.straight[action].append(delta)
        else:
            self.turning[action].append(delta)

    def resolve(self):
        base = [median(self.straight[a]) if self.straight[a] else NOMINAL_BASE
                for a in range(PLANAR)]
        gaps = [median(self.turning[a])-base[a] for a in range(PLANAR) if self.turning[a]]
        turn = median(gaps) if gaps else NOMINAL_TURN
        base = [min(max(v, BASE_RANGE[0]), BASE_RANGE[1]) for v in base]
        return base, min(max(turn, TURN_RANGE[0]), TURN_RANGE[1])

    def export(self):
        base, turn = self.resolve()
        payload = dict(schema=SCHEMA, base=base, turn=turn,
                       samples=dict(straight=[len(v) for v in self.straight],
                                    turning=[len(v) for v in self.turning]))
        validate(payload)
        return payload


def nominal():
    return dict(schema=SCHEMA, base=[NOMINAL_BASE]*PLANAR, turn=NOMINAL_TURN,
                samples=dict(straight=[0]*PLANAR, turning=[0]*PLANAR))


def restore(payload):
    validate(payload)
    return Calibration(payload['base'], payload['turn'])


def permuted(payload):
    """Same numbers, wrong actions: isolates content from merely having values."""
    validate(payload)
    base = payload['base']
    rotated = base[1:]+base[:1]
    out = dict(payload, base=rotated)
    validate(out)
    return out


def error_against(payload, body):
    validate(payload)
    return dict(base=[payload['base'][a]-body.base[a] for a in range(PLANAR)],
                turn=payload['turn']-body.turn,
                absolute=sum(abs(payload['base'][a]-body.base[a]) for a in range(PLANAR))
                + abs(payload['turn']-body.turn))
