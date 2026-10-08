"""
Pure action gate. OK / MODIFY / BLOCK.
Does not run curl, ping, or commands_dispatch.
"""

from __future__ import annotations

from typing import Tuple

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    GATE_BLOCK,
    GATE_MODIFY,
    GATE_OK,
    N_ACTIONS,
    U_SHORT,
    WSP_FLAG_VETO,
)


def gate(
    wsp: bytes,
    *,
    cam_hit: bool,
    extract_ok: bool,
    E: Tuple[int, int, int, int, int, int],
    proposed: int,
    inhibit: bool = False,
    threat: bool = False,
    n_actions: int = N_ACTIONS,
) -> Tuple[int, int, int]:
    """Return (decision, action, flags).

    Order from docs/05-NEXUS-0-SPEC.md §8.

    OPEN-1: `n_actions` is how many gears the world that asked has, and it
    defaults to the frozen three, so every existing caller folds `proposed`
    exactly as it always did (5 still comes out 2). A four-gear world has
    to say so, and if it did not, `open` would enter here as 3 and leave as
    0 — the environment would never see the verb, every ABRIR would be an
    approach, and the slice would be OBJ-1 wearing a fourth column.

    The rules below are unchanged. `open` is not a threat and not a wait,
    so it matches none of them and leaves through GATE_OK; an inhibited
    slot still blocks to WAIT, whatever was proposed.
    """
    del wsp, cam_hit  # reserved for later rules; keep signature stable
    a = int(proposed) % int(n_actions)
    u = int(E[4]) if len(E) > 4 else 0
    flags = 0

    if inhibit:
        return GATE_BLOCK, ACTION_WAIT, WSP_FLAG_VETO

    if (not extract_ok) and a == ACTION_APPROACH and threat:
        return GATE_MODIFY, ACTION_AVOID, WSP_FLAG_VETO

    if u >= U_SHORT and a == ACTION_WAIT and threat:
        return GATE_MODIFY, ACTION_AVOID, WSP_FLAG_VETO

    return GATE_OK, a, flags
