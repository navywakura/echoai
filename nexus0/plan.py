"""
NEXUS-2: one- and two-step counterfactuals over T.

Reads Q and T, writes neither. No reward is invented here: the only
values in play are the ones Q already learned, backed up through the
transitions T already observed. Integer throughout, γ = 7/8 — the same
rational Q backs up with — clipped to int8.

Depth 2 costs at most 3×3 leaf evaluations. This is a lookahead, not a
search: no frontier, no queue, no tree to grow.

Not wired into `Agent.turn`. The 320-turn bench still selects with
`Q.best`; this module is gated by unit tests until `select()` takes it
as an option.
"""

from __future__ import annotations

from typing import List

from echoai.nexus0.constants import ACTION_WAIT, GAMMA_DEN, GAMMA_NUM, N_ACTIONS
from echoai.nexus0.qtable import QTable
from echoai.nexus0.types import clip_i8
from echoai.nexus0.world import World


def _discount(v: int) -> int:
    return clip_i8((GAMMA_NUM * int(v)) // GAMMA_DEN)


def _score(world: World, q: QTable, slot: int, a: int, depth: int) -> int:
    """max(what Q says here, what T shows ahead).

    The root term matters: without it every action whose successors are
    still flat scores 0, all three tie, and the tie-break sits the agent
    down — measured at 71 % wait over 256 turns before this max existed.

    It is optimistic on purpose: a bad successor cannot pull an action
    below its own root Q, so a negative lookahead is masked while
    `Q[slot][a]` is still 0. Approach loses on score only once the root
    itself has been punished.
    """
    root = q.get(slot, a)
    nxt = world.predict(slot, a)
    if nxt is None:
        # T never saw this pair. Nothing to look through: stay myopic.
        return clip_i8(root)
    if depth <= 1:
        look = q.max_q(nxt)
    else:
        look = _discount(_value(world, q, nxt, depth - 1))
    return clip_i8(max(root, look))


def _value(world: World, q: QTable, slot: int, depth: int) -> int:
    if depth <= 0:
        return clip_i8(q.max_q(slot))
    return max(_score(world, q, slot, b, depth) for b in range(N_ACTIONS))


def scores(world: World, q: QTable, slot: int, depth: int = 2) -> List[int]:
    """One int per action. depth < 1 is clamped to 1."""
    d = max(1, int(depth))
    return [_score(world, q, slot, a, d) for a in range(N_ACTIONS)]


def best(world: World, q: QTable, slot: int, depth: int = 2) -> int:
    """argmax over `scores`. Tie → wait, same tie-break as QTable.best."""
    row = scores(world, q, slot, depth)
    m = max(row)
    winners = [i for i, v in enumerate(row) if v == m]
    if ACTION_WAIT in winners:
        return ACTION_WAIT
    return winners[0]
