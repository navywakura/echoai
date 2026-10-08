"""
ROOM-1 — two rooms, one map.

PULPO-C's cube, twice. The two rooms are built from the same floor, the
same goal and the same physics, and the only thing that tells them apart
is an integer that lives on the env:

    env.frame in {0, 1}      which room the body is standing in

That integer is **outside** the 16 B packet. `encode_cell` writes
`index & 0xFF` into ext.seq and nothing else, so a pose reads the same
sixteen bytes in room A and in room B. 324 places, 162 packets.

That is not an accident to be patched. CAM 4096 is not the size of the
world; it is the number of *cognitive* states, and two places that behave
the same are one cognitive state. The body walks into B already knowing
it, because knowing B is the same thing as knowing A. Compression, not a
bug — and the price of the claim is that it has to be paid in numbers:

    packets_across      162, not 324          the rooms share
    dynamic_alias       0                     and sharing costs nothing
    exam in B           collects, from the canonical START
    the same, scratch   collects less         the transfer is real
    cam_occupied_AB     no bigger than A's    two rooms, one memory

The last line is where a shared packet could have been a lie: if the
second room quietly allocated a second set of slots the body would be
paying for both rooms while claiming one.

**What a shared packet costs when the rooms are not identical.** Put the
plug of PULPO into B and leave A open. The packets are still shared —
they must be, the encoder never saw a room — but four `approach` rows
now disagree, and the body has no way to ask which room it is in. That
is DynamicAlias: same WSP, different dynamics. It is measured here and
reported as a number (`dynamic_alias_with_hole`), and it is **not**
fixed: writing the room into ext.domain would break I2, and writing it
into ext.seq would put 324 places under a 256 ceiling and destroy the
sharing this slice exists to demonstrate. The hole belongs to ROOM-2.

No portal: a door whose packet is local-only *is* an alias in that cell,
so it would smuggle in ROOM-2's problem. A→B is a teleport, as in
WORLD-3.

    PYTHONPATH=. python3 -m echoai.nexus0.room1
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.core.wsp import unpack

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    BENCH_SEED,
    N_ACTIONS,
    R_SUCCESS,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY
from echoai.nexus0 import body3d as cube

N_FRAMES = 2
FRAME_A = 0
FRAME_B = 1

# The identical pair, and the mutant that is run rather than described.
# A room is a layout of the cube; the frame is which one the body is in.
ROOMS: Tuple[str, str] = (cube.LAYOUT_OPEN, cube.LAYOUT_OPEN)
ROOMS_WITH_HOLE: Tuple[str, str] = (cube.LAYOUT_OPEN, cube.LAYOUT_BLOCK)

# 162 local poses per room, two rooms. Places, not packets: the gap
# between these two numbers is the whole of the slice.
PLACES = N_FRAMES * cube.N_POSES


class Room1Env(cube.Body3DEnv):
    """One room of the pair. The cube of PULPO with a frame on it.

    Subclass and not a copy: the physics is `Body3DEnv`'s, step for step,
    so nothing here can quietly become a second cube. `frame` is the only
    thing added, it is read by the report and by nobody in the loop, and
    it never reaches `cell()` — which returns the **local** pose, 0..161,
    exactly what `encode_cell` is given.
    """

    def __init__(self, frame: int = FRAME_A, layout: Optional[str] = None,
                 seed: int = BENCH_SEED) -> None:
        self.frame = int(frame) % N_FRAMES
        # The frame picks the room. Passing a layout is how the mutant
        # builds a pair that is not identical; the default pair is.
        super().__init__(
            layout=ROOMS[self.frame] if layout is None else layout, seed=seed
        )


def room_env(frame: int, rooms: Tuple[str, str] = ROOMS) -> Room1Env:
    return Room1Env(frame, rooms[int(frame) % N_FRAMES])


# ---------------------------------------------------------- the packets

def packet_of(index: int) -> bytes:
    """The 16 B of a local pose. No room, no frame: there is nowhere to
    put one, and this is the point rather than a limitation."""
    return encode_cell(index, cube.KINDS[index])


def packets_in(frame: int, rooms: Tuple[str, str] = ROOMS) -> set:
    """Distinct packets a body can emit in one room, over every pose."""
    env = room_env(frame, rooms)
    return {encode_cell(env.teleport(i).index, env.kind[i])
            for i in range(cube.N_POSES)}


def _by_packet() -> Dict[bytes, List[int]]:
    out: Dict[bytes, List[int]] = {}
    for i in range(cube.N_POSES):
        out.setdefault(packet_of(i), []).append(i)
    return out


def dynamic_alias(rooms: Tuple[str, str] = ROOMS,
                  standable_only: bool = True) -> List[dict]:
    """Pairs the body cannot tell apart that do not behave the same.

    Same 16 B in room A and in room B, same action, and `approach` lands
    on two different packets. This is the alias that actually hurts: not
    two names for one thing, but one name for two things whose futures
    differ, which is precisely what T cannot hold at once.

    `standable_only` keeps the count to poses the body can stand on in
    both rooms. A pose inside stone is not a place that behaves
    differently; it is not a place. The whole successor table is counted
    too, and both numbers go in the report.
    """
    groups = _by_packet()
    out: List[dict] = []
    for i in range(cube.N_POSES):
        for j in groups.get(packet_of(i), ()):
            if standable_only and not (
                cube.is_floor(*cube.pose_of(i)[:3], rooms[FRAME_A])
                and cube.is_floor(*cube.pose_of(j)[:3], rooms[FRAME_B])
            ):
                continue
            lands_a = cube.NEXT[rooms[FRAME_A]][ACTION_APPROACH][i]
            lands_b = cube.NEXT[rooms[FRAME_B]][ACTION_APPROACH][j]
            if packet_of(lands_a) != packet_of(lands_b):
                out.append({
                    "pose_in_A": cube.pose_name(i),
                    "pose_in_B": cube.pose_name(j),
                    "A_lands": cube.pose_name(lands_a),
                    "B_lands": cube.pose_name(lands_b),
                })
    return out


def ext_of(index: int) -> dict:
    return unpack(packet_of(index))["ext"]


def domain_is_zero() -> bool:
    """I2, checked over every packet this slice can emit, not asserted."""
    return all(ext_of(i)["domain"] == 0 for i in range(cube.N_POSES))


def style_is_zero() -> bool:
    """The other byte a room could have been smuggled into."""
    return all(ext_of(i)["style"] == 0 for i in range(cube.N_POSES))


def seq_is_the_local_pose() -> bool:
    """And the third: a strided index would make the rooms distinct and
    blow the ceiling at the same time."""
    return all(ext_of(i)["seq"] == i & 0xFF for i in range(cube.N_POSES))


def packet_ceiling_holds() -> bool:
    """encode_cell(0) == encode_cell(256). Measured, never raised."""
    return encode_cell(0, KIND_EMPTY) == encode_cell(
        cube.PACKET_CEILING, KIND_EMPTY
    )


# ------------------------------------------------------------ the agent

def _slot(ag, index: int) -> int:
    return ag.cam.get(packet_of(index))


def _cam_occupied(ag) -> int:
    return sum(1 for s in ag.cam.slot if s.occupied)


def t_against(ag, env: Room1Env) -> dict:
    """What T already says about this room, before a step is taken in it.

    Every pose the body can stand on: does T's `approach` row name the
    slot the room will actually hand back? For a room it has never been
    in, this is the transfer stated without money in it.
    """
    agree = 0
    asked = 0
    for index in cube.reachable(env.layout):
        slot = _slot(ag, index)
        if slot < 0:
            continue
        pred = ag.t.predict(slot, ACTION_APPROACH)
        if pred is None:
            continue
        asked += 1
        truth = cube.NEXT[env.layout][ACTION_APPROACH][index]
        agree += int(pred == _slot(ag, truth))
    return {"asked": asked, "agree": agree}


def school(ag, env: Room1Env, turn: int) -> Tuple[List[dict], int]:
    """PULPO-C's reverse curriculum, in whatever room it is handed.

    Nearest the goal first, then further out; teleporting is a training
    aid and the exam always starts at the canonical START. The distances
    are flooded over the successor table of the room the body is in, so
    no route is named here either.
    """
    by_dist = cube.poses_by_distance(env.layout)
    ag.env = env
    phases: List[dict] = []
    for d in sorted(k for k in by_dist if k > 0):
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


def exam(ag, env: Room1Env, turns: int = cube.EXAM_TURNS) -> dict:
    """Greedy, cortex off, from the canonical START of whichever room."""
    ag.env = env
    # The pose the exam actually began on, not the one it meant to: a
    # report that prints a constant here cannot fail on a start moved
    # next door to the prize.
    began = env.teleport(cube.START).index
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
        "frame": env.frame,
        "start": cube.pose_name(began),
        "goal_hits": hits,
        "reward_sum": total,
        "poses_visited": len(set(poses)),
        "trail": [cube.pose_name(p) for p in poses[:16]],
    }


def _fresh(env: Room1Env):
    from echoai.nexus0.loop import Agent
    return Agent(env=env, remainder=True, explore_flat=True)


# ------------------------------------------------------------ the slice

def experiment() -> dict:
    a_env = room_env(FRAME_A)
    ag = _fresh(a_env)

    phases, turn = school(ag, a_env, 0)
    # The turn counter is the guard on the whole claim: if a single turn
    # were taken in B before the exam, B would be collecting because it
    # was trained, not because it was transferred.
    turns_after_A = ag.metrics.turns
    cam_a = _cam_occupied(ag)
    t_in_a = t_against(ag, a_env)

    # The room it has never been in, asked before it is walked.
    b_env = room_env(FRAME_B)
    t_in_b = t_against(ag, b_env)

    # A copy sits the exam in A, so the body that walks into B is exactly
    # the body that finished the curriculum and nothing else.
    exam_a = exam(copy.deepcopy(ag), room_env(FRAME_A))

    turns_before_b_exam = ag.metrics.turns
    exam_b = exam(ag, b_env)
    cam_ab = _cam_occupied(ag)

    # Control: the same agent, never having seen A, dropped into B.
    scratch = _fresh(room_env(FRAME_B))
    t_in_b_scratch = t_against(scratch, room_env(FRAME_B))
    exam_b_scratch = exam(scratch, room_env(FRAME_B))

    # Reported, not a KPI: what B costs when it is not transferred but
    # learned. It says the transferred number is not magic — it is the
    # same number, for the price of no turns at all.
    schooled = _fresh(room_env(FRAME_B))
    _p, schooled_turns = school(schooled, room_env(FRAME_B), 0)
    exam_b_schooled = exam(schooled, room_env(FRAME_B))

    # The mutant, run. B keeps the packets and loses four `approach` rows.
    holed = dynamic_alias(ROOMS_WITH_HOLE)
    holed_table = dynamic_alias(ROOMS_WITH_HOLE, standable_only=False)
    hole_env = room_env(FRAME_B, ROOMS_WITH_HOLE)
    t_in_hole = t_against(copy.deepcopy(ag), hole_env)
    exam_hole = exam(copy.deepcopy(ag), hole_env)

    packets_a = packets_in(FRAME_A)
    packets_b = packets_in(FRAME_B)
    packets_hole = packets_in(FRAME_B, ROOMS_WITH_HOLE)
    across = packets_a | packets_b

    a_probe = room_env(FRAME_A)
    b_probe = room_env(FRAME_B)
    same_packet = all(
        encode_cell(a_probe.teleport(i).index, a_probe.kind[i])
        == encode_cell(b_probe.teleport(i).index, b_probe.kind[i])
        for i in range(cube.N_POSES)
    )

    return {
        "world": "room1",
        "slice": "room-1",
        "frames": N_FRAMES,
        "local_poses": cube.N_POSES,
        "places": PLACES,
        "rooms": list(ROOMS),
        "rooms_with_hole": list(ROOMS_WITH_HOLE),
        "actions": N_ACTIONS,
        "start": cube.pose_name(cube.START),
        # The rooms share, and the sharing is what the packet says.
        "packets_in_A": len(packets_a),
        "packets_in_B": len(packets_b),
        "packets_across": len(across),
        "packet_is_the_same_in_both_rooms": same_packet,
        "kinds_are_the_same_in_both_rooms": a_probe.kind == b_probe.kind,
        "frame_is_outside_the_packet": (a_probe.frame != b_probe.frame
                                        and same_packet),
        "domain_is_zero": domain_is_zero(),
        "style_is_zero": style_is_zero(),
        "seq_is_the_local_pose": seq_is_the_local_pose(),
        "packet_ceiling": cube.PACKET_CEILING,
        "packet_ceiling_holds": packet_ceiling_holds(),
        # And sharing costs nothing while the rooms behave alike.
        "dynamic_alias": len(dynamic_alias(ROOMS)),
        "dynamic_alias_table": len(
            dynamic_alias(ROOMS, standable_only=False)
        ),
        "dynamic_alias_pairs": dynamic_alias(ROOMS),
        # The mutant: same packets, four rows apart.
        "packets_in_B_with_hole": len(packets_hole),
        "packets_shared_with_hole": packets_hole == packets_b,
        "dynamic_alias_with_hole": len(holed),
        "dynamic_alias_with_hole_table": len(holed_table),
        "dynamic_alias_with_hole_pairs": holed_table,
        "approach_rows_that_differ_with_hole": len(cube.approach_diff()),
        "domain_is_zero_with_hole": domain_is_zero(),
        "t_agrees_in_B_with_hole": t_in_hole["agree"],
        "t_asked_in_B_with_hole": t_in_hole["asked"],
        "exam_B_with_hole_goal_hits": exam_hole["goal_hits"],
        # It knows B before it walks it.
        "t_known_in_A": t_in_a["agree"],
        "t_asked_in_A": t_in_a["asked"],
        "t_known_in_B_before_a_step": t_in_b["agree"],
        "t_asked_in_B_before_a_step": t_in_b["asked"],
        "t_known_in_B_scratch": t_in_b_scratch["agree"],
        # And it walks it.
        "curriculum": phases,
        "curriculum_turns": turn,
        "exam_turns": cube.EXAM_TURNS,
        "exam_start_is_canonical": exam_b["start"] == cube.pose_name(cube.START),
        "turns_after_A": turns_after_A,
        "turns_in_B_before_the_exam": turns_before_b_exam - turns_after_A,
        "exam_A_goal_hits": exam_a["goal_hits"],
        "exam_B_transferred_goal_hits": exam_b["goal_hits"],
        "exam_B_transferred_reward_sum": exam_b["reward_sum"],
        "exam_B_transferred_trail": exam_b["trail"],
        "exam_B_scratch_goal_hits": exam_b_scratch["goal_hits"],
        "exam_B_scratch_trail": exam_b_scratch["trail"],
        "transfer_gain": exam_b["goal_hits"] - exam_b_scratch["goal_hits"],
        "transfer_costs_no_turns": exam_b["goal_hits"] >= exam_a["goal_hits"],
        "exam_B_schooled_goal_hits": exam_b_schooled["goal_hits"],
        "exam_B_schooled_turns": schooled_turns,
        # Two rooms, one memory.
        "cam_occupied_A": cam_a,
        "cam_occupied_AB": cam_ab,
        "cam_margin": cam_a // 5,
        "cam_shared": cam_ab <= cam_a + cam_a // 5,
        "cam_slots": len(ag.cam.slot),
        "cam_occupied_scratch": _cam_occupied(scratch),
        "remainder": bool(ag.q.remainder),
        "explore_flat": bool(ag.q.explore_flat),
        "false_facts": max(a.metrics.false_facts for a in (ag, scratch)),
        "destroyed": max(a.metrics.destroyed for a in (ag, scratch)),
        "cortex_calls": max(a.metrics.cortex_calls for a in (ag, scratch)),
        "questions": max(a.metrics.questions for a in (ag, scratch)),
    }


def green(report: dict) -> bool:
    """One map, two rooms — and the hole reported rather than papered."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["actions"] == 3
        and report["frames"] == N_FRAMES
        and report["local_poses"] == cube.N_POSES
        # the rooms share a packet, and it carries no room
        and report["packets_across"] == cube.N_POSES
        and report["packets_in_A"] == cube.N_POSES
        and report["packets_in_B"] == cube.N_POSES
        and report["packet_is_the_same_in_both_rooms"]
        and report["frame_is_outside_the_packet"]
        and report["domain_is_zero"]
        and report["style_is_zero"]
        and report["seq_is_the_local_pose"]
        and report["packet_ceiling_holds"]
        # sharing costs nothing here
        and report["dynamic_alias"] == 0
        and report["dynamic_alias_table"] == 0
        # and what it costs when the rooms differ is a number, not a patch
        and report["dynamic_alias_with_hole"] > 0
        and report["packets_shared_with_hole"]
        and report["domain_is_zero_with_hole"]
        # it knew B before it walked it, and then it walked it
        and report["t_known_in_B_before_a_step"] > 0
        and report["t_known_in_B_scratch"] == 0
        and report["exam_start_is_canonical"]
        and report["exam_B_transferred_goal_hits"] > 0
        and report["turns_in_B_before_the_exam"] == 0
        and report["transfer_gain"] > 0
        # two rooms, one memory
        and report["cam_shared"]
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_room1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
