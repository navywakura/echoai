"""
NEXUS-4a ATTEND — decide whether the fast loop is enough.

The switch, not the novelist. Without it a cortex is called on every
turn and the whole two-clock claim collapses into a router. Integer
predicate, no model, no allocation: it answers "is this turn beyond the
fast path?" and says which of the reasons fired.

Spec: `echoai/docs/06-LADDER.md` § NEXUS-4 — ATTEND = MISS ∨ UNCERTAIN
∨ NOVEL ∨ … The first cut carried four of those; SIGN-C adds CONFLICT,
and GOAL_COMPLEX and HUMAN are later rungs and are not faked here.

CONFLICT is a reason code here and **not a branch of `attend()`**, on
purpose. Every other reason is knowable before the action: the packet,
the slot, the Q row and the T row are all on the table when the turn
starts. A contradiction is not — it exists only once the world has
answered, and `attend()` runs before `env.step()`. Making it a branch
would mean handing this predicate a fact from the future. The loop
therefore decides it after the step and reports the same code, so the
vocabulary of reasons stays one enum instead of two.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from echoai.nexus0.constants import C_PLASTIC, HAM_MISS, T_CONF_DECENT

REASON_OFF = 0
REASON_MISS = 1
REASON_NO_EXTRACT = 2
REASON_LOW_C = 3
REASON_NOVEL = 4
REASON_NO_MAP = 5
# SIGN-C. Appended, never renumbered: a log line written before this slice
# existed still reads the same reason it was written with.
REASON_CONFLICT = 6

REASON_NAME = {
    REASON_OFF: "off",
    REASON_MISS: "miss",
    REASON_NO_EXTRACT: "no_extract",
    REASON_LOW_C: "low_C",
    REASON_NOVEL: "novel",
    REASON_NO_MAP: "no_map",
    REASON_CONFLICT: "conflict",
}

E_C = 3  # V A D C U B


def attend(
    slot_hit: bool,
    extract_ok: bool,
    E: Sequence[int],
    kind_novel: bool,
    ham: int,
    q_confident: bool,
    t_known: bool,
    t_conf: int = 0,
) -> Tuple[bool, int]:
    """Return (wake the cortex?, reason code).

    Certainty is what the fast loop actually holds — a policy and a map —
    not the poster on the packet. `E` stays in the signature for callers
    and is deliberately **not** read for LOW_C: in this env it is the
    constant `default_e()` with C = 15, so trusting it woke the cortex on
    73 % of turns and made the switch a router.

    - `q_confident`: the Q row for this slot is not a full tie, i.e. the
      fast loop has a preference to act on.
    - `t_known`: T has seen the action that preference would take. wait
      mapping to itself counts as known, and should: a known standstill
      is precisely a turn the fast path can handle alone.
    - `t_conf`: how good that row of T is, 0..3 (`world.conf`). `t_known`
      stays the bool `conf >= 1`; this is the quality behind it, so that
      "seen once" and "seen eight times with no conflict" stop reading
      the same. A decent map (>= 2) on an otherwise ordinary turn is not
      a reason to spend the slow clock.

    Conditions are an OR, so check order only picks the label.
    """
    if (not slot_hit) or int(ham) >= HAM_MISS:
        return True, REASON_MISS
    if not extract_ok:
        return True, REASON_NO_EXTRACT
    if kind_novel:
        return True, REASON_NOVEL
    if not q_confident:
        return True, REASON_LOW_C
    if not t_known:
        # A decent map is not a missing one. This only ever silences
        # NO_MAP: every other reason keeps its wake, and nothing here can
        # turn an OFF into a wake.
        if int(t_conf) >= T_CONF_DECENT:
            return False, REASON_OFF
        return True, REASON_NO_MAP
    return False, REASON_OFF


def reason_name(code: int) -> str:
    return REASON_NAME.get(int(code), "?")
