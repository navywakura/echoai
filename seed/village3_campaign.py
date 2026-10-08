"""Versioned memory experiment; no writes to closed village2 artifacts."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import FunctionType

from seed import village2 as base, village3 as v
from seed.game_selfimprove import atomic, canonical, sha, journal
from seed.village2_campaign import checks, diary_valid

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "lab/seed/village3-20260928"
SEEDS = tuple(range(43000, 43016))
SOURCES = ("seed/village2.py", "seed/village2_campaign.py", "seed/village3.py",
           "seed/village3_campaign.py", "seed/game_selfimprove.py", "tests/test_village3.py",
           "docs/ECHO45-EGO-MEMORIA3-DEVELOPMENT.md", "docs/ECHO45-EGO-MEMORIA3-DESIGN.md")


def sources():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def save(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(gzip.compress(canonical(record).encode(), mtime=0))


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def summary(record):
    d, n = (record["cases"][k] for k in ("debt", "no_debt"))
    return {"checks": checks(record), "first": d["first"], "last": d["last"],
            "control_first": n["first"], "control_last": n["last"],
            "total_cost": sum(r["cost"] for r in d["rows"]), "record_sha256": sha(record)}


def observe(row, seed):
    if row["episode"] % 80 == 0:
        journal(ROOT / "development/journal.jsonl", dict(kind="village_decision", origin="DEVELOPMENT",
                seed=seed, agent=row["offer"]["agent"], **{k: row[k] for k in
                ("episode", "context", "q_values", "verified", "wrote", "cost", "claims", "entry_hash")}))


def development():
    initial = sources()
    root = ROOT / "development"
    root.mkdir(parents=True, exist_ok=True)
    profile = root / "sources.json"
    if profile.exists():
        assert json.loads(profile.read_text()) == initial, "use a new development revision"
    else:
        atomic(profile, initial)
    summaries = {}
    for seed in range(1, 25):
        def visible_run(*args, **kwargs):
            return v.run(*args, **kwargs, observer=lambda row: observe(row, seed))
        experiment = FunctionType(v.experiment.__code__, dict(v.experiment.__globals__, run=visible_run))
        pair = {}
        for name, fn in (("revised", experiment), ("baseline", base.experiment)):
            path = root / f"{name}-{seed}.json.gz"
            record = read(path) if path.exists() else fn(seed)
            if not path.exists():
                save(path, record)
            pair[name] = summary(record)
        summaries[str(seed)] = pair
        print(canonical({"seed": seed, "checks": pair["revised"]["checks"],
                         "cost_delta": pair["revised"]["total_cost"] - pair["baseline"]["total_cost"]}), flush=True)
    assert sources() == initial
    passed = all(all(x["revised"]["checks"].values()) for x in summaries.values())
    cost_delta = sum(x["revised"]["total_cost"] - x["baseline"]["total_cost"] for x in summaries.values())
    atomic(root / "summary.json", {"sources": initial, "seeds": summaries, "passed": passed,
                                   "aggregate_cost_delta": cost_delta, "promote": passed and cost_delta <= 0})


def integrity():
    p = json.loads((ROOT / "profile.json").read_text())
    assert p["sources"] == sources() and p["seeds"] == list(SEEDS)
    return p


def examine():
    dev = json.loads((ROOT / "development/summary.json").read_text())
    assert dev["promote"] and dev["sources"] == sources(), "development not promoted"
    assert not (ROOT / "opened.json").exists(), "sealed exam already opened"
    atomic(ROOT / "profile.json", {"sources": sources(), "seeds": SEEDS, "horizon": v.HORIZON,
                                   "development_sha256": sha(dev)})
    for name in SOURCES:
        target = ROOT / "source-archive" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((REPO / name).read_bytes())
    atomic(ROOT / "opened.json", {"at": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()})
    for seed in SEEDS:
        save(ROOT / f"exam-{seed}.json.gz", v.experiment(seed))
        integrity()
        print(canonical({"recorded": seed, "of": 16}), flush=True)
    subprocess.run([sys.executable, "-m", "seed.village3_campaign", "audit"], cwd=REPO, check=True)


def audit():
    integrity()
    opened = json.loads((ROOT / "opened.json").read_text())
    assert opened["pid"] != os.getpid(), "audit needs a separate process"
    reports = {}
    for seed in SEEDS:
        stored = read(ROOT / f"exam-{seed}.json.gz")
        assert sha(stored) == sha(v.experiment(seed)), "replay mismatch"
        for case in stored["cases"].values():
            diary_valid(case)
            assert case["first"] == base.metrics(case["rows"][:base.FIRST])
            assert case["last"] == base.metrics(case["rows"][-base.LAST:])
        for case in (*stored["ablations"].values(), *stored["stability"].values()):
            diary_valid(case["probe"])
        reports[str(seed)] = summary(stored)
        print(canonical({"replayed": seed, "checks": reports[str(seed)]["checks"]}), flush=True)
    integrity()
    result = {"green": all(all(x["checks"].values()) for x in reports.values()), "M6": True,
              "seeds": reports, "sources": sources(), "audit_pid": os.getpid(),
              "closed": datetime.now(timezone.utc).isoformat(), "cost_usd": 0}
    atomic(ROOT / "audit.json", result)
    print(canonical({"green": result["green"], "M6": True}), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("dev", "exam", "audit"))
    {"dev": development, "exam": examine, "audit": audit}[ap.parse_args().command]()
