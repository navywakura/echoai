"""
CUERPO-1 — a body, not another graph.

The animal stops being an index in a table. It has a **pose**: where it
stands and which way it faces. Orientation is state of the body, not a
fourth action — the loop never sees a "north", it sees three actions and
a 16 B packet, exactly as in the ring.

    grid     5 x 5, six walls
    heading  0,1,2,3 = E, N, W, S   (y grows north)
    pose     index = (x + 5*y)*4 + heading      100 bins, < 256

    approach   one step the way it is facing. Into a wall or off the
               grid: it does not move, and the collision pays R_THREAT.
    avoid      turn 90 deg counter-clockwise (E->N->W->S). No translation.
    wait       nothing moves.

The room:

    y=4   S' .  .  .  G          S = start (0,0) facing E
    y=3   .  #  #  #  .          G = goal  (4,4)
    y=2   .  .  .  .  .          # = wall
    y=1   .  #  #  #  .          row y=2 is the corridor
    y=0   S  .  .  .  .

`kind` is a property of the **floor tile**, never of the heading: the
four poses standing on the goal tile are all GOAL, and the pose index is
what tells them apart. **No floor tile is painted THREAT.** The threat in
this world is the collision itself — approach into a wall — so nothing is
repainted to fake geometry, and `cell.threat` is false everywhere, which
means the gate never modifies an action here. The bump's -16 goes
straight into Q, unhelped.

Two layouts, one change of physics:

    open    the corridor is clear
    block   the middle of the corridor, (2,2), becomes a wall

Same start, same goal, same headings, same kinds. Nothing is repainted:
either there is a wall or there is not. The room still has a way round —
the left and right columns — so `block` is a harder room, not an
impossible one.

The analogy is a cerebellum predicting the consequence of a movement,
and it is an analogy: T here predicts a successor **pose** under a floor
plan, instead of `(i+1) % n`. That is the whole of the claim.

Not MiniGrid, not eight actions, not lidar, not a camera, not Akida.
Lidar and camera come later. The KPI runs with the cortex off.

    PYTHONPATH=. python3 -m echoai.nexus0.body
"""

from __future__ import annotations

import json
import sys
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

W = 5
H = 5
HEADINGS = 4
N_POSES = W * H * HEADINGS  # 100, and 100 < 256: no two poses share a packet
POSES_REQUESTED = 100

# E, N, W, S. y grows north, so +1 on the heading is a left turn.
EAST, NORTH, WEST, SOUTH = 0, 1, 2, 3
DIRS: Tuple[Tuple[int, int], ...] = ((1, 0), (0, 1), (-1, 0), (0, -1))
HEADING_NAME = ("E", "N", "W", "S")

WALLS: Tuple[Tuple[int, int], ...] = (
    (1, 1), (2, 1), (3, 1),
    (1, 3), (2, 3), (3, 3),
)
BLOCKED = (2, 2)  # the corridor tile that `block` closes

START_XY = (0, 0)
START_HEADING = EAST
GOAL_XY = (4, 4)

LAYOUT_OPEN = "open"
LAYOUT_BLOCK = "block"
LAYOUTS = (LAYOUT_OPEN, LAYOUT_BLOCK)

TRAIN_TURNS = 1024
PROBE_TURNS = 128


def index_of(x: int, y: int, h: int) -> int:
    """(x, y, heading) -> pose index. The formula, in one place."""
    return (int(x) + W * int(y)) * HEADINGS + (int(h) % HEADINGS)


def pose_of(index: int) -> Tuple[int, int, int]:
    """pose index -> (x, y, heading). The inverse, in one place."""
    tile, h = divmod(int(index) % N_POSES, HEADINGS)
    return tile % W, tile // W, h


def pose_name(index: int) -> str:
    x, y, h = pose_of(index)
    return f"({x},{y},{HEADING_NAME[h]})"


START = index_of(*START_XY, START_HEADING)
GOAL_POSES: Tuple[int, ...] = tuple(index_of(*GOAL_XY, h) for h in range(HEADINGS))


def walls_of(layout: str) -> frozenset:
    if layout == LAYOUT_BLOCK:
        return frozenset(WALLS + (BLOCKED,))
    return frozenset(WALLS)


def on_grid(x: int, y: int) -> bool:
    return 0 <= x < W and 0 <= y < H


def is_floor(x: int, y: int, layout: str) -> bool:
    return on_grid(x, y) and (x, y) not in walls_of(layout)


# One kind list for the whole body, shared by both layouts and indexed by
# pose. A tile's kind is the same under all four headings.
KINDS: List[int] = [KIND_EMPTY] * N_POSES
for _h in range(HEADINGS):
    KINDS[index_of(*GOAL_XY, _h)] = KIND_GOAL


def bumps(index: int, layout: str) -> bool:
    """Would `approach` from this pose hit a wall or the edge?

    False for a pose inside a wall: you cannot stand there, so there is
    nothing to collide with. The goal is asked about first by `_payoff`,
    so collecting never reads as a collision.
    """
    x, y, h = pose_of(index)
    if not is_floor(x, y, layout):
        return False
    dx, dy = DIRS[h]
    return not is_floor(x + dx, y + dy, layout)


def _successors(layout: str) -> Dict[int, Dict[int, int]]:
    """Successor by table, for every pose and every action.

    `avoid` is body physics and never consults the room: turning is the
    same act in an open field and in a cupboard, so changing the floor
    plan changes no `avoid` row at all. `approach` is the only action the
    room can answer.
    """
    approach: Dict[int, int] = {}
    avoid: Dict[int, int] = {}
    wait: Dict[int, int] = {}
    for index in range(N_POSES):
        x, y, h = pose_of(index)
        avoid[index] = index_of(x, y, (h + 1) % HEADINGS)
        wait[index] = index
        if index in GOAL_POSES:
            # Collect and go home. A goal you can stand on and re-collect
            # is a reward pump, not a room.
            approach[index] = START
        elif not is_floor(x, y, layout):
            # Unreachable. Its own successor, so the table is total
            # without inventing a move out of a wall.
            approach[index] = index
        elif bumps(index, layout):
            approach[index] = index
        else:
            dx, dy = DIRS[h]
            approach[index] = index_of(x + dx, y + dy, h)
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
        i for i in range(N_POSES) if is_floor(*pose_of(i)[:2], layout)
    )


class BodyEnv:
    """A turtle in a small room. Same interface the ring gives Agent."""

    def __init__(self, layout: str = LAYOUT_OPEN, seed: int = BENCH_SEED) -> None:
        if layout not in NEXT:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        self.kind: List[int] = list(KINDS)
        self.i = START
        self.hidden_bit = True  # part of the contract; nothing hides here
        self.last_reward = 0
        self.bumped = False
        self.reset()

    def reset(self) -> None:
        self.i = START
        self.kind = list(KINDS)
        self.last_reward = 0
        self.bumped = False

    def cell(self) -> Cell:
        return Cell(index=self.i, kind=self.kind[self.i])

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % N_POSES
        return self.cell()

    def _payoff(self, aa: int) -> int:
        kind = self.kind[self.i]
        if aa == ACTION_APPROACH:
            if kind == KIND_GOAL:
                return R_SUCCESS
            if bumps(self.i, self.layout):
                # The collision *is* the threat. No floor tile is painted
                # THREAT to fake one, and the ring's own reward table is
                # what pays: nothing here was retuned.
                return _reward(KIND_THREAT, ACTION_APPROACH, self.hidden_bit)
        return _reward(kind, aa, self.hidden_bit)

    def step(self, a: int):
        aa = int(a) % N_ACTIONS
        r = self._payoff(aa)
        # Facing north from the goal tile is also facing off the grid, so
        # `bumps()` alone would call every collection a collision. The
        # goal is asked about first here exactly as it is in `_payoff`.
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


def stepper(index: int) -> Optional[int]:
    """The baseline: always one step east, blind to heading and to walls.

    None when that would leave the grid — an arithmetic guess that cannot
    even be stated is a miss, not a free pass.
    """
    x, y, h = pose_of(index)
    if x + 1 >= W:
        return None
    return index_of(x + 1, y, h)


def t_vs_stepper(ag, layout: str) -> dict:
    """Score T and the stepper on the same poses, offline.

    Only poses whose `approach` row T has actually learned are counted,
    so both are answering the same questions. This is not a 0.99 world
    model: it is the same comparison JUMP made in the ring, where the
    ring's own arithmetic was beaten by a table that had seen the two
    exceptions. Here the exceptions are heading and walls.
    """
    t_hits = 0
    step_hits = 0
    asked = 0
    t_right_step_wrong: List[dict] = []
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
            t_right_step_wrong.append({
                "pose": pose_name(index),
                "why": "wall" if bumps(index, layout) else "heading",
                "truth": pose_name(truth),
                "stepper_said": None if guess is None else pose_name(guess),
            })
    # A stepper that could not even state a guess is the cheap half of the
    # win. Show the cases where it answered and was wrong first, and one
    # of each reason if the room offers both.
    answered = [e for e in t_right_step_wrong if e["stepper_said"] is not None]
    shown: List[dict] = []
    for why in ("heading", "wall"):
        for e in answered:
            if e["why"] == why:
                shown.append(e)
                break
    for e in answered + t_right_step_wrong:
        if len(shown) >= 4:
            break
        if e not in shown:
            shown.append(e)
    return {
        "stepper_answered_and_missed": len(answered),
        "asked": asked,
        "t_hits": t_hits,
        "stepper_hits": step_hits,
        "t_beats_stepper": t_hits > step_hits,
        "examples": shown,
    }


def approach_diff() -> List[int]:
    """Exactly which poses change where `approach` lands, open -> block."""
    return [
        i
        for i in range(N_POSES)
        if NEXT[LAYOUT_OPEN][ACTION_APPROACH][i]
        != NEXT[LAYOUT_BLOCK][ACTION_APPROACH][i]
    ]


def _train_free(layout: str, turns: int):
    """One agent, the ring's own defaults, cortex off, nobody helping.

    `run()` and nothing else: the animal goes where its own policy takes
    it. This is the arm the KPI is scored on, because a map built while
    an operator carried the animal from tile to tile would be measuring
    the operator.
    """
    from echoai.nexus0.loop import Agent

    ag = Agent(env=BodyEnv(layout))
    ag.run(turns)
    return ag


def _train_swept(layout: str, turns: int):
    """The same agent, carried to every reachable pose in turn.

    Not the KPI — the operator moving the animal. It answers a different
    question: what does T look like when the whole room has been felt,
    rather than the corner the policy happens to like? Teleporting is
    part of the env contract and the ring's own bench does it between
    phases; `env.step` still has three actions.
    """
    from echoai.nexus0.loop import Agent

    ag = Agent(env=BodyEnv(layout))
    poses = reachable(layout)
    for t in range(turns):
        ag.env.teleport(poses[t % len(poses)])
        ag.turn(t)
    return ag


def _stood_on(ag, layout: str) -> List[int]:
    """Poses the agent actually started a turn on, not merely allocated."""
    out = []
    for i in reachable(layout):
        slot = _slot(ag, i)
        if slot >= 0 and ag.cam.slot[slot].hits > 1:
            out.append(i)
    return out


def _greedy_probe(ag, turns: int) -> dict:
    """What the learned policy does when the coin is taken away."""
    ag.env = BodyEnv(ag.env.layout)
    ag.env.teleport(START)
    total = 0
    goal_hits = 0
    bumps_hit = 0
    poses = set()
    for t in range(turns):
        poses.add(ag.env.cell().index)
        ag.turn(TRAIN_TURNS + t, greedy=True)
        r = int(ag.env.last_reward)
        total += r
        goal_hits += int(r == R_SUCCESS)
        bumps_hit += int(ag.env.bumped)
    return {
        "reward_sum": total,
        "goal_hits": goal_hits,
        "bumps": bumps_hit,
        "poses_visited": len(poses),
    }


def experiment() -> dict:
    # The KPI arm: nobody carried the animal anywhere.
    free = _train_free(LAYOUT_OPEN, TRAIN_TURNS)
    free_scored = t_vs_stepper(free, LAYOUT_OPEN)
    free_poses = _stood_on(free, LAYOUT_OPEN)

    # The whole room, felt by hand. A second question, not the KPI.
    ag = _train_swept(LAYOUT_OPEN, TRAIN_TURNS)
    scored = t_vs_stepper(ag, LAYOUT_OPEN)

    # Physics, asked of the env rather than asserted in prose.
    probe = BodyEnv(LAYOUT_OPEN)
    probe.teleport(index_of(0, 0, WEST))  # facing off the grid
    bump_r, bump_cell = probe.step(ACTION_APPROACH)
    probe.teleport(index_of(2, 2, EAST))
    turn_r, turn_cell = probe.step(ACTION_AVOID)
    probe.teleport(GOAL_POSES[EAST])
    goal_r, goal_cell = probe.step(ACTION_APPROACH)

    # The room changes under the same agent: nothing is reset but the
    # floor plan, exactly as HOME -> SHIFT did.
    diff = approach_diff()
    before = {
        i: ag.t.predict(_slot(ag, i), ACTION_APPROACH)
        for i in reachable(LAYOUT_OPEN)
        if _slot(ag, i) >= 0
    }
    ag.env = BodyEnv(LAYOUT_BLOCK)
    ag.env.teleport(START)
    after = {
        i: ag.t.predict(_slot(ag, i), ACTION_APPROACH)
        for i in before
    }
    survived = sum(1 for i in before if before[i] == after[i])
    unaffected = [i for i in before if i not in set(diff)]
    still_true = sum(
        1
        for i in unaffected
        if after[i] is not None
        and after[i] == _slot(ag, NEXT[LAYOUT_BLOCK][ACTION_APPROACH][i])
    )

    # Greedy from the start, in the room it trained in. Reported beside
    # the KPI, never as the KPI: reaching the goal on purpose is WALK-1.
    greedy_free = _greedy_probe(_train_free(LAYOUT_OPEN, TRAIN_TURNS), PROBE_TURNS)
    greedy_swept = _greedy_probe(_train_swept(LAYOUT_OPEN, TRAIN_TURNS), PROBE_TURNS)

    return {
        "world": "body",
        "poses_requested": POSES_REQUESTED,
        "poses": N_POSES,
        "reason": "host",
        "grid": [W, H],
        "headings": HEADINGS,
        "actions": N_ACTIONS,
        "turn_direction": "counter-clockwise (E->N->W->S)",
        "walls_open": [list(t) for t in WALLS],
        "blocked_tile": list(BLOCKED),
        "start": pose_name(START),
        "goal": f"({GOAL_XY[0]},{GOAL_XY[1]})",
        "reachable_poses_open": len(reachable(LAYOUT_OPEN)),
        "reachable_poses_block": len(reachable(LAYOUT_BLOCK)),
        "packet_ceiling": 256,
        "max_pose_index": N_POSES - 1,
        "train_turns": TRAIN_TURNS,
        # KPI 1 — T predicts a pose under a floor plan, arithmetic does not.
        # Scored on the free-running agent: no operator, no teleporting.
        "free_poses_stood_on": len(free_poses),
        "free_loop": [pose_name(i) for i in free_poses],
        "t_asked": free_scored["asked"],
        "t_hits": free_scored["t_hits"],
        "stepper_hits": free_scored["stepper_hits"],
        "t_beats_stepper": free_scored["t_beats_stepper"],
        "stepper_answered_and_missed": free_scored["stepper_answered_and_missed"],
        "t_right_stepper_wrong": free_scored["examples"],
        # Every positive reward in this room is a goal collected: no floor
        # tile is THREAT, so R_AVOID_OK can never be paid and action_pos
        # counts collections exactly.
        "free_goal_hits_in_training": free.metrics.action_pos,
        # Why the greedy probe below stands still, as a number rather than
        # an excuse. Same integer credit horizon WORLD-3 measured: alpha =
        # 1/4 drops a positive delta below 4, so value stops travelling
        # about three steps back from the goal. Making the body walk the
        # whole loop on purpose is WALK-1.
        "free_loop_q_approach": [
            free.q.row(_slot(free, i))[ACTION_APPROACH]
            if _slot(free, i) >= 0 else None
            for i in free_poses
        ],
        # The same comparison over the whole room, felt by hand.
        "swept_t_asked": scored["asked"],
        "swept_t_hits": scored["t_hits"],
        "swept_stepper_hits": scored["stepper_hits"],
        "swept_t_beats_stepper": scored["t_beats_stepper"],
        "swept_stepper_answered_and_missed":
            scored["stepper_answered_and_missed"],
        "swept_t_right_stepper_wrong": scored["examples"],
        # KPI 2 — the collision is the threat.
        "bump_reward": int(bump_r),
        "bump_pose_unchanged": bump_cell.index == index_of(0, 0, WEST),
        "bump_is_threat": int(bump_r) == R_THREAT,
        # KPI 3 — avoid turns, it does not translate.
        "turn_from": pose_name(index_of(2, 2, EAST)),
        "turn_to": pose_name(turn_cell.index),
        "avoid_turns_not_translates": pose_of(turn_cell.index)[:2] == (2, 2),
        "turn_reward": int(turn_r),
        # KPI 4 — the goal does not pump.
        "goal_reward": int(goal_r),
        "goal_returns_to_start": goal_cell.index == START,
        # KPI 5 — one change of physics, counted.
        "approach_diff_count": len(diff),
        "approach_diff_poses": [pose_name(i) for i in diff],
        "avoid_diff_count": sum(
            1
            for i in range(N_POSES)
            if NEXT[LAYOUT_OPEN][ACTION_AVOID][i]
            != NEXT[LAYOUT_BLOCK][ACTION_AVOID][i]
        ),
        "t_rows_carried": len(before),
        "t_rows_unchanged_by_the_move": survived,
        "t_rows_unaffected": len(unaffected),
        "t_unaffected_still_true_in_block": still_true,
        "cam_occupied": _cam_occupied(ag),
        "cam_slots": len(ag.cam.slot),
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
        "cortex_calls": ag.metrics.cortex_calls,
        "questions": ag.metrics.questions,
        # Beside the KPI, not part of it. WALK-1 is the next slice.
        "greedy_probe_turns": PROBE_TURNS,
        "greedy_free": greedy_free,
        "greedy_swept": greedy_swept,
    }


# --------------------------------------------------------------------
# WALK-1 — reverse curriculum in training, exam at the canonical start.
# --------------------------------------------------------------------

EXAM_TURNS = 128
PHASE_REPS = 24  # times each pose at a given distance is trained from


def distances(layout: str) -> Dict[int, int]:
    """Minimum actions until a goal is collected, standing on each pose.

    Flooded backwards over the successor table itself, so a turn costs a
    step exactly as a step does, and a wall is not a shortcut. Not
    Manhattan: Manhattan is blind to heading, and heading is half of this
    body's state.
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
    """Descend the distance map from `start` to a goal pose.

    Read out of the physics, never written down: this is what the report
    prints Q along, and nothing chooses an action from it.
    """
    dist = distances(layout)
    path = [start]
    here = start
    while dist.get(here, 0) > 0:
        best = None
        for a in (ACTION_APPROACH, ACTION_AVOID):
            nxt = NEXT[layout][a][here]
            if nxt != here and dist.get(nxt, 10 ** 6) == dist[here] - 1:
                best = nxt
                break
        if best is None:
            break
        path.append(best)
        here = best
    return path


def credit_chain(shift: int, steps: int, reward: int = R_SUCCESS) -> List[int]:
    """Where integer Q stops, as arithmetic rather than as an excuse.

    A pure model of `qtable.update` on a chain of states whose only pay-off
    is `reward` at the end, iterated to its fixed point. Nothing is
    monkeypatched and `qtable` is not touched: this only replays the
    integer expression it already computes,

        q <- q + ((r + (7 * q_next) // 8 - q) >> shift)

    With the shipped shift of 2, a positive delta below 4 shifts to zero
    and the chain stops dead. The prediction is checked against the
    measured rows in the report.
    """
    chain = [0] * (steps + 1)
    for _ in range(4096):
        moved = False
        for k in range(steps + 1):
            r = reward if k == 0 else 0
            nxt = chain[k - 1] if k > 0 else 0
            delta = r + (GAMMA_NUM * nxt) // GAMMA_DEN - chain[k]
            step = delta >> int(shift)
            if step:
                chain[k] += step
                moved = True
        if not moved:
            break
    return chain


def _exam(ag, turns: int = EXAM_TURNS) -> dict:
    """Greedy, cortex off, from the canonical start of CUERPO-1.

    Not from a pose one step from the goal. `START` is the module
    constant the whole slice is built on, and green() checks the name of
    the pose the exam actually used.
    """
    ag.env = BodyEnv(LAYOUT_OPEN)
    ag.env.teleport(START)
    total = 0
    hits = 0
    bumped = 0
    poses = set()
    for t in range(turns):
        poses.add(ag.env.cell().index)
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
        "poses_visited": len(poses),
    }


def credit_chain_remainder(steps: int, reward: int = R_SUCCESS) -> List[int]:
    """The same chain, with the crumbs kept. Arithmetic, not a run.

    With the remainder, a delta of 1, 2 or 3 is owed rather than dropped,
    so every state converges on its target exactly and the chain becomes
    `q_k = (7 * q_(k+1)) // 8` with no `- 3`. alpha is still 1/4; what
    changed is only that nothing is thrown away.
    """
    chain = [0] * (steps + 1)
    for _ in range(4096):
        moved = False
        for k in range(steps + 1):
            r = reward if k == 0 else 0
            nxt = chain[k - 1] if k > 0 else 0
            target = r + (GAMMA_NUM * nxt) // GAMMA_DEN
            if chain[k] != target:
                chain[k] += 1 if target > chain[k] else -1
                moved = True
        if not moved:
            break
    return chain


def walk(remainder: bool = False) -> dict:
    """Train outward from the goal; examine from the start. One agent.

    The curriculum changes only **where a training turn is taken from**.
    Q, T and CAM are never copied, reset or written by hand, exploration
    is the usual `q.select`, and no action anywhere is chosen from a
    stored route.

    `remainder` is CREDIT-1 and nothing else about this function changes
    with it: same curriculum, same exam, same start, same rewards, same
    alpha. The only difference is whether `QTable.update` keeps the three
    quarters that `>> 2` discards.
    """
    from echoai.nexus0.loop import Agent

    layout = LAYOUT_OPEN
    by_dist = poses_by_distance(layout)
    dist = distances(layout)
    ag = Agent(env=BodyEnv(layout), remainder=remainder)

    turn = 0
    rem_peak = 0
    phases: List[dict] = []
    for d in sorted(k for k in by_dist if k > 0):
        before = ag.metrics.action_pos
        for _rep in range(PHASE_REPS):
            for pose in by_dist[d]:
                ag.env.teleport(pose)
                for _ in range(d + 2):
                    ag.turn(turn)
                    turn += 1
        sample = by_dist[d][0]
        if remainder:
            rem_peak = max(
                rem_peak,
                max(
                    (abs(v)
                     for p in reachable(layout) if _slot(ag, p) >= 0
                     for v in ag.q.rem[_slot(ag, p)]),
                    default=0,
                ),
            )
        phases.append({
            "dist": d,
            "poses": len(by_dist[d]),
            "turns": PHASE_REPS * len(by_dist[d]) * (d + 2),
            "goal_hits_in_phase": ag.metrics.action_pos - before,
            "q_approach_at_a_pose_of_this_distance":
                ag.q.row(_slot(ag, sample))[ACTION_APPROACH],
        })

    path = shortest_path(layout, START)
    exam = _exam(ag)

    q_by_dist = {}
    for d in sorted(by_dist):
        rows = [
            ag.q.row(_slot(ag, p))[ACTION_APPROACH]
            for p in by_dist[d]
            if _slot(ag, p) >= 0
        ]
        q_by_dist[str(d)] = max(rows) if rows else None

    rem_rows = [
        ag.q.rem[_slot(ag, p)][ACTION_APPROACH]
        for p in path
        if _slot(ag, p) >= 0
    ] if remainder else []
    return {
        "world": "body",
        "slice": "credit1" if remainder else "walk1",
        "remainder": bool(remainder),
        "layout": layout,
        # Copied so it is visible that none of them moved.
        "alpha_shift": ALPHA_SHIFT,
        "gamma": [GAMMA_NUM, GAMMA_DEN],
        "R": {"success": R_SUCCESS, "threat": R_THREAT, "avoid_ok": R_AVOID_OK},
        "traces": False,
        "plan_depth": ag.plan_depth,
        "start_distance": dist.get(START),
        "curriculum": phases,
        "curriculum_turns": turn,
        "exam_start": exam["start"],
        "exam_start_is_canonical": exam["start"] == pose_name(START),
        "exam_turns": exam["turns"],
        "exam_goal_hits": exam["goal_hits"],
        "exam_reward_sum": exam["reward_sum"],
        "exam_bumps": exam["bumps"],
        "exam_poses_visited": exam["poses_visited"],
        "path_from_start": [pose_name(p) for p in path],
        "path_distances": [dist.get(p) for p in path],
        "q_approach_along_a_path_from_start": [
            ag.q.row(_slot(ag, p))[ACTION_APPROACH] if _slot(ag, p) >= 0 else None
            for p in path
        ],
        "q_rows_along_a_path_from_start": [
            ag.q.row(_slot(ag, p)) if _slot(ag, p) >= 0 else None for p in path
        ],
        "best_q_approach_by_distance": q_by_dist,
        # The wall, predicted from the shipped integers alone. Untouched
        # by this slice: the remainder is another road, not a new alpha.
        "credit_chain_shift_2": credit_chain(ALPHA_SHIFT, 12),
        "credit_chain_shift_0": credit_chain(0, 12),
        "credit_chain_with_remainder": credit_chain_remainder(12),
        # What the crumbs actually look like. At the fixed point delta is
        # zero and nothing is owed, so the end-state remainder is mostly
        # 0 — the number that matters is how big the debt ever got while
        # the value was still moving, and it is small and bounded.
        "rem_along_a_path_from_start": rem_rows,
        "rem_abs_max_on_path": max((abs(v) for v in rem_rows), default=0),
        "rem_abs_max_during_training": rem_peak,
        "rem_nonzero_at_end": sum(
            1
            for p in reachable(layout)
            if _slot(ag, p) >= 0
            for v in ag.q.rem[_slot(ag, p)]
            if v
        ) if remainder else 0,
        "rem_rows_allocated": len(ag.q.rem),
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
        "cortex_calls": ag.metrics.cortex_calls,
        "questions": ag.metrics.questions,
    }


def walk_green(report: dict) -> bool:
    """The KPI, unweakened: the animal collects at least once, greedy,
    starting from the canonical start of CUERPO-1."""
    return bool(
        report["exam_start_is_canonical"]
        and report["exam_goal_hits"] > 0
        and report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["alpha_shift"] == ALPHA_SHIFT
        and report["R"]["success"] == R_SUCCESS
        and report["R"]["threat"] == R_THREAT
        and report["R"]["avoid_ok"] == R_AVOID_OK
        and report["gamma"] == [GAMMA_NUM, GAMMA_DEN]
        and not report["traces"]
    )


def green(report: dict) -> bool:
    """Every KPI at once. One red number and the slice is red."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["actions"] == 3
        and report["poses"] == POSES_REQUESTED
        and report["t_beats_stepper"]
        and report["swept_t_beats_stepper"]
        and report["bump_is_threat"]
        and report["bump_pose_unchanged"]
        and report["avoid_turns_not_translates"]
        and report["goal_returns_to_start"]
        and report["approach_diff_count"] > 0
        and report["avoid_diff_count"] == 0
        and report["t_unaffected_still_true_in_block"]
        == report["t_rows_unaffected"]
    )


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--walk-remainder" in argv:
        return main_walk(remainder=True)
    if "--walk" in argv:
        return main_walk()
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_cuerpo1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


def main_walk(remainder: bool = False) -> int:
    report = walk(remainder=remainder)
    report["green"] = walk_green(report)
    name = "nexus0_credit1_report.json" if remainder else "nexus0_walk1_report.json"
    out = Path(__file__).resolve().parents[1] / "lab" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
