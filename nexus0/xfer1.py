"""
XFER-1 — the same animal, three worlds.

Not the same class run three times, and not three agents handed copies of
each other's tables. **One `Agent` object**, born once, whose CAM, Q, T and
pattern memory are the same four objects before and after each border —
checked by identity, not by resemblance. What changes at a border is
`ag.env` and one latch: `prev_slot`, the claim that the body was somewhere
a moment ago, which stops being true the instant the world underneath it
is swapped. Dropping that is not forgetting anything.

    PARK_A   school
    PARK_B   first change
    PARK_C   second change, and not the first one again

The three share the encoder, the WSP identities, the kinds and three
actions. What differs between them is **physics**, by successor table: one
edge moved at the A→B border and two at B→C, so at each entry T holds rows
that are still right and at least one that is now wrong. Both counts are
measured off the tables and printed.

Inside every layout, unchanged, sits PATTERN-0's order-2 riff: at one cell
the successor depends on which cell the body came from. The rule is read
off a cycle by `pattern0.successors_of`, the same function that generated
it there, so it is one table and not three branches. Nothing anywhere in
this file's core reads the name of a world.

What is being asked, and how it could be faked:

    the same animal          four `id()` checks across both borders, and
                             a mutant for each of the four memories being
                             quietly replaced
    it is the memory         a scratch agent per border, matched on seat,
                             seed, flags, turns and the exact `turn`
                             values handed to the policy, so `% 8` cannot
                             pay for the result
    and not the clock        an age control that has spent the same turns
                             in a park with no hazard, no prize and no
                             riff: same mileage, nothing learned
    both borders, separately gain_B and gain_C are each required to be
                             positive; a positive total is not enough

    PYTHONPATH=. python3 -m echoai.nexus0.xfer1
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from echoai.nexus0 import pattern, pattern0, thought
from echoai.nexus0.constants import (
    ACTION_APPROACH,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
    N_ACTIONS,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_GOAL, KIND_THREAT, Cell, _reward

# The park. Stride 13, so consecutive indices never let arithmetic look
# like a world model, and every index is under the 256-packet ceiling.
S0, S1, H1, S3, H2, S5, H3, S7, GOAL = 5, 18, 31, 44, 57, 70, 83, 96, 109
D1, D2 = 122, 135        # the two detours the borders open
R0, R1, R2 = 148, 161, 174   # the riff
HAZARDS = (H1, H2, H3)
N_CELLS_PARK = 256

# The riff, written once and read off a cycle — the same shape and the
# same generator PATTERN-0 used. At R0 the successor depends on where the
# body came from, and one-step T cannot see it.
RIFF_CYCLE: Tuple[int, ...] = (R1, R0, R2, R0)
RIFF_CELLS = (R0, R1, R2)

KINDS: List[int] = [KIND_EMPTY] * N_CELLS_PARK
for _h in HAZARDS:
    KINDS[_h] = KIND_THREAT
KINDS[GOAL] = KIND_GOAL

# The corridor, as one table. `avoid` at the hazard steps *past* it rather
# than back: sidestepping and carrying on, so a body that has learned the
# hazard laps the park instead of pumping a reward against it.
BASE_APPROACH: Dict[int, int] = {
    S0: S1, S1: H1, H1: S3, S3: H2, H2: S5, S5: H3, H3: S7,
    S7: GOAL, GOAL: S0, D1: S1, D2: GOAL,
}
BASE_AVOID: Dict[int, int] = {
    S0: S0, S1: S0, H1: S3, S3: S1, H2: S5, S5: S3, H3: S7,
    S7: S5, GOAL: S7, D1: S0, D2: S5,
}

PARK_A, PARK_B, PARK_C, PARK_VOID = "park_a", "park_b", "park_c", "park_void"
LAYOUTS = (PARK_A, PARK_B, PARK_C)

# The only thing a layout is: a handful of moved edges. No kind changes,
# no seed, no colour, no starting position — physics.
EDITS: Dict[str, Dict[int, int]] = {
    PARK_A: {},
    PARK_B: {S0: D1},              # the walk out of the seat gains a step
    PARK_C: {S7: D2},              # and B's edge goes back to what it was
    PARK_VOID: {},
}

SCHOOL_TURNS = 512
RIFF_TURNS = 96
WINDOW_TURNS = 64
PROBE_STEPS = 24
SEAT = S0
# Declared before the exam, identical for both arms of each border, and a
# multiple of EPS_PERIOD so the exploration phase lines up exactly.
TURN_BASE = {PARK_B: 10_000, PARK_C: 20_000}

CORE_MODULES = ("loop", "pattern", "qtable", "world", "gate", "encoder")


def approach_table(layout: str) -> Dict[int, int]:
    table = dict(BASE_APPROACH)
    table.update(EDITS[layout])
    return table


def riff_table() -> Dict[Tuple[int, int], int]:
    """(prev, cur) → next, off the cycle. The same in every layout."""
    return pattern0.successors_of(RIFF_CYCLE)


def physics_differences(one: str, other: str) -> List[Tuple[int, int]]:
    """(cell, action) whose successor is not the same in the two layouts.

    Counted off the tables rather than claimed. The riff is shared by
    construction and contributes nothing here, which is the point: what
    moves between parks is the corridor, and the regularity does not.
    """
    out: List[Tuple[int, int]] = []
    a, b = approach_table(one), approach_table(other)
    for cell in sorted(set(a) | set(b)):
        if a.get(cell) != b.get(cell):
            out.append((cell, ACTION_APPROACH))
    return out


class ParkEnv:
    """One park, three layouts, and a riff that is the same in all of them.

    The env contract only: `cell()`, `step()`, `reset()`, `teleport()`,
    `reveal()` and `kind`. Nothing here is read by the loop except through
    that contract, and the loop is not told which layout it is standing in.
    """

    def __init__(self, layout: str = PARK_A, seed: int = BENCH_SEED,
                 void: bool = False) -> None:
        if layout not in EDITS:
            raise ValueError(f"unknown layout: {layout}")
        self.layout = layout
        self.seed = int(seed)
        self.void = bool(void)
        self.approach = approach_table(layout)
        self.avoid = dict(BASE_AVOID)
        # The age control's park: the same walk and the same mileage, with
        # no hazard and no prize. It has **no riff at all** — an earlier
        # version claimed one "whose successors alternate", and that was a
        # dead claim: `aged_agent` never teleports into R0/R1/R2 and the
        # alternating branch returned `options[0]` every time, so nothing
        # alternated and nothing ran. A control regularity asserted but
        # not executed is worse than none, so it is gone; that the aged
        # body never touches the riff is a measured fact, not a promise.
        self.kind: List[int] = ([KIND_EMPTY] * N_CELLS_PARK if self.void
                                else list(KINDS))
        self.riff = ({} if self.void else riff_table())
        self.hidden_bit = True
        self.last_reward = 0
        self.reset()

    def reset(self) -> None:
        self.i = SEAT
        self.prev = GOAL  # the seat's predecessor on the lap
        self.last_reward = 0

    def cell(self) -> Cell:
        return Cell(index=self.i, kind=self.kind[self.i])

    def teleport(self, i: int, prev: Optional[int] = None) -> Cell:
        self.i = int(i) % N_CELLS_PARK
        if prev is not None:
            self.prev = int(prev) % N_CELLS_PARK
        return self.cell()

    def _successor(self, aa: int) -> int:
        key = (self.prev, self.i)
        if aa == ACTION_APPROACH:
            if key in self.riff:
                return self.riff[key]
            return self.approach.get(self.i, self.i)
        if aa == ACTION_AVOID:
            if self.i in RIFF_CELLS:
                return self.i
            return self.avoid.get(self.i, self.i)
        return self.i

    def step(self, a: int):
        aa = int(a) % N_ACTIONS
        r = _reward(self.kind[self.i], aa, self.hidden_bit)
        nxt = self._successor(aa)
        # Standing still does not change where the body came from, so a
        # pause does not break the riff's context.
        if nxt != self.i:
            self.prev = self.i
        self.i = nxt
        self.last_reward = int(r)
        return r, self.cell()

    def reveal(self, extract: str) -> bool:
        """Nothing hidden here. Part of the contract, and honest."""
        return False


def slot_of(ag, index: int, kind: Optional[int] = None) -> int:
    """This agent's own slot for that packet, or -1. Allocates nothing."""
    k = KINDS[index] if kind is None else kind
    return ag.cam.get(encode_cell(index, k))


def new_agent(pattern_on: bool = True):
    """The default animal, plus the opt-in extension and nothing else."""
    from echoai.nexus0.loop import Agent

    return Agent(ask=False, pattern_memory=pattern_on,
                 env=ParkEnv(PARK_A))


def _walk(ag, turns: int, base: int = 0) -> dict:
    """`turns` turns from wherever the body is, with declared turn values.

    The turn values and the entry cell come back with the numbers. Whether
    two arms were matched is a property of the protocol, not of the result
    — in this park the exploration phase happens not to change the reward,
    so a control run on different turns would look identical and no number
    would notice. The fingerprint does.
    """
    entry_cell = ag.env.cell().index
    used: List[int] = []
    total = 0
    hazard_approaches = 0
    hazard_sidesteps = 0
    goals = 0
    for i in range(turns):
        here = ag.env.cell().index
        used.append(base + i)
        a = ag.turn(base + i)
        r = int(ag.env.last_reward)
        total += r
        if here in HAZARDS:
            hazard_approaches += int(int(a) % N_ACTIONS == ACTION_APPROACH)
            hazard_sidesteps += int(int(a) % N_ACTIONS == ACTION_AVOID)
        if here == GOAL and int(a) % N_ACTIONS == ACTION_APPROACH:
            goals += 1
    return {"reward": total, "turns": turns, "goals": goals,
            "hazard_approaches": hazard_approaches,
            "hazard_sidesteps": hazard_sidesteps,
            "entry_cell": entry_cell,
            "turn_first": used[0] if used else None,
            "turn_last": used[-1] if used else None,
            "turn_fingerprint": sum(used)}


def aged_agent(prior_turns: int):
    """The same mileage, in a park with nothing in it.

    No hazard, no prize, and no riff: this body walks the corridor and
    never teleports into R0/R1/R2, which is what the tests measure rather
    than what this docstring asserts. A fresh one per border, with exactly
    the turns the taught animal has taken by that point — an age control
    that had already walked the previous border would be carrying the very
    knowledge it exists to rule out, which is what the first version did.
    """
    ag = new_agent()
    ag.env = ParkEnv(PARK_VOID, void=True)
    ag.env.reset()
    ag.clear_context()
    _walk(ag, prior_turns)
    return ag


def school(ag, layout: str = PARK_A, void: bool = False) -> dict:
    """The corridor, then the riff. The only place anything is taught."""
    ag.env = ParkEnv(layout, void=void)
    ag.env.reset()
    ag.clear_context()
    corridor = _walk(ag, SCHOOL_TURNS)
    # The riff is entered by teleport — the corridor does not lead into
    # it — so the latch is dropped: a transition may not begin in the
    # corridor and end in the riff.
    ag.env.teleport(R0, prev=R1)
    ag.clear_context()
    riff = _walk(ag, RIFF_TURNS, base=SCHOOL_TURNS)
    return {"corridor": corridor, "riff": riff}


def cross_into(ag, layout: str) -> None:
    """A border. `ag.env` is replaced and the latch is dropped.

    Nothing else. CAM, Q, T and the pattern memory are the same four
    objects on the other side — that is the whole claim, and `identities`
    below is what checks it.
    """
    ag.env = ParkEnv(layout)
    ag.env.teleport(SEAT, prev=GOAL)
    ag.clear_context()


def is_same_body(ag, original) -> bool:
    """`is`, and nothing else.

    Four identical memories grafted into a new `Agent` are four identical
    memories in a new body: `identities()` cannot tell them apart, because
    it only looks at what the body is carrying. This looks at the body.
    """
    return ag is original


def identities(ag) -> Dict[str, int]:
    return {"cam": id(ag.cam), "q": id(ag.q), "t": id(ag.t),
            "pattern": id(ag.pattern_memory)}


def protocol_signature(ag) -> Dict[str, Any]:
    """Everything two arms have to agree on to be a matched pair.

    Deterministic values, no ids. The layout is deliberately absent: it is
    the one thing the age arm is *supposed* to differ by. `matched_flags`
    used to compare the taught animal against a bare `Agent()` that took
    no part in the experiment, so a scratch born with `ask=True`,
    `cortex=True` and no pattern memory would have gone unnoticed.
    """
    return {
        "n_actions": int(ag.n_actions),
        "ask_enabled": bool(ag.ask_enabled),
        "cortex_enabled": bool(ag.cortex_enabled),
        "pattern_memory": ag.pattern_memory is not None,
        "plan_depth": int(ag.plan_depth),
        "escalate_enabled": bool(ag.escalate_enabled),
        "conflict_attend": bool(ag.conflict_attend),
        "q_trace": bool(ag.q.trace),
        "q_remainder": bool(ag.q.remainder),
        "q_explore_flat": bool(ag.q.explore_flat),
        "q_width": int(ag.q.n_actions),
        "env_seed": int(ag.env.seed),
        "window_turns": WINDOW_TURNS,
    }


def signatures_match(signatures: Dict[str, Dict[str, Any]]) -> bool:
    """All the arms are the same kind of animal. One authority, testable."""
    return len({json.dumps(v, sort_keys=True)
                for v in signatures.values()}) <= 1


def arm_metrics(ag) -> Dict[str, int]:
    """What an arm did to the invariants. Summed over every arm that ran."""
    return {
        "false_facts": int(ag.metrics.false_facts),
        "destroyed": int(ag.metrics.destroyed),
        "cortex_calls": int(ag.metrics.cortex_calls),
        "cortex_rejected": int(ag.metrics.cortex_rejected),
        "questions": int(ag.metrics.questions),
    }


def t_rows_against(ag, layout: str) -> dict:
    """What T holds about this layout, before a single turn is taken in it.

    Rows that still describe the new park, and rows that do not. Both are
    counted off T and the layout's own table — a border that contradicted
    nothing would not be a border, and one that contradicted everything
    would not be a transfer.
    """
    table = approach_table(layout)
    known = agree = 0
    wrong: List[int] = []
    for cell, nxt in sorted(table.items()):
        s = slot_of(ag, cell)
        if s < 0:
            continue
        pred = ag.t.predict(s, ACTION_APPROACH)
        if pred is None:
            continue
        known += 1
        target = slot_of(ag, nxt)
        if target >= 0 and pred == target:
            agree += 1
        else:
            wrong.append(cell)
    return {"known": known, "agree": agree, "contradicted": len(wrong),
            "contradicted_cells": wrong}


def riff_points(layout: str = PARK_A) -> List[Tuple[int, int, int, int]]:
    """(prev_cell, cell, action, next_cell) walked off the riff itself.

    The same physical points for both arms; each maps them through its own
    CAM. Generated from the rule, not replayed from anybody's training.
    """
    out: List[Tuple[int, int, int, int]] = []
    for phase in range(len(RIFF_CYCLE)):
        env = ParkEnv(layout)
        env.teleport(RIFF_CYCLE[phase], prev=RIFF_CYCLE[phase - 1])
        for _ in range(PROBE_STEPS):
            prev_cell, cur_cell = env.prev, env.i
            env.step(ACTION_APPROACH)
            out.append((prev_cell, cur_cell, ACTION_APPROACH, env.i))
    return out


def probe(ag, points) -> dict:
    """Ask the frozen memory, then reveal. No reward, no write, no learning.

    `None` is a miss and stays in the denominator: a memory that answers
    nothing has not tied with one that answers right.
    """
    before = ag.pattern_memory.observations
    hits = unknown = 0
    for prev_cell, cur_cell, action, nxt_cell in points:
        prev = slot_of(ag, prev_cell)
        cur = slot_of(ag, cur_cell)
        guess = ag.pattern_memory.predict(prev, cur, action)
        target = slot_of(ag, nxt_cell)
        if guess is None:
            unknown += 1
        elif target >= 0 and guess == target:
            hits += 1
    return {"points": len(points), "hits": hits, "unknown": unknown,
            "observes": ag.pattern_memory.observations - before}


WORLD_NAMES = frozenset(set(LAYOUTS) | {PARK_VOID, "PARK_A", "PARK_B",
                                        "PARK_C", "PARK_VOID",
                                        "park_a", "park_b", "park_c"})
# What a world calls itself, however it is spelled. A core module that
# reads any of these off the env is branching on a world's name even if
# no park is named in its source.
# `level` is deliberately not here: `escalate.level` is the ladder
# rung and has nothing to do with a world's name — a check that
# flagged it would be measuring the wrong thing loudly.
WORLD_LABEL_FIELDS = ("layout", "park", "world_name", "world_id")


def world_name_branches(sources: Dict[str, str]) -> List[str]:
    """No module of the animal may know what a park is called.

    Two rules, and only two, because a third was dead. A string constant,
    an identifier and an attribute spelling a layout's name are all *text*
    in the source, so the sweep below subsumes every AST check of that
    kind and no mutant could tell them apart; the AST rule that survives
    is a different question — whether the module asks the world what it is
    called, which it can do without naming any park.

    Takes the sources so the check itself can be shown a module that does
    branch: a scan only ever run on clean files has not been tested.
    """
    out: List[str] = []
    for mod, source in sorted(sources.items()):
        for name in sorted(WORLD_NAMES):
            if name in source:
                out.append(f"{mod}: menciona {name}")
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Attribute) and node.attr in WORLD_LABEL_FIELDS:
                out.append(f"{mod}: lee `{node.attr}` del mundo")
    return sorted(set(out))


def core_sources() -> Dict[str, str]:
    here = Path(__file__).resolve().parent
    return {f"{mod}.py": (here / f"{mod}.py").read_text(encoding="utf-8")
            for mod in CORE_MODULES}


def resolve_points(ag, points) -> List[Tuple[int, int, int, int]]:
    """The riff's points as integer tuples, through one CAM that knows them.

    This is what makes the ablation below perceptually matched. The
    original scratch row scores 0/96, and that zero is fully explained by
    its CAM having no slot for R0/R1/R2 — it never gets as far as asking
    the pattern memory anything. To isolate the memory's *own* usefulness
    the two arms have to be handed the same resolved integers.
    """
    return [(slot_of(ag, prev), slot_of(ag, cur), action, slot_of(ag, nxt))
            for prev, cur, action, nxt in points]


def probe_resolved(memory, resolved) -> dict:
    """Ask one memory about already-resolved tuples. Writes nothing.

    `None` is a miss and stays in the denominator: a memory that says
    nothing has not drawn with one that says the right thing.
    """
    before = memory.observations
    hits = unknown = 0
    for prev, cur, action, nxt in resolved:
        guess = memory.predict(prev, cur, action)
        if guess is None:
            unknown += 1
        elif guess == nxt:
            hits += 1
    return {"points": len(resolved), "hits": hits, "unknown": unknown,
            "observes": memory.observations - before}


def known_slots(resolved) -> int:
    """Tuples every one of whose four slots this CAM could resolve."""
    return sum(1 for row in resolved if min(row[0], row[1], row[3]) >= 0)


def ablation(ag, points) -> dict:
    """The trained memory against an empty one, on identical integers.

    Same tuples, same targets, same number of resolvable slots, and
    neither probe may write anything anywhere.
    """
    resolved = resolve_points(ag, points)
    empty = pattern.PatternMemory()
    trained_probe = probe_resolved(ag.pattern_memory, resolved)
    empty_probe = probe_resolved(empty, resolved)
    return {
        "points": len(resolved),
        "known_slots": known_slots(resolved),
        "mapping_matched": known_slots(resolved) == len(resolved),
        "trained": trained_probe,
        "empty": empty_probe,
        "writes": trained_probe["observes"] + empty_probe["observes"],
    }


def channel_audit(turns: int = 64, skip_at: Optional[int] = None,
                  leak_at_slot: Optional[int] = None) -> dict:
    """Does the pattern memory get exactly what T gets?

    Recorded from the real calls, on a real run, with one `clear_context`
    in the middle. The rule the loop implements is: after a cut, Pattern
    skips exactly the first transition (it has no `prev_slot` yet), and
    every other transition reaches both — with the same
    `(slot, action, next_slot)` in the same order.

    The mutant this replaces built an empty memory and compared it with a
    trained one, which audits nothing about the channel.
    """
    ag = new_agent()
    ag.env = ParkEnv(PARK_A)
    ag.env.reset()
    ag.clear_context()
    cut_at = [0, turns // 2]

    t_calls: List[Tuple[int, int, int, int]] = []
    p_calls: List[Tuple[int, int, int, int, int]] = []
    cursor = {"turn": -1}
    real_t, real_p = ag.t.observe, ag.pattern_memory.observe

    def watch_t(s, a, n):
        t_calls.append((cursor["turn"], int(s), int(a), int(n)))
        return real_t(s, a, n)

    def watch_p(prev, s, a, n):
        # `skip_at` drops exactly one transition on its way to the memory:
        # the audit has to be able to come back false, or it is a rule
        # nothing can violate.
        if skip_at is not None and len(p_calls) == int(skip_at):
            p_calls.append((cursor["turn"], -1, -1, -1, -1))
            return None
        p_calls.append((cursor["turn"], int(prev), int(s), int(a), int(n)))
        return real_p(prev, s, a, n)

    ag.t.observe = watch_t
    ag.pattern_memory.observe = watch_p
    for i in range(turns):
        if i in cut_at and i:
            ag.clear_context()
        cursor["turn"] = i
        ag.turn(i)
    ag.t.observe, ag.pattern_memory.observe = real_t, real_p

    # The first T call at or after each cut is the one Pattern must skip.
    skipped = set()
    for cut in cut_at:
        later = [turn for turn, *_ in t_calls if turn >= cut]
        if later:
            skipped.add(min(later))
    expected = [(s, a, n) for turn, s, a, n in t_calls if turn not in skipped]
    got = [(s, a, n) for _turn, _prev, s, a, n in p_calls]

    # And a self model that refuses a step must silence both of them.
    class _Refuses:
        def observe_step(self, slot, a, slot_n):
            return False

    # Both counters, from the real calls. Comparing `quiet.t.pred[0]`
    # before and after was not an audit: that one arbitrary row can sit
    # unchanged while T learns in any of the other 4095 slots, which is
    # exactly what `leak_at_slot` below does on purpose.
    quiet = new_agent()
    quiet.env = ParkEnv(PARK_A)
    quiet.env.reset()
    quiet.clear_context()
    quiet.self_model = _Refuses()
    refused_t: List[tuple] = []
    refused_p: List[tuple] = []
    quiet_t, quiet_p = quiet.t.observe, quiet.pattern_memory.observe

    def watch_quiet_t(s, a, n):
        refused_t.append((int(s), int(a), int(n)))
        return quiet_t(s, a, n)

    def watch_quiet_p(prev, s, a, n):
        refused_p.append((int(prev), int(s), int(a), int(n)))
        return quiet_p(prev, s, a, n)

    quiet.t.observe = watch_quiet_t
    quiet.pattern_memory.observe = watch_quiet_p
    for i in range(8):
        quiet.turn(i)
    if leak_at_slot is not None:
        # A transition reaching T after the refusal, in a slot the old
        # check never looked at.
        quiet.t.observe(int(leak_at_slot), 0, int(leak_at_slot))
    quiet.t.observe, quiet.pattern_memory.observe = quiet_t, quiet_p
    # No `matches` here: a conjunction beside its own conjuncts is a
    # second way of saying the same thing, and hardcoding it to True
    # changed no test. The verdict is derived once, in `experiment`.
    return {
        "turns": turns,
        "cuts": len(cut_at),
        "skipped_one": skip_at is not None,
        "t_observations": len(t_calls),
        "pattern_observations": len(p_calls),
        "skipped_after_cuts": sorted(skipped),
        "counts_match": len(got) == len(expected),
        "projection_matches": got == expected,
        "refused_t_observations": len(refused_t),
        "refused_pattern_observations": len(refused_p),
        "refused_step_silences_both": bool(
            not refused_t and not refused_p),
    }


def core_world_name_branches() -> List[str]:
    return world_name_branches(core_sources())


# --- one border, both arms, matched ------------------------------------
def border(taught, layout: str, points, void_agent=None,
           original=None) -> dict:
    """The transferred animal and a scratch birth, on the same terms.

    Same env class and layout, same seed, same seat and physical state on
    entry, same flags, same number of actions, same turns — and the same
    `turn` values handed to the policy, so the ε phase cannot pay for the
    result. Both are probed with every memory frozen *before* either takes
    a turn here.
    """
    base = TURN_BASE[layout]
    before = identities(taught)
    cross_into(taught, layout)
    t_rows = t_rows_against(taught, layout)

    scratch = new_agent()
    cross_into(scratch, layout)
    if void_agent is not None:
        cross_into(void_agent, layout)

    # The signatures of the arms that actually run, taken before any of
    # them takes a turn. The layout is not in them: it is what the age
    # arm is meant to differ by.
    arms = {"transfer": taught, "scratch": scratch}
    if void_agent is not None:
        arms["age"] = void_agent
    signatures = {k: protocol_signature(v) for k, v in arms.items()}

    probes = {"transfer": probe(taught, points), "scratch": probe(scratch, points)}
    if void_agent is not None:
        probes["age"] = probe(void_agent, points)
    # The perceptually matched one: same resolved integers for both.
    matched = ablation(taught, points)

    transfer = _walk(taught, WINDOW_TURNS, base=base)
    control = _walk(scratch, WINDOW_TURNS, base=base)
    age = _walk(void_agent, WINDOW_TURNS, base=base) if void_agent else None

    return {
        "layout": layout,
        "turn_base": base,
        "same_agent_object": bool(
            original is None or is_same_body(taught, original)),
        "protocol_signatures": signatures,
        "protocol_signatures_match": signatures_match(signatures),
        "arm_metrics": {k: arm_metrics(v) for k, v in arms.items()},
        "ablation": matched,
        "matched_turn_values": bool(
            transfer["turn_first"] == control["turn_first"]
            and transfer["turn_last"] == control["turn_last"]
            and transfer["turn_fingerprint"] == control["turn_fingerprint"]),
        "matched_entry_cell": bool(
            transfer["entry_cell"] == control["entry_cell"] == SEAT),
        "window_turns": WINDOW_TURNS,
        "seat": SEAT,
        "identities_before": before,
        "identities_after": identities(taught),
        "same_objects": before == identities(taught),
        "t_rows_on_entry": t_rows,
        "transfer": transfer,
        "scratch": control,
        "age": age,
        "gain": transfer["reward"] - control["reward"],
        "age_gain": (age["reward"] - control["reward"]) if age else 0,
        "pattern": probes,
    }


# --- the battery --------------------------------------------------------
REQUIRED_MUTANTS = (
    "nace un Agent nuevo al entrar en B",
    "nace un Agent nuevo al entrar en C",
    "copia las tablas a otro Agent y lo llama el mismo",
    "Agent nuevo con las cuatro memorias antiguas injertadas",
    "gain_B positivo pero desligado de las restas",
    "gain_C positivo pero desligado de las restas",
    "el scratch nace sin PatternMemory",
    "el scratch nace con cortex y ask encendidos",
    "el scratch nace con otro remainder o explore_flat",
    "el control de edad nace con otros flags",
    "el scratch nace con otra semilla",
    "la ablación cita una CAM que no resuelve",
    "una transición se le quita a PatternMemory",
    "borra CAM en una frontera",
    "borra Q en una frontera",
    "borra T en una frontera",
    "borra PatternMemory en una frontera",
    "no limpia prev_slot y cose dos mundos",
    "PatternMemory no recibe las mismas transiciones que T",
    "la sonda aprende durante el examen",
    "None cuenta como acierto",
    "los no cubiertos salen del denominador",
    "transfer y scratch en turnos distintos",
    "scratch entra desde otro asiento",
    "scratch usa otra fase de exploración",
    "el total esconde gain_B <= 0",
    "el total esconde gain_C <= 0",
    "PARK_C repite la física de PARK_B",
    "una rama por nombre de mundo en el core",
    "el control de edad recibe la regularidad verdadera",
    "las filas crudas desaparecen del informe",
    "una fila cruda dice que el cuerpo no es el mismo",
    "la firma cruda del scratch difiere",
    "un scratch registra una llamada al córtex",
    "un brazo registra un rechazo del córtex",
    "la ablación cruda dice que no está emparejada",
    "el canal crudo dice que la proyección no cuadra",
    "tras el rechazo T observa fuera de la fila cero",
    "el contador de rechazo contradice su resumen",
    "los tres brazos pierden la misma clave de la firma",
    "los tres brazos incumplen el protocolo por igual",
    "el predictor vacío deja de declarar sus None",
    "una ablación de 95 puntos junto a una sonda de 96",
    "sólo turn_first cambia y matched sigue en true",
    "sólo el fingerprint cambia",
    "sólo el asiento del brazo de edad cambia",
    "una sonda declara hits mayores que sus puntos",
    "una sonda declara un contador booleano",
    "la ablación declara una escritura",
    "el informe borra un mutante requerido",
    "un mutante futuro vivo con contadores mentirosos",
)


def battery_state(battery: Any) -> dict:
    """Recounted from the list. TALK-1c's discipline, from the start."""
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


def mutants(rows: Dict[str, dict], points) -> List[dict]:
    """A counterexample per claim, each an actual run or an actual scan."""
    from echoai.core.cam import Cam

    from echoai.nexus0.qtable import QTable
    from echoai.nexus0.world import World

    out: List[dict] = []

    def note(name: str, killed: bool, evidence) -> None:
        out.append({"mutant": name, "killed": bool(killed),
                    "evidence": evidence})

    honest = {k: rows[k]["gain"] for k in (PARK_B, PARK_C)}

    # 1, 2 — a new birth at each border is not the same animal.
    for layout in (PARK_B, PARK_C):
        taught = new_agent()
        school(taught)
        before = identities(taught)
        fresh = new_agent()
        cross_into(fresh, layout)
        label = "B" if layout == PARK_B else "C"
        note(f"nace un Agent nuevo al entrar en {label}",
             identities(fresh) != before,
             {"before": sorted(before), "after_is_a_new_object": True})

    # 3 — snapshots copied into another body. Resemblance is not identity.
    taught = new_agent()
    school(taught)
    twin = new_agent()
    twin.q.load_rows([taught.q.row(i) for i in range(len(taught.q.q))])
    note("copia las tablas a otro Agent y lo llama el mismo",
         identities(twin) != identities(taught),
         {"rows_copied": True, "same_objects": False})

    # 3b — a new body with the four old memories grafted in. Every
    # `identities()` check passes; only `is` sees it.
    grafted = new_agent()
    grafted.cam, grafted.q = taught.cam, taught.q
    grafted.t, grafted.pattern_memory = taught.t, taught.pattern_memory
    note("Agent nuevo con las cuatro memorias antiguas injertadas",
         identities(grafted) == identities(taught)
         and not is_same_body(grafted, taught),
         {"identities_iguales": True, "same_agent_object": False})

    # 3c — gains that are positive and are not the differences.
    for label in ("B", "C"):
        bent = _report_shape(rows)
        bent[f"gain_{label}"] = 1
        bent["aggregate_transfer_gain"] = bent["gain_B"] + bent["gain_C"]
        bent["gains_equal_reward_differences"] = False
        note(f"gain_{label} positivo pero desligado de las restas",
             not green(bent) and bent[f"gain_{label}"] > 0,
             {"gain": bent[f"gain_{label}"],
              "resta": bent[f"transfer_reward_{label}"]
              - bent[f"scratch_reward_{label}"]})

    # 3d — arms that are not the same kind of animal.
    honest_sig = protocol_signature(new_agent())
    for label, build in (
            ("el scratch nace sin PatternMemory",
             lambda: new_agent(pattern_on=False)),
            ("el scratch nace con cortex y ask encendidos",
             lambda: __import__("echoai.nexus0.loop", fromlist=["Agent"])
             .Agent(ask=True, cortex=True, pattern_memory=True,
                    env=ParkEnv(PARK_A))),
            ("el scratch nace con otro remainder o explore_flat",
             lambda: __import__("echoai.nexus0.loop", fromlist=["Agent"])
             .Agent(ask=False, pattern_memory=True, explore_flat=True,
                    env=ParkEnv(PARK_A))),
            ("el control de edad nace con otros flags",
             lambda: __import__("echoai.nexus0.loop", fromlist=["Agent"])
             .Agent(ask=False, pattern_memory=True, plan_depth=2,
                    env=ParkEnv(PARK_VOID, void=True))),
            ("el scratch nace con otra semilla",
             lambda: __import__("echoai.nexus0.loop", fromlist=["Agent"])
             .Agent(ask=False, pattern_memory=True,
                    env=ParkEnv(PARK_A, seed=1)))):
        odd = build()
        note(label, protocol_signature(odd) != honest_sig,
             {"campos_distintos": sorted(
                 k for k in honest_sig
                 if protocol_signature(odd)[k] != honest_sig[k])})

    # 3e — an ablation that is not perceptually matched.
    blind = ablation(new_agent(), points)
    note("la ablación cita una CAM que no resuelve",
         not blind["mapping_matched"] and blind["trained"]["hits"] == 0
         and rows[PARK_B]["ablation"]["mapping_matched"],
         {"known_slots": blind["known_slots"], "points": blind["points"],
          "trained_hits": blind["trained"]["hits"]})

    # 4-7 — a memory quietly replaced at the border.
    for label, field, factory in (("CAM", "cam", Cam), ("Q", "q", QTable),
                                  ("T", "t", World),
                                  ("PatternMemory", "pattern_memory",
                                   pattern.PatternMemory)):
        wiped = new_agent()
        school(wiped)
        before = identities(wiped)
        cross_into(wiped, PARK_B)
        setattr(wiped, field, factory())
        walked = _walk(wiped, WINDOW_TURNS, base=TURN_BASE[PARK_B])
        note(f"borra {label} en una frontera",
             identities(wiped) != before,
             {"gain_after": walked["reward"] - rows[PARK_B]["scratch"]["reward"],
              "identity_broken": True})

    # 8 — the latch left standing, so a transition begins in one park and
    # ends in another.
    sewn = new_agent()
    school(sewn)
    size_before = sewn.pattern_memory.size
    sewn.env = ParkEnv(PARK_B)
    sewn.env.teleport(SEAT, prev=GOAL)   # no clear_context()
    sewn.turn(TURN_BASE[PARK_B])
    sewn_size = sewn.pattern_memory.size
    clean = new_agent()
    school(clean)
    cross_into(clean, PARK_B)
    clean.turn(TURN_BASE[PARK_B])
    note("no limpia prev_slot y cose dos mundos",
         sewn_size > clean.pattern_memory.size,
         {"con_latch": sewn_size, "sin_latch": clean.pattern_memory.size,
          "antes": size_before})

    # 9 — the channel itself, audited from the real calls. The version
    # this replaces built an empty memory and compared it with a trained
    # one, which audits nothing about what either was fed.
    audit = channel_audit()
    note("PatternMemory no recibe las mismas transiciones que T",
         audit["counts_match"] and audit["projection_matches"]
         and audit["refused_step_silences_both"]
         and audit["pattern_observations"]
         == audit["t_observations"] - audit["cuts"],
         {k: audit[k] for k in ("t_observations", "pattern_observations",
                                "skipped_after_cuts", "counts_match",
                                "projection_matches",
                                "refused_step_silences_both")})
    # and one transition taken away from Pattern without turning it off
    thin = new_agent()
    thin.env = ParkEnv(PARK_A)
    thin.env.reset()
    thin.clear_context()
    real_p = thin.pattern_memory.observe
    seen = {"n": 0}

    def skip_one(prev, s, a, n):
        seen["n"] += 1
        if seen["n"] == 5:
            return None       # the mutant: one transition never arrives
        return real_p(prev, s, a, n)

    thin.pattern_memory.observe = skip_one
    for i in range(32):
        thin.turn(i)
    thin.pattern_memory.observe = real_p
    full = new_agent()
    full.env = ParkEnv(PARK_A)
    full.env.reset()
    full.clear_context()
    for i in range(32):
        full.turn(i)
    note("una transición se le quita a PatternMemory",
         thin.pattern_memory.snapshot_hash()
         != full.pattern_memory.snapshot_hash(),
         {"observadas_completa": full.pattern_memory.observations,
          "observadas_recortada": thin.pattern_memory.observations})

    # 10 — a probe that learns is not a probe.
    leaky = new_agent()
    school(leaky)
    before_obs = leaky.pattern_memory.observations
    for prev_cell, cur_cell, action, nxt_cell in points[:8]:
        leaky.pattern_memory.observe(slot_of(leaky, prev_cell),
                                     slot_of(leaky, cur_cell), action,
                                     slot_of(leaky, nxt_cell))
    note("la sonda aprende durante el examen",
         leaky.pattern_memory.observations > before_obs
         and rows[PARK_B]["pattern"]["transfer"]["observes"] == 0,
         {"sonda_honesta": rows[PARK_B]["pattern"]["transfer"]["observes"],
          "sonda_con_fuga": leaky.pattern_memory.observations - before_obs})

    # 11, 12 — None as a hit, and the denominator shrunk to fit.
    bent_scratch = (rows[PARK_B]["pattern"]["scratch"]["hits"]
                    + rows[PARK_B]["pattern"]["scratch"]["unknown"])
    note("None cuenta como acierto",
         bent_scratch >= rows[PARK_B]["pattern"]["transfer"]["hits"],
         {"scratch_con_None": bent_scratch,
          "transfer": rows[PARK_B]["pattern"]["transfer"]["hits"]})
    covered = (rows[PARK_B]["pattern"]["scratch"]["points"]
               - rows[PARK_B]["pattern"]["scratch"]["unknown"])
    note("los no cubiertos salen del denominador", covered == 0,
         {"denominador_recortado": covered,
          "denominador_real": rows[PARK_B]["pattern"]["scratch"]["points"]})

    # 13, 14, 15 — an unmatched control.
    matched = rows[PARK_B]["scratch"]
    for label, seat, base, field in (
            ("transfer y scratch en turnos distintos", SEAT,
             TURN_BASE[PARK_B] + 64, "turn_fingerprint"),
            ("scratch entra desde otro asiento", S5,
             TURN_BASE[PARK_B], "entry_cell"),
            ("scratch usa otra fase de exploración", SEAT,
             TURN_BASE[PARK_B] + 3, "turn_fingerprint")):
        odd = new_agent()
        odd.env = ParkEnv(PARK_B)
        odd.env.teleport(seat, prev=GOAL)
        odd.clear_context()
        walked = _walk(odd, WINDOW_TURNS, base=base)
        # Checked on the protocol, not on the outcome: here the ε phase
        # does not move the reward, so an unmatched control would score
        # the same and no number would notice.
        note(label, walked[field] != matched[field],
             {"campo": field, "desemparejado": walked[field],
              "emparejado": matched[field],
              "reward_desemparejado": walked["reward"],
              "reward_emparejado": matched["reward"]})

    # 16, 17 — a positive total hiding a zero.
    for layout, label in ((PARK_B, "B"), (PARK_C, "C")):
        bent = _report_shape(rows)
        bent[f"transfer_reward_{label}"] = bent[f"scratch_reward_{label}"]
        bent[f"gain_{label}"] = 0
        bent["aggregate_transfer_gain"] = bent["gain_B"] + bent["gain_C"]
        note(f"el total esconde gain_{label} <= 0",
             not green(bent) and bent["aggregate_transfer_gain"] > 0,
             {"gain_B": bent["gain_B"], "gain_C": bent["gain_C"],
              "agregado": bent["aggregate_transfer_gain"]})

    # 18 — a second border that is not one.
    note("PARK_C repite la física de PARK_B",
         bool(physics_differences(PARK_B, PARK_C))
         and not physics_differences(PARK_B, PARK_B),
         {"B_C": physics_differences(PARK_B, PARK_C),
          "B_B": physics_differences(PARK_B, PARK_B)})

    # 19 — the animal reading a world's name.
    dirty = world_name_branches(
        {"loop.py": "def f(layout):\n    if layout == 'park_b':\n        pass\n"})
    note("una rama por nombre de mundo en el core",
         not core_world_name_branches() and bool(dirty),
         {"real": core_world_name_branches(), "inyectado": dirty})

    # 20 — an age control that was taught the real thing after all.
    aged_wrongly = new_agent()
    school(aged_wrongly)
    cross_into(aged_wrongly, PARK_B)
    note("el control de edad recibe la regularidad verdadera",
         probe(aged_wrongly, points)["hits"] > 0
         and rows[PARK_B]["pattern"]["age"]["hits"] == 0,
         {"edad_honesta": rows[PARK_B]["pattern"]["age"]["hits"],
          "edad_con_la_regla": probe(aged_wrongly, points)["hits"]})

    # 20b — the certificate contradicting its own evidence. Every one of
    # these leaves the top-level summaries saying everything is fine.
    def raw(bend) -> bool:
        shape = _report_shape(rows)
        shape["rows"] = {k: json.loads(json.dumps(v)) for k, v in rows.items()}
        shape["arm_metrics"] = {k: json.loads(json.dumps(v["arm_metrics"]))
                                for k, v in rows.items()}
        shape["channel"] = json.loads(json.dumps(channel_audit()))
        bend(shape)
        return not green(shape)

    note("las filas crudas desaparecen del informe",
         raw(lambda r: r.update(rows={})) and raw(lambda r: r.update(rows=None)),
         {"rows_vacías": True, "rows_None": True})
    note("una fila cruda dice que el cuerpo no es el mismo",
         raw(lambda r: r["rows"][PARK_B].update(same_agent_object=False)),
         {"fila": PARK_B})
    note("la firma cruda del scratch difiere",
         raw(lambda r: r["rows"][PARK_B]["protocol_signatures"]["scratch"]
             .update(ask_enabled=True)),
         {"campo": "ask_enabled"})
    note("un scratch registra una llamada al córtex",
         raw(lambda r: r["arm_metrics"][PARK_B]["scratch"]
             .update(cortex_calls=1)), {"brazo": "scratch"})
    note("un brazo registra un rechazo del córtex",
         raw(lambda r: r["arm_metrics"][PARK_C]["age"]
             .update(cortex_rejected=1)), {"brazo": "age"})
    note("la ablación cruda dice que no está emparejada",
         raw(lambda r: r["rows"][PARK_B]["ablation"]
             .update(mapping_matched=False)), {"fila": PARK_B})
    note("el canal crudo dice que la proyección no cuadra",
         raw(lambda r: r["channel"].update(projection_matches=False)),
         {"campo": "projection_matches"})
    leaked = channel_audit(leak_at_slot=1234)
    note("tras el rechazo T observa fuera de la fila cero",
         leaked["refused_t_observations"] > 0
         and not leaked["refused_step_silences_both"]
         and raw(lambda r: r.update(channel=leaked)),
         {"refused_t_observations": leaked["refused_t_observations"],
          "refused_pattern_observations":
              leaked["refused_pattern_observations"]})

    # 20c — the graph contradicting itself. Every one of these leaves the
    # top-level summaries saying everything is fine, and several leave the
    # row's own booleans saying it too.
    def bend_raw(bend) -> bool:
        shape = _report_shape(rows)
        shape["rows"] = json.loads(json.dumps(rows))
        shape["arm_metrics"] = {k: json.loads(json.dumps(v["arm_metrics"]))
                                for k, v in rows.items()}
        shape["channel"] = json.loads(json.dumps(channel_audit()))
        bend(shape)
        return not green(shape)

    def drop_key(r):
        for arm in ARMS:
            r["rows"][PARK_B]["protocol_signatures"][arm].pop("ask_enabled")

    def break_protocol(r):
        for layout in (PARK_B, PARK_C):
            for arm in ARMS:
                r["rows"][layout]["protocol_signatures"][arm]["ask_enabled"] = True

    def shrink_ablation(r):
        ab = r["rows"][PARK_B]["ablation"]
        ab["points"] = ab["known_slots"] = 95
        ab["trained"]["points"] = ab["empty"]["points"] = 95
        ab["trained"]["hits"] = 95
        ab["trained"]["unknown"] = 0
        ab["empty"]["unknown"] = 95
        r["pattern_probe_known_slots_B"] = 95
        r["trained_pattern_hits_B"] = 95

    for label, bend in (
        ("el contador de rechazo contradice su resumen",
         lambda r: r["channel"].update(refused_t_observations=1)),
        ("los tres brazos pierden la misma clave de la firma", drop_key),
        ("los tres brazos incumplen el protocolo por igual", break_protocol),
        ("el predictor vacío deja de declarar sus None",
         lambda r: r["rows"][PARK_B]["ablation"]["empty"].update(unknown=0)),
        ("una ablación de 95 puntos junto a una sonda de 96", shrink_ablation),
        ("sólo turn_first cambia y matched sigue en true",
         lambda r: r["rows"][PARK_B]["transfer"].update(
             turn_first=r["rows"][PARK_B]["transfer"]["turn_first"] + 1)),
        ("sólo el fingerprint cambia",
         lambda r: r["rows"][PARK_C]["scratch"].update(
             turn_fingerprint=r["rows"][PARK_C]["scratch"]["turn_fingerprint"] + 1)),
        ("sólo el asiento del brazo de edad cambia",
         lambda r: r["rows"][PARK_B]["age"].update(entry_cell=S5)),
        ("una sonda declara hits mayores que sus puntos",
         lambda r: r["rows"][PARK_B]["pattern"]["transfer"].update(hits=999)),
        ("una sonda declara un contador booleano",
         lambda r: r["rows"][PARK_C]["pattern"]["scratch"].update(observes=False)),
        ("la ablación declara una escritura",
         lambda r: r["rows"][PARK_B]["ablation"]["trained"].update(observes=1)),
    ):
        note(label, bend_raw(bend), {"resúmenes": "sin tocar"})

    # 21, 22 — the battery itself.
    shrunk = _report_shape(rows)
    shrunk["mutants"] = [m for m in shrunk["mutants"]
                         if m["mutant"] != "borra Q en una frontera"]
    shrunk["mutants_total"] = len(shrunk["mutants"])
    shrunk["mutants_killed"] = len(shrunk["mutants"])
    note("el informe borra un mutante requerido", not green(shrunk),
         {"missing": battery_state(shrunk["mutants"])["missing"]})
    future = _report_shape(rows)
    future["mutants"] = future["mutants"] + [
        {"mutant": "extra futuro vivo", "killed": False}]
    future["mutants_total"] = len(future["mutants"])
    future["mutants_killed"] = len(future["mutants"])
    note("un mutante futuro vivo con contadores mentirosos",
         not green(future),
         {"alive": battery_state(future["mutants"])["alive"]})
    del honest
    return out


def _report_shape(rows: Dict[str, dict],
                  channel: Optional[dict] = None) -> dict:
    """A green-shaped report, for bending inside the battery.

    It carries the **real** rows, arm metrics and channel: since `green()`
    recomputes from those, a shape built out of summaries alone would no
    longer pass and every bend below would be testing nothing.
    """
    audit = channel_audit() if channel is None else channel
    b, c = rows[PARK_B], rows[PARK_C]
    return {
        "rows": {k: v for k, v in rows.items()},
        "arm_metrics": {k: v["arm_metrics"] for k, v in rows.items()},
        "channel": audit,
        "all_arms_cortex_rejected": sum(
            m["cortex_rejected"] for v in rows.values()
            for m in v["arm_metrics"].values()),
        "age_control_gain_B": b["age_gain"], "age_control_gain_C": c["age_gain"],
        "pattern_transfer_hits_B": b["pattern"]["transfer"]["hits"],
        "pattern_scratch_hits_B": b["pattern"]["scratch"]["hits"],
        "pattern_transfer_hits_C": c["pattern"]["transfer"]["hits"],
        "pattern_scratch_hits_C": c["pattern"]["scratch"]["hits"],
        "worlds": len(LAYOUTS),
        "same_agent_across_worlds": True,
        "same_cam_object": True, "same_q_object": True,
        "same_t_object": True, "same_pattern_object": True,
        "same_agent_object": True,
        "gains_equal_reward_differences": True,
        "protocol_signatures_match": True,
        "all_arms_false_facts": 0, "all_arms_destroyed": 0,
        "all_arms_cortex_calls": 0,
        "pattern_probe_mapping_matched_B": True,
        "pattern_probe_mapping_matched_C": True,
        "pattern_probe_known_slots_B": b["ablation"]["known_slots"],
        "pattern_probe_known_slots_C": c["ablation"]["known_slots"],
        "trained_pattern_hits_B": b["ablation"]["trained"]["hits"],
        "trained_pattern_hits_C": c["ablation"]["trained"]["hits"],
        "empty_pattern_hits_B": b["ablation"]["empty"]["hits"],
        "empty_pattern_hits_C": c["ablation"]["empty"]["hits"],
        "pattern_probe_writes": 0,
        "pattern_channel_matches_t": True,
        "world_physics_differences_A_B": 1,
        "world_physics_differences_B_C": 2,
        "t_known_rows_on_entry_B": 9, "t_known_rows_on_entry_C": 10,
        "t_contradictions_on_entry_B": 1, "t_contradictions_on_entry_C": 1,
        "transfer_reward_B": b["transfer"]["reward"],
        "scratch_reward_B": b["scratch"]["reward"],
        "transfer_reward_C": c["transfer"]["reward"],
        "scratch_reward_C": c["scratch"]["reward"],
        "gain_B": b["gain"], "gain_C": c["gain"],
        "aggregate_transfer_gain": b["gain"] + c["gain"],
        "pattern_entry_points_B": b["pattern"]["transfer"]["points"],
        "pattern_entry_points_C": c["pattern"]["transfer"]["points"],
        "pattern_observes_during_entry_probes": 0,
        "matched_seat": True, "matched_turns": True, "matched_flags": True,
        "world_name_branches_in_core": [],
        "false_facts": 0, "destroyed": 0, "cortex_calls": 0,
        "llm_calls": 0, "human_labels": 0,
        "n_actions": N_ACTIONS, "thought_keys": len(thought.KEYS),
        "default_agent_has_pattern_memory": False,
        "mutants": [{"mutant": n, "killed": True} for n in REQUIRED_MUTANTS],
        "mutants_total": len(REQUIRED_MUTANTS),
        "mutants_killed": len(REQUIRED_MUTANTS),
    }


# --- the experiment -----------------------------------------------------
def experiment() -> dict:
    from echoai.nexus0.loop import Agent

    points = riff_points()

    # One birth. Everything after this is the same object.
    taught = new_agent()
    # A reference to the body itself, not to what it is carrying. Four
    # identical memories grafted into a new `Agent` pass every
    # `identities()` check there is; only `is` sees the difference.
    born_agent = taught
    born = identities(taught)
    schooling = school(taught)
    after_school = identities(taught)

    rows: Dict[str, dict] = {}
    mileage = SCHOOL_TURNS + RIFF_TURNS
    for layout in (PARK_B, PARK_C):
        # A fresh one per border, with exactly the turns the taught
        # animal has taken by this point. Reusing one would hand the
        # second border a control that had already walked the first —
        # and that is not hypothetical: the first version of this did
        # exactly that and scored the age control a gain of +72 at C.
        aged = aged_agent(mileage)
        rows[layout] = border(taught, layout, points, void_agent=aged,
                              original=born_agent)
        mileage += WINDOW_TURNS
    after_borders = identities(taught)

    channel = channel_audit()
    battery = mutants(rows, points)
    state = battery_state(battery)

    default = Agent()
    b, c = rows[PARK_B], rows[PARK_C]
    out: Dict[str, Any] = {
        "world": "xfer1",
        "layouts": list(LAYOUTS),
        "worlds": len(LAYOUTS),
        "cells": {"corridor": [S0, S1, H1, S3, H2, S5, H3, S7, GOAL],
                  "detours": [D1, D2], "riff": list(RIFF_CELLS)},
        "riff_cycle": list(RIFF_CYCLE),
        "school_turns": SCHOOL_TURNS, "riff_turns": RIFF_TURNS,
        "window_turns": WINDOW_TURNS, "seat": SEAT,
        "turn_base": {k: v for k, v in TURN_BASE.items()},
        "schooling": schooling,

        # --- one animal ---------------------------------------------
        # The comparison, not the addresses: `id()` values are where the
        # objects happened to land this run, and printing them would make
        # the report differ from itself between two identical runs.
        "identity_survives_school": born == after_school,
        "identity_survives_borders": after_school == after_borders,
        "identity_checks": {k: born[k] == after_borders[k] for k in born},
        "same_agent_across_worlds": bool(
            born == after_school == after_borders),
        # The body, by `is`. A separate claim from the four memories, and
        # the one the grafting counterexample breaks.
        # Decided at the border, where the border happens. `experiment`
        # only conjoins the rows: two places computing this would be two
        # ways of saying the same thing, and neither could be shown to be
        # the one doing the work.
        "same_agent_object": bool(
            all(rows[k]["same_agent_object"] for k in rows)),
        "same_cam_object": born["cam"] == after_borders["cam"],
        "same_q_object": born["q"] == after_borders["q"],
        "same_t_object": born["t"] == after_borders["t"],
        "same_pattern_object": born["pattern"] == after_borders["pattern"],

        # --- three worlds, and real physics between them -------------
        "world_physics_differences_A_B": len(
            physics_differences(PARK_A, PARK_B)),
        "world_physics_differences_B_C": len(
            physics_differences(PARK_B, PARK_C)),
        "physics_differences_A_B": physics_differences(PARK_A, PARK_B),
        "physics_differences_B_C": physics_differences(PARK_B, PARK_C),
        "t_known_rows_on_entry_B": b["t_rows_on_entry"]["known"],
        "t_known_rows_on_entry_C": c["t_rows_on_entry"]["known"],
        "t_agreements_on_entry_B": b["t_rows_on_entry"]["agree"],
        "t_agreements_on_entry_C": c["t_rows_on_entry"]["agree"],
        "t_contradictions_on_entry_B": b["t_rows_on_entry"]["contradicted"],
        "t_contradictions_on_entry_C": c["t_rows_on_entry"]["contradicted"],

        # --- the two borders, each on its own ------------------------
        "transfer_reward_B": b["transfer"]["reward"],
        "scratch_reward_B": b["scratch"]["reward"],
        "gain_B": b["gain"],
        "transfer_reward_C": c["transfer"]["reward"],
        "scratch_reward_C": c["scratch"]["reward"],
        "gain_C": c["gain"],
        "aggregate_transfer_gain": b["gain"] + c["gain"],
        "age_control_reward_B": b["age"]["reward"],
        "age_control_reward_C": c["age"]["reward"],
        "age_control_gain_B": b["age_gain"],
        "age_control_gain_C": c["age_gain"],
        "rows": {k: {kk: vv for kk, vv in v.items()
                     if kk not in ("identities_before", "identities_after")}
                 for k, v in rows.items()},

        # --- the pattern probe ---------------------------------------
        "pattern_entry_points_B": b["pattern"]["transfer"]["points"],
        "pattern_entry_points_C": c["pattern"]["transfer"]["points"],
        "pattern_transfer_hits_B": b["pattern"]["transfer"]["hits"],
        "pattern_scratch_hits_B": b["pattern"]["scratch"]["hits"],
        "pattern_transfer_hits_C": c["pattern"]["transfer"]["hits"],
        "pattern_scratch_hits_C": c["pattern"]["scratch"]["hits"],
        "pattern_age_hits_B": b["pattern"]["age"]["hits"],
        "pattern_age_hits_C": c["pattern"]["age"]["hits"],
        "pattern_unknown_B": b["pattern"]["scratch"]["unknown"],
        "pattern_observes_during_entry_probes": sum(
            v["observes"] for row in (b, c) for v in row["pattern"].values()),
        "pattern_mature_contexts": len(taught.pattern_memory.mature_counts()),
        "pattern_size": taught.pattern_memory.size,
        "pattern_capacity": taught.pattern_memory.capacity,
        "pattern_dropped": taught.pattern_memory.dropped,

        # --- matched, and it is checkable ----------------------------
        # gains, tied to the rewards they are supposed to be
        "gains_equal_reward_differences": bool(
            b["gain"] == b["transfer"]["reward"] - b["scratch"]["reward"]
            and c["gain"] == c["transfer"]["reward"] - c["scratch"]["reward"]),
        # the protocol, of the arms that ran
        "protocol_signatures_match": bool(b["protocol_signatures_match"]
                                          and c["protocol_signatures_match"]),
        "protocol_signature": b["protocol_signatures"]["transfer"],
        "arm_metrics": {k: v["arm_metrics"] for k, v in rows.items()},
        "all_arms_false_facts": sum(
            m["false_facts"] for v in rows.values()
            for m in v["arm_metrics"].values()),
        "all_arms_destroyed": sum(
            m["destroyed"] for v in rows.values()
            for m in v["arm_metrics"].values()),
        "all_arms_cortex_calls": sum(
            m["cortex_calls"] for v in rows.values()
            for m in v["arm_metrics"].values()),
        "all_arms_cortex_rejected": sum(
            m["cortex_rejected"] for v in rows.values()
            for m in v["arm_metrics"].values()),
        # the ablation, perceptually matched
        "pattern_probe_mapping_matched_B": b["ablation"]["mapping_matched"],
        "pattern_probe_mapping_matched_C": c["ablation"]["mapping_matched"],
        "pattern_probe_known_slots_B": b["ablation"]["known_slots"],
        "pattern_probe_known_slots_C": c["ablation"]["known_slots"],
        "trained_pattern_hits_B": b["ablation"]["trained"]["hits"],
        "empty_pattern_hits_B": b["ablation"]["empty"]["hits"],
        "trained_pattern_hits_C": c["ablation"]["trained"]["hits"],
        "empty_pattern_hits_C": c["ablation"]["empty"]["hits"],
        "pattern_probe_writes": b["ablation"]["writes"] + c["ablation"]["writes"],
        # the channel
        "channel": channel,
        "pattern_channel_matches_t": bool(
            channel["counts_match"] and channel["projection_matches"]
            and channel["refused_step_silences_both"]
            and channel["pattern_observations"]
            == channel["t_observations"] - channel["cuts"]),
        "matched_seat": bool(b["matched_entry_cell"] and c["matched_entry_cell"]),
        "matched_turns": bool(b["matched_turn_values"] and c["matched_turn_values"]
                              and b["window_turns"] == c["window_turns"]
                              == WINDOW_TURNS),
        "age_control_mileage_B": SCHOOL_TURNS + RIFF_TURNS,
        "age_control_mileage_C": SCHOOL_TURNS + RIFF_TURNS + WINDOW_TURNS,
        "matched_flags": bool(b["protocol_signatures_match"]
                              and c["protocol_signatures_match"]),

        # --- locks ----------------------------------------------------
        "world_name_branches_in_core": core_world_name_branches(),
        "false_facts": taught.metrics.false_facts,
        "destroyed": taught.metrics.destroyed,
        "cortex_calls": taught.metrics.cortex_calls,
        # The cortex hook is the only door to a model, so this is exactly
        # `all_arms_cortex_calls` under another name — reported because
        # the KPI asks for it, and not pretended to be an independent
        # measurement: `green()` gates on the cortex sum.
        "llm_calls": sum(m["cortex_calls"] for v in rows.values()
                         for m in v["arm_metrics"].values()),
        # Nothing in this park says anything: the world sets no
        # `extract_text` on any cell, counted rather than claimed.
        "human_labels": sum(
            1 for layout in (PARK_A, PARK_B, PARK_C, PARK_VOID)
            for cell in range(N_CELLS_PARK)
            if ParkEnv(layout, void=layout == PARK_VOID)
            .teleport(cell).extract_text is not None),
        "n_actions": N_ACTIONS,
        "thought_keys": len(thought.KEYS),
        "default_agent_has_pattern_memory": default.pattern_memory is not None,

        "mutants": battery,
        "mutants_total": state["total"],
        "mutants_killed": state["killed"],
        "required_mutants": len(REQUIRED_MUTANTS),
        "required_mutants_missing": state["missing"],
        "mutants_alive": state["alive"],
        "mutants_malformed": state["malformed"],
    }
    return out


ARMS = ("transfer", "scratch", "age")

# The protocol XFER-1 promised, written out. A literal rather than a call
# to `protocol_signature(new_agent())`, so that a change to `new_agent`
# turns a test red instead of quietly moving the expectation with it —
# the test below pins the two together.
XFER1_PROTOCOL: Dict[str, Any] = {
    "n_actions": N_ACTIONS,
    "ask_enabled": False,
    "cortex_enabled": False,
    "pattern_memory": True,
    "plan_depth": 0,
    "escalate_enabled": False,
    "conflict_attend": False,
    "q_trace": False,
    "q_remainder": False,
    "q_explore_flat": False,
    "q_width": N_ACTIONS,
    "env_seed": BENCH_SEED,
    "window_turns": WINDOW_TURNS,
}
SIGNATURE_BOOLS = ("ask_enabled", "cortex_enabled", "pattern_memory",
                   "escalate_enabled", "conflict_attend", "q_trace",
                   "q_remainder", "q_explore_flat")
SIGNATURE_INTS = ("n_actions", "plan_depth", "q_width", "env_seed",
                  "window_turns")
WALK_FIELDS = ("entry_cell", "turns", "turn_first", "turn_last",
               "turn_fingerprint")
PROBE_FIELDS = ("points", "hits", "unknown", "observes")
# The channel's honest shape, measured and then fixed.
CHANNEL_TURNS = 64
CHANNEL_CUTS = (0, 32)


def _is_int(value: Any) -> bool:
    """An integer, and not a bool wearing one's coat."""
    return isinstance(value, int) and not isinstance(value, bool)


def signature_evidence(sigs: Any) -> Optional[dict]:
    """Three signatures that are complete, well typed, equal — and right.

    `signatures_match` proves equality and nothing else: three arms that
    all have `ask_enabled=True` agree perfectly and all three break the
    protocol. And three arms that have all *dropped* the same key agree
    too. So the keys are fixed, the types are checked, and every arm is
    compared against `XFER1_PROTOCOL`.
    """
    if not isinstance(sigs, dict) or set(sigs) != set(ARMS):
        return None
    for arm in ARMS:
        sig = sigs[arm]
        if not isinstance(sig, dict):
            return None
        # Types first, with `.get`, so a missing key fails here; then the
        # comparison, which is what catches an extra one. A separate
        # key-set check sat above these and could not fail on its own.
        for key in SIGNATURE_BOOLS:
            if not isinstance(sig.get(key), bool):
                return None
        for key in SIGNATURE_INTS:
            if not _is_int(sig.get(key)):
                return None
        # `0 == False` in Python, so the types above are not subsumed by
        # this: `ask_enabled: 0` compares equal to `ask_enabled: False`.
        if sig != XFER1_PROTOCOL:
            return None
    return {"match": signatures_match(sigs), "canonical": True}


def walk_evidence(row: Any) -> Optional[dict]:
    """The protocol, recomputed from the three walks themselves.

    `matched_turn_values` and `matched_entry_cell` are not believed: the
    fields they summarise are read off `transfer`, `scratch` and `age` and
    compared, and the fingerprint is recomputed from the first turn and
    the count — it is the sum of the turn values, so it cannot be moved
    without moving one of those.
    """
    if not isinstance(row, dict):
        return None
    walks = {}
    for arm in ARMS:
        walk = row.get(arm)
        if not isinstance(walk, dict):
            return None
        for key in WALK_FIELDS + ("reward",):
            if not _is_int(walk.get(key)):
                return None
        walks[arm] = walk
    first = walks["transfer"]
    for key in WALK_FIELDS:
        if any(walks[arm][key] != first[key] for arm in ARMS):
            return None
    if first["turns"] != WINDOW_TURNS or first["entry_cell"] != SEAT:
        return None
    if first["turn_last"] != first["turn_first"] + first["turns"] - 1:
        return None
    if first["turn_fingerprint"] != sum(
            range(first["turn_first"], first["turn_last"] + 1)):
        return None
    return {
        "entry_cell": first["entry_cell"],
        "turns": first["turns"],
        "turn_first": first["turn_first"],
        "turn_last": first["turn_last"],
        "turn_fingerprint": first["turn_fingerprint"],
        "rewards": {arm: walks[arm]["reward"] for arm in ARMS},
    }


def _probe_ok(probe: Any, points: Optional[int] = None) -> Optional[dict]:
    """One probe's counters: typed, in range, and adding up."""
    if not isinstance(probe, dict):
        return None
    for key in PROBE_FIELDS:
        if not _is_int(probe.get(key)):
            return None
    n = probe["points"]
    if n < 1 or (points is not None and n != points):
        return None
    if not 0 <= probe["hits"] <= n:
        return None
    if not 0 <= probe["unknown"] <= n:
        return None
    # The rest are wrong answers, so the two cannot exceed the whole.
    if probe["hits"] + probe["unknown"] > n:
        return None
    if probe["observes"] != 0:
        return None
    return probe


def pattern_evidence(row: Any) -> Optional[dict]:
    """Every denominator, and the published entry table.

    A `None` is a miss that stays in the denominator, so the empty
    predictor has to *declare* its unknowns: `empty.unknown = 0` beside
    `points = 96` is a memory claiming to have answered. And the ablation
    has to be scored on the same points as the entry probe — 95 of them
    quoted next to a 96-point probe is a different experiment.
    """
    if not isinstance(row, dict):
        return None
    probes = row.get("pattern")
    if not isinstance(probes, dict) or set(probes) != set(ARMS):
        return None
    points = None
    for arm in ARMS:
        got = _probe_ok(probes[arm], points)
        if got is None:
            return None
        points = got["points"]
    if probes["transfer"]["hits"] != points or probes["transfer"]["unknown"]:
        return None
    for arm in ("scratch", "age"):
        if probes[arm]["hits"] != 0 or probes[arm]["unknown"] != points:
            return None

    ab = row.get("ablation")
    if not isinstance(ab, dict):
        return None
    for key in ("points", "known_slots", "writes"):
        if not _is_int(ab.get(key)):
            return None
    if ab["points"] != points or ab["known_slots"] != ab["points"]:
        return None
    if ab.get("mapping_matched") is not True:
        return None
    trained = _probe_ok(ab.get("trained"), points)
    empty = _probe_ok(ab.get("empty"), points)
    if trained is None or empty is None:
        return None
    if trained["hits"] != points or trained["unknown"] != 0:
        return None
    if empty["hits"] != 0 or empty["unknown"] != points:
        return None
    if trained["hits"] <= empty["hits"]:
        return None
    if ab["writes"] != trained["observes"] + empty["observes"] or ab["writes"]:
        return None
    return {"points": points, "probes": probes, "ablation": ab,
            "probe_observes": sum(probes[arm]["observes"] for arm in ARMS)}


def channel_evidence(channel: Any) -> Optional[dict]:
    """The channel's counters, and the verdict recomputed from them.

    `refused_step_silences_both` is computed correctly inside
    `channel_audit`, and was still believed here — so moving
    `refused_t_observations` to 1 and leaving the boolean alone passed.
    """
    if not isinstance(channel, dict):
        return None
    for key in ("turns", "cuts", "t_observations", "pattern_observations",
                "refused_t_observations", "refused_pattern_observations"):
        if not _is_int(channel.get(key)):
            return None
    for key in ("counts_match", "projection_matches",
                "refused_step_silences_both"):
        if not isinstance(channel.get(key), bool):
            return None
    cuts = channel.get("skipped_after_cuts")
    if not isinstance(cuts, list) or not all(_is_int(v) for v in cuts):
        return None
    if channel["turns"] != CHANNEL_TURNS:
        return None
    if channel["t_observations"] != channel["turns"]:
        return None
    if channel["cuts"] != len(cuts) or tuple(cuts) != CHANNEL_CUTS:
        return None
    if channel["pattern_observations"] != channel["t_observations"] - channel["cuts"]:
        return None
    if not channel["counts_match"] or not channel["projection_matches"]:
        return None
    silent = (channel["refused_t_observations"] == 0
              and channel["refused_pattern_observations"] == 0)
    if channel["refused_step_silences_both"] != silent or not silent:
        return None
    return {"silent": silent, "cuts": channel["cuts"]}


def evidence(report: Any) -> Optional[dict]:
    """Recompute every claim from the raw rows, or None if anything is off.

    `green()` used to read the top-level summaries the report writes about
    its own evidence, so a certificate could contradict the rows beneath
    it — emptying `rows` changed nothing. Then the summaries were tied to
    the rows, and the rows could still contradict *each other*: three
    signatures agreeing on the wrong protocol, an ablation of 95 points
    beside a 96-point probe, a refusal counter beside a boolean that
    disagreed with it.

    So there is one validator per structure, each returning `None` rather
    than a boolean anybody could set: shape, types, ranges and a
    recomputed relation. Nothing here raises.
    """
    if not isinstance(report, dict):
        return None
    rows = report.get("rows")
    if not isinstance(rows, dict) or set(rows) != {PARK_B, PARK_C}:
        return None
    metrics = report.get("arm_metrics")
    if not isinstance(metrics, dict) or set(metrics) != {PARK_B, PARK_C}:
        return None
    chan = channel_evidence(report.get("channel"))
    if chan is None:
        return None

    out: Dict[str, Any] = {"rewards": {}, "gains": {}, "age_gains": {},
                           "ablation": {}, "pattern": {}, "walks": {},
                           "channel": chan}
    sums = {"false_facts": 0, "destroyed": 0, "cortex_calls": 0,
            "cortex_rejected": 0}
    for layout in (PARK_B, PARK_C):
        row, arms = rows[layout], metrics[layout]
        if not isinstance(row, dict) or not isinstance(arms, dict):
            return None
        if set(arms) != set(ARMS):
            return None
        for arm in ARMS:
            m = arms[arm]
            if not isinstance(m, dict):
                return None
            for key in sums:
                if not _is_int(m.get(key)):
                    return None
                sums[key] += m[key]

        if row.get("same_agent_object") is not True:
            return None
        # The four memories, said by the border itself.
        if row.get("same_objects") is not True:
            return None

        sig = signature_evidence(row.get("protocol_signatures"))
        if sig is None or not sig["match"]:
            return None
        if row.get("protocol_signatures_match") is not True:
            return None

        walk = walk_evidence(row)
        if walk is None:
            return None
        # The row's own booleans, tied to the recomputation rather than
        # believed: `turn_first` moved by one used to pass with
        # `matched_turn_values` still saying true.
        if row.get("matched_turn_values") is not True:
            return None
        if row.get("matched_entry_cell") is not True:
            return None
        out["walks"][layout] = walk

        pat = pattern_evidence(row)
        if pat is None:
            return None
        out["pattern"][layout] = pat["probes"]
        out["ablation"][layout] = pat["ablation"]

        out["rewards"][layout] = walk["rewards"]
        out["gains"][layout] = walk["rewards"]["transfer"] - walk["rewards"]["scratch"]
        out["age_gains"][layout] = walk["rewards"]["age"] - walk["rewards"]["scratch"]

    # And the two borders were run on the same points and the same window.
    if (out["pattern"][PARK_B]["transfer"]["points"]
            != out["pattern"][PARK_C]["transfer"]["points"]):
        return None
    out["sums"] = sums
    out["channel_matches"] = True
    return out


def green(report: dict) -> bool:
    """Every KPI at once, read off the evidence and not off the summary.

    Where the report keeps a summary of something the rows already say,
    the summary is required to *equal* the recomputation rather than to be
    believed instead of it.
    """
    try:
        return _green(report)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        # A gate that crashes on a bad certificate has not judged it. The
        # net covers the whole verdict, not only the shape check:
        # `evidence` validates the skeleton, and a row can still be
        # missing a leaf it never promised.
        return False


def _green(report: dict) -> bool:
    ev = evidence(report)
    if ev is None:
        return False
    if any(v != 0 for v in ev["sums"].values()):
        return False
    if report.get("llm_calls") != ev["sums"]["cortex_calls"]:
        return False
    # Every top-level summary of the evidence, tied to the evidence.
    for layout, label in ((PARK_B, "B"), (PARK_C, "C")):
        ab = ev["ablation"][layout]
        if report.get(f"transfer_reward_{label}") != ev["rewards"][layout]["transfer"]:
            return False
        if report.get(f"scratch_reward_{label}") != ev["rewards"][layout]["scratch"]:
            return False
        if report.get(f"gain_{label}") != ev["gains"][layout]:
            return False
        if report.get(f"age_control_gain_{label}") != ev["age_gains"][layout]:
            return False
        if ev["gains"][layout] <= 0 or ev["age_gains"][layout] > 0:
            return False
        for key, value in (
                (f"pattern_probe_mapping_matched_{label}", ab["mapping_matched"]),
                (f"pattern_probe_known_slots_{label}", ab["known_slots"]),
                (f"trained_pattern_hits_{label}", ab["trained"]["hits"]),
                (f"empty_pattern_hits_{label}", ab["empty"]["hits"])):
            if report.get(key) != value:
                return False
        probes = ev["pattern"][layout]
        if report.get(f"pattern_entry_points_{label}") != probes["transfer"]["points"]:
            return False
        if report.get(f"pattern_transfer_hits_{label}") != probes["transfer"]["hits"]:
            return False
        if report.get(f"pattern_scratch_hits_{label}") != probes["scratch"]["hits"]:
            return False
        if report.get(f"pattern_age_hits_{label}") != probes["age"]["hits"]:
            return False
        # (the ablation is tied to the probe's own points inside
        # `pattern_evidence`, which is where that structure lives)
        walk = ev["walks"][layout]
    if report.get("aggregate_transfer_gain") != sum(ev["gains"].values()):
        return False
    # The two summaries of "nothing was written while probing", tied to
    # the rows that say it rather than kept as a second opinion.
    if report.get("pattern_probe_writes") != sum(
            ev["ablation"][layout].get("writes", 0)
            for layout in (PARK_B, PARK_C)):
        return False
    if report.get("pattern_observes_during_entry_probes") != sum(
            probe_row["observes"] for layout in (PARK_B, PARK_C)
            for probe_row in ev["pattern"][layout].values()):
        return False

    for key in ("same_agent_object", "protocol_signatures_match",
                "matched_flags", "gains_equal_reward_differences",
                "pattern_channel_matches_t", "matched_seat", "matched_turns",
                "same_agent_across_worlds", "same_cam_object",
                "same_q_object", "same_t_object", "same_pattern_object"):
        if report.get(key) is not True:
            return False
    if report.get("all_arms_false_facts") != ev["sums"]["false_facts"]:
        return False
    if report.get("all_arms_destroyed") != ev["sums"]["destroyed"]:
        return False
    if report.get("all_arms_cortex_calls") != ev["sums"]["cortex_calls"]:
        return False
    if report.get("all_arms_cortex_rejected") != ev["sums"]["cortex_rejected"]:
        return False
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
        report["worlds"] == 3
        # (the identity booleans are required in the loop above, where
        # every self-declared boolean of this report is required at once)
        # and three worlds, not one world with three names
        and report["world_physics_differences_A_B"] > 0
        and report["world_physics_differences_B_C"] > 0
        and report["t_known_rows_on_entry_B"] > 0
        and report["t_known_rows_on_entry_C"] > 0
        and report["t_contradictions_on_entry_B"] > 0
        and report["t_contradictions_on_entry_C"] > 0
        # each border on its own; a positive total is not enough
        # Everything about the two borders is checked above, from the
        # rows themselves. What is left here is what has no row.
        # the memory's own usefulness, measured apart
        # and the animal never asks which park it is in
        and report["world_name_branches_in_core"] == []
        and report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["cortex_calls"] == 0
        and report["human_labels"] == 0
        and report["n_actions"] == N_ACTIONS
        and report["thought_keys"] == 22
        and not report["default_agent_has_pattern_memory"]
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_xfer1_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
