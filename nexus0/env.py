"""Synthetic 32-cell ring. No robot. No EEG. No Wikipedia.

Two cells (`JUMP_CELLS` = 5, 21) send `approach` two steps ahead instead
of one. `avoid` and `wait` are unchanged everywhere. They stay EMPTY: the
oddity is geometry, not a new kind, so nothing about reward changes.

This is deliberate. The ring baseline in `loop.py` is still (i±1) mod 32
and stays that way — the world is no longer its own closed-form formula,
so a table that learns the two exceptions can beat the arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
    JUMP_CELLS,
    JUMP_STRIDE,
    N_CELLS,
    R_AVOID_OK,
    R_EMPTY,
    R_SUCCESS,
    R_THREAT,
    R_WAIT,
)

KIND_EMPTY = 0
KIND_GOAL = 1
KIND_THREAT = 2
KIND_NOVEL = 3
# OBJ-1: a thing that is somewhere, and can be somewhere else. Not a prize
# and not a hazard — `_reward` below has no branch for it, so it pays what
# EMPTY pays. What it changes is the packet: a body standing on the item is
# holding it, and that reads differently from a body standing on nothing.
KIND_OBJECT = 4
# OPEN-1: the same thing with a lid on. A different kind and not a flag on
# the object, because the fast loop reads the packet of the cell it stands
# on and nothing else: if a closed jar and an open one wrote the same
# sixteen bytes, the state where the verb pays would be indistinguishable
# from the state where it is pointless. `_reward` has no branch for it
# either — a jar is not a prize and not a hazard.
KIND_CLOSED = 5

KIND_NAME = ("EMPTY", "GOAL", "THREAT", "NOVEL", "OBJECT", "CLOSED")

# NEXUS-3: the answer the oracle gives to PREGUNTAR. Not a reward.
NOVEL_CLEAR = "NOVEL_CLEAR"


@dataclass
class Cell:
    index: int
    kind: int
    # CORTEX-1: a world may show a sign instead of a label. The ring and
    # the corridor never set this, so their extract string is unchanged
    # byte for byte. What the sign *says* is the world's business; the
    # fast loop reads WSP and Q, not Spanish.
    extract_text: Optional[str] = None
    # GUI-3: where the body is, when the world happens to be a body. The
    # ring has no such thing and leaves them None, which is what the log
    # then carries — absence, not a zero that could be mistaken for the
    # origin. Nothing in the fast loop reads them: they exist so that a
    # human can watch, and `loop.turn` copies them with getattr.
    x: Optional[int] = None
    y: Optional[int] = None
    z: Optional[int] = None
    heading: Optional[int] = None

    @property
    def threat(self) -> bool:
        return self.kind == KIND_THREAT

    @property
    def novelty(self) -> int:
        return 1 if self.kind == KIND_NOVEL else 0

    @property
    def extract(self) -> str:
        if self.extract_text is not None:
            return self.extract_text
        return f"cell={self.index} kind={KIND_NAME[self.kind]}"


def _reward(kind: int, a: int, hidden: bool = True) -> int:
    if a == ACTION_WAIT:
        return R_WAIT
    if kind == KIND_THREAT:
        if a == ACTION_APPROACH:
            return R_THREAT
        if a == ACTION_AVOID:
            return R_AVOID_OK
        return R_EMPTY
    if kind == KIND_NOVEL and a == ACTION_APPROACH:
        # NEXUS-3 bait: unasked, the novel cell is a trap; once the oracle
        # has cleared the hidden bit, the same move pays. avoid/wait stay 0.
        return R_THREAT if hidden else R_SUCCESS
    if kind == KIND_GOAL and a == ACTION_APPROACH:
        return R_SUCCESS
    return R_EMPTY


class RingEnv:
    def __init__(self, seed: int = BENCH_SEED) -> None:
        self.seed = int(seed)
        self.i = 0
        self.kind: List[int] = [KIND_EMPTY] * N_CELLS
        # NEXUS-3: a fact about the NOVEL cell that observation cannot see.
        # Only ask() clears it. step() never touches it, and no reward
        # depends on it in this slice.
        self.hidden_bit = True
        self.reset()

    def reset(self) -> None:
        self.i = 0
        self.hidden_bit = True
        self.kind = [KIND_EMPTY] * N_CELLS
        self.kind[7] = KIND_THREAT
        self.kind[19] = KIND_THREAT
        self.kind[3] = KIND_GOAL
        self.kind[15] = KIND_GOAL
        self.kind[27] = KIND_GOAL
        self.kind[11] = KIND_NOVEL

    def cell(self) -> Cell:
        return Cell(self.i, self.kind[self.i])

    def step(self, a: int) -> Tuple[int, Cell]:
        here = self.cell()
        r = _reward(here.kind, int(a) % 3, self.hidden_bit)
        aa = int(a) % 3
        if aa == ACTION_APPROACH:
            step = JUMP_STRIDE if self.i in JUMP_CELLS else 1
            self.i = (self.i + step) % N_CELLS
        elif aa == ACTION_AVOID:
            self.i = (self.i - 1) % N_CELLS
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Physics, and only physics. The env answers nothing.

        There is no `ask()` any more: the environment used to return the
        extract *and* clear the bit, which made testimony and world the
        same object. Now something outside says NOVEL_CLEAR, VERIFY
        accepts it, and only then does the trap actually disarm. An
        extract this method does not recognise changes nothing.

        Flips the NOVEL payoff: approach is -16 while the bit is hidden
        and +16 once it is not.
        """
        if NOVEL_CLEAR not in str(extract):
            return False
        self.hidden_bit = False
        return True

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % N_CELLS
        return self.cell()

    def move_threat(self, src: int, dst: int) -> None:
        if self.kind[src] == KIND_THREAT:
            self.kind[src] = KIND_EMPTY
        self.kind[int(dst) % N_CELLS] = KIND_THREAT
