"""Capacity sweep, audited historical controls and a queue behind S6-PROBE1.

No frozen source is edited. The original solver/verifier/recorder are reused.
All additional ARC measurements are known development, never sealed exams.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))
from echoai.seed import gym, sandbox
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from echoai.seed.kenyon_bench import sample, NAMES
from echoai.seed.learn import Library
from seed import kenyon_arc1 as original

HISTORY = REPO / "lab/seed/capacity500k-arc1-20260930"
ROOT = REPO / "lab/seed/capacity-study-20261001"
S6 = REPO / "lab/seed/s6probe1-20260930"
CAPACITIES = (640, 4096, 16384, 65536, 500000)
NEW_ARMS = ("guide4096", "guide16384", "guide65536")
ARMS = ("base",) + tuple("guide" + str(n) for n in CAPACITIES)
HISTORICAL = {"base": "base", "guide640": "guide640", "guide500000": "guide500k"}
CONFIG = {"capacities": list(CAPACITIES), "expansions": 400, "depth": 4,
          "workers": 2, "attempts": 1, "model_calls": 0,
          "origin": "ARC1_TRAINING_DEVELOPMENT", "full_replay": True}
OWN_SOURCES = ("seed/capacity_study.py", "tests/test_capacity_study.py",
               "docs/ECHO45-CAPACITY-STUDY-DESIGN.md")
_STUDY = None


def require(value, message):
    if not value:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


read, save, digest, file_hash = original.read, original.save, original.digest, original.file_hash


def status(stage, **fields):
    data = {"stage": stage, "at": now(), "condition": "CAPACITY-STUDY", **fields}
    save(ROOT / "status.json", data)
    print(json.dumps(data, ensure_ascii=False), flush=True)


def check_pair(primary, replay):
    require(original.stable(primary) == original.stable(replay), "replay differs")
    require(primary["result"]["expansions"] <= CONFIG["expansions"], "budget exceeded")
    require(primary["result"]["test_ok"] is None, "solver saw test labels")
    require(primary["demonstration_replay"] is True, "program verification failed")


def paired(before, after):
    require(set(before) == set(after), "different task cohorts")
    a = {k for k, v in before.items() if v}
    b = {k for k, v in after.items() if v}
    return {"gained": sorted(b-a), "lost": sorted(a-b), "delta": len(b)-len(a)}


def checked_task(task_id, profile):
    require(task_id in profile["fit"] or task_id in profile["development"], "task outside declared development")
    path = gym.POOLS["arc1"] / (task_id + ".json")
    require(file_hash(path) == profile["tasks"][task_id], "task changed")
    return original.solver_input(read(path))


def fit(profile):
    sandbox._set_level("S2v")
    lib = Library(profile["state"]["concepts"], profile["state"]["prior"])
    guides = {"guide"+str(n): SparsePrimitiveGuide(n) for n in CAPACITIES}
    times = {arm: 0.0 for arm in guides}
    for tid in profile["fit"]:
        task = checked_task(tid, profile)
        for arm, guide in guides.items():
            start = time.process_time()
            guide.observe(task, profile["programs"][tid], lib)
            times[arm] += time.process_time()-start
    return guides, times


def synthetic():
    rows = {}
    for n in CAPACITIES:
        guide = SparsePrimitiveGuide(n)
        for seed in range(80):
            task, name = sample(seed)
            guide.observe(task, [(name,)])
        results = []
        for seed in range(1000, 1040):
            task, name = sample(seed)
            scores = guide.probs(task)
            results.append({"seed": seed, "expected": name,
                            "predicted": max(NAMES, key=lambda k: scores[k])})
        rows[str(n)] = {"correct": sum(x["expected"] == x["predicted"] for x in results),
                        "of": 40, "rows": results}
    return {"origin": "SYNTHETIC_DEVELOPMENT", "metric": "primitive_family_top1",
            "official_arc_score": False, "results": rows}


def import_controls(profile):
    manifest = {}
    rows = {}
    expected = digest(profile)
    for arm, old_arm in HISTORICAL.items():
        rows[arm] = []
        for tid in profile["development"]:
            paths = [HISTORY / phase / "results" / old_arm / (tid + ".json")
                     for phase in ("primary", "audit")]
            a, b = map(read, paths)
            require(a["profile_sha256"] == expected, "wrong historical profile")
            require(a["task"] == tid and a["arm"] == old_arm, "wrong historical identity")
            check_pair(a, b)
            rows[arm].append(a)
            for path in paths:
                manifest[str(path.relative_to(REPO))] = file_hash(path)
    return rows, manifest


def prepare():
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / "profile.json").exists():
        return integrity()
    # This original check verifies hashes, provenance and interpreter, without playing.
    p = original.integrity()
    require(not set(p["fit"]) & set(p["development"]), "train/development overlap")
    require(len(p["fit"]) == 60 and len(p["development"]) == 250, "unexpected cohort")
    _, historical = import_controls(p)
    files = tuple(p["sources"]) + OWN_SOURCES
    profile = {"at": now(), "config": CONFIG, "source_profile": p,
               "source_profile_sha256": file_hash(HISTORY / "profile.json"),
               "sources": {f: file_hash(REPO / f) for f in files},
               "historical_receipts": historical, "python": sys.version,
               "s6_profile_sha256": file_hash(S6 / "profile.json")}
    guides, times = fit(p)
    info = original.guide_info(guides)
    for arm in info:
        info[arm]["training_cpu_seconds"] = times[arm]
    save(ROOT / "training.json", {"guides": info, "model_calls": 0, "fit": len(p["fit"])})
    save(ROOT / "synthetic.json", synthetic())
    for name in files:
        target = ROOT / "source-archive" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / name).read_bytes())
    save(ROOT / "profile.json", profile)
    status("PREPARED", games_started=False, imported_results=750, imported_replays=750)
    report(profile)
    return profile


def integrity():
    p = read(ROOT / "profile.json")
    require(p["config"] == CONFIG and p["python"] == sys.version, "configuration changed")
    for name, expected in p["sources"].items():
        require(file_hash(REPO / name) == expected, "source changed: " + name)
    require(file_hash(HISTORY / "profile.json") == p["source_profile_sha256"], "historical profile changed")
    require(file_hash(S6 / "profile.json") == p["s6_profile_sha256"], "S6 profile changed")
    for name, expected in p["historical_receipts"].items():
        require(file_hash(REPO / name) == expected, "historical receipt changed: " + name)
    original.integrity()
    return p


def probe_finished(status_value, result):
    return (status_value.get("stage") == "DONE" and bool(result)
            and result.get("singles") == 200 and result.get("replay_failures") == []
            and result.get("exam_opened") is False and result.get("B_measured") is False)


def init_worker(profile):
    global _STUDY
    _STUDY = profile
    original.ROOT = ROOT
    original._PROFILE = profile["source_profile"]
    original._GUIDES = fit(original._PROFILE)[0]


def measure(job):
    tid, arm, phase = job
    require(arm in NEW_ARMS, "only new capacity arms may execute")
    require(tid in _STUDY["source_profile"]["development"], "not a development task")
    checked_task(tid, _STUDY["source_profile"])
    journal = ROOT / phase / "decisions" / arm / tid
    if journal.exists():
        target = ROOT / "interrupted" / (str(time.time_ns()) + "-" + arm + "-" + tid)
        target.parent.mkdir(parents=True, exist_ok=True)
        journal.rename(target)
    row = original.one(job)
    row["study_profile_sha256"] = digest(_STUDY)
    return row


def report(profile=None):
    profile = profile or read(ROOT / "profile.json")
    historical, _ = import_controls(profile["source_profile"])
    rows = dict(historical)
    complete, progress = set(HISTORICAL), {}
    for arm in NEW_ARMS:
        rows[arm] = []
        primary_count = replay_count = 0
        for tid in profile["source_profile"]["development"]:
            a = ROOT / "primary/results" / arm / (tid+".json")
            b = ROOT / "audit/results" / arm / (tid+".json")
            primary_count += a.exists()
            if a.exists() and b.exists():
                first, second = read(a), read(b)
                require(first.get("study_profile_sha256") == digest(profile), "wrong study profile")
                require(first["task"] == tid and first["arm"] == arm, "wrong result identity")
                check_pair(first, second)
                replay_count += 1
                rows[arm].append(first)
        progress[arm] = {"primary": primary_count, "replay": replay_count, "of": 250}
        if replay_count == 250:
            complete.add(arm)
    totals = {}
    base = {r["task"]: r["correct"] for r in rows["base"]}
    small = {r["task"]: r["correct"] for r in rows["guide640"]}
    training = read(ROOT / "training.json")["guides"]
    for arm in ARMS:
        value = {"units": 0 if arm == "base" else int(arm[5:]),
                 "status": "AUDITED" if arm in complete else "PENDING",
                 "measurement_batch": "2026-09-30" if arm in HISTORICAL else "CAPACITY-STUDY"}
        if arm != "base":
            value.update(training[arm])
        if arm in complete:
            items = rows[arm]
            solved = {r["task"]: r["correct"] for r in items}
            value.update(solved=sum(solved.values()), of=len(items),
                         cpu_seconds=sum(r["cost"]["cpu_seconds"] for r in items),
                         expansions=sum(r["result"]["expansions"] for r in items),
                         applications=sum(r["applications"] for r in items),
                         versus_base=paired(base, solved), versus_640=paired(small, solved))
        totals[arm] = value
    value = {"at": now(), "profile_sha256": digest(profile), "official_arc_score": False,
             "origin": "ARC1_TRAINING_DEVELOPMENT", "complete": len(complete) == len(ARMS),
             "historical_replays_checked": 750, "new_progress": progress, "arms": totals,
             "timing_note": "CPU descriptive; historical and new arms measured in different batches"}
    save(ROOT / "summary.json", value)
    return value


def run(profile):
    # Recheck the gate even for a direct CLI invocation.
    require(probe_finished(read(S6 / "status.json"), read(S6 / "result.json")
                           if (S6 / "result.json").exists() else {}), "S6-PROBE1 is not finished")
    profile = integrity()
    os.nice(10)
    ids = profile["source_profile"]["development"]
    for phase in ("primary", "audit"):
        jobs = [(tid, arm, phase) for i, tid in enumerate(ids)
                for arm in NEW_ARMS[i % 3:] + NEW_ARMS[:i % 3]
                if not (ROOT / phase / "results" / arm / (tid+".json")).exists()]
        # A fresh pool for audit rebuilds all guides and repeats every new result.
        with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn"),
                                 initializer=init_worker, initargs=(profile,)) as pool:
            for n, row in enumerate(pool.map(measure, jobs, chunksize=1), 1):
                if phase == "audit":
                    check_pair(read(ROOT / "primary/results" / row["arm"] / (row["task"]+".json")), row)
                save(ROOT / phase / "results" / row["arm"] / (row["task"]+".json"), row)
                status(phase.upper(), completed=n, pending_at_start=len(jobs),
                       task=row["task"], arm=row["arm"], games_started=True)
        integrity()
        report(profile)
    summary = report(profile)
    require(summary["complete"], "incomplete study")
    status("DONE", games_started=True, new_measurements=750, new_replays=750)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "report", "run", "follow"))
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == "report":
            print(json.dumps(report(integrity()), indent=2)); return
        profile = prepare()
        if args.command == "prepare":
            return
        try:
            if args.command == "follow":
                while not probe_finished(read(S6 / "status.json"), read(S6 / "result.json")
                                         if (S6 / "result.json").exists() else {}):
                    integrity()
                    status("WAITING_S6", games_started=False,
                           prerequisite=read(S6 / "status.json").get("stage"))
                    time.sleep(30)
            run(profile)
            from seed.capacity_media import build
            build()
        except Exception as exc:
            status("BLOCKED", error=type(exc).__name__, message=str(exc))
            raise


if __name__ == "__main__":
    main()
