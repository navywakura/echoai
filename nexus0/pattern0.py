"""
PATTERN-0 — a riff one-step T cannot hear.

    ... B → A → C → A → B → A → C → A ...

At `A`, under the same action, the world hands back `C` sometimes and `B`
other times. `World.predict(A, approach)` has one row and one answer, so
it is right about half the time — not because it is broken, but because
the fact that decides the successor is not in its argument list. Where
the body **came from** is.

    (B, A, approach) → C
    (C, A, approach) → B

Both deterministic. That is the whole of the pattern, and no part of it is
a word, a label, a phrase or a model: it is three integers in and one out.

What this file has to prove, and each of the ways it could cheat:

    the ambiguity is measured        successor counts read off T's own
                                     inverse, not asserted from the cycle
    the exam is held out             segments that come *later in time*:
                                     generated after both memories were
                                     frozen and hashed, restarted from
                                     four phases of the cycle with the
                                     local counter back at zero. The
                                     training walk is a single run from
                                     phase 0 and does pass through all
                                     four phases on the way — what it
                                     never sees is these transitions
    nothing learns during it         both memories wrapped in a counter,
                                     both hashed before and after
    the context is load-bearing      a predictor without `prev` collapses
                                     onto T and the gain goes to zero
    it is not a clock                `turn % k` for every small k is
                                     scored on the same points and fails;
                                     the memory's API has no turn in it
    it is not a coincidence          a world whose successors are balanced
                                     by construction matures no rule
    the memory is bounded            more contexts than capacity: `size`
                                     stops, nothing already learned moves,
                                     and `dropped` says how many were lost

No Agent is built here and nothing is wired into the hot path: XFER-1 gets
to decide what deserves to cross worlds after seeing this measured.

    PYTHONPATH=. python3 -m echoai.nexus0.pattern0
"""

from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event

from echoai.nexus0 import pattern
from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    N_ACTIONS,
    N_SLOTS,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, Cell
from echoai.nexus0.pattern import ContextPredictor, PatternMemory, context_key
from echoai.nexus0.types import default_e
from echoai.nexus0.world import World

# Three cells, deliberately not consecutive: consecutive indices would let
# arithmetic look like a world model, the same trap WORLD-3's spine avoids.
CELL_A, CELL_B, CELL_C = 3, 17, 29
# The riff, written once. Everything below is read off it rather than
# repeated, so there is no second copy of the rule to drift.
CYCLE: Tuple[int, ...] = (CELL_B, CELL_A, CELL_C, CELL_A)
RULE = "B -> A -> C -> A, repetido"

TRAIN_STEPS = 200
EXAM_STEPS = 40
CLOCK_PERIODS = (2, 3, 4, 5, 6, 8)


def successors_of(cycle: Tuple[int, ...] = CYCLE) -> Dict[Tuple[int, int], int]:
    """(prev, cur) → next, read off the cycle itself.

    The physics is generated from the sequence, not typed out beside it.
    Nothing in `pattern.py` sees this table or these three numbers.
    """
    out: Dict[Tuple[int, int], int] = {}
    n = len(cycle)
    for i in range(n):
        out[(cycle[i - 1], cycle[i])] = cycle[(i + 1) % n]
    return out


def balanced_successors() -> Dict[Tuple[int, int], List[int]]:
    """The control world: every context has two successors, half and half.

    Designed, not left to chance. `A` after `B` goes to `C` and then to
    `B` and then to `C` again, so the context is contradicted on its
    second observation for ever.
    """
    cells = (CELL_A, CELL_B, CELL_C)
    # Total over every (prev, cur) the walk can reach, and two successors
    # for each, taken in turn. So every context is contradicted on its
    # second observation and stays contradicted: no rule can mature here
    # by luck, which is what "designed, not left to chance" has to mean.
    return {(p, c): [x for x in cells if x != c]
            for p in cells for c in cells}


class PatternEnv:
    """Three EMPTY cells and a memory of one step. No reward, no kind.

    The world is what carries the hidden state — `prev` — and that is the
    point: nothing the fast loop perceives contains it, so a predictor
    that only sees the current packet cannot recover it.
    """

    def __init__(self, phase: int = 0, cycle: Tuple[int, ...] = CYCLE,
                 balanced: bool = False) -> None:
        self.cycle = tuple(cycle)
        self.balanced = bool(balanced)
        self.table = successors_of(self.cycle)
        self.alt_table = balanced_successors()
        self._turn_of: Counter = Counter()
        self.kind: List[int] = [KIND_EMPTY] * (max(self.cycle) + 1)
        self.hidden_bit = True
        self.last_reward = 0
        self.teleport(phase)

    def teleport(self, phase: int) -> None:
        """Start at a phase of the cycle, with `prev` set from it."""
        p = int(phase) % len(self.cycle)
        self.prev = self.cycle[p - 1]
        self.i = self.cycle[p]

    def cell(self) -> Cell:
        return Cell(index=self.i, kind=KIND_EMPTY)

    def step(self, a: int) -> int:
        """Approach walks the riff; anything else stands still.

        Standing still does not change where the body came from, so the
        context survives a pause — which is what makes `avoid` an
        unambiguous observation rather than a hole in the sequence.
        """
        if int(a) != ACTION_APPROACH:
            self.last_reward = 0
            return self.i
        here = (self.prev, self.i)
        if self.balanced:
            options = self.alt_table[here]
            nxt = options[self._turn_of[here] % len(options)]
            self._turn_of[here] += 1
        else:
            nxt = self.table[here]
        self.prev, self.i = self.i, nxt
        self.last_reward = 0
        return nxt


def _slot(cam: Cam, index: int) -> int:
    """A real WSP packet and a real CAM slot, allocated like the loop does."""
    wsp = encode_cell(index, KIND_EMPTY)
    s = cam.get(wsp)
    if s >= 0:
        return s
    vertex, _, _ = encode_event(wsp)
    s, _ = allocate(cam, wsp, vertex, 0, default_e(), has_fact=0, extract="",
                    source="nexus0-pattern", label="", key=wsp)
    return s


def walk(env: PatternEnv, steps: int,
         action: int = ACTION_APPROACH) -> List[Tuple[int, int, int, int]]:
    """(prev_cell, cell, action, next_cell) for each step taken."""
    out = []
    for _ in range(steps):
        prev_cell, cur_cell = env.prev, env.i
        nxt_cell = env.step(action)
        out.append((prev_cell, cur_cell, action, nxt_cell))
    return out


def to_slots(cam: Cam, steps) -> List[Tuple[int, int, int, int]]:
    return [(_slot(cam, p), _slot(cam, c), a, _slot(cam, n))
            for p, c, a, n in steps]


class Watched:
    """Counts `observe()`. The exam has to make none of these."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.observes = 0

    def observe(self, *a, **kw):
        self.observes += 1
        return self.inner.observe(*a, **kw)

    def predict(self, *a, **kw):
        return self.inner.predict(*a, **kw)


def world_hash(t: World) -> str:
    import hashlib

    blob = repr([t.pred, t.n, t.alt, t.alt_n]).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def successor_counts(t: World) -> Dict[Tuple[int, int], Dict[int, int]]:
    """Successors per (slot, action), off T's own inverse.

    Measured, not claimed. A `(s, a)` with more than one successor here is
    ambiguous *because it was observed to be*, and the report prints the
    counts so nobody has to take the cycle's word for it.
    """
    out: Dict[Tuple[int, int], Dict[int, int]] = {}
    for s in range(N_SLOTS):
        for nxt, a, count in t.inv[s]:
            out.setdefault((s, a), {})[nxt] = int(count)
    return out


def train(balanced: bool = False, steps: int = TRAIN_STEPS,
          capacity: int = pattern.PATTERN_CAPACITY,
          min_hits: int = pattern.PATTERN_MIN_HITS,
          pauses: Optional[bool] = None):
    """One walk, two memories, exactly the same transitions to both.

    `pauses` adds a few `avoid` standstills so the action field of the
    context is not a constant. They are switched off in the balanced
    control on purpose: standing still *is* a regularity, and a control
    that is supposed to contain none must not be handed one — otherwise
    `no_pattern_mature` would be false for a reason that has nothing to
    do with the claim.
    """
    if pauses is None:
        pauses = not balanced
    cam = Cam()
    t = World()
    mem = PatternMemory(capacity=capacity, min_hits=min_hits)
    env = PatternEnv(phase=0, balanced=balanced)
    steps_cells = walk(env, steps)
    if pauses:
        for cell in CYCLE:
            pause = PatternEnv(phase=CYCLE.index(cell), balanced=balanced)
            steps_cells += walk(pause, 3, action=ACTION_AVOID)
    stream = to_slots(cam, steps_cells)
    for prev, cur, a, nxt in stream:
        t.observe(cur, a, nxt)
        mem.observe(prev, cur, a, nxt)
    return cam, t, mem, stream


def exam(cam: Cam, t: World, mem: PatternMemory,
         rotations: Tuple[int, ...] = (0, 1, 2, 3),
         steps: int = EXAM_STEPS, balanced: bool = False,
         learn: bool = False, ambiguous=None) -> dict:
    """Segments generated after the freeze, both predictors asked first.

    Not a slice of the list the memories were fed: these steps are taken
    later, from a fresh env at each phase, and the successor is used to
    advance the context and for nothing else. No `observe()` unless
    `learn` is set, which is what a mutant does.
    """
    watched_t, watched_m = Watched(t), Watched(mem)
    combined = ContextPredictor(watched_t, watched_m)
    if ambiguous is None:
        # Which (slot, action) T was *observed* to be of two minds about.
        # Injectable so an arm can be scored on the same points with a
        # predictor that knows nothing — see `unknown_*` in the report.
        ambiguous = {k for k, v in successor_counts(t).items() if len(v) > 1}

    decision_points = 0
    t_hits = pattern_hits = 0
    pattern_unknown = 0
    by_rotation: List[dict] = []
    clock: Dict[int, int] = {p: 0 for p in CLOCK_PERIODS}
    clock_table = _clock_table(cam, t)

    for rot in rotations:
        env = PatternEnv(phase=rot, balanced=balanced)
        r_points = r_t = r_p = 0
        first_local_turn: Optional[int] = None
        # The local counter starts at zero in every rotation, so an
        # absolute clock cannot be right in more than one of them.
        for local_turn in range(steps):
            if first_local_turn is None:
                first_local_turn = local_turn
            prev_cell, cur_cell = env.prev, env.i
            prev, cur = _slot(cam, prev_cell), _slot(cam, cur_cell)
            a = ACTION_APPROACH
            guess_t = watched_t.predict(cur, a)
            guess_p, source = combined.predict(prev, cur, a)
            nxt = _slot(cam, env.step(a))
            if (cur, a) not in ambiguous:
                continue
            r_points += 1
            r_t += int(guess_t == nxt)
            r_p += int(guess_p == nxt)
            if source != "pattern":
                pattern_unknown += 1
            for period in CLOCK_PERIODS:
                clock[period] += int(
                    clock_table.get((period, local_turn % period)) == nxt)
            if learn:
                watched_t.observe(cur, a, nxt)
                watched_m.observe(prev, cur, a, nxt)
        decision_points += r_points
        t_hits += r_t
        pattern_hits += r_p
        by_rotation.append({"rotation": rot, "decision_points": r_points,
                            "t_hits": r_t, "pattern_hits": r_p,
                            # Zero in every rotation, or an absolute clock
                            # would only have to be right once.
                            "first_local_turn": first_local_turn})

    return {
        "decision_points": decision_points,
        "t_hits": t_hits,
        "pattern_hits": pattern_hits,
        "prediction_gain_hits": pattern_hits - t_hits,
        "pattern_unknown": pattern_unknown,
        "by_rotation": by_rotation,
        "clock_hits": {str(k): v for k, v in clock.items()},
        "observes_during_exam": watched_t.observes + watched_m.observes,
    }


def _clock_table(cam: Cam, t: World) -> Dict[Tuple[int, int], int]:
    """What a `turn % period` predictor would answer, fitted on training.

    Built from the training walk at phase 0 — the best an absolute clock
    could do, given exactly what the honest predictors were given.
    """
    env = PatternEnv(phase=0)
    votes: Dict[Tuple[int, int], Counter] = {}
    for local_turn, (prev_cell, cur_cell, a, nxt_cell) in enumerate(
            walk(env, TRAIN_STEPS)):
        for period in CLOCK_PERIODS:
            votes.setdefault((period, local_turn % period),
                             Counter())[_slot(cam, nxt_cell)] += 1
    return {k: v.most_common(1)[0][0] for k, v in votes.items()}


# --- the controls -------------------------------------------------------
def train_without_context(steps: int = TRAIN_STEPS):
    """The same walk with `prev` thrown away. The field, made non-load-bearing.

    Every context collapses onto `(0, cur, action)`, which is exactly what
    T already has — so `A` under approach is contradicted, never matures,
    and the composite falls through to T on every point. The gain has to
    go to zero, or `prev` was decoration.
    """
    cam = Cam()
    t = World()
    mem = PatternMemory()
    env = PatternEnv(phase=0)
    for prev, cur, a, nxt in to_slots(cam, walk(env, steps)):
        t.observe(cur, a, nxt)
        mem.observe(0, cur, a, nxt)  # the mutant: no previous slot
    return cam, t, mem


def capacity_probe(capacity: int = 4) -> dict:
    """More contexts than room. Nothing already learned may move."""
    mem = PatternMemory(capacity=capacity)
    stored: Dict[int, int] = {}
    for k in range(capacity):
        for _ in range(mem.min_hits):
            mem.observe(k, k + 100, 0, k + 200)
        stored[context_key(k, k + 100, 0)] = k + 200
    before = {key: mem.predict(k, k + 100, 0)
              for k, key in enumerate(stored)}
    size_before, dropped_before = mem.size, mem.dropped
    for k in range(capacity, capacity + 16):
        for _ in range(mem.min_hits):
            mem.observe(k, k + 100, 0, k + 200)
    after = {key: mem.predict(k, k + 100, 0)
             for k, key in enumerate(stored)}
    return {
        "capacity": mem.capacity,
        "size_before": size_before,
        "size_after": mem.size,
        "dropped_before": dropped_before,
        "dropped_after": mem.dropped,
        "size_never_exceeds_capacity": mem.size <= mem.capacity,
        "nothing_was_overwritten": before == after,
        "new_contexts_were_dropped": mem.dropped > dropped_before,
        "stored_answers": [before[k] for k in stored],
    }


# --- isolation ----------------------------------------------------------
FORBIDDEN_NAMES = {"Cam", "QTable", "World", "Agent", "encode_cell",
                   "allocate", "encode_event", "pack", "unpack"}
FORBIDDEN_FIELDS = {"wsp", "kind", "reward", "extract", "has_fact", "q_row",
                    "cam", "q"}
# Objects the memory may be *handed* but must never write into.
# `ContextPredictor` holds a `World` and is allowed to ask it one thing.
FOREIGN_RECEIVERS = ("world", "t", "cam", "q")
# The tables that belong to somebody else. `PatternMemory` has fields of
# the same four names, and those are its own — the difference is the
# receiver, not the name, so the check is on `self.world.pred` and never
# on `self.pred`.
FOREIGN_TABLES = ("pred", "n", "alt", "alt_n", "inv", "conflicts")
FORBIDDEN_CALLS = ("observe", "reset_traces", "update", "put", "load_rows",
                   "set", "allocate")


def _root_attribute(node: ast.AST) -> Optional[ast.Attribute]:
    """Peel `[i][j]` off an assignment target down to the attribute.

    `self.world.pred[0][0] = 9` is a `Subscript` of a `Subscript` of an
    `Attribute`, and only the attribute says whose table is being written.
    Looking at the target's own node type was how five different writes
    into `World` came back clean.
    """
    while isinstance(node, (ast.Subscript, ast.Starred)):
        node = node.value
    return node if isinstance(node, ast.Attribute) else None


def _foreign_write(target: ast.AST) -> Optional[str]:
    """`world.pred`, `t.alt_n`, … — or None if it is the memory's own."""
    attr = _root_attribute(target)
    if attr is None or attr.attr not in FOREIGN_TABLES:
        return None
    owner = attr.value
    if isinstance(owner, ast.Attribute) and owner.attr in FOREIGN_RECEIVERS:
        return f"{owner.attr}.{attr.attr}"
    if isinstance(owner, ast.Name) and owner.id in FOREIGN_RECEIVERS:
        return f"{owner.id}.{attr.attr}"
    return None


def isolation_findings(source: str, where: str = "pattern.py") -> List[str]:
    """The memory holds integers and reaches nothing.

    No CAM, no Q, no encoder, no packet; no write into anything it is
    handed. `ContextPredictor` is given a `World` and may call `predict`
    on it and nothing else.

    A write is a write whatever syntax it arrives in: `Assign`, `AnnAssign`
    and `AugAssign`, through any number of subscripts. The earlier version
    only looked at attribute *names* and at calls, so every one of

        self.world.pred[0][0] = 9      self.world.alt[0][0] = 9
        self.world.n[0][0] += 1        self.world.alt_n[0][0] = 1
        self.world.pred = []

    came back clean. What separates those from `PatternMemory`'s own
    `self.pred[i] = nxt` is the receiver, not the field name — the memory
    has tables called `pred`, `n`, `alt` and `alt_n` of its own, and they
    are not anybody else's business either way.
    """
    out: List[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = ([a.name for a in node.names]
                     + ([node.module] if isinstance(node, ast.ImportFrom)
                        and node.module else []))
            for name in names:
                leaf = name.split(".")[-1]
                if leaf in FORBIDDEN_NAMES:
                    out.append(f"{where}: importa {name}")
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            flat: List[ast.AST] = []
            for t in targets:
                if isinstance(t, (ast.Tuple, ast.List)):
                    flat.extend(t.elts)
                else:
                    flat.append(t)
            for t in flat:
                hit = _foreign_write(t)
                if hit is not None:
                    out.append(f"{where}: escribe en `{hit}`")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_FIELDS:
                out.append(f"{where}: toca `{node.attr}`")
            if (node.attr in FORBIDDEN_CALLS
                    and isinstance(node.value, ast.Attribute)
                    and node.value.attr in FOREIGN_RECEIVERS):
                out.append(f"{where}: llama a {node.value.attr}.{node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for cell in (f"={CELL_A}", f"={CELL_B}", f"={CELL_C}"):
                if cell in node.value:
                    out.append(f"{where}: nombra una celda del banco")
    return out


# Each way out, injected on its own, so no single detection can be
# carrying the rest. The composite that used to stand here passed as
# long as *something* was found, which is how five writes into `World`
# hid behind one forbidden import.
ISOLATION_INJECTIONS: Tuple[Tuple[str, str], ...] = (
    ("importa World", "from echoai.nexus0.world import World\n"),
    ("importa la CAM", "from echoai.core.cam import Cam\n"),
    ("importa el encoder", "from echoai.nexus0.encoder import encode_cell\n"),
    ("llama a world.observe",
     "def x(self):\n    self.world.observe(1, 2, 3)\n"),
    ("escribe world.pred", "def x(self):\n    self.world.pred[0][0] = 9\n"),
    ("escribe world.n", "def x(self):\n    self.world.n[0][0] += 1\n"),
    ("escribe world.alt", "def x(self):\n    self.world.alt[0][0] = 9\n"),
    ("escribe world.alt_n", "def x(self):\n    self.world.alt_n[0][0] = 1\n"),
    ("reemplaza world.pred entera",
     "def x(self):\n    self.world.pred = []\n"),
    ("escribe t.alt_n", "def x(self):\n    self.t.alt_n[0][0] = 1\n"),
    ("guarda un WSP", "def x(self):\n    self.wsp = b''\n"),
    ("toca la CAM", "def x(self):\n    self.cam.put(1)\n"),
)


# --- the battery --------------------------------------------------------
REQUIRED_MUTANTS = (
    "ignora el slot anterior",
    "sólo (s,a) haciéndose pasar por patrón",
    "predice por turn % periodo",
    "aprende durante el examen",
    "precarga el futuro del examen",
    "madura tras una sola observación",
    "puntúa sólo los casos cubiertos",
    "compara T y patrón en turnos distintos",
    "memoria sin límite",
    "la capacidad llena sobrescribe una regla",
    "dropped no aumenta",
    "el control sin regularidad madura una regla",
    "el patrón real no toca nada",
    "el patrón importa World",
    "el patrón importa la CAM",
    "el patrón importa el encoder",
    "el patrón llama a world.observe",
    "el patrón escribe world.pred",
    "el patrón escribe world.n",
    "el patrón escribe world.alt",
    "el patrón escribe world.alt_n",
    "el patrón reemplaza world.pred entera",
    "el patrón escribe t.alt_n",
    "el patrón guarda un WSP",
    "el patrón toca la CAM",
    "green deja de exigir ganancia",
    "green deja de exigir frecuencia",
    "green deja de exigir congelación",
    "se borra un mutante requerido",
)


def battery_state(battery: Any) -> dict:
    """Recounted from the list. Same discipline TALK-1c had to learn.

    Its own copy rather than an import of `talk1`: the two gates protect
    different claims and must not be able to drift into each other.
    """
    if not isinstance(battery, list):
        return {"missing": sorted(REQUIRED_MUTANTS), "duplicated": [],
                "alive": [], "malformed": ["`mutants` no es una lista"],
                "total": 0, "killed": 0}
    names: List[str] = []
    alive: List[str] = []
    malformed: List[str] = []
    killed = 0
    for i, entry in enumerate(battery):
        if not isinstance(entry, dict):
            malformed.append(f"[{i}] no es un objeto")
            continue
        name = entry.get("mutant")
        if isinstance(name, str) and name.strip():
            names.append(name)
        else:
            malformed.append(f"[{i}] sin nombre: {name!r}")
            name = f"[{i}]"
        dead = entry.get("killed")
        if not isinstance(dead, bool):
            malformed.append(f"[{i}] `killed` no es booleano: {dead!r}")
            continue
        if dead:
            killed += 1
        else:
            alive.append(name)
    return {
        "missing": sorted(set(REQUIRED_MUTANTS) - set(names)),
        "duplicated": sorted({n for n in names if names.count(n) > 1}),
        "alive": sorted(alive),
        "malformed": sorted(malformed),
        "total": len(battery),
        "killed": killed,
    }


def mutants(cam: Cam, t: World, mem: PatternMemory, honest: dict) -> List[dict]:
    """Alternative predictors and doubled outputs, each of which must lose."""
    out: List[dict] = []

    def note(name: str, killed: bool, evidence) -> None:
        out.append({"mutant": name, "killed": bool(killed),
                    "evidence": evidence})

    # 1 & 2 — the context field, removed two different ways.
    cam_n, t_n, mem_n = train_without_context()
    blind = exam(cam_n, t_n, mem_n)
    note("ignora el slot anterior", blind["prediction_gain_hits"] <= 0,
         {"gain": blind["prediction_gain_hits"], "mature": len(
             {k: v for k, v in mem_n.mature_counts().items()})})
    only_sa = PatternMemory()
    for prev, cur, a, nxt in to_slots(Cam(), walk(PatternEnv(0), TRAIN_STEPS)):
        only_sa.observe(cur, cur, a, nxt)  # the current slot twice: no history
    note("sólo (s,a) haciéndose pasar por patrón",
         only_sa.predict(_slot(cam, CELL_A), _slot(cam, CELL_A),
                         ACTION_APPROACH) is None,
         {"mature_at_the_ambiguous_state": False})

    # 3 — an absolute clock, fitted on the same training walk.
    best_clock = max(int(v) for v in honest["clock_hits"].values())
    note("predice por turn % periodo", best_clock < honest["pattern_hits"],
         {"best_clock_hits": best_clock, "pattern_hits": honest["pattern_hits"],
          "t_hits": honest["t_hits"]})

    # 4 — learning during held-out.
    before_t, before_m = world_hash(t), mem.snapshot_hash()
    leaky = exam(cam, t, mem, learn=True)
    note("aprende durante el examen",
         leaky["observes_during_exam"] > 0
         and (world_hash(t) != before_t or mem.snapshot_hash() != before_m),
         {"observes": leaky["observes_during_exam"],
          "t_hash_moved": world_hash(t) != before_t,
          "pattern_hash_moved": mem.snapshot_hash() != before_m})

    # 5 — preloading the exam's own segments. Caught by the same hash: a
    # memory trained past the training boundary is not the frozen one.
    preloaded = PatternMemory()
    for rot in (0, 1, 2, 3):
        for prev, cur, a, nxt in to_slots(cam, walk(PatternEnv(rot), EXAM_STEPS)):
            preloaded.observe(prev, cur, a, nxt)
    note("precarga el futuro del examen",
         preloaded.snapshot_hash() != before_m,
         {"differs_from_the_frozen_memory": True})

    # 6 — maturity after a single observation.
    eager = PatternMemory(min_hits=1)
    eager.observe(11, 22, 0, 33)
    strict = PatternMemory()
    strict.observe(11, 22, 0, 33)
    note("madura tras una sola observación",
         eager.predict(11, 22, 0) is not None
         and strict.predict(11, 22, 0) is None,
         {"eager": eager.predict(11, 22, 0), "strict": strict.predict(11, 22, 0)})

    # 7 — dropping the uncovered points from the denominator.
    covered = honest["decision_points"] - honest["pattern_unknown"]
    note("puntúa sólo los casos cubiertos",
         covered != honest["decision_points"] or honest["pattern_unknown"] == 0,
         {"decision_points": honest["decision_points"],
          "pattern_unknown": honest["pattern_unknown"],
          "note": "None no es acierto y no sale del denominador"})

    # 8 — scoring the two at different steps.
    shifted = _shifted_scoring(cam, t, mem)
    note("compara T y patrón en turnos distintos",
         shifted["prediction_gain_hits"] != honest["prediction_gain_hits"],
         {"shifted_gain": shifted["prediction_gain_hits"],
          "honest_gain": honest["prediction_gain_hits"]})

    # 9, 10, 11 — the bound, the incumbent and the counter.
    probe = capacity_probe()
    note("memoria sin límite", probe["size_never_exceeds_capacity"],
         {"size": probe["size_after"], "capacity": probe["capacity"]})
    note("la capacidad llena sobrescribe una regla",
         probe["nothing_was_overwritten"], probe["stored_answers"])
    note("dropped no aumenta", probe["new_contexts_were_dropped"],
         {"dropped": probe["dropped_after"]})

    # 12 — a world with no regularity to find.
    _cam_b, t_b, mem_b = train(balanced=True)[:3]
    flat = exam(_cam_b, t_b, mem_b, balanced=True)
    note("el control sin regularidad madura una regla",
         not mem_b.mature_counts() and flat["prediction_gain_hits"] <= 0,
         {"mature": len(mem_b.mature_counts()),
          "gain": flat["prediction_gain_hits"],
          "conflicts": mem_b.conflicts})

    # 13 — the memory reaching into the animal, one way out at a time.
    # A single composite injection passed as long as *anything* was found,
    # which is exactly how five different writes into `World` hid behind
    # one forbidden import.
    findings = isolation_findings(
        Path(pattern.__file__).read_text(encoding="utf-8"))
    note("el patrón real no toca nada", not findings, {"findings": findings})
    for label, injected in ISOLATION_INJECTIONS:
        hits = isolation_findings(injected, "mutante")
        note(f"el patrón {label}", bool(hits), hits)

    # 14, 15, 16, 17 — the gate itself.
    base = dict(honest)
    note("green deja de exigir ganancia",
         not green(dict(_report_shape(honest), prediction_gain_hits=0)),
         {"gain": 0})
    note("green deja de exigir frecuencia",
         not green(dict(_report_shape(honest), min_hits=1)), {"min_hits": 1})
    note("green deja de exigir congelación",
         not green(dict(_report_shape(honest), observes_during_exam=1)),
         {"observes": 1})
    shrunk = _report_shape(honest)
    shrunk["mutants"] = [m for m in shrunk["mutants"]
                         if m["mutant"] != "ignora el slot anterior"]
    note("se borra un mutante requerido", not green(shrunk),
         {"missing": battery_state(shrunk["mutants"])["missing"]})
    del base
    return out


def _shifted_scoring(cam: Cam, t: World, mem: PatternMemory) -> dict:
    """T scored on step i, the pattern on step i+1. Same points, wrong pairing."""
    ambiguous = {k for k, v in successor_counts(t).items() if len(v) > 1}
    combined = ContextPredictor(t, mem)
    t_hits = pattern_hits = points = 0
    for rot in (0, 1, 2, 3):
        env = PatternEnv(phase=rot)
        pending: Optional[int] = None
        for _ in range(EXAM_STEPS):
            prev, cur = _slot(cam, env.prev), _slot(cam, env.i)
            a = ACTION_APPROACH
            guess_t = t.predict(cur, a)
            guess_p, _ = combined.predict(prev, cur, a)
            nxt = _slot(cam, env.step(a))
            if (cur, a) in ambiguous:
                points += 1
                t_hits += int(guess_t == nxt)
                if pending is not None:
                    pattern_hits += int(pending == nxt)
                pending = guess_p
    return {"decision_points": points, "t_hits": t_hits,
            "pattern_hits": pattern_hits,
            "prediction_gain_hits": pattern_hits - t_hits}


def _report_shape(honest: dict) -> dict:
    """A minimal green-shaped report, for bending in the battery above."""
    return {
        "decision_points": honest["decision_points"],
        "t_hits": honest["t_hits"],
        "pattern_hits": honest["pattern_hits"],
        "prediction_gain_hits": honest["prediction_gain_hits"],
        "pattern_unknown": honest["pattern_unknown"],
        "observes_during_exam": 0,
        "min_hits": pattern.PATTERN_MIN_HITS,
        "context_order": pattern.PATTERN_ORDER,
        "t_hash_before": "x", "t_hash_after": "x",
        "pattern_hash_before": "y", "pattern_hash_after": "y",
        "size": 7, "capacity": pattern.PATTERN_CAPACITY, "dropped": 0,
        "unknown_decision_points": honest["decision_points"],
        "unknown_pattern_hits": 0, "unknown_t_hits": 0,
        "unknown_pattern_unknown": honest["decision_points"],
        "exam_local_turn_starts": [0, 0, 0, 0],
        "ambiguous_states": 1,
        "no_pattern_mature": True,
        "no_pattern_gain_hits": 0,
        "no_context_gain_hits": 0,
        "absolute_clock_control_fails": True,
        "size_never_exceeds_capacity": True,
        "nothing_was_overwritten": True,
        "new_contexts_were_dropped": True,
        "isolation_findings": [],
        "human_labels": 0, "llm_calls": 0, "cortex_calls": 0,
        "false_facts": 0, "destroyed": 0,
        "mutants": [{"mutant": n, "killed": True} for n in REQUIRED_MUTANTS],
        "mutants_total": len(REQUIRED_MUTANTS),
        "mutants_killed": len(REQUIRED_MUTANTS),
    }


# --- the experiment -----------------------------------------------------
def experiment() -> dict:
    cam, t, mem, stream = train()

    counts = successor_counts(t)
    ambiguous = {k: v for k, v in counts.items() if len(v) > 1}
    t_before, m_before = world_hash(t), mem.snapshot_hash()

    honest = exam(cam, t, mem)

    t_after, m_after = world_hash(t), mem.snapshot_hash()

    # The three controls, each an arm rather than a sentence.
    _c, t_flat, mem_flat = train(balanced=True)[:3]
    flat = exam(_c, t_flat, mem_flat, balanced=True)
    cam_n, t_n, mem_n = train_without_context()
    blind = exam(cam_n, t_n, mem_n)
    probe = capacity_probe()

    # Scored on exactly the same points, with a predictor that knows
    # nothing: every answer is None. `None` is a miss and stays in the
    # denominator, so this arm must show the full count of points and no
    # hits at all. Without it, "no cuenta como acierto" and "no sale del
    # denominador" are two rules nothing can violate.
    ambiguous_keys = set(ambiguous)
    naive = exam(cam, World(), PatternMemory(), ambiguous=ambiguous_keys)

    best_clock = max(int(v) for v in honest["clock_hits"].values())
    battery = mutants(cam, t, mem, honest)
    state = battery_state(battery)

    out: Dict[str, Any] = {
        "world": "pattern0",
        "rule_description": RULE,
        "cycle": list(CYCLE),
        "context_order": mem.order,
        "capacity": mem.capacity,
        "size": mem.size,
        "dropped": mem.dropped,
        "min_hits": mem.min_hits,
        "train_transitions": len(stream),
        "exam_transitions": EXAM_STEPS * 4,
        "exam_rotations": [0, 1, 2, 3],
        "exam_steps_per_rotation": EXAM_STEPS,

        # Measured, not asserted: the successors T actually saw.
        "ambiguous_state_counts": {
            f"slot {s} · acción {a}": v for (s, a), v in ambiguous.items()},
        "ambiguous_states": len(ambiguous),
        "pattern_context_counts": {
            str(k): v for k, v in sorted(mem.mature_counts().items())},
        "mature_contexts": len(mem.mature_counts()),

        "decision_points": honest["decision_points"],
        "t_hits": honest["t_hits"],
        "pattern_hits": honest["pattern_hits"],
        "prediction_gain_hits": honest["prediction_gain_hits"],
        "pattern_unknown": honest["pattern_unknown"],
        "by_rotation": honest["by_rotation"],
        "clock_hits": honest["clock_hits"],
        "best_clock_hits": best_clock,
        "absolute_clock_control_fails": bool(
            best_clock < honest["pattern_hits"]),

        "unknown_decision_points": naive["decision_points"],
        "unknown_pattern_hits": naive["pattern_hits"],
        "unknown_t_hits": naive["t_hits"],
        "unknown_pattern_unknown": naive["pattern_unknown"],
        "exam_local_turn_starts": [r["first_local_turn"]
                                   for r in honest["by_rotation"]],

        "observes_during_exam": honest["observes_during_exam"],
        "t_hash_before": t_before, "t_hash_after": t_after,
        "pattern_hash_before": m_before, "pattern_hash_after": m_after,
        "memories_frozen": bool(t_before == t_after and m_before == m_after),

        # Control 1: no regularity to find.
        "no_pattern_mature": not mem_flat.mature_counts(),
        "no_pattern_gain_hits": flat["prediction_gain_hits"],
        "no_pattern_conflicts": mem_flat.conflicts,
        # Control 2: the context field, made non-load-bearing.
        "no_context_gain_hits": blind["prediction_gain_hits"],
        "no_context_mature": len(mem_n.mature_counts()),
        # Control 3: a memory that will not fit what it is shown.
        "size_never_exceeds_capacity": probe["size_never_exceeds_capacity"],
        "nothing_was_overwritten": probe["nothing_was_overwritten"],
        "new_contexts_were_dropped": probe["new_contexts_were_dropped"],
        "capacity_probe": probe,

        "isolation_findings": isolation_findings(
            Path(pattern.__file__).read_text(encoding="utf-8")),
        "predict_takes_no_turn": _predict_signature(),

        "mutants": battery,
        "mutants_total": state["total"],
        "mutants_killed": state["killed"],
        "required_mutants": len(REQUIRED_MUTANTS),
        "required_mutants_missing": state["missing"],
        "mutants_alive": state["alive"],
        "mutants_malformed": state["malformed"],

        "human_labels": 0,
        "llm_calls": 0,
        "cortex_calls": 0,
        "false_facts": sum(1 for s in cam.slot if s.has_fact and not s.extract),
        "destroyed": cam.destroyed,
        "n_actions": N_ACTIONS,
    }
    return out


def _predict_signature() -> bool:
    """No turn, no clock, no world name in the memory's own API."""
    import inspect

    for fn in (PatternMemory.predict, PatternMemory.observe,
               ContextPredictor.predict):
        names = set(inspect.signature(fn).parameters)
        if names & {"turn", "clock", "world_name", "phase", "rotation", "t"}:
            return False
    return True


def green(report: dict) -> bool:
    """Every KPI at once. One red number and the slice is red."""
    state = battery_state(report.get("mutants"))
    if state["malformed"] or state["missing"] or state["duplicated"]:
        return False
    if state["alive"]:
        return False
    if report.get("mutants_total") != state["total"]:
        return False
    if report.get("mutants_killed") != state["killed"]:
        return False
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["llm_calls"] == 0
        and report["human_labels"] == 0
        # there is something for one-step T to be blind to, and it was
        # measured rather than designed in a comment
        and report["ambiguous_states"] >= 1
        # the memory answered on the held-out points, and beat T there
        and report["decision_points"] > 0
        and report["pattern_unknown"] == 0
        # None is not a hit, and does not leave the denominator
        and report["unknown_decision_points"] == report["decision_points"]
        and report["unknown_pattern_hits"] == 0
        and report["unknown_t_hits"] == 0
        and report["unknown_pattern_unknown"] == report["decision_points"]
        # every rotation counts from zero
        and set(report["exam_local_turn_starts"]) == {0}
        and report["prediction_gain_hits"] > 0
        and report["pattern_hits"] > report["t_hits"]
        # nothing learned during the exam, and both memories are the ones
        # that were frozen
        and report["observes_during_exam"] == 0
        and report["t_hash_before"] == report["t_hash_after"]
        and report["pattern_hash_before"] == report["pattern_hash_after"]
        # frequency, and an order that is actually a context
        and report["min_hits"] >= 2
        and report["context_order"] >= 2
        and report["predict_takes_no_turn"]
        # the three controls
        and report["no_pattern_mature"]
        and report["no_pattern_gain_hits"] <= 0
        and report["no_context_gain_hits"] <= 0
        and report["absolute_clock_control_fails"]
        # the bound
        and report["size"] <= report["capacity"]
        and report["size_never_exceeds_capacity"]
        and report["nothing_was_overwritten"]
        and report["new_contexts_were_dropped"]
        and report["isolation_findings"] == []
        and report["n_actions"] == N_ACTIONS
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_pattern0_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
