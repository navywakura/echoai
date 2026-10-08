"""Preregistered ARC-2 training-only ablations; never read evaluation tasks."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))
from echoai.seed import refinement as r
from echoai.seed.learn import Library
from seed.game_selfimprove import atomic, canonical, sha

ROOT = REPO / "lab/seed/refinement-dev-20260928"
DATA = REPO / "lab/arc2/ARC-AGI-2/data/training"
SOURCES = ("seed/refinement.py", "seed/refinement_bench.py", "seed/dsl.py", "seed/learn.py",
           "tests/test_refinement.py", "echo_arc/observe.py", "docs/ECHO45-REFINEMENT-DESIGN.md")
ARMS = {"one_pass": {"views": False, "rounds": 1, "relations": False},
        "refinement": {"views": False, "rounds": 4, "relations": False},
        "multi_view": {"views": True, "rounds": 4, "relations": False},
        "relations": {"views": True, "rounds": 4, "relations": True}}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def configuration():
    ids = json.loads((REPO / "lab/arc2/split.json").read_text())["dev"]
    ids = sorted(ids, key=lambda name: sha("refinement-dev-20260928/" + name))[:12]
    return {"dataset": str(DATA.relative_to(REPO)), "training_only": True, "tasks": ids,
            "arms": ARMS, "max_trials": 2000, "max_depth": 4, "beam_width": 12,
            "max_hypotheses": 32, "workers": 2, "model_calls": 0,
            "criterion": "development diagnostic only; no reserved green verdict"}


def prepare():
    cfg = configuration()
    inputs = {name: hashlib.sha256((DATA / (name + ".json")).read_bytes()).hexdigest() for name in cfg["tasks"]}
    profile = {"sources": hashes(), "configuration": cfg, "inputs": inputs, "python": sys.version}
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == profile
    else:
        for source in SOURCES:
            target = ROOT / "source-archive" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as f:
                f.write((REPO / source).read_bytes())
        atomic(ROOT / "profile.json", profile)
    return integrity()


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == hashes() and profile["configuration"] == configuration()
    assert profile["python"] == sys.version
    assert all(hashlib.sha256((DATA / (name + ".json")).read_bytes()).hexdigest() == digest
               for name, digest in profile["inputs"].items())
    return profile


def one(item):
    name, arm, cfg = item
    from echoai.echo_arc.observe import Journal
    task = json.loads((DATA / (name + ".json")).read_text())
    public = r.solver_input(task)
    library = r.RefinementLibrary() if cfg["relations"] else Library()
    journal = Journal(ROOT / "decisions" / arm / name / "arc-decisions.jsonl")
    try:
        result = r.solve(public, library, max_trials=2000, max_depth=4, beam_width=12,
                         views=cfg["views"], rounds=cfg["rounds"], max_hypotheses=32, journal=journal)
    finally:
        journal.close()
    # Reexecute each emitted representative separately, then expose dev answers to the judge.
    verified = True
    for program in result["programs"]:
        assert all(r.execute(r.grid(p["input"]), program, library) == r.grid(p["output"]) for p in task["train"])
    correct = [any(attempt[i] == p["output"] for attempt in result["attempts"])
               for i, p in enumerate(task["test"])]
    return {"task": name, "arm": arm, "result": result, "correct": correct,
            "solved": all(correct), "independent_demonstration_replay": verified,
            "origin": "ARC2_TRAINING_DEVELOPMENT", "task_sha256": sha(task)}


def run():
    profile = integrity()
    cfg = profile["configuration"]
    pending, rows = [], []
    for name in cfg["tasks"]:
        for arm, settings in ARMS.items():
            path = ROOT / "results" / arm / (name + ".json")
            if path.exists():
                saved = json.loads(path.read_text())
                assert saved["profile_sha256"] == sha(profile) and sha(saved["record"]) == saved["sha256"]
                rows.append(saved["record"])
            else:
                pending.append((name, arm, settings))
    with ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("spawn")) as pool:
        for future in as_completed([pool.submit(one, item) for item in pending]):
            row = future.result()
            atomic(ROOT / "results" / row["arm"] / (row["task"] + ".json"),
                   {"profile_sha256": sha(profile), "record": row, "sha256": sha(row)})
            rows.append(row)
            state = {"stage": "RUNNING", "completed": len(rows), "total": len(cfg["tasks"]) * len(ARMS),
                     "at": datetime.now(timezone.utc).isoformat()}
            atomic(ROOT / "status.json", state)
            print(canonical(state), flush=True)
    integrity()
    totals = {arm: {"solved": sum(row["solved"] for row in rows if row["arm"] == arm),
                   "tasks": len(cfg["tasks"]),
                   "trials": sum(row["result"]["trials"] for row in rows if row["arm"] == arm),
                   "ambiguous": sum(row["result"]["status"] == "AMBIGUOUS" for row in rows if row["arm"] == arm),
                   "verified_fit": sum(row["result"]["verified_programs"] > 0 for row in rows if row["arm"] == arm)}
              for arm in ARMS}
    summary = {"stage": "CLOSED", "at": datetime.now(timezone.utc).isoformat(), "totals": totals,
               "profile_sha256": sha(profile), "training_only": True, "reserved_exam": False,
               "green": None, "llm_calls": 0, "weight_updates": 0}
    atomic(ROOT / "summary.json", summary)
    atomic(ROOT / "status.json", summary)
    lines = ["# Bucle de refinamiento: desarrollo ARC-2", "", "Doce tareas de entrenamiento; ningún examen reservado.", "",
             "| Brazo | Aciertos | Ajuste exacto de ejemplos | Ambigüedad | Programas probados |",
             "|---|---:|---:|---:|---:|"]
    for arm, result in totals.items():
        lines.append(f"| {arm} | {result['solved']}/12 | {result['verified_fit']} | {result['ambiguous']} | {result['trials']} |")
    lines += ["", "Mismo límite de 2000 programas por tarea y brazo; se informa el gasto real porque una sola pasada puede usar menos.",
              "Estos resultados diagnostican desarrollo, no demuestran transferencia reservada ni un 100 %.", "",
              "[Contrato](ECHO45-REFINEMENT-DESIGN.md) · [Datos](../lab/seed/refinement-dev-20260928/summary.json)", ""]
    (REPO / "docs/ECHO45-REFINEMENT-RESULTS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["prepare"]:
            prepare()
        elif sys.argv[1:] == ["run"]:
            run()
        else:
            raise SystemExit("use prepare or run")
    except Exception as exc:
        atomic(ROOT / "status.json", {"stage": "FAILED", "error": type(exc).__name__, "message": str(exc)})
        raise
