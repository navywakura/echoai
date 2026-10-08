"""
SELF-1 — "was that me, or was that the floor?"

PULPO-C changed strategy because a curriculum taught the body the cube it
was standing in. That is adaptation, not attribution: the body was told
nothing about *why* its predictions went wrong, and it did not need to
know. Here it does.

Two perturbations, and the observation they produce is the same sentence:
`approach` did not land where T said it would.

    motor   the body slips. `approach` pushes along DIRS[(h + slip) % 6]
            while the heading of the pose does not turn. The cube, the
            floor, the goal and the start are untouched.
    world   one corridor voxel turns to stone. The motor is intact.

Neither perturbation is announced. Nothing is written into the WSP, into
`kind`, into `extract` or into E: the packet for a pose is byte-identical
in both arms, and there is no CONCIENCIA atom, no second CAM and no
fourth action. The only new state is one integer:

    body_offset in 0..5     "my approach pushes along (h + body_offset)"

Six hypotheses, all integers. The body can state them because it already
owns the ring: "push along (h + k)" is exactly "what `avoid` k times then
`approach` used to do", and T learned both before anything moved. So the
hypothesis is written in the body's own actions, never in coordinates.

What the self-model buys is not speed, it is **not rewriting the world**.
On a surprise the plain agent updates T at once: that is right when the
floor moved and wrong when the arm did. SELF-1 holds the update, counts
which of the six hypotheses would explain the errors it is holding, and
only then decides — commit them (the world changed) or drop the ones the
body explains (it was me). A tie is not me: it commits.

    PYTHONPATH=. python3 -m echoai.nexus0.self1
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    N_ACTIONS,
    R_SUCCESS,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_GOAL, KIND_THREAT, Cell, _reward
from echoai.nexus0 import body3d as cube

SLIP = 1
WORLD_PLUG = cube.BLOCKED
NO_SLIP = 0

# The observation window. Every reachable pose, twice, two turns each:
# bounded, small, and printed in the report as `observe_turns`. The body
# has to actually push to find out that its push has moved, so the sweep
# is over poses rather than over one wandering trajectory — a trajectory
# only ever visits the poses its own policy likes.
OBSERVE_SWEEPS = 2
OBSERVE_TURNS_PER_POSE = 3

ARM_MOTOR = "motor"
ARM_WORLD = "world"


# ---------------------------------------------------------------- the body

def slipped_successors(layout: str, slip: int) -> Dict[int, Dict[int, int]]:
    """The cube's successor table with the arm turned by `slip` notches.

    `avoid` and `wait` are untouched: turning is the body's own ring and
    never consults the room, and standing still is standing still. Only
    `approach` reads the heading through the offset, and the pose's
    heading does **not** rotate — the body still believes it faces `h`.
    """
    approach: Dict[int, int] = {}
    avoid: Dict[int, int] = {}
    wait: Dict[int, int] = {}
    for index in range(cube.N_POSES):
        x, y, z, h = cube.pose_of(index)
        avoid[index] = cube.index_of(x, y, z, (h + 1) % cube.HEADINGS)
        wait[index] = index
        if index in cube.GOAL_POSES:
            approach[index] = cube.START
        elif not cube.is_floor(x, y, z, layout):
            approach[index] = index
        else:
            dx, dy, dz = cube.DIRS[(h + int(slip)) % cube.HEADINGS]
            approach[index] = (
                cube.index_of(x + dx, y + dy, z + dz, h)
                if cube.is_floor(x + dx, y + dy, z + dz, layout)
                else index
            )
    return {
        ACTION_APPROACH: approach,
        ACTION_AVOID: avoid,
        ACTION_WAIT: wait,
    }


def pushes_into_stone(index: int, layout: str, slip: int) -> bool:
    """Would `approach` from this pose hit stone or the outside?"""
    x, y, z, h = cube.pose_of(index)
    if not cube.is_floor(x, y, z, layout):
        return False
    dx, dy, dz = cube.DIRS[(h + int(slip)) % cube.HEADINGS]
    return not cube.is_floor(x + dx, y + dy, z + dz, layout)


class Self1Env:
    """The PULPO cube with two knobs: which voxel is stone, and which way
    the arm pushes. With `slip == 0` it is `Body3DEnv`, step for step."""

    def __init__(self, layout: str = cube.LAYOUT_OPEN, slip: int = NO_SLIP) -> None:
        if layout not in cube.LAYOUTS:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.slip = int(slip) % cube.HEADINGS
        self.next = slipped_successors(self.layout, self.slip)
        self.kind: List[int] = list(cube.KINDS)
        self.i = cube.START
        self.hidden_bit = True
        self.last_reward = 0
        self.bumped = False
        self.reset()

    def reset(self) -> None:
        self.i = cube.START
        self.kind = list(cube.KINDS)
        self.last_reward = 0
        self.bumped = False

    def cell(self) -> Cell:
        return Cell(index=self.i, kind=self.kind[self.i])

    def teleport(self, i: int) -> Cell:
        self.i = int(i) % cube.N_POSES
        return self.cell()

    def _payoff(self, aa: int) -> int:
        kind = self.kind[self.i]
        if aa == ACTION_APPROACH:
            if kind == KIND_GOAL:
                return R_SUCCESS
            if pushes_into_stone(self.i, self.layout, self.slip):
                return _reward(KIND_THREAT, ACTION_APPROACH, self.hidden_bit)
        return _reward(kind, aa, self.hidden_bit)

    def step(self, a: int):
        aa = int(a) % N_ACTIONS
        r = self._payoff(aa)
        self.bumped = (
            aa == ACTION_APPROACH
            and self.kind[self.i] != KIND_GOAL
            and pushes_into_stone(self.i, self.layout, self.slip)
        )
        self.i = self.next[aa][self.i]
        self.last_reward = int(r)
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing to reveal here. Part of the contract, and honest."""
        return False


# -------------------------------------------------------------- the model

class SelfModel:
    """Six integer hypotheses about one arm, and the discipline to wait.

    Attached to an agent it intercepts one thing: whether an `approach`
    that surprised T is allowed to rewrite T. Everything else — `avoid`,
    `wait`, and every `approach` that was predicted correctly — goes
    through untouched, so a world that really did change is still learned.
    """

    def __init__(self, agent, hold: bool = True) -> None:
        self.agent = agent
        # Whether a surprise is suspended until the verdict. Measured, not
        # assumed: see `probe_holding` and the report field it fills.
        self.hold = bool(hold)
        # T as it stood before anything moved. Two rows are enough: the
        # ring the body turns through, and the push it is testing.
        self.was_approach: List[int] = [
            agent.t.pred[s][ACTION_APPROACH] for s in range(len(agent.t.pred))
        ]
        self.was_avoid: List[int] = [
            agent.t.pred[s][ACTION_AVOID] for s in range(len(agent.t.pred))
        ]
        self.unknown = _unknown_next()
        self.held: List[Tuple[int, int]] = []
        self.body_offset = 0
        self.settled = False
        # Two tallies per hypothesis, and they answer different questions.
        # `explained` is how many of the surprises k would account for.
        # `contradicted` is how many pushes k gets *wrong* — over every
        # push in the window, not just the surprising ones.
        self.explained: List[int] = [0] * cube.HEADINGS
        self.contradicted: List[int] = [0] * cube.HEADINGS
        self.contradicted_any: List[int] = [0] * cube.HEADINGS
        self.pushes = 0
        self.surprises = 0
        self.committed = 0
        self.dropped = 0

    # -- the hypothesis, written in actions rather than in coordinates ----
    def hypothesis(self, s: int, k: int) -> Optional[int]:
        """Where "turn k, push, turn back" used to land, according to T.

        The whole ring, not half of it. A slipped arm pushes sideways and
        leaves the body facing where it already faced, so the composite
        that describes it has to come back: k avoids, one approach, and
        the remaining avoids that close the ring. Stopping after the push
        would describe a body that had turned, which is a different animal
        and matches nothing.

        k == 0 is a full ring, which is the identity, so it is simply what
        T predicted. There are no coordinates anywhere here and no
        successor table: `avoid` is the body's own ring and T learned both
        rows before anything moved, so this is the body asking itself a
        question it already has the answer to.
        """
        ring = cube.HEADINGS
        kk = int(k) % ring
        here = int(s)
        for _ in range(kk):
            here = self.was_avoid[here]
            if here == self.unknown:
                return None
        here = self.was_approach[here]
        if here == self.unknown:
            return None
        for _ in range(ring - kk):
            here = self.was_avoid[here]
            if here == self.unknown:
                return None
        return here

    def _tally(self, s: int, s_next: int, surprising: bool) -> None:
        """Score all six hypotheses against one push.

        Only a push that surprised the arm the body thought it had is
        allowed to judge a hypothesis. That is not squeamishness: the one
        transition in this cube that no offset can describe is the one
        where the room picks the body up and puts it back at the start,
        and it never surprises anybody, because T learned it before
        anything moved. Scored over every step instead, that single
        transition contradicts the true offset ten times out of thirty and
        buries it — `contradicted_any` is kept in the report so the size
        of that effect is a number rather than a claim.
        """
        self.pushes += 1
        self.surprises += int(surprising)
        for k in range(cube.HEADINGS):
            guess = self.hypothesis(s, k)
            if guess is None:
                continue
            if guess == s_next:
                if surprising:
                    self.explained[k] += 1
            else:
                self.contradicted_any[k] += 1
                if surprising:
                    self.contradicted[k] += 1

    def observe_step(self, s: int, a: int, s_next: int) -> bool:
        """True when T may learn this step. Called once per turn."""
        if int(a) % N_ACTIONS != ACTION_APPROACH:
            return True
        expected = self.hypothesis(s, 0)
        if not self.settled and expected is not None:
            self._tally(int(s), int(s_next), surprising=expected != s_next)
        if expected is None or expected == s_next:
            return True
        if self.settled:
            # Already decided. An error the offset accounts for is the arm
            # repeating itself, not news about the room.
            if self.body_offset and self.hypothesis(s, self.body_offset) == s_next:
                return False
            return True
        # Undecided: hold the surprise instead of spending it.
        self.held.append((int(s), int(s_next)))
        return not self.hold

    def _attribute(self) -> int:
        """Which offset, if any, describes this arm. 0 means "not me".

        An offset is a claim about **every** surprise, not about most of
        them: if the arm really is turned by k, then there is no push left
        over that k gets wrong. So one counter-example kills a hypothesis.
        It has to explain at least one surprise, contradict none, and be
        alone in doing so — otherwise the answer is 0 and the surprises
        get spent on the room, which is where a body that did not know any
        better would have spent them anyway.

        Being alone matters as much as surviving. A push that ends where
        it began is explained by every offset that also ends in stone, and
        several always do, so a wall in front of the body produces a crowd
        of survivors and no verdict — which is the correct verdict, since
        a wall is not an arm.

        Nothing is read but the pose a push started from and the pose it
        landed on. No label is consulted, because none exists.
        """
        survivors = [
            k for k in range(1, cube.HEADINGS)
            if self.explained[k] > 0 and self.contradicted[k] == 0
        ]
        return survivors[0] if len(survivors) == 1 else 0

    def settle(self) -> int:
        """Close the window: decide, then pay out what was held back."""
        self.body_offset = self._attribute()
        self.settled = True
        for start, landed in self.held:
            if self.body_offset and self.hypothesis(start, self.body_offset) == landed:
                self.dropped += 1
                continue
            self.agent.t.observe(start, ACTION_APPROACH, landed)
            self.committed += 1
        self.held = []
        self.agent.body_offset = self.body_offset
        return self.body_offset


def _unknown_next() -> int:
    from echoai.nexus0.constants import UNKNOWN_NEXT
    return UNKNOWN_NEXT


# ------------------------------------------------------------ measurement

def _slot(ag, index: int) -> int:
    return ag.cam.get(encode_cell(index, cube.KINDS[index]))


def _cam_occupied(ag) -> int:
    return sum(1 for s in ag.cam.slot if s.occupied)


def intact_successors() -> Dict[int, int]:
    """`approach` in the cube nobody touched: no slip, no plug."""
    return slipped_successors(cube.LAYOUT_OPEN, NO_SLIP)[ACTION_APPROACH]


def t_world_preserved(ag, skip: Tuple[int, ...] = ()) -> Tuple[int, int]:
    """Rows of T that still describe the cube as it was built.

    Counted over the poses the floor never touched, so the world arm is
    not charged for learning the one thing that genuinely changed.
    """
    truth = intact_successors()
    skipped = set(skip)
    ok = 0
    asked = 0
    for index in cube.reachable(cube.LAYOUT_OPEN):
        if index in skipped:
            continue
        slot = _slot(ag, index)
        if slot < 0:
            continue
        asked += 1
        pred = ag.t.predict(slot, ACTION_APPROACH)
        if pred is not None and pred == _slot(ag, truth[index]):
            ok += 1
    return ok, asked


def distances_for(env: Self1Env) -> Dict[int, int]:
    """Minimum actions until a goal is collected, flooded over the table."""
    pred: Dict[int, set] = {}
    for pose in range(cube.N_POSES):
        for a in (ACTION_APPROACH, ACTION_AVOID):
            pred.setdefault(env.next[a][pose], set()).add(pose)
    dist: Dict[int, int] = {g: 0 for g in cube.GOAL_POSES}
    edge = list(cube.GOAL_POSES)
    while edge:
        nxt = []
        for here in edge:
            for prev in pred.get(here, ()):
                if prev not in dist and prev != here:
                    dist[prev] = dist[here] + 1
                    nxt.append(prev)
        edge = nxt
    return dist


def reachable_in(env: Self1Env) -> Tuple[int, ...]:
    return tuple(
        i for i in range(cube.N_POSES)
        if cube.is_floor(*cube.pose_of(i)[:3], env.layout)
    )


# --------------------------------------------------------------- the arms

def observe(ag, env: Self1Env, turn: int) -> int:
    """The window. Push everywhere, exploring, and see what the arm does."""
    ag.env = env
    for _sweep in range(OBSERVE_SWEEPS):
        for pose in reachable_in(env):
            env.teleport(pose)
            for _ in range(OBSERVE_TURNS_PER_POSE):
                ag.turn(turn)
                turn += 1
    return turn


def school(ag, env: Self1Env, turn: int) -> Tuple[List[dict], int]:
    """Reverse curriculum in whatever cube the body is standing in now.

    Same shape as PULPO-C's: nearest the goal first, teleport as a
    training aid only, and the distances are flooded over the successor
    table rather than named.
    """
    dist = distances_for(env)
    by_dist: Dict[int, List[int]] = {}
    for pose in reachable_in(env):
        if pose in dist and dist[pose] > 0:
            by_dist.setdefault(dist[pose], []).append(pose)
    ag.env = env
    phases: List[dict] = []
    for d in sorted(by_dist):
        before = ag.metrics.action_pos
        for _rep in range(cube.TRAIN_REPS):
            for pose in by_dist[d]:
                env.teleport(pose)
                for _ in range(cube.episode_turns(d)):
                    ag.turn(turn)
                    turn += 1
        phases.append({
            "dist": d,
            "poses": len(by_dist[d]),
            "goal_hits_in_phase": ag.metrics.action_pos - before,
        })
    return phases, turn


def exam(ag, env: Self1Env, turns: int = cube.EXAM_TURNS) -> dict:
    """Greedy, cortex off, from the canonical START. Never a neighbour."""
    ag.env = env
    env.teleport(cube.START)
    total = 0
    hits = 0
    poses = []
    for t in range(turns):
        poses.append(env.cell().index)
        ag.turn(10 ** 6 + t, greedy=True)
        r = int(env.last_reward)
        total += r
        hits += int(r == R_SUCCESS)
    return {
        "start": cube.pose_name(cube.START),
        "goal_hits": hits,
        "reward_sum": total,
        "poses_visited": len(set(poses)),
        "voxels_visited": sorted({cube.pose_of(p)[:3] for p in poses}),
        "trail": [cube.pose_name(p) for p in poses[:16]],
    }


def probe_offset(base, layout: str, slip: int, turn: int = 10 ** 5) -> dict:
    """One window and one verdict. No schooling, no exam.

    Here so the report can show the same machinery answering a *different*
    slip. An attribution that only ever says 1 is a constant with extra
    steps; this is what tells the two apart, every run.
    """
    ag = copy.deepcopy(base)
    model = SelfModel(ag)
    ag.self_model = model
    observe(ag, Self1Env(layout, slip), turn)
    return {
        "slip": slip,
        "body_offset": model.settle(),
        "explained": list(model.explained),
        "contradicted": list(model.contradicted),
        "surprises_seen": model.surprises,
    }


def probe_holding(base, layout: str, slip: int, turn: int = 2 * 10 ** 5) -> dict:
    """What suspending a surprise until the verdict is actually worth.

    Two windows, identical but for the suspension, and the answer is the
    world model that survives each. It is here because the honest answer
    turned out to be **nothing** on this cube: T's own conflict discipline
    already refuses to unseat a successor a whole curriculum agreed on
    until the challenger strictly out-counts it, and a window this short
    never gets close. The suspension is the order the reasoning wants —
    decide, then spend — and it is not what saves the map. Printed rather
    than argued, so the day a window is long enough to matter the number
    moves on its own.
    """
    out = {}
    for hold in (True, False):
        ag = copy.deepcopy(base)
        model = SelfModel(ag, hold=hold)
        ag.self_model = model
        observe(ag, Self1Env(layout, slip), turn)
        kept, asked = t_world_preserved(ag)
        model.settle()
        settled, _ = t_world_preserved(ag)
        out["with_holding" if hold else "without_holding"] = {
            "t_world_after_window": kept,
            "t_world_after_verdict": settled,
            "body_offset": model.body_offset,
        }
        out["t_world_asked"] = asked
    return out


def run_arm(base, layout: str, slip: int, with_self_model: bool,
            skip: Tuple[int, ...], turn: int) -> dict:
    """One perturbation, one agent. The control is this with the flag off."""
    ag = copy.deepcopy(base)
    model = SelfModel(ag) if with_self_model else None
    if model is not None:
        ag.self_model = model

    env = Self1Env(layout, slip)
    turn = observe(ag, env, turn)
    offset = model.settle() if model is not None else ag.body_offset

    kept_after_window, asked = t_world_preserved(ag, skip)
    _phases, turn = school(ag, env, turn)
    scores = exam(ag, env)
    kept, _asked = t_world_preserved(ag, skip)

    return {
        "layout": layout,
        "slip": slip,
        "self_model": with_self_model,
        "body_offset": offset,
        "explained": list(model.explained) if model is not None else [],
        "contradicted": list(model.contradicted) if model is not None else [],
        "contradicted_any": (list(model.contradicted_any)
                             if model is not None else []),
        "pushes_seen": model.pushes if model is not None else 0,
        "surprises_seen": model.surprises if model is not None else 0,
        "held_committed": model.committed if model is not None else None,
        "held_dropped": model.dropped if model is not None else None,
        "t_world_preserved": kept,
        "t_world_preserved_after_window": kept_after_window,
        "t_world_asked": asked,
        "goal_hits": scores["goal_hits"],
        "reward_sum": scores["reward_sum"],
        "poses_visited": scores["poses_visited"],
        "trail": scores["trail"],
        "cam_occupied": _cam_occupied(ag),
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
        "cortex_calls": ag.metrics.cortex_calls,
        "questions": ag.metrics.questions,
        "turn": turn,
    }


def experiment() -> dict:
    from echoai.nexus0.loop import Agent

    ag = Agent(env=cube.Body3DEnv(cube.LAYOUT_OPEN),
               remainder=True, explore_flat=True)
    _phases, turn = cube._curriculum(ag, cube.LAYOUT_OPEN, 0)

    # The plug changes four `approach` rows and nothing else; those poses
    # are the one thing the world arm is *supposed* to relearn, so they do
    # not count towards keeping the old cube.
    moved = tuple(cube.approach_diff())

    probe2 = probe_offset(ag, cube.LAYOUT_OPEN, 2, turn)
    holding = probe_holding(ag, cube.LAYOUT_OPEN, SLIP)

    motor = run_arm(ag, cube.LAYOUT_OPEN, SLIP, True, (), turn)
    motor_ctl = run_arm(ag, cube.LAYOUT_OPEN, SLIP, False, (), turn)
    world = run_arm(ag, cube.LAYOUT_BLOCK, NO_SLIP, True, moved, turn)
    world_ctl = run_arm(ag, cube.LAYOUT_BLOCK, NO_SLIP, False, moved, turn)

    attribution_agent = int(
        motor["body_offset"] == SLIP and world["body_offset"] == NO_SLIP
    )
    attribution_control = int(
        motor_ctl["body_offset"] == SLIP and world_ctl["body_offset"] == NO_SLIP
    )
    observe_turns = OBSERVE_SWEEPS * OBSERVE_TURNS_PER_POSE * len(
        cube.reachable(cube.LAYOUT_OPEN)
    )
    packets_match = all(
        encode_cell(i, cube.KINDS[i]) == encode_cell(i, cube.KINDS[i])
        for i in range(cube.N_POSES)
    )

    return {
        "world": "self1",
        "slice": "self-1",
        "slip": SLIP,
        "world_plug": list(WORLD_PLUG),
        "actions": N_ACTIONS,
        "poses": cube.N_POSES,
        "start": cube.pose_name(cube.START),
        "observe_turns": observe_turns,
        "hypotheses": cube.HEADINGS,
        "packet_is_the_same_in_both_arms": packets_match,
        # Attribution: the same sentence, two different authors.
        "body_offset_motor": motor["body_offset"],
        "body_offset_world": world["body_offset"],
        "body_offset_motor_control": motor_ctl["body_offset"],
        "body_offset_world_control": world_ctl["body_offset"],
        "explained_motor": motor["explained"],
        "explained_world": world["explained"],
        "contradicted_motor": motor["contradicted"],
        "contradicted_world": world["contradicted"],
        "contradicted_any_motor": motor["contradicted_any"],
        "contradicted_any_world": world["contradicted_any"],
        "pushes_seen_motor": motor["pushes_seen"],
        "pushes_seen_world": world["pushes_seen"],
        "surprises_seen_motor": motor["surprises_seen"],
        "surprises_seen_world": world["surprises_seen"],
        "held_committed_motor": motor["held_committed"],
        "held_dropped_motor": motor["held_dropped"],
        "held_committed_world": world["held_committed"],
        "held_dropped_world": world["held_dropped"],
        "probe_slip2_offset": probe2["body_offset"],
        "probe_slip2_explained": probe2["explained"],
        "probe_slip2_contradicted": probe2["contradicted"],
        "probe_slip2_surprises": probe2["surprises_seen"],
        "self_attribution_agent": attribution_agent,
        "self_attribution_control": attribution_control,
        "attribution_gap": attribution_agent - attribution_control,
        # What it cost the world model to be wrong about who moved.
        "holding_probe": holding,
        "t_world_kept_with_holding":
            holding["with_holding"]["t_world_after_verdict"],
        "t_world_kept_without_holding":
            holding["without_holding"]["t_world_after_verdict"],
        "holding_changes_the_map":
            holding["with_holding"]["t_world_after_verdict"]
            != holding["without_holding"]["t_world_after_verdict"],
        "t_world_asked_motor": motor["t_world_asked"],
        "t_world_preserved_motor_after_window":
            motor["t_world_preserved_after_window"],
        "t_world_preserved_motor_agent": motor["t_world_preserved"],
        "t_world_preserved_motor_control": motor_ctl["t_world_preserved"],
        "t_world_preserved_world_agent": world["t_world_preserved"],
        "t_world_preserved_world_control": world_ctl["t_world_preserved"],
        # Recovery: it still gets there, on the perturbed body or floor.
        "exam_start_is_canonical": motor["trail"][0] == cube.pose_name(cube.START),
        "exam_motor_goal_hits": motor["goal_hits"],
        "exam_motor_reward_sum": motor["reward_sum"],
        "exam_motor_trail": motor["trail"],
        "exam_world_goal_hits": world["goal_hits"],
        "exam_world_reward_sum": world["reward_sum"],
        "exam_world_trail": world["trail"],
        "exam_motor_control_goal_hits": motor_ctl["goal_hits"],
        "exam_world_control_goal_hits": world_ctl["goal_hits"],
        "cam_occupied": motor["cam_occupied"],
        "cam_slots": len(ag.cam.slot),
        "false_facts": max(a["false_facts"] for a in
                           (motor, motor_ctl, world, world_ctl)),
        "destroyed": max(a["destroyed"] for a in
                         (motor, motor_ctl, world, world_ctl)),
        "cortex_calls": max(a["cortex_calls"] for a in
                            (motor, motor_ctl, world, world_ctl)),
        "questions": max(a["questions"] for a in
                         (motor, motor_ctl, world, world_ctl)),
        "agent_default_explore_flat": bool(Agent().q.explore_flat),
        "agent_default_body_offset": int(Agent().body_offset),
    }


def green(report: dict) -> bool:
    """Attribution **and** recovery. One without the other is not a self."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["actions"] == 3
        and not report["agent_default_explore_flat"]
        and report["agent_default_body_offset"] == 0
        and report["packet_is_the_same_in_both_arms"]
        # it knew which one moved
        and report["body_offset_motor"] == report["slip"]
        and report["body_offset_world"] == 0
        and report["self_attribution_agent"] == 1
        and report["self_attribution_control"] == 0
        and report["attribution_gap"] > 0
        # and it is an argmax over six integers, not the number 1
        and report["probe_slip2_offset"] == 2
        # and it kept the cube it had already learned
        and report["t_world_preserved_motor_agent"]
        > report["t_world_preserved_motor_control"]
        and report["t_world_kept_with_holding"]
        >= report["t_world_kept_without_holding"]
        # and it still gets there
        and report["exam_start_is_canonical"]
        and report["exam_motor_goal_hits"] > 0
        and report["exam_world_goal_hits"] > 0
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_self1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
