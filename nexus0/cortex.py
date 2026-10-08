"""
NEXUS-4a cortex stub — emits WSP, never facts.

There is no LLM here and no wrapper around `navi10_engine.think`. This
is the shape the slow clock has to fit: it receives a 16 B packet and an
ATTEND reason, and it returns a 16 B packet. Prose cannot come out of
this function because prose has no way in.

Firewall (`echoai/docs/02-INVARIANTS.md`): a hypothesis is never a fact.
This module has no CAM handle, calls no `allocate`, and sets no
`has_fact` — it cannot write one even by mistake. Counting the call is
the loop's job, so the count reflects the loop's decision, not this
file's opinion of itself.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from typing import Optional

from echoai.core.wsp import E_NAMES, pack

from echoai.nexus0.attend import REASON_NOVEL
from echoai.nexus0.encoder import ATOM_ID, encode_ask
from echoai.nexus0.constants import WSP_BYTES

ENV_CMD = "NAVI_CORTEX_CMD"
ENV_LOG = "NAVI_CORTEX_LOG"
ENV_TIMEOUT = "NAVI_CORTEX_TIMEOUT"
CMD_TIMEOUT_S = 10


def _timeout_s() -> float:
    """CI stays at 10 s. A local 4B may need longer; the operator says so."""
    raw = os.environ.get(ENV_TIMEOUT, "").strip()
    if not raw:
        return float(CMD_TIMEOUT_S)
    try:
        value = float(raw)
    except ValueError:
        return float(CMD_TIMEOUT_S)
    return value if value > 0 else float(CMD_TIMEOUT_S)

# "YO → TEMER → PELIGRO @AHORA", optionally followed by "| E[...]".
_COMPACT = re.compile(
    r"^\s*([A-Z_]+)\s*→\s*([A-Z_]+)\s*→\s*([A-Z_]+)\s*@\s*([A-Z_]+)\s*$"
)
_E_FIELD = re.compile(r"\b([VADCUB])\s*([+-]?\d+)\b")
_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")


def propose(wsp: bytes, reason: int) -> bytes:
    """Return the packet the slow clock would emit for this turn.

    Novel and unexplained → propose asking, which is the same 16 B
    PREGUNTAR the fast loop already knows how to send to the oracle. Any
    other reason → hand the observation straight back unchanged; the
    stub has no hypothesis of its own and does not invent one.
    """
    if len(wsp) != WSP_BYTES:
        raise ValueError("WSP must be 16 bytes")
    if int(reason) == REASON_NOVEL:
        return encode_ask()
    return wsp


def parse_reply(text: str) -> Optional[bytes]:
    """Accept 16 B from a slow clock, or nothing at all.

    Two forms only: 32 hex characters, or a compact line of known atoms
    (`YO → TEMER → PELIGRO @AHORA`, with an optional `| E[...]` tail).
    Anything else — a sentence, a JSON answer, a number with units, a
    VERIFY claim — returns None, and the caller keeps the observation.

    This is the firewall in function form. A model that will not speak
    atoms does not get to write into the loop.
    """
    if not isinstance(text, str):
        return None
    raw = text.strip()
    if not raw:
        return None

    if _HEX32.match(raw):
        return bytes.fromhex(raw)

    head, _, tail = raw.partition("|")
    m = _COMPACT.match(head)
    if not m:
        return None
    names = m.groups()
    if any(n not in ATOM_ID for n in names):
        return None
    src, rel, dst, time = (ATOM_ID[n] for n in names)

    e = {k: 0 for k in E_NAMES}
    if tail.strip():
        found = _E_FIELD.findall(tail)
        if not found:
            return None  # there was a tail, and it was not an E block
        for key, val in found:
            e[key] = int(val)
    return pack(src=src, rel=rel, dst=dst, time=time, E=e, generator=0x05)


def complete(turn: dict) -> Optional[str]:
    """Hand one turn to a local binary, if the operator named one.

    No HTTP, no SDK, no default. `NAVI_CORTEX_CMD` is an argv line; the
    turn goes in as JSON on stdin and whatever comes back on stdout is
    passed to parse_reply, which will reject it unless it is 16 B. With
    the variable unset this returns None and the stub answers instead.
    """
    cmd = os.environ.get(ENV_CMD, "").strip()
    if not cmd:
        return None
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            input=json.dumps(turn, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=_timeout_s(),
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout
