"""Plan A2 planner: identical logic to A1, with an isolation-safe import graph.

The only change from `planner_a1` is that cost arithmetic and calibration come
from `costs_a2`, which knows nothing about worlds, so this module can be shipped
into the cage without shipping the simulator. Behaviour is unchanged and a test
pins that: on the historical rooms both planners produce the same routes.
"""
import heapq

from echoai.nexus0.compose1.controller import add, distance
from echoai.nexus0.compose1_v3.controller import Composer as Previous
from . import costs_a2

REVISIT_PENALTY = 2*costs_a2.NOMINAL_BASE
GOAL_BONUS = 10**6


class CostPlanner(Previous):
    def __init__(self, model, goal, calibration, *, learning=False,
                 reserve=costs_a2.RESERVE_DEFAULT):
        super().__init__(model, goal)
        costs_a2.validate(calibration)
        if type(reserve) is not int or not 1 <= reserve <= 14:
            raise ValueError('reserve constant out of declared range')
        self.calibration = costs_a2.restore(calibration) if learning else None
        self.believed = (list(calibration['base']), calibration['turn'])
        self.learning = bool(learning)
        self.reserve = reserve
        self.last_action = -1
        self.pending_obs = None
        self.observations = 0

    def frozen(self):
        return self.believed if not self.learning else self.calibration.resolve()

    def update(self, frame):
        previous = self.pending_obs
        super().update(frame)
        if previous is None:
            return
        heading, action, before = previous
        spent = before-self.energy
        self.pending_obs = None
        if spent <= 0:
            return
        self.observations += 1
        if self.learning:
            self.calibration.observe(None if heading < 0 else heading, action, spent)
            self.believed = self.calibration.resolve()

    def output(self, action, path, status, count):
        result = super().output(action, path, status, count)
        if action != 6:
            self.pending_obs = (self.last_action, action, self.energy)
            self.last_action = action
        return result

    def search(self, target):
        before = self.model.fingerprint()
        base, turn = self.believed
        cheapest = min(base)
        frontier = [(0, 0, self.pos, (), self.last_action, (self.pos,), 0)]
        generated = 1
        terminals = []
        while frontier:
            _, depth, node, path, heading, ancestors, spent = heapq.heappop(frontier)
            if path:
                score = spent-GOAL_BONUS if node == target else spent+cheapest*distance(node, target)
                terminals.append((score, -depth, path))
            if depth >= self.max_depth or node == target:
                continue
            for action in range(costs_a2.PLANAR):
                delta = self.model.predict(action)
                if delta is None:
                    continue
                nxt = add(node, delta)
                if nxt in ancestors or not self.free(nxt) or generated >= self.budget:
                    continue
                generated += 1
                step = base[action]+(turn if heading >= 0 and heading != action else 0)
                cost = spent+step+REVISIT_PENALTY*self.visits.get(nxt, 0)
                heapq.heappush(frontier, (cost+cheapest*distance(nxt, target), depth+1,
                                          nxt, path+(action,), action, ancestors+(nxt,), cost))
        self.imagined_writes += before != self.model.fingerprint()
        return (list(min(terminals)[2]) if terminals else []), generated

    def decide(self, frame):
        """`echo32` only. Reserve arithmetic is parameterised, not rescaled."""
        self.pending = []
        self.update(frame)
        self.turns += 1
        if frame['station_observed'] and self.pos == self.goal:
            return self.output(6, [], 'reached', 0)
        if self.turns > 64:
            return self.output(6, [], 'budget_exhausted', 0)
        reserve = self.reserve
        if self.energy < (distance(self.pos, self.goal)+distance(self.goal, self.home))*reserve+10:
            self.returning = True
        if self.returning and self.pos == self.home:
            return self.output(6, [], 'abandoned_at_home', 0)
        if self.returning:
            path, count = self.route_home(self.pos) or [], 0
        else:
            path, count = self.search(self.goal)
        if not path:
            return self.output(6, [], 'access_not_found', count)
        action = path[0]
        home = self.route_home(add(self.pos, self.model.predict(action)))
        if home is None or self.energy-reserve < len(home)*reserve+10:
            self.returning = True
            if self.pos == self.home:
                return self.output(6, [], 'abandoned_at_home', count)
            path = self.route_home(self.pos) or []
            if not path:
                return self.output(6, [], 'return_not_found', count)
            action = path[0]
        nxt = add(self.pos, self.model.predict(action))
        if not self.free(nxt):
            return self.output(6, [], 'evidence_block', count)
        return self.output(action, path, 'returning' if self.returning else 'moving', count)
