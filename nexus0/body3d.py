"""
PULPO — a body in three dimensions, and a strategy that changes.

    3 x 3 x 3 voxels, 6 headings (faces, not 24 orientations)
    index = (x + 3*y + 9*z) * 6 + h        0 .. 161, and 161 < 256

162 poses fit under `encode_cell`'s one-byte `seq`, which is why the cube
is 3 and not 4: 4**3 * 6 = 384 and two places would become one place. The
ceiling is measured here, not raised.

    approach   one voxel the way it faces. Into stone or off the cube it
               does not move, and the collision pays R_THREAT.
    avoid      cycle the heading, h -> (h+1) % 6. No translation. Three
               actions, so there is no separate yaw and pitch: turning is
               one ring through +X, -X, +Y, -Y, +Z, -Z.
    wait       nothing moves.

`kind` belongs to the voxel and reads the same from all six headings. No
floor is painted THREAT — the threat is the collision, as in CUERPO-1 —
so `cell.threat` is false everywhere and the gate never modifies an
action here. The goal collects R_SUCCESS and sends the body home, so a
goal you can stand on is not a pump.

The room is two disjoint corridors between the same two voxels:

    short   (0,0,0) +X +X  +Y +Y  +Z      (2,2,1)     7 actions
    long    (0,0,0) +Y +Y  +Z     +X +X   (2,2,1)    11 actions

Both are five voxel moves and they are **not** the same price, because
turning is a cycle: a heading costs `(want - have) % 6` avoids. The short
corridor leaves along the start heading and turns twice, forward round the
ring, for 5 + 2. The long one has to turn away at the very first pose and
then walk the ring most of the way round to face +X again, for 5 + 6. The
difference is physics, not a label. The two corridors share only the start
and the goal, and no voxel of one touches a voxel of the other, so there
is no third route hiding between them.

Eleven is not an arbitrary length. `value_horizon()` says the integer
chain keeps a positive Q for exactly eleven steps, so the detour is the
longest one this arithmetic can still see. A cube whose detour is twelve
is unlearnable no matter how long you train it — measured, not assumed.

`block` turns **one** voxel of the short corridor, (2,1,0), to stone. The
long corridor is untouched, so the goal is still reachable — the cheap
way is simply gone. That is the whole experiment: the fast loop has to
stop doing the thing that used to work, with the cortex off.

Two of the detour's turns happen in **open air**: at (0,0,0,+X), where
walking forward still works, and at (0,2,1,-Z), where it walks back the
way it came. `qtable.select` answers `approach` on a flat row, so neither
turn can be found by a body that only ever learns from collisions. That
is why this slice pulls `explore_flat`: with it off the detour is
invisible, and the run below reports both numbers.

    PYTHONPATH=. python3 -m echoai.nexus0.body3d
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    ALPHA_SHIFT,
    BENCH_SEED,
    GAMMA_DEN,
    GAMMA_NUM,
    N_ACTIONS,
    R_AVOID_OK,
    R_SUCCESS,
    R_THREAT,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_GOAL, KIND_THREAT, Cell, _reward

SIDE = 3
HEADINGS = 6
N_VOXELS = SIDE ** 3
N_POSES = N_VOXELS * HEADINGS  # 162
POSES_REQUESTED = 162
PACKET_CEILING = 256

# The turning ring. `avoid` walks it one step at a time.
#
# Grouped by sign, not by axis: +X -> +Y -> +Z is one turn each. The other
# order (+X, -X, +Y, ...) costs two turns per corner and puts the body
# through an intermediate heading that points back down the corridor it
# just walked — a pose where `approach` succeeds, so its Q row stays flat,
# and a flat row is exactly where `qtable.select` can never try `avoid`.
# Measured: with that ring nothing is learned at all, from any geometry.
PLUS_X, PLUS_Y, PLUS_Z, MINUS_X, MINUS_Y, MINUS_Z = range(6)
DIRS: Tuple[Tuple[int, int, int], ...] = (
    (1, 0, 0), (0, 1, 0), (0, 0, 1), (-1, 0, 0), (0, -1, 0), (0, 0, -1),
)
HEADING_NAME = ("+X", "+Y", "+Z", "-X", "-Y", "-Z")

START_XYZ = (0, 0, 0)
START_HEADING = PLUS_X
GOAL_XYZ = (2, 2, 1)

SHORT_PATH: Tuple[Tuple[int, int, int], ...] = (
    (0, 0, 0), (1, 0, 0), (2, 0, 0), (2, 1, 0), (2, 2, 0), (2, 2, 1),
)
LONG_PATH: Tuple[Tuple[int, int, int], ...] = (
    (0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 2, 1), (1, 2, 1), (2, 2, 1),
)
FLOOR: frozenset = frozenset(SHORT_PATH) | frozenset(LONG_PATH)
BLOCKED = (2, 1, 0)  # the plug: the middle of the short corridor

LAYOUT_OPEN = "open"
LAYOUT_BLOCK = "block"
LAYOUTS = (LAYOUT_OPEN, LAYOUT_BLOCK)

TRAIN_REPS = 20
EXAM_TURNS = 512
def episode_turns(d: int) -> int:
    """Turns per teleport at distance `d`. Two properties, both measured.

    **Long enough.** `d + 2` is the greedy budget — walk there, collect,
    one spare — and it is exactly what a body that never explores needs.
    A body that does explore spends turns on the other two actions, so the
    budget scales with the ring it is trying: `d + 2` collects 0 in the
    open exam where `N_ACTIONS * (d + 2)` collects 47.

    **Coprime with N_ACTIONS.** `qtable.select` cycles `turn % N_ACTIONS`,
    and the turn counter runs straight through the teleports. If an
    episode is a whole number of cycles long, every repetition offers each
    pose the same action it was offered last time, and twenty reps learn
    what one rep learned. Measured on the pose the detour has to turn at:
    with `3 * (d + 2)` turns it was handed `wait` twenty times and
    `approach` twenty times and `avoid` never once. The `+ 1` makes the
    phase precess, so each repetition offers the next action along.
    """
    return N_ACTIONS * (int(d) + 2) + 1


def index_of(x: int, y: int, z: int, h: int) -> int:
    return (int(x) + SIDE * int(y) + SIDE * SIDE * int(z)) * HEADINGS + (
        int(h) % HEADINGS
    )


def pose_of(index: int) -> Tuple[int, int, int, int]:
    vox, h = divmod(int(index) % N_POSES, HEADINGS)
    z, rest = divmod(vox, SIDE * SIDE)
    y, x = divmod(rest, SIDE)
    return x, y, z, h


def pose_name(index: int) -> str:
    x, y, z, h = pose_of(index)
    return f"({x},{y},{z},{HEADING_NAME[h]})"


START = index_of(*START_XYZ, START_HEADING)
GOAL_POSES: Tuple[int, ...] = tuple(index_of(*GOAL_XYZ, h) for h in range(HEADINGS))


def floor_of(layout: str) -> frozenset:
    if layout == LAYOUT_BLOCK:
        return FLOOR - {BLOCKED}
    return FLOOR


def on_cube(x: int, y: int, z: int) -> bool:
    return 0 <= x < SIDE and 0 <= y < SIDE and 0 <= z < SIDE


def is_floor(x: int, y: int, z: int, layout: str) -> bool:
    return on_cube(x, y, z) and (x, y, z) in floor_of(layout)


# One kind list for the whole cube, shared by both layouts and indexed by
# pose. A voxel's kind reads the same from all six headings.
KINDS: List[int] = [KIND_EMPTY] * N_POSES
for _h in range(HEADINGS):
    KINDS[index_of(*GOAL_XYZ, _h)] = KIND_GOAL


def bumps(index: int, layout: str) -> bool:
    """Would `approach` from this pose hit stone or the outside?

    False for a pose inside stone: you cannot stand there, so there is
    nothing to walk into. The goal is asked about first by `_payoff`, so
    collecting never reads as a collision.
    """
    x, y, z, h = pose_of(index)
    if not is_floor(x, y, z, layout):
        return False
    dx, dy, dz = DIRS[h]
    return not is_floor(x + dx, y + dy, z + dz, layout)


def _successors(layout: str) -> Dict[int, Dict[int, int]]:
    """Successor by table, for every pose and every action.

    `avoid` is body physics and never consults the room, so closing a
    voxel changes no turning row at all. `approach` is the only action the
    cube can answer.
    """
    approach: Dict[int, int] = {}
    avoid: Dict[int, int] = {}
    wait: Dict[int, int] = {}
    for index in range(N_POSES):
        x, y, z, h = pose_of(index)
        avoid[index] = index_of(x, y, z, (h + 1) % HEADINGS)
        wait[index] = index
        if index in GOAL_POSES:
            approach[index] = START
        elif not is_floor(x, y, z, layout):
            approach[index] = index
        elif bumps(index, layout):
            approach[index] = index
        else:
            dx, dy, dz = DIRS[h]
            approach[index] = index_of(x + dx, y + dy, z + dz, h)
    return {
        ACTION_APPROACH: approach,
        ACTION_AVOID: avoid,
        ACTION_WAIT: wait,
    }


NEXT: Dict[str, Dict[int, Dict[int, int]]] = {
    layout: _successors(layout) for layout in LAYOUTS
}


def reachable(layout: str) -> Tuple[int, ...]:
    return tuple(
        i for i in range(N_POSES) if is_floor(*pose_of(i)[:3], layout)
    )


class Body3DEnv:
    """A body in a 3x3x3 cube. Same interface the ring gives Agent."""

    def __init__(self, layout: str = LAYOUT_OPEN, seed: int = BENCH_SEED) -> None:
        if layout not in NEXT:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        self.kind: List[int] = list(KINDS)
        self.i = START
        self.hidden_bit = True
        self.last_reward = 0
        self.bumped = False
        self.reset()

    def reset(self) -> None:
        self.i = START
        self.kind = list(KINDS)
        self.last_reward = 0
        self.bumped = False

    def cell(self) -> Cell:
        # GUI-3: the pose, spelled out. The index already holds it — the
        # cell is `(x + 3y + 9z) * 6 + h` — but a viewer that had to undo
        # that arithmetic would be a second copy of this cube's geometry
        # living in a browser. The world says where it is; nobody guesses.
        x, y, z, h = pose_of(self.i)
        return Cell(index=self.i, kind=self.kind[self.i],
                    x=x, y=y, z=z, heading=h)

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % N_POSES
        return self.cell()

    def _payoff(self, aa: int) -> int:
        kind = self.kind[self.i]
        if aa == ACTION_APPROACH:
            if kind == KIND_GOAL:
                return R_SUCCESS
            if bumps(self.i, self.layout):
                return _reward(KIND_THREAT, ACTION_APPROACH, self.hidden_bit)
        return _reward(kind, aa, self.hidden_bit)

    def step(self, a: int):
        aa = int(a) % N_ACTIONS
        r = self._payoff(aa)
        self.bumped = (
            aa == ACTION_APPROACH
            and self.kind[self.i] != KIND_GOAL
            and bumps(self.i, self.layout)
        )
        self.i = NEXT[self.layout][aa][self.i]
        self.last_reward = int(r)
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing to reveal here. Part of the contract, and honest."""
        return False


def _slot(ag, index: int) -> int:
    return ag.cam.get(encode_cell(index, KINDS[index]))


def _cam_occupied(ag) -> int:
    return sum(1 for s in ag.cam.slot if s.occupied)


def distances(layout: str) -> Dict[int, int]:
    """Minimum actions until a goal is collected, flooded over the table.

    A turn costs a step, exactly as a move does, so this is the cost the
    body actually pays and not a straight-line guess.
    """
    pred: Dict[int, set] = {}
    for pose in range(N_POSES):
        for a in (ACTION_APPROACH, ACTION_AVOID):
            pred.setdefault(NEXT[layout][a][pose], set()).add(pose)
    dist: Dict[int, int] = {g: 0 for g in GOAL_POSES}
    edge = list(GOAL_POSES)
    while edge:
        nxt = []
        for here in edge:
            for prev in pred.get(here, ()):
                if prev not in dist and prev != here:
                    dist[prev] = dist[here] + 1
                    nxt.append(prev)
        edge = nxt
    return dist


def poses_by_distance(layout: str) -> Dict[int, List[int]]:
    out: Dict[int, List[int]] = {}
    dist = distances(layout)
    for pose in reachable(layout):
        if pose in dist:
            out.setdefault(dist[pose], []).append(pose)
    return out


def shortest_path(layout: str, start: int) -> List[int]:
    """Descend the distance map. For the report only — nothing acts on it."""
    dist = distances(layout)
    path = [start]
    here = start
    while dist.get(here, 0) > 0:
        step = None
        for a in (ACTION_APPROACH, ACTION_AVOID):
            nxt = NEXT[layout][a][here]
            if nxt != here and dist.get(nxt, 10 ** 6) == dist[here] - 1:
                step = nxt
                break
        if step is None:
            break
        path.append(step)
        here = step
    return path


def stepper(index: int) -> Optional[int]:
    """Baseline: always one voxel along +X, blind to heading and stone."""
    x, y, z, h = pose_of(index)
    if x + 1 >= SIDE:
        return None
    return index_of(x + 1, y, z, h)


def t_vs_stepper(ag, layout: str) -> dict:
    """Score T and the stepper on the same poses, offline."""
    t_hits = 0
    step_hits = 0
    asked = 0
    wins: List[dict] = []
    for index in reachable(layout):
        slot = _slot(ag, index)
        if slot < 0:
            continue
        pred = ag.t.predict(slot, ACTION_APPROACH)
        if pred is None:
            continue
        asked += 1
        truth = NEXT[layout][ACTION_APPROACH][index]
        truth_slot = _slot(ag, truth)
        t_ok = truth_slot >= 0 and pred == truth_slot
        guess = stepper(index)
        guess_slot = -1 if guess is None else _slot(ag, guess)
        step_ok = guess is not None and guess_slot >= 0 and guess_slot == truth_slot
        t_hits += int(t_ok)
        step_hits += int(step_ok)
        if t_ok and not step_ok:
            wins.append({
                "pose": pose_name(index),
                "why": "stone" if bumps(index, layout) else "heading",
                "truth": pose_name(truth),
                "stepper_said": None if guess is None else pose_name(guess),
            })
    answered = [w for w in wins if w["stepper_said"] is not None]
    shown: List[dict] = []
    for why in ("heading", "stone"):
        for w in answered:
            if w["why"] == why:
                shown.append(w)
                break
    for w in answered + wins:
        if len(shown) >= 4:
            break
        if w not in shown:
            shown.append(w)
    return {
        "asked": asked,
        "t_hits": t_hits,
        "stepper_hits": step_hits,
        "t_beats_stepper": t_hits > step_hits,
        "stepper_answered_and_missed": len(answered),
        "examples": shown,
    }


def approach_diff() -> List[int]:
    """Poses whose `approach` lands somewhere else once the plug is in."""
    return [
        i
        for i in range(N_POSES)
        if NEXT[LAYOUT_OPEN][ACTION_APPROACH][i]
        != NEXT[LAYOUT_BLOCK][ACTION_APPROACH][i]
    ]


def value_horizon(reward: int = R_SUCCESS, span: int = 40) -> int:
    """The last distance whose Q is still positive. Arithmetic, not a run.

    With the remainder every state converges on its target exactly, so the
    chain is `q_k = (7 * q_(k+1)) // 8` closed into a cycle by the goal
    sending the body home: `q_0 = R_SUCCESS + (7 * q_start) // 8`. The
    integer divide kills the last unit at 12, and the feedback through the
    cycle does not save it.
    """
    q = [0] * (span + 1)
    for _ in range(8000):
        moved = False
        for k in range(span + 1):
            target = (reward + (7 * q[span]) // 8) if k == 0 else (7 * q[k - 1]) // 8
            if q[k] != target:
                q[k] += 1 if target > q[k] else -1
                moved = True
        if not moved:
            break
    return max((i for i, v in enumerate(q) if v > 0), default=0)


def turn_poses(layout: str, explore_flat: bool = False) -> List[dict]:
    """Every pose where the shortest route must turn, and whether the body
    can ever find that turn.

    With `explore_flat` off, `qtable.select` answers `approach` on a flat
    row, always. So `avoid` is only tried once a row is *not* flat, and the
    only thing that unflattens a row at a pose the route must turn at is
    the -16 of walking into stone: a turn in open air is a turn the fast
    loop cannot discover. With the lever on, a flat row joins the same
    `turn % 3` cycle a non-flat row already had, so an open-air turn gets
    tried like any other — which is the whole of PULPO-C, and why this
    function takes the flag instead of assuming it.
    """
    dist = distances(layout)
    out: List[dict] = []
    here = START
    for _ in range(64):
        if dist.get(here, 0) <= 0:
            break
        if dist.get(NEXT[layout][ACTION_APPROACH][here], 10 ** 6) == dist[here] - 1:
            here = NEXT[layout][ACTION_APPROACH][here]
            continue
        nxt = NEXT[layout][ACTION_AVOID][here]
        if dist.get(nxt, 10 ** 6) != dist[here] - 1:
            break
        out.append({
            "pose": pose_name(here),
            "approach_bumps": bumps(here, layout),
            "in_open_air": not bumps(here, layout),
            "discoverable": bool(explore_flat) or bumps(here, layout),
        })
        here = nxt
    return out


def _exam(ag, layout: str, turns: int = EXAM_TURNS) -> dict:
    """Greedy, cortex off, from the canonical start. Never from a
    neighbour of the goal: `START` is the module constant, and the report
    prints the pose that was actually used."""
    ag.env = Body3DEnv(layout)
    ag.env.teleport(START)
    total = 0
    hits = 0
    bumped = 0
    poses = []
    for t in range(turns):
        poses.append(ag.env.cell().index)
        ag.turn(10 ** 6 + t, greedy=True)
        r = int(ag.env.last_reward)
        total += r
        hits += int(r == R_SUCCESS)
        bumped += int(ag.env.bumped)
    return {
        "start": pose_name(START),
        "turns": turns,
        "goal_hits": hits,
        "reward_sum": total,
        "bumps": bumped,
        "poses_visited": len(set(poses)),
        "voxels_visited": sorted({pose_of(p)[:3] for p in poses}),
        "axes_moved": sorted(
            {a for p in poses for a in range(3) if pose_of(p)[a] != START_XYZ[a]}
        ),
        "trail": [pose_name(p) for p in poses[:40]],
    }


def _corridor_use(exam: dict) -> dict:
    """Which corridor did the greedy body actually walk?"""
    seen = {tuple(v) for v in exam["voxels_visited"]}
    short_only = set(SHORT_PATH) - set(LONG_PATH)
    long_only = set(LONG_PATH) - set(SHORT_PATH)
    return {
        "short_voxels_visited": sorted(seen & short_only),
        "long_voxels_visited": sorted(seen & long_only),
        "used_the_detour": bool(seen & long_only),
        "reached_the_goal_voxel": GOAL_XYZ in seen,
    }


def _curriculum(ag, layout: str, turn: int) -> Tuple[List[dict], int]:
    """Reverse curriculum: nearest to the goal first, then further out.

    Teleporting is a *training* aid and nothing else — the exam below
    always starts at the canonical START. The layout is a parameter
    because after the plug the same body has to be schooled on the cube
    it is actually standing in; `poses_by_distance` is flooded over the
    successor table of that layout, so no route is named anywhere here.
    """
    by_dist = poses_by_distance(layout)
    ag.env = Body3DEnv(layout)
    phases: List[dict] = []
    for d in sorted(k for k in by_dist if k > 0):
        before = ag.metrics.action_pos
        for _rep in range(TRAIN_REPS):
            for pose in by_dist[d]:
                ag.env.teleport(pose)
                for _ in range(episode_turns(d)):
                    ag.turn(turn)
                    turn += 1
        phases.append({
            "dist": d,
            "poses": len(by_dist[d]),
            "goal_hits_in_phase": ag.metrics.action_pos - before,
        })
    return phases, turn


def _control_without_the_lever() -> dict:
    """The same schedule with `explore_flat` off. The mutant, run every
    time rather than described.

    Nothing else changes: same cube, same plug, same reverse curriculum in
    both layouts, same remainder, same turns. If the detour still collects
    with a flat row pinned to `approach`, then the lever is not what buys
    it and the claim above is wrong.
    """
    from echoai.nexus0.loop import Agent

    ag = Agent(env=Body3DEnv(LAYOUT_OPEN), remainder=True, explore_flat=False)
    _phases, turn = _curriculum(ag, LAYOUT_OPEN, 0)
    exam_open = _exam(ag, LAYOUT_OPEN)
    _readapt, turn = _curriculum(ag, LAYOUT_BLOCK, turn)
    exam_block = _exam(ag, LAYOUT_BLOCK)
    return {
        "explore_flat": False,
        "open_goal_hits": exam_open["goal_hits"],
        "block_goal_hits": exam_block["goal_hits"],
        "block_reward_sum": exam_block["reward_sum"],
        "block_used_the_detour": _corridor_use(exam_block)["used_the_detour"],
        "block_trail": exam_block["trail"][:12],
    }


def experiment() -> dict:
    """Train in `open`; plug the short corridor; school the same body on
    the cube it is now in; then examine both, greedy, from START."""
    from echoai.nexus0.loop import Agent

    dist_open = distances(LAYOUT_OPEN)
    dist_block = distances(LAYOUT_BLOCK)
    ag = Agent(env=Body3DEnv(LAYOUT_OPEN), remainder=True, explore_flat=True)

    phases, turn = _curriculum(ag, LAYOUT_OPEN, 0)
    phases_turns = turn

    scored = t_vs_stepper(ag, LAYOUT_OPEN)
    # Only rows T actually holds. A pose it was never walked through has
    # no prediction to survive the plug, and counting it as a casualty
    # would be a lie in the other direction.
    t_before = {
        i: ag.t.predict(_slot(ag, i), ACTION_APPROACH)
        for i in reachable(LAYOUT_OPEN)
        if _slot(ag, i) >= 0
        and ag.t.predict(_slot(ag, i), ACTION_APPROACH) is not None
    }

    exam_open = _exam(ag, LAYOUT_OPEN)

    # The plug goes in. Nothing is reset: same Q, same T, same CAM, same
    # three actions, cortex still off. What follows is the same reverse
    # curriculum, now on the cube that has a wall in it.
    diff = approach_diff()
    readapt, turn = _curriculum(ag, LAYOUT_BLOCK, turn)
    readapt_turns = turn - phases_turns

    exam_block = _exam(ag, LAYOUT_BLOCK)
    # And what the detour cost the arm that already worked. Reported, not
    # a KPI: the plug is still in, so this is the old corridor reopened.
    exam_open_after = _exam(ag, LAYOUT_OPEN)

    control = _control_without_the_lever()

    unaffected = [i for i in t_before if i not in set(diff)]
    still_true = sum(
        1
        for i in unaffected
        if ag.t.predict(_slot(ag, i), ACTION_APPROACH) is not None
        and ag.t.predict(_slot(ag, i), ACTION_APPROACH)
        == _slot(ag, NEXT[LAYOUT_BLOCK][ACTION_APPROACH][i])
    )

    return {
        "world": "body3d",
        "slice": "pulpo",
        "poses_requested": POSES_REQUESTED,
        "poses": N_POSES,
        "max_index": N_POSES - 1,
        "packet_ceiling": PACKET_CEILING,
        "voxels": N_VOXELS,
        "headings": HEADINGS,
        "actions": N_ACTIONS,
        "turn_is_a_cycle": "h -> (h+1) % 6 over " + ",".join(HEADING_NAME),
        "short_path": [list(v) for v in SHORT_PATH],
        "long_path": [list(v) for v in LONG_PATH],
        "blocked_voxel": list(BLOCKED),
        "stone_voxels": sorted(
            [list(v) for v in
             ({(x, y, z) for x in range(SIDE) for y in range(SIDE)
               for z in range(SIDE)} - FLOOR)]
        ),
        "start": pose_name(START),
        "goal": list(GOAL_XYZ),
        "reachable_open": len(reachable(LAYOUT_OPEN)),
        "reachable_block": len(reachable(LAYOUT_BLOCK)),
        "start_distance_open": dist_open.get(START),
        "start_distance_block": dist_block.get(START),
        "short_cost_open": len(shortest_path(LAYOUT_OPEN, START)) - 1,
        "detour_cost_block": len(shortest_path(LAYOUT_BLOCK, START)) - 1,
        "remainder": bool(ag.q.remainder),
        "explore_flat": bool(ag.q.explore_flat),
        "alpha_shift": ALPHA_SHIFT,
        "gamma": [GAMMA_NUM, GAMMA_DEN],
        "R": {"success": R_SUCCESS, "threat": R_THREAT, "avoid_ok": R_AVOID_OK},
        "traces": False,
        "plan_depth": ag.plan_depth,
        "curriculum": phases,
        "curriculum_turns": phases_turns,
        "readapt": readapt,
        "readapt_turns": readapt_turns,
        "total_train_turns": turn,
        # KPI: T against blind arithmetic.
        "t_asked": scored["asked"],
        "t_hits": scored["t_hits"],
        "stepper_hits": scored["stepper_hits"],
        "t_beats_stepper": scored["t_beats_stepper"],
        "stepper_answered_and_missed": scored["stepper_answered_and_missed"],
        "t_right_stepper_wrong": scored["examples"],
        # KPI: it walks, and then it walks differently.
        "exam_start": exam_open["start"],
        "exam_start_is_canonical": exam_open["start"] == pose_name(START),
        "exam_turns": EXAM_TURNS,
        "exam_open_goal_hits": exam_open["goal_hits"],
        "exam_open_reward_sum": exam_open["reward_sum"],
        "exam_open_poses_visited": exam_open["poses_visited"],
        "exam_open_bumps": exam_open["bumps"],
        "exam_open_corridor": _corridor_use(exam_open),
        "exam_open_axes_moved": exam_open["axes_moved"],
        "exam_open_goal_hits_after_readapt": exam_open_after["goal_hits"],
        "exam_open_corridor_after_readapt": _corridor_use(exam_open_after),
        "exam_block_goal_hits": exam_block["goal_hits"],
        "exam_block_reward_sum": exam_block["reward_sum"],
        "exam_block_poses_visited": exam_block["poses_visited"],
        "exam_block_bumps": exam_block["bumps"],
        "exam_block_corridor": _corridor_use(exam_block),
        "exam_block_trail": exam_block["trail"],
        # T survives the change everywhere the change did not reach.
        "approach_diff_count": len(diff),
        "approach_diff_poses": [pose_name(i) for i in diff],
        "avoid_diff_count": sum(
            1
            for i in range(N_POSES)
            if NEXT[LAYOUT_OPEN][ACTION_AVOID][i]
            != NEXT[LAYOUT_BLOCK][ACTION_AVOID][i]
        ),
        "t_rows_carried": len(t_before),
        "t_rows_unaffected": len(unaffected),
        "t_unaffected_still_true_in_block": still_true,
        # Why the blocked arm is what it is, as numbers rather than prose.
        "value_horizon": value_horizon(),
        "turn_poses_open": turn_poses(LAYOUT_OPEN, ag.q.explore_flat),
        "turn_poses_block": turn_poses(LAYOUT_BLOCK, ag.q.explore_flat),
        "open_route_is_learnable": all(
            t["discoverable"] for t in turn_poses(LAYOUT_OPEN, ag.q.explore_flat)
        ),
        "block_route_is_learnable": all(
            t["discoverable"] for t in turn_poses(LAYOUT_BLOCK, ag.q.explore_flat)
        ),
        # The same two questions with the lever off, so the report says what
        # the lever is actually buying instead of asserting it in prose.
        "open_route_is_learnable_without_the_lever": all(
            t["discoverable"] for t in turn_poses(LAYOUT_OPEN)
        ),
        "block_route_is_learnable_without_the_lever": all(
            t["discoverable"] for t in turn_poses(LAYOUT_BLOCK)
        ),
        "control_without_the_lever": control,
        "control_open_goal_hits": control["open_goal_hits"],
        "control_block_goal_hits": control["block_goal_hits"],
        "lever_buys_the_detour":
            control["block_goal_hits"] < exam_block["goal_hits"],
        "open_air_turns_open": sum(
            1 for t in turn_poses(LAYOUT_OPEN) if t["in_open_air"]
        ),
        "open_air_turns_block": sum(
            1 for t in turn_poses(LAYOUT_BLOCK) if t["in_open_air"]
        ),
        "detour_fits_the_horizon":
            len(shortest_path(LAYOUT_BLOCK, START)) - 1 <= value_horizon(),
        "cam_occupied": _cam_occupied(ag),
        "cam_slots": len(ag.cam.slot),
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
        "cortex_calls": ag.metrics.cortex_calls,
        "questions": ag.metrics.questions,
    }


def green(report: dict) -> bool:
    """Three at once: a 3D body, a walk, and a change of strategy."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["actions"] == 3
        and report["poses"] == POSES_REQUESTED
        and report["max_index"] == 161
        and report["remainder"]
        and report["alpha_shift"] == ALPHA_SHIFT
        and report["R"]["success"] == R_SUCCESS
        and not report["traces"]
        and report["t_beats_stepper"]
        and report["exam_start_is_canonical"]
        and report["exam_open_goal_hits"] > 0
        and report["exam_block_goal_hits"] > 0
        and report["exam_block_corridor"]["used_the_detour"]
        and report["detour_cost_block"] <= report["value_horizon"]
        and report["detour_cost_block"] > report["short_cost_open"]
        and report["explore_flat"]
        and report["approach_diff_count"] > 0
        and report["avoid_diff_count"] == 0
        and report["t_unaffected_still_true_in_block"]
        == report["t_rows_unaffected"]
        and report["start_distance_block"] is not None
    )


# GUI-3. Its own name, so a cube walk never lands on the ring's diary.
THOUGHT_LOG = "thought_body3d.jsonl"
THOUGHT_TURNS = 64


def thought_walk(out=None, turns: int = THOUGHT_TURNS) -> dict:
    """School the body, then walk it greedily from START with the diary on.

    The curriculum is thirty thousand turns of teleporting, and a replay
    of that is a body blinking around a cube rather than a body walking.
    So the diary is opened *after* the schooling and for one greedy walk
    from the canonical START — which is `_exam` with a log attached and
    nothing else changed: same Q, same T, same CAM, cortex still off, no
    report written and no route named.
    """
    from echoai.nexus0.loop import Agent

    path = Path(out) if out else (
        Path(__file__).resolve().parents[1] / "lab" / THOUGHT_LOG
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()  # one run, one log

    ag = Agent(env=Body3DEnv(LAYOUT_OPEN), remainder=True, explore_flat=True)
    _phases, _turn = _curriculum(ag, LAYOUT_OPEN, 0)
    ag.thought_log = str(path)
    walk = _exam(ag, LAYOUT_OPEN, int(turns))

    lines = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    posed = [r for r in lines if r.get("x") is not None]
    return {
        "log": str(path),
        "turns": len(lines),
        "lines_with_a_pose": len(posed),
        "goal_hits": walk["goal_hits"],
        "voxels_visited": len({(r["x"], r["y"], r["z"]) for r in posed}),
        "headings_seen": sorted({r["heading"] for r in posed}),
        "frame": posed[0]["frame"] if posed else None,
        "start": walk["start"],
        "trail": walk["trail"][:12],
    }


# GUI-3.5. Slow enough for a human and for the board's 200 ms poll; the
# point of `--live` is time, not speed.
LIVE_PACE = 0.12


def live_walk(out=None, pace: float = LIVE_PACE, turns=None) -> int:
    """School once, then walk greedily and do not stop.

    The cube has no more space to give — 162 poses is all there is — so
    what `--live` adds is time. `approach` on the goal collects and puts
    the body back at START, which means a greedy body walks the corridor
    again, and again, for as long as it is left running. Nothing is
    learned that the exam did not already learn: same Q, same T, same
    CAM, cortex off, and the diary is the same jsonl a board can follow.

    One run, one log: the file is truncated at the start, because a
    replay that begins with somebody else's walk is a replay that lies
    about what happened next.
    """
    from echoai.nexus0.loop import Agent

    path = Path(out) if out else (
        Path(__file__).resolve().parents[1] / "lab" / THOUGHT_LOG
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    ag = Agent(env=Body3DEnv(LAYOUT_OPEN), remainder=True, explore_flat=True)
    _phases, _turn = _curriculum(ag, LAYOUT_OPEN, 0)
    ag.env = Body3DEnv(LAYOUT_OPEN)
    ag.env.teleport(START)
    ag.thought_log = str(path)

    sys.stdout.write(f"{path}\n")
    sys.stdout.write(
        f"walking from {pose_name(START)} — Ctrl-C to stop\n"
    )
    sys.stdout.flush()
    t = 0
    paid = ag.metrics.action_pos  # the school's collections are not the walk's
    try:
        while turns is None or t < int(turns):
            ag.turn(10 ** 6 + t, greedy=True)
            t += 1
            # The log is appended and closed once per turn by the loop's
            # own writer, so there is nothing to flush here: a reader that
            # arrives between two turns always sees whole lines.
            if pace:
                time.sleep(float(pace))
    except KeyboardInterrupt:
        sys.stdout.write("\n")
    sys.stdout.write(
        f"{t} turns · {ag.metrics.action_pos - paid} collected\n")
    return t


def _arg(argv, name, default):
    return argv[argv.index(name) + 1] if name in argv else default


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--live" in argv:
        # A diary, not a report, exactly as `--thought`: no lab json is
        # opened on this path at all.
        turns = _arg(argv, "--turns", None)
        live_walk(
            out=_arg(argv, "--out", None),
            pace=float(_arg(argv, "--pace", LIVE_PACE)),
            turns=None if turns is None else int(turns),
        )
        return 0
    if "--thought" in argv:
        # A diary, not a report: `nexus0_pulpo_report.json` is not opened
        # on this path at all.
        walk = thought_walk()
        json.dump(walk, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if (walk["lines_with_a_pose"] == walk["turns"] > 0
                     and walk["goal_hits"] > 0) else 1
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_pulpo_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
