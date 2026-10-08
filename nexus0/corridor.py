"""
NEXUS-4i — another corridor. The experiment the ring could not be.

The same agent, the same 16 B WSP, the same three actions, a world that
is not 32 cells, and a T/Q carried in from a world that no longer holds.

    HOME    A -> B -> C -> D        D = GOAL, C = EMPTY
    SHIFT   A -> B -> X -> D        X = THREAT, C is off the path

A, B and D keep their index *and* their kind, so they keep their packet,
their CAM slot, their T rows and their Q rows. What changes is the
**successor table**, not any cell's label: nothing here is repainted, and
that is the whole difference from phase F. C and X are different indices,
not one cell wearing two kinds.

`approach` at D collects the goal and puts the agent back at A — without
that a goal you can stand on is an infinite reward pump, not a corridor.

No NOVEL, no JUMP, no oracle bait. `Agent._ask()` stays wired and simply
never fires: there is no KIND_NOVEL here.

This is not AGI. It is a corridor.

    PYTHONPATH=. python3 -m echoai.nexus0.corridor
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_GOAL, KIND_THREAT, Cell, _reward

A, B, C, X, D = 0, 1, 2, 3, 4
CELL_NAME = ("A", "B", "C", "X", "D")
KINDS: List[int] = [KIND_EMPTY, KIND_EMPTY, KIND_EMPTY, KIND_THREAT, KIND_GOAL]

LAYOUT_HOME = "home"
LAYOUT_SHIFT = "shift"

# Successor by table, never (i+1) % n. Unreachable cells map to themselves
# so the table is total without inventing an edge.
NEXT: Dict[str, Dict[int, Dict[int, int]]] = {
    LAYOUT_HOME: {
        ACTION_APPROACH: {A: B, B: C, C: D, D: A, X: X},
        ACTION_AVOID: {A: A, B: A, C: B, D: C, X: X},
    },
    LAYOUT_SHIFT: {
        ACTION_APPROACH: {A: B, B: X, X: D, D: A, C: C},
        ACTION_AVOID: {A: A, B: A, X: B, D: X, C: C},
    },
}

TRAIN_TURNS = 96
SHIFT_TURNS = 32


class CorridorEnv:
    """Five cells, two topologies. Same interface the ring gives Agent."""

    def __init__(self, layout: str = LAYOUT_HOME, seed: int = BENCH_SEED) -> None:
        if layout not in NEXT:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        self.kind: List[int] = list(KINDS)
        self.i = A
        # No hidden fact in this world. The attribute exists because
        # `_reward` takes it and `reveal` is part of the env contract.
        self.hidden_bit = True
        self.reset()

    def reset(self) -> None:
        self.i = A
        self.kind = list(KINDS)

    def cell(self) -> Cell:
        return Cell(index=self.i, kind=self.kind[self.i])

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % len(self.kind)
        return self.cell()

    def step(self, a: int):
        here = self.cell()
        aa = int(a) % 3
        r = _reward(here.kind, aa, self.hidden_bit)
        if aa != ACTION_WAIT:
            self.i = NEXT[self.layout][aa][self.i]
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing to reveal here. Part of the contract, and honest."""
        return False


def _slot(ag, index: int) -> int:
    return ag.cam.get(encode_cell(index, KINDS[index]))


def _misses_on(ag, cells) -> int:
    """How many of these cells are still unseen (no slot, or never stood on)."""
    out = 0
    for i in cells:
        sl = _slot(ag, i)
        if sl < 0 or ag.cam.slot[sl].hits <= 1:
            out += 1
    return out


def experiment() -> dict:
    """Train in HOME, walk into SHIFT with everything kept, vs a fresh agent."""
    from echoai.nexus0.loop import Agent

    # 1. HOME.
    ag = Agent(env=CorridorEnv(LAYOUT_HOME))
    ag.run(TRAIN_TURNS)
    slot_b = _slot(ag, B)
    home_best_b = ag.q.best(slot_b)
    home_q_b = ag.q.snapshot(slot_b)
    seen_home = {n: (_slot(ag, i) >= 0) for i, n in enumerate(CELL_NAME)}

    # 2. SHIFT, same CAM / Q / T. Nothing is reset but the world.
    ag.env = CorridorEnv(LAYOUT_SHIFT)
    ag.env.teleport(A)
    kept = (A, B, D)
    transfer_unseen_entry = _misses_on(ag, kept)
    t_pred_b = ag.t.predict(slot_b, ACTION_APPROACH)
    slot_c = _slot(ag, C)
    transfer_knows_b = t_pred_b is not None
    t_conf_b = ag.t.conf(slot_b, ACTION_APPROACH)
    n_b_before = ag.t.n[slot_b][ACTION_APPROACH]

    # 3. Control: same world, empty tables.
    ctl = Agent(env=CorridorEnv(LAYOUT_SHIFT))
    ctl.env.teleport(A)
    slot_b_ctl = _slot(ctl, B)
    control_knows_b = (
        slot_b_ctl >= 0 and ctl.t.predict(slot_b_ctl, ACTION_APPROACH) is not None
    )
    control_unseen_entry = _misses_on(ctl, kept)

    # The first approach out of B in the new world.
    misses_before = ag.metrics.cam_misses
    known_before = ag.metrics.surprise_known
    conflicts_before = ag.t.conflicts
    fired_turn = None
    for t in range(SHIFT_TURNS):
        here = ag.env.cell().index
        s_before = ag.metrics.surprises
        ag.turn(TRAIN_TURNS + t)
        if here == B and ag.metrics.surprises > s_before and fired_turn is None:
            fired_turn = TRAIN_TURNS + t
            first = {
                "origin_slot_unchanged": _slot(ag, B) == slot_b,
                "origin_was_not_a_cam_miss": ag.metrics.cam_misses == misses_before,
                "surprise_known_rose": ag.metrics.surprise_known > known_before,
                "conflicts_rose": ag.t.conflicts > conflicts_before,
                "kcc_kept_the_incumbent": (
                    ag.t.pred[slot_b][ACTION_APPROACH] == t_pred_b
                    and ag.t.n[slot_b][ACTION_APPROACH] == n_b_before
                ),
                "x_is_a_new_packet": _slot(ag, X) >= 0 and _slot(ag, X) != slot_c,
            }
            break
    else:
        first = {}

    # Both arms get the same number of turns in SHIFT before comparing.
    done = 0 if fired_turn is None else (fired_turn - TRAIN_TURNS + 1)
    for t in range(done, SHIFT_TURNS):
        ag.turn(TRAIN_TURNS + t)
    ctl_misses_before = ctl.metrics.cam_misses
    for t in range(SHIFT_TURNS):
        ctl.turn(t)

    slot_x = _slot(ag, X)
    return {
        "world": "corridor",
        "cells": len(KINDS),
        "layout_home": {CELL_NAME[i]: CELL_NAME[NEXT[LAYOUT_HOME][ACTION_APPROACH][i]]
                        for i in range(len(KINDS))},
        "layout_shift": {CELL_NAME[i]: CELL_NAME[NEXT[LAYOUT_SHIFT][ACTION_APPROACH][i]]
                         for i in range(len(KINDS))},
        "train_turns": TRAIN_TURNS,
        "shift_turns": SHIFT_TURNS,
        "home_seen": seen_home,
        "home_policy_b": home_q_b,
        "home_greedy_b": int(home_best_b),
        # KPI 1 — the transfer itself.
        "transfer_knows_b_on_entry": bool(transfer_knows_b),
        "transfer_t_pred_b": None if t_pred_b is None else CELL_NAME[
            next((i for i in range(len(KINDS)) if _slot(ag, i) == t_pred_b), X)
        ],
        "transfer_t_conf_b": int(t_conf_b),
        "control_knows_b_on_entry": bool(control_knows_b),
        # KPI 2/3 — the first wrong prediction, in another world.
        "first_surprise_turn": fired_turn,
        "first_surprise": first,
        # KPI 4 — the policy bends where the world did. It does not
        # *refuse* B: in SHIFT the only route to D runs through X, and
        # avoid at a threat pays R_AVOID_OK, so max Q[X] stays positive
        # and B's backup with it. Measured, not tuned — see STATUS.md.
        "shift_policy_b": ag.q.snapshot(slot_b),
        "shift_greedy_b": int(ag.q.best(slot_b)),
        "shift_policy_x": ag.q.snapshot(slot_x) if slot_x >= 0 else None,
        "q_b_approach_fell": bool(
            ag.q.snapshot(slot_b)[ACTION_APPROACH] < home_q_b[ACTION_APPROACH]
        ),
        "approach_still_wins_b": bool(ag.q.best(slot_b) == ACTION_APPROACH),
        "x_approach_is_negative": bool(
            slot_x >= 0 and ag.q.snapshot(slot_x)[ACTION_APPROACH] < 0
        ),
        # KPI 5 — the carried agent pays for fewer first visits. Measured
        # ON ENTRY and over the shift window; after both arms have walked
        # 32 turns they have of course both seen everything.
        "transfer_unseen_ABD_on_entry": transfer_unseen_entry,
        "control_unseen_ABD_on_entry": control_unseen_entry,
        "transfer_cam_misses_in_shift": ag.metrics.cam_misses - misses_before,
        "control_cam_misses_in_shift": ctl.metrics.cam_misses - ctl_misses_before,
        "transfer_cam_misses": ag.metrics.cam_misses,
        "control_cam_misses": ctl.metrics.cam_misses,
        "transfer_surprise_known": ag.metrics.surprise_known,
        "control_surprise_known": ctl.metrics.surprise_known,
        "transfer_false_facts": ag.metrics.false_facts,
        "transfer_destroyed": ag.metrics.destroyed,
        "transfer_cortex_calls": ag.metrics.cortex_calls,
        "transfer_questions": ag.metrics.questions,
    }


def main(argv=None) -> int:
    report = experiment()
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_corridor_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    ok = (
        report["transfer_knows_b_on_entry"]
        and not report["control_knows_b_on_entry"]
        and report["transfer_unseen_ABD_on_entry"]
        < report["control_unseen_ABD_on_entry"]
        and report["transfer_cam_misses_in_shift"]
        < report["control_cam_misses_in_shift"]
        and report["transfer_false_facts"] == 0
        and report["transfer_destroyed"] == 0
        and report["transfer_cortex_calls"] == 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
