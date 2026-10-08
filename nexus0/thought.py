"""
NEXUS-4c — one line per turn, every turn.

`cortex.jsonl` only holds the ~40 turns that woke the slow clock. This
is the other log: the whole run, including the quiet turns, so the ring
can be replayed and watched. Fixed keys, integers and atoms, no field
for prose — same contract discipline as `cortex_turn.py`.

It is a record of what the fast loop did. It is not a brain render.
"""

from __future__ import annotations

import json
from typing import List, Optional

from echoai.nexus0.attend import reason_name
from echoai.nexus0.constants import GATE_OK
from echoai.nexus0.encoder import compact
from echoai.nexus0.env import KIND_NAME

# GUI-1 widened this set from 12 to 17. The board cannot paint what the
# log does not carry, and N / S / δ / the cortex proposal / the gate's
# verdict were all computed in `loop.turn` and then dropped on the floor.
# Integers and null, no prose and no nested events[]: a viewer can derive
# a timeline from these, and cannot derive them from a timeline.
KEYS = (
    "turn", "cell", "kind", "action", "reward", "wsp",
    "attend_on", "reason_name", "q_row", "t_pred",
    "questions", "cortex_calls",
    # GUI-1
    "n", "s", "delta", "cortex_action", "gate_decision",
    # GUI-3 widened it again, and for the same reason: the board cannot
    # paint a cube the log does not carry. `cell` is one integer and the
    # pose it stands for is three plus a heading -- deriving one from the
    # other inside a viewer would put this cube's geometry in a browser.
    # Integers or null, never prose: the ring has no pose and writes five
    # nulls, which is the honest reading of "there is no such thing here".
    "x", "y", "z", "heading", "frame",
)

# OPEN-1 adds a fourth name, not a fourth key: a world with a lid can
# log `open`, and a reader of an older jsonl sees the same three it
# always saw. KEYS is untouched at 22.
ACTION_NAME = ("approach", "avoid", "wait", "open")


def _int_or_none(v) -> Optional[int]:
    return None if v is None else int(v)


def build(
    turn: int,
    cell: int,
    kind: int,
    action: int,
    reward: int,
    wsp: bytes,
    attend_on: bool,
    reason: int,
    q_row: List[int],
    t_pred: Optional[int],
    questions: int,
    cortex_calls: int,
    n: int = 0,
    s: int = 0,
    delta: int = 0,
    cortex_action: Optional[int] = None,
    gate_decision: int = GATE_OK,
    x: Optional[int] = None,
    y: Optional[int] = None,
    z: Optional[int] = None,
    heading: Optional[int] = None,
    frame: Optional[int] = None,
) -> dict:
    """One turn, as the loop actually saw it.

    `n`, `s` and `delta` are the three learnings counted apart in
    NEXUS-4g — a CAM miss on the origin, a T prediction that was wrong,
    a non-zero TD error — as 0/1 flags for this turn. `cortex_action` is
    the proposal `_propose` consumed, or None when the slow clock
    proposed nothing (it was off, it did not wake, or it woke and said
    nothing this parser would accept). `gate_decision` is what the gate
    did with the action, not what was asked of it.

    `x`, `y`, `z`, `heading` and `frame` are GUI-3's five: where the body
    was when the turn started, when the world is one that has a where.
    None everywhere else, and a None is written as null rather than
    dropped, so every line of every world still carries the same keys.
    """
    return {
        "turn": int(turn),
        "cell": int(cell),
        "kind": KIND_NAME[int(kind)],
        "action": int(action),
        "reward": int(reward),
        "wsp": compact(wsp),
        "attend_on": bool(attend_on),
        "reason_name": reason_name(reason),
        "q_row": [int(v) for v in q_row],
        "t_pred": None if t_pred is None else int(t_pred),
        "questions": int(questions),
        "cortex_calls": int(cortex_calls),
        "n": int(n),
        "s": int(s),
        "delta": int(delta),
        "cortex_action": None if cortex_action is None else int(cortex_action),
        "gate_decision": int(gate_decision),
        "x": _int_or_none(x),
        "y": _int_or_none(y),
        "z": _int_or_none(z),
        "heading": _int_or_none(heading),
        "frame": _int_or_none(frame),
    }


def to_line(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True)
