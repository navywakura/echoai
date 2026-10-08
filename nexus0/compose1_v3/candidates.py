"""Cost-aware bounded search; the V2 sensor and execution contract is reused."""
import heapq
from echoai.nexus0.compose1_v2.controller import Composer as Previous
from echoai.nexus0.compose1.controller import add, distance


class Composer(Previous):
    def search(self, target):
        before = self.model.fingerprint()
        values = self.model.values(self.feature()) if self.mode != 'conventional' else [0]*7
        # Queue order and terminal comparison use the same accumulated cost.
        # A cell reached by a worse path must not suppress a later better path.
        frontier = [(0, 0, self.pos, (), 0, (self.pos,))]
        best = {(self.pos, 0): 0}
        generated = 1
        terminals = []
        while frontier:
            _, depth, node, path, visits, ancestors = heapq.heappop(frontier)
            children = []
            if depth < self.max_depth and node != target:
                for action in range(6):
                    delta = self.model.predict(action)
                    if delta is None:
                        continue
                    nxt = add(node, delta)
                    if nxt in ancestors or not self.free(nxt):
                        continue
                    cost = visits+self.visits.get(nxt, 0)*20
                    key = (nxt, depth+1)
                    if best.get(key, 10**12) <= cost or generated >= self.budget:
                        continue
                    best[key] = cost
                    generated += 1
                    priority = distance(nxt, target)*10+depth+1+cost
                    children.append((priority, depth+1, nxt, path+(action,), cost, ancestors+(nxt,)))
            if path and (not children or node == target):
                score = -10000+depth if node == target else distance(node, target)*10+depth+visits
                terminals.append((score, -depth, -values[path[0]], path))
            for child in children:
                heapq.heappush(frontier, child)
        self.imagined_writes += before != self.model.fingerprint()
        return (list(min(terminals)[3]) if terminals else []), generated


class PrefixWait(Previous):
    """A-only alternate: compare prefixes at an equal padded horizon."""
    def search(self, target):
        before = self.model.fingerprint()
        values = self.model.values(self.feature()) if self.mode != 'conventional' else [0]*7
        frontier = [(0, 0, self.pos, (), 0, (self.pos,))]
        generated = 1
        terminals = []
        while frontier:
            _, depth, node, path, visits, ancestors = heapq.heappop(frontier)
            if path:
                score = -10000+depth if node == target else distance(node, target)*10+self.max_depth+visits
                terminals.append((score, -depth, -values[path[0]], path))
            if depth >= self.max_depth or node == target:
                continue
            for action in range(6):
                delta = self.model.predict(action)
                if delta is None:
                    continue
                nxt = add(node, delta)
                if nxt in ancestors or not self.free(nxt) or generated >= self.budget:
                    continue
                generated += 1
                cost = visits+self.visits.get(nxt, 0)*20
                heapq.heappush(frontier, (distance(nxt, target)*10+cost, depth+1, nxt,
                                        path+(action,), cost, ancestors+(nxt,)))
        self.imagined_writes += before != self.model.fingerprint()
        return (list(min(terminals)[3]) if terminals else []), generated
