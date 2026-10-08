"""ECHO-SEED · the gym: training tasks only. Evaluation sets are sealed and cannot be read here.

Pools (public, Apache-2.0): ARC-AGI-1 training (400) and ARC-AGI-2 training (1000), deduplicated by
task id. A fixed 20 % of them (by seed) is HOLDOUT: never used to learn, only to measure whether
what was learned transfers to tasks the sandbox has not seen.
SEALED: ARC-AGI-1 evaluation, ARC-AGI-2 evaluation and ARC-AGI-3 exam games. Only the exam
command of a later, approved contract may open them.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOLS = {"arc1": ROOT / "lab/seed/ARC-AGI/data/training", "arc2": ROOT / "lab/arc2/ARC-AGI-2/data/training"}
SEALED = (ROOT / "lab/seed/ARC-AGI/data/evaluation", ROOT / "lab/arc2/ARC-AGI-2/data/evaluation")
SEED = "echo-seed-20260925"


def _guard(path):
    p = Path(path).resolve()
    for s in SEALED:
        if s.resolve() in p.parents or p == s.resolve():
            raise PermissionError("sealed evaluation set: %s" % p)
    return p


def catalogue():
    """{task_id: path}, ARC-AGI-1 first so a duplicated id keeps its ARC-AGI-1 copy."""
    out = {}
    for pool in ("arc1", "arc2"):
        for f in sorted(POOLS[pool].glob("*.json")):
            out.setdefault(f.stem, _guard(f))
    return out


def split():
    cat = catalogue()
    ids = sorted(cat, key=lambda t: hashlib.sha256((t + SEED).encode()).hexdigest())
    n_hold = len(ids) // 5
    return {"train": sorted(ids[n_hold:]), "holdout": sorted(ids[:n_hold])}


def load(task_id):
    return json.loads(_guard(catalogue()[task_id]).read_text())
