"""GEN-1: one inherited exploration integer, with fresh child memory.

Selection and examination use disjoint seeds.  A child receives only ``b``;
CAM, Q, T, body, vitality and counters are newly constructed.  No cortex or
hardware participates in this benchmark.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.echo2 import INITIAL_H, LIVES, NUTRITION
from echoai.nexus0.food1 import FoodEnv
from echoai.nexus0.loop import Agent
from echoai.nexus0.vita1 import VitalEnv


CANDIDATES = (-1, 0, 1)
SELECTION_SEEDS = (17, 101, 20260903)
EXAM_SEEDS = (211, 307, 401, 503, 601)
PHASE_MODULUS = 30000
CRITERION_WINDOW = 5
CRITERION_SUCCESSES = 4
CENSORED_CAP = LIVES + 1
SCHEMA_VERSION = 1


def new_agent(b: int, *, nutrition: int = NUTRITION) -> Agent:
    return Agent(
        env=VitalEnv(FoodEnv(nutrition)),
        initial_h=INITIAL_H,
        ask=False,
        remainder=True,
        explore_flat=True,
        inherited_b=b,
    )


def spawn_child(parent: Agent, *, nutrition: int = NUTRITION) -> Agent:
    """Birth transfers exactly one immutable configuration integer."""
    return new_agent(parent.q.inherited_b, nutrition=nutrition)


def phase_schedule(seed: int) -> Tuple[int, ...]:
    rng = random.Random(int(seed))
    return tuple(rng.randrange(PHASE_MODULUS) for _ in range(LIVES))


def _memory_fingerprint(agent: Agent) -> dict:
    """Compact deterministic evidence for CAM/Q/T contents."""
    cam_h = hashlib.sha256()
    occupied = 0
    for i, slot in enumerate(agent.cam.slot):
        if not slot.occupied:
            continue
        occupied += 1
        cam_h.update(i.to_bytes(2, "little"))
        cam_h.update(slot.wsp)
        cam_h.update(int(slot.hits).to_bytes(2, "little"))

    q_h = hashlib.sha256()
    q_nonzero = rem_nonzero = 0
    for table, key in ((agent.q.q, "q"), (agent.q.rem, "r")):
        q_h.update(key.encode("ascii"))
        for row in table:
            for value in row:
                q_h.update(int(value).to_bytes(2, "little", signed=True))
                if key == "q":
                    q_nonzero += int(value != 0)
                else:
                    rem_nonzero += int(value != 0)

    t_h = hashlib.sha256()
    t_known = 0
    for table in (agent.t.pred, agent.t.n, agent.t.alt, agent.t.alt_n):
        for row in table:
            for value in row:
                t_h.update(int(value).to_bytes(2, "little", signed=False))
    for row in agent.t.n:
        t_known += sum(value > 0 for value in row)
    return {
        "cam_occupied": occupied,
        "q_nonzero": q_nonzero,
        "rem_nonzero": rem_nonzero,
        "t_known": t_known,
        "cam": cam_h.hexdigest(),
        "q": q_h.hexdigest(),
        "t": t_h.hexdigest(),
    }


def _is_success(row: dict) -> bool:
    return (
        row.get("turns") == INITIAL_H + NUTRITION
        and row.get("terminal") is True
        and row.get("h") == 0
        and row.get("consumed") == 1
    )


def episodes_to_criterion(lives: Sequence[dict]) -> Optional[int]:
    success = [_is_success(row) for row in lives]
    for end in range(CRITERION_WINDOW, len(success) + 1):
        window = success[end - CRITERION_WINDOW:end]
        if sum(window) >= CRITERION_SUCCESSES:
            return end
    return None


def _summarize(lives: Sequence[dict]) -> dict:
    criterion = episodes_to_criterion(lives)
    return {
        "episodes_to_criterion": criterion,
        "censored": criterion is None,
        "capped_episodes_to_criterion": (
            CENSORED_CAP if criterion is None else criterion
        ),
        "turns_to_criterion": (
            None if criterion is None
            else sum(row["turns"] for row in lives[:criterion])
        ),
        "successes": sum(_is_success(row) for row in lives),
        "successes_last10": sum(_is_success(row) for row in lives[-10:]),
    }


def _disable_q_learning(agent: Agent) -> None:
    def no_update(_s: int, _a: int, _r: int, _next: int,
                  *, terminal: bool = False) -> int:
        return 0
    agent.q.update = no_update  # type: ignore[method-assign]


def run_arm(agent: Agent, phases: Sequence[int], *, learning: bool = True
            ) -> Tuple[dict, Agent]:
    if len(phases) != LIVES:
        raise ValueError("one external phase is required per life")
    birth = _memory_fingerprint(agent)
    if not learning:
        _disable_q_learning(agent)

    lives: List[dict] = []
    memory_ids = (id(agent.cam), id(agent.q), id(agent.t))
    identities_preserved = True
    for life, phase in enumerate(phases):
        if life:
            agent.respawn()
            identities_preserved &= memory_ids == (
                id(agent.cam), id(agent.q), id(agent.t)
            )
        reward_sum = 0
        proposals = [0] * agent.n_actions
        actions = [0] * agent.n_actions
        gate = [0, 0, 0]
        explorations = 0
        max_turns = INITIAL_H + max(0, agent.env.nutrition)
        while not agent.episode_terminal and agent.life_turns < max_turns:
            turn = life * PHASE_MODULUS + int(phase) + agent.life_turns
            action = agent.turn(turn)
            proposal = agent.last_proposed_action
            decision = agent.last_gate_decision
            if proposal is None or decision is None:
                raise RuntimeError("decision instrumentation missing")
            proposals[proposal] += 1
            actions[action] += 1
            gate[decision] += 1
            explorations += int(agent.last_explore)
            reward_sum += agent.last_reward
        row = {
            "life": life + 1,
            "phase": int(phase),
            "turns": agent.life_turns,
            "terminal": agent.episode_terminal,
            "h": agent.H,
            "consumed": agent.env.consumed,
            "reward_sum": reward_sum,
            "proposals": proposals,
            "actions": actions,
            "gate": gate,
            "explorations": explorations,
        }
        row["success"] = _is_success(row)
        lives.append(row)

    report = {
        "b": agent.q.inherited_b,
        "learning": learning,
        "phases": list(phases),
        "lives": lives,
        "birth": birth,
        "final": _memory_fingerprint(agent),
        "respawn_preserves_memory": identities_preserved,
        "deaths": agent.deaths,
        "false_facts": agent.metrics.false_facts,
        "destroyed": agent.cam.destroyed,
        "cortex_calls": agent.metrics.cortex_calls,
    }
    report.update(_summarize(lives))
    return report, agent


def _candidate_rank(row: dict) -> tuple:
    b = row["b"]
    tie = 0 if b == 0 else (1 if b == -1 else 2)
    return row["score"], tie


def select_parent() -> Tuple[dict, Agent]:
    candidates = []
    parents: Dict[int, Agent] = {}
    for b in CANDIDATES:
        arms = []
        for seed in SELECTION_SEEDS:
            arm, trained = run_arm(new_agent(b), phase_schedule(seed))
            arms.append({"seed": seed, "arm": arm})
            if seed == SELECTION_SEEDS[0]:
                parents[b] = trained
        score = sum(row["arm"]["capped_episodes_to_criterion"]
                    for row in arms)
        candidates.append({"b": b, "score": score, "arms": arms})
    winner = min(candidates, key=_candidate_rank)["b"]
    return {"candidates": candidates, "winner_b": winner}, parents[winner]


def _median(values: Sequence[int]) -> int:
    ordered = sorted(int(value) for value in values)
    if not ordered or len(ordered) % 2 == 0:
        raise ValueError("GEN-1 medians require a non-empty odd sample")
    return ordered[len(ordered) // 2]


def experiment() -> dict:
    selection, parent = select_parent()
    winner = selection["winner_b"]
    exam = []
    inert = []
    no_q = []
    for seed in EXAM_SEEDS:
        phases = phase_schedule(seed)

        inherited, _ = run_arm(spawn_child(parent), phases)
        naive, _ = run_arm(new_agent(0), phases)
        erased_child = spawn_child(parent)
        erased_child.q.inherited_b = 0
        erase_b, _ = run_arm(erased_child, phases)
        static_b, _ = run_arm(new_agent(winner), phases)
        exam.append({"seed": seed, "inherited": inherited, "naive": naive,
                     "erase_b": erase_b, "static_b": static_b})

        inert_inherited, _ = run_arm(
            spawn_child(parent, nutrition=0), phases
        )
        inert_naive, _ = run_arm(new_agent(0, nutrition=0), phases)
        inert.append({"seed": seed, "inherited": inert_inherited,
                      "naive": inert_naive})

        frozen_inherited, _ = run_arm(
            spawn_child(parent), phases, learning=False
        )
        frozen_naive, _ = run_arm(
            new_agent(0), phases, learning=False
        )
        no_q.append({"seed": seed, "inherited": frozen_inherited,
                     "naive": frozen_naive})

    inherited_caps = [row["inherited"]["capped_episodes_to_criterion"]
                      for row in exam]
    naive_caps = [row["naive"]["capped_episodes_to_criterion"]
                  for row in exam]
    return {
        "schema": SCHEMA_VERSION,
        "slice": "GEN-1",
        "protocol": {
            "candidates": list(CANDIDATES),
            "selection_seeds": list(SELECTION_SEEDS),
            "exam_seeds": list(EXAM_SEEDS),
            "lives": LIVES,
            "initial_h": INITIAL_H,
            "nutrition": NUTRITION,
            "phase_modulus": PHASE_MODULUS,
            "criterion_window": CRITERION_WINDOW,
            "criterion_successes": CRITERION_SUCCESSES,
            "censored_cap": CENSORED_CAP,
        },
        "selection": selection,
        "transmitted_b": winner,
        "parent_final": _memory_fingerprint(parent),
        "exam": exam,
        "inert_control": inert,
        "no_q_control": no_q,
        "headline": {
            "inherited_median": _median(inherited_caps),
            "naive_median": _median(naive_caps),
            "strict_pair_wins": sum(a < b for a, b in
                                    zip(inherited_caps, naive_caps)),
            "inherited_reached": sum(value < CENSORED_CAP
                                     for value in inherited_caps),
        },
    }


def _valid_arm(arm: dict, phases: Sequence[int], *, nutrition: int = NUTRITION
               ) -> bool:
    if arm["phases"] != list(phases) or len(arm["lives"]) != LIVES:
        return False
    if arm["deaths"] != LIVES or arm["respawn_preserves_memory"] is not True:
        return False
    if any(arm[key] != 0 for key in ("false_facts", "destroyed", "cortex_calls")):
        return False
    if arm["b"] not in CANDIDATES or type(arm["learning"]) is not bool:
        return False
    birth = arm["birth"]
    if any(birth[key] != 0 for key in
           ("cam_occupied", "q_nonzero", "rem_nonzero", "t_known")):
        return False
    for i, row in enumerate(arm["lives"]):
        if row["life"] != i + 1 or row["phase"] != phases[i]:
            return False
        if row["terminal"] is not True or row["h"] != 0:
            return False
        if (type(row["consumed"]) is not int or row["consumed"] not in (0, 1)
                or row["turns"] != INITIAL_H + max(0, nutrition) * row["consumed"]
                or len(row["proposals"]) != 3 or len(row["actions"]) != 3
                or len(row["gate"]) != 3):
            return False
        if row["success"] is not _is_success(row):
            return False
        if sum(row["proposals"]) != row["turns"]:
            return False
        if sum(row["actions"]) != row["turns"]:
            return False
        if sum(row["gate"]) != row["turns"]:
            return False
    expected = _summarize(arm["lives"])
    return all(arm[key] == value for key, value in expected.items())


def green(report: dict) -> bool:
    """Rebuild selection and causal comparisons from individual lives."""
    try:
        expected_protocol = {
            "candidates": list(CANDIDATES),
            "selection_seeds": list(SELECTION_SEEDS),
            "exam_seeds": list(EXAM_SEEDS),
            "lives": LIVES,
            "initial_h": INITIAL_H,
            "nutrition": NUTRITION,
            "phase_modulus": PHASE_MODULUS,
            "criterion_window": CRITERION_WINDOW,
            "criterion_successes": CRITERION_SUCCESSES,
            "censored_cap": CENSORED_CAP,
        }
        if (report["schema"], report["slice"], report["protocol"]) != (
                SCHEMA_VERSION, "GEN-1", expected_protocol):
            return False

        candidates = report["selection"]["candidates"]
        if [row["b"] for row in candidates] != list(CANDIDATES):
            return False
        for candidate in candidates:
            if [row["seed"] for row in candidate["arms"]] != list(SELECTION_SEEDS):
                return False
            score = 0
            for seeded in candidate["arms"]:
                phases = phase_schedule(seeded["seed"])
                if not _valid_arm(seeded["arm"], phases):
                    return False
                if seeded["arm"]["learning"] is not True:
                    return False
                if seeded["arm"]["b"] != candidate["b"]:
                    return False
                score += seeded["arm"]["capped_episodes_to_criterion"]
            if candidate["score"] != score:
                return False
        winner = min(candidates, key=_candidate_rank)["b"]
        if report["selection"]["winner_b"] != winner:
            return False
        if report["transmitted_b"] != winner:
            return False
        winner_row = next(row for row in candidates if row["b"] == winner)
        if report["parent_final"] != winner_row["arms"][0]["arm"]["final"]:
            return False

        if [row["seed"] for row in report["exam"]] != list(EXAM_SEEDS):
            return False
        inherited_caps: List[int] = []
        naive_caps: List[int] = []
        inherited_last = naive_last = 0
        reached = 0
        for row in report["exam"]:
            phases = phase_schedule(row["seed"])
            for name in ("inherited", "naive", "erase_b", "static_b"):
                if not _valid_arm(row[name], phases):
                    return False
                if row[name]["learning"] is not True:
                    return False
            if row["inherited"]["b"] != winner or row["static_b"]["b"] != winner:
                return False
            if row["naive"]["b"] != 0 or row["erase_b"]["b"] != 0:
                return False
            if row["inherited"]["lives"] != row["static_b"]["lives"]:
                return False
            if row["naive"]["lives"] != row["erase_b"]["lives"]:
                return False
            inherited_caps.append(row["inherited"]["capped_episodes_to_criterion"])
            naive_caps.append(row["naive"]["capped_episodes_to_criterion"])
            reached += int(not row["inherited"]["censored"])
            inherited_last += row["inherited"]["successes_last10"]
            naive_last += row["naive"]["successes_last10"]

        if [row["seed"] for row in report["inert_control"]] != list(EXAM_SEEDS):
            return False
        for row in report["inert_control"]:
            phases = phase_schedule(row["seed"])
            for name in ("inherited", "naive"):
                arm = row[name]
                if not _valid_arm(arm, phases, nutrition=0):
                    return False
                if arm["learning"] is not True:
                    return False
                if arm["episodes_to_criterion"] is not None:
                    return False
                if any(life["turns"] != INITIAL_H for life in arm["lives"]):
                    return False

        frozen_caps = []
        if [row["seed"] for row in report["no_q_control"]] != list(EXAM_SEEDS):
            return False
        for row in report["no_q_control"]:
            phases = phase_schedule(row["seed"])
            for name in ("inherited", "naive"):
                if not _valid_arm(row[name], phases):
                    return False
                if row[name]["learning"] is not False:
                    return False
                if row[name]["final"]["q_nonzero"] != 0:
                    return False
            if row["inherited"]["lives"] != row["naive"]["lives"]:
                return False
            frozen_caps.append(row["inherited"]["capped_episodes_to_criterion"])

        headline = {
            "inherited_median": _median(inherited_caps),
            "naive_median": _median(naive_caps),
            "strict_pair_wins": sum(a < b for a, b in
                                    zip(inherited_caps, naive_caps)),
            "inherited_reached": reached,
        }
        if report["headline"] != headline:
            return False
        return (
            reached >= 4
            and headline["inherited_median"] < headline["naive_median"]
            and headline["strict_pair_wins"] >= 3
            and inherited_last >= naive_last
            and headline["inherited_median"] < _median(frozen_caps)
        )
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_gen1_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({"green": report["green"],
                      "transmitted_b": report["transmitted_b"],
                      "headline": report["headline"],
                      "report": str(path)}, indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
