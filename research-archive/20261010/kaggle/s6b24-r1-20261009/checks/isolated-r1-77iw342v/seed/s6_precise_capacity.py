"""B5 instrument control, frozen before measurement; no LLM or reserved exam."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import multiprocessing
from pathlib import Path
import signal
import sys
from types import FunctionType

from echo_arc import precise_patch as patch, precise_patch_grammar as grammar
from seed import s6_capacity as previous
from seed import game_selfimprove_b4 as b4
from seed.game_selfimprove import atomic, canonical, sha

REPO = b4.REPO
ROOT = REPO / "lab/seed/s6-precise-capacity-20260928"
LIVE = REPO / "lab/observability/s6-precise-capacity-20260928"
A = b4.A
B = [(v, s, 0, 2000) for v in (2, 3) for s in range(24120, 24140)]
WORKERS = 4
SOURCES = list(dict.fromkeys(previous.SOURCES + [
    "echo_arc/precise_patch.py", "echo_arc/precise_patch_grammar.py",
    "echo_arc/precise_observe.py", "seed/s6_precise_capacity.py",
    "tests/test_precise_patch.py", "tests/test_s6_precise_capacity.py",
    "docs/ECHO45-S6-PRECISE-CONTROL.md"]))
now = previous.now
same_behavior = previous.same_behavior
result = previous.result


def candidate(program=None):
    return {"format": "local", "program": patch.validate(patch.EMPTY if program is None else program)}


class Execution:
    @staticmethod
    def validate(value):
        if type(value) is not dict or set(value) != {"format", "program"} or value["format"] != "local":
            raise ValueError("B5 local patches only")
        return candidate(value["program"])

    @staticmethod
    def digest(value):
        return sha(Execution.validate(value))

    @staticmethod
    def play(env, budget, seed, value, recorder=None):
        from echo_arc import runner
        from echo_arc.precise_observe import PreciseObservedAgent
        cls = patch.agent_class(Execution.validate(value)["program"])
        actors = []

        def factory(_):
            def make(*args, **kwargs):
                actor = cls(*args, **kwargs)
                actors.append(actor)
                if recorder is None:
                    return actor
                recorder.bind_actor(actor)
                return PreciseObservedAgent(actor, recorder)
            return make

        play = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=factory),
                            runner.play.__name__, runner.play.__defaults__)
        record = play(env, budget, seed, agent_name="s6b5")
        record["patch_hits"] = list(getattr(actors[0], "patch_hits", []))
        return record


def controls():
    r = {"reset_known": ["eq", 1]}
    choices = [
        ("hold20_after_level", dict(r, level=["ge", 1]), "HOLD", 20),
        ("hold20_after_event", dict(r, world_events=["ge", 1]), "HOLD", 20),
        ("hold20_no_effect", dict(r, pending_effect=["eq", 0]), "HOLD", 20),
        ("hold20_useful", dict(r, reset_useful=["eq", 1]), "HOLD", 20),
        ("hold20_no_path", dict(r, path_pending=["eq", 0]), "HOLD", 20),
        ("hold20_pending", {"reset_pending": ["eq", 1], "pending_effect": ["eq", 0]}, "HOLD", 20),
        ("hold10_no_effect", dict(r, pending_effect=["eq", 0]), "HOLD", 10),
        ("cap20_stuck", dict(r, pending_effect=["eq", 0], stagnation=["ge", 8]), "COOLDOWN_CAP", 20),
        ("cap0_stuck", dict(r, pending_effect=["eq", 0], stagnation=["ge", 16]), "COOLDOWN_CAP", 0),
        ("body16_error", {"body_known": ["eq", 0], "pred_error": ["eq", 1]}, "MIN_EVIDENCE", 16),
        ("body12_no_trial", {"body_known": ["eq", 0], "trial_pending": ["eq", 0]}, "MIN_EVIDENCE", 12),
        ("babble4_error", {"body_known": ["eq", 0], "pred_error": ["eq", 1]}, "BABBLE", 4),
    ]
    allowed = {canonical(g) for g in grammar.conditions()}
    out = []
    for name, guard, parameter, value in choices:
        assert canonical(guard) in allowed, "human control must be model-expressible"
        out.append({"name": name, "candidate": candidate({"patches": [{"when": guard, "set": {parameter: value}}]})})
    return out


def configuration():
    return {"purpose": "HUMAN_INSTRUMENT_CONTROL_ONLY", "A": A, "B": B,
            "budget": 2000, "workers": WORKERS, "candidates": controls(),
            "selection": "first passing candidate in frozen order",
            "criteria": "+2 A levels; no individual A/B level or score loss; full replay",
            "score_tolerance": 1e-10, "llm_calls": 0, "exam_access": False,
            "max_games": 2280, "observe": "all A; no protected B; passive parity preflight"}


def sources():
    import hashlib
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == sources(), "B5 control source changed"
    assert profile["configuration"] == json.loads(canonical(configuration()))
    assert profile["runtime"] == previous.runtime()
    previous.integrity()
    return profile


def prepare():
    previous.integrity()
    profile = {"sources": sources(), "configuration": configuration(), "runtime": previous.runtime()}
    path = ROOT / "profile.json"
    if path.exists():
        assert json.loads(path.read_text()) == json.loads(canonical(profile))
    else:
        for source in SOURCES:
            target = ROOT / "source-archive" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write((REPO / source).read_bytes())
        atomic(path, profile)
        atomic(ROOT / "prepared.json", {"at": now(), "profile_sha256": sha(profile)})
    return integrity()


def status(stage, **data):
    row = dict(at=now(), stage=stage, **data)
    atomic(ROOT / "status.json", row)
    print(json.dumps(row), flush=True)


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    from echo_arc.precise_observe import PreciseRecorder
    value, spec, record_dir = item
    version, seed, rep, budget = spec
    assert version in (2, 3) and rep == 0 and budget == 2000
    assert seed in range(20) or seed in range(24120, 24140), "B5 development only"
    assert record_dir is None or seed in range(20), "only A observations"
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    recorder = None
    try:
        env = _gym_env(version, seed)
        counted = b4.old.accounting().ResetCounter(env)
        if record_dir is not None:
            recorder = PreciseRecorder(Journal(Path(record_dir) / "arc-decisions.jsonl"))
            recorder.write(kind="start", origin="DEVELOPMENT", agent="s6b5", budget=budget,
                           strategy_sha256=Execution.digest(value))
            recorder.write(kind="game", game=env.game_id)
        rec = Execution.play(counted, budget, runner.seed_for(env.game_id, rep), value, recorder)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=Execution.digest(value), automatic_reset_indices=counted.automatic,
                   origin="DEVELOPMENT_A" if seed < 20 else "PROTECTED_B")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        if recorder is not None:
            rec["episodes"] = recorder.episodes()
        assert counted.emitted == len(rec["actions"])
        b4.old.accounting().check_record(rec)
        return rec
    finally:
        if recorder is not None:
            recorder.write(kind="end", status="closed")
            recorder.close()
        signal.alarm(0)


def measure(label, value, specs, observed=True, replay=False):
    profile = integrity()
    digest = Execution.digest(value)
    records, jobs = {}, []
    partition = "replay" if replay else "main"
    for spec in specs:
        visible = observed and spec[1] in range(20)
        key = sha({"profile": sha(profile), "candidate": value, "spec": spec, "observed": visible})
        path = ROOT / "cache" / partition / (key + ".json")
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved["key"] == key and sha(saved["record"]) == saved["digest"]
            records[tuple(spec)] = saved["record"]
        else:
            directory = str(LIVE / partition / digest / key) if visible else None
            jobs.append((value, tuple(spec), directory))
    if jobs:
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context("spawn"),
                                 initializer=b4.old.worker_init) as pool:
            pending = {pool.submit(play_one, item): item for item in jobs}
            for future in as_completed(pending):
                rec = future.result()
                spec = [rec[k] for k in ("version", "seed", "rep", "budget")]
                visible = observed and rec["seed"] in range(20)
                key = sha({"profile": sha(profile), "candidate": value, "spec": spec, "observed": visible})
                atomic(ROOT / "cache" / partition / (key + ".json"), {"key": key, "digest": sha(rec), "record": rec})
                records[tuple(spec)] = rec
                status("MEASURING", label=label, completed=len(records), total=len(specs))
    rows = [records[tuple(spec)] for spec in specs]
    integrity()
    measured = {"levels": sum(r["levels_completed"] for r in rows), "rows": rows,
                "score": sum(r["score"] for r in rows), "trace_digest": sha(rows)}
    atomic(ROOT / "measurements" / (label + ".json"), measured)
    return measured


def run():
    integrity()
    status("START", candidates=len(controls()))
    empty = candidate()
    base_a = measure("baseline/A", empty, A)
    historical = json.loads((b4.ROOT / "baseline-local.json").read_text())
    assert all(same_behavior(a, b) for a, b in zip(base_a["rows"], historical["rows"]))
    plain = measure("preflight/plain", empty, [(3, 0, 0, 2000)], observed=False)
    assert same_behavior(plain["rows"][0], next(r for r in base_a["rows"] if r["version"] == 3 and r["seed"] == 0))
    inactive = candidate({"patches": [{"when": {"level": ["ge", 100]}, "set": {"COOLDOWN_CAP": 0}}]})
    inert = measure("preflight/inactive", inactive, A)
    assert all(same_behavior(a, b) for a, b in zip(base_a["rows"], inert["rows"]))
    assert not any(sum(r["patch_hits"]) for r in inert["rows"])
    base_b = measure("baseline/B", empty, B)
    assert measure("baseline/replay-A", empty, A, replay=True)["trace_digest"] == base_a["trace_digest"]
    assert measure("baseline/replay-B", empty, B, replay=True)["trace_digest"] == base_b["trace_digest"]
    atomic(ROOT / "preflight.json", {"at": now(), "pass": True, "native_parity": True,
           "observer_parity": True, "inactive_parity": True, "full_baseline_replay": True,
           "A": base_a["levels"], "B": base_b["levels"]})
    verdicts, winner = [], None
    for index, item in enumerate(controls()):
        name, value = item["name"], item["candidate"]
        status("CANDIDATE", name=name, index=index + 1, total=len(controls()))
        a = measure("controls/" + name + "/A", value, A)
        repeat = measure("controls/" + name + "/replay-A", value, A, replay=True)
        verdict = {"name": name, "candidate": value, "A": result(base_a, a)}
        if a["trace_digest"] != repeat["trace_digest"]:
            verdict.update(verdict="V2", reason="A full replay differs")
        elif a["levels"] < base_a["levels"] + 2 or not b4.no_regressions(base_a, a):
            verdict.update(verdict="V3", reason="under +2 levels or individual A regression")
        else:
            b = measure("controls/" + name + "/B", value, B)
            repeat = measure("controls/" + name + "/replay-B", value, B, replay=True)
            verdict["B"] = result(base_b, b)
            if b["trace_digest"] != repeat["trace_digest"]:
                verdict.update(verdict="V2", reason="B full replay differs")
            elif not b4.no_regressions(base_b, b):
                verdict.update(verdict="V4", reason="individual protected B regression")
            else:
                verdict.update(verdict="POSITIVE_CONTROL", reason="unchanged V1-V4 pass")
                winner = winner or name
        verdicts.append(verdict)
        atomic(ROOT / "verdicts.json", verdicts)
        status("VERDICT", name=name, verdict=verdict["verdict"], gain=verdict["A"]["gain"])
    summary = {"at": now(), "status": "POSITIVE_CONTROL" if winner else "NO_POSITIVE_IN_BOUNDED_SEARCH",
               "winner": winner, "manual": True, "S6_green": False, "llm_calls": 0,
               "profile_sha256": sha(integrity()), "verdicts": verdicts}
    atomic(ROOT / "summary.json", summary)
    publish(summary)
    status("CLOSED", result=summary["status"], winner=winner)


def publish(summary):
    lines = ["# S6: control de cambios precisos", "", "Estado: **" + summary["status"] + "**. S6 sigue ROJO.", "",
             "Doce controles humanos preregistrados; B nueva 24120–24139. Sin modelo ni examen.", "",
             "| Control | Niveles A | Pérdidas A | Veredicto |", "|---|---:|---:|---|"]
    for verdict in summary["verdicts"]:
        a = verdict["A"]
        lines.append(f"| {verdict['name']} | {a['before_levels']}→{a['after_levels']} | {len(a['loss_indices'])} | {verdict['verdict']} |")
    lines += ["", "Un control manual positivo valida la herramienta; todavía no demuestra automejora.",
              "Un resultado negativo solo descarta estos doce candidatos bajo este presupuesto.", "",
              "[Evidencia](../lab/seed/s6-precise-capacity-20260928/summary.json)", ""]
    (REPO / "docs/ECHO45-S6-PRECISE-RESULTS.md").write_text("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["run"]:
        try:
            run()
        except BaseException as exc:
            status("FAILED", error=type(exc).__name__, message=str(exc))
            raise
    else:
        raise SystemExit("use prepare or run")
