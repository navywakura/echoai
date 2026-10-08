"""
Integer Q-table for NEXUS-0.

    Q[4096][3] int8     12288 B
    δ = r + ((7 * max Q[s']) >> 3) - Q[s,a]
    Q ← clip_i8(Q + (δ >> 2))     # α = 1/4

Does not touch WSP. CAM stores episodes; this stores policy.
"""

from __future__ import annotations

from math import gcd
from typing import List, Optional, Sequence, Tuple

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_WAIT,
    ALPHA_SHIFT,
    EPS_PERIOD,
    GAMMA_DEN,
    GAMMA_NUM,
    N_ACTIONS,
    N_SLOTS,
    TRACE_CREDIT,
    TRACE_MAX,
    TRACE_SHIFT,
)
from echoai.nexus0.types import clip_i8


def trunc_div(x: int, shift: int = ALPHA_SHIFT) -> int:
    """x / 2**shift, truncated **toward zero**. Not Python's `>>`.

    `(-5) >> 2` is -2: the arithmetic shift floors, so a negative delta of
    -5 would pay -2 where +5 pays +1, and the remainder below would owe
    credit that was already spent. 5 -> 1, 3 -> 0, -3 -> 0, -5 -> -1.
    Integers only: no divmod on negatives, no float, no round().
    """
    n = abs(int(x)) >> int(shift)
    return -n if x < 0 else n


class QTable:
    def __init__(self, trace: bool = False, remainder: bool = False,
                 explore_flat: bool = False,
                 n_actions: Optional[int] = None,
                 inherited_b: int = 0) -> None:
        # OPEN-1: how many gears this table has. `None` is the frozen
        # `constants.N_ACTIONS`, which is 3 and stays 3 — the ring, the
        # corridor, the cube and the jar-less worlds all get exactly the
        # table they always had, down to the width of every row. A world
        # that has grown a fourth verb because it grew a fourth physics
        # asks for it by name, and only that world pays for it.
        self.n_actions = N_ACTIONS if n_actions is None else int(n_actions)
        if self.n_actions < N_ACTIONS:
            raise ValueError("a world cannot have fewer gears than three")
        if type(inherited_b) is not int or inherited_b not in (-1, 0, 1):
            raise ValueError("inherited_b must be one of -1, 0, 1")
        # GEN-1: one inherited integer changes only how often a settled
        # policy explores.  Zero is the exact historical period.
        self.inherited_b = inherited_b
        self.q: List[List[int]] = [
            [0] * self.n_actions for _ in range(N_SLOTS)
        ]
        # NEXUS-3b eligibility traces, opt-in. Default off: update() then
        # is byte-for-byte the one that produced [-12, +5, 0].
        self.trace = bool(trace)
        # PULPO-C: let a flat row be explored instead of always answering
        # `approach`. Opt-in, default off, and it costs no memory at all —
        # see select(). Nothing in update() reads it.
        self.explore_flat = bool(explore_flat)
        # CREDIT-1: keep the crumbs that `delta >> 2` throws away, opt-in.
        # Default off, and off means **no array at all** — the ring pays
        # nothing for a lever it does not pull, and `update` takes exactly
        # the branch it always took.
        self.remainder = bool(remainder)
        if self.remainder and self.trace:
            raise ValueError("traces and the remainder are two answers to "
                             "the same question; pick one")
        self.rem: List[List[int]] = (
            [[0] * self.n_actions for _ in range(N_SLOTS)]
            if self.remainder else []
        )
        self.z: List[List[int]] = (
            [[0] * self.n_actions for _ in range(N_SLOTS)]
            if self.trace else []
        )
        # Only the handful of (s,a) with z>0 are ever touched. With
        # credit 16 and a 7/8 decay a trace dies after ~12 steps.
        self._active: List[Tuple[int, int]] = []

    def reset_traces(self) -> None:
        for s, a in self._active:
            self.z[s][a] = 0
        self._active = []

    def _s(self, s: int) -> int:
        return int(s) & (N_SLOTS - 1)

    def get(self, s: int, a: int) -> int:
        return self.q[self._s(s)][int(a) % self.n_actions]

    def set(self, s: int, a: int, v: int) -> None:
        self.q[self._s(s)][int(a) % self.n_actions] = clip_i8(v)

    def row(self, s: int) -> List[int]:
        return list(self.q[self._s(s)])

    def max_q(self, s: int) -> int:
        row = self.q[self._s(s)]
        return max(row)

    def best(self, s: int) -> int:
        """argmax. Full tie → wait. Partial tie prefers wait."""
        row = self.q[self._s(s)]
        m = max(row)
        winners = [i for i, v in enumerate(row) if v == m]
        if ACTION_WAIT in winners:
            return ACTION_WAIT
        return winners[0]

    def margin(self, s: int) -> int:
        """ΔQ: best minus runner-up. 0 on a full tie, never negative.

        How much the policy prefers its own answer. Small means the fast
        loop is nearly indifferent, which is the only place a deeper look
        can change anything.
        """
        row = sorted(self.q[self._s(s)], reverse=True)
        return int(row[0] - row[1])

    def flat(self, row: Sequence[int]) -> bool:
        """No column prefers anything. With four gears the tie is all four.

        The three-gear branch is the literal expression this has always
        been, so a table of the frozen width takes exactly the comparison
        it took before OPEN-1 existed. A row of four that only tied on its
        first three would read as settled while `open` still had a vote.
        """
        if self.n_actions == N_ACTIONS:
            return row[0] == row[1] == row[2]
        return min(row) == max(row)

    def is_explore(self, s: int, turn: int, greedy: bool = False) -> bool:
        """True when select() explores instead of exploiting.

        Single source of truth: select() below is written on top of it, and
        a caller that wants to substitute its own exploit step (a planner)
        must not steal the exploration turns or the ring is never walked.
        """
        if greedy:
            return False
        row = self.q[self._s(s)]
        if self.flat(row):
            return True
        period = self.exploration_period()
        return bool(period) and int(turn) % period == 0

    def exploration_period(self) -> int:
        """GEN-1's only causal effect: 4, 8 or 16 integer turns."""
        if not EPS_PERIOD:
            return 0
        if self.inherited_b < 0:
            return EPS_PERIOD >> 1
        if self.inherited_b > 0:
            return EPS_PERIOD << 1
        return EPS_PERIOD

    def select(self, s: int, turn: int, greedy: bool = False) -> int:
        """ε-greedy. Full tie during training → approach so the ring is visited.

        `explore_flat` is PULPO-C's one lever. With it off — the default,
        and what the ring measures — a flat row always answers `approach`,
        so the only action ever tried at an untouched state is the one that
        walks forward. A turn is therefore discovered only where walking
        forward hurts: against stone. A turn in open air is invisible.

        With it on, a flat row takes the same `turn % N_ACTIONS` cycle a
        non-flat row already takes on an exploration turn, so `avoid` gets
        its go. Exploitation is untouched: `best()` still decides every
        greedy turn and every non-exploring turn.
        """
        if not self.is_explore(s, turn, greedy):
            return self.best(s)
        row = self.q[self._s(s)]
        if self.flat(row):
            if not self.explore_flat:
                return ACTION_APPROACH
            # A flat row explores on *every* turn, so consecutive turns
            # already walk every gear whatever the width is.
            return int(turn) % self.n_actions
        return self._settled_phase(turn) % self.n_actions

    def _settled_phase(self, turn: int) -> int:
        """The phase an exploration turn on a settled row counts from.

        A settled row only explores when `turn % EPS_PERIOD == 0`, so the
        gear it is offered is `(EPS_PERIOD * k) % n_actions` — which walks
        every gear only when the two moduli are coprime. With period 8 and
        three gears that is 0, 2, 1, 0, 2, 1: all three, which is what the
        ring has always had and why this branch is the plain `turn` for a
        table of the frozen width. With four gears it is 0, 0, 0, 0 for
        ever: `approach` at every settled state in the run, and `open`
        offered at none of them — the verb would be unlearnable for a
        reason that has nothing to do with the lid. When the two share a
        factor the count of exploration turns is used instead, and that
        cycles by construction.
        """
        period = self.exploration_period()
        if period and gcd(period, self.n_actions) != 1:
            return int(turn) // period
        return int(turn)

    def update(self, s: int, a: int, r: int, s_next: int, *,
               terminal: bool = False) -> int:
        """Return δ (pre-alpha). Mutates Q[s,a], and its trace if enabled.

        An episode's terminal transition has no future value. Pay its
        delta through existing traces before clearing them, so credit
        cannot cross into the next life. Learned Q and integer remainders
        persist. The caller supplies terminality from the environment;
        rewards alone never imply death. Existing callers are unchanged.
        """
        ss = self._s(s)
        aa = int(a) % self.n_actions
        q_sa = self.q[ss][aa]
        max_next = 0 if terminal else self.max_q(s_next)
        backed = (GAMMA_NUM * int(max_next)) // GAMMA_DEN
        delta = int(r) + backed - q_sa
        if self.remainder:
            # alpha is still 1/4. What changes is that the three quarters
            # `>> 2` discards are not thrown away: they are owed, and paid
            # as soon as they add up to a whole unit. Four deltas of 3 pay
            # 3 units, not 0 — which is the whole of CREDIT-1.
            owed = self.rem[ss][aa] + delta
            step = trunc_div(owed)
            self.rem[ss][aa] = owed - (step << ALPHA_SHIFT)
            wanted = q_sa + step
            self.q[ss][aa] = clip_i8(wanted)
            if self.q[ss][aa] != wanted:
                # int8 rail. The credit could not be paid, so stop owing
                # it — otherwise the debt grows without bound against a
                # value that cannot move.
                self.rem[ss][aa] = 0
            return delta
        if not self.trace:
            self.q[ss][aa] = clip_i8(q_sa + (delta >> ALPHA_SHIFT))
            return delta

        # Credit this step, then pay δ back along the path just walked.
        # TRACE_CREDIT >> TRACE_SHIFT == 1 >> ALPHA_SHIFT, so the current
        # step gets exactly today's α = 1/4 and older steps get less.
        if self.z[ss][aa] == 0:
            self._active.append((ss, aa))
        self.z[ss][aa] = min(TRACE_MAX, self.z[ss][aa] + TRACE_CREDIT)

        alive: List[Tuple[int, int]] = []
        for i, j in self._active:
            zv = self.z[i][j]
            self.q[i][j] = clip_i8(self.q[i][j] + ((delta * zv) >> TRACE_SHIFT))
            zv = (GAMMA_NUM * zv) // GAMMA_DEN
            self.z[i][j] = zv
            if zv > 0:
                alive.append((i, j))
        self._active = alive
        if terminal:
            self.reset_traces()
        return delta

    def snapshot(self, s: int) -> List[int]:
        return self.row(s)

    def load_rows(self, rows: Sequence[Sequence[int]]) -> None:
        for i, row in enumerate(rows):
            if i >= N_SLOTS:
                break
            for a in range(self.n_actions):
                self.q[i][a] = clip_i8(row[a] if a < len(row) else 0)
