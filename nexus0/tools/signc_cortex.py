#!/usr/bin/env python3
"""
SIGN-C — the slow clock for CI, with no weights in it.

Same twenty-line discipline as `sign_cortex.py`, and deliberately not an
import of it: SIGN's rule is "entra" / "no entres", and a world whose
lever has been reversed does not use those two words. Two rules in one
file would make either slice's stub a superset that could pass the other
slice's mutants by accident.

What is *not* here is the whole point. There is no node id, no kind, no
layout, no map and no route: stdin carries one `cortex_turn` record and
this file reads exactly one field of it, `extract` — the sentence the
world posted. It cannot know where the body is, where it landed, or that
anything contradicted anything. It answers one atom, and if the sentence
is not one it understands it answers nothing at all, which is a real
answer: a cortex that always speaks is a cortex that cannot be wrong.

    stdin   one `cortex_turn.build` record as JSON
    stdout  exactly one line `cortex.parse_reply` accepts, or nothing

No imports from echoai, no network, no model.

    NAVI_CORTEX_CMD="python3 echoai/nexus0/tools/signc_cortex.py"
"""

from __future__ import annotations

import json
import sys

AVOID = "YO → TEMER → AQUI @AHORA"
APPROACH = "YO → UNIR → AQUI @AHORA"

# Order matters and the refusals come first: a sign that reverses a lever
# says what is *no longer* true before it says what to do, so "ya no es la
# trampa" contains the word a naive hazard-matcher would trip on. Matching
# the instruction rather than the noun is the whole of the rule.
REFUSE = ("no entres", "no pases", "no sigas", "retrocede", "date la vuelta")
INVITE = ("entra", "pasa", "sigue", "adelante", "cruza")


def decide(extract: str) -> str:
    """The whole of the model. Twelve words of Spanish and no world."""
    text = str(extract).lower()
    if any(w in text for w in REFUSE):
        return AVOID
    if any(w in text for w in INVITE):
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
