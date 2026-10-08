"""SHIFT-S: an acquired food becomes poisonous, without resetting memory.

Only environment chemistry changes. Compare continued learning against
the same trained Q frozen at the boundary, and a fresh agent. All exams
start at the canonical START; no action or route is supplied by the bank.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pickle
import random
from contextlib import nullcontext
from pathlib import Path
from statistics import median
from unittest.mock import patch

from echoai.nexus0.echo2 import INITIAL_H, LIVES, NUTRITION, SEEDS, new_agent


def fingerprint(value):
    """Local before/after audit, not a portable serialization format."""
    return hashlib.sha256(pickle.dumps(value, protocol=4)).hexdigest()


def memories(agent):
    return {name: fingerprint(getattr(agent, name)) for name in ("cam", "q", "t")}


def run_lives(agent, seed, offset, *, freeze_q=False):
    rng = random.Random(seed)
    rows = []
    q_before = fingerprint((agent.q.q, agent.q.rem))
    surprise_before = agent.metrics.surprise_known
    with (patch.object(agent.q, "update", return_value=0) if freeze_q else nullcontext()):
        for life in range(LIVES):
            if agent.episode_terminal:
                agent.respawn()
            phase = rng.randrange(10000)
            entry = agent.env.i
            while not agent.episode_terminal and agent.life_turns < INITIAL_H + NUTRITION:
                agent.turn(offset + life * 10000 + phase + agent.life_turns)
            rows.append(dict(turns=agent.life_turns, consumed=agent.env.consumed,
                             h=agent.H, terminal=agent.episode_terminal,
                             phase=phase, entry=entry))
    return dict(lives=rows, total_turns=sum(r["turns"] for r in rows),
                consumed=sum(r["consumed"] for r in rows),
                median_last_10=median(r["turns"] for r in rows[-10:]),
                q_before=q_before, q_after=fingerprint((agent.q.q, agent.q.rem)),
                surprise_known=agent.metrics.surprise_known - surprise_before,
                false_facts=agent.metrics.false_facts, destroyed=agent.cam.destroyed,
                cortex_calls=agent.metrics.cortex_calls,
                cam_occupied=sum(s.occupied != 0 for s in agent.cam.slot))


def experiment():
    rows = []
    for seed in SEEDS:
        agent = new_agent()
        home = run_lives(agent, seed, 0)
        agent.respawn()
        identity = (agent.cam, agent.q, agent.t)
        before = memories(agent)
        observation = agent.observation(agent.env.cell()).hex()
        # The only intervention in the transferred agent: physical effect
        # of the existing object. No repaint, hint, memory write or reset.
        agent.env.world.nutrition = -NUTRITION
        after = memories(agent)
        frozen = copy.deepcopy(agent)
        frozen_initial = memories(frozen)
        scratch = new_agent(-NUTRITION)
        boundary = dict(before=before, after=after,
                        identity_preserved=all(x is y for x, y in zip(identity, (agent.cam, agent.q, agent.t))),
                        observation_before=observation,
                        observation_after=agent.observation(agent.env.cell()).hex(),
                        frozen_initial=frozen_initial)
        shifted = run_lives(agent, seed + 1, 1000000)
        fixed = run_lives(frozen, seed + 1, 1000000, freeze_q=True)
        naive = run_lives(scratch, seed + 1, 1000000)
        rows.append(dict(seed=seed, boundary=boundary, home=home,
                         adapt=shifted, frozen=fixed, scratch=naive,
                         gain_vs_frozen=shifted["total_turns"] - fixed["total_turns"],
                         gain_vs_scratch=shifted["total_turns"] - naive["total_turns"]))
    return dict(slice="SHIFT-S", seeds=list(SEEDS), lives=LIVES,
                initial_h=INITIAL_H, nutrition_before=NUTRITION,
                nutrition_after=-NUTRITION, rows=rows)


def valid_arm(arm, *, home=False):
    from echoai.nexus0.body3d import START
    rows = arm["lives"]
    if len(rows) != LIVES:
        return False
    for row in rows:
        if any(type(row[k]) is not int for k in ("h", "turns", "consumed", "phase", "entry")):
            return False
        if (row["terminal"] is not True or row["h"] != 0
                or row["consumed"] not in (0, 1) or row["entry"] != START
                or not 0 <= row["phase"] < 10000):
            return False
        if home:
            if row["turns"] != INITIAL_H + NUTRITION * row["consumed"]:
                return False
        elif not 1 <= row["turns"] <= INITIAL_H:
            return False
        elif row["consumed"] == 0 and row["turns"] != INITIAL_H:
            return False
    return (arm["total_turns"] == sum(r["turns"] for r in rows)
            and arm["consumed"] == sum(r["consumed"] for r in rows)
            and arm["median_last_10"] == median(r["turns"] for r in rows[-10:])
            and all(type(arm[k]) is int and arm[k] == 0
                    for k in ("false_facts", "destroyed", "cortex_calls"))
            and type(arm["cam_occupied"]) is int and 0 < arm["cam_occupied"] <= 4096)


def green(report):
    try:
        if (report["slice"], report["seeds"], report["lives"], report["initial_h"],
            report["nutrition_before"], report["nutrition_after"]) != (
                "SHIFT-S", list(SEEDS), LIVES, INITIAL_H, NUTRITION, -NUTRITION):
            return False
        if [row["seed"] for row in report["rows"]] != list(SEEDS):
            return False
        for row in report["rows"]:
            b = row["boundary"]
            if (b["identity_preserved"] is not True or b["before"] != b["after"]
                    or b["frozen_initial"] != b["after"]
                    or set(b["before"]) != {"cam", "q", "t"}
                    or b["observation_before"] != b["observation_after"]):
                return False
            for name in ("home", "adapt", "frozen", "scratch"):
                if not valid_arm(row[name], home=name == "home"):
                    return False
            a, f, s = (row[k] for k in ("adapt", "frozen", "scratch"))
            phases = [[r["phase"] for r in row[k]["lives"]] for k in ("adapt", "frozen", "scratch")]
            rng = random.Random(row["seed"] + 1)
            expected_phases = [rng.randrange(10000) for _ in range(LIVES)]
            if any(p != expected_phases for p in phases):
                return False
            if (a["q_before"] != f["q_before"] or f["q_before"] != f["q_after"]
                    or a["q_before"] == a["q_after"]):
                return False
            gain = a["total_turns"] - f["total_turns"]
            if (gain <= 0 or row["gain_vs_frozen"] != gain
                    or row["gain_vs_scratch"] != a["total_turns"] - s["total_turns"]
                    or a["consumed"] >= f["consumed"]
                    or a["median_last_10"] <= f["median_last_10"]
                    or row["home"]["consumed"] == 0):
                return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def main():
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_shifts_report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(green=report["green"], rows=[dict(
        seed=r["seed"], gain_vs_frozen=r["gain_vs_frozen"],
        gain_vs_scratch=r["gain_vs_scratch"],
        poison_consumptions={k: r[k]["consumed"] for k in ("adapt", "frozen", "scratch")}
    ) for r in report["rows"]], report=str(path)), indent=2))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
