"""Frozen, training-only ARC-1 comparison of base / 640 / 500k guide units.

Use prepare, run, audit, or follow. Existing solvers and sealed sources remain
unchanged. Timing is descriptive; deterministic budgets and outcomes replay.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))

from echoai.seed import dsl, gym, sandbox
from echoai.seed.learn import Library, solve
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from echoai.seed.final_eval import solver_input, judge, learned_state, provenance_audit
from seed.arc_comparison import freeze_guard
from echoai.echo_arc.observe import Journal

ROOT = REPO / "lab/seed/capacity500k-arc1-20260930"
ARMS = ("base", "guide640", "guide500k")
CONFIG = {"expansions": 400, "depth": 4, "attempts": 1, "workers": 2,
          "training_only": True, "model_calls": 0, "level": "S2v"}
SOURCES = ("seed/kenyon_arc1.py", "seed/kenyon_capacity.py", "seed/learn.py",
           "seed/dsl.py", "seed/gym.py", "seed/sandbox.py", "seed/final_eval.py",
           "seed/arc_comparison.py", "echo_arc/observe.py", "tests/test_kenyon_capacity.py",
           "tests/test_kenyon_arc1.py", "docs/ECHO45-CAPACITY500K-ARC1-DESIGN.md")
STATE_FILES = ("library.json", "prior.json", "manifest.json", "journal.jsonl")
_PROFILE = None
_GUIDES = {}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    with temporary.open("w") as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def status(stage, **data):
    value = {"stage": stage, "at": datetime.now(timezone.utc).isoformat(), **data}
    save(ROOT / "status.json", value)
    print(json.dumps(value, sort_keys=True), flush=True)


def configuration():
    arc1 = {p.stem for p in gym.POOLS["arc1"].glob("*.json")}
    train = set(gym.split()["train"])
    known = sandbox.verified_programs("echo45-s2v")
    fit = sorted(arc1 & set(known))
    development = sorted((arc1 & train) - set(known))
    if len(fit) != 60 or len(development) != 250:
        raise ValueError("cohort differs from preregistered 60 / 250 tasks")
    assert set(fit) <= train and not set(fit) & set(development)
    return fit, development, {tid: known[tid] for tid in fit}


def integrity():
    profile = read(ROOT / "profile.json")
    assert profile["configuration"] == CONFIG
    assert profile["sources"] == {name: file_hash(REPO / name) for name in SOURCES}
    assert profile["python"] == sys.version
    assert profile["protected"] == freeze_guard()
    assert all(file_hash(REPO / name) == expected for name, expected in profile["state_files"].items())
    assert all(file_hash(gym.POOLS["arc1"] / (tid + ".json")) == expected
               for tid, expected in profile["tasks"].items())
    return profile


def prepare():
    if (ROOT / "profile.json").exists():
        return integrity()
    sandbox._set_level(CONFIG["level"])
    provenance = provenance_audit()
    fit, development, programs = configuration()
    state = learned_state()
    contributors = {tid for concept in state["concepts"].values() for tid in concept["tasks"]}
    assert not contributors & set(development)
    state_root = REPO / "lab/seed/sandboxes/echo45-s2v"
    profile = {"configuration": CONFIG, "sources": {name: file_hash(REPO / name) for name in SOURCES},
               "python": sys.version, "protected": freeze_guard(), "state": state,
               "state_files": {str((state_root / name).relative_to(REPO)): file_hash(state_root / name)
                               for name in STATE_FILES}, "provenance": provenance,
               "fit": fit, "development": development, "programs": programs,
               "tasks": {tid: file_hash(gym.POOLS["arc1"] / (tid + ".json")) for tid in fit + development}}
    for name in SOURCES:
        target = ROOT / "source-archive" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / name).read_bytes())
    save(ROOT / "profile.json", profile)
    guides = fit_guides(profile)
    save(ROOT / "training.json", {"profile_sha256": digest(profile), "guides": guide_info(guides),
                                 "programs_reverified": len(fit), "model_calls": 0})
    status("PREPARED", tasks=len(development), arms=ARMS)
    return profile


def fit_guides(profile):
    sandbox._set_level(CONFIG["level"])
    lib = Library(profile["state"]["concepts"], profile["state"]["prior"])
    guides = {"guide640": SparsePrimitiveGuide(640), "guide500k": SparsePrimitiveGuide(500_000)}
    for tid in profile["fit"]:
        task = solver_input(read(gym.POOLS["arc1"] / (tid + ".json")))
        for guide in guides.values():
            guide.observe(task, profile["programs"][tid], lib)
    return guides


def guide_info(guides):
    return {arm: {"units": guide.units, "weight_bytes": len(guide.weights),
                  "nonzero_units": sum(w != 0 for w in guide.weights), "examples": guide.examples,
                  "weights_sha256": hashlib.sha256(guide.weights).hexdigest()}
            for arm, guide in guides.items()}


def init_worker(profile):
    global _PROFILE, _GUIDES
    _PROFILE = profile
    _GUIDES = fit_guides(profile)
    assert guide_info(_GUIDES) == read(ROOT / "training.json")["guides"]


class MeasuredLibrary(Library):
    def __init__(self, state):
        super().__init__(state["concepts"], state["prior"])
        self.applications = 0
        self.primitive_steps = 0

    def apply(self, grid, item):
        self.applications += 1
        self.primitive_steps += len(self.expand(item))
        return super().apply(grid, item)


def one(job):
    tid, arm, phase = job
    profile = _PROFILE
    task = read(gym.POOLS["arc1"] / (tid + ".json"))
    public = solver_input(task)
    assert all(set(pair) == {"input"} for pair in public["test"])
    lib = MeasuredLibrary(profile["state"])
    before = digest({"concepts": lib.concepts, "prior": lib.prior})
    journal = Journal(ROOT / phase / "decisions" / arm / tid / "arc-decisions.jsonl")
    wall, cpu = time.perf_counter(), time.process_time()
    try:
        journal.write(kind="observation", origin="ARC1_TRAINING_DEVELOPMENT", task=tid, arm=arm,
                      public_sha256=digest(public), demonstrations=len(public["train"]),
                      test_inputs=len(public["test"]), budget=CONFIG)
        if arm != "base":
            lib.guide = _GUIDES[arm].probs(public)
            journal.write(kind="hypothesis", task=tid, arm=arm, guide=lib.guide,
                          criterion="prioritize primitives; exact replay still required")
        result = solve(public, lib, max_expansions=CONFIG["expansions"], max_depth=CONFIG["depth"])
        duration = {"wall_seconds": time.perf_counter() - wall, "cpu_seconds": time.process_time() - cpu,
                    "worker_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        assert result["test_ok"] is None and result["expansions"] <= CONFIG["expansions"]
        assert before == digest({"concepts": lib.concepts, "prior": lib.prior})
        verified = result["program"] is None or verify_program(public, result["program"], profile["state"])
        assert verified
        journal.write(kind="result", task=tid, arm=arm, program=result["program"],
                      exact_demonstration_replay=verified, expansions=result["expansions"],
                      predictions=result["predictions"], applications=lib.applications)
    finally:
        journal.close()
    # Only the judge below reads development test outputs.
    return {"profile_sha256": digest(profile), "task": tid, "arm": arm,
            "public_sha256": digest(public), "correct": bool(judge(task, result)),
            "result": result, "applications": lib.applications,
            "primitive_steps_upper_count": lib.primitive_steps, "cost": duration,
            "demonstration_replay": verified, "origin": "ARC1_TRAINING_DEVELOPMENT"}


def verify_program(public, program, state):
    lib = Library(state["concepts"], state["prior"])
    for pair in public["train"]:
        out = dsl.G(pair["input"])
        for item in program:
            out = lib.apply(out, item)
        if out != dsl.G(pair["output"]):
            return False
    return True


def stable(row):
    return {key: value for key, value in row.items() if key != "cost"}


def execute(phase):
    profile = integrity()
    jobs = [(tid, arm, phase) for tid in profile["development"] for arm in ARMS]
    pending = []
    for tid, arm, _ in jobs:
        path = ROOT / phase / "results" / arm / (tid + ".json")
        if path.exists():
            assert read(path)["profile_sha256"] == digest(profile)
        else:
            pending.append((tid, arm, phase))
    done = len(jobs) - len(pending)
    status(phase.upper(), completed=done, total=len(jobs))
    with ProcessPoolExecutor(max_workers=CONFIG["workers"], mp_context=multiprocessing.get_context("spawn"),
                             initializer=init_worker, initargs=(profile,)) as pool:
        for future in as_completed([pool.submit(one, job) for job in pending]):
            row = future.result()
            save(ROOT / phase / "results" / row["arm"] / (row["task"] + ".json"), row)
            if phase == "audit":
                primary = read(ROOT / "primary/results" / row["arm"] / (row["task"] + ".json"))
                assert stable(primary) == stable(row), (row["task"], row["arm"], "replay differs")
            done += 1
            status(phase.upper(), completed=done, total=len(jobs))
    integrity()


def totals(rows):
    index = {(row["task"], row["arm"]): row for row in rows}
    assert len(index) == len(rows)
    ids = sorted({row["task"] for row in rows})
    assert set(index) == {(tid, arm) for tid in ids for arm in ARMS}
    base = {tid for tid in ids if index[tid, "base"]["correct"]}
    result = {}
    for arm in ARMS:
        solved = {tid for tid in ids if index[tid, arm]["correct"]}
        subset = [index[tid, arm] for tid in ids]
        result[arm] = {"solved": len(solved), "of": len(ids), "gained": sorted(solved-base),
                       "lost": sorted(base-solved), "expansions": sum(r["result"]["expansions"] for r in subset),
                       "applications": sum(r["applications"] for r in subset),
                       "primitive_steps_upper_count": sum(r["primitive_steps_upper_count"] for r in subset),
                       "cpu_seconds": sum(r["cost"]["cpu_seconds"] for r in subset),
                       "wall_seconds_sum": sum(r["cost"]["wall_seconds"] for r in subset)}
    return result


def close():
    profile = integrity()
    rows = [read(ROOT / "primary/results" / arm / (tid + ".json"))
            for tid in profile["development"] for arm in ARMS]
    replay = [read(ROOT / "audit/results" / arm / (tid + ".json"))
              for tid in profile["development"] for arm in ARMS]
    assert all(stable(a) == stable(b) for a, b in zip(rows, replay))
    result = totals(rows)
    checks = {"more_than_base": result["guide500k"]["solved"] > result["base"]["solved"],
              "more_than_640": result["guide500k"]["solved"] > result["guide640"]["solved"],
              "no_base_regressions": not result["guide500k"]["lost"],
              "budget": all(r["result"]["expansions"] <= CONFIG["expansions"] for r in rows),
              "audit": True}
    summary = {"profile_sha256": digest(profile), "totals": result, "checks": checks,
               "green": all(checks.values()), "replays": len(rows), "official_arc_score": False}
    save(ROOT / "summary.json", summary)
    lines = ["# CAPACITY-500K · ARC-1 de desarrollo", "",
             "250 tareas de training, separadas de los 60 programas usados para entrenar las guías.", "",
             "| Brazo | Exactas | Ganadas | Perdidas | Expansiones | CPU s |", "|---|---:|---:|---:|---:|---:|"]
    for arm, value in result.items():
        lines.append(f"| {arm} | {value['solved']}/250 | {len(value['gained'])} | {len(value['lost'])} | {value['expansions']} | {value['cpu_seconds']:.1f} |")
    lines += ["", "Puerta 500k: **" + ("VERDE" if summary["green"] else "ROJA") + "**. " +
              str(len(rows)) + " resultados completos reproducidos en otro proceso.", "",
              "Es desarrollo conocido de ARC-1 training, no una nueva puntuación oficial ni un cierre S6.", "",
              "[Contrato](ECHO45-CAPACITY500K-ARC1-DESIGN.md) · [Datos](../lab/seed/capacity500k-arc1-20260930/summary.json).", ""]
    (REPO / "docs/ECHO45-CAPACITY500K-ARC1-RESULTS.md").write_text("\n".join(lines))
    status("CLOSED", green=summary["green"], checks=checks, solved={a: v["solved"] for a, v in result.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "audit", "follow"))
    command = parser.parse_args().command
    if command == "prepare":
        prepare()
    elif command == "run":
        execute("primary")
    elif command == "audit":
        execute("audit")
        close()
    else:
        prepare()
        execute("primary")
        execute("audit")
        close()


if __name__ == "__main__":
    main()
