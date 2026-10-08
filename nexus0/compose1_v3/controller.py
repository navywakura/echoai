"""Cost-aware bounded search; the V2 sensor and execution contract is reused."""
import heapq
from echoai.nexus0.compose1_v2.controller import Composer as Previous
from echoai.nexus0.compose1.controller import add, distance


class Composer(Previous):
    """Compare progress and revisits with a common horizon regularizer."""
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
