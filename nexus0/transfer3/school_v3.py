"""Single-ingestion school; reward and exploration are independent factors."""
from echoai.nexus0.compose1.controller import add, distance
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.sim3.canon import canonical_bytes
from .rehearsal_v2 import Space
from . import policy

VARIANTS = {
    'corrected': dict(reward='progress', coverage=False),
    'reward_only': dict(reward='step_and_arrival', coverage=False),
    'coverage_only': dict(reward='progress', coverage=True),
}


def reward(kind, before, after, goal, observed):
    if kind not in ('progress', 'step_and_arrival'):
        raise ValueError('reward protocol')
    value = -1 + 32 * int(observed and tuple(after) == tuple(goal))
    if kind == 'progress':
        value += 8 * (distance(before, goal) - distance(after, goal))
    return value


class Student(Composer):
    """The second query of the *same* capture does not create new evidence.

V2 calls update(after), then decide(after) to act. Preserve that scheduling
and Q update timing, but ingest each timestamp exactly once. A changed packet
at the same time is refused rather than silently discarded.
"""
    def __init__(self, snapshot, goal, *, coverage=False, counts=None):
        super().__init__(snapshot, goal)
        self.last_capture = None
        self.last_frame = None
        self.ingestions = self.duplicate_queries = 0
        self.coverage = coverage
        self.counts = {} if counts is None else counts
        self.exploration_proposals = 0

    def update(self, frame):
        timestamp = frame['now_ns']
        raw = canonical_bytes(frame)
        if self.last_capture is not None and timestamp <= self.last_capture:
            if timestamp == self.last_capture and raw == self.last_frame:
                self.duplicate_queries += 1
                return
            raise ValueError('stale or conflicting capture')
        super().update(frame)
        self.last_capture, self.last_frame = timestamp, raw
        self.ingestions += 1

    def search(self, target):
        # Training only. Every fourth decision requests the least sampled
        # admissible first action. The normal Composer gate still executes.
        if self.coverage and self.turns % 4 == 0:
            counts = self.counts.get(self.feature().hex(), [0]*4)
            allowed = []
            for action in range(4):
                delta = self.model.predict(action)
                if delta is None:
                    continue
                nxt = add(self.pos, delta)
                if not self.free(nxt):
                    continue
                home = self.route_home(nxt)
                if home is not None and self.energy-4 >= 4*len(home)+10:
                    allowed.append(action)
            if allowed:
                self.exploration_proposals += 1
                return [min(allowed, key=lambda a: (counts[a], a))], len(allowed)
        return super().search(target)


def episode(payload, seed, variant, counts):
    config = VARIANTS[variant]
    world = Space(seed)
    student = Student(policy.restore(payload).snapshot(), world.goal,
                      coverage=config['coverage'], counts=counts)
    rows = []
    reserve_violations = 0
    for _ in range(65):
        frame = world.scan()
        decision = student.decide(frame)
        row = dict(observation=frame, decision=decision, consequence=None)
        rows.append(row)
        if decision['status'] not in ('moving', 'returning'):
            break
        wsp = bytes.fromhex(decision['wsp'])
        if len(wsp) != 16 or wsp[1] != 11 or not 0 <= wsp[13] < 4:
            raise ValueError('school planar WSP')
        action = wsp[13]
        feature = student.feature()
        before = world.pos
        home = world.home_distance(add(before, student.model.predict(action)))
        reserve_violations += home is None or world.energy-4 < home*4+10
        consequence = world.step(action)
        after = world.scan()
        student.update(after)
        value = reward(config['reward'], before, world.pos, world.goal, after['station_observed'])
        next_feature = student.feature()
        student.model.learn_reward(feature, action, value, next_feature)
        counts.setdefault(feature.hex(), [0]*4)[action] += 1
        row.update(consequence=consequence, after=after,
                   learning=dict(before=feature.hex(), after=next_feature.hex(), reward=value))
    captures = {r['observation']['now_ns'] for r in rows}
    captures.update(r['after']['now_ns'] for r in rows if 'after' in r)
    if student.ingestions != len(captures) or sum(student.visits.values()) != len(captures):
        raise ValueError('one capture must mean one ingestion and one visit')
    return dict(seed=seed, rows=rows, status=rows[-1]['decision']['status'],
                moves=world.steps, energy_spent=240-world.energy,
                collisions=world.collisions, reserve_violations=reserve_violations,
                ingestions=student.ingestions, unique_captures=len(captures),
                visit_count=sum(student.visits.values()), duplicate_queries=student.duplicate_queries,
                exploration_proposals=student.exploration_proposals), policy.export(student.model)
