"""
SIGN-C — the turn where being wrong is what makes the slow clock speak.

WORLD-3 already showed that T survives a change of topology and is wrong
in exactly one place: the fork. CORTEX-1 already showed that a sentence
the fast loop cannot read can change a decision. Neither of those is this
slice. This one is the join: **the contradiction is the reason**.

    train in HOME      T learns the spine, Q learns the last three nodes
    walk into SHIFT    same CAM, same T, same Q, one edge moved
    stand on the fork  Q says approach with margin >= ESC_MARGIN,
                       T says the successor is C, and the world has
                       posted a sign here in Spanish
    act                the world hands back the other node
    only now           the slow clock is woken, with REASON_CONFLICT and
                       with the origin's own sentence, and its atom is
                       consumed on the next turn

The order is the claim. Nothing reads the sign before the world has
contradicted the map: `_conflict_origin` merely copies it, and
`cortex.complete` is not reached until after `env.step()`. A slice that
consulted the sign first would be CORTEX-1 with a longer walk-up.

What the fast loop is *not* short of: the ordinary ATTEND ladder is on in
the `ladder` arm below, wakes on the landing node for LOW_C, reads that
node's own record, and earns nothing. Same cable, same stub, same world.
Only the reason differs, and only the conflict reason carries the
sentence from the place where the commitment was made.

Two things measured here came out against the plan, and both are in the
report as numbers rather than as prose:

**1. At a hazard the fast loop needs no cortex.** The intended landing
node was WORLD-3's X, a THREAT, on the reasoning that a flat Q row waits
and collects nothing while `avoid` pays +8. It does not: `loop.turn`
hands a threat cell `E[U] = 80`, `U_SHORT` is 60, and `gate`'s second
MODIFY rule turns that proposed `wait` into `avoid` before the world sees
it. The fast arm collects the +8 by itself and the ROI of any cortex that
proposes `TEMER` there is exactly 0. `placements()` prices both landing
kinds and prints the number; the bench uses the one that can come out
differently, because a control that cannot lose is the experiment run
twice.

**2. TEMER cannot earn in this world at all.** The only two positive
payoffs are `approach` at a GOAL (+16) and `avoid` at a THREAT (+8), and
the gate already takes the second one for free. So the sign says what the
world actually changed — the lever reversed, what was the hazard is now
the prize — and the atom that follows from it is `UNIR`. The verb is one
of the three this bench has; no fourth action, no new reward, no new
edge. The successor table is `graph.NEXT[shift]` imported verbatim; the
single byte SIGN-C owns is the *kind* of the node the moved edge lands
on, and that node is unreachable in HOME either way.

    PYTHONPATH=. python3 -m echoai.nexus0.signc
"""

from __future__ import annotations

import json
import shlex
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from echoai.nexus0 import bench, graph, thought
from echoai.nexus0.attend import REASON_CONFLICT, reason_name
from echoai.nexus0.constants import (
    ACTION_APPROACH,
    BENCH_TURNS,
    R_SUCCESS,
    ACTION_AVOID,
    ACTION_WAIT,
    BENCH_SEED,
    ESC_MARGIN,
    N_ACTIONS,
    UNKNOWN_NEXT,
)
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_EMPTY, KIND_GOAL, KIND_NAME, KIND_THREAT, Cell
from echoai.nexus0.sign import cortex_env
from echoai.nexus0.types import action_name

LAYOUT_HOME = graph.LAYOUT_HOME
LAYOUT_SHIFT = graph.LAYOUT_SHIFT

# The fork. The sign is here and nowhere else: the origin of the
# commitment, not the place where it is found out.
SIGN_NODE = graph.B
# Where SHIFT's moved edge lands. WORLD-3's own node, WORLD-3's own edges
# (approach -> GOAL, avoid -> B), unreachable in HOME in both layouts.
LANDING_NODE = graph.X

# The sign, in Spanish. It names no node, no action id and no route: it
# says what changed and what to do about it, which is all a sign says.
SIGN_TEXT = (
    "AMBAR: la palanca giro al reves. "
    "Lo de delante ya no es la trampa: ahora es el premio. Entra."
)

# The same sign for the world where the moved edge lands on a hazard.
# `placements()` needs each landing kind priced with the sentence that is
# *true* in it: handing the hazard world a sign that says "entra" would
# price a lying cortex, not the best a cortex could do there.
SIGN_TEXT_RETREAT = (
    "AMBAR: la palanca giro al reves. "
    "Lo de delante ya no es el premio: ahora es la trampa. Retrocede."
)

# The landing kinds priced against each other. Both are kinds this repo
# already has and `_reward` already pays; neither is invented here.
LANDING_KINDS: Dict[str, int] = {"threat": KIND_THREAT, "goal": KIND_GOAL}
LANDING_KIND = KIND_GOAL  # chosen by placements(), not by taste

TRAIN_TURNS = graph.TRAIN_TURNS
SHIFT_TURNS = 8
CONFLICT_TURN = 0  # the turn in SHIFT where the world disagrees with T
CONSUME_TURN = 1  # the turn the one-turn hypothesis is spent on


class SignCEnv(graph.GraphEnv):
    """WORLD-3, with a sentence on the fork and a kind on the landing node.

    Everything else is `graph.GraphEnv` by inheritance: the same 256
    addresses, the same spine, the same successor tables, the same
    `_reward`. `cell()` adds `extract_text` on the fork, which is outside
    the sixteen bytes by construction — `encode_cell(index, kind)` is all
    the packet ever sees, so the fork's WSP, CAM slot, T row and Q row are
    byte-for-byte the ones WORLD-3 trained.
    """

    def __init__(
        self,
        layout: str = LAYOUT_HOME,
        seed: int = BENCH_SEED,
        sign_text: Optional[str] = SIGN_TEXT,
        landing_kind: int = LANDING_KIND,
        sign_node: int = SIGN_NODE,
        signed_layouts: tuple = (LAYOUT_SHIFT,),
    ) -> None:
        self.sign_text = sign_text
        self.landing_kind = int(landing_kind)
        self.sign_node = int(sign_node)
        self.signed_layouts = tuple(signed_layouts)
        super().__init__(layout=layout, seed=seed)

    def reset(self) -> None:
        super().reset()
        self.kind[LANDING_NODE] = self.landing_kind

    def cell(self) -> Cell:
        c = super().cell()
        if (
            self.i == self.sign_node
            and self.layout in self.signed_layouts
            and self.sign_text
        ):
            c.extract_text = str(self.sign_text)
        return c


def cortex_cmd() -> str:
    """The argv line for the CI cortex. No weights, no network."""
    script = Path(__file__).resolve().parent / "tools" / "signc_cortex.py"
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def prose_cmd() -> str:
    """A slow clock that answers in Spanish instead of atoms. The firewall
    in argv form: `parse_reply` rejects it and Q keeps the turn."""
    return (
        f"{shlex.quote(sys.executable)} -c "
        f"{shlex.quote('print(\"me parece que deberias retroceder un poco\")')}"
    )


def _line(record: dict) -> dict:
    """One diary line, with the two integer codes read out as names.

    Only a projection: every value here comes from the jsonl and none is
    recomputed. `action` and `cortex_action` are ints in the log, and a
    report that printed `0` twice would hide which of them is the verb the
    body took and which is where it came from.
    """
    act = record["cortex_action"]
    return {
        "turn": int(record["turn"]),
        "cell": int(record["cell"]),
        "attend_on": bool(record["attend_on"]),
        "reason_name": str(record["reason_name"]),
        "cortex_calls": int(record["cortex_calls"]),
        "cortex_action": None if act is None else thought.ACTION_NAME[int(act)],
        "action": thought.ACTION_NAME[int(record["action"])],
        "reward": int(record["reward"]),
        "s": int(record["s"]),
        "gate_decision": int(record["gate_decision"]),
    }


def canonical_bench() -> dict:
    """The ring's own numbers, recomputed here, written nowhere.

    `bench.run()` computes and `bench.main()` writes, so this cannot touch
    `lab/nexus0_report.json`. The suite already protects these locks; what
    this adds is that the JSON which says `green: true` protects them too,
    so SIGN-C can never be green on top of a bench that has moved. The
    256/31/0/168 of a bare `Agent().run()` is a different, shorter run and
    is not a substitute for it.
    """
    from echoai.nexus0.loop import Agent

    with cortex_env(None):
        report = bench.run()
        ring = Agent(cortex=True)
        ring.run(BENCH_TURNS)
    return {
        "policy_after": [int(v) for v in report["policy_after"]],
        "novel_approach_return": int(report["novel_approach_return"]),
        "cam_misses": int(report["cam_misses"]),
        "surprises": int(report["surprises"]),
        "deltas": int(report["deltas"]),
        "surprise_known": int(report["surprise_known"]),
        "cortex_calls": int(report["cortex_calls"]),
        "false_facts": int(report["false_facts"]),
        "destroyed": int(report["destroyed"]),
        "encoder_beats_fnv": bool(report["encoder_beats_fnv"]),
        "t_beats_ring": bool(report["t_beats_ring"]),
        "negative_delta_causes_policy_change": bool(
            report["negative_delta_causes_policy_change"]),
        "ring_cortex_wakes": int(ring.metrics.cortex_calls),
        "ring_turns": int(BENCH_TURNS),
        "ring_conflict_wakes": int(ring.conflict_wakes),
    }


def _packet_is_blind_to_the_sign() -> bool:
    """Same fork, same sixteen bytes, and only one of the two has a sign."""
    plain = graph.GraphEnv(LAYOUT_SHIFT)
    plain.teleport(SIGN_NODE)
    signed = SignCEnv(LAYOUT_SHIFT)
    signed.teleport(SIGN_NODE)
    a, b = plain.cell(), signed.cell()
    return bool(
        encode_cell(a.index, a.kind) == encode_cell(b.index, b.kind)
        and a.extract_text is None
        and b.extract_text == SIGN_TEXT
    )


def _slot(ag, node: int, kind: int) -> int:
    return ag.cam.get(encode_cell(node, kind))


def _train(landing_kind: int, sign_text, signed_layouts):
    """One agent, HOME, WORLD-3's own 512 turns, cortex off.

    Every arm trains through this, and the landing node is unreachable in
    HOME whatever its kind, so the tables the arms enter SHIFT with are
    identical — the report checks that rather than assuming it.
    """
    from echoai.nexus0.loop import Agent

    ag = Agent(
        ask=False,
        env=SignCEnv(
            LAYOUT_HOME,
            sign_text=sign_text,
            landing_kind=landing_kind,
            signed_layouts=signed_layouts,
        ),
    )
    ag.run(TRAIN_TURNS)
    return ag


def arm(
    name: str,
    cmd: Optional[str],
    cortex_on: bool = False,
    conflict_on: bool = False,
    landing_kind: int = LANDING_KIND,
    sign_text: Optional[str] = SIGN_TEXT,
    signed_layouts: tuple = (LAYOUT_SHIFT,),
    shift_layout: str = LAYOUT_SHIFT,
    blind_t: bool = False,
    q_row_at_fork: Optional[List[int]] = None,
    turns: int = SHIFT_TURNS,
) -> dict:
    """Train in HOME, enter `shift_layout` on the fork, walk greedily.

    Everything an arm can differ by is a keyword here, so a mutant is a
    call and not a copy of the bench.
    """
    from echoai.nexus0.loop import Agent  # noqa: F401  (kept for symmetry)

    ag = _train(landing_kind, sign_text, signed_layouts)
    ag.cortex_enabled = bool(cortex_on)
    ag.conflict_attend = bool(conflict_on)
    slot_b = _slot(ag, SIGN_NODE, KIND_EMPTY)
    q_home = ag.q.row(slot_b)

    ag.env = SignCEnv(
        shift_layout,
        sign_text=sign_text,
        landing_kind=landing_kind,
        signed_layouts=signed_layouts,
    )
    ag.env.teleport(SIGN_NODE)

    if q_row_at_fork is not None:
        # A fork the fast loop is nearly indifferent about. Being wrong
        # about a coin-flip is not news, and must not wake anything.
        ag.q.q[slot_b] = [int(v) for v in q_row_at_fork]
    if blind_t:
        # T never learned this row. Nothing was predicted, so nothing was
        # contradicted: a T_MISS is ignorance, not a conflict.
        ag.t.pred[slot_b][ACTION_APPROACH] = UNKNOWN_NEXT

    # Read standing in the new world, after every mutation: an arm that
    # quietly cleared a table on the way in has to show up here.
    origin = {
        "slot": int(slot_b),
        "hits": int(ag.cam.slot[slot_b].hits),
        "q_row": ag.q.row(slot_b),
        "q_row_after_home": q_home,
        "q_best": action_name(ag.q.best(slot_b)),
        "q_margin": int(ag.q.margin(slot_b)),
        "t_pred": ag.t.predict(slot_b, ACTION_APPROACH),
        "t_conf": int(ag.t.conf(slot_b, ACTION_APPROACH)),
        "language": ag.env.cell().extract_text,
    }
    origin["was_known_to_t"] = origin["t_pred"] is not None
    origin["was_not_a_cam_miss"] = origin["hits"] > 1
    origin["q_margin_is_enough"] = origin["q_margin"] >= ESC_MARGIN
    origin["world_language"] = bool(
        origin["language"] is not None and str(origin["language"]).strip()
    )

    calls_before = ag.metrics.cortex_calls
    tmp = tempfile.TemporaryDirectory()
    # The diary, because the diary is what the KPI is about. A field
    # derived from `ag.last_attend` after the fact would be a paraphrase
    # of the log; this is the log. It goes to a scratch directory and is
    # never shipped — no second jsonl joins `lab/`.
    ag.thought_log = str(Path(tmp.name) / "thought.jsonl")
    with cortex_env(cmd):
        a0 = ag.turn(TRAIN_TURNS + CONFLICT_TURN, greedy=True)
        r0 = int(ag.env.last_reward)
        landed = int(ag.env.cell().index)
        wakes_after_step = int(ag.conflict_wakes)
        # Read at the wake, not at the end of the walk: `last_attend` is
        # the reason of the *last* attend decision, and eight turns later
        # it is somebody else's.
        reason_at_conflict = reason_name(ag.last_attend[1])
        actions_before = ag.metrics.cortex_actions

        a1 = ag.turn(TRAIN_TURNS + CONSUME_TURN, greedy=True)
        r1 = int(ag.env.last_reward)
        reason_at_landing = reason_name(ag.last_attend[1])
        actions_after = ag.metrics.cortex_actions

        rewards = [r0, r1]
        for t in range(CONSUME_TURN + 1, turns):
            ag.turn(TRAIN_TURNS + t, greedy=True)
            rewards.append(int(ag.env.last_reward))

    diary = [json.loads(x) for x
             in Path(ag.thought_log).read_text(encoding="utf-8").splitlines()]
    tmp.cleanup()
    ag.thought_log = None
    conflict_line = _line(diary[CONFLICT_TURN])
    consume_line = _line(diary[CONSUME_TURN])

    slot_landing = _slot(ag, LANDING_NODE, landing_kind)
    return {
        "arm": name,
        "cortex": bool(cortex_on),
        "conflict_attend": bool(conflict_on),
        "landing_kind": KIND_NAME[landing_kind],
        "shift_layout": shift_layout,
        "origin": origin,
        "conflict_action": action_name(a0),
        "conflict_reward": r0,
        "landed_node": landed,
        "landed_on_the_moved_edge": landed == LANDING_NODE,
        "landing_slot_is_new": slot_landing >= 0 and slot_landing != origin["t_pred"],
        # The contradiction itself, straight off the loop's own counter.
        "t_prediction_contradicted": bool(
            origin["t_pred"] is not None
            and origin["t_pred"] != _slot(ag, landed, ag.env.kind[landed])
        ),
        "conflict_wakes": int(ag.conflict_wakes),
        "conflict_wakes_on_the_conflict_turn": wakes_after_step,
        "cortex_calls": int(ag.metrics.cortex_calls) - calls_before,
        "cortex_rejected": int(ag.metrics.cortex_rejected),
        "cortex_actions_total": int(ag.metrics.cortex_actions),
        "proposal_consumed_next_turn": bool(actions_after - actions_before == 1),
        "attend_reason": reason_at_conflict,
        "attend_reason_at_landing": reason_at_landing,
        # The two lines, as written. `attend_reason_at_landing` is kept
        # beside them and is `off` by design now: the consuming turn makes
        # no ATTEND decision, and a report that demanded `conflict` there
        # was demanding the bug.
        "conflict_line": conflict_line,
        "consume_line": consume_line,
        "cortex_calls_delta_on_conflict": (
            conflict_line["cortex_calls"] - calls_before),
        "cortex_calls_delta_on_consume": (
            consume_line["cortex_calls"] - conflict_line["cortex_calls"]),
        "one_line_claims_the_wake": bool(
            sum(1 for ln in diary
                if ln["attend_on"] and ln["reason_name"] == "conflict") == 1),
        "action_at_landing": action_name(a1),
        "reward_at_landing": r1,
        "reward_sum_shift": sum(rewards),
        "rewards": rewards,
        "questions": int(ag.metrics.questions),
        "false_facts": int(ag.metrics.false_facts),
        "destroyed": int(ag.metrics.destroyed),
        "t_conflicts": int(ag.t.conflicts),
    }


def placements() -> List[dict]:
    """Price both landing kinds before promising one.

    The KPI needs a control that can come out differently. At a THREAT it
    cannot: the gate rescues the fast arm's `wait` into the `avoid` that
    pays, so both arms collect the same +8 and the difference the slice is
    supposed to measure is 0 by construction. The table is in the report
    so the choice of GOAL is a number and not a preference.
    """
    rows = []
    cmd = cortex_cmd()
    text = {"threat": SIGN_TEXT_RETREAT, "goal": SIGN_TEXT}
    for label, kind in LANDING_KINDS.items():
        fast = arm(f"fast_{label}", None, landing_kind=kind,
                   sign_text=text[label])
        cx = arm(
            f"signc_{label}", cmd, cortex_on=True, conflict_on=True,
            landing_kind=kind, sign_text=text[label],
        )
        rows.append({
            "landing_kind": label,
            "sign": text[label],
            "fast_action_at_landing": fast["action_at_landing"],
            "fast_reward_at_landing": fast["reward_at_landing"],
            "cortex_action_at_landing": cx["action_at_landing"],
            "cortex_reward_at_landing": cx["reward_at_landing"],
            "CortexROI": cx["reward_at_landing"] - fast["reward_at_landing"],
            "discriminates": bool(
                cx["reward_at_landing"] > fast["reward_at_landing"]
            ),
        })
    return rows


def experiment() -> dict:
    cmd = cortex_cmd()

    signc = arm("signc", cmd, cortex_on=True, conflict_on=True)
    fast = arm("fast", None)
    ladder = arm("ladder", cmd, cortex_on=True, conflict_on=False)

    mutants = {
        # The sign is gone. Same contradiction, same margin, same T.
        "no_language": arm("no_language", cmd, cortex_on=True, conflict_on=True,
                           sign_text=None),
        # The world hands back the label the loop would have written
        # anyway. A rótulo is not a sign.
        "synthetic_label": arm(
            "synthetic_label", cmd, cortex_on=True, conflict_on=True,
            sign_text=Cell(index=SIGN_NODE, kind=KIND_EMPTY).extract,
        ),
        "empty_language": arm("empty_language", cmd, cortex_on=True,
                              conflict_on=True, sign_text="   "),
        # The sign is there and T is right: HOME's own edge, so approach
        # lands exactly where the map said.
        "t_agrees": arm("t_agrees", cmd, cortex_on=True, conflict_on=True,
                        shift_layout=LAYOUT_HOME,
                        signed_layouts=(LAYOUT_HOME, LAYOUT_SHIFT)),
        # T never learned the row. Nothing predicted, nothing contradicted.
        "t_miss": arm("t_miss", cmd, cortex_on=True, conflict_on=True,
                      blind_t=True),
        # Q was nearly indifferent at the fork.
        "low_margin": arm("low_margin", cmd, cortex_on=True, conflict_on=True,
                          q_row_at_fork=[4, 3, 0]),
        # The slow clock answers in Spanish. The firewall keeps the turn.
        "prose_reply": arm("prose_reply", prose_cmd(), cortex_on=True,
                           conflict_on=True),
    }

    roi = signc["reward_at_landing"] - fast["reward_at_landing"]
    roi_window = signc["reward_sum_shift"] - fast["reward_sum_shift"]

    canon = canonical_bench()
    out: Dict[str, object] = {
        "world": "signc",
        "base": "world3",
        "nodes": graph.N_NODES,
        "actions": N_ACTIONS,
        "fork_node": SIGN_NODE,
        "fork_pos": graph.FORK_POS,
        "home_next_of_fork": graph.C,
        "shift_next_of_fork": LANDING_NODE,
        "landing_kind": KIND_NAME[LANDING_KIND],
        "sign_node": SIGN_NODE,
        "sign_text": SIGN_TEXT,
        # Derived, standing on the fork in both worlds: WORLD-3's own env
        # and this one hand back the same sixteen bytes, and only one of
        # them has a sentence. Written as `encode_cell(a) == encode_cell(a)`
        # it would be a tautology, and read off an env still sitting at
        # START it was simply false — the first version of this field was
        # both.
        "sign_is_outside_the_packet": _packet_is_blind_to_the_sign(),
        "fork_wsp_hex": encode_cell(SIGN_NODE, KIND_EMPTY).hex(),
        "train_turns": TRAIN_TURNS,
        "shift_turns": SHIFT_TURNS,
        "greedy": True,
        "cortex_cmd": cmd,
        "esc_margin": ESC_MARGIN,
        "reason_conflict_code": REASON_CONFLICT,
        "reason_conflict_name": reason_name(REASON_CONFLICT),

        # --- the single causal closure ------------------------------
        "origin_was_known_to_t": signc["origin"]["was_known_to_t"],
        "origin_t_pred_is_home_c": bool(
            signc["origin"]["t_pred"]
            == _slot(_train(LANDING_KIND, SIGN_TEXT, (LAYOUT_SHIFT,)),
                     graph.C, KIND_EMPTY)
        ),
        "origin_t_conf": signc["origin"]["t_conf"],
        "origin_was_not_a_cam_miss": signc["origin"]["was_not_a_cam_miss"],
        "origin_hits": signc["origin"]["hits"],
        "q_margin_at_origin": signc["origin"]["q_margin"],
        "q_margin_is_enough": signc["origin"]["q_margin_is_enough"],
        "q_best_at_origin": signc["origin"]["q_best"],
        "world_language_at_origin": signc["origin"]["world_language"],
        "t_prediction_contradicted": signc["t_prediction_contradicted"],
        "landed_on_the_moved_edge": signc["landed_on_the_moved_edge"],
        "attend_reason": signc["attend_reason"],
        "attend_reason_at_landing": signc["attend_reason_at_landing"],
        "conflict_wakes": signc["conflict_wakes"],
        "cortex_calls": signc["cortex_calls"],
        "cortex_calls_are_only_the_conflict": bool(
            signc["cortex_calls"] == signc["conflict_wakes"]
        ),
        "proposal_consumed_next_turn": signc["proposal_consumed_next_turn"],
        "action_at_landing": signc["action_at_landing"],
        "reward_at_landing": signc["reward_at_landing"],

        # --- the control --------------------------------------------
        "control_conflict_observed": fast["t_prediction_contradicted"],
        "control_action_at_landing": fast["action_at_landing"],
        "control_reward_at_landing": fast["reward_at_landing"],
        "control_reward_sum_shift": fast["reward_sum_shift"],
        "control_cortex_wakes": fast["cortex_calls"],
        "control_cortex_actions": fast["cortex_actions_total"],
        "signc_reward_sum_shift": signc["reward_sum_shift"],
        "CortexROI": roi,
        "CortexROI_window": roi_window,
        "control_scores_less": bool(
            signc["reward_sum_shift"] > fast["reward_sum_shift"]
        ),
        # The ordinary ladder, same cortex, same cable, same world: it
        # wakes on the landing node and earns nothing, because the reason
        # it woke for carries that node's own record and not the sign.
        "ladder_cortex_wakes": ladder["cortex_calls"],
        "ladder_conflict_wakes": ladder["conflict_wakes"],
        "ladder_attend_reason": ladder["attend_reason_at_landing"],
        "ladder_reward_at_landing": ladder["reward_at_landing"],
        "ladder_reward_sum_shift": ladder["reward_sum_shift"],
        "ladder_earns_nothing": bool(
            ladder["reward_sum_shift"] == fast["reward_sum_shift"]
        ),

        # --- the same tables in every arm ---------------------------
        "arms_train_identically": bool(
            signc["origin"]["q_row_after_home"]
            == fast["origin"]["q_row_after_home"]
            == ladder["origin"]["q_row_after_home"]
        ),

        # --- both landing kinds, priced -----------------------------
        "placements": placements(),

        # --- mutants -------------------------------------------------
        "mutants": {
            k: {
                "conflict_wakes": v["conflict_wakes"],
                "cortex_actions": v["cortex_actions_total"],
                "cortex_rejected": v["cortex_rejected"],
                "reward_at_landing": v["reward_at_landing"],
                "reward_sum_shift": v["reward_sum_shift"],
                "attend_reason": v["attend_reason"],
                "attend_reason_at_landing": v["attend_reason_at_landing"],
            }
            for k, v in mutants.items()
        },

        # --- the two lines, and only one of them woke -----------------
        "conflict_line": signc["conflict_line"],
        "consume_line": signc["consume_line"],
        "cortex_calls_delta_on_conflict": signc["cortex_calls_delta_on_conflict"],
        "cortex_calls_delta_on_consume": signc["cortex_calls_delta_on_consume"],
        "one_line_claims_the_wake": signc["one_line_claims_the_wake"],

        # --- locks ----------------------------------------------------
        "false_facts": (
            signc["false_facts"] + fast["false_facts"] + ladder["false_facts"]
        ),
        "destroyed": (
            signc["destroyed"] + fast["destroyed"] + ladder["destroyed"]
        ),
        "questions": signc["questions"] + fast["questions"],
        # The canonical bench, not a shorter run standing in for it.
        "canonical_bench": canon,
        "ring_cortex_wakes": canon["ring_cortex_wakes"],
        "ring_wakes_unchanged": bool(canon["ring_cortex_wakes"] == 36),
        "default_agent_has_conflict_attend": _default_flag(),
    }
    return out


def _default_flag() -> bool:
    from echoai.nexus0.loop import Agent

    return bool(Agent().conflict_attend)


def green(report: dict) -> bool:
    """Every KPI at once. One red number and the slice is red."""
    mut = report["mutants"]
    silent = ("no_language", "synthetic_label", "empty_language", "t_agrees",
              "t_miss", "low_margin")
    return bool(
        report["false_facts"] == 0
        and report["destroyed"] == 0
        and report["actions"] == N_ACTIONS
        # the closure, in order
        and report["sign_is_outside_the_packet"]
        and report["origin_was_known_to_t"]
        and report["origin_t_pred_is_home_c"]
        and report["origin_was_not_a_cam_miss"]
        and report["q_margin_is_enough"]
        and report["q_best_at_origin"] == "approach"
        and report["world_language_at_origin"]
        and report["t_prediction_contradicted"]
        and report["landed_on_the_moved_edge"]
        and report["attend_reason"] == "conflict"
        and report["conflict_wakes"] == 1
        and report["cortex_calls_are_only_the_conflict"]
        and report["proposal_consumed_next_turn"]
        and report["action_at_landing"] == "approach"
        and report["CortexROI"] > 0
        # the control saw the same contradiction and could not use it
        and report["control_conflict_observed"]
        and report["control_cortex_wakes"] == 0
        and report["control_cortex_actions"] == 0
        and report["control_scores_less"]
        # the ordinary ladder is not what earned it
        and report["ladder_conflict_wakes"] == 0
        and report["ladder_cortex_wakes"] > 0
        and report["ladder_attend_reason"] != "conflict"
        and report["ladder_earns_nothing"]
        and report["arms_train_identically"]
        # a reply that is not atoms is not an action
        and mut["prose_reply"]["conflict_wakes"] == 1
        and mut["prose_reply"]["cortex_actions"] == 0
        and mut["prose_reply"]["cortex_rejected"] == 1
        and mut["prose_reply"]["reward_sum_shift"]
        == report["control_reward_sum_shift"]
        # and every way of not being a conflict is silence
        and all(mut[k]["conflict_wakes"] == 0 for k in silent)
        and all(mut[k]["cortex_actions"] == 0 for k in silent)
        # one conflict, one wake, one true line
        and report["one_line_claims_the_wake"]
        and report["conflict_line"]["attend_on"]
        and report["conflict_line"]["reason_name"] == "conflict"
        and report["conflict_line"]["cortex_action"] is None
        and report["cortex_calls_delta_on_conflict"] == 1
        and report["consume_line"]["attend_on"] is False
        and report["consume_line"]["reason_name"] == "off"
        and report["consume_line"]["cortex_action"] == "approach"
        and report["consume_line"]["action"] == "approach"
        and report["consume_line"]["reward"] == R_SUCCESS
        and report["cortex_calls_delta_on_consume"] == 0
        # the ring is where it was, on its own bench and not a stand-in
        and _canon_is_green(report["canonical_bench"])
        and report["ring_wakes_unchanged"]
        and not report["default_agent_has_conflict_attend"]
    )


def _canon_is_green(canon: dict) -> bool:
    """The ring's locks, every one of them, as booleans of the numbers.

    Nothing here is new: these are the KPIs `docs/05-NEXUS-0-SPEC.md` §12
    and `echoai/CLAUDE.md` already fix, recomputed so that no SIGN-C report
    can call itself green while the bench underneath it has drifted.
    """
    return bool(
        canon["policy_after"] == [-12, 5, 0]
        and canon["novel_approach_return"] == 80
        and [canon["cam_misses"], canon["surprises"], canon["deltas"]]
        == [33, 1, 217]
        and canon["surprise_known"] == 1
        and canon["cortex_calls"] == 0
        and canon["false_facts"] == 0
        and canon["destroyed"] == 0
        and canon["encoder_beats_fnv"]
        and canon["t_beats_ring"]
        and canon["negative_delta_causes_policy_change"]
        and canon["ring_cortex_wakes"] == 36
        and canon["ring_turns"] == BENCH_TURNS
        and canon["ring_conflict_wakes"] == 0
    )


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    out = Path(__file__).resolve().parents[1] / "lab" / "nexus0_signc_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
