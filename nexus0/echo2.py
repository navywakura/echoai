"""Reproducible VITA-1 / FOOD-1 / SURV-1 probes. No hardware or LLM.

FOOD-1 isolates consumption with an item already in hand. SURV-1 starts
at the canonical cube START and must acquire that same item by walking.
One finite item per life: lifespan is bounded by initial H + nutrition.
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from statistics import median

from echoai.nexus0 import body3d as cube
from echoai.nexus0.food1 import FoodEnv
from echoai.nexus0.loop import Agent
from echoai.nexus0.obj1 import ITEM_XYZ
from echoai.nexus0.qtable import QTable
from echoai.nexus0.vita1 import VitalEnv
from echoai.nexus0.world import World

SEEDS = (17, 101, 20260903)
LIVES = 50
INITIAL_H = 16
NUTRITION = 24


def new_agent(nutrition=NUTRITION, initial_h=INITIAL_H):
    return Agent(env=VitalEnv(FoodEnv(nutrition)), initial_h=initial_h,
                 ask=False, remainder=True, explore_flat=True)


def food_probe():
    rows = {}
    for name, nutrition in (("food", 24), ("poison", -24), ("inert", 0)):
        a = new_agent(nutrition, initial_h=8)
        pose = cube.index_of(*ITEM_XYZ, 0)
        for life in range(32):
            a.env.teleport(pose)
            a.run(40)
            if not a.episode_terminal:
                raise RuntimeError("finite food did not terminate the life")
            a.respawn()
        a.env.teleport(pose)
        slot = a.cam.get(a.observation(a.env.cell()))
        before = a.H
        row = a.q.row(slot)
        action = a.turn(a.metrics.turns, greedy=True)
        rows[name] = dict(action=action, q=row, h_before=before, h_after=a.H,
                          consumed=a.env.consumed, false_facts=a.metrics.false_facts,
                          destroyed=a.cam.destroyed, cortex_calls=a.metrics.cortex_calls)
    return rows


def survival_arm(seed, persist, *, nutrition=NUTRITION):
    rng = random.Random(seed)
    a = new_agent(nutrition)
    lives = []
    identities_preserved = True
    for life in range(LIVES):
        identities = (a.cam, a.q, a.t)
        if life:
            a.respawn()
            identities_preserved &= all(x is y for x, y in zip(identities, (a.cam, a.q, a.t)))
            if not persist:
                # Matched control: same CAM and physics, fresh Q/T only.
                a.q = QTable(remainder=True, explore_flat=True)
                a.t = World()
        phase = rng.randrange(10000)
        reward_sum = 0
        living_bonus_turns = 0
        while not a.episode_terminal and a.life_turns < INITIAL_H + max(0, nutrition):
            a.turn(life * 10000 + phase + a.life_turns)
            r = a.last_reward
            reward_sum += r
            living_bonus_turns += int(r == 1)
        lives.append(dict(turns=a.life_turns, terminal=a.episode_terminal,
                          h=a.H, consumed=a.env.consumed, phase=phase,
                          reward_sum=reward_sum, living_bonus_turns=living_bonus_turns))
    return dict(lives=lives, median=median(row["turns"] for row in lives),
                deaths=a.deaths, respawn_preserves_memory=identities_preserved,
                false_facts=a.metrics.false_facts, destroyed=a.cam.destroyed,
                cortex_calls=a.metrics.cortex_calls,
                cam_occupied=sum(s.occupied != 0 for s in a.cam.slot))


def experiment():
    rows = []
    for seed in SEEDS:
        rows.append(dict(seed=seed, persist=survival_arm(seed, True),
                         reset=survival_arm(seed, False)))
    # A world with no nutritional benefit must not acquire extra life.
    inert = dict(persist=survival_arm(SEEDS[0], True, nutrition=0),
                 reset=survival_arm(SEEDS[0], False, nutrition=0))
    return dict(initial_h=INITIAL_H, nutrition=NUTRITION, lives=LIVES,
                seeds=list(SEEDS), food=food_probe(), survival=rows, inert=inert)


def green(report):
    """Recompute lifespan claims from the individual lives, fail closed."""
    try:
        if (report["initial_h"], report["nutrition"], report["lives"], report["seeds"]) != (
                INITIAL_H, NUTRITION, LIVES, list(SEEDS)):
            return False
        food = report["food"]
        if set(food) != {"food", "poison", "inert"}:
            return False
        for name, row in food.items():
            if any(row[k] != 0 for k in ("false_facts", "destroyed", "cortex_calls")):
                return False
            if name == "food":
                if row["action"] != 0 or row["consumed"] != 1 or row["h_after"] <= row["h_before"]:
                    return False
            elif row["action"] == 0 or row["consumed"] != 0:
                return False
        if [r["seed"] for r in report["survival"]] != list(SEEDS):
            return False
        for pair, nutrition in ([(r, NUTRITION) for r in report["survival"]]
                                + [(report["inert"], 0)]):
            medians = []
            for name in ("persist", "reset"):
                arm = pair[name]
                lives = arm["lives"]
                if len(lives) != LIVES or arm["deaths"] != LIVES:
                    return False
                if arm["respawn_preserves_memory"] is not True:
                    return False
                if any(arm[k] != 0 for k in ("false_facts", "destroyed", "cortex_calls")):
                    return False
                if not 0 < arm["cam_occupied"] <= 4096:
                    return False
                for row in lives:
                    if (row["terminal"] is not True or type(row["h"]) is not int
                            or row["h"] != 0 or type(row["turns"]) is not int
                            or type(row["consumed"]) is not int or row["consumed"] not in (0, 1)
                            or row["turns"] != INITIAL_H + nutrition * row["consumed"]
                            or row["living_bonus_turns"] != 0):
                        return False
                m = median(row["turns"] for row in lives)
                if m != arm["median"]:
                    return False
                medians.append(m)
            if [r["phase"] for r in pair["persist"]["lives"]] != [r["phase"] for r in pair["reset"]["lives"]]:
                return False
            if nutrition and not medians[0] > medians[1]:
                return False
            if not nutrition and medians != [INITIAL_H, INITIAL_H]:
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def main():
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(green=report["green"], food=report["food"],
                         survival=[dict(seed=r["seed"], persist=r["persist"]["median"],
                                        reset=r["reset"]["median"]) for r in report["survival"]],
                         report=str(path)), indent=2))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
