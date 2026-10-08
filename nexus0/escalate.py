"""
NEXUS-4f — how much to think, not another map.

ATTEND answers "is this turn beyond the fast path?". This answers the
cheaper question underneath it: given that the fast path is handling the
turn, is its preference strong enough to act on, or is it worth spending
one lookahead first? Integer, pure, no Agent, no allocation.

The ladder is five rungs (docs/06-LADDER.md); this slice wires exactly
two of them:

    0  Q          the policy's own argmax
    1  T one-step reserved — NOT wired. T already runs every turn in the
                  loop (observe + predict + surprise), so a rung that
                  only consults it would be a label on work already done.
    2  SEARCH     plan.best over T, depth 2
    3  ASK        reserved — PREGUNTAR stays `Agent._ask()`, the single
                  path to the oracle, fired before the action is chosen.
                  It is not a fourth gear and is not returned here.
    4  CORTEX     reserved — that decision is ATTEND's, in `attend.py`.
                  This module does not duplicate it and must not be read
                  as replacing it.

So `level()` returns 0 or 2. The other three are named so the ladder is
one enum rather than three vocabularies, and each says why it is unwired.
"""

from __future__ import annotations

from echoai.nexus0.constants import ESC_MARGIN

LEVEL_Q = 0
LEVEL_T = 1
LEVEL_SEARCH = 2
LEVEL_ASK = 3
LEVEL_CORTEX = 4

LEVEL_NAME = {
    LEVEL_Q: "q",
    LEVEL_T: "t",
    LEVEL_SEARCH: "search",
    LEVEL_ASK: "ask",
    LEVEL_CORTEX: "cortex",
}


def level(
    margin: int,
    t_conf: int = 0,
    kind_novel: bool = False,
    extract_ok: bool = True,
    cortex_enabled: bool = False,
) -> int:
    """Which rung this turn deserves. 0 or 2 in this slice.

    Only `margin` decides. The rest of the signature is the ladder's
    inputs, kept so the caller is written once and so a later rung does
    not change every call site — they are deliberately not read yet, the
    same discipline `E` gets in `attend()`.

    A clear winner is not worth a lookahead: whatever the plan returns,
    the root max in `plan.best` already contains Q[s, best], so a search
    on a decided row can only reproduce it. Escalate when ΔQ is small.
    """
    if int(margin) > ESC_MARGIN:
        return LEVEL_Q
    return LEVEL_SEARCH


def level_name(code: int) -> str:
    return LEVEL_NAME.get(int(code), "?")
