#!/usr/bin/env python3
"""
CORTEX-1 — the slow clock, with no weights in it.

A 4B model is not the claim. The claim is the *cable*: something outside
the fast loop reads the language the world put in front of it and answers
in atoms, and the loop treats that answer as a proposal the gate can still
refuse. This file is that something, in twenty lines, so CI never needs a
2.5 GB download to prove the cable carries current.

    stdin   one `cortex_turn.build` record as JSON
    stdout  exactly one line `cortex.parse_reply` accepts, or nothing

The rule reads the sign, not the kind: the fast loop already has the kind
(it is in the WSP) and the kind is EMPTY on both signs. If the sign says
"no entres" the answer is TEMER; if it says "entra" it is UNIR; if there
is no sign it says nothing at all, and the loop must fall back to Q and
count a reject. Saying nothing is a real answer here — a cortex that
always speaks is a cortex that cannot be wrong.

No imports from echoai, no network, no model. Invoked through
`NAVI_CORTEX_CMD`, like any other local binary would be.

    NAVI_CORTEX_CMD="python3 echoai/nexus0/tools/sign_cortex.py"
"""

from __future__ import annotations

import json
import sys

AVOID = "YO → TEMER → AQUI @AHORA"
APPROACH = "YO → UNIR → AQUI @AHORA"


def decide(extract: str) -> str:
    """The whole of the model. Order matters: check the refusal first."""
    text = str(extract).lower()
    if "no entres" in text:
        return AVOID
    if "entra" in text:
        return APPROACH
    return ""


def main() -> int:
    try:
        turn = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    line = decide(turn.get("extract", ""))
    if line:
        sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
