"""
OPEN-1 — a fourth gear, because there is a fourth physics.

OBJ-1's world has a glass in it. This one has a glass **with a lid on**,
and until the lid comes off the glass cannot be picked up at all. That is
the whole of the licence for a new verb: `ABRIR` exists here because there
is something in the room that only opening changes, and it exists nowhere
else. The ring, the corridor, the cube and the jar-less cube all still
have three gears, and `constants.N_ACTIONS` is still 3.

    ITEM (0,1,0)   OBJ-1's glass, now shut         DEST (1,0,0)  the table
    closed         landing on it does nothing      standing on it is legal
    ABRIR          on the closed jar, and only there
    open           OBJ-1's physics, unchanged, down to the delivery

**Closed is a place you can stand.** In OBJ-1 the body could never be on
the glass without holding it, because landing was holding. Here it can,
and that state is precisely the one that asks for the verb: a pose where
approach walks off, avoid turns, wait does nothing, and only the fourth
thing changes the world.

**And closed is a different sixteen bytes.**

    KIND_CLOSED   YO -> OBSERVAR -> CERRAR      E identical to EMPTY's
    KIND_OBJECT   YO -> OBSERVAR -> OTRO        in hand, as in OBJ-1
    seq is still `index & 0xFF`, ext.domain 0, ext.style 0

The packet says *what is being looked at*, never what to do about it, so
the rel stays OBSERVAR and `ABRIR` (atom 25) appears nowhere in it. If a
shut jar and an open one read alike, the one state where the verb pays
would be indistinguishable from the state where it is pointless, and Q
could not learn it at all.

**The fourth column is a flag, not a constant.** `QTable`, `Agent` and
`gate` all take `n_actions`, all default to the frozen three, and only
this module asks for four. Three places would otherwise have silently
turned the verb back into `approach`:

    qtable.select     `turn % 3` never offers `open` on a flat row —
                      the state that pays is the state that cannot try
    qtable.is_explore a four-wide row that ties on its first three
                      reads as settled while `open` still has a vote
    gate              `proposed % 3` sends 3 out as 0; the environment
                      would never once see the verb

Each of those makes this slice reduce to OBJ-1 while still looking green,
which is why each is a mutant below rather than a sentence here.

**Eleven, and no more.** Flooded: two actions to reach the jar, one to
open it, seven to carry it to the table, one to deliver. Eleven is exactly
`value_horizon()`; the arithmetic can still see the reward at the far end
and would not at twelve. Nothing here is tuned to make it fit — if a
longer jar did not fit, the answer would be to stop, not to move gamma.

    PYTHONPATH=. python3 -m echoai.nexus0.open1
"""

from __future__ import annotations

import copy
import inspect
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from echoai.core.wsp import unpack

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
    N_ACTIONS,
    R_SUCCESS,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_CLOSED, KIND_EMPTY, KIND_OBJECT, Cell
from echoai.nexus0 import body3d as cube
from echoai.nexus0 import obj1
from echoai.nexus0.obj1 import DEST_XYZ, ITEM_XYZ, voxel_of

# The fourth gear. Its number lives here and not in `constants`, because
# it is a property of this world and not of the agent: a body in a room
# with no lid in it has no use for a name for opening one.
ACTION_OPEN = 3
GEARS_WITH_A_LID = N_ACTIONS + 1

# The two halves of a state. SHUT is "the jar is closed and lying at
# ITEM"; the body may be standing on it. HELD is OBJ-1's carrying half.
# There is no third: opening happens only while standing on the jar, so
# an open jar on the floor is not a state this world can produce.
SHUT = 0
HELD = 1

EXAM_TURNS = cube.EXAM_TURNS


def episode_turns(d: int) -> int:
    """PULPO's budget, counted in this world's gears.

    Same shape as `body3d.episode_turns` and for the same two reasons.
    Long enough: a greedy body needs `d + 2` and an exploring one spends
    turns on the other gears, so the budget scales with the ring it is
    trying. Coprime with the number of gears: `select` cycles
    `turn % n_actions` and the counter runs through the teleports, so an
    episode that is a whole number of cycles long offers every pose the
    same action every repetition. With four gears `4d + 9` is odd, and an
    odd length can never divide a cycle of four — where PULPO's `3d + 7`
    is even for odd `d` and would have hidden two of the four gears at
    exactly the poses that need them.
    """
    return GEARS_WITH_A_LID * (int(d) + 2) + 1


# ------------------------------------------------------------ the world

class Open1Env(obj1.Obj1Env):
    """OBJ-1's room with a lid on the glass.

    A subclass and not a copy: the movement, the coupling, the delivery
    and the reset are OBJ-1's, so nothing here can quietly become a second
    set of physics. What is added is one boolean on the env and one gear
    that can change it.
    """

    def __init__(self, layout: str = cube.LAYOUT_OPEN,
                 seed: int = BENCH_SEED,
                 pays_an_empty_table: bool = False,
                 starts_open: bool = False) -> None:
        # The mutant switch: a jar that is born open is not a jar, and the
        # world is OBJ-1 again. Read by `reset`, so it survives a delivery.
        self.starts_open = bool(starts_open)
        self.lid_open = bool(starts_open)
        super().__init__(layout=layout, seed=seed,
                         pays_an_empty_table=pays_an_empty_table)

    # -- the room ---------------------------------------------------

    def _paint(self) -> None:
        """The jar's voxel, from all six headings. Shut or open, never both.

        A body standing on an open jar is holding it, so OBJECT and "in
        hand" stay the one fact they were in OBJ-1. CLOSED is the new
        thing: a place that can be stood on with empty hands.
        """
        self.kind = [KIND_EMPTY] * cube.N_POSES
        here = KIND_OBJECT if self.lid_open else KIND_CLOSED
        for h in range(cube.HEADINGS):
            self.kind[cube.index_of(*self.obj, h)] = here

    def reset(self) -> None:
        self.lid_open = bool(self.starts_open)
        super().reset()

    def teleport(self, i: int, holding: Optional[bool] = None) -> Cell:
        """Training aid. `holding=True` means the lid is off and in hand.

        The exam never passes the second argument. A teleport onto a shut
        jar leaves it shut and the hands empty, which is the state the
        curriculum needs and which OBJ-1's teleport would have coupled.
        """
        if holding is True:
            self.lid_open = True
        elif holding is False:
            self.lid_open = bool(self.starts_open)
        if not self.lid_open:
            # Shut: standing on it is standing on it, and nothing more.
            self.i = int(i) % cube.N_POSES
            self.coupled = False
            self.obj = ITEM_XYZ
            self._paint()
            return self.cell()
        return super().teleport(i, holding=holding)

    # -- the verb ---------------------------------------------------

    def opens(self, aa: int) -> bool:
        """Is this the action that takes the lid off?

        Only `ABRIR`, only on the jar's own voxel, only while it is shut.
        There is no opening at a distance and no opening of the floor: a
        verb that works everywhere is not a verb, it is a decoration.
        """
        return bool(aa == ACTION_OPEN
                    and not self.lid_open
                    and voxel_of(self.i) == self.obj)

    def step(self, a: int) -> Tuple[int, Cell]:
        aa = int(a) % GEARS_WITH_A_LID
        if aa == ACTION_OPEN:
            # Opening pays nothing. The lid is a gate on the glass, not a
            # second prize, and a verb that paid would be learned for its
            # own sake and pressed at every wall.
            if self.opens(aa):
                self.lid_open = True
                self.coupled = True   # on an open jar is holding it
                self.used_open += 1
            self.last_delivered = False
            self.last_was_an_empty_table = False
            self.bumped = False
            self._paint()
            self.last_reward = 0
            return 0, self.cell()
        if not self.lid_open:
            # Shut, and this is one of the three old gears. Movement is
            # OBJ-1's, but the glass is furniture: it does not follow and
            # walking onto it does not pick it up.
            return self._step_while_shut(aa)
        reward, cell = super().step(aa)
        if reward == R_SUCCESS:
            # Delivering puts the lid back on. OBJ-1's reset sends the body
            # home and the glass back to ITEM but knows nothing about a
            # lid, so without this the world quietly becomes OBJ-1 after
            # its first collect — every episode would train the second half
            # of its turns on a jar that is not there.
            self.lid_open = bool(self.starts_open)
            self._paint()
            cell = self.cell()
        return reward, cell

    def _step_while_shut(self, aa: int) -> Tuple[int, Cell]:
        reward = 0
        self.last_delivered = False
        self.last_was_an_empty_table = bool(
            aa == ACTION_APPROACH and voxel_of(self.i) == DEST_XYZ)
        self.bumped = bool(aa == ACTION_APPROACH
                           and cube.bumps(self.i, self.layout))
        if self.bumped:
            reward = self._payoff(aa)
        if aa == ACTION_AVOID:
            x, y, z, h = cube.pose_of(self.i)
            self.i = cube.index_of(x, y, z, (h + 1) % cube.HEADINGS)
        elif aa == ACTION_APPROACH:
            x, y, z, h = cube.pose_of(self.i)
            dx, dy, dz = cube.DIRS[h]
            ahead = (x + dx, y + dy, z + dz)
            if (cube.is_floor(x, y, z, self.layout)
                    and cube.is_floor(*ahead, self.layout)):
                self.i = cube.index_of(*ahead, h)
        self._paint()
        self.last_reward = int(reward)
        return reward, self.cell()


def fresh_env(**kw) -> Open1Env:
    env = Open1Env(**kw)
    env.used_open = 0
    return env


# Counter lives on the class so `reset` never clears it: it is the exam's
# tally of how often the verb was actually used, not part of the physics.
Open1Env.used_open = 0


# ------------------------------------------------- the abstract states

State = Tuple[int, int]


def valid_states(layout: str = cube.LAYOUT_OPEN,
                 starts_open: bool = False) -> List[State]:
    """Every (pose, jar) the physics can produce.

    With the lid on, standing on the jar is legal and empty-handed, so
    unlike OBJ-1 the item's own poses appear in **both** halves. With the
    lid already off this is OBJ-1's state space exactly, item poses
    excluded from the free half, and a test walks the two against each
    other.
    """
    out: List[State] = []
    for i in cube.reachable(layout):
        out.append((i, HELD))
        if starts_open and voxel_of(i) == ITEM_XYZ:
            continue
        out.append((i, SHUT))
    return out


def successor(state: State, a: int, layout: str = cube.LAYOUT_OPEN,
              starts_open: bool = False) -> State:
    """The arithmetic `step` runs, over a state instead of an env.

    Written once and used for the distance flood; the env above is what
    actually moves, and a test walks one against the other so they cannot
    drift apart.
    """
    i, jar = state
    if a == ACTION_OPEN:
        if jar == SHUT and voxel_of(i) == ITEM_XYZ and not starts_open:
            return (i, HELD)
        return state
    if jar == HELD:
        # OBJ-1's arithmetic, and its answer *whole*: delivering hands back
        # a body at START that is no longer carrying anything, and forcing
        # HELD on that would have the flood believe the glass is still in
        # hand on the far side of a collect.
        nxt = obj1.successor((i, obj1.HELD), a, layout, False,
                             ITEM_XYZ, DEST_XYZ)
        return (nxt[0], HELD if nxt[1] == obj1.HELD else SHUT)
    if starts_open:
        # No lid: landing on the glass is holding it, exactly as OBJ-1.
        nxt = obj1.successor((i, obj1.FREE), a, layout, False,
                             ITEM_XYZ, DEST_XYZ)
        return (nxt[0], HELD if nxt[1] == obj1.HELD else SHUT)
    x, y, z, h = cube.pose_of(i)
    if a == ACTION_AVOID:
        return (cube.index_of(x, y, z, (h + 1) % cube.HEADINGS), SHUT)
    if a == ACTION_WAIT:
        return state
    dx, dy, dz = cube.DIRS[h]
    ahead = (x + dx, y + dy, z + dz)
    if not cube.is_floor(x, y, z, layout) or not cube.is_floor(*ahead, layout):
        return state
    return (cube.index_of(*ahead, h), SHUT)


def distances(layout: str = cube.LAYOUT_OPEN,
              starts_open: bool = False) -> Dict[State, int]:
    """Actions until the body stands on the table holding the glass."""
    all_states = valid_states(layout, starts_open)
    pred: Dict[State, Set[State]] = {}
    for s in all_states:
        for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_OPEN):
            pred.setdefault(successor(s, a, layout, starts_open),
                            set()).add(s)
    return obj1._flood(pred, [
        s for s in all_states
        if voxel_of(s[0]) == DEST_XYZ and s[1] == HELD
    ])


def states_by_distance(layout: str = cube.LAYOUT_OPEN,
                       starts_open: bool = False
                       ) -> Dict[int, List[State]]:
    out: Dict[int, List[State]] = {}
    for s, d in distances(layout, starts_open).items():
        if d > 0:
            out.setdefault(d, []).append(s)
    for d in out:
        out[d].sort()
    return out


def shortest_collect(layout: str = cube.LAYOUT_OPEN,
                     starts_open: bool = False) -> Optional[int]:
    d = distances(layout, starts_open).get((cube.START, SHUT))
    return None if d is None else d + 1


def opens_needed(layout: str = cube.LAYOUT_OPEN) -> int:
    """How many times the cheapest trip has to use the verb. One."""
    dist = distances(layout)
    here: State = (cube.START, SHUT)
    used = 0
    for _ in range(64):
        if dist.get(here, 0) <= 0:
            break
        for a in (ACTION_APPROACH, ACTION_AVOID, ACTION_OPEN):
            nxt = successor(here, a)
            if nxt != here and dist.get(nxt, 10 ** 6) == dist[here] - 1:
                used += int(a == ACTION_OPEN)
                here = nxt
                break
        else:
            break
    return used


# ------------------------------------------------------------ the bytes

def ext_of(index: int, kind: int) -> dict:
    return unpack(encode_cell(index, kind))["ext"]


KINDS_HERE = (KIND_EMPTY, KIND_OBJECT, KIND_CLOSED)


def _ext_is_zero(field: str) -> bool:
    return all(ext_of(i, k)[field] == 0
               for i in range(cube.N_POSES) for k in KINDS_HERE)


def seq_is_the_local_pose() -> bool:
    return all(ext_of(i, k)["seq"] == i & 0xFF
               for i in range(cube.N_POSES) for k in KINDS_HERE)


def packets() -> Dict[str, Set[bytes]]:
    out = {}
    for name, kind in (("empty", KIND_EMPTY), ("object", KIND_OBJECT),
                       ("closed", KIND_CLOSED)):
        out[name] = {encode_cell(i, kind) for i in range(cube.N_POSES)}
    out["across"] = out["empty"] | out["object"] | out["closed"]
    return out


def packet_ceiling_holds() -> bool:
    return encode_cell(0, KIND_EMPTY) == encode_cell(
        cube.PACKET_CEILING, KIND_EMPTY)


def the_verb_is_not_in_the_packet() -> bool:
    """`ABRIR` is a gear. It must appear in no sixteen bytes this world
    emits — a packet says what is being looked at, not what to do."""
    from echoai.nexus0.encoder import ATOM_ID
    abrir = ATOM_ID["ABRIR"]
    for i in range(cube.N_POSES):
        for k in KINDS_HERE:
            p = unpack(encode_cell(i, k))
            if abrir in (p["src"], p["rel"], p["dst"], p["time"]):
                return False
    return True


# ------------------------------------------------------------ the agent

def _cam_occupied(ag) -> int:
    return sum(1 for s in ag.cam.slot if s.occupied)


def _fresh(env: Open1Env, gears: int = GEARS_WITH_A_LID):
    from echoai.nexus0.loop import Agent
    return Agent(env=env, remainder=True, explore_flat=True, n_actions=gears)


def probe_the_jar() -> dict:
    """Three questions asked of the world directly, not counted off a run.

    A shut jar that could be picked up, a verb that worked on empty floor,
    or a verb that did nothing on the jar would each turn this slice into
    something else, and none of the three shows up as a wrong number in an
    exam that simply collects less.
    """
    entry = next(
        i for i in cube.reachable(cube.LAYOUT_OPEN)
        if voxel_of(i) != ITEM_XYZ
        and voxel_of(successor((i, SHUT), ACTION_APPROACH)[0]) == ITEM_XYZ)

    env = fresh_env()
    env.teleport(entry)
    env.step(ACTION_APPROACH)
    closed_couples = env.coupled
    closed_kind = env.cell().kind
    on_the_jar = voxel_of(env.i) == ITEM_XYZ

    env.step(ACTION_OPEN)
    open_couples = env.coupled
    open_kind = env.cell().kind
    lid = env.lid_open

    away = fresh_env()
    away.teleport(cube.START)
    before = (away.lid_open, away.coupled, away.i)
    reward, _c = away.step(ACTION_OPEN)
    return {
        "reached_the_jar": on_the_jar,
        "closed_approach_does_not_couple": not closed_couples,
        "closed_reads_closed": closed_kind == KIND_CLOSED,
        "open_on_jar_couples": open_couples and lid,
        "open_reads_object": open_kind == KIND_OBJECT,
        "open_elsewhere_is_noop":
            (away.lid_open, away.coupled, away.i) == before and reward == 0,
        "opening_pays": reward,
    }


def stuck_on_the_jar(ag, turns: int = 32) -> dict:
    """Stand the agent on the shut jar and let it try, greedily.

    The control never walks to the jar at all — with three gears nothing in
    the closed half of this world leads anywhere that pays, so every row
    there stays flat and `best` answers wait. That is a true thing about
    the world and a weak thing to report, because a body that never sets
    out has not been shown to be unable to open anything. So it is carried
    to the jar and asked there, where the verb is the only thing that would
    help: whatever it does, the lid stays on.
    """
    env = fresh_env()
    env.teleport(cube.index_of(*ITEM_XYZ, 0))
    ag.env = env
    opened = False
    coupled = False
    for t in range(turns):
        ag.turn(2 * 10 ** 6 + t, greedy=True)
        opened = opened or env.lid_open
        coupled = coupled or env.coupled
    return {
        "turns": turns,
        "lid_came_off": opened,
        "picked_it_up": coupled,
        "gears": ag.n_actions,
    }


def best_q_in_the_shut_room(ag) -> int:
    """The most any policy row is worth in the closed half of the world.

    Zero means no state there leads to anything: not that the body chose
    wrongly, but that there was nothing to choose. It is the number that
    says why the control stands still instead of walking to the jar.
    """
    best = 0
    for i in cube.reachable(cube.LAYOUT_OPEN):
        for kind in (KIND_EMPTY, KIND_CLOSED):
            slot = ag.cam.get(encode_cell(i, kind))
            if slot >= 0:
                best = max(best, max(ag.q.row(slot)))
    return best


def school(ag, env: Open1Env, turn: int = 0) -> Tuple[List[dict], int]:
    """Reverse curriculum, nearest the delivery first, in three stages.

    Holding, then standing on the shut jar, then shut and elsewhere. The
    middle one is the new stage and the reason the verb is ever tried: it
    is a pose where approach walks off, avoid turns and wait does nothing,
    so the only thing that shortens the distance is the fourth gear. The
    stages are a split of one flood over one successor table; no route is
    named in any of them, and the exam always starts at the canonical
    START with the lid on.
    """
    by_dist = states_by_distance(env.layout, env.starts_open)
    ag.env = env

    def stage_of(s: State) -> str:
        if s[1] == HELD:
            return "holding"
        return "on the jar" if voxel_of(s[0]) == ITEM_XYZ else "shut"

    phases: List[dict] = []
    for stage in ("holding", "on the jar", "shut"):
        for d in sorted(by_dist):
            here = [s for s in by_dist[d] if stage_of(s) == stage]
            if not here:
                continue
            before = ag.metrics.action_pos
            opened = env.used_open
            for _rep in range(cube.TRAIN_REPS):
                for pose, half in here:
                    env.teleport(pose, holding=(half == HELD))
                    for _ in range(episode_turns(d)):
                        ag.turn(turn)
                        turn += 1
            phases.append({
                "stage": stage,
                "dist": d,
                "states": len(here),
                "collects_in_phase": ag.metrics.action_pos - before,
                "opens_in_phase": env.used_open - opened,
            })
    return phases, turn


def exam(ag, env: Open1Env, turns: int = EXAM_TURNS) -> dict:
    """Greedy, cortex off, from the canonical START with the lid on."""
    ag.env = env
    env.reset()
    env.used_open = 0
    began = env.teleport(cube.START).index
    lid_at_the_start = env.lid_open
    total = 0
    hits = 0
    object_hits = 0
    stood_on_the_jar = False
    stood_on_dest = False
    poses: List[int] = []
    for t in range(turns):
        poses.append(env.cell().index)
        stood_on_the_jar = stood_on_the_jar or voxel_of(env.i) == ITEM_XYZ
        stood_on_dest = stood_on_dest or voxel_of(env.i) == DEST_XYZ
        ag.turn(10 ** 6 + t, greedy=True)
        r = int(env.last_reward)
        total += r
        hits += int(r == R_SUCCESS)
        object_hits += int(env.last_delivered)
    return {
        "start": cube.pose_name(began),
        "lid_started_closed": not lid_at_the_start,
        "turns": turns,
        "collects": hits,
        "object_hits": object_hits,
        "collections_are_object_at_Y": object_hits == hits,
        "used_open": env.used_open,
        "reward_sum": total,
        "stood_on_the_jar": stood_on_the_jar,
        "stood_on_dest": stood_on_dest,
        "poses_visited": len(set(poses)),
        "trail": [cube.pose_name(p) for p in poses[:16]],
    }


# ------------------------------------------------------------ the slice

def _control() -> dict:
    """The same room and the same schedule, with three gears.

    It has no verb for the lid, so nothing it can do to the jar changes
    the jar. Run, not described.
    """
    env = fresh_env()
    ag = _fresh(env, gears=N_ACTIONS)
    phases, turn = school(ag, env)
    sat = exam(copy.deepcopy(ag), fresh_env())
    sat["n_actions"] = ag.n_actions
    sat["q_width"] = len(ag.q.row(0))
    sat["train_turns"] = turn
    sat["phases"] = len(phases)
    sat["best_q_in_the_shut_room"] = best_q_in_the_shut_room(ag)
    sat["stuck"] = stuck_on_the_jar(copy.deepcopy(ag))
    return sat


def _mutant() -> dict:
    """A jar born open is not a jar. Three gears, and it collects — which
    is the proof that the fourth one is buying the lid and not the walk."""
    env = fresh_env(starts_open=True)
    ag = _fresh(env, gears=N_ACTIONS)
    _phases, turn = school(ag, env)
    sat = exam(copy.deepcopy(ag), fresh_env(starts_open=True))
    sat["n_actions"] = ag.n_actions
    sat["train_turns"] = turn
    return sat


def experiment() -> dict:
    from echoai.nexus0.loop import Agent

    env = fresh_env()
    ag = _fresh(env)
    phases, turn = school(ag, env)

    sat = exam(ag, fresh_env())
    control = _control()
    mutant = _mutant()
    probe = probe_the_jar()
    pkt = packets()
    trip = shortest_collect()

    return {
        "world": "open1",
        "slice": "open-1",
        "item": list(ITEM_XYZ),
        "dest": list(DEST_XYZ),
        "start": cube.pose_name(cube.START),
        "layout": env.layout,
        # Three gears everywhere else, four here, and the constant is 3.
        "actions_default": N_ACTIONS,
        "actions_this_world": GEARS_WITH_A_LID,
        "default_agent_q_width": len(Agent().q.row(0)),
        "this_agent_q_width": len(ag.q.row(0)),
        "lid_starts_closed": not env.starts_open,
        # The bytes.
        "domain_is_zero": _ext_is_zero("domain"),
        "style_is_zero": _ext_is_zero("style"),
        "seq_is_the_local_pose": seq_is_the_local_pose(),
        "packet_ceiling": cube.PACKET_CEILING,
        "packet_ceiling_holds": packet_ceiling_holds(),
        "the_verb_is_not_in_the_packet": the_verb_is_not_in_the_packet(),
        "packets_empty": len(pkt["empty"]),
        "packets_object": len(pkt["object"]),
        "packets_closed": len(pkt["closed"]),
        "packets_across": len(pkt["across"]),
        "index_max": obj1.index_max(),
        "states": len(valid_states()),
        # The geometry, flooded and not drawn.
        "shortest_collect": trip,
        "shortest_collect_without_the_lid": shortest_collect(
            starts_open=True),
        "opens_on_the_cheapest_trip": opens_needed(),
        "value_horizon": cube.value_horizon(),
        "collect_fits_the_horizon": trip is not None
        and trip <= cube.value_horizon(),
        # The world, asked directly.
        "probe_closed_approach_does_not_couple":
            probe["closed_approach_does_not_couple"],
        "probe_closed_reads_closed": probe["closed_reads_closed"],
        "probe_open_on_jar_couples": probe["open_on_jar_couples"],
        "probe_open_reads_object": probe["open_reads_object"],
        "probe_open_elsewhere_is_noop": probe["open_elsewhere_is_noop"],
        "probe_opening_pays": probe["opening_pays"],
        # The school and the exam.
        "curriculum": phases,
        "curriculum_turns": turn,
        "episode_turns_is_odd": episode_turns(1) % 2 == 1,
        "exam_turns": EXAM_TURNS,
        "exam_start": sat["start"],
        "exam_start_is_canonical": sat["start"] == cube.pose_name(cube.START),
        "exam_lid_started_closed": sat["lid_started_closed"],
        "exam_collects": sat["collects"],
        "exam_object_hits": sat["object_hits"],
        "exam_used_open": sat["used_open"],
        "exam_collections_are_object_at_Y":
            sat["collections_are_object_at_Y"],
        "exam_reward_sum": sat["reward_sum"],
        "exam_poses_visited": sat["poses_visited"],
        "exam_trail": sat["trail"],
        # The control: same jar, three gears.
        "control_n_actions": control["n_actions"],
        "control_q_width": control["q_width"],
        "control_train_turns": control["train_turns"],
        "control_object_hits": control["object_hits"],
        "control_used_open": control["used_open"],
        "control_went_to_the_jar": control["stood_on_the_jar"],
        # It does not: with three gears the closed half of this world has
        # nothing in it that leads anywhere, so every row there is flat and
        # `best` answers wait. Reported as it comes, and then the question
        # is asked where it can actually be answered — on the jar itself.
        "control_best_q_in_the_shut_room": control["best_q_in_the_shut_room"],
        "control_on_the_jar_turns": control["stuck"]["turns"],
        "control_on_the_jar_opened_it": control["stuck"]["lid_came_off"],
        "control_on_the_jar_picked_it_up": control["stuck"]["picked_it_up"],
        "control_trail": control["trail"],
        # The mutant: no lid, three gears.
        "mutant_n_actions": mutant["n_actions"],
        "mutant_already_open_object_hits": mutant["object_hits"],
        "mutant_already_open_used_open": mutant["used_open"],
        "mutant_trail": mutant["trail"],
        "cam_occupied": _cam_occupied(ag),
        "cam_slots": len(ag.cam.slot),
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
        "cortex_calls": ag.metrics.cortex_calls,
        "questions": ag.metrics.questions,
    }


def green(report: dict) -> bool:
    """A verb, because there is a lid. And the lid is what it buys."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["actions_default"] == 3
        and report["default_agent_q_width"] == 3
        and report["actions_this_world"] == 4
        and report["this_agent_q_width"] == 4
        and report["lid_starts_closed"]
        and report["domain_is_zero"]
        and report["style_is_zero"]
        and report["seq_is_the_local_pose"]
        and report["packet_ceiling_holds"]
        and report["the_verb_is_not_in_the_packet"]
        and report["index_max"] == cube.N_POSES - 1
        and report["collect_fits_the_horizon"]
        and report["opens_on_the_cheapest_trip"] == 1
        and report["exam_start_is_canonical"]
        and report["exam_lid_started_closed"]
        and report["exam_object_hits"] > 0
        and report["exam_used_open"] > 0
        and report["exam_collections_are_object_at_Y"]
        and report["probe_closed_approach_does_not_couple"]
        and report["probe_open_on_jar_couples"]
        and report["probe_open_elsewhere_is_noop"]
        and report["probe_opening_pays"] == 0
        and report["control_n_actions"] == 3
        and report["control_object_hits"] == 0
        and report["control_used_open"] == 0
        and not report["control_on_the_jar_opened_it"]
        and not report["control_on_the_jar_picked_it_up"]
        and report["mutant_n_actions"] == 3
        and report["mutant_already_open_object_hits"] > 0
        and report["mutant_already_open_used_open"] == 0
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_open1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
