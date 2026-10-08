"""
Discrete one-step world model T(s, a) → ŝ'.

T and counts are static tables. KCC: a conflicting observation does
not erase the winner until the new value has a strictly higher count.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from echoai.core.qn import hamming16

from echoai.nexus0.constants import (
    ACTION_WAIT,
    INV_MAX_ENTRIES,
    N_ACTIONS,
    N_SLOTS,
    T_CONF_DECENT,
    T_CONF_HIGH,
    T_CONF_HIGH_N,
    T_CONF_NONE,
    T_CONF_ONCE,
    T_MISS_ERROR,
    UNKNOWN_NEXT,
)


class World:
    def __init__(self, n_actions: Optional[int] = None) -> None:
        # OPEN-1: as many columns as the world has gears, defaulting to the
        # frozen three. A four-gear world folded to three would record what
        # `open` did on top of what `approach` did — one row holding two
        # different futures, which is the alias T exists to not have.
        self.n_actions = N_ACTIONS if n_actions is None else int(n_actions)
        self.pred: List[List[int]] = [
            [UNKNOWN_NEXT] * self.n_actions for _ in range(N_SLOTS)
        ]
        self.n: List[List[int]] = [
            [0] * self.n_actions for _ in range(N_SLOTS)
        ]
        self.alt: List[List[int]] = [
            [UNKNOWN_NEXT] * self.n_actions for _ in range(N_SLOTS)
        ]
        self.alt_n: List[List[int]] = [
            [0] * self.n_actions for _ in range(N_SLOTS)
        ]
        self.conflicts: int = 0
        # I(s, s') → a, observed neighbours only. One short list per slot
        # of [s_next, action, count]; empty until something is seen.
        self.inv: List[List[List[int]]] = [[] for _ in range(N_SLOTS)]
        self.inv_dropped: int = 0

    def _s(self, s: int) -> int:
        return int(s) & (N_SLOTS - 1)

    def predict(self, s: int, a: int) -> Optional[int]:
        v = self.pred[self._s(s)][int(a) % self.n_actions]
        if v == UNKNOWN_NEXT:
            return None
        return int(v)

    def observe(self, s: int, a: int, s_next: int) -> None:
        ss = self._s(s)
        aa = int(a) % self.n_actions
        nxt = int(s_next) & (N_SLOTS - 1)
        # The inverse records the observation itself, before T's KCC
        # decides anything: what got taken to reach s' is a fact about
        # this step, not about which s' currently wins the row.
        self._observe_inverse(ss, aa, nxt)
        cur = self.pred[ss][aa]
        if cur == UNKNOWN_NEXT:
            self.pred[ss][aa] = nxt
            self.n[ss][aa] = 1
            return
        if cur == nxt:
            if self.n[ss][aa] < 65535:
                self.n[ss][aa] += 1
            return
        self.conflicts += 1
        if self.alt[ss][aa] != nxt:
            if self.alt[ss][aa] == UNKNOWN_NEXT or self.alt_n[ss][aa] == 0:
                self.alt[ss][aa] = nxt
                self.alt_n[ss][aa] = 1
            else:
                # third value: keep current alt, just count a conflict
                return
        else:
            if self.alt_n[ss][aa] < 65535:
                self.alt_n[ss][aa] += 1
        if self.alt_n[ss][aa] > self.n[ss][aa]:
            self.pred[ss][aa], self.alt[ss][aa] = self.alt[ss][aa], self.pred[ss][aa]
            self.n[ss][aa], self.alt_n[ss][aa] = self.alt_n[ss][aa], self.n[ss][aa]

    def _observe_inverse(self, ss: int, aa: int, nxt: int) -> None:
        row = self.inv[ss]
        for entry in row:
            if entry[0] == nxt and entry[1] == aa:
                if entry[2] < 65535:
                    entry[2] += 1
                return
        if len(row) >= INV_MAX_ENTRIES:
            # Saturated slot. Counted rather than silently forgotten, so a
            # topology that needs more than INV_MAX_ENTRIES shows up as a
            # number instead of as a wrong answer.
            self.inv_dropped += 1
            return
        row.append([nxt, aa, 1])

    def inverse(self, s: int, s_next: int) -> Optional[int]:
        """Which action was taken to get from s to s'? None if unobserved.

        Not a 4096x4096 matrix: only the successors this slot has actually
        been seen to reach. Same KCC discipline as T — the highest count
        wins, and a second action for the same s' does not displace the
        first until it strictly beats it. Ties keep the incumbent, i.e.
        the entry appended first.

        The one fallback: a standstill. If s' is s and `wait` has been
        observed at all from s, the answer is `wait`. Without that
        evidence the answer is None — a stationary step is never guessed
        to be `approach`.
        """
        ss = self._s(s)
        nn = int(s_next) & (N_SLOTS - 1)
        best_a: Optional[int] = None
        best_c = 0
        for nxt, a, c in self.inv[ss]:
            if nxt == nn and c > best_c:
                best_c = c
                best_a = a
        if best_a is not None:
            return best_a
        if ss == nn and self.n[ss][ACTION_WAIT] >= 1:
            return ACTION_WAIT
        return None

    def inv_size(self) -> int:
        """Total entries held by the inverse. The n-squared canary."""
        return sum(len(row) for row in self.inv)

    def error(self, s: int, a: int, s_next: int, vertex_pred: Optional[int],
              vertex_real: int) -> int:
        """Hamming of vertices if both known; else T_MISS_ERROR."""
        if vertex_pred is None:
            return T_MISS_ERROR
        return hamming16(int(vertex_pred), int(vertex_real))

    def known(self, s: int, a: int) -> bool:
        return self.pred[self._s(s)][int(a) % self.n_actions] != UNKNOWN_NEXT

    def conf(self, s: int, a: int) -> int:
        """How good is this row of T? An integer in 0..3, no float.

        `known()` answers yes/no; this answers how well. It reads only the
        counters `observe()` already keeps, so it costs nothing new in the
        fast path.

            n == 0                 → 0   never seen
            n == 1                 → 1   one observation
            n >= 2, alt_n == 0     → 2   consistent
            n >= T_CONF_HIGH_N     → 3   very consistent
            alt_n > 0              → 2 at most, whatever n is

        The cap is the point. In phase F the threat moves and one row
        gets a second, different s'; the winner may keep a high n, but a
        row that was ever contradicted is not the same evidence as a row
        that never was.
        """
        ss = self._s(s)
        aa = int(a) % self.n_actions
        if self.pred[ss][aa] == UNKNOWN_NEXT:
            return T_CONF_NONE
        n = self.n[ss][aa]
        if n <= 0:
            return T_CONF_NONE
        if n == 1:
            return T_CONF_ONCE
        if self.alt_n[ss][aa] > 0:
            return T_CONF_DECENT
        return T_CONF_HIGH if n >= T_CONF_HIGH_N else T_CONF_DECENT

    def pair(self, s: int, a: int) -> Tuple[int, int]:
        ss = self._s(s)
        aa = int(a) % self.n_actions
        return self.pred[ss][aa], self.n[ss][aa]
