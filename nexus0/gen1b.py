"""GEN-1b: inherit a local evidence budget; examine frozen learned policy."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0 import body3d as cube
from echoai.nexus0.constants import ACTION_WAIT, N_ACTIONS
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.food1 import FoodEnv
from echoai.nexus0.gate import gate
from echoai.nexus0.gen1 import _memory_fingerprint
from echoai.nexus0.loop import Agent
from echoai.nexus0.types import default_e
from echoai.nexus0.vita1 import VitalEnv


BUDGETS = (1, 2, 4)
DEFAULT_BUDGET = 2
SELECTION_ITEMS = ((1, 0, 0), (0, 1, 0), (2, 0, 0))
EXAM_ITEMS = ((0, 2, 0), (2, 1, 0), (0, 2, 1), (2, 2, 0), (1, 2, 1))
SELECTION_SEEDS = (701, 809, 907)
EXAM_SEEDS = (1009, 1103, 1201, 1301, 1409)
LIVES = 40
INITIAL_H = 16
NUTRITION = 24
PHASE_MODULUS = 30000
WINDOW = 4
WINDOW_SUCCESSES = 3
CENSORED_CAP = LIVES + 1
SCHEMA = 1


class ForageEnv(FoodEnv):
    """FOOD-1 physics with the same-looking item at a fixed floor voxel."""

    def __init__(self, item: Sequence[int], nutrition: int = NUTRITION) -> None:
        xyz = tuple(int(v) for v in item)
        if len(xyz) != 3 or xyz not in cube.floor_of(cube.LAYOUT_OPEN):
            raise ValueError("item must be one reachable open-layout voxel")
        if xyz == cube.START_XYZ:
            raise ValueError("item cannot begin under the body")
        self.item_xyz = xyz
        super().__init__(nutrition)

    def reset(self) -> None:
        super().reset()
        self.obj = self.item_xyz
        self.coupled = False
        self.i = cube.index_of(*cube.START_XYZ, cube.PLUS_X)
        self._paint()


def phases_for(seed: int) -> Tuple[int, ...]:
    rng = random.Random(int(seed))
    return tuple(rng.randrange(PHASE_MODULUS) for _ in range(LIVES))


def new_agent(budget: int, item: Sequence[int], *, nutrition: int = NUTRITION
              ) -> Agent:
    return Agent(
        env=VitalEnv(ForageEnv(item, nutrition)),
        initial_h=INITIAL_H,
        ask=False,
        remainder=True,
        explore_flat=True,
        evidence_budget=budget,
        evidence_greedy=False,
    )


def spawn_child(parent: Agent, item: Sequence[int], *, nutrition: int = NUTRITION
                ) -> Agent:
    return new_agent(parent.evidence_budget, item, nutrition=nutrition)


def _disable_q(agent: Agent) -> None:
    def no_update(_s: int, _a: int, _r: int, _next: int,
                  *, terminal: bool = False) -> int:
        return 0
    agent.q.update = no_update  # type: ignore[method-assign]


def frozen_exam(agent: Agent, item: Sequence[int], *, nutrition: int = NUTRITION
                ) -> dict:
    """Read CAM/Q and run fresh physics; never write trained memory."""
    env = VitalEnv(ForageEnv(item, nutrition))
    h = INITIAL_H
    before = (agent.cam.used, agent.cam.destroyed, agent.t.conflicts,
              agent.t.inv_dropped, tuple(agent.q._active))
    touched: Dict[int, tuple] = {}
    trace: List[List[int]] = []
    unknown = 0
    limit = INITIAL_H + max(0, nutrition)
    while h > 0 and len(trace) < limit:
        cell = env.cell()
        wsp = encode_cell(cell.index, cell.kind, vitality=h)
        slot = agent.cam.get(wsp)
        unknown += int(slot < 0)
        if slot >= 0 and slot not in touched:
            source = agent.cam.slot[slot]
            touched[slot] = (tuple(agent.q.row(slot)), source.wsp,
                             source.hits, source.weight, source.flags)
        proposed = ACTION_WAIT if slot < 0 else agent.q.best(slot)
        e6 = default_e()
        e6 = (*e6[:4], wsp[8], e6[5])
        inhibit = bool(slot >= 0 and agent.cam.slot[slot].flags & 0x04)
        decision, action, _flags = gate(
            wsp,
            cam_hit=slot >= 0,
            extract_ok=bool(cell.extract),
            E=e6,
            proposed=proposed,
            inhibit=inhibit,
            threat=cell.threat,
            n_actions=N_ACTIONS,
        )
        reward, _next, h_next = env.step_vital(action, h)
        trace.append([cell.index, h, proposed, decision, action,
                      int(reward), int(h_next)])
        h = h_next
    after = (agent.cam.used, agent.cam.destroyed, agent.t.conflicts,
             agent.t.inv_dropped, tuple(agent.q._active))
    rows_unchanged = all(
        snapshot == (tuple(agent.q.row(slot)), agent.cam.slot[slot].wsp,
                     agent.cam.slot[slot].hits, agent.cam.slot[slot].weight,
                     agent.cam.slot[slot].flags)
        for slot, snapshot in touched.items()
    )
    return {
        "success": env.consumed == 1 and h == 0 and len(trace) == limit,
        "turns": len(trace),
        "terminal": h == 0,
        "h": h,
        "consumed": env.consumed,
        "unknown": unknown,
        "trace": trace,
        "source_unchanged": before == after and rows_unchanged,
    }


def episodes_to_criterion(evaluations: Sequence[dict]) -> Optional[int]:
    success = [row.get("success") is True for row in evaluations]
    for end in range(WINDOW, len(success) + 1):
        if sum(success[end - WINDOW:end]) >= WINDOW_SUCCESSES:
            return end
    return None


def _summary(evaluations: Sequence[dict]) -> dict:
    criterion = episodes_to_criterion(evaluations)
    return {
        "episodes_to_criterion": criterion,
        "censored": criterion is None,
        "capped": CENSORED_CAP if criterion is None else criterion,
        "exam_successes": sum(row["success"] for row in evaluations),
        "exam_successes_last8": sum(row["success"] for row in evaluations[-8:]),
    }


def run_arm(agent: Agent, phases: Sequence[int], item: Sequence[int], *,
            learning: bool = True) -> Tuple[dict, Agent]:
    if len(phases) != LIVES:
        raise ValueError("one phase per life required")
    if not learning:
        _disable_q(agent)
    birth = _memory_fingerprint(agent)
    identities = (id(agent.cam), id(agent.q), id(agent.t))
    training = []
    evaluations = []
    preserved = True
    for life, phase in enumerate(phases):
        if life:
            agent.respawn()
            preserved &= identities == (id(agent.cam), id(agent.q), id(agent.t))
        actions = [0] * N_ACTIONS
        evidence_turns = 0
        reward_sum = 0
        limit = INITIAL_H + max(0, agent.env.nutrition)
        while not agent.episode_terminal and agent.life_turns < limit:
            turn = life * PHASE_MODULUS + int(phase) + agent.life_turns
            action = agent.turn(turn)
            actions[action] += 1
            evidence_turns += int(agent.last_evidence_explore)
            reward_sum += agent.last_reward
        training.append({
            "life": life + 1,
            "phase": int(phase),
            "turns": agent.life_turns,
            "terminal": agent.episode_terminal,
            "h": agent.H,
            "consumed": agent.env.consumed,
            "actions": actions,
            "evidence_turns": evidence_turns,
            "reward_sum": reward_sum,
        })
        evaluation = frozen_exam(agent, item, nutrition=agent.env.nutrition)
        evaluation["life"] = life + 1
        evaluations.append(evaluation)

    report = {
        "budget": agent.evidence_budget,
        "learning": learning,
        "item": list(item),
        "phases": list(phases),
        "training": training,
        "evaluations": evaluations,
        "birth": birth,
        "final": _memory_fingerprint(agent),
        "respawn_preserves_memory": preserved,
        "deaths": agent.deaths,
        "false_facts": agent.metrics.false_facts,
        "destroyed": agent.cam.destroyed,
        "cortex_calls": agent.metrics.cortex_calls,
    }
    report.update(_summary(evaluations))
    return report, agent


def _rank(row: dict) -> tuple:
    tie = {2: 0, 1: 1, 4: 2}[row["budget"]]
    return row["score"], tie


def select_parent() -> Tuple[dict, Agent]:
    candidates = []
    parents: Dict[int, Agent] = {}
    for budget in BUDGETS:
        arms = []
        for item in SELECTION_ITEMS:
            for seed in SELECTION_SEEDS:
                arm, trained = run_arm(
                    new_agent(budget, item), phases_for(seed), item
                )
                arms.append({"item": list(item), "seed": seed, "arm": arm})
                if item == SELECTION_ITEMS[0] and seed == SELECTION_SEEDS[0]:
                    parents[budget] = trained
        score = sum(row["arm"]["capped"] for row in arms)
        candidates.append({"budget": budget, "score": score, "arms": arms})
    winner = min(candidates, key=_rank)["budget"]
    return {"candidates": candidates, "winner": winner}, parents[winner]


def _median(values: Sequence[int]) -> int:
    ordered = sorted(int(v) for v in values)
    return ordered[len(ordered) // 2]


def experiment() -> dict:
    selection, parent = select_parent()
    winner = selection["winner"]
    exam = []
    for item in EXAM_ITEMS:
        for seed in EXAM_SEEDS:
            phases = phases_for(seed)
            inherited, _ = run_arm(spawn_child(parent, item), phases, item)
            naive, _ = run_arm(new_agent(DEFAULT_BUDGET, item), phases, item)
            historical, _ = run_arm(new_agent(0, item), phases, item)
            erased = spawn_child(parent, item)
            erased.evidence_budget = DEFAULT_BUDGET
            erase_b, _ = run_arm(erased, phases, item)
            direct, _ = run_arm(new_agent(winner, item), phases, item)
            no_q, _ = run_arm(spawn_child(parent, item), phases, item,
                              learning=False)
            exam.append({"item": list(item), "seed": seed,
                         "inherited": inherited, "naive": naive,
                         "historical": historical, "erase_b": erase_b,
                         "direct": direct, "no_q": no_q})

    inert = []
    item = EXAM_ITEMS[0]
    for seed in EXAM_SEEDS:
        phases = phases_for(seed)
        inherited, _ = run_arm(spawn_child(parent, item, nutrition=0),
                               phases, item)
        naive, _ = run_arm(new_agent(DEFAULT_BUDGET, item, nutrition=0),
                           phases, item)
        inert.append({"seed": seed, "item": list(item),
                      "inherited": inherited, "naive": naive})

    inherited_caps = [row["inherited"]["capped"] for row in exam]
    naive_caps = [row["naive"]["capped"] for row in exam]
    historical_caps = [row["historical"]["capped"] for row in exam]
    return {
        "schema": SCHEMA,
        "slice": "GEN-1b",
        "protocol": {
            "budgets": list(BUDGETS), "default_budget": DEFAULT_BUDGET,
            "selection_items": [list(x) for x in SELECTION_ITEMS],
            "exam_items": [list(x) for x in EXAM_ITEMS],
            "selection_seeds": list(SELECTION_SEEDS),
            "exam_seeds": list(EXAM_SEEDS), "lives": LIVES,
            "initial_h": INITIAL_H, "nutrition": NUTRITION,
            "phase_modulus": PHASE_MODULUS, "window": WINDOW,
            "window_successes": WINDOW_SUCCESSES,
            "censored_cap": CENSORED_CAP,
        },
        "selection": selection,
        "transmitted_budget": winner,
        "parent_final": _memory_fingerprint(parent),
        "exam": exam,
        "inert_control": inert,
        "headline": {
            "inherited_median": _median(inherited_caps),
            "naive_median": _median(naive_caps),
            "historical_median": _median(historical_caps),
            "strict_pair_wins": sum(a < b for a, b in
                                    zip(inherited_caps, naive_caps)),
            "inherited_reached": sum(v < CENSORED_CAP for v in inherited_caps),
        },
    }


def _valid_arm(arm: dict, phases: Sequence[int], item: Sequence[int], *,
               nutrition: int = NUTRITION) -> bool:
    if (arm["item"] != list(item) or arm["phases"] != list(phases)
            or len(arm["training"]) != LIVES
            or len(arm["evaluations"]) != LIVES):
        return False
    if arm["budget"] not in (0, *BUDGETS) or type(arm["learning"]) is not bool:
        return False
    if (arm["deaths"] != LIVES or arm["respawn_preserves_memory"] is not True
            or any(arm[k] != 0 for k in
                   ("false_facts", "destroyed", "cortex_calls"))):
        return False
    if any(arm["birth"][k] != 0 for k in
           ("cam_occupied", "q_nonzero", "rem_nonzero", "t_known")):
        return False
    for i, (train, evaluation) in enumerate(zip(arm["training"],
                                                arm["evaluations"])):
        if (train["life"] != i + 1 or train["phase"] != phases[i]
                or train["terminal"] is not True or train["h"] != 0
                or train["consumed"] not in (0, 1)
                or train["turns"] != INITIAL_H + max(0, nutrition) * train["consumed"]
                or sum(train["actions"]) != train["turns"]):
            return False
        if (evaluation["life"] != i + 1
                or evaluation["terminal"] is not True
                or evaluation["h"] != 0
                or evaluation["consumed"] not in (0, 1)
                or evaluation["source_unchanged"] is not True
                or len(evaluation["trace"]) != evaluation["turns"]):
            return False
        expected_success = (evaluation["consumed"] == 1
                            and evaluation["turns"] == INITIAL_H + max(0, nutrition))
        if evaluation["success"] is not expected_success:
            return False
    return all(arm[k] == v for k, v in _summary(arm["evaluations"]).items())


def green(report: dict) -> bool:
    try:
        if report["schema"] != SCHEMA or report["slice"] != "GEN-1b":
            return False
        p = report["protocol"]
        if (p["budgets"], p["default_budget"], p["selection_items"],
                p["exam_items"], p["selection_seeds"], p["exam_seeds"],
                p["lives"], p["initial_h"], p["nutrition"],
                p["phase_modulus"], p["window"], p["window_successes"],
                p["censored_cap"]) != (
                    list(BUDGETS), DEFAULT_BUDGET,
                    [list(x) for x in SELECTION_ITEMS],
                    [list(x) for x in EXAM_ITEMS], list(SELECTION_SEEDS),
                    list(EXAM_SEEDS), LIVES, INITIAL_H, NUTRITION,
                    PHASE_MODULUS, WINDOW, WINDOW_SUCCESSES, CENSORED_CAP):
            return False

        candidates = report["selection"]["candidates"]
        if [x["budget"] for x in candidates] != list(BUDGETS):
            return False
        expected_keys = [(list(item), seed) for item in SELECTION_ITEMS
                         for seed in SELECTION_SEEDS]
        for candidate in candidates:
            if [(x["item"], x["seed"]) for x in candidate["arms"]] != expected_keys:
                return False
            score = 0
            for row in candidate["arms"]:
                if not _valid_arm(row["arm"], phases_for(row["seed"]), row["item"]):
                    return False
                if row["arm"]["budget"] != candidate["budget"]:
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

        expected_exam = [(list(item), seed) for item in EXAM_ITEMS
                         for seed in EXAM_SEEDS]
        if [(x["item"], x["seed"]) for x in report["exam"]] != expected_exam:
            return False
        inherited_caps = []
        naive_caps = []
        historical_caps = []
        no_q_reached = 0
        for row in report["exam"]:
            phases = phases_for(row["seed"])
            for name in ("inherited", "naive", "historical", "erase_b",
                         "direct", "no_q"):
                if not _valid_arm(row[name], phases, row["item"]):
                    return False
            if (row["inherited"]["budget"] != winner
                    or row["direct"]["budget"] != winner
                    or row["naive"]["budget"] != DEFAULT_BUDGET
                    or row["erase_b"]["budget"] != DEFAULT_BUDGET
                    or row["historical"]["budget"] != 0
                    or row["no_q"]["learning"] is not False):
                return False
            if (row["inherited"]["training"] != row["direct"]["training"]
                    or row["inherited"]["evaluations"] != row["direct"]["evaluations"]
                    or row["naive"]["training"] != row["erase_b"]["training"]
                    or row["naive"]["evaluations"] != row["erase_b"]["evaluations"]):
                return False
            inherited_caps.append(row["inherited"]["capped"])
            naive_caps.append(row["naive"]["capped"])
            historical_caps.append(row["historical"]["capped"])
            no_q_reached += int(not row["no_q"]["censored"])

        if [(x["item"], x["seed"]) for x in report["inert_control"]] != [
                (list(EXAM_ITEMS[0]), seed) for seed in EXAM_SEEDS]:
            return False
        for row in report["inert_control"]:
            for name in ("inherited", "naive"):
                arm = row[name]
                if not _valid_arm(arm, phases_for(row["seed"]), row["item"],
                                  nutrition=0):
                    return False
                if any(x["turns"] != INITIAL_H for x in arm["training"]):
                    return False

        headline = {
            "inherited_median": _median(inherited_caps),
            "naive_median": _median(naive_caps),
            "historical_median": _median(historical_caps),
            "strict_pair_wins": sum(a < b for a, b in
                                    zip(inherited_caps, naive_caps)),
            "inherited_reached": sum(v < CENSORED_CAP for v in inherited_caps),
        }
        if report["headline"] != headline:
            return False
        return (winner != DEFAULT_BUDGET
                and headline["inherited_reached"] >= 20
                and headline["strict_pair_wins"] >= 15
                and headline["inherited_median"] < headline["naive_median"]
                and headline["inherited_median"] <= headline["historical_median"]
                and no_q_reached == 0)
    except (KeyError, TypeError, ValueError, IndexError, StopIteration):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_gen1b_report.json"
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
