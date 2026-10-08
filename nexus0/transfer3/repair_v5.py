"""Public development repairs. No new planner, campaign or exam claims.

Reuse the frozen controller and Q table; change only the training boundary.
Failure reward is an explicit new experimental parameter, not a retroactive
reinterpretation of v3/v4. Budget truncation is not environmental termination.
"""
from copy import deepcopy

from echoai.nexus0.compose1.model import Effects, state_packet
from echoai.nexus0.compose1.controller import add
from echoai.nexus0.compose1.space import DIRECTIONS
from . import policy
from .school_v3 import Student, reward

FAILURES = frozenset(('budget_exhausted', 'abandoned_at_home',
                      'access_not_found', 'return_not_found', 'evidence_block'))
ACTIVE = frozenset(('moving', 'returning'))
PROTOCOL = dict(version=5, scope='public-repair-diagnostics-only',
                progress_reward='8*(L1_before-L1_after)-1+32*observed_arrival',
                step_and_arrival_reward='-1+32*observed_arrival',
                failure_bonus=-32, truncation_terminal=False,
                goal_coordinates_known=True, campaign_enabled=False)


class CheckedEffects(Effects):
    def slot(self, w, create=False):
        slot = super().slot(w, create)
        if create and slot < 0:
            raise ValueError('CAM capacity: allocation refused before Q/T write')
        return slot

    def learn_reward(self, feature, action, value, next_feature, *, terminal=False):
        if type(terminal) is not bool:
            raise ValueError('terminal must be explicit boolean')
        if type(action) is not int or not 0 <= action < 4 or type(value) is not int:
            raise ValueError('planar action and integer reward required')
        source = self.slot(feature, True)
        # Terminal learning needs no allocation of the successor.
        dest = source if terminal else self.slot(next_feature, True)
        return self.q.update(source, action, value, dest, terminal=terminal)


def restore(payload):
    policy.validate(payload)
    model = CheckedEffects()
    # Same programmed locomotion in every arm, through checked allocation.
    for action in range(4):
        for _ in range(2):
            model.observe_effect(True, action, DIRECTIONS[action])
    for row in payload['q']:
        slot = model.slot(state_packet(row['feature'], 3), True)
        for action, value in enumerate(row['values']):
            model.q.set(slot, action, value)
    return model


def reserve_violation(world, action):
    """Independent adjudicator, identical for school and local diagnostic exam."""
    if type(action) is not int or not 0 <= action < 4:
        raise ValueError('planar action')
    home = world.home_distance(add(world.pos, DIRECTIONS[action]))
    return home is None or world.energy-4 < 4*home+10


def terminal_outcome(agent, frame):
    # Query a copy: never increment the live agent's turns, evidence, counts or
    # visits. Q cannot change existence of a search path, only its tie-breaking.
    # The next real decision is made AFTER learning, not cached before learning.
    probe = deepcopy(agent, {id(agent.model): agent.model})
    status = probe.decide(frame)['status']
    if status not in ACTIVE | FAILURES | {'reached'}:
        raise ValueError('unknown mission outcome')
    return status if status not in ACTIVE else None


def episode(world, payload, *, learn=True, reward_kind='progress', coverage=False,
            move_budget=64, failure_bonus=-32):
    """A public local diagnostic, NOT an isolated acceptance exam.

    Exactly one scan per physical timestamp, including dynamic camera lag.
    Initial failures have no fabricated predecessor and therefore no Q update.
    """
    if type(move_budget) is not int or not 1 <= move_budget <= 64:
        raise ValueError('move budget')
    if type(failure_bonus) is not int or not -127 <= failure_bonus <= 0:
        raise ValueError('failure bonus')
    if reward_kind not in ('progress', 'step_and_arrival'):
        raise ValueError('reward kind')
    counts = {}
    agent = Student(restore(payload).snapshot(), world.goal,
                    coverage=coverage if learn else False, counts=counts)
    agent.model = CheckedEffects.restore(agent.model.snapshot())
    initial = agent.model.fingerprint()
    frame = world.scan()
    rows = []
    violations = 0
    status = 'training_budget_cut' if learn else 'diagnostic_budget_cut'
    for _ in range(move_budget):
        decision = agent.decide(frame)
        if decision['status'] not in ACTIVE:
            status = decision['status']
            break
        wsp = bytes.fromhex(decision['wsp'])
        if len(wsp) != 16 or wsp[1] != 11 or not 0 <= wsp[13] < 4:
            raise ValueError('planar WSP command')
        action = wsp[13]
        feature = agent.feature()
        before = world.pos
        violations += reserve_violation(world, action)
        consequence = world.step(action)
        after = world.scan()
        agent.update(after)
        outcome = terminal_outcome(agent, after)
        row = dict(observation=frame, decision=decision, consequence=consequence,
                   after=after, outcome=outcome, learning=None)
        if learn:
            value = reward(reward_kind, before, world.pos, world.goal,
                           after['station_observed'])
            if outcome in FAILURES:
                value += failure_bonus
            next_feature = agent.feature()
            agent.model.learn_reward(feature, action, value, next_feature,
                                     terminal=outcome is not None)
            counts.setdefault(feature.hex(), [0]*4)[action] += 1
            row['learning'] = dict(before=feature.hex(), after=next_feature.hex(),
                                   reward=value, terminal=outcome is not None)
        rows.append(row)
        frame = after  # Never scan a second time at this timestamp.
        if outcome is not None:
            status = outcome
            break
    if agent.ingestions != world.steps+1 or sum(agent.visits.values()) != agent.ingestions:
        raise ValueError('capture multiplicity')
    return dict(status=status, moves=world.steps, rows=rows, counts=counts,
                ingestions=agent.ingestions, visits=sum(agent.visits.values()),
                collisions=world.collisions, reserve_violations=violations,
                model_unchanged=initial == agent.model.fingerprint(),
                payload=policy.export(agent.model), isolated=False)
