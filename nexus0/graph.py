"""
WORLD-3 — a graph of 256 nodes, and the first body-map: position *is* node.

Not the ring, not the corridor of five, not SIGN. Same `Agent`, same 16 B
WSP, same three actions, same `encode_cell(index, kind)`. What is new is
the address space: 256 nodes, successors by **table**, never `(i+1) % n`
and never a 2D grid that would invent a north the agent has no action for.

    spine   16 shared nodes, index and kind identical in both layouts
    HOME    ... -> B -> C -> GOAL -> (back to the start of the spine)
    SHIFT   ... -> B -> X -> GOAL -> (back to the start of the spine)

**Exactly one edge differs between the two layouts**: `approach` out of the
fork B. C and X are two different nodes with two different kinds (EMPTY and
THREAT), not one node repainted — nothing here changes its label, so every
packet, CAM slot, T row and Q row survives the move. In HOME nothing points
at X; in SHIFT nothing points at C. Both tables are total.

`approach` at GOAL collects and returns to the start of the spine: a goal
you can stand on and re-collect is a reward pump, not a world. The 239
nodes off the path are their own successors, so the table is total without
inventing an edge.

Where the fork sits, and why it is not node 1 of the spine. This Q is
integer with alpha = 1/4, so a positive delta below 4 shifts to zero and
value stops travelling. Measured on this very spine (`credit_horizon` in
the report): counting back from GOAL the rows read 13, 8, 4, 0, 0, ... —
**three** nodes deep and no further, at 512 turns and unchanged at 2048.
Eligibility traces (`trace=True`) do not extend it; they spread the debt
and leave the far spine negative. So the fork is spine position 13, inside
the horizon. Put it at position 1 and both arms would stand still in a flat
row, and `transfer_gain` would be 0 - 0: a KPI that cannot be failed is not
a KPI. The horizon is reported as a number, not designed around in silence.

The KPI runs with the cortex **off**. If it needed a 4B it would be a
chatbot in costume, not a transfer.

This is not AGI. It is the corridor of five grown to 256 addresses.

    PYTHONPATH=. python3 -m echoai.nexus0.graph
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
    N_ACTIONS,
    R_AVOID_OK,
    R_SUCCESS,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_GOAL, KIND_THREAT, Cell, _reward

# 256 is not a round number picked for the poster. `encode_cell` writes the
# node index into ext.seq as `index & 0xFF`, so node 256 would hand back
# byte-for-byte the packet of node 0. 256 is exactly this encoder's ceiling
# before two places become one — the number ANTI-ALIAS will have to move.
N_NODES = 256
PACKET_CEILING = 256

SPINE_LEN = 16
# Scattered on purpose: consecutive indices would let the ring's own
# arithmetic baseline look like a world model. Stride 13 from 5.
SPINE: tuple = tuple(5 + 13 * k for k in range(SPINE_LEN))

START_POS = 0
FORK_POS = 13  # inside the measured credit horizon; see the module docstring
GOAL_POS = SPINE_LEN - 1

START = SPINE[START_POS]  # 5
B = SPINE[FORK_POS]  # 174 — the fork
C = SPINE[FORK_POS + 1]  # 187 — where HOME says approach lands
GOAL = SPINE[GOAL_POS]  # 200
X = 251  # THREAT, off the spine, where SHIFT says approach lands

LAYOUT_HOME = "home"
LAYOUT_SHIFT = "shift"
LAYOUTS = (LAYOUT_HOME, LAYOUT_SHIFT)

# One kind list for the whole world, shared by both layouts. Nothing is
# repainted: that is the entire difference from the ring's phase F.
KINDS: List[int] = [KIND_EMPTY] * N_NODES
KINDS[GOAL] = KIND_GOAL
KINDS[X] = KIND_THREAT

TRAIN_TURNS = 512  # the spine profile is converged here; 2048 reads the same
SHIFT_TURNS = 64


def _successors(layout: str) -> Dict[int, Dict[int, int]]:
    """Successor by table. Off-path nodes are their own successor."""
    approach = {i: i for i in range(N_NODES)}
    avoid = {i: i for i in range(N_NODES)}
    wait = {i: i for i in range(N_NODES)}
    for p, node in enumerate(SPINE):
        # The spine is walked forward and closes at the goal.
        approach[node] = SPINE[p + 1] if p + 1 < SPINE_LEN else SPINE[START_POS]
        # avoid steps one back along the spine, or stays if there is no back.
        avoid[node] = SPINE[p - 1] if p > 0 else SPINE[START_POS]
    # X hangs off the fork in both tables: it rejoins at GOAL and retreats
    # to B. In HOME nothing points at it, which is what makes it unseen.
    approach[X] = GOAL
    avoid[X] = B
    # The one edge that differs.
    approach[B] = C if layout == LAYOUT_HOME else X
    return {ACTION_APPROACH: approach, ACTION_AVOID: avoid, ACTION_WAIT: wait}


NEXT: Dict[str, Dict[int, Dict[int, int]]] = {
    layout: _successors(layout) for layout in LAYOUTS
}

# Everything the agent can actually stand on: the spine plus X.
REACHABLE: tuple = tuple(sorted(set(SPINE) | {X}))


class GraphEnv:
    """256 nodes, two topologies, one edge apart. The env contract only."""

    def __init__(self, layout: str = LAYOUT_HOME, seed: int = BENCH_SEED) -> None:
        if layout not in NEXT:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        self.kind: List[int] = list(KINDS)
        self.i = START
        # Part of the contract and honest: nothing is hidden in this world,
        # and `_reward` takes the flag.
        self.hidden_bit = True
        self.last_reward = 0
        self.reset()

    def reset(self) -> None:
        self.i = START
        self.kind = list(KINDS)
        self.last_reward = 0

    def cell(self) -> Cell:
        return Cell(index=self.i, kind=self.kind[self.i])

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % N_NODES
        return self.cell()

    def step(self, a: int):
        here = self.cell()
        aa = int(a) % N_ACTIONS
        r = _reward(here.kind, aa, self.hidden_bit)
        self.i = NEXT[self.layout][aa][self.i]
        self.last_reward = int(r)
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing to reveal here. Part of the contract, and honest."""
        return False


def _slot(ag, node: int) -> int:
    return ag.cam.get(encode_cell(node, KINDS[node]))


def _unseen(ag, nodes) -> int:
    """Nodes with no CAM slot, or a slot never actually stood on."""
    out = 0
    for node in nodes:
        sl = _slot(ag, node)
        if sl < 0 or ag.cam.slot[sl].hits <= 1:
            out += 1
    return out


def _cam_occupied(ag) -> int:
    return sum(1 for s in ag.cam.slot if s.occupied)


def _q_approach_profile(ag) -> List[int]:
    """Q[approach] along the spine. This is the credit horizon, as a list."""
    out = []
    for node in SPINE:
        sl = _slot(ag, node)
        out.append(ag.q.row(sl)[ACTION_APPROACH] if sl >= 0 else None)
    return out


def _t_against(ag, layout: str) -> dict:
    """What T says about `approach` at every spine node, against the
    successor table of `layout`, before a single turn is taken there.

    This is the transfer stated without money in it: 15 of the 16 rows
    still describe the new world exactly, and the one that does not is the
    fork. A row whose successor has never been allocated a slot counts as
    a disagreement, which is the honest reading — T names a place, and X
    is not that place.
    """
    known = 0
    matches = 0
    wrong: List[int] = []
    for pos, node in enumerate(SPINE):
        slot = _slot(ag, node)
        if slot < 0:
            continue
        pred = ag.t.predict(slot, ACTION_APPROACH)
        if pred is None:
            continue
        known += 1
        actual = _slot(ag, NEXT[layout][ACTION_APPROACH][node])
        if actual >= 0 and pred == actual:
            matches += 1
        else:
            wrong.append(pos)
    return {"known": known, "matches": matches, "wrong_positions": wrong}


def _greedy_profile(ag) -> List[Optional[int]]:
    out = []
    for node in SPINE:
        sl = _slot(ag, node)
        out.append(int(ag.q.best(sl)) if sl >= 0 else None)
    return out


def _walk_greedy(ag, turns: int, offset: int = 0) -> dict:
    """Greedy turns in the world the agent is standing in. Reward summed
    off the env, because `turn()` returns the action, not the payoff."""
    total = 0
    goal_hits = 0
    avoid_pay = 0
    for t in range(turns):
        ag.turn(offset + t, greedy=True)
        r = int(ag.env.last_reward)
        total += r
        if r == R_SUCCESS:
            goal_hits += 1
        elif r == R_AVOID_OK:
            avoid_pay += 1
    return {"reward_sum": total, "goal_hits": goal_hits, "avoid_pays": avoid_pay}


def experiment() -> dict:
    """Train in HOME, walk into SHIFT with CAM/T/Q kept, versus a fresh agent."""
    from echoai.nexus0.loop import Agent

    # 1. HOME. One agent, the ring's own defaults, cortex off.
    ag = Agent(env=GraphEnv(LAYOUT_HOME))
    ag.run(TRAIN_TURNS)
    slot_b = _slot(ag, B)
    slot_c = _slot(ag, C)
    home_profile = _q_approach_profile(ag)
    home_greedy = _greedy_profile(ag)
    home_q_b = ag.q.snapshot(slot_b)
    home_cam = _cam_occupied(ag)
    home_unseen_spine = _unseen(ag, SPINE)

    # 2. SHIFT. Same CAM, same T, same Q. Nothing is reset but the world,
    # and both arms enter standing on the fork — the one node where the
    # world changed, and the only place a policy exists at all.
    ag.env = GraphEnv(LAYOUT_SHIFT)
    ag.env.teleport(B)
    # Read after the swap, not before: "knows the fork on entry" has to be
    # a fact about the agent standing in the new world, or an arm that
    # quietly cleared T on the way in would still pass.
    t_pred_b = ag.t.predict(slot_b, ACTION_APPROACH)
    t_conf_b = ag.t.conf(slot_b, ACTION_APPROACH)
    transfer_knows_fork = t_pred_b is not None and t_pred_b == slot_c
    transfer_unseen_on_entry = _unseen(ag, SPINE)
    t_vs_shift = _t_against(ag, LAYOUT_SHIFT)
    t_vs_home = _t_against(ag, LAYOUT_HOME)

    # 3. Control: same world, same seat, empty tables.
    ctl = Agent(env=GraphEnv(LAYOUT_SHIFT))
    ctl.env.teleport(B)
    slot_b_ctl = _slot(ctl, B)
    control_knows_fork = (
        slot_b_ctl >= 0 and ctl.t.predict(slot_b_ctl, ACTION_APPROACH) is not None
    )
    control_unseen_on_entry = _unseen(ctl, SPINE)

    # The first approach out of the fork in the new world: T committed to
    # C and the world hands back X. The agent is wrong exactly where the
    # world changed, and nowhere else.
    known_before = ag.metrics.surprise_known
    misses_before = ag.metrics.cam_misses
    conflicts_before = ag.t.conflicts
    first_action = ag.turn(TRAIN_TURNS, greedy=True)
    first_reward = int(ag.env.last_reward)
    first = {
        "action": int(first_action),
        "origin_slot_unchanged": _slot(ag, B) == slot_b,
        "origin_was_not_a_cam_miss": ag.metrics.cam_misses == misses_before,
        "surprise_known_rose": ag.metrics.surprise_known > known_before,
        "conflicts_rose": ag.t.conflicts > conflicts_before,
        "landed_on_x": ag.env.cell().index == X,
        "x_is_a_new_packet": _slot(ag, X) >= 0 and _slot(ag, X) != slot_c,
    }

    # Same number of turns, same seed, greedy, same seat.
    kept = _walk_greedy(ag, SHIFT_TURNS - 1, offset=TRAIN_TURNS + 1)
    kept["reward_sum"] += first_reward
    fresh = _walk_greedy(ctl, SHIFT_TURNS)

    transfer_gain = int(kept["reward_sum"]) - int(fresh["reward_sum"])
    return {
        "world": "graph",
        "nodes_requested": N_NODES,
        "nodes": N_NODES,
        "reason": "packet_ceiling",
        "reachable_nodes": len(REACHABLE),
        "packet_ceiling": PACKET_CEILING,
        "actions": N_ACTIONS,
        "spine": list(SPINE),
        "spine_len": SPINE_LEN,
        "fork_pos": FORK_POS,
        "fork_node": B,
        "home_next_of_fork": C,
        "shift_next_of_fork": X,
        "goal_node": GOAL,
        "start_node": START,
        "train_turns": TRAIN_TURNS,
        "shift_turns": SHIFT_TURNS,
        "greedy": True,
        "cortex_calls": ag.metrics.cortex_calls,
        # The credit horizon, as measured on this spine. Not a limit that
        # was worked around: a number.
        "credit_horizon_q_approach": home_profile,
        "home_greedy_by_spine_pos": home_greedy,
        "home_q_fork": home_q_b,
        # KPI 1 — T survives the change of topology.
        "transfer_knows_fork": bool(transfer_knows_fork),
        "transfer_t_pred_is_home_c": bool(t_pred_b == slot_c),
        "transfer_t_conf_fork": int(t_conf_b),
        "control_knows_fork": bool(control_knows_fork),
        # The transfer without money in it: every spine row T learned in
        # HOME still describes SHIFT, except the one edge that moved.
        "t_rows_known_on_entry": t_vs_shift["known"],
        "t_matches_shift_on_entry": t_vs_shift["matches"],
        "t_wrong_spine_positions_in_shift": t_vs_shift["wrong_positions"],
        "t_matches_home_on_entry": t_vs_home["matches"],
        "control_t_rows_known_on_entry": _t_against(ctl, LAYOUT_SHIFT)["known"],
        # KPI 2 — and being right about HOME makes it wrong about SHIFT.
        "first_shift_turn": first,
        # KPI 3 — the number.
        "transfer_reward_sum_shift": int(kept["reward_sum"]),
        "control_reward_sum_shift": int(fresh["reward_sum"]),
        "transfer_gain": transfer_gain,
        "transfer_goal_hits_in_shift": int(kept["goal_hits"]),
        "transfer_avoid_pays_in_shift": int(kept["avoid_pays"]),
        "control_goal_hits_in_shift": int(fresh["goal_hits"]),
        # KPI 4 — the control did not copy anything.
        "transfer_unseen_spine_on_entry": transfer_unseen_on_entry,
        "control_unseen_spine_on_entry": control_unseen_on_entry,
        "home_unseen_spine_after_train": home_unseen_spine,
        # CAM pressure, honestly: 256 addresses, 17 places, 4096 slots.
        "cam_occupied_home": home_cam,
        "cam_occupied_shift": _cam_occupied(ag),
        "cam_slots": len(ag.cam.slot),
        "false_facts": ag.metrics.false_facts + ctl.metrics.false_facts,
        "destroyed": ag.metrics.destroyed + ctl.metrics.destroyed,
        "questions": ag.metrics.questions + ctl.metrics.questions,
        "t_conflicts": ag.t.conflicts,
        "inv_dropped": ag.t.inv_dropped,
    }


def green(report: dict) -> bool:
    """Every KPI at once. One red number and the slice is red."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["nodes"] == N_NODES
        and report["actions"] == 3
        and report["transfer_knows_fork"]
        and report["transfer_t_pred_is_home_c"]
        and report["transfer_t_conf_fork"] >= 1
        and not report["control_knows_fork"]
        and report["t_rows_known_on_entry"] == SPINE_LEN
        and report["t_matches_shift_on_entry"] == SPINE_LEN - 1
        and report["t_wrong_spine_positions_in_shift"] == [FORK_POS]
        and report["t_matches_home_on_entry"] == SPINE_LEN
        and report["control_t_rows_known_on_entry"] == 0
        and report["first_shift_turn"]["landed_on_x"]
        and report["first_shift_turn"]["surprise_known_rose"]
        and report["first_shift_turn"]["origin_was_not_a_cam_miss"]
        and report["transfer_gain"] > 0
        and report["control_unseen_spine_on_entry"]
        > report["transfer_unseen_spine_on_entry"]
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_world3_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
