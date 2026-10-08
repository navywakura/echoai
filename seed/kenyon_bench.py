"""Small synthetic development check of 640 versus 500k sparse guide units.

This measures primitive ranking only, not an ARC score or S6 result.
"""
import json
import random

from echoai.seed import dsl
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide


NAMES = ("fliplr", "flipud", "rot90", "rot180")


def sample(seed):
    rng = random.Random(seed)
    name = NAMES[seed % len(NAMES)]
    train = []
    for _ in range(3):
        grid = [[rng.randrange(5) for _ in range(6)] for _ in range(4)]
        train.append({"input": grid, "output": [list(row) for row in getattr(dsl, name)(dsl.G(grid))]})
    return {"train": train, "test": [{"input": [[rng.randrange(5) for _ in range(6)] for _ in range(4)]}]}, name


def run():
    results = {}
    for capacity in (640, 500_000):
        guide = SparsePrimitiveGuide(capacity)
        for seed in range(80):
            task, name = sample(seed)
            guide.observe(task, [(name,)])
        hits = 0
        for seed in range(1000, 1040):
            task, name = sample(seed)
            scores = guide.probs(task)
            hits += name == max(NAMES, key=lambda candidate: scores[candidate])
        results[str(capacity)] = {"top1": hits, "of": 40, "examples": guide.examples,
                                   "allocated_bytes": len(guide.weights),
                                   "nonzero_units": sum(v != 0 for v in guide.weights)}
    return {"origin": "SYNTHETIC_DEVELOPMENT", "metric": "primitive_family_top1",
            "not_arc_score": True, "s6_unchanged": True, "results": results}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
