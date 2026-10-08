"""Plan B1 planner: burst-aware admissibility and a reserve consistent with belief.

Two changes over `planner_a2`, both applied identically to every arm:

* the admissibility gate checks **every cell the burst traverses**, not only its
  endpoint, so a multi-cell actuation cannot be commanded into a wall;
* the reserve estimate divides distance by the agent's own believed reach.

The second is a deliberate departure from Plan A, where the reserve constant was
frozen so that learning could not buy safety. Here a gate that assumes one cell
per actuation is simply false for a burst body, and forcing it on a calibrated
arm is not fairness but sabotage. The rule is identical in every arm; only the
belief it reads differs, which is the factor under test.
"""
import heapq

from echoai.nexus0.compose1.controller import add, distance
from . import costs_a2
from .planner_a2 import CostPlanner, GOAL_BONUS, REVISIT_PENALTY


def unit(delta):
    return tuple(0 if v == 0 else (1 if v > 0 else -1) for v in delta)


class GainPlanner(CostPlanner):
    def believed_reach(self):
        spans = [sum(abs(v) for v in (self.model.predict(a) or (0, 0, 0)))
                 for a in range(costs_a2.PLANAR)]
        return max(spans) or 1

    def per_cell_reserve(self):
        return max(1, -(-self.reserve//self.believed_reach()))

    def free_path(self, node, delta):
        step, pos = unit(delta), node
        for _ in range(sum(abs(v) for v in delta)):
            pos = add(pos, step)
            if not self.free(pos):
                return False
        return True

    def search(self, target):
        before = self.model.fingerprint()
        base, turn = self.believed
        reach = self.believed_reach()
        cheapest = min(base)
        frontier = [(0, 0, self.pos, (), self.last_action, (self.pos,), 0)]
        generated, terminals = 1, []
        while frontier:
            _, depth, node, path, heading, ancestors, spent = heapq.heappop(frontier)
            if path:
                score = (spent-GOAL_BONUS if node == target
                         else spent+cheapest*distance(node, target)//reach)
                terminals.append((score, -depth, path))
            if depth >= self.max_depth or node == target:
                continue
            for action in range(costs_a2.PLANAR):
                delta = self.model.predict(action)
                if delta is None:
                    continue
                nxt = add(node, delta)
                if nxt in ancestors or not self.free_path(node, delta) or generated >= self.budget:
                    continue
                generated += 1
                step = base[action]+(turn if heading >= 0 and heading != action else 0)
                cost = spent+step+REVISIT_PENALTY*self.visits.get(nxt, 0)
                heapq.heappush(frontier, (cost+cheapest*distance(nxt, target)//reach, depth+1,
                                          nxt, path+(action,), action, ancestors+(nxt,), cost))
        self.imagined_writes += before != self.model.fingerprint()
        return (list(min(terminals)[2]) if terminals else []), generated

    def decide(self, frame):
        self.pending = []
        self.update(frame)
        self.turns += 1
        if frame['station_observed'] and self.pos == self.goal:
            return self.output(6, [], 'reached', 0)
        if self.turns > 64:
            return self.output(6, [], 'budget_exhausted', 0)
        per_cell = self.per_cell_reserve()
        if self.energy < (distance(self.pos, self.goal)+distance(self.goal, self.home))*per_cell+10:
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
        if home is None or self.energy-self.reserve < len(home)*per_cell+10:
            self.returning = True
            if self.pos == self.home:
                return self.output(6, [], 'abandoned_at_home', count)
            path = self.route_home(self.pos) or []
            if not path:
                return self.output(6, [], 'return_not_found', count)
            action = path[0]
        if not self.free_path(self.pos, self.model.predict(action)):
            return self.output(6, [], 'evidence_block', count)
        return self.output(action, path, 'returning' if self.returning else 'moving', count)
