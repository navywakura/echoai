"""v5.8: order/count memories over observed object entries, extending frozen v5.7."""
from collections import Counter, deque

import numpy as np

from echo_arc.agent import Arc3EchoV57, _components
from echo_arc.temporal_memory import CountMemory, OrderMemory


class Arc3EchoV58(Arc3EchoV57):
    ORDER_ENABLED = True
    COUNT_ENABLED = True
    MAX_MARKERS = 8
    MAX_PROBE = 8
    MAX_SEARCH = 4000

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.order_memory = OrderMemory()
        self.count_memory = CountMemory(complete=False)
        self.markers = {}
        self.temporal_queue = deque()
        self.temporal_trials = Counter()
        self.temporal_effect = None
        self.temporal_effect_active = False
        self.temporal_decision = None
        self.temporal_steps = 0
        self.temporal_entries = 0
        self._temporal_act = None
        self._temporal_transition = None
        self._temporal_occupied = None
        self.temporal_state = {}

    def _enabled(self):
        return self.ORDER_ENABLED or self.COUNT_ENABLED

    def _motor_ready(self):
        return (self.me is not None and self.pos is not None and len(self.my_cells) == 1
                and not self._click_mode() and not self.mode_keys and not self.pushable
                and self.keys and all(k in self.rule for k in self.keys)
                and all(k in self.available for k in self.keys)
                and all(self.key_tries[k] >= self.babble for k in self.keys))

    def _read_markers(self, frame):
        if not self._motor_ready():
            return
        cells = self.my_cells[0]
        ys, xs = [y for y, _ in cells], [x for _, x in cells]
        bh, bw = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
        if len(cells) != bh * bw:
            return
        for n, pts, c in _components(frame):
            if c == self.me[0] or n >= len(cells) or not pts:
                continue
            if self.clock is not None and any(self.clock[y, x] for y, x in pts):
                continue
            py, px = [y for y, _ in pts], [x for _, x in pts]
            if (max(py) - min(py) + 1, max(px) - min(px) + 1) != (bh, bw):
                continue
            centre = (sum(px) * 2 // n, sum(py) * 2 // n)
            if centre not in self.markers and len(self.markers) >= self.MAX_MARKERS:
                continue
            self.markers[centre] = int(c)

    def _remote_change(self, before, after, old_cells):
        if before is None or before.shape != after.shape or not old_cells or not self.my_cells:
            return None
        floor = self.passed.most_common(1)[0][0] if self.passed else None
        if floor is None:
            return None
        changed = before != after
        changed[0, :] = changed[-1, :] = changed[:, 0] = changed[:, -1] = False
        if self.clock is not None:
            changed &= ~self.clock
        for inst in list(old_cells) + list(self.my_cells):
            for y, x in inst:
                changed[y, x] = False
        removed = changed & (after == floor) & (before != floor)
        added = changed & (before == floor) & (after != floor)
        minimum = max(2, len(self.my_cells[0]) // 2)
        for mode, mask in (("removed", removed), ("added", added)):
            pts = np.argwhere(mask)
            if len(pts) >= minimum:
                return {"change": mode, "pixels": len(pts),
                        "region": [int(pts[:, 0].min()), int(pts[:, 1].min()),
                                   int(pts[:, 0].max()), int(pts[:, 1].max())]}
        return None

    def observe_state(self, frame):
        before, pos0, cells0, me0 = self.last_frame, self.pos, self.my_cells, self.me
        st = super().observe_state(frame)
        self._temporal_transition = None
        if self._enabled() and self._motor_ready():
            f = np.asarray(frame)
            if before is not None and before.shape == f.shape:
                self._read_markers(before)
            self._read_markers(f)
            act = self._temporal_act
            if act and act[0] == "K" and act[1] in self.rule and me0 == self.me and pos0 is not None:
                d = self.rule[act[1]]
                actual = (self.pos[0] - pos0[0], self.pos[1] - pos0[1])
                # A teleport/reset does not teach entries or counts.
                if actual in ((0, 0), d):
                    marker = self.pos if self.pos in self.markers else None
                    change = self._remote_change(before, f, cells0)
                    self._temporal_transition = (marker, change, actual != (0, 0))
        self._snapshot_temporal()
        return st

    def _walk_exact(self, goal):
        if self.pos is None or not self.my_cells or not self.rule:
            return None
        cells = [p for inst in self.my_cells for p in inst]
        fm = self._fitmap(self.last_frame, cells, set(cells), self._walls())
        prev, queue = {(0, 0): None}, deque([(0, 0)])
        while queue and len(prev) <= self.MAX_SEARCH:
            off = queue.popleft()
            p = (self.pos[0] + 2 * off[1], self.pos[1] + 2 * off[0])
            if abs(p[0] - goal[0]) + abs(p[1] - goal[1]) <= 1:
                path = []
                while prev[off] is not None:
                    off, key = prev[off]
                    path.append(key)
                return list(reversed(path))
            for key, (dx, dy) in sorted(self.rule.items()):
                nxt = (off[0] + dy // 2, off[1] + dx // 2)
                if nxt in prev or (p, key) in self.blocked:
                    continue
                if -64 <= nxt[0] <= 64 and -64 <= nxt[1] <= 64 and fm[nxt[0] + 64, nxt[1] + 64]:
                    prev[nxt] = (off, key)
                    queue.append(nxt)
        return None

    def _leave_marker(self):
        cells = self.my_cells[0]
        for key, (dx, dy) in sorted(self.rule.items()):
            if (self.pos, key) in self.blocked:
                continue
            if (-dx, -dy) not in self.rule.values():
                continue
            if self._fits(self.last_frame, cells, set(cells), dy // 2, dx // 2, self._walls()):
                return key
        return None

    def _make_trial(self):
        reachable = {p: self._walk_exact(p) for p in sorted(self.markers)}
        reachable = {p: route for p, route in reachable.items() if route is not None}
        if not reachable:
            return
        by_kind = {}
        for p in reachable:
            by_kind.setdefault(self.markers[p], []).append(p)
        if self.ORDER_ENABLED:
            for pair in self.order_memory.candidates():
                if all(c in by_kind for c in pair):
                    ps = tuple(by_kind[c][0] for c in pair)
                    if self.temporal_trials[("order", ps)] == 0:
                        self.temporal_trials[("order", ps)] += 1
                        self.temporal_queue.extend(ps)
                        self.temporal_decision = {"module": "H1", "operation": "test_learned_order", "sequence": list(pair)}
                        return
        if self.COUNT_ENABLED:
            for p in sorted(reachable):
                n = self.count_memory.threshold(self.markers[p])
                have = self.count_memory.counts[p]
                if n is not None and have < n:
                    self.temporal_queue.extend([p] * min(n - have, self.MAX_PROBE))
                    self.temporal_decision = {"module": "H3", "operation": "test_learned_count", "entries": n, "have": have}
                    return
        trials = []
        for a, route in reachable.items():
            if self.COUNT_ENABLED and self.count_memory.counts[a] < self.MAX_PROBE:
                pair = (a, a)
                trials.append((self.temporal_trials[("probe", pair)], len(route), pair))
            if self.ORDER_ENABLED:
                for b in reachable:
                    if a != b:
                        pair = (a, b)
                        distance = abs(a[0] - b[0]) + abs(a[1] - b[1])
                        step = max(max(abs(x), abs(y)) for x, y in self.rule.values())
                        trials.append((self.temporal_trials[("probe", pair)], len(route) + distance // max(1, step), pair))
        if trials:
            _, _, pair = min(trials)
            self.temporal_trials[("probe", pair)] += 1
            self.temporal_queue.extend(pair)
            self.temporal_decision = {"module": "H3" if pair[0] == pair[1] else "H1", "operation": "probe", "targets": list(pair)}

    def _temporal_step(self):
        if not self._motor_ready() or len(self.markers) < 2 or self.path:
            return None
        if self.temporal_effect_active:
            last = set(self.count_memory.counts)
            choices = []
            for p, c in self.markers.items():
                route = self._walk_exact(p)
                if route:
                    choices.append((int(p in last), -self.goal_colours[c], len(route), p, route))
            if choices:
                *_, p, route = min(choices)
                self.temporal_decision = {"module": "temporal", "operation": "explore_after_effect", "target": p}
                return route[0]
            return None
        if not self.temporal_queue:
            self._make_trial()
        if not self.temporal_queue:
            return None
        p = self.temporal_queue[0]
        if self.temporal_decision is None:
            self.temporal_decision = {"module": "H1/H3", "operation": "execute_entry_trial", "next": p}
        route = self._walk_exact(p)
        if route is None:
            self.temporal_queue.clear()
            return None
        if route:
            return route[0]
        # Being on the marker is not an entry. Leave, then come back.
        self.temporal_decision = dict(self.temporal_decision, reenter=p)
        return self._leave_marker()

    def choose(self, state):
        self.temporal_decision = None
        if self._enabled() and not self._motor_ready():
            self.count_memory.complete = False
        key = self._temporal_step() if self._enabled() else None
        if key is not None:
            self.last_key = key
            self.key_tries[key] += 1
            self._last_mode = None
            self.temporal_steps += 1
            act = ("K", key, None)
        else:
            act = super().choose(state)
        self._temporal_act = act
        self._snapshot_temporal()
        return act

    def _reset_temporal(self, level_up):
        self.order_memory.reset()
        self.count_memory.reset(complete=self._motor_ready())
        self.temporal_queue.clear()
        self.temporal_effect_active = False
        self._temporal_occupied = None
        self._temporal_transition = None
        if level_up:
            self.markers.clear()
            self.temporal_trials.clear()

    def learn(self, state, act, next_state, game_over, level_up):
        transition = self._temporal_transition
        if self._enabled() and transition is not None and not game_over and not level_up and act[0] != "R":
            marker, change, moved = transition
            was_open = self.temporal_effect_active
            opened = change is not None and change["change"] == "removed"
            if change is not None:
                self.temporal_effect = change
                self.temporal_effect_active = opened
                self.temporal_queue.clear()
                # Geometry changed; old blocked edges must be tested anew.
                self.blocked.clear()
            if moved and marker != self._temporal_occupied:
                if marker is not None:
                    c = self.markers[marker]
                    self.temporal_entries += 1
                    if self.ORDER_ENABLED:
                        pair = self.order_memory.enter(c, effect=opened, evaluate=not was_open)
                        if pair is not None:
                            self.hypotheses.append((self.level, ("entry_order", pair), "proposed"))
                    if self.COUNT_ENABLED:
                        n = self.count_memory.position(marker, c, effect=opened, evaluate=not was_open)
                        if opened and n is not None:
                            self.hypotheses.append((self.level, ("entry_count", c, n), "proposed"))
                    else:
                        # Episode occupancy is observational state, not a learned count rule.
                        self.count_memory.position(marker, c)
                    if self.temporal_queue and self.temporal_queue[0] == marker:
                        self.temporal_queue.popleft()
                else:
                    self.count_memory.position(None)
                self._temporal_occupied = marker
        super().learn(state, act, next_state, game_over, level_up)
        if game_over or level_up or act[0] == "R":
            self._reset_temporal(level_up)
        self._temporal_act = None
        self._temporal_transition = None
        self._snapshot_temporal()

    def _snapshot_temporal(self):
        self.temporal_state = {"order_enabled": self.ORDER_ENABLED, "count_enabled": self.COUNT_ENABLED,
                               "decision": self.temporal_decision, "queue": list(self.temporal_queue),
                               "counts": [[list(p), n] for p, n in self.count_memory.counts.items()],
                               "orders": self.order_memory.report(), "thresholds": self.count_memory.report(),
                               "coverage_complete": self.count_memory.complete, "effect": self.temporal_effect,
                               "effect_active": self.temporal_effect_active, "steps": self.temporal_steps,
                               "entries": self.temporal_entries}

    def report(self):
        return dict(super().report(), temporal=self.temporal_state)


class Arc3EchoV58NoOrder(Arc3EchoV58):
    ORDER_ENABLED = False


class Arc3EchoV58NoCount(Arc3EchoV58):
    COUNT_ENABLED = False


class Arc3EchoV58NoMemory(Arc3EchoV58):
    ORDER_ENABLED = False
    COUNT_ENABLED = False
