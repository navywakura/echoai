"""ECHO-SEED · S2 dreams: invented tasks for training an intuition (recognition) network.

    python3 -m echoai.seed.dreams OUT.npz --n 200000 --level S1 --workers 10

A dream = a random program of 1-3 library steps (with colours from the grid) applied to a REAL input
grid from the gym's TRAIN pool (never the holdout, never an evaluation set). Because ECHO wrote the
program, it knows the answer: which primitive families the task needs. The network learns to look
at (input -> output) pairs and say which primitives to try first. It only ORDERS the search; a
program still counts only if ECHO verifies it on every example.

Each dream becomes 3 pairs built from 3 different input grids of the same task, like an ARC task.
Stored as uint8 one-hot-free grids (padded 30x30, value 255 = outside) + multi-hot labels.
"""
import argparse
import hashlib
import json
import random
from multiprocessing import Pool

import numpy as np

from echoai.seed import dsl, gym

PAD = 30


def primitive_names():
    return sorted(list(dsl.NO_ARG) + list(dsl.ONE_COLOR) + list(dsl.TWO_COLOR))


def pad(g):
    a = np.full((PAD, PAD), 255, dtype=np.uint8)
    a[: len(g), : len(g[0])] = np.array(g, dtype=np.uint8)
    return a


def _random_step(rng, g):
    kind = rng.randrange(10)
    cols = sorted(dsl.palette(g))
    if kind < 6:
        return (rng.choice(sorted(dsl.NO_ARG)),)
    if kind < 9:
        return (rng.choice(sorted(dsl.ONE_COLOR)), rng.choice(cols + list(range(10))))
    return (rng.choice(sorted(dsl.TWO_COLOR)), rng.choice(cols), rng.randrange(10))


_INPUTS = []


def _level(level):
    {"S1": dsl.enable_s1, "S1b": dsl.enable_s1b, "S2v": dsl.enable_s2v}.get(level, lambda: None)()


def _init(inputs, level):
    _INPUTS[:] = inputs
    _level(level)


def dream(args):
    seed, level = args
    inputs = _INPUTS
    if dsl.LEVEL != level:
        _level(level)
    rng = random.Random(seed)
    for _ in range(50):                                   # retry until the program works on 3 inputs
        grids = rng.sample(inputs, 3)
        steps = [_random_step(rng, grids[0]) for _ in range(rng.choice((1, 1, 2, 2, 3)))]
        outs = []
        try:
            for g in grids:
                o = g
                for st in steps:
                    o = dsl.apply_step(o, st)
                outs.append(o)
        except (ValueError, IndexError, ZeroDivisionError, TypeError):
            continue
        if any(o == g for o, g in zip(outs, grids)):
            continue                                      # the program must change every grid
        return [(pad(g), pad(o)) for g, o in zip(grids, outs)], sorted({st[0] for st in steps})
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=200000)
    ap.add_argument("--level", default="S1")
    ap.add_argument("--workers", type=int, default=10)
    args = ap.parse_args(argv)
    _level(args.level)
    names = primitive_names()
    # real input grids from the TRAIN pool only (the gym refuses evaluation sets; holdout excluded here)
    inputs = []
    for tid in gym.split()["train"]:
        for p in gym.load(tid)["train"]:
            try:
                inputs.append(dsl.G(p["input"]))
            except ValueError:
                pass
    with Pool(args.workers, initializer=_init, initargs=(inputs, args.level)) as pool:
        res = [r for r in pool.imap(dream, [(i, args.level) for i in range(args.n)], chunksize=200) if r]
    X = np.stack([np.stack([np.stack([a, b]) for a, b in pairs]) for pairs, _ in res])    # (N, 3, 2, 30, 30)
    Y = np.zeros((len(res), len(names)), dtype=np.uint8)
    for i, (_, labels) in enumerate(res):
        for l in labels:
            Y[i, names.index(l)] = 1
    np.savez_compressed(args.out, X=X, Y=Y, names=np.array(names))
    meta = {"dreams": len(res), "requested": args.n, "level": args.level, "primitives": len(names),
            "inputs_from_train_pool": len(inputs), "sha256_Y": hashlib.sha256(Y.tobytes()).hexdigest()}
    print(json.dumps(meta))


if __name__ == "__main__":
    raise SystemExit(main())
