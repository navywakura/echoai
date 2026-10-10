"""Preregistered manual capacity controls; development only, no LLM or exam."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import multiprocessing
from pathlib import Path
import signal
import sys
import uuid

from echo_arc import local_patch, local_patch_grammar
from seed import game_selfimprove_b4 as b4
from seed.game_selfimprove import atomic, canonical, sha

REPO = b4.REPO
ROOT = REPO / "lab/seed/s6-capacity-20260928"
LIVE = REPO / "lab/observability/s6-capacity-20260928"
WORKERS = 4
SOURCES = list(dict.fromkeys(b4.SOURCES + ["seed/s6_capacity.py", "tests/test_s6_capacity.py",
                                       "docs/ECHO45-S6-CAPACITY-CONTROL.md"]))
BEHAVIOR_KEYS = ("actions", "frames", "levels", "levels_completed", "actions_per_level",
                 "automatic_reset_indices", "resets", "win_levels", "score", "model")


def controls():
    # Single patches, expressible by the frozen B4 model grammar. Fixed order.
    choices = [
        ("body16", "body_known", 0, "MIN_EVIDENCE", 16),
        ("body12", "body_known", 0, "MIN_EVIDENCE", 12),
        ("body10", "body_known", 0, "MIN_EVIDENCE", 10),
        ("motor16", "motor_ready", 0, "MIN_EVIDENCE", 16),
        ("keys16", "click_only", 0, "MIN_EVIDENCE", 16),
        ("click16", "click_only", 1, "MIN_EVIDENCE", 16),
        ("after1", "temporal_open", 1, "AFTER_EFFECT_POLICY", 1),
        ("after2", "temporal_open", 1, "AFTER_EFFECT_POLICY", 2),
        ("count_first", "motor_ready", 1, "PROBE_STRATEGY", 1),
        ("order_first", "motor_ready", 1, "PROBE_STRATEGY", 2),
        ("probe4", "motor_ready", 1, "ENTRY_PROBE_LIMIT", 4),
        ("probe12", "motor_ready", 1, "ENTRY_PROBE_LIMIT", 12),
        ("probe16", "motor_ready", 1, "ENTRY_PROBE_LIMIT", 16),
        ("order_support", "order_known", 1, "ORDER_MIN_SUPPORT", 2),
        ("count_support", "count_known", 1, "COUNT_MIN_SUPPORT", 2),
        ("count_only", "motor_ready", 1, "ORDER_ENABLED", 0),
        ("order_only", "motor_ready", 1, "COUNT_ENABLED", 0),
        ("hold80", "reset_known", 1, "HOLD", 80),
        ("hold20", "reset_known", 1, "HOLD", 20),
        ("babble4", "body_known", 0, "BABBLE", 4),
    ]
    out = []
    for name, feature, threshold, parameter, value in choices:
        guard = {feature: ["eq", threshold]}
        assert guard in local_patch_grammar.conditions()
        candidate = b4.strategy("local", {"patches": [{"when": guard, "set": {parameter: value}}]})
        out.append({"name": name, "candidate": b4.Execution.validate(candidate)})
    return out


def configuration():
    return {"purpose": "HUMAN_INSTRUMENT_CONTROL_ONLY", "cohort": "DEVELOPMENT",
            "A": b4.A, "B": b4.B, "budget": 2000, "workers": WORKERS,
            "candidates": controls(), "selection": "first passing candidate in frozen order",
            "criteria": "+2 A levels and no individual A/B level or score loss; full A/B replay",
            "score_tolerance": 1e-10, "llm_calls": 0, "paid": False,
            "observe": "one complete game v3 seed0 per measurement; passive parity preflight",
            "max_games": 2640, "exam_access": False}


def sources():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def runtime():
    packages = {p: importlib.metadata.version(p) for p in ("numpy", "arcengine", "arc-agi")}
    code = {}
    for name in ("arcengine", "arc_agi"):
        spec = importlib.util.find_spec(name)
        for base in spec.submodule_search_locations:
            for path in sorted(Path(base).rglob("*.py")):
                code[name + "/" + str(path.relative_to(base))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"packages": packages, "sdk_sources": code, "python": sys.version}


def prepare():
    b4.integrity()
    profile = {"sources": sources(), "configuration": configuration(), "runtime": runtime()}
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / "profile.json"
    if path.exists():
        assert json.loads(path.read_text()) == json.loads(canonical(profile)), "control profile changed"
    else:
        atomic(path, profile)
        for source in SOURCES:
            target = ROOT / "source-archive" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as f:
                f.write((REPO / source).read_bytes())
        atomic(ROOT / "prepared.json", {"at": now(), "profile_sha256": sha(profile)})
    return integrity()


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == sources(), "control sources changed"
    assert profile["configuration"] == json.loads(canonical(configuration())), "control configuration changed"
    assert profile["runtime"] == runtime(), "control runtime changed"
    b4.integrity()
    return profile


def now():
    return datetime.now(timezone.utc).isoformat()


def status(stage, **data):
    atomic(ROOT / "status.json", dict(at=now(), stage=stage, **data))
    print(json.dumps(dict(at=now(), stage=stage, **data)), flush=True)


def same_behavior(before, after):
    return canonical({k: before[k] for k in BEHAVIOR_KEYS}) == canonical({k: after[k] for k in BEHAVIOR_KEYS})


def result(before, after):
    assert [(r["version"], r["seed"], r["rep"], r["budget"]) for r in before["rows"]] == \
           [(r["version"], r["seed"], r["rep"], r["budget"]) for r in after["rows"]], "unpaired games"
    losses = [i for i, (b, a) in enumerate(zip(before["rows"], after["rows"]))
              if a["levels_completed"] < b["levels_completed"] or a["score"] + 1e-10 < b["score"]]
    return {"before_levels": before["levels"], "after_levels": after["levels"],
            "gain": after["levels"] - before["levels"], "loss_indices": losses,
            "activated_games": sum(any(r["patch_hits"]) for r in after["rows"]),
            "activation_count": sum(sum(r["patch_hits"]) for r in after["rows"]),
            "changed_action_games": sum(b["actions"] != a["actions"] for b, a in zip(before["rows"], after["rows"])),
            "changed_frame_games": sum(b["frames"] != a["frames"] for b, a in zip(before["rows"], after["rows"])),
            "trace_digest": after["trace_digest"]}


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    from echo_arc.repair_evidence import Recorder
    candidate, spec, visible = item
    version, seed, rep, budget = spec
    assert version in (2, 3) and seed in range(40) and rep == 0, "development only"
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    recorder = None
    try:
        env = _gym_env(version, seed)
        counted = b4.old.accounting().ResetCounter(env)
        if visible:
            recorder = Recorder(Journal(Path(visible) / "arc-decisions.jsonl"))
            recorder.write(kind="start", origin="DEVELOPMENT", agent="s6-capacity", budget=budget,
                           mission="Control humano de capacidad: observar, actuar y verificar la reparación.",
                           strategy_sha256=b4.Execution.digest(candidate))
            recorder.write(kind="game", game=env.game_id)
        rec = b4.Execution.play(counted, budget, runner.seed_for(env.game_id, rep), candidate, recorder)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=b4.Execution.digest(candidate), automatic_reset_indices=counted.automatic,
                   origin="DEVELOPMENT")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        assert counted.emitted == len(rec["actions"])
        b4.old.accounting().check_record(rec)
        return rec
    finally:
        if recorder is not None:
            recorder.write(kind="end", status="closed")
            recorder.close()
        signal.alarm(0)


def measure(label, candidate, specs, observed=True):
    profile = integrity()
    records = {}
    jobs = []
    folder = ROOT / label
    for spec in specs:
        key = sha({"profile": sha(profile), "candidate": candidate, "spec": spec})
        path = folder / "cache" / (key + ".json")
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved["key"] == key and sha(saved["record"]) == saved["digest"]
            records[tuple(spec)] = saved["record"]
        else:
            visible = str(LIVE / label / uuid.uuid4().hex) if observed and spec[:3] == (3, 0, 0) else None
            jobs.append((candidate, tuple(spec), visible))
    if jobs:
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn"),
                                 initializer=b4.old.worker_init) as pool:
            pending = {pool.submit(play_one, item): item for item in jobs}
            for future in as_completed(pending):
                rec = future.result()
                spec = [rec[k] for k in ("version", "seed", "rep", "budget")]
                key = sha({"profile": sha(profile), "candidate": candidate, "spec": spec})
                atomic(folder / "cache" / (key + ".json"), {"key": key, "digest": sha(rec), "record": rec})
                records[tuple(spec)] = rec
                status("MEASURING", label=label, completed=len(records), total=len(specs))
    rows = [records[tuple(spec)] for spec in specs]
    integrity()
    return {"levels": sum(r["levels_completed"] for r in rows), "rows": rows,
            "score": sum(r["score"] for r in rows), "trace_digest": sha(rows)}


def diagnose():
    b4.integrity()
    baseline = json.loads((b4.ROOT / "baseline-local.json").read_text())
    out = {}
    for arm in ("local-fijo", "local-echo"):
        verdicts = [e for e in b4.events(b4.ROOT / arm / "journal.jsonl") if e["kind"] == "verdict"]
        candidate = verdicts[0]["candidate"]
        rows = []
        for path in (b4.ROOT / "measurements" / arm / "cache").glob("*.json"):
            saved = json.loads(path.read_text())
            assert sha(saved["record"]) == saved["digest"]
            if saved["record"]["policy_sha256"] == b4.Execution.digest(candidate):
                rows.append(saved["record"])
        rows.sort(key=lambda r: (r["version"], r["seed"], r["rep"]))
        assert len(rows) == len(b4.A)
        trial = {"rows": rows, "levels": sum(r["levels_completed"] for r in rows), "trace_digest": sha(rows)}
        out[arm] = dict(result(baseline, trial), candidate=candidate,
                        calls=len(verdicts), unique_proposals=len({sha(e["proposal"]) for e in verdicts}))
    atomic(ROOT / "historical-diagnostic.json", out)
    return out


def run():
    integrity()
    status("START", candidates=len(controls()))
    diagnose()
    empty = b4.strategy("local")
    # Compare passive tracing to native execution in fresh worker processes.
    spec = [(3, 0, 0, 2000)]
    plain = measure("preflight/plain", empty, spec, observed=False)
    observed = measure("preflight/observed", empty, spec)
    assert plain["trace_digest"] == observed["trace_digest"], "observer changed native execution"
    base_a = measure("baseline/A", empty, b4.A)
    historical = json.loads((b4.ROOT / "baseline-local.json").read_text())
    assert all(same_behavior(b, a) for b, a in zip(historical["rows"], base_a["rows"])), "native baseline changed"
    inert = b4.strategy("local", {"patches": [{"when": {"level": ["ge", 100]}, "set": {"HOLD": 80}}]})
    unchanged = measure("preflight/inactive", inert, b4.A)
    assert all(same_behavior(b, a) for b, a in zip(base_a["rows"], unchanged["rows"])), "inactive patch changed behavior"
    assert not any(sum(r["patch_hits"]) for r in unchanged["rows"])
    base_b = measure("baseline/B", empty, b4.B)
    replay_a = measure("baseline/replay-A", empty, b4.A)
    replay_b = measure("baseline/replay-B", empty, b4.B)
    assert base_a["trace_digest"] == replay_a["trace_digest"] and base_b["trace_digest"] == replay_b["trace_digest"]
    atomic(ROOT / "preflight.json", {"at": now(), "observer_parity": True, "historical_baseline_parity": True,
                                    "inactive_parity": True, "baseline_replay": True,
                                    "A_levels": base_a["levels"], "B_levels": base_b["levels"]})
    verdicts, winner = [], None
    for index, control in enumerate(controls()):
        name, candidate = control["name"], control["candidate"]
        status("CANDIDATE", index=index + 1, total=len(controls()), name=name)
        trial = measure("candidates/" + name + "/A", candidate, b4.A)
        replay = measure("replays/" + name + "/A", candidate, b4.A)
        verdict = dict(name=name, candidate=candidate, A=result(base_a, trial))
        if trial["trace_digest"] != replay["trace_digest"]:
            verdict.update(verdict="V2", reason="full replay differs")
        elif trial["levels"] - base_a["levels"] < 2 or not b4.no_regressions(base_a, trial):
            verdict.update(verdict="V3", reason="under two A levels gain or individual A regression")
        else:
            protected = measure("candidates/" + name + "/B", candidate, b4.B)
            repeat_b = measure("replays/" + name + "/B", candidate, b4.B)
            verdict["B"] = result(base_b, protected)
            if protected["trace_digest"] != repeat_b["trace_digest"]:
                verdict.update(verdict="V2", reason="full B replay differs")
            elif not b4.no_regressions(base_b, protected):
                verdict.update(verdict="V4", reason="individual B regression")
            else:
                verdict.update(verdict="POSITIVE_CONTROL", reason="manual repair passes unchanged V1-V4")
                if winner is None:
                    winner = name
        verdicts.append(verdict)
        atomic(ROOT / "verdicts.json", verdicts)
        status("VERDICT", name=name, verdict=verdict["verdict"], gain=verdict["A"]["gain"], winner=winner)
    integrity()
    summary = {"at": now(), "status": "POSITIVE_CONTROL" if winner else "NO_POSITIVE_IN_BOUNDED_SEARCH",
               "winner": winner, "manual": True, "S6_green": False, "llm_calls": 0,
               "profile_sha256": sha(integrity()), "verdicts": verdicts}
    atomic(ROOT / "summary.json", summary)
    publish(summary)
    status("CLOSED", status=summary["status"], winner=winner)


def publish(summary):
    lines = ["# Control de capacidad S6 — resultados", "", "2026-09-28. Solo desarrollo; control humano, sin LLM.", "",
             "Estado: **" + summary["status"] + "**. S6 sigue **ROJO**.", "",
             "Se conservaron +2 niveles A y ausencia de pérdidas individuales A/B. No se abrió un examen.", "",
             "| Control | A | Pérdidas A | Partidas activadas | Acciones distintas | Veredicto |",
             "|---|---:|---:|---:|---:|---|"]
    for verdict in summary["verdicts"]:
        a = verdict["A"]
        lines.append(f"| {verdict['name']} | {a['before_levels']}→{a['after_levels']} | {len(a['loss_indices'])} | {a['activated_games']} | {a['changed_action_games']} | {verdict['verdict']} |")
    lines += ["", "Una mejora manual valida la capacidad del instrumento; no demuestra automejora ni transferencia.",
              "Una búsqueda sin control positivo solo descarta estos 20 candidatos bajo este presupuesto.", "",
              "[Contrato](ECHO45-S6-CAPACITY-CONTROL.md) · [Evidencia](../lab/seed/s6-capacity-20260928/summary.json)", ""]
    (REPO / "docs/ECHO45-S6-CAPACITY-RESULTS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "prepare":
        prepare()
    elif command == "run":
        try:
            run()
        except BaseException as exc:
            status("FAILED", error=type(exc).__name__, message=str(exc))
            raise
    else:
        raise SystemExit("use prepare or run")
