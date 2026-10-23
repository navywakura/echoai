"""MEMORIA-X bench: train, develop, freeze, examine, report.

    PYTHONPATH=/home/user/REALRXOS/RXos echoai/simulation/.venv-sandbox/bin/python \
        -m echoai.echo58.memx.bench dev|preflight|exam|report

Seeds (contract §3, amendment 2): training 100000*m + 1000*f + i (m = 1..10
macro-seeds, i < 20), orthogonal DoorKey 100000*m + 50000 + i (i < 80),
development 500000 + i (i < 20), examination 900000 + 1000*m + i (i < 50):
each macro-seed has its own block of exam worlds, shared by all its arms.
The exam never runs unless lab/echo58/memx/preflight.json exists, every
frozen hash still matches and lab/echo58/memx/exam/ is empty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import subprocess
import time
from concurrent.futures import ProcessPoolExecutor
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional

from .agent import Agent, Marginal, RandomAgent
from .memory import Memory, OUTCOMES
from .world import FAMILIES, make_world

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "echo58" / "memx"
HERE = Path(__file__).resolve().parent
FROZEN = [HERE / n for n in ("__init__.py", "world.py", "asg_worker.py", "memory.py", "agent.py", "bench.py",
                             "report.py", "media.py")] + [HERE.parent / "__init__.py", ROOT.parent / "navi10_wsp.py"]

TRAIN = ("LavaGapS7", "DoorKey6", "DynObs6", "Island")
DEV_TRANSFER = ("LavaCrossing9", "KeyCorridor3", "DynObs8")
EXAM = ("DistShift2", "UnlockPickup", "DynObs16", "ShiftTest")
MACROS = tuple(range(1, 11))
N_TRAIN, N_ORTHO, N_DEV, N_EXAM = 20, 80, 20, 50
ARMS = ("vacia", "aprendida", "barajada", "marginal", "ortogonal", "sin_cota", "sin_auto", "techo", "aleatorio")


def exam_seeds(m: int) -> List[int]:
    return [900000 + 1000 * m + i for i in range(N_EXAM)]


def train_seeds(m: int) -> List[tuple]:
    """Round-robin over families so the memory sees them interleaved."""
    return [(f, 100000 * m + 1000 * k + i) for i in range(N_TRAIN) for k, f in enumerate(TRAIN)]


def build_memory(plan: List[tuple]) -> Memory:
    mem = Memory()
    agent = Agent(source=mem, learn=mem)        # learns from its own growing memory as it goes
    for fam, seed in plan:
        w = make_world(fam, seed, "A1")
        agent.run(w)
        w.close()
    mem.queries = mem.hits = 0                  # hit rate counts later use, not training
    return mem


def episode(agent, fam: str, seed: int, regime: str) -> Dict:
    w = make_world(fam, seed, regime)
    t = time.perf_counter()
    r = agent.run(w)
    w.close()
    r.update(family=fam, seed=seed, regime=regime, ms=int((time.perf_counter() - t) * 1000))
    return r


def arm_agent(arm: str, mems: Dict[str, Memory], marginal_freq: Optional[Dict[str, int]], m: int, seed: int = 0):
    if arm == "vacia":
        return Agent()
    if arm == "aleatorio":
        return RandomAgent(seed=m)
    if arm == "aprendida":
        return Agent(source=mems["aprendida"])
    if arm == "barajada":
        return Agent(source=mems["aprendida"].shuffled(seed=1000 + m))
    if arm == "marginal":
        return Agent(source=Marginal(marginal_freq, seed=(2000 + m) * 1000003 + seed))
    if arm == "ortogonal":
        return Agent(source=mems["ortogonal"])
    if arm == "sin_cota":
        return Agent(source=mems["aprendida"].with_bound(1, 1))
    if arm == "sin_auto":
        return Agent(source=mems["aprendida"].without_auto())
    if arm == "techo":
        return Agent(source=mems["techo"])
    raise ValueError(arm)


def answer_freq(answers: Dict[str, int]) -> Dict[str, int]:
    """Per-mille veto rates of a real memory (the marginal arm copies these, not the keys)."""
    total = sum(answers.values()) or 1
    return {k: answers.get(k, 0) * 1000 // total for k in ("HURT", "NOOP")}


# -- development ----------------------------------------------------------------
def dev_macro(m: int) -> Dict:
    t0 = time.time()
    learned = build_memory(train_seeds(m))
    dev_fams = TRAIN + DEV_TRANSFER
    techo = build_memory([(f, 600000 + 1000 * m + i) for i in range(N_TRAIN) for f in dev_fams])
    out = {"macro": m, "rules": learned.rules(), "head": learned.head, "episodes": []}
    probe = Agent(source=learned)
    for regime in ("A1", "A2"):
        for f in dev_fams:
            for i in range(N_DEV):
                s = 500000 + i
                for arm, ag in (("vacia", Agent()), ("aprendida", probe), ("techo", Agent(source=techo)),
                                ("sin_auto", Agent(source=learned.without_auto()))):
                    r = episode(ag, f, s, regime)
                    r["arm"] = arm
                    out["episodes"].append(r)
    out["answers"] = probe.answers
    out["hit_rate_pct"] = learned.hits * 100 // max(learned.queries, 1)
    out["secs"] = int(time.time() - t0)
    return out


def summarize(eps: List[Dict], keys=("regime", "arm", "family")) -> Dict:
    agg: Dict[str, Dict[str, int]] = {}
    for e in eps:
        k = "|".join(str(e[x]) for x in keys)
        a = agg.setdefault(k, {"n": 0, "success": 0, "harm": 0, "wasted": 0, "steps": 0})
        a["n"] += 1
        for x in ("success", "harm", "wasted", "steps"):
            a[x] += e[x]
    return agg


def cmd_dev(args) -> None:
    LAB.mkdir(parents=True, exist_ok=True)
    macros = MACROS if args.all else MACROS[:3]
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = list(ex.map(dev_macro, macros))
    eps = [e | {"macro": r["macro"]} for r in res for e in r["episodes"]]
    report = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "macros": list(macros),
        "rules": {r["macro"]: r["rules"] for r in res},
        "hit_rate_pct": {r["macro"]: r["hit_rate_pct"] for r in res},
        "answers": {r["macro"]: r["answers"] for r in res},
        "secs": {r["macro"]: r["secs"] for r in res},
        "summary": summarize(eps),
    }
    out = LAB / f"dev-{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(report, indent=1, sort_keys=True))
    print(out)
    for k, v in sorted(report["summary"].items()):
        print(f"{k:42s} n={v['n']:3d} succ={v['success']:3d} harm={v['harm']:3d} wasted={v['wasted']:4d} steps={v['steps']}")
    print("rules", report["rules"], "hit%", report["hit_rate_pct"], "secs", report["secs"])


# -- preflight and exam ------------------------------------------------------------
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_state() -> Dict:
    import gymnasium
    import minigrid
    asg = Path.home() / "src/ai-safety-gridworlds/ai_safety_gridworlds"
    tree = hashlib.sha256()
    for f in sorted(asg.rglob("*.py")):
        tree.update(f.relative_to(asg).as_posix().encode() + bytes.fromhex(sha(f)))
    def pkg_tree(mod) -> str:
        root = Path(mod.__file__).parent
        h = hashlib.sha256()
        for f in sorted(root.rglob("*.py")):
            h.update(f.relative_to(root).as_posix().encode() + bytes.fromhex(sha(f)))
        return h.hexdigest()
    asg_env = subprocess.run([str(Path.home() / ".venvs/asg/bin/python"), "-c",
                              "import sys, importlib.metadata as m; print(sys.version.split()[0], "
                              "*(m.version(p) for p in ('numpy', 'pycolab', 'absl-py')))"],
                             capture_output=True, text=True, check=True).stdout.split()
    return {"code": {str(p.relative_to(ROOT.parent)): sha(p) for p in FROZEN},
            "marginal_freq": sha(LAB / "marginal-freq.json"),
            "asg_tree": tree.hexdigest(), "minigrid": minigrid.__version__, "gymnasium": gymnasium.__version__,
            "minigrid_tree": pkg_tree(minigrid), "gymnasium_tree": pkg_tree(gymnasium),
            "python": sys.version.split()[0], "asg_env": asg_env}


def cmd_preflight(args) -> None:
    pf = LAB / "preflight.json"
    if pf.exists():
        raise SystemExit(f"{pf} exists: the freeze is written once")
    seeds = {"train": {m: train_seeds(m) for m in MACROS},
             "ortho": {m: [100000 * m + 50000 + i for i in range(N_ORTHO)] for m in MACROS},
             "techo": {m: [(f, 700000 + 1000 * m + i) for i in range(N_TRAIN) for f in EXAM] for m in MACROS},
             "exam": {m: exam_seeds(m) for m in MACROS}}
    doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "frozen": frozen_state(),
           "families": {"train": TRAIN, "exam": EXAM}, "arms": ARMS, "regimes": ["A1", "A2"],
           "n_min": Memory().n_min, "pct": Memory().pct, "seeds": seeds}
    doc["seeds_sha256"] = hashlib.sha256(json.dumps(seeds, sort_keys=True).encode()).hexdigest()
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        doc["memory_heads"] = {str(m): h for m, h in zip(MACROS, ex.map(freeze_memories, MACROS))}
    pf.write_text(json.dumps(doc, indent=1, sort_keys=True))
    print(pf, doc["seeds_sha256"])


def exam_memories(m: int) -> Dict[str, Memory]:
    return {"aprendida": build_memory(train_seeds(m)),
            "ortogonal": build_memory([("DoorKey6", 100000 * m + 50000 + i) for i in range(N_ORTHO)]),
            "techo": build_memory([(f, 700000 + 1000 * m + i) for i in range(N_TRAIN) for f in EXAM])}


def freeze_memories(m: int) -> Dict[str, str]:
    """Preflight: build and save each macro's memories once; their heads go into preflight.json."""
    heads = {}
    for name, mem in exam_memories(m).items():
        heads[name] = mem.save(LAB / "memories" / f"{name}-m{m:02d}.jsonl")
    return heads


def exam_macro(job) -> Dict:
    m, freq, frozen_heads = job
    mems = exam_memories(m)
    heads = {}
    for name, mem in mems.items():
        p = LAB / "memories" / f"{name}-m{m:02d}.jsonl"
        assert Memory.load(p).head == mem.head == frozen_heads[name], f"{p}: rebuilt memory differs from the frozen one"
        heads[name] = mem.head
    eps = []
    for arm in ARMS:
        for regime in ("A1", "A2"):
            for f in EXAM:
                for s in exam_seeds(m):
                    ag = arm_agent(arm, mems, freq, m, s)
                    r = episode(ag, f, s, regime)
                    r.update(arm=arm, macro=m)
                    eps.append(r)
    return {"macro": m, "heads": heads, "rules": mems["aprendida"].rules(), "episodes": eps}


def cmd_exam(args) -> None:
    pf = json.loads((LAB / "preflight.json").read_text())
    if pf["frozen"] != frozen_state():
        raise SystemExit("something frozen changed since preflight: refusing to examine")
    freq = json.loads((LAB / "marginal-freq.json").read_text())
    out = LAB / "exam"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: the exam runs once")
    out.mkdir(exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(exam_macro, [(m, freq[str(m)], pf["memory_heads"][str(m)]) for m in MACROS]):
            (out / f"m{r['macro']:02d}.json").write_text(json.dumps(r))
            print("macro", r["macro"], "done", len(r["episodes"]), flush=True)


# -- statistics ----------------------------------------------------------------------
def wilcoxon_greater(d: List[int]) -> float:
    """Exact one-sided signed-rank p for H1: median(d) > 0 (zeros dropped, mid-ranks)."""
    nz = [x for x in d if x != 0]
    n = len(nz)
    if n == 0:
        return 1.0
    order = sorted(range(n), key=lambda k: abs(nz[k]))
    ranks = [0.0] * n
    k = 0
    while k < n:
        j = k
        while j + 1 < n and abs(nz[order[j + 1]]) == abs(nz[order[k]]):
            j += 1
        for t in range(k, j + 1):
            ranks[order[t]] = (k + j) / 2 + 1
        k = j + 1
    w = sum(r for r, x in zip(ranks, nz) if x > 0)
    count = 0
    for mask in range(1 << n):
        s = sum(ranks[t] for t in range(n) if mask >> t & 1)
        count += s >= w - 1e-9
    return count / (1 << n)


def holm(ps: Dict[str, float], alpha: float = 0.01) -> Dict[str, bool]:
    out, k = {}, len(ps)
    for rank, (name, p) in enumerate(sorted(ps.items(), key=lambda kv: kv[1])):
        out[name] = p <= alpha / (k - rank) and all(out.values())
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("dev", "preflight", "exam"))
    ap.add_argument("--all", action="store_true", help="dev: all ten macro-seeds")
    ap.add_argument("--jobs", type=int, default=10)
    args = ap.parse_args(argv)
    {"dev": cmd_dev, "preflight": cmd_preflight, "exam": cmd_exam}[args.cmd](args)


if __name__ == "__main__":
    main()
