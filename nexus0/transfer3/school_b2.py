"""Evaluator-side gym. Learner receives frames only, never this world."""
from echoai.core.wsp import pack
from .calib_b2 import Learner
from .gain_b1 import GainRoom, declared_body


class Gym(GainRoom):
    def __init__(self, gains, axis):
        super().__init__(0,declared_body(),gains,aligned=True)
        self.domain = {(x,y,0) if axis == 0 else (y,x,0)
                       for x in range(-9,10) for y in range(-4,5)}
        self.solids = {p for p in self.domain if abs(p[axis]) == 9 or abs(p[1-axis]) == 4}
        self.camera_solids = set(self.solids)


def train(gains):
    learner, traces = Learner(), []
    for a in range(4):
        world = Gym(gains,a//2)
        before = world.scan()
        for _ in range(2):
            wsp = pack(src=2,rel=11,dst=5,time=8,E={},domain=9,generator=8,style=a)
            consequence = world.step(a)
            after = world.scan()
            learner.observe(before,wsp,after)
            traces.append(dict(before=before,wsp=wsp.hex(),after=after,consequence=consequence))
            before = after
    payload = learner.export()
    return dict(payload=payload,moves=len(traces),energy=sum(t['consequence']['cost'] for t in traces),
                collisions=sum(t['consequence']['blocked'] for t in traces),traces=traces)


def replay(school):
    learner = Learner()
    for row in school['traces']:
        learner.observe(row['before'],bytes.fromhex(row['wsp']),row['after'])
    if learner.export() != school['payload']:
        raise ValueError('school payload does not follow observations')
    return learner.export()
