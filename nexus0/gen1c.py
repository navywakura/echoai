"""GEN-1c: inherit evidence needed to calibrate a noisy edge actuator."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.constants import ACTION_WAIT, N_ACTIONS
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import Cell, KIND_EMPTY, KIND_OBJECT
from echoai.nexus0.gen1 import _memory_fingerprint
from echoai.nexus0.loop import Agent


BUDGETS = (1, 2, 4)
DEFAULT_BUDGET = 2
SELECTION_CONTEXTS = (3, 7, 11)
EXAM_CONTEXTS = (5, 9, 13, 17)
SELECTION_SEEDS = (3109, 3121, 3137)
EXAM_SEEDS = (3203, 3221, 3251, 3271, 3299)
LIVES = 50
INITIAL_H = 16
NOISE_TENTHS = 3
PHASE_MODULUS = 30000
WINDOW = 8
CENSORED_CAP = LIVES + 1
SCHEMA = 1


class CalibrationEnv:
    """One observable control context and one noisy terminal consequence."""

    def __init__(self, context: int, seed: int) -> None:
        if type(context) is not int or not 0 <= context < 32:
            raise ValueError("context must be an integer in 0..31")
        if type(seed) is not int:
            raise ValueError("seed must be integer")
        self.context = context
        self.seed = seed
        self.kind = [KIND_EMPTY] * 32
        self.kind[context] = KIND_OBJECT
        self.life = -1
        self.last_reward = 0
        self.reset()

    @property
    def best_action(self) -> int:
        return (self.context + self.seed) & 1

    def reset(self) -> None:
        self.life += 1
        self.last_reward = 0

    def cell(self) -> Cell:
        return Cell(index=self.context, kind=KIND_OBJECT)

    def step_vital(self, action: int, h: int):
        if type(h) is not int or not 1 <= h <= 127:
            raise ValueError("only a living integer H can act")
        aa = int(action) % N_ACTIONS
        roll = (self.seed * 17 + self.context * 7
                + self.life * 31 + aa * 13) % 10
        flipped = roll < NOISE_TENTHS
        if aa == ACTION_WAIT:
            reward = -8
        else:
            reward = 16 if ((aa == self.best_action) != flipped) else -16
        self.last_reward = reward
        return reward, self.cell(), 0

    def step(self, action: int):
        reward, cell, _h = self.step_vital(action, 1)
        return reward, cell

    def teleport(self, _index: int) -> Cell:
        return self.cell()

    def reveal(self, _extract: str) -> bool:
        return False


def phases_for(seed: int) -> Tuple[int, ...]:
    rng = random.Random(int(seed))
    return tuple(rng.randrange(PHASE_MODULUS) for _ in range(LIVES))


def new_agent(budget: int, context: int, seed: int) -> Agent:
    return Agent(env=CalibrationEnv(context, seed), initial_h=INITIAL_H,
                 ask=False, remainder=True, explore_flat=True,
                 evidence_budget=budget, evidence_greedy=False)


def spawn_child(parent: Agent, context: int, seed: int) -> Agent:
    return new_agent(parent.evidence_budget, context, seed)


def _disable_q(agent: Agent) -> None:
    def no_update(_s: int, _a: int, _r: int, _next: int,
                  *, terminal: bool = False) -> int:
        return 0
    agent.q.update = no_update  # type: ignore[method-assign]


def criterion(rows: Sequence[dict]) -> Optional[int]:
    for end in range(WINDOW, len(rows) + 1):
        if all(row.get("success") is True for row in rows[end - WINDOW:end]):
            return end
    return None


def _summary(rows: Sequence[dict]) -> dict:
    value = criterion(rows)
    return {"episodes_to_criterion": value,
            "censored": value is None,
            "capped": CENSORED_CAP if value is None else value,
            "successes": sum(row["success"] for row in rows)}


def run_arm(agent: Agent, phases: Sequence[int], *, learning: bool = True
            ) -> Tuple[dict, Agent]:
    if len(phases) != LIVES:
        raise ValueError("one phase per life required")
    if not learning:
        _disable_q(agent)
    birth = _memory_fingerprint(agent)
    identities = (id(agent.cam), id(agent.q), id(agent.t))
    rows: List[dict] = []
    preserved = True
    for life, phase in enumerate(phases):
        if life:
            agent.respawn()
            preserved &= identities == (id(agent.cam), id(agent.q), id(agent.t))
        turn = life * PHASE_MODULUS + int(phase)
        action = agent.turn(turn)
        cell = agent.env.cell()
        wsp = encode_cell(cell.index, cell.kind, vitality=INITIAL_H)
        slot = agent.cam.get(wsp)
        exam_action = ACTION_WAIT if slot < 0 else agent.q.best(slot)
        rows.append({"life": life + 1, "phase": int(phase),
                     "training_action": action,
                     "evidence_explore": agent.last_evidence_explore,
                     "reward": agent.last_reward,
                     "exam_action": exam_action,
                     "best_action": agent.env.best_action,
                     "q": [] if slot < 0 else agent.q.row(slot),
                     "success": exam_action == agent.env.best_action})
    report = {"budget": agent.evidence_budget, "learning": learning,
              "context": agent.env.context, "seed": agent.env.seed,
              "phases": list(phases), "rows": rows, "birth": birth,
              "final": _memory_fingerprint(agent),
              "respawn_preserves_memory": preserved,
              "deaths": agent.deaths,
              "false_facts": agent.metrics.false_facts,
              "destroyed": agent.cam.destroyed,
              "cortex_calls": agent.metrics.cortex_calls}
    report.update(_summary(rows))
    return report, agent


def _rank(row: dict) -> tuple:
    return row["score"], {2: 0, 1: 1, 4: 2}[row["budget"]]


def select_parent() -> Tuple[dict, Agent]:
    candidates = []
    parents: Dict[int, Agent] = {}
    for budget in BUDGETS:
        arms = []
        for context in SELECTION_CONTEXTS:
            for seed in SELECTION_SEEDS:
                arm, trained = run_arm(new_agent(budget, context, seed),
                                       phases_for(seed))
                arms.append({"context": context, "seed": seed, "arm": arm})
                if context == SELECTION_CONTEXTS[0] and seed == SELECTION_SEEDS[0]:
                    parents[budget] = trained
        score = sum(row["arm"]["capped"] for row in arms)
        candidates.append({"budget": budget, "score": score, "arms": arms})
    winner = min(candidates, key=_rank)["budget"]
    return {"candidates": candidates, "winner": winner}, parents[winner]


def _median(values: Sequence[int]) -> int:
    ordered = sorted(int(value) for value in values)
    return (ordered[(len(ordered) - 1) // 2] + ordered[len(ordered) // 2]) // 2


def experiment() -> dict:
    selection, parent = select_parent()
    winner = selection["winner"]
    exam = []
    for context in EXAM_CONTEXTS:
        for seed in EXAM_SEEDS:
            phases = phases_for(seed)
            inherited, _ = run_arm(spawn_child(parent, context, seed), phases)
            naive, _ = run_arm(new_agent(DEFAULT_BUDGET, context, seed), phases)
            historical, _ = run_arm(new_agent(0, context, seed), phases)
            erased = spawn_child(parent, context, seed)
            erased.evidence_budget = DEFAULT_BUDGET
            erase_b, _ = run_arm(erased, phases)
            direct, _ = run_arm(new_agent(winner, context, seed), phases)
            no_q, _ = run_arm(spawn_child(parent, context, seed), phases,
                              learning=False)
            exam.append({"context": context, "seed": seed,
                         "inherited": inherited, "naive": naive,
                         "historical": historical, "erase_b": erase_b,
                         "direct": direct, "no_q": no_q})
    inherited = [row["inherited"]["capped"] for row in exam]
    naive = [row["naive"]["capped"] for row in exam]
    historical = [row["historical"]["capped"] for row in exam]
    return {"schema": SCHEMA, "slice": "GEN-1c",
            "protocol": {"budgets": list(BUDGETS),
                         "default_budget": DEFAULT_BUDGET,
                         "selection_contexts": list(SELECTION_CONTEXTS),
                         "exam_contexts": list(EXAM_CONTEXTS),
                         "selection_seeds": list(SELECTION_SEEDS),
                         "exam_seeds": list(EXAM_SEEDS), "lives": LIVES,
                         "initial_h": INITIAL_H,
                         "noise_tenths": NOISE_TENTHS,
                         "phase_modulus": PHASE_MODULUS,
                         "window": WINDOW, "censored_cap": CENSORED_CAP},
            "selection": selection, "transmitted_budget": winner,
            "parent_final": _memory_fingerprint(parent), "exam": exam,
            "headline": {"inherited_median": _median(inherited),
                         "naive_median": _median(naive),
                         "historical_median": _median(historical),
                         "inherited_sum": sum(inherited),
                         "naive_sum": sum(naive),
                         "historical_sum": sum(historical),
                         "strict_wins": sum(a < b for a, b in zip(inherited, naive)),
                         "strict_losses": sum(a > b for a, b in zip(inherited, naive)),
                         "reached": sum(a < CENSORED_CAP for a in inherited)}}


def _valid_arm(arm: dict, context: int, seed: int) -> bool:
    phases = phases_for(seed)
    if (arm["context"] != context or arm["seed"] != seed
            or arm["phases"] != list(phases) or len(arm["rows"]) != LIVES
            or arm["deaths"] != LIVES
            or arm["respawn_preserves_memory"] is not True
            or any(arm[k] != 0 for k in
                   ("false_facts", "destroyed", "cortex_calls"))):
        return False
    if any(arm["birth"][k] != 0 for k in
           ("cam_occupied", "q_nonzero", "rem_nonzero", "t_known")):
        return False
    for i, row in enumerate(arm["rows"]):
        if (row["life"] != i + 1 or row["phase"] != phases[i]
                or row["training_action"] not in range(N_ACTIONS)
                or row["exam_action"] not in range(N_ACTIONS)
                or row["best_action"] not in (0, 1)
                or row["success"] is not
                (row["exam_action"] == row["best_action"])):
            return False
    return all(arm[k] == value for k, value in _summary(arm["rows"]).items())


def green(report: dict) -> bool:
    try:
        if report["schema"] != SCHEMA or report["slice"] != "GEN-1c":
            return False
        p = report["protocol"]
        if (p["budgets"], p["default_budget"], p["selection_contexts"],
                p["exam_contexts"], p["selection_seeds"], p["exam_seeds"],
                p["lives"], p["initial_h"], p["noise_tenths"],
                p["phase_modulus"], p["window"], p["censored_cap"]) != (
                    list(BUDGETS), DEFAULT_BUDGET, list(SELECTION_CONTEXTS),
                    list(EXAM_CONTEXTS), list(SELECTION_SEEDS), list(EXAM_SEEDS),
                    LIVES, INITIAL_H, NOISE_TENTHS, PHASE_MODULUS, WINDOW,
                    CENSORED_CAP):
            return False
        candidates = report["selection"]["candidates"]
        if [x["budget"] for x in candidates] != list(BUDGETS):
            return False
        selection_keys = [(c, s) for c in SELECTION_CONTEXTS
                          for s in SELECTION_SEEDS]
        for candidate in candidates:
            if [(x["context"], x["seed"]) for x in candidate["arms"]] != selection_keys:
                return False
            score = 0
            for row in candidate["arms"]:
                if (not _valid_arm(row["arm"], row["context"], row["seed"])
                        or row["arm"]["budget"] != candidate["budget"]):
                    return False
                score += row["arm"]["capped"]
            if score != candidate["score"]:
                return False
        winner = min(candidates, key=_rank)["budget"]
        if (report["selection"]["winner"] != winner
                or report["transmitted_budget"] != winner):
            return False
        winner_row = next(x for x in candidates if x["budget"] == winner)
        if report["parent_final"] != winner_row["arms"][0]["arm"]["final"]:
            return False

        exam_keys = [(c, s) for c in EXAM_CONTEXTS for s in EXAM_SEEDS]
        if [(x["context"], x["seed"]) for x in report["exam"]] != exam_keys:
            return False
        inherited = []
        naive = []
        historical = []
        no_q_reached = 0
        for row in report["exam"]:
            for name in ("inherited", "naive", "historical", "erase_b",
                         "direct", "no_q"):
                if not _valid_arm(row[name], row["context"], row["seed"]):
                    return False
            if (row["inherited"]["budget"] != winner
                    or row["direct"]["budget"] != winner
                    or row["naive"]["budget"] != DEFAULT_BUDGET
                    or row["erase_b"]["budget"] != DEFAULT_BUDGET
                    or row["historical"]["budget"] != 0
                    or row["no_q"]["learning"] is not False):
                return False
            if (row["inherited"]["rows"] != row["direct"]["rows"]
                    or row["naive"]["rows"] != row["erase_b"]["rows"]):
                return False
            inherited.append(row["inherited"]["capped"])
            naive.append(row["naive"]["capped"])
            historical.append(row["historical"]["capped"])
            no_q_reached += int(not row["no_q"]["censored"])
        headline = {"inherited_median": _median(inherited),
                    "naive_median": _median(naive),
                    "historical_median": _median(historical),
                    "inherited_sum": sum(inherited), "naive_sum": sum(naive),
                    "historical_sum": sum(historical),
                    "strict_wins": sum(a < b for a, b in zip(inherited, naive)),
                    "strict_losses": sum(a > b for a, b in zip(inherited, naive)),
                    "reached": sum(a < CENSORED_CAP for a in inherited)}
        if report["headline"] != headline:
            return False
        return (winner != DEFAULT_BUDGET and headline["reached"] >= 18
                and headline["inherited_median"] < headline["naive_median"]
                and 5 * headline["inherited_sum"] <= 4 * headline["naive_sum"]
                and headline["strict_wins"] >= 10
                and headline["strict_losses"] <= 4
                and headline["inherited_sum"] < headline["historical_sum"]
                and no_q_reached == 0)
    except (KeyError, TypeError, ValueError, IndexError, StopIteration):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_gen1c_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({"green": report["green"],
                      "transmitted_budget": report["transmitted_budget"],
                      "headline": report["headline"], "report": str(path)},
                     indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
