"""
NEXUS-4b — the contract a slow clock is allowed to see.

One woken turn, as integers and atoms. There is no field for prose here
and that is the whole point: a model plugged into this hook receives a
16 B packet, a slot, a Q row, a T prediction and a verifiable extract,
and it is expected to answer with 16 B. If it answers with a paragraph,
`cortex.parse_reply` returns None and the turn is thrown away.

The record is written after the fast loop has already decided. Nothing
here can become a fact: CAM is not reachable from this module.
"""

from __future__ import annotations

import json
from typing import List, Optional

from echoai.nexus0.attend import reason_name
from echoai.nexus0.encoder import compact


def build(
    turn: int,
    reason: int,
    wsp_in: bytes,
    wsp_out: bytes,
    slot: int,
    ham: int,
    q_row: List[int],
    t_pred: Optional[int],
    extract: str,
) -> dict:
    """The whole vocabulary of a cortex turn. No free text field."""
    return {
        "turn": int(turn),
        "reason": int(reason),
        "reason_name": reason_name(reason),
        "wsp_in": compact(wsp_in),
        "wsp_in_hex": wsp_in.hex(),
        "slot": int(slot),
        "ham": int(ham),
        "q_row": [int(v) for v in q_row],
        "t_pred": None if t_pred is None else int(t_pred),
        "extract": str(extract),
        "wsp_out": compact(wsp_out),
        "wsp_out_hex": wsp_out.hex(),
    }


def to_line(record: dict) -> str:
    """One JSON object per line, sorted keys, no newlines inside."""
    return json.dumps(record, ensure_ascii=False, sort_keys=True)
