"""Development on already-open bodies; never grants prospective DREAM green."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from echoai.echo4.continuity import canonical
from echoai.echo4.dream_bench import evaluate as legacy_evaluate, persist, summary
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import Policy as LegacyPolicy
from echoai.echo4.dream_v3 import (
    DEVELOPMENT, ReplayEvaluator, binding, cases, evaluate, histories, starters,
)
from echoai.echo4.dream_v3_profile import Policy


def build(directory, *, checking=False):
    parent = binding()
    groups, costs = [], []
    for i, bodies in enumerate(DEVELOPMENT):
        print(f"development group {i}: collect actual conditional branches", flush=True)
        group, cost = histories(directory, f"history-{i}.json", cases(bodies), checking=checking)
        groups.append(group)
        costs.append(cost)
    evaluator = ReplayEvaluator(groups)
    chosen, scores = evaluator.select(Policy(), starters())
    results = []
    for i, rows in enumerate(groups):
        print(f"development group {i}: compare controls", flush=True)
        arms = {"selected": evaluate(chosen, rows), "fixed": evaluate(Policy(), rows),
                "random": evaluate(Policy(), rows, random_seed=260923 + i * 10000),
                "adaptive": evaluate(Policy(), rows, active=True),
                "legacy_v2": legacy_evaluate(LegacyPolicy((4, 5, 0, 1, 2, 3)), rows)}
        parity = (arms["selected"] == evaluate(chosen, rows, replay=True)
                  and arms["fixed"] == evaluate(Policy(), rows, replay=True)
                  and arms["random"] == evaluate(Policy(), rows, replay=True, random_seed=260923 + i * 10000)
                  and arms["adaptive"] == evaluate(Policy(), rows, replay=True, active=True))
        digest = persist(directory, f"online-{i}.json", arms, checking)
        results.append({"metrics": {k: summary(v) for k, v in arms.items()},
                        "parity": parity, "online_sha256": digest})
        print(json.dumps(results[-1]), flush=True)
    report = {"scope": "development only, prior examinations already opened",
              "parent": parent, "bodies": DEVELOPMENT, "collection": costs,
              "selected": chosen.data(), "scores": scores, "results": results,
              "replay_cost": evaluator.cost(), "dream1_green": False}
    report["reproduction_sha256"] = sha(canonical(report))
    persist(directory, "report.json", report, checking)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run", "verify"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        args.directory.mkdir(parents=True, exist_ok=False)
    report = build(args.directory, checking=args.command == "verify")
    print(json.dumps({"reproduction_sha256": report["reproduction_sha256"], "dream1_green": False}))


if __name__ == "__main__":
    main()
