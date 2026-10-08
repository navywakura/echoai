"""Agent-safe bounded gain transfer, learned in the existing CAM/T model."""
from echoai.nexus0.compose1.model import Effects, state_packet
from echoai.nexus0.compose1.controller import Composer, add

SCHEMA = 'transfer3-actuation-gain-b2'
AXES = ((1,0,0), (-1,0,0), (0,1,0), (0,-1,0))


class Model(Effects):
    def slot(self, w, create=False):
        result = super().slot(w, create)
        if create and result < 0:
            raise ValueError('gain CAM full')
        return result


def validate(payload):
    if type(payload) is not dict or set(payload) != {'schema', 'gains', 'samples'}:
        raise ValueError('gain fields')
    if payload['schema'] != SCHEMA:
        raise ValueError('gain schema')
    for key, lo, hi in (('gains',1,4), ('samples',0,2)):
        row = payload[key]
        if type(row) is not list or len(row) != 4 or any(type(x) is not int or not lo <= x <= hi for x in row):
            raise ValueError('gain values/counts')
    if sum(g > 1 for g in payload['gains']) > 1:
        raise ValueError('one enhanced axis')
    if any(n not in (0,2) for n in payload['samples']):
        raise ValueError('incomplete calibration')
    return payload


def prior(gain):
    return validate(dict(schema=SCHEMA, gains=[gain,1,1,1], samples=[0]*4))


def restore(payload):
    validate(payload)
    model = Model()
    for a, gain in enumerate(payload['gains']):
        for _ in range(2):
            model.observe_effect(True, a, tuple(gain*v for v in AXES[a]))
    return model


class Learner:
    """Only public sensor frames and executed WSP; no world reference."""
    def __init__(self):
        self.model = Model()
        self.samples = [0]*4

    def observe(self, before, wsp, after):
        if type(wsp) is not bytes or len(wsp) != 16 or wsp[1] != 11 or not 0 <= wsp[13] < 4:
            raise ValueError('executed planar WSP')
        a = wsp[13]
        sensor = Composer(Model().snapshot(), (0,0,0))
        sensor.update(before)
        pos = sensor.pos
        # All four potential cells must be observed free: blocked displacements
        # cannot masquerade as a smaller intrinsic gain.
        for _ in range(4):
            pos = add(pos, AXES[a])
            if not sensor.free(pos):
                raise ValueError('censored gain observation')
        if after['now_ns'] <= before['now_ns']:
            raise ValueError('noncausal capture')
        sensor.update(after)
        delta = tuple(b-a for a,b in zip(before['odometry'], after['odometry']))
        gain = sum(abs(v) for v in delta)
        if not 1 <= gain <= 4 or delta != tuple(gain*v for v in AXES[a]):
            raise ValueError('invalid observed displacement')
        previous = self.model.predict(a)
        # Check the first sample too, before T's confidence reaches two.
        slot = self.model.slot(state_packet(1,1))
        if self.samples[a] and slot >= 0:
            previous = self.model.deltas[self.model.t.predict(slot,a)]
        if previous is not None and previous != delta:
            raise ValueError('conflicting gain observation')
        if self.samples[a] >= 2:
            raise ValueError('school sample budget')
        self.model.observe_effect(True, a, delta)
        self.samples[a] += 1

    def export(self):
        if self.samples != [2]*4 or self.model.t.conflicts:
            raise ValueError('incomplete/conflicting school')
        gains = [sum(abs(x) for x in self.model.predict(a)) for a in range(4)]
        return validate(dict(schema=SCHEMA, gains=gains, samples=list(self.samples)))
