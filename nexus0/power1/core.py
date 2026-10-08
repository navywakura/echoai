"""Cost gate, not a planner. Every movement output is the existing 16-byte WSP."""
import copy
from echoai.nexus0.cause1.core import wsp

TTL = 250_000_000
RESERVE = 40
PHASES = ('0', '1', 'land')
UNITS = ('sim_u', 'mC')


def integer(value, low=0, high=10**12):
    return type(value) is int and low <= value <= high


class Model:
    def __init__(self, snapshot):
        if (type(snapshot) is not dict or set(snapshot) != {'unit', 'costs'}
                or snapshot['unit'] not in UNITS or type(snapshot['costs']) is not dict
                or not set(snapshot['costs']) <= set(PHASES)):
            raise ValueError('model schema')
        for cost in snapshot['costs'].values():
            if (type(cost) is not dict or set(cost) != {'n', 'nominal', 'maximum', 'upper'}
                    or not all(integer(v, 1) for v in cost.values()) or cost['n'] < 8
                    or not cost['nominal'] <= cost['maximum'] <= cost['upper']
                    or cost['upper'] != (cost['maximum']*125+99)//100):
                raise ValueError('cost model')
        self.data = copy.deepcopy(snapshot)

    def snapshot(self):
        return copy.deepcopy(self.data)

    @classmethod
    def fit(cls, records, unit='sim_u'):
        samples = {phase: [] for phase in PHASES}
        last = -1
        for row in records:
            if (set(row) != {'seq', 'phase', 'before', 'after', 'elapsed_ms', 'confirmed', 'unit'}
                    or row['unit'] != unit or row['phase'] not in PHASES
                    or row['confirmed'] is not True or not integer(row['seq']) or row['seq'] <= last
                    or not integer(row['before']) or not integer(row['after'])
                    or not integer(row['elapsed_ms'], 1, 60000)
                    or row['before'] <= row['after']):
                raise ValueError('unconfirmed/invalid consumption receipt')
            samples[row['phase']].append(row['before']-row['after'])
            last = row['seq']
        costs = {}
        for phase, values in samples.items():
            if len(values) >= 8:
                maximum = max(values)
                costs[phase] = dict(n=len(values), nominal=(sum(values)+len(values)-1)//len(values),
                                    maximum=maximum, upper=(maximum*125+99)//100)
        return cls(dict(unit=unit, costs=costs))

    def route(self, path, field='upper'):
        if path is None:
            return None
        if type(path) is not list or len(path) > 64 or any(type(a) is not int or a not in (0, 1) for a in path):
            raise ValueError('bounded route')
        if any(str(a) not in self.data['costs'] for a in path):
            return None
        return sum(self.data['costs'][str(a)][field] for a in path)


def valid_frame(frame, unit):
    if type(frame) is not dict or set(frame) != {'now_ns', 'battery', 'routes', 'at_home', 'goal_reached'}:
        return False
    battery, routes = frame['battery'], frame['routes']
    return (integer(frame['now_ns']) and type(battery) is dict
            and set(battery) == {'capture_ns', 'remaining', 'capacity', 'unit'}
            and battery['unit'] == unit and integer(battery['capture_ns'])
            and 0 <= frame['now_ns']-battery['capture_ns'] <= TTL
            and integer(battery['capacity'], 1) and integer(battery['remaining'])
            and battery['remaining'] <= battery['capacity']
            and type(routes) is dict and set(routes) == {'out', 'goal_home', 'home'}
            and all(p is None or (type(p) is list and len(p) <= 64
                    and all(type(a) is int and a in (0, 1) for a in p)) for p in routes.values())
            and type(frame['at_home']) is bool and type(frame['goal_reached']) is bool
            and frame['at_home'] == (routes['home'] == [])
            and frame['goal_reached'] == (routes['out'] == []))


class Guard:
    def __init__(self, snapshot, policy='cost'):
        if policy not in ('cost', 'fixed'):
            raise ValueError('policy')
        self.model = Model(snapshot)
        self.policy = policy
        self.returning = False
        self.stopped = False
        self.last_capture = -1
        self.last_now = -1
        self.last_remaining = None
        self.capacity = None

    def decide(self, frame):
        def output(action, reason, **details):
            if action == 6:
                self.stopped = True
            return dict(wsp=wsp(action), reason=reason, returning=self.returning,
                        stopped=self.stopped, **details)

        if self.stopped:
            return output(6, 'session_closed')
        if not valid_frame(frame, self.model.data['unit']):
            return output(6, 'unknown_evidence', viable=False)
        battery, routes = frame['battery'], frame['routes']
        remaining = battery['remaining']
        if (battery['capture_ns'] <= self.last_capture or frame['now_ns'] <= self.last_now
                or (self.last_remaining is not None and remaining > self.last_remaining)
                or (self.capacity is not None and battery['capacity'] != self.capacity)):
            return output(6, 'battery_discontinuity', viable=False)
        self.last_capture = battery['capture_ns']
        self.last_now = frame['now_ns']
        self.last_remaining = remaining
        self.capacity = battery['capacity']
        landed_cost = self.model.data['costs'].get('land')
        if landed_cost is None:
            return output(6, 'unknown_landing', viable=False)
        landing = landed_cost['upper']
        out = self.model.route(routes['out'])
        home_goal = self.model.route(routes['goal_home'])
        home = self.model.route(routes['home'])
        mission = None if out is None or home_goal is None else out+home_goal+landing+RESERVE
        retreat = None if home is None else home+landing+RESERVE
        details = dict(mission_required=mission, return_required=retreat,
                       landing_required=landing+RESERVE, remaining=remaining, unit=battery['unit'])
        if frame['goal_reached']:
            self.returning = True
        if self.policy == 'cost':
            if mission is None or remaining < mission:
                self.returning = True
        elif remaining*100 < battery['capacity']*20:
            self.returning = True
        if self.returning and frame['at_home']:
            return output(6, 'land_home', viable=remaining >= landing+RESERVE, **details)
        if self.returning:
            if retreat is None or (self.policy == 'cost' and remaining < retreat):
                return output(6, 'land_local', viable=remaining >= landing+RESERVE, **details)
            return output(routes['home'][0], 'return', viable=True, **details)
        if routes['out'] is None or not routes['out']:
            return output(6, 'unknown_route', viable=False, **details)
        return output(routes['out'][0], 'continue', viable=True, **details)
