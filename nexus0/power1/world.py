"""Private deterministic energy plant. Not mounted in the public consumer."""
import copy
import random
import time
from echoai.nexus0.cause1.core import decode, wsp
from .core import Guard, RESERVE

CONDITIONS = ('short_low', 'long_high', 'return_now', 'margin', 'comfortable')
POLICIES = ('cost', 'fixed', 'oracle')


def calibration():
    rng = random.Random(20263100)
    records = []
    for phase, low, high in [('0', 8, 12), ('1', 12, 16), ('land', 18, 23)]:
        costs = [low+i % (high-low+1) for i in range(32)]
        rng.shuffle(costs)
        for cost in costs:
            records.append(dict(seq=len(records), phase=phase, before=1000, after=1000-cost,
                                elapsed_ms=4000, confirmed=True, unit='sim_u'))
    return records


class World:
    def __init__(self, seed, condition):
        if condition not in CONDITIONS:
            raise ValueError('condition')
        rng = random.Random(seed)
        self.seed, self.condition = seed, condition
        self.capacity = 1000
        self.pos = 4 if condition == 'return_now' else 0
        if condition == 'short_low':
            self.goal, self.energy = rng.randint(1, 2), rng.randint(145, 179)
        elif condition == 'long_high':
            self.goal, self.energy = rng.randint(10, 14), rng.randint(210, 240)
        elif condition == 'return_now':
            self.goal, self.energy = rng.randint(10, 12), rng.randint(200, 215)
        elif condition == 'margin':
            self.goal, self.energy = 3, rng.randint(140, 165)
        else:
            self.goal, self.energy = rng.randint(3, 5), rng.randint(400, 500)
        self.start_energy, self.start_pos = self.energy, self.pos
        self.north = [rng.randint(8, 12) for _ in range(16)]
        self.south = [rng.randint(12, 16) for _ in range(16)]
        self.landing = rng.randint(18, 23)
        if condition == 'margin':
            self.north, self.south, self.landing = [15]*16, [20]*16, 29
        self.turn, self.reached, self.landed, self.dead = 0, False, False, False
        self.initial_feasible = self.mission_cost()+RESERVE <= self.energy
        self.permission_violations = 0
        self.path_reserve_violations = 0

    def return_cost(self):
        return sum(self.south[1:self.pos+1])+self.landing

    def mission_cost(self):
        return sum(self.north[self.pos:self.goal])+sum(self.south[1:self.goal+1])+self.landing

    def observe(self):
        stamp = (self.turn+1)*1_000_000_000
        return dict(now_ns=stamp, battery=dict(capture_ns=stamp, remaining=self.energy,
                    capacity=self.capacity, unit='sim_u'), routes=dict(out=[0]*(self.goal-self.pos),
                    goal_home=[1]*self.goal, home=[1]*self.pos), at_home=self.pos == 0,
                    goal_reached=self.pos == self.goal)

    def step(self, decision):
        if self.dead or self.landed:
            raise ValueError('terminal world')
        action = decode(decision['wsp'])
        if action == 0 and self.mission_cost()+RESERVE > self.energy:
            self.permission_violations += 1
        before = dict(position=self.pos, remaining=self.energy)
        if action == 0:
            if self.pos >= self.goal:
                raise ValueError('past goal')
            cost = self.north[self.pos]
            self.pos += 1
        elif action == 1:
            if self.pos <= 0:
                raise ValueError('past home')
            cost = self.south[self.pos]
            self.pos -= 1
        else:
            cost = self.landing
            self.landed = True
        self.energy -= cost
        self.turn += 1
        self.reached |= self.pos == self.goal
        self.dead = self.energy < 0
        if not self.landed and self.energy < self.return_cost()+RESERVE:
            self.path_reserve_violations += 1
        return dict(before=before, action=action, cost=cost, after=dict(position=self.pos,
                    remaining=self.energy), landed=self.landed, dead=self.dead)


class Oracle:
    def __init__(self):
        self.returning = False

    def decide(self, world):
        if world.pos == world.goal or world.mission_cost()+RESERVE > world.energy:
            self.returning = True
        if self.returning:
            if world.pos == 0:
                return dict(wsp=wsp(6), reason='land_home')
            if world.return_cost()+RESERVE > world.energy:
                return dict(wsp=wsp(6), reason='land_local')
            return dict(wsp=wsp(1), reason='return')
        return dict(wsp=wsp(0), reason='continue')


def episode(seed, condition, policy, model, consumer=None):
    world = World(seed, condition)
    oracle_initial = Oracle().decide(world)['reason']
    actor = Oracle() if policy == 'oracle' else Guard(model, policy)
    if consumer is not None and policy != 'oracle':
        if consumer.call(dict(model=model, policy=policy)) != {'ready': True}:
            raise RuntimeError('consumer initialization')
    trace, latency = [], []
    for _ in range(64):
        frame = world.observe()
        start = time.monotonic_ns()
        if policy == 'oracle':
            decision = actor.decide(world)
        elif consumer is not None:
            decision = consumer.call(frame)
        else:
            decision = actor.decide(frame)
        latency.append(time.monotonic_ns()-start)
        transition = world.step(decision)
        trace.append(dict(frame=frame, decision=decision, transition=transition))
        if world.dead or world.landed:
            break
    safe = world.landed and not world.dead and world.pos == 0 and world.energy >= RESERVE
    return dict(seed=seed, condition=condition, policy=policy, trace=trace,
        result=dict(safe=safe, landed=world.landed, dead=world.dead, home=world.pos == 0,
            reached=world.reached, successful=safe and world.reached, initial_feasible=world.initial_feasible,
            correct_initial=trace[0]['decision']['reason'] == oracle_initial,
            false_abort=not world.reached and world.initial_feasible,
            correct_abort=not world.reached and not world.initial_feasible and safe,
            returned=any(row['transition']['action'] == 1 for row in trace),
            mission_permission_violations=world.permission_violations,
            reserve_violations=world.path_reserve_violations+int(world.energy < RESERVE),
            consumed=world.start_energy-world.energy, remaining=world.energy, moves=world.turn-1),
        latency_ns=latency, isolated=consumer is not None and policy != 'oracle')


def audit_episode(record, model):
    expected = episode(record['seed'], record['condition'], record['policy'], model)
    actual = copy.deepcopy(record)
    for key in ('latency_ns', 'isolated'):
        actual.pop(key, None)
        expected.pop(key, None)
    return actual == expected
