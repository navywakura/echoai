"""ARC-3E-POLICY-1: the existing delayed credit mechanism with new actions.

This is a new contextual policy, not village Q values relabelled as ARC skills.
The verifier and the hard work budget belong to the solver, not this policy.
"""
from copy import deepcopy
import json

from seed.village3 import Echo as DelayedEcho, HORIZON

ACTIONS = ('recall_first', 'search_first')


def tuples(value):
    return tuple(tuples(x) for x in value) if isinstance(value, list) else value


class ArcPolicy(DelayedEcho):
    def __init__(self, seed=47000):
        super().__init__(seed)
        self.q = {c: [[0, 0] for _ in ACTIONS] for c in ('single', 'multiple', 'resize')}
        self.events = set()
        self.tickets = {}

    def allowed(self):
        return [0, 1]

    def begin(self, key, context, action, cost, age):
        if key in self.credit or context not in self.q or action not in self.allowed():
            raise ValueError('duplicate ticket or invalid policy decision')
        if any(type(n) is not int or n < 0 for n in (cost, age)):
            raise ValueError('integer cost/age required')
        super().begin(key, context, action, cost, age)
        self.tickets[key] = {'cost': cost, 'verified': False}

    def charge(self, key, cost, event=None):
        if key not in self.credit or type(cost) is not int or cost < 0:
            raise ValueError('known ticket and nonnegative cost required')
        if event is not None:
            tag = (key, str(event))
            if tag in self.events:
                raise ValueError('cost event already charged')
            self.events.add(tag)
        super().charge(key, cost)
        self.tickets[key]['cost'] += cost

    def verified(self, key, reward):
        if key not in self.pending_returns or self.tickets[key]['verified']:
            raise ValueError('pending uncredited verified outcome required')
        if type(reward) is not int or reward < 0:
            raise ValueError('nonnegative integer utility required')
        self.pending_returns[key][1] += reward
        self.tickets[key]['verified'] = True

    def state(self):
        return dict(super().state(), schema='arc-delayed-policy-1', actions=ACTIONS,
                    events=sorted(self.events), tickets=deepcopy(self.tickets))

    @classmethod
    def restore(cls, state):
        if state.get('schema') != 'arc-delayed-policy-1' or tuple(state['actions']) != ACTIONS or state['return_horizon'] != HORIZON:
            raise ValueError('policy schema/actions/horizon mismatch')
        obj = cls()
        if set(state['q']) != set(obj.q):
            raise ValueError('policy contexts changed')
        for c, cells in state['q'].items():
            if len(cells) != 2 or any(len(v) != 2 or any(type(n) is not int for n in v) or v[1] < 0 for v in cells):
                raise ValueError('invalid return table')
        for name in ('q', 'credit', 'pending_returns', 'matured', 'tickets'):
            setattr(obj, name, deepcopy(state[name]))
        obj.events = {tuple(e) for e in state['events']}
        obj.rng.setstate(tuples(state['rng']))
        if set(obj.tickets) != set(obj.credit) or not set(obj.pending_returns) <= set(obj.credit):
            raise ValueError('orphaned delayed consequences')
        if any(c not in obj.q or a not in obj.allowed() for c, a in obj.credit.values()):
            raise ValueError('invalid action credit')
        return obj

    def canonical_state(self):
        return json.loads(json.dumps(self.state()))
