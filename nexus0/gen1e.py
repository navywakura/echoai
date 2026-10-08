"""GEN-1e: confirm inherited local caution on paired actuator noise."""
from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.constants import ACTION_WAIT, N_ACTIONS
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import Cell, KIND_EMPTY, KIND_OBJECT
from echoai.nexus0.gen1 import _memory_fingerprint
from echoai.nexus0.loop import Agent


BUDGETS = (1, 2, 4, 8)
DEFAULT_BUDGET = 2
LIVES = 48
INITIAL_H = 16
PHASE_MODULUS = 30000
WINDOW = 8
SCORE_START = 24
CENSORED_CAP = LIVES + 1
SELECTION_N = 24
EXAM_N = 64
DOMAIN = "ECHO-AI/GEN-1e/2026-09-09"
SCHEMA = 1
MASK64 = (1 << 64) - 1


def derived_pairs(partition: str, count: int) -> Tuple[Tuple[int, int], ...]:
    rows = []
    for index in range(count):
        material = f"{DOMAIN}/{partition}/{index}".encode("ascii")
        digest = hashlib.sha256(material).digest()
        rows.append((digest[0] % 32, int.from_bytes(digest[1:5], "big")))
    return tuple(rows)


def pairs_hash(rows: Sequence[Tuple[int, int]]) -> str:
    body = ";".join(f"{context}:{seed}" for context, seed in rows)
    return hashlib.sha256(body.encode("ascii")).hexdigest()


SELECTION_PAIRS = derived_pairs("selection", SELECTION_N)
EXAM_PAIRS = derived_pairs("exam", EXAM_N)


def _mix64(value: int) -> int:
    value = (int(value) + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return value ^ (value >> 31)


def noisy(seed: int, context: int, life: int) -> bool:
    key = (int(seed) ^ (int(context) * 0xD6E8FEB86659FD93)
           ^ (int(life) * 0xA0761D6478BD642F)) & MASK64
    return (_mix64(key) >> 32) < ((3 * (1 << 32)) // 10)


class CalibrationEnv:
    """One context, one terminal command and action-independent noise."""

    def __init__(self, context: int, seed: int) -> None:
        if type(context) is not int or not 0 <= context < 32:
            raise ValueError("context must be an integer in 0..31")
        if type(seed) is not int or not 0 <= seed < (1 << 32):
            raise ValueError("seed must be an unsigned 32-bit integer")
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
        if aa == ACTION_WAIT:
            reward = -8
        else:
            reward = 16 if ((aa == self.best_action) != noisy(
                self.seed, self.context, self.life)) else -16
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
                 evidence_budget=budget)


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
    return {
        "episodes_to_criterion": value,
        "censored": value is None,
        "capped": CENSORED_CAP if value is None else value,
        "successes": sum(row["success"] for row in rows),
        "late_errors": sum(not row["success"] for row in rows[SCORE_START:]),
    }


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
        action = agent.turn(life * PHASE_MODULUS + int(phase))
        cell = agent.env.cell()
        wsp = encode_cell(cell.index, cell.kind, vitality=INITIAL_H)
        slot = agent.cam.get(wsp)
        before = None if slot < 0 else (
            tuple(agent.q.row(slot)), agent.cam.slot[slot].hits,
            tuple(agent.t.n[slot]))
        exam_action = ACTION_WAIT if slot < 0 else agent.q.best(slot)
        after = None if slot < 0 else (
            tuple(agent.q.row(slot)), agent.cam.slot[slot].hits,
            tuple(agent.t.n[slot]))
        rows.append({
            "life": life + 1, "phase": int(phase),
            "training_action": action,
            "evidence_explore": agent.last_evidence_explore,
            "noise": noisy(agent.env.seed, agent.env.context, life),
            "reward": agent.last_reward, "exam_action": exam_action,
            "best_action": agent.env.best_action,
            "q": [] if slot < 0 else agent.q.row(slot),
            "exam_unchanged": before == after,
            "success": exam_action == agent.env.best_action,
        })
    report = {
        "budget": agent.evidence_budget, "learning": learning,
        "context": agent.env.context, "seed": agent.env.seed,
        "phases": list(phases), "rows": rows, "birth": birth,
        "final": _memory_fingerprint(agent),
        "respawn_preserves_memory": preserved, "deaths": agent.deaths,
        "false_facts": agent.metrics.false_facts,
        "destroyed": agent.cam.destroyed,
        "cortex_calls": agent.metrics.cortex_calls,
    }
    report.update(_summary(rows))
    return report, agent


def _rank(row: dict) -> tuple:
    return row["score"], {2: 0, 1: 1, 4: 2, 8: 3}[row["budget"]]


def select_parent() -> Tuple[dict, Agent]:
    candidates = []
    parents: Dict[int, Agent] = {}
    for budget in BUDGETS:
        arms = []
        for index, (context, seed) in enumerate(SELECTION_PAIRS):
            arm, trained = run_arm(new_agent(budget, context, seed),
                                   phases_for(seed))
            arms.append({"index": index, "context": context, "seed": seed,
                         "arm": arm})
            if index == 0:
                parents[budget] = trained
        candidates.append({"budget": budget,
                           "score": sum(x["arm"]["late_errors"] for x in arms),
                           "arms": arms})
    winner = min(candidates, key=_rank)["budget"]
    return {"candidates": candidates, "winner": winner}, parents[winner]


def _median(values: Sequence[int]) -> int:
    values = sorted(int(x) for x in values)
    return (values[(len(values) - 1) // 2] + values[len(values) // 2]) // 2


def _sign_test(wins: int, losses: int) -> Tuple[int, int]:
    n = wins + losses
    if n == 0:
        return 1, 1
    numerator = sum(math.comb(n, k) for k in range(losses + 1))
    return numerator, 1 << n


def experiment() -> dict:
    selection, parent = select_parent()
    winner = selection["winner"]
    exam = []
    for index, (context, seed) in enumerate(EXAM_PAIRS):
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
        exam.append({"index": index, "context": context, "seed": seed,
                     "inherited": inherited, "naive": naive,
                     "historical": historical, "erase_b": erase_b,
                     "direct": direct, "no_q": no_q})
    inherited = [x["inherited"]["late_errors"] for x in exam]
    naive = [x["naive"]["late_errors"] for x in exam]
    historical = [x["historical"]["late_errors"] for x in exam]
    wins = sum(a < b for a, b in zip(inherited, naive))
    losses = sum(a > b for a, b in zip(inherited, naive))
    p_num, p_den = _sign_test(wins, losses)
    return {
        "schema": SCHEMA, "slice": "GEN-1e",
        "protocol": {
            "budgets": list(BUDGETS), "default_budget": DEFAULT_BUDGET,
            "lives": LIVES, "initial_h": INITIAL_H,
            "phase_modulus": PHASE_MODULUS, "window": WINDOW,
            "score_start": SCORE_START, "censored_cap": CENSORED_CAP,
            "domain": DOMAIN, "selection_n": SELECTION_N,
            "exam_n": EXAM_N,
            "selection_pairs_hash": pairs_hash(SELECTION_PAIRS),
            "exam_pairs_hash": pairs_hash(EXAM_PAIRS),
            "selection_pairs": [list(x) for x in SELECTION_PAIRS],
            "exam_pairs": [list(x) for x in EXAM_PAIRS],
        },
        "selection": selection, "transmitted_budget": winner,
        "parent_final": _memory_fingerprint(parent), "exam": exam,
        "headline": {
            "inherited_late_errors": sum(inherited),
            "naive_late_errors": sum(naive),
            "historical_late_errors": sum(historical),
            "inherited_median_errors": _median(inherited),
            "naive_median_errors": _median(naive),
            "strict_wins": wins, "strict_losses": losses,
            "ties": EXAM_N - wins - losses,
            "sign_p_numerator": p_num, "sign_p_denominator": p_den,
            "reached": sum(not x["inherited"]["censored"] for x in exam),
        },
    }


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
    env = CalibrationEnv(context, seed)
    for i, row in enumerate(arm["rows"]):
        if i:
            env.reset()
        action = row["training_action"]
        expected_reward, _cell, _h = env.step_vital(action, INITIAL_H)
        if (row["life"] != i + 1 or row["phase"] != phases[i]
                or action not in range(N_ACTIONS)
                or row["noise"] is not noisy(seed, context, i)
                or row["reward"] != expected_reward
                or row["exam_action"] not in range(N_ACTIONS)
                or row["best_action"] != env.best_action
                or row["exam_unchanged"] is not True
                or row["success"] is not
                (row["exam_action"] == row["best_action"])):
            return False
    return all(arm[k] == value for k, value in _summary(arm["rows"]).items())


def green(report: dict) -> bool:
    try:
        if report["schema"] != SCHEMA or report["slice"] != "GEN-1e":
            return False
        p = report["protocol"]
        expected_protocol = {
            "budgets": list(BUDGETS), "default_budget": DEFAULT_BUDGET,
            "lives": LIVES, "initial_h": INITIAL_H,
            "phase_modulus": PHASE_MODULUS, "window": WINDOW,
            "score_start": SCORE_START, "censored_cap": CENSORED_CAP,
            "domain": DOMAIN, "selection_n": SELECTION_N,
            "exam_n": EXAM_N,
            "selection_pairs_hash": pairs_hash(SELECTION_PAIRS),
            "exam_pairs_hash": pairs_hash(EXAM_PAIRS),
            "selection_pairs": [list(x) for x in SELECTION_PAIRS],
            "exam_pairs": [list(x) for x in EXAM_PAIRS],
        }
        if p != expected_protocol:
            return False
        candidates = report["selection"]["candidates"]
        if [x["budget"] for x in candidates] != list(BUDGETS):
            return False
        for candidate in candidates:
            score = 0
            if len(candidate["arms"]) != SELECTION_N:
                return False
            for index, row in enumerate(candidate["arms"]):
                context, seed = SELECTION_PAIRS[index]
                if ((row["index"], row["context"], row["seed"])
                        != (index, context, seed)
                        or not _valid_arm(row["arm"], context, seed)
                        or row["arm"]["budget"] != candidate["budget"]):
                    return False
                score += row["arm"]["late_errors"]
            if score != candidate["score"]:
                return False
        winner = min(candidates, key=_rank)["budget"]
        if (report["selection"]["winner"] != winner
                or report["transmitted_budget"] != winner):
            return False
        winner_row = next(x for x in candidates if x["budget"] == winner)
        if report["parent_final"] != winner_row["arms"][0]["arm"]["final"]:
            return False

        inherited = []
        naive = []
        historical = []
        reached = 0
        no_q_successes = 0
        no_q_reached = 0
        if len(report["exam"]) != EXAM_N:
            return False
        for index, row in enumerate(report["exam"]):
            context, seed = EXAM_PAIRS[index]
            if ((row["index"], row["context"], row["seed"])
                    != (index, context, seed)):
                return False
            for name in ("inherited", "naive", "historical", "erase_b",
                         "direct", "no_q"):
                if not _valid_arm(row[name], context, seed):
                    return False
            if (row["inherited"]["budget"] != winner
                    or row["direct"]["budget"] != winner
                    or row["naive"]["budget"] != DEFAULT_BUDGET
                    or row["erase_b"]["budget"] != DEFAULT_BUDGET
                    or row["historical"]["budget"] != 0
                    or row["no_q"]["learning"] is not False
                    or row["inherited"]["rows"] != row["direct"]["rows"]
                    or row["inherited"]["final"] != row["direct"]["final"]
                    or row["naive"]["rows"] != row["erase_b"]["rows"]
                    or row["naive"]["final"] != row["erase_b"]["final"]
                    or row["no_q"]["final"]["q_nonzero"] != 0
                    or row["no_q"]["final"]["rem_nonzero"] != 0):
                return False
            inherited.append(row["inherited"]["late_errors"])
            naive.append(row["naive"]["late_errors"])
            historical.append(row["historical"]["late_errors"])
            reached += int(not row["inherited"]["censored"])
            no_q_successes += row["no_q"]["successes"]
            no_q_reached += int(not row["no_q"]["censored"])
        wins = sum(a < b for a, b in zip(inherited, naive))
        losses = sum(a > b for a, b in zip(inherited, naive))
        p_num, p_den = _sign_test(wins, losses)
        headline = {
            "inherited_late_errors": sum(inherited),
            "naive_late_errors": sum(naive),
            "historical_late_errors": sum(historical),
            "inherited_median_errors": _median(inherited),
            "naive_median_errors": _median(naive),
            "strict_wins": wins, "strict_losses": losses,
            "ties": EXAM_N - wins - losses,
            "sign_p_numerator": p_num, "sign_p_denominator": p_den,
            "reached": reached,
        }
        if report["headline"] != headline:
            return False
        return (winner == 8 and reached >= 60
                and 10 * sum(inherited) <= 7 * sum(naive)
                and sum(inherited) < sum(historical)
                and wins > losses and 100 * p_num <= p_den
                and no_q_successes == 0 and no_q_reached == 0)
    except (KeyError, TypeError, ValueError, IndexError, StopIteration):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_gen1e_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps({"green": report["green"],
                      "transmitted_budget": report["transmitted_budget"],
                      "selection": [(x["budget"], x["score"])
                                    for x in report["selection"]["candidates"]],
                      "headline": report["headline"], "report": str(path)},
                     indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
