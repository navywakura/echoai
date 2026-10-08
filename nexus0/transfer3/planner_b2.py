"""B2 reuses B1; safe reserve never discounts all directions by one gain."""
from collections import deque
from echoai.nexus0.compose1.controller import add
from echoai.nexus0.fusion1.core import unpack
from .planner_b1 import GainPlanner, unit


class Planner(GainPlanner):
    def __init__(self, *args, safe=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.safe = safe

    def per_cell_reserve(self):
        return self.reserve if self.safe else super().per_cell_reserve()

    def route_home(self, p):
        if not self.safe:
            return super().route_home(p)
        known = {cell for cell,m in self.cells.items() if m.records and
                 unpack(bytes.fromhex(m.records[-1]['wsp']))[0] == 0}
        queue, seen = deque([(p, [])]), {p}
        while queue:
            node, path = queue.popleft()
            if node == self.home:
                return path
            for a in range(4):
                delta = self.model.predict(a)
                if delta is None:
                    continue
                nxt, clear = node, True
                for _ in range(sum(abs(v) for v in delta)):
                    nxt = add(nxt, unit(delta))
                    if nxt not in known:
                        clear = False
                        break
                if clear and nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path+[a]))
        return None
