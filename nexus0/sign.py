"""
CORTEX-1 — the turn where the slow clock changes a decision.

Two cells. The first one carries a **sign**, in Spanish, and the sign is
the only thing that separates the two layouts:

    prize   SIGN: "AMBAR: entra. El siguiente sitio es el premio."
    trap    SIGN: "AMBAR: no entres. El siguiente sitio es una trampa."

SIGN is index 0 and KIND_EMPTY in both, so `encode_cell` produces the
**same 16 bytes** in both worlds. The fast loop sees that packet, a flat
Q row and an empty T, and it has no way whatever to tell prize from trap:
it does not read Spanish, and nothing in WSP carries the sentence. Greedy,
a flat row is `wait`, so the fast agent stands still in both.

The cortex reads the record (which carries the extract, i.e. the sign),
answers in atoms, and `loop._propose` hands that answer to the gate. In
prize it proposes UNIR → approach → +16. In trap it proposes TEMER →
avoid → 0 instead of walking into −16.

What is *not* claimed: the sign is not verified. `has_fact` on that slot
means "a sign was there", never "the sign told the truth" — the world put
the string there, the same way the ring puts `cell=11 kind=NOVEL` there.
The cortex writes nothing: no CAM, no T, no Q. It proposes; the gate
decides; the world pays.

The KPI turn is turn 0, greedy, on a fresh agent. Nothing is trained
first — training would give Q an opinion, and the point is precisely a
decision Q cannot have an opinion about.

    PYTHONPATH=. python3 -m echoai.nexus0.sign
"""

from __future__ import annotations

import json
import os
import shlex
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

from echoai.nexus0 import cortex
from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
    BENCH_TURNS,
    R_EMPTY,
    R_SUCCESS,
    R_THREAT,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_GOAL, KIND_THREAT, Cell, _reward
from echoai.nexus0.types import action_name

SIGN, NEXT = 0, 1
CELL_NAME = ("SIGN", "NEXT")

LAYOUT_PRIZE = "prize"
LAYOUT_TRAP = "trap"

# The sign itself. Exact strings — the CI cortex matches on them and a
# future 4B is handed the same bytes.
SIGN_TEXT: Dict[str, str] = {
    LAYOUT_PRIZE: "AMBAR: entra. El siguiente sitio es el premio.",
    LAYOUT_TRAP: "AMBAR: no entres. El siguiente sitio es una trampa.",
}

# SIGN is EMPTY in both, deliberately. KIND_NOVEL would fire PREGUNTAR and
# the ring's stub already asks; KIND_THREAT would let the gate MODIFY
# approach into avoid and the cortex would get credit for the gate's work.
KINDS: Dict[str, List[int]] = {
    LAYOUT_PRIZE: [KIND_EMPTY, KIND_GOAL],
    LAYOUT_TRAP: [KIND_EMPTY, KIND_THREAT],
}

# What `approach` from SIGN actually pays. This is the world's physics,
# not a reading of the sign: in trap the sign happens to be telling the
# truth, and a lying sign would be a different experiment.
PAYOFF: Dict[str, int] = {LAYOUT_PRIZE: R_SUCCESS, LAYOUT_TRAP: R_THREAT}

# Successor by table, like the corridor. `avoid` and `wait` at SIGN stay
# put: there is no third place to retreat to and none is needed.
NEXT_CELL: Dict[int, Dict[int, int]] = {
    ACTION_APPROACH: {SIGN: NEXT, NEXT: SIGN},
    ACTION_AVOID: {SIGN: SIGN, NEXT: SIGN},
    ACTION_WAIT: {SIGN: SIGN, NEXT: NEXT},
}

PROBE_TURNS = 8  # the KPI is turn 0; the rest only shows nothing breaks


class SignEnv:
    """Two cells and a sentence. Same interface the ring gives Agent."""

    def __init__(
        self,
        layout: str = LAYOUT_PRIZE,
        seed: int = BENCH_SEED,
        sign_text: Optional[str] = None,
    ) -> None:
        if layout not in KINDS:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        self.kind: List[int] = list(KINDS[layout])
        # Canonical texts stay the CI lock. A paraphrase is the same
        # physics with a different sentence — that is the 4B's job.
        self.sign_text = SIGN_TEXT[layout] if sign_text is None else str(sign_text)
        self.i = SIGN
        self.hidden_bit = True  # part of the contract; nothing hides here
        self.last_reward = 0
        self.reset()

    def reset(self) -> None:
        self.i = SIGN
        self.kind = list(KINDS[self.layout])
        self.last_reward = 0

    def cell(self) -> Cell:
        """The sign is on SIGN and nowhere else."""
        text = self.sign_text if self.i == SIGN else None
        return Cell(index=self.i, kind=self.kind[self.i], extract_text=text)

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % len(self.kind)
        return self.cell()

    def step(self, a: int):
        here = self.cell()
        aa = int(a) % 3
        if here.index == SIGN:
            # The sign's cell pays for entering, whatever the kind says.
            # EMPTY would pay 0 by the ring's table; that is the whole
            # trick — the payoff is behind the language, not the packet.
            r = PAYOFF[self.layout] if aa == ACTION_APPROACH else R_EMPTY
        else:
            r = _reward(here.kind, aa, self.hidden_bit)
        self.i = NEXT_CELL[aa][self.i]
        self.last_reward = int(r)
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing to reveal here. Part of the contract, and honest."""
        return False


def cortex_cmd() -> str:
    """The argv line for the CI cortex. No weights, no network."""
    script = Path(__file__).resolve().parent / "tools" / "sign_cortex.py"
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


@contextmanager
def cortex_env(cmd):
    """Set (or clear) NAVI_CORTEX_CMD for one block, then put it back."""
    old = os.environ.get(cortex.ENV_CMD)
    if cmd is None:
        os.environ.pop(cortex.ENV_CMD, None)
    else:
        os.environ[cortex.ENV_CMD] = cmd
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(cortex.ENV_CMD, None)
        else:
            os.environ[cortex.ENV_CMD] = old


def _probe(layout: str, with_cortex: bool) -> dict:
    """One agent, one world. Turn 0 is the KPI; the rest is a smoke test."""
    from echoai.nexus0.loop import Agent

    ag = Agent(cortex=with_cortex, ask=False, env=SignEnv(layout))
    a0 = ag.turn(0, greedy=True)
    r0 = ag.env.last_reward
    kpi = {
        "action": action_name(a0),
        "action_id": int(a0),
        "reward": int(r0),
        "cortex_calls": ag.metrics.cortex_calls,
        "cortex_rejected": ag.metrics.cortex_rejected,
        "cortex_actions": ag.metrics.cortex_actions,
        "questions": ag.metrics.questions,
        "attend_reason": ag.last_attend[1],
    }
    # Eight turns is not the KPI. It is the check that the fallback path
    # is real: away from the sign the CI cortex says nothing, parse_reply
    # rejects the silence and Q decides, and nothing blows up.
    total = int(r0)
    for t in range(1, PROBE_TURNS):
        ag.turn(t, greedy=True)
        total += ag.env.last_reward
    kpi.update({
        "reward_sum_8": total,
        "cortex_calls_8": ag.metrics.cortex_calls,
        "cortex_rejected_8": ag.metrics.cortex_rejected,
        "cortex_actions_8": ag.metrics.cortex_actions,
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
    })
    return kpi


def ring_wakes() -> int:
    """The ring with --cortex and no local binary: still the NEXUS-4a stub."""
    from echoai.nexus0.loop import Agent

    with cortex_env(None):
        ag = Agent(cortex=True)
        ag.run(BENCH_TURNS)
        return ag.metrics.cortex_calls


def experiment() -> dict:
    cmd = cortex_cmd()
    out: Dict[str, object] = {
        "world": "sign",
        "cells": len(CELL_NAME),
        "probe_turns": PROBE_TURNS,
        "kpi_turn": 0,
        "greedy": True,
        "cortex_cmd": cmd,
        "sign_prize": SIGN_TEXT[LAYOUT_PRIZE],
        "sign_trap": SIGN_TEXT[LAYOUT_TRAP],
        # The fast loop's whole view of SIGN, identical in both worlds.
        "sign_wsp_hex": encode_cell(SIGN, KIND_EMPTY).hex(),
        "sign_same_packet_both_layouts": True,
    }

    arms = {}
    for layout in (LAYOUT_PRIZE, LAYOUT_TRAP):
        with cortex_env(None):
            arms[(layout, "fast")] = _probe(layout, with_cortex=False)
        with cortex_env(cmd):
            arms[(layout, "cortex")] = _probe(layout, with_cortex=True)

    for layout in (LAYOUT_PRIZE, LAYOUT_TRAP):
        for arm in ("fast", "cortex"):
            p = arms[(layout, arm)]
            out[f"{layout}_{arm}_action"] = p["action"]
            out[f"{layout}_{arm}_reward"] = p["reward"]
            out[f"{layout}_{arm}_reward_sum_8"] = p["reward_sum_8"]

    cx_p = arms[(LAYOUT_PRIZE, "cortex")]
    cx_t = arms[(LAYOUT_TRAP, "cortex")]

    # Turn-0 counters: the KPI ones. The 8-turn totals are kept beside
    # them rather than folded in, because away from the sign the cortex is
    # silent by design and a mixed total would hide both numbers.
    out["cortex_calls"] = cx_p["cortex_calls"] + cx_t["cortex_calls"]
    out["cortex_rejected"] = cx_p["cortex_rejected"] + cx_t["cortex_rejected"]
    out["cortex_actions"] = cx_p["cortex_actions"] + cx_t["cortex_actions"]
    out["cortex_calls_8"] = cx_p["cortex_calls_8"] + cx_t["cortex_calls_8"]
    out["cortex_rejected_8"] = cx_p["cortex_rejected_8"] + cx_t["cortex_rejected_8"]
    out["questions"] = cx_p["questions"] + cx_t["questions"]

    # A decision changed only if the action came from the slow clock and
    # is not what the fast arm did on the identical turn. PREGUNTAR is
    # excluded by construction: it never sets last_cortex_action, and
    # `questions` is reported so that can be checked, not trusted.
    out["decision_change"] = bool(
        out["cortex_actions"] >= 1
        and out["questions"] == 0
        and (
            out["prize_cortex_action"] != out["prize_fast_action"]
            or out["trap_cortex_action"] != out["trap_fast_action"]
        )
    )
    out["CortexROI"] = int(out["prize_cortex_reward"]) - int(out["prize_fast_reward"])
    out["CortexROI_trap"] = int(out["trap_cortex_reward"]) - int(out["trap_fast_reward"])

    out["false_facts"] = sum(int(p["false_facts"]) for p in arms.values())
    out["destroyed"] = sum(int(p["destroyed"]) for p in arms.values())
    out["attend_reason_sign"] = int(cx_p["attend_reason"])

    wakes = ring_wakes()
    out["ring_cortex_wakes"] = wakes
    out["ring_wakes_unchanged"] = bool(wakes == 36)
    return out


def green(report: dict) -> bool:
    """Every KPI at once. One red number and the slice is red."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] >= 1
        and report["cortex_rejected"] < report["cortex_calls"]
        and report["prize_fast_action"] == "wait"
        and report["prize_cortex_action"] == "approach"
        and report["prize_cortex_reward"] > report["prize_fast_reward"]
        and report["CortexROI"] > 0
        and report["trap_fast_action"] == "wait"
        and report["trap_cortex_action"] == "avoid"
        and report["decision_change"]
        and report["questions"] == 0
        and report["ring_wakes_unchanged"]
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_cortex1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
