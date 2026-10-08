"""
OBJ-1 — the world has things in it, not only a me.

PULPO's cube pays when *the body* stands on (2,2,1). This slice pays when
*the thing* does. Same 3x3x3 open cube, same START, same three actions,
same integers, cortex still off. What is new is that one voxel of the room
is an item, and that the item can be somewhere else than where it started.

The table is **not** PULPO's goal voxel, and that is the whole difference
between a slice that closes and one that does not. See the last section.

    ITEM   (0,1,0)     it begins here, one step up the long arm
    DEST   (1,0,0)     the table, one step up the short arm
    collect            approach, standing on the table, with the item there

**Carrying is physics, not a flag.** `approach` that lands on the item's
voxel couples; while coupled the item is wherever the body is; there is no
fourth gear to pick up with and no `carrying` bit anywhere in the sixteen
bytes. `UNIR` is still approach.

**And carrying is visible.** The fast loop reads one thing: the packet of
the cell it is standing on. If a body with the glass and a body without it
emitted the same packet, Q would average two futures into one row and the
whole slice would be theatre. So the item is a `kind` — `KIND_OBJECT`,
`YO -> OBSERVAR -> OTRO` — painted on the voxel the item is in *now*.
Standing on that voxel is the same event as holding it, because landing
there is what coupling is, so "OBJECT here" and "coupled" are one fact
seen from two sides rather than two facts to keep in step.

    162 poses x EMPTY  +  162 poses x OBJECT  =  324 packets, CAM 4096
    ext.seq is still `index & 0xFF`, ext.domain 0, ext.style 0

The table is **not** painted `KIND_GOAL`. That is the mutant, and it is run
below rather than described: a cube where standing on the table pays is
PULPO again, and a body schooled on it walks to the table and leaves the
glass where it lies.

**Do not call `Body3DEnv.step`.** In PULPO's successor table `approach` on
the goal teleports the body home, and reusing it would collect for arriving
rather than for delivering. `step`, `_payoff` and `reset` here are this
module's own; `DIRS`, `bumps`, `is_floor`, `pose_of` and `index_of` are the
cube's and are imported, not copied.

**Why the item and the table are where they are.** The control has to be
able to fail: a body paid for `agent_at_Y` must be able to sit at the table
with empty hands. It cannot if the item lies on the cheapest way there,
because then it couples on the way whether it cares or not — that is what
happened with the table nailed to PULPO's goal, where every placement of
the item was either free or twelve actions away, and twelve is past the
horizon. Moving the *table* is what buys the control back; the cube, the
floor, gamma and the horizon are all untouched.

    the two arms meet only at START
    DEST (1,0,0)   one approach from START      cost_to_dest_alone  1
    ITEM (0,1,0)   one turn and one approach    shortest_collect   10  <= 11

Both numbers are flooded over the successor table below, never drawn. The
item is on the other arm, so a body that only wants the table walks one
step and is there, and a body that overshoots the table carries on down
the short arm — away from the glass, not towards it.

`cost_to_dest_alone` floods with **this module's** arithmetic and not with
`cube.distances`: PULPO's flood runs to PULPO's goal, which is no longer
the table, and it would have agreed only by the accident of the two having
once been the same voxel.

    PYTHONPATH=. python3 -m echoai.nexus0.obj1
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
    R_THREAT,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_OBJECT, Cell, _reward
from echoai.nexus0 import body3d as cube

ITEM_XYZ: Tuple[int, int, int] = (0, 1, 0)
DEST_XYZ: Tuple[int, int, int] = (1, 0, 0)

# The two halves of a state, as integers. FREE means the item is lying at
# ITEM_XYZ; HELD means it is wherever the body is. There is no third case:
# there is no putting down.
FREE = 0
HELD = 1

EXAM_TURNS = cube.EXAM_TURNS


def voxel_of(index: int) -> Tuple[int, int, int]:
    return cube.pose_of(index)[:3]


# ------------------------------------------------------------ the world

class Obj1Env:
    """A body, a cube, and one thing in it.

    Same contract the ring gives `Agent`: `cell()`, `step()`, `reset()`,
    `teleport()`, `reveal()`, and a `kind` list the loop can index. The
    physics is written here because PULPO's is not this physics.
    """

    def __init__(self, layout: str = cube.LAYOUT_OPEN,
                 seed: int = BENCH_SEED,
                 pays_an_empty_table: bool = False) -> None:
        if layout not in cube.LAYOUTS:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        # The mutant switch, off by default: when it is on the table pays
        # for a body standing on it and never asks about the item.
        self.pays_an_empty_table = bool(pays_an_empty_table)
        self.hidden_bit = True
        self.i = cube.START
        self.obj: Tuple[int, int, int] = ITEM_XYZ
        self.coupled = False
        self.kind: List[int] = [KIND_EMPTY] * cube.N_POSES
        self.last_reward = 0
        self.bumped = False
        # Report-only bookkeeping, written by `step` and read by nothing in
        # the fast loop. `Agent` never looks at an env attribute that is
        # not `kind`, and these exist so the exam can say what happened
        # without re-deriving it from a trail.
        self.last_delivered = False
        self.last_was_an_empty_table = False
        self.reset()

    # -- the room ---------------------------------------------------

    def _paint(self) -> None:
        """One kind list, rebuilt from where the item is. Six headings of
        the item's voxel read OBJECT; everything else reads EMPTY.

        The table is not painted. A body that arrives with nothing sees the
        same sixteen bytes it saw in the corridor, which is the point.
        """
        self.kind = [KIND_EMPTY] * cube.N_POSES
        for h in range(cube.HEADINGS):
            self.kind[cube.index_of(*self.obj, h)] = KIND_OBJECT

    def reset(self) -> None:
        self.i = cube.START
        self.obj = ITEM_XYZ
        self.coupled = False
        self.last_reward = 0
        self.bumped = False
        self.last_delivered = False
        self.last_was_an_empty_table = False
        self._paint()

    def cell(self) -> Cell:
        x, y, z, h = cube.pose_of(self.i)
        return Cell(index=self.i, kind=self.kind[self.i],
                    x=x, y=y, z=z, heading=h)

    def teleport(self, i: int, holding: Optional[bool] = None) -> Cell:
        """Training aid, exactly as in PULPO. The exam never uses the
        second argument, and the first is always the canonical START.

        `holding=True` puts the item in the body's own voxel, which is what
        being coupled means. Landing on the item couples, so a teleport
        onto the item's voxel couples too — otherwise the curriculum could
        stand in a place the physics cannot produce.
        """
        self.i = int(i) % cube.N_POSES
        if holding is True:
            self.coupled = True
            self.obj = voxel_of(self.i)
        elif holding is False:
            self.coupled = False
            self.obj = ITEM_XYZ
        if not self.coupled and voxel_of(self.i) == self.obj:
            self.coupled = True
        self._paint()
        return self.cell()

    # -- the payoff -------------------------------------------------

    def delivers(self, aa: int) -> bool:
        """Is this the action that collects? `object_at_Y`, not `agent_at_Y`.

        Asked before anything moves, as in PULPO. With the mutant switch on
        the second half of the question is not asked at all.
        """
        if aa != ACTION_APPROACH or voxel_of(self.i) != DEST_XYZ:
            return False
        return self.pays_an_empty_table or self.obj == DEST_XYZ

    def _payoff(self, aa: int) -> int:
        if aa == ACTION_APPROACH:
            if self.delivers(aa):
                return R_SUCCESS
            if cube.bumps(self.i, self.layout):
                return R_THREAT
        # An item is a thing, not a prize: OBJECT pays what EMPTY pays.
        return _reward(self.kind[self.i], aa, self.hidden_bit)

    # -- the step ---------------------------------------------------

    def step(self, a: int) -> Tuple[int, Cell]:
        aa = int(a) % N_ACTIONS
        r = self._payoff(aa)
        collected = self.delivers(aa)
        self.last_delivered = bool(collected and self.obj == DEST_XYZ)
        self.last_was_an_empty_table = bool(
            aa == ACTION_APPROACH
            and voxel_of(self.i) == DEST_XYZ
            and self.obj != DEST_XYZ
        )
        self.bumped = bool(
            aa == ACTION_APPROACH
            and not collected
            and cube.bumps(self.i, self.layout)
        )
        if collected:
            # Home, and the item back where it lay. No putting down: this
            # is the only place coupling ends.
            self.i = cube.START
            self.obj = ITEM_XYZ
            self.coupled = False
        elif aa == ACTION_AVOID:
            x, y, z, h = cube.pose_of(self.i)
            self.i = cube.index_of(x, y, z, (h + 1) % cube.HEADINGS)
        elif aa == ACTION_APPROACH:
            x, y, z, h = cube.pose_of(self.i)
            dx, dy, dz = cube.DIRS[h]
            ahead = (x + dx, y + dy, z + dz)
            if (cube.is_floor(x, y, z, self.layout)
                    and cube.is_floor(*ahead, self.layout)):
                self.i = cube.index_of(*ahead, h)
                if self.coupled:
                    self.obj = ahead
                elif ahead == self.obj:
                    self.coupled = True
        self._paint()
        self.last_reward = int(r)
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing to reveal here. Part of the contract, and honest."""
        return False


# ------------------------------------------------- the abstract states

State = Tuple[int, int]


def valid_states(layout: str = cube.LAYOUT_OPEN,
                 item: Tuple[int, int, int] = ITEM_XYZ) -> List[State]:
    """Every (pose, item) the physics can actually produce.

    A pose on the item's voxel with the item still lying there is not one
    of them: landing there couples, and so does teleporting there, so the
    body is never standing on the glass without holding it. That matters —
    if it were reachable it would emit an OBJECT packet while free, and
    OBJECT would stop meaning "in hand".
    """
    out: List[State] = []
    for i in cube.reachable(layout):
        out.append((i, HELD))
        if voxel_of(i) != item:
            out.append((i, FREE))
    return out


def successor(state: State, a: int, layout: str = cube.LAYOUT_OPEN,
              pays_an_empty_table: bool = False,
              item: Tuple[int, int, int] = ITEM_XYZ,
              dest: Tuple[int, int, int] = DEST_XYZ) -> State:
    """The same arithmetic `step` runs, over a state instead of an env.

    Written once here and used for the distance flood; the env above is
    what actually moves. A test walks one against the other so they cannot
    drift apart.
    """
    i, held = state
    x, y, z, h = cube.pose_of(i)
    if a == ACTION_APPROACH and (x, y, z) == dest and (
            pays_an_empty_table or held == HELD):
        return (cube.START, FREE)
    if a == ACTION_AVOID:
        return (cube.index_of(x, y, z, (h + 1) % cube.HEADINGS), held)
    if a == ACTION_WAIT:
        return state
    dx, dy, dz = cube.DIRS[h]
    ahead = (x + dx, y + dy, z + dz)
    if not cube.is_floor(x, y, z, layout) or not cube.is_floor(*ahead, layout):
        return state
    return (cube.index_of(*ahead, h),
            HELD if (held == HELD or ahead == item) else FREE)


def _flood(pred: Dict[State, Set[State]],
           targets: List[State]) -> Dict[State, int]:
    """Breadth first, backwards over a predecessor map. The one BFS here."""
    dist: Dict[State, int] = {t: 0 for t in targets}
    edge = list(dist)
    while edge:
        nxt: List[State] = []
        for here in edge:
            for prev in pred.get(here, ()):
                if prev not in dist and prev != here:
                    dist[prev] = dist[here] + 1
                    nxt.append(prev)
        edge = nxt
    return dist


def distances(layout: str = cube.LAYOUT_OPEN,
              pays_an_empty_table: bool = False,
              item: Tuple[int, int, int] = ITEM_XYZ,
              dest: Tuple[int, int, int] = DEST_XYZ) -> Dict[State, int]:
    """Actions until the body is standing where the collect happens.

    Flooded backwards over the successor table, exactly as PULPO floods its
    poses, so nothing here names a route. Zero is "the collecting approach
    is available now", so the trip costs `dist + 1`.
    """
    all_states = valid_states(layout, item)
    pred: Dict[State, Set[State]] = {}
    for s in all_states:
        for a in (ACTION_APPROACH, ACTION_AVOID):
            pred.setdefault(
                successor(s, a, layout, pays_an_empty_table, item, dest),
                set()
            ).add(s)
    return _flood(pred, [
        s for s in all_states
        if voxel_of(s[0]) == dest and (pays_an_empty_table or s[1] == HELD)
    ])


def states_by_distance(layout: str = cube.LAYOUT_OPEN,
                       pays_an_empty_table: bool = False
                       ) -> Dict[int, List[State]]:
    out: Dict[int, List[State]] = {}
    for s, d in distances(layout, pays_an_empty_table).items():
        if d > 0:
            out.setdefault(d, []).append(s)
    for d in out:
        out[d].sort()
    return out


def shortest_collect(layout: str = cube.LAYOUT_OPEN,
                     item: Tuple[int, int, int] = ITEM_XYZ,
                     dest: Tuple[int, int, int] = DEST_XYZ) -> Optional[int]:
    d = distances(layout, item=item, dest=dest).get((cube.START, FREE))
    return None if d is None else d + 1


# A voxel off the cube. Nothing can be standing on it and no step can land
# there, so a flood run with the item here is a flood of a room with no
# glass in it. Used only to price the table against itself.
NO_ITEM: Tuple[int, int, int] = (-1, -1, -1)


def dest_distances(layout: str = cube.LAYOUT_OPEN,
                   item: Tuple[int, int, int] = ITEM_XYZ,
                   dest: Tuple[int, int, int] = DEST_XYZ
                   ) -> Dict[State, int]:
    """Actions until the body is *standing* on the table with empty hands.

    Not `cube.distances`. PULPO floods to PULPO's goal, and that is not
    this table any more; while the two happened to be the same voxel the
    two numbers agreed by accident, and an accident that stops holding the
    day a constant moves is not a measurement.

    Flooded over the half of the state space where the hands are empty, so
    a step that lands on the glass leaves the graph instead of counting as
    progress. That is exactly what "alone" has to mean here: the price of
    the table to a body that does not pick anything up.
    """
    free = [s for s in valid_states(layout, item) if s[1] == FREE]
    pred: Dict[State, Set[State]] = {}
    for s in free:
        for a in (ACTION_APPROACH, ACTION_AVOID):
            nxt = successor(s, a, layout, False, item, dest)
            if nxt[1] == FREE:
                pred.setdefault(nxt, set()).add(s)
    return _flood(pred, [s for s in free if voxel_of(s[0]) == dest])


def cost_to_dest_alone(layout: str = cube.LAYOUT_OPEN,
                       item: Tuple[int, int, int] = ITEM_XYZ,
                       dest: Tuple[int, int, int] = DEST_XYZ
                       ) -> Optional[int]:
    """The table, empty-handed, from the canonical START."""
    return dest_distances(layout, item, dest).get((cube.START, FREE))


def item_on_cheapest_dest_path(layout: str = cube.LAYOUT_OPEN,
                               item: Tuple[int, int, int] = ITEM_XYZ,
                               dest: Tuple[int, int, int] = DEST_XYZ
                               ) -> bool:
    """Does going to the table cost more when the glass may not be touched?

    The same flood twice: once with the glass where it lies, once with the
    room empty. If the two prices differ, every cheapest way to the table
    runs over the item and no control can arrive without it — which is the
    whole reason this slice's table is not PULPO's goal voxel.
    """
    alone = cost_to_dest_alone(layout, item, dest)
    empty = cost_to_dest_alone(layout, NO_ITEM, dest)
    if alone is None:
        return empty is not None
    return empty is not None and alone > empty


def placements(layout: str = cube.LAYOUT_OPEN) -> List[dict]:
    """Every (item, table) pair the open floor allows, priced.

    `detour` is what fetching costs over simply arriving: the trip with the
    glass, minus the collecting approach, minus the empty-handed price of
    the table. Zero means the glass is free — it lies on the way a body
    that does not care about it would have walked anyway, and no control
    can then tell the two bodies apart by where they went.

    The first draft of this swept the item with the **table frozen** on
    PULPO's goal voxel, and reported that no placement worked. That was
    true of that table and false of this cube: with the table free to move
    as well there are eighteen pairs that fit the horizon and still cost a
    detour. A sweep that holds one of two variables still is not a sweep.

    Flooded, not drawn.
    """
    horizon = cube.value_horizon()
    floor = sorted(cube.floor_of(layout))
    out: List[dict] = []
    for v in floor:
        for d in floor:
            if v == d or v == cube.START_XYZ or d == cube.START_XYZ:
                continue
            trip = shortest_collect(layout, item=v, dest=d)
            alone = cost_to_dest_alone(layout, item=v, dest=d)
            if trip is None or alone is None:
                continue
            out.append({
                "item": list(v),
                "dest": list(d),
                "collect": trip,
                "alone": alone,
                "detour": (trip - 1) - alone,
                "fits_the_horizon": trip <= horizon,
                "item_on_cheapest_dest_path":
                    item_on_cheapest_dest_path(layout, v, d),
            })
    return out


# ------------------------------------------------------------ the bytes

def packet_of(index: int, kind: int) -> bytes:
    return encode_cell(index, kind)


def packets() -> Dict[str, Set[bytes]]:
    empty = {packet_of(i, KIND_EMPTY) for i in range(cube.N_POSES)}
    thing = {packet_of(i, KIND_OBJECT) for i in range(cube.N_POSES)}
    return {"empty": empty, "object": thing, "across": empty | thing}


def ext_of(index: int, kind: int) -> dict:
    return unpack(packet_of(index, kind))["ext"]


def _ext_is_zero(field: str) -> bool:
    return all(
        ext_of(i, k)[field] == 0
        for i in range(cube.N_POSES)
        for k in (KIND_EMPTY, KIND_OBJECT)
    )


def seq_is_the_local_pose() -> bool:
    return all(
        ext_of(i, k)["seq"] == i & 0xFF
        for i in range(cube.N_POSES)
        for k in (KIND_EMPTY, KIND_OBJECT)
    )


def coupled_is_env_not_wsp() -> bool:
    """Holding lives on the world, and the sixteen bytes cannot see it.

    Derived, not asserted. `packet_of` takes a pose and a kind and has no
    third argument to hand it an env; `coupled` is an attribute of the env
    and of nothing else; and the three ext fields a hand could have been
    smuggled into read the same as they did before this slice existed. Add
    an env parameter to the encoder path, or write a bit into style, and
    this goes red.
    """
    return bool(
        list(inspect.signature(packet_of).parameters) == ["index", "kind"]
        and hasattr(Obj1Env(), "coupled")
        and "coupled" not in inspect.getsource(packet_of)
        and _ext_is_zero("domain")
        and _ext_is_zero("style")
        and seq_is_the_local_pose()
    )


def packet_ceiling_holds() -> bool:
    """encode_cell(0) == encode_cell(256). Measured, never raised."""
    return packet_of(0, KIND_EMPTY) == packet_of(
        cube.PACKET_CEILING, KIND_EMPTY
    )


def no_pose_is_ever_a_goal() -> bool:
    """The table is a place, not a prize.

    Asked of every voxel the item can be in, not of the table alone: if a
    single kind list anywhere in this world painted a goal, `_reward` would
    pay for standing rather than for delivering, and the slice would be
    PULPO with a longer docstring.
    """
    env = Obj1Env()
    for v in cube.FLOOR:
        env.obj = v
        env._paint()
        if any(k not in (KIND_EMPTY, KIND_OBJECT) for k in env.kind):
            return False
    return True


def index_max() -> int:
    """The largest index the body ever hands the encoder. 161, not 162*27:
    the item is a kind on a voxel, never a factor in the address."""
    env = Obj1Env()
    seen = -1
    for i in range(cube.N_POSES):
        seen = max(seen, env.teleport(i).index)
    return seen


# ------------------------------------------------------------ the agent

def probe_the_table(pays_an_empty_table: bool = False) -> dict:
    """Stand on the table and approach — once with the item, once without.

    The exam never produces the second turn: a body that fetches is holding
    the glass by the time it arrives, so `agent_at_Y_without_object` sums a
    reward over zero turns and prints 0 because nothing happened. A field
    that cannot disagree with itself is not a KPI. So the question is asked
    directly, from every heading, and the answer is a number the env had to
    produce.

    Nothing here is training and nothing here is greedy: it is two calls to
    `step` on a fresh world.
    """
    empty_reward = 0
    empty_collects = 0
    full_reward = 0
    item_moved = False
    sent_home = 0
    for h in range(cube.HEADINGS):
        env = Obj1Env(pays_an_empty_table=pays_an_empty_table)
        env.teleport(cube.index_of(*DEST_XYZ, h), holding=False)
        before = env.obj
        r, _c = env.step(ACTION_APPROACH)
        empty_reward += int(r)
        empty_collects += int(r == R_SUCCESS)
        item_moved = item_moved or env.obj != before

        env = Obj1Env(pays_an_empty_table=pays_an_empty_table)
        env.teleport(cube.index_of(*DEST_XYZ, h), holding=True)
        r, _c = env.step(ACTION_APPROACH)
        full_reward += int(r)
        sent_home += int(env.i == cube.START and env.obj == ITEM_XYZ
                         and not env.coupled)
    return {
        "headings": cube.HEADINGS,
        # Not zero: four of the six headings face a wall from the table,
        # and walking into stone costs R_THREAT here exactly as it does in
        # PULPO. What must be zero is the other number — how many of the
        # six paid for arriving.
        "empty_table_reward_sum": empty_reward,
        "empty_table_collects": empty_collects,
        "full_table_reward_sum": full_reward,
        "the_item_stayed_put": not item_moved,
        "delivering_sends_the_body_home": sent_home,
    }


def _slot(ag, env: Obj1Env, index: int) -> int:
    return ag.cam.get(packet_of(index, env.kind[index]))


def _cam_occupied(ag) -> int:
    return sum(1 for s in ag.cam.slot if s.occupied)


def values_an_empty_table(ag) -> int:
    """What the policy thinks `approach` is worth on the table, holding
    nothing, in the packet the real world emits there.

    This cube cannot separate the two bodies by behaviour — the item lies
    on the only corridor the value horizon can afford, so both walk the
    same eight actions. It can separate them here: a body paid for
    arriving has learned that an empty table is worth something, and a
    body paid for delivering has not. Q, not a trail.
    """
    return max(
        ag.q.get(ag.cam.get(packet_of(cube.index_of(*DEST_XYZ, h),
                                      KIND_EMPTY)), ACTION_APPROACH)
        for h in range(cube.HEADINGS)
    )


def _fresh(env: Obj1Env):
    from echoai.nexus0.loop import Agent
    return Agent(env=env, remainder=True, explore_flat=True)


def school(ag, env: Obj1Env, turn: int = 0) -> Tuple[List[dict], int]:
    """Reverse curriculum in two stages, nearest the collect first.

    Stage one is the body already holding the item: the item follows, so
    the distance is the pose's own distance to the table plus the approach
    that delivers. Stage two is the body with empty hands and the item lying
    where it lies. Both are the same flood over the same successor table,
    split by which half of the state they are in — no route is named in
    either, and the exam below always starts at the canonical START with
    the item at ITEM_XYZ.
    """
    by_dist = states_by_distance(env.layout, env.pays_an_empty_table)
    ag.env = env
    phases: List[dict] = []
    for stage, held in (("holding", HELD), ("alone", FREE)):
        for d in sorted(by_dist):
            here = [s for s in by_dist[d] if s[1] == held]
            if not here:
                continue
            before = ag.metrics.action_pos
            for _rep in range(cube.TRAIN_REPS):
                for pose, _h in here:
                    env.teleport(pose, holding=(held == HELD))
                    for _ in range(cube.episode_turns(d)):
                        ag.turn(turn)
                        turn += 1
            phases.append({
                "stage": stage,
                "dist": d,
                "states": len(here),
                "collects_in_phase": ag.metrics.action_pos - before,
            })
    return phases, turn


def exam(ag, env: Obj1Env, turns: int = EXAM_TURNS) -> dict:
    """Greedy, cortex off, from the canonical START with the item at rest.

    Every number the report quotes about a collect is taken from the env at
    the turn it happened, not reconstructed afterwards: `object_hits` counts
    the collects where the item was on the table, and the empty-table sum is
    what a body standing there with nothing was actually paid.
    """
    ag.env = env
    env.reset()
    began = env.teleport(cube.START).index
    item_began = env.obj
    total = 0
    hits = 0
    object_hits = 0
    empty_table_reward = 0
    empty_table_tries = 0
    stood_on_dest = False
    held_turns = 0
    poses: List[int] = []
    for t in range(turns):
        poses.append(env.cell().index)
        stood_on_dest = stood_on_dest or voxel_of(env.i) == DEST_XYZ
        held_turns += int(env.coupled)
        ag.turn(10 ** 6 + t, greedy=True)
        r = int(env.last_reward)
        total += r
        hits += int(r == R_SUCCESS)
        object_hits += int(env.last_delivered)
        if env.last_was_an_empty_table:
            empty_table_tries += 1
            empty_table_reward += r
    return {
        "start": cube.pose_name(began),
        "item_start": list(item_began),
        "turns": turns,
        "collects": hits,
        "object_hits": object_hits,
        "collections_are_object_at_Y": object_hits == hits,
        "agent_at_Y_without_object_tries": empty_table_tries,
        "agent_at_Y_without_object_reward_sum": empty_table_reward,
        "reward_sum": total,
        "stood_on_dest": stood_on_dest,
        "turns_holding_the_item": held_turns,
        "poses_visited": len(set(poses)),
        "trail": [cube.pose_name(p) for p in poses[:16]],
    }


# ------------------------------------------------------------ the slice

def _control_and_mutant() -> Tuple[dict, dict]:
    """One schooling on a cube that pays for arriving, two exams.

    The control sits the real exam: a body paid for `agent_at_Y` is asked
    to deliver. The mutant sits its own: the cube that pays an empty table,
    to show what that cube's collects are made of. Both are run every time,
    neither is described.
    """
    mutant_env = Obj1Env(pays_an_empty_table=True)
    ag = _fresh(mutant_env)
    phases, turn = school(ag, mutant_env)
    control = exam(copy.deepcopy(ag), Obj1Env())
    mutant = exam(copy.deepcopy(ag), Obj1Env(pays_an_empty_table=True))
    control["train_turns"] = turn
    control["phases"] = len(phases)
    control["values_an_empty_table"] = values_an_empty_table(ag)
    return control, mutant


def experiment() -> dict:
    env = Obj1Env()
    ag = _fresh(env)
    phases, turn = school(ag, env)
    turns_after_school = ag.metrics.turns

    sat = exam(ag, Obj1Env())
    control, mutant = _control_and_mutant()

    pkt = packets()
    alone = cost_to_dest_alone()
    trip = shortest_collect()
    probe = probe_the_table()
    place = placements()
    # A pair the control can actually fail on: the trip fits the horizon,
    # fetching costs a detour, and no cheapest way to the table touches the
    # glass. The first draft of this slice found none because it swept the
    # item with the table nailed to PULPO's goal.
    usable = [q for q in place
              if q["fits_the_horizon"] and q["detour"] > 0
              and not q["item_on_cheapest_dest_path"]]

    report = {
        "world": "obj1",
        "slice": "obj-1",
        "item": list(ITEM_XYZ),
        "dest": list(DEST_XYZ),
        "start": cube.pose_name(cube.START),
        "layout": env.layout,
        "actions": N_ACTIONS,
        # Where carrying lives, checked rather than claimed.
        "coupled_is_env_not_wsp": coupled_is_env_not_wsp(),
        "dest_is_not_kind_goal": no_pose_is_ever_a_goal(),
        "domain_is_zero": _ext_is_zero("domain"),
        "style_is_zero": _ext_is_zero("style"),
        "seq_is_the_local_pose": seq_is_the_local_pose(),
        "packet_ceiling": cube.PACKET_CEILING,
        "packet_ceiling_holds": packet_ceiling_holds(),
        "packets_empty": len(pkt["empty"]),
        "packets_object": len(pkt["object"]),
        "packets_across": len(pkt["across"]),
        "index_max": index_max(),
        "states": len(valid_states()),
        # The geometry, flooded and not drawn.
        "shortest_collect": trip,
        "cost_to_dest_alone": alone,
        "value_horizon": cube.value_horizon(),
        "collect_fits_the_horizon": trip is not None
        and trip <= cube.value_horizon(),
        "item_costs_a_detour": trip is not None and alone is not None
        and (trip - 1) > alone,
        "item_on_cheapest_dest_path": item_on_cheapest_dest_path(),
        "placements": place,
        "placement_pairs": len(place),
        "placements_that_cost_a_detour_and_fit": [
            [q["item"], q["dest"]] for q in usable
        ],
        "this_pair_is_one_of_them":
            [list(ITEM_XYZ), list(DEST_XYZ)] in
            [[q["item"], q["dest"]] for q in usable],
        # The school and the exam.
        "curriculum": phases,
        "curriculum_turns": turn,
        "turns_after_school": turns_after_school,
        "exam_turns": EXAM_TURNS,
        "exam_start": sat["start"],
        "exam_start_is_canonical": sat["start"] == cube.pose_name(cube.START),
        "exam_item_starts_at_item": sat["item_start"] == list(ITEM_XYZ),
        "exam_collects": sat["collects"],
        "exam_object_hits": sat["object_hits"],
        "exam_collections_are_object_at_Y": sat["collections_are_object_at_Y"],
        "exam_agent_at_Y_without_object_tries":
            sat["agent_at_Y_without_object_tries"],
        "exam_agent_at_Y_without_object_reward_sum":
            sat["agent_at_Y_without_object_reward_sum"],
        # Asked of the world rather than counted off an exam that never
        # produced the turn. Both run, every time.
        "probe_headings": probe["headings"],
        "probe_empty_table_reward_sum": probe["empty_table_reward_sum"],
        "probe_empty_table_collects": probe["empty_table_collects"],
        "probe_full_table_reward_sum": probe["full_table_reward_sum"],
        "probe_the_item_stayed_put": probe["the_item_stayed_put"],
        "probe_delivering_sends_the_body_home":
            probe["delivering_sends_the_body_home"],
        "exam_values_an_empty_table": values_an_empty_table(ag),
        "exam_reward_sum": sat["reward_sum"],
        "exam_turns_holding_the_item": sat["turns_holding_the_item"],
        "exam_poses_visited": sat["poses_visited"],
        "exam_trail": sat["trail"],
        # The control: paid for arriving, asked to deliver.
        "control_pays_an_empty_table": True,
        "control_train_turns": control["train_turns"],
        "control_collects": control["collects"],
        "control_object_hits": control["object_hits"],
        "control_went_to_dest": control["stood_on_dest"],
        "control_turns_holding_the_item": control["turns_holding_the_item"],
        "control_trail": control["trail"],
        "control_values_an_empty_table": control["values_an_empty_table"],
        "control_learned_a_different_table":
            control["values_an_empty_table"] > values_an_empty_table(ag),
        # The mutant, in the cube it was schooled on.
        "mutant_pays_empty_Y": mutant["collects"] > 0
        and probe_the_table(pays_an_empty_table=True)["empty_table_collects"]
        == cube.HEADINGS,
        "mutant_collects": mutant["collects"],
        "mutant_object_hits": mutant["object_hits"],
        "mutant_agent_at_Y_without_object_tries":
            mutant["agent_at_Y_without_object_tries"],
        "mutant_trail": mutant["trail"],
        "cam_occupied": _cam_occupied(ag),
        "cam_slots": len(ag.cam.slot),
        "false_facts": ag.metrics.false_facts,
        "destroyed": ag.metrics.destroyed,
        "cortex_calls": ag.metrics.cortex_calls,
        "questions": ag.metrics.questions,
    }
    return report


def green(report: dict) -> bool:
    """The thing arrives, and arriving alone does not pay."""
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["questions"] == 0
        and report["actions"] == 3
        and report["index_max"] == cube.N_POSES - 1
        and report["domain_is_zero"]
        and report["style_is_zero"]
        and report["seq_is_the_local_pose"]
        and report["packet_ceiling_holds"]
        and report["dest_is_not_kind_goal"]
        and report["coupled_is_env_not_wsp"]
        and report["collect_fits_the_horizon"]
        and report["exam_start_is_canonical"]
        and report["exam_item_starts_at_item"]
        and report["exam_object_hits"] > 0
        and report["exam_collections_are_object_at_Y"]
        and report["exam_agent_at_Y_without_object_reward_sum"] == 0
        and report["probe_empty_table_collects"] == 0
        and report["probe_full_table_reward_sum"]
        == R_SUCCESS * cube.HEADINGS
        and report["probe_the_item_stayed_put"]
        and report["probe_delivering_sends_the_body_home"] == cube.HEADINGS
        and report["control_object_hits"] == 0
        and report["control_went_to_dest"]
        and report["mutant_pays_empty_Y"]
        and report["mutant_object_hits"] == 0
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_obj1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
