"""Prepare and resume the frozen R1-R4 final examination, with a full replay audit."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import time

from seed.final_eval import digest, solver_input, judge, solve_one, learned_state

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))
ROOT = REPO / "lab/final/echo45-20260928"
ARC_PYTHON = REPO / "lab/arc3/ARC-AGI-3-Agents/.venv/bin/python"
B4 = REPO / "lab/seed/s6b4-20260928"
DATASETS = {"R1": ("lab/seed/ARC-AGI", 400), "R2": ("lab/arc2/ARC-AGI-2", 120)}
ARMS = ("semilla", "sin_s6", "con_s6")
CONFIG = {"grid_expansions": 400, "grid_depth": 4, "arc_decisions": 2000,
          "arc_environment_seed": 0, "rep": 0, "workers": 4, "R3_min_levels": 23,
          "cost_usd": 0, "aliases_are_explicit": True}


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
    tmp.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_metadata():
    result = {}
    for name, (folder, expected) in DATASETS.items():
        repo = REPO / folder
        subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "data/evaluation"], cwd=repo, check=True)
        listing = subprocess.check_output(["git", "ls-tree", "-r", "HEAD", "data/evaluation"], cwd=repo, text=True)
        rows = [line.split("\t", 1)[1] for line in listing.splitlines() if line.endswith(".json")]
        assert len(rows) == expected and sorted(rows) == sorted(
            str(p.relative_to(repo)) for p in (repo / "data/evaluation").glob("*.json"))
        result[name] = {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                        "tree_digest": digest(listing), "tasks": rows}
    # Hash only; preparing never parses evaluation grids or game implementations.
    files = sorted((REPO / "lab/arc3/environment_files").rglob("*.py")) + sorted(
        (REPO / "lab/arc3/environment_files").rglob("metadata.json"))
    result["R3"] = {str(p.relative_to(REPO)): hash_file(p) for p in files}
    return result


def sources():
    paths = ["seed/final_eval.py", "seed/final_arc.py", "seed/final_campaign.py",
             "seed/learn.py", "seed/dsl.py", "seed/sandbox.py", "seed/gym.py",
             "tests/test_final_exam.py", "docs/ECHO45-FINAL-EXAM-DESIGN.md", "lab/arc3/split.json",
             "lab/seed/s6-final-20260927/audit.json", "lab/seed/s6-final-20260927/echo/completed.json"]
    paths += [str(p.relative_to(REPO)) for p in sorted((REPO / "echo_arc").glob("*.py"))]
    paths += ["lab/kaggle/s6b4-runtime2-20260928/" + p for p in (
        "controller.py", "generate.py", "closure.py", "profile.json", "closure-profile.json",
        "inference-audit.json", "closure.json")]
    paths += ["lab/seed/s6b4-20260928/profile.json"]
    for sandbox_name in ("echo45-s2v", "echo45-s2-a"):
        paths += [f"lab/seed/sandboxes/{sandbox_name}/{f}" for f in ("library.json", "prior.json", "manifest.json", "journal.jsonl")
                  if (REPO / f"lab/seed/sandboxes/{sandbox_name}/{f}").exists()]
    if (B4 / "stopped-after-pilot.json").exists():
        paths += [str((B4 / f).relative_to(REPO)) for f in ("pilot.json", "stopped-after-pilot.json")]
    elif (B4 / "exam/audit.json").exists():
        paths += [str((B4 / f).relative_to(REPO)) for f in ("strategies.json", "completed.json", "exam/audit.json")]
    return {p: hash_file(REPO / p) for p in paths}


def s6_result():
    inference = read(REPO / "lab/kaggle/s6b4-runtime2-20260928/inference-audit.json")
    assert inference["valid"] and read(REPO / "lab/kaggle/s6b4-runtime2-20260928/closure.json")["inference_audit_valid"]
    if (B4 / "stopped-after-pilot.json").exists():
        assert read(B4 / "stopped-after-pilot.json")["exam_opened"] is False
        return {"green": False, "phase": "pilot", "actor": {"kind": "base"}}
    audit = read(B4 / "exam/audit.json")
    green = audit["green"]
    actor = {"kind": "base"}
    if green:
        candidate = read(B4 / "strategies.json")["echo"]
        assert candidate["format"] == "local"
        actor = {"kind": "patch", "program": candidate["program"]}
    return {"green": green, "phase": "exam", "actor": actor}


def arc_runtime():
    code = """import importlib.metadata as m,importlib.util as u,json,platform,hashlib,pathlib
sources={}
for package in ('arc_agi','arcengine'):
 root=pathlib.Path(u.find_spec(package).origin).parent
 sources.update({package+'/'+str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*.py'))})
print(json.dumps({'python':platform.python_version(),'sdk_sources':sources,**{p:m.version(p) for p in ('numpy','arcengine','arc-agi')}}))
"""
    return json.loads(subprocess.check_output([str(ARC_PYTHON), "-c", code], text=True))


def profile():
    # A finished pilot or full B4 audit is required to select and freeze once.
    s6 = s6_result()
    a = read(REPO / "lab/seed/s6-final-20260927/echo/completed.json")
    assert a["ops"] == 0 and read(REPO / "lab/seed/s6-final-20260927/audit.json")["arms"]["echo"]["accepted"] == []
    games = [g for g in read(REPO / "lab/arc3/split.json")["exam"] if not g.startswith("ls20-")]
    assert len(games) == 16
    return {"configuration": CONFIG, "sources": sources(), "corpora": corpus_metadata(),
            "learned": learned_state(), "arc_runtime": arc_runtime(), "games": games,
            "grid_python": subprocess.check_output(["/usr/bin/python3", "-c", "import platform;print(platform.python_version())"], text=True).strip(),
            "grid_s6_ops": 0, "s6": s6,
            "actors": {"semilla": {"kind": "seed"}, "sin_s6": {"kind": "base"}, "con_s6": s6["actor"]}}


def integrity():
    frozen = read(ROOT / "profile.json")
    assert frozen == profile(), "final profile changed"
    return frozen


def prepare():
    development = read(ROOT / "development.json")
    assert development["passed"] and development["harness_sources"] == harness_hashes()
    p = profile()
    if (ROOT / "profile.json").exists():
        return integrity()
    save(ROOT / "profile.json", p)
    save(ROOT / "prepared.json", {"at": now(), "digest": digest(p), "exam_opened": False})
    for file in p["sources"]:
        dest = ROOT / "source-archive" / file
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((REPO / file).read_bytes())
    return p


def measure_grid(name, frozen, audit=False):
    corpus = REPO / DATASETS[name][0]
    originals = {Path(p).stem: read(corpus / p) for p in frozen["corpora"][name]["tasks"]}
    trained = frozen["learned"]
    results = {}
    for arm in ("semilla", "sin_s6"):
        level, concepts, prior = ("S0", {}, {}) if arm == "semilla" else (
            trained["level"], trained["concepts"], trained["prior"])
        jobs = [(tid, solver_input(task), level, concepts, prior, CONFIG["grid_expansions"])
                for tid, task in sorted(originals.items())]
        paths = {tid: ROOT / "grid" / name / arm / (tid + ".json") for tid in originals}
        pending = jobs if audit else [job for job in jobs if not paths[job[0]].exists()]
        with ProcessPoolExecutor(max_workers=CONFIG["workers"], mp_context=multiprocessing.get_context("spawn")) as pool:
            for row in pool.map(solve_one, pending, chunksize=1):
                row["correct"] = judge(originals[row["task"]], row["result"])
                row["source_digest"] = digest(frozen)
                if audit:
                    assert row == read(paths[row["task"]]), (name, arm, row["task"])
                else:
                    save(paths[row["task"]], row)
                    save(ROOT / "status.json", {"stage": "GRID", "exam": name, "arm": arm,
                         "completed": sum(p.exists() for p in paths.values()), "of": len(paths), "at": now()})
        records = [read(paths[tid]) for tid in sorted(originals)]
        for job, row in zip(jobs, records):
            assert row["public_sha256"] == digest(job[1]) and row["source_digest"] == digest(frozen)
            assert row["level"] == level and row["budget"] == CONFIG["grid_expansions"]
            assert row["correct"] == judge(originals[row["task"]], row["result"])
        results[arm] = {"solved": sum(r["correct"] for r in records), "tasks": len(records), "records_digest": digest(records)}
    results["con_s6"] = dict(results["sin_s6"], alias_of="sin_s6", reason="S6-A accepted zero operations")
    return results


def measure_arc(frozen, audit=False):
    from seed.final_arc import one, accounting, protocol_check
    results, distinct = {}, {}
    for arm, actor in frozen["actors"].items():
        key = digest(actor)
        if key in distinct:
            results[arm] = dict(results[distinct[key]], alias_of=distinct[key], reason="identical frozen actor")
            continue
        distinct[key] = arm
        records = []
        for game in frozen["games"]:
            path = ROOT / "arc" / arm / (game + ".json")
            if audit or not path.exists():
                record = one(game, actor, CONFIG["arc_decisions"])
                record["source_digest"] = digest(frozen)
                if audit:
                    assert record == read(path), (arm, game)
                else:
                    save(path, record)
            record = read(path)
            assert record["source_digest"] == digest(frozen) and record["actor"] == actor
            assert record["accounting"] == accounting(record)
            assert record["sdk_counter_verified"] and protocol_check(record)
            records.append(record)
            if not audit:
                save(ROOT / "status.json", {"stage": "ARC3", "arm": arm, "completed": len(records), "of": 16, "at": now()})
        assert sum(r["win_levels"] for r in records) == 112
        results[arm] = {"levels": sum(r["levels_completed"] for r in records), "of": 112,
                        "historical_score": sum(r["historical_score"] for r in records) / 16,
                        "contract_score": sum(r["contract_score"] for r in records) / 16,
                        "decisions": sum(r["accounting"]["decisions"] for r in records),
                        "automatic_resets": sum(r["resets"] for r in records), "records_digest": digest(records)}
    return results


def arc_stage(audit=False):
    frozen = integrity()
    result = measure_arc(frozen, audit)
    integrity()
    save(ROOT / ("arc-audit.json" if audit else "arc-results.json"), result)


def exam():
    frozen = prepare()
    opened = ROOT / "opened.json"
    if opened.exists():
        assert read(opened)["digest"] == digest(frozen)
    else:
        save(opened, {"at": now(), "digest": digest(frozen)})
    grid = {name: measure_grid(name, frozen) for name in DATASETS}
    save(ROOT / "grid-results.json", grid)
    subprocess.run([str(ARC_PYTHON), "-m", "seed.final_campaign", "arc"], cwd=REPO, check=True,
                   env=dict(os.environ, MPLCONFIGDIR=str(ROOT / "matplotlib")))
    integrity()
    subprocess.run([sys.executable, "-m", "seed.final_campaign", "audit"], cwd=REPO, check=True)


def audit():
    frozen = integrity()
    assert read(ROOT / "opened.json")["digest"] == digest(frozen)
    from seed.final_eval import provenance_audit
    provenance = provenance_audit()
    grid = {name: measure_grid(name, frozen, True) for name in DATASETS}
    assert grid == read(ROOT / "grid-results.json")
    subprocess.run([str(ARC_PYTHON), "-m", "seed.final_campaign", "arc-audit"], cwd=REPO, check=True,
                   env=dict(os.environ, MPLCONFIGDIR=str(ROOT / "matplotlib")))
    arc = read(ROOT / "arc-audit.json")
    assert arc == read(ROOT / "arc-results.json")
    integrity()
    criteria = {name: grid[name]["con_s6"]["solved"] > grid[name]["semilla"]["solved"] and
                grid[name]["con_s6"]["solved"] > 0 for name in DATASETS}
    criteria.update(R3=arc["con_s6"]["levels"] >= CONFIG["R3_min_levels"], R4=True)
    result = {"criteria": criteria, "green": all(criteria.values()), "grid": grid, "arc": arc,
              "provenance": provenance, "source_digest": digest(frozen), "closed": now(), "audit_pid": os.getpid()}
    save(ROOT / "audit.json", result)
    publish(result, frozen)


def publish(result, frozen):
    lines = ["# ECHO-4.5 · examen final R1–R4", "", "**" + ("VERDE" if result["green"] else "ROJO") +
             "** según el contrato. Cierre de medición; no equivale al verde de S6 o memoria.", "",
             "| Brazo | R1 /400 | R2 /120 | R3 /112 | Score contrato |", "|---|---:|---:|---:|---:|"]
    for arm in ARMS:
        lines.append(f"| {arm} | {result['grid']['R1'][arm]['solved']} | {result['grid']['R2'][arm]['solved']} | "
                     f"{result['arc'][arm]['levels']} | {result['arc'][arm]['contract_score']:.6f} |")
    lines += ["", "Criterios: " + ", ".join(k + (" ✅" if v else " ❌") for k, v in result["criteria"].items()), "",
              "S6-B4: " + ("VERDE" if frozen["s6"]["green"] else "no promovido"),
              "CON/SIN S6 de rejillas son idénticos: cero operaciones aceptadas de S6-A.",
              "Si B4 no promociona, los dos brazos v5.8 también son idénticos y se indican como alias.",
              "ARC3 tuvo exámenes anteriores; no se presenta como una nueva cohorte ciega.",
              "El gateway y los envíos externos quedan pendientes de validación y aprobación.", "",
              "[Contrato](ECHO45-FINAL-EXAM-DESIGN.md) · [Auditoría](../lab/final/echo45-20260928/audit.json).", ""]
    (REPO / "docs/ECHO45-FINAL-EXAM-RESULTS.md").write_text("\n".join(lines))


def harness_hashes():
    paths = ["seed/final_eval.py", "seed/final_arc.py", "seed/final_campaign.py", "tests/test_final_exam.py",
             "docs/ECHO45-FINAL-EXAM-DESIGN.md"]
    return {p: hash_file(REPO / p) for p in paths}


def development():
    from echoai.seed import gym
    from seed.final_eval import provenance_audit
    initial_sources = harness_hashes()
    start = time.monotonic()
    ids = gym.split()["train"][:8]
    learned = learned_state()
    timings = {}
    for name, state in (("semilla", {"level": "S0", "concepts": {}, "prior": {}}), ("sin_s6", learned)):
        begin = time.monotonic()
        jobs = [(tid, solver_input(gym.load(tid)), state["level"], state["concepts"], state["prior"], 400) for tid in ids]
        with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn")) as pool:
            rows = list(pool.map(solve_one, jobs))
        assert len(rows) == 8
        save(ROOT / ("development-grid-" + name + ".json"), rows)
        timings[name] = time.monotonic() - begin
    code = "from seed.final_arc import one;from seed.final_campaign import ROOT,save;import time;t=time.monotonic();r=one('bp35-0a0ad940',{'kind':'base'});save(ROOT/'development-arc.json',{'record':r,'seconds':time.monotonic()-t})"
    subprocess.run([str(ARC_PYTHON), "-c", code], cwd=REPO, check=True,
                   env=dict(os.environ, MPLCONFIGDIR=str(ROOT / "matplotlib")))
    provenance = provenance_audit()
    assert initial_sources == harness_hashes(), "sources changed during development"
    save(ROOT / "development.json", {"passed": True, "harness_sources": initial_sources,
         "grid_seconds_per_8": timings, "arc_seconds_per_game": read(ROOT / "development-arc.json")["seconds"],
         "provenance": provenance, "seconds": time.monotonic() - start, "at": now(), "reserved_opened": False})
    print(json.dumps(read(ROOT / "development.json")), flush=True)


def watch():
    ROOT.mkdir(parents=True, exist_ok=True)
    while not ((B4 / "stopped-after-pilot.json").exists() or (B4 / "exam/audit.json").exists()) or not (
            REPO / "lab/kaggle/s6b4-runtime2-20260928/closure.json").exists():
        save(ROOT / "status.json", {"stage": "WAIT_S6_B4_CONCLUSION", "at": now(), "reserved_opened": False})
        time.sleep(30)
    with (ROOT / "exam.log").open("a") as log:
        proc = subprocess.run([sys.executable, "-u", "-m", "seed.final_campaign", "exam"], cwd=REPO,
                              stdout=log, stderr=subprocess.STDOUT)
    save(ROOT / "exit.json", {"exit_code": proc.returncode, "at": now(), "audit_exists": (ROOT / "audit.json").exists()})
    assert proc.returncode == 0, "final exam stopped; preserve records and logs"


if __name__ == "__main__":
    assert __debug__
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("stage", choices=("dev", "prepare", "exam", "audit", "arc", "arc-audit", "watch"))
    stage = ap.parse_args().stage
    {"dev": development, "prepare": prepare, "exam": exam, "audit": audit,
     "arc": arc_stage, "arc-audit": lambda: arc_stage(True), "watch": watch}[stage]()
