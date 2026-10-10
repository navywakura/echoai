"""Guarded-repair pilot and conditional continuation; all evidence is training-only."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import signal
from types import FunctionType
import sys

from seed import game_selfimprove_b3 as old
from seed.game_selfimprove import atomic, canonical, sha, journal, events
from echo_arc import local_patch as patch, temporal_policy as global_policy

REPO = old.REPO
ROOT = REPO / "lab/seed/s6b4-20260928"
BASE = REPO / "lab/kaggle/s6b4-20260928"
A, B = old.A, old.B
PILOT_CALLS, FULL_CALLS = 6, 30
ARMS = ("local-fijo", "local-echo", "global-fijo", "global-echo")
MODEL, REVISION = old.MODEL, old.REVISION
DEVELOPMENT_FILES = sorted(str(p.relative_to(REPO)) for p in
    (REPO / "lab/kaggle/s6b2-20260927/development_environments").rglob("*")
    if p.is_file() and p.suffix in (".py", ".json"))
SOURCES = old.SOURCE_PATHS + DEVELOPMENT_FILES + ["echo_arc/local_patch.py", "echo_arc/local_patch_grammar.py",
           "echo_arc/repair_evidence.py", "seed/game_selfimprove_b4.py",
           "tests/test_local_patch.py", "tests/test_repair_evidence.py", "tests/test_repair_campaign.py",
           "docs/ECHO45-S6-B4-DESIGN.md", "lab/kaggle/s6b4-20260928/generate.py",
           "lab/kaggle/s6b4-20260928/transport.py", "lab/kaggle/s6b4-20260928/preflight.py",
           "lab/kaggle/s6b4-20260928/background.py", "lab/kaggle/s6b4-20260928/evaluate.py"]


def config():
    return {"A": A, "B": B, "base": "v5.8", "pilot_calls_per_arm": PILOT_CALLS,
            "pilot_arms": list(ARMS), "full_calls_per_local_arm": FULL_CALLS, "max_program_patches": 32,
            "model": MODEL, "revision": REVISION, "temperature": .7, "top_p": .95, "max_new_tokens": 900,
            "workers": 4, "paid": False, "exam_seeds": list(range(19000, 19060)),
            "exam_versions": [2, 3], "exam_reps": [0, 1, 2], "exam_budget": 2000,
            "promote": "local ECHO accepts >=1 repair; A gains >=2 levels; no individual A/B loss"}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == hashes(), "B4 sources changed"
    assert profile["configuration"] == json.loads(canonical(config())), "B4 configuration changed"
    old.integrity()
    return profile


def prepare():
    profile = {"sources": hashes(), "configuration": config(),
               "runtime": {p: importlib.metadata.version(p) for p in ("numpy", "arcengine", "arc-agi")}}
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == json.loads(canonical(profile))
    else:
        atomic(ROOT / "profile.json", profile)
        for p in SOURCES:
            target = ROOT / "source-archive" / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / p).read_bytes())
    integrity()
    return profile


def strategy(fmt, program=None):
    return {"format": fmt, "program": program if program is not None else
            (patch.EMPTY if fmt == "local" else global_policy.EMPTY)}


class Execution:
    @staticmethod
    def validate(candidate):
        if type(candidate) is not dict or set(candidate) != {"format", "program"} or candidate["format"] not in ("local", "global"):
            raise ValueError("invalid strategy format")
        module = patch if candidate["format"] == "local" else global_policy
        return strategy(candidate["format"], module.validate(candidate["program"]))

    @staticmethod
    def digest(candidate):
        return sha(Execution.validate(candidate))

    @staticmethod
    def play(env, budget, seed, candidate, recorder=None):
        from echo_arc import runner
        from echo_arc.observe import ObservedAgent
        module = patch if candidate["format"] == "local" else global_policy
        cls = module.agent_class(candidate["program"])
        actors = []
        def factory(_):
            def make(*args, **kwargs):
                actor = cls(*args, **kwargs)
                actors.append(actor)
                if recorder is None:
                    return actor
                recorder.bind_actor(actor)
                return ObservedAgent(actor, recorder)
            return make
        play = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=factory),
                            runner.play.__name__, runner.play.__defaults__)
        rec = play(env, budget, seed, agent_name="s6b4")
        rec["patch_hits"] = list(getattr(actors[0], "patch_hits", []))
        return rec


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    from echo_arc.repair_evidence import Recorder
    candidate, spec, record_dir, observed = item
    version, seed, rep, budget = spec
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    recorder = None
    try:
        env = _gym_env(version, seed)
        counted = old.accounting().ResetCounter(env)
        if observed:
            assert seed in range(40), "training observation only"
            recorder = Recorder(Journal(Path(record_dir) / "arc-decisions.jsonl"))
            recorder.write(kind="start", origin="DEVELOPMENT", agent="s6b4", budget=budget,
                           strategy_sha256=Execution.digest(candidate))
            recorder.write(kind="game", game=env.game_id)
            live_parts = Path(record_dir).parts
            if (candidate["format"] == "local" and version == 3 and seed == 0 and
                    (("measurements" in live_parts and "local-echo" in live_parts) or
                     ("baseline" in live_parts and "local" in live_parts))):
                visible = REPO / "lab/observability/s6b4-live" / Execution.digest(candidate)[:16]
                visible.mkdir(parents=True, exist_ok=True)
                os.link(recorder.journal.path, visible / "arc-decisions.jsonl")
        rec = Execution.play(counted, budget, runner.seed_for(env.game_id, rep), candidate, recorder)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=Execution.digest(candidate), automatic_reset_indices=counted.automatic,
                   origin="DEVELOPMENT" if observed else "RESERVED_EXAM_S6B4")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        if recorder is not None:
            rec["episodes"] = recorder.episodes()
        assert counted.emitted == len(rec["actions"])
        old.accounting().check_record(rec)
        return rec
    finally:
        if recorder is not None:
            recorder.write(kind="end", status="closed")
            recorder.close()
        signal.alarm(0)


measure = FunctionType(old.measure.__code__, dict(old.measure.__globals__, integrity=integrity,
                       policy=Execution, play_one=play_one), old.measure.__name__, old.measure.__defaults__)
no_regressions = old.no_regressions


def public_rows(result):
    return [{"index": i, "levels": r["levels_completed"],
             "actions_per_level": r["actions_per_level"],
             "episodes": (r.get("episodes", [])[:1] + r.get("episodes", [])[-1:])
             if len(r.get("episodes", [])) > 2 else r.get("episodes", [])}
            for i, r in enumerate(result["rows"])]


def counterexamples(before, after):
    out = []
    for i, (b, a) in enumerate(zip(before["rows"], after["rows"])):
        if a["levels_completed"] < b["levels_completed"] or a["score"] + 1e-10 < b["score"]:
            out.append({"index": i, "before_levels": b["levels_completed"], "after_levels": a["levels_completed"],
                        "score_regression": a["score"] + 1e-10 < b["score"],
                        "before_episodes": b.get("episodes", [])[-2:], "after_episodes": a.get("episodes", [])[-2:]})
    return out[:2]


def reconstruct(arm):
    current = strategy(arm.split('-')[0])
    stats = {t: [0, 0] for t in old.TYPES}
    accepted, feedback = [], []
    for e in events(ROOT / arm / "journal.jsonl"):
        if e["kind"] != "verdict":
            continue
        stats[e["type"]][0] += 1
        if e["verdict"] == "accepted":
            current = e["candidate"]
            stats[e["type"]][1] += 1
            accepted.append(e)
        feedback.append({k: e[k] for k in ("id", "verdict", "reason", "proposal", "counterexamples") if k in e})
    return current, stats, accepted, feedback


def episode_pattern(row):
    e = (row.get("episodes") or [{}])[-1]
    f = e.get("features", {})
    return tuple(f.get(k, 0) for k in ("click_only", "body_known", "motor_ready", "temporal_open", "order_known", "count_known"))


def requests(arm, round_id, first_id, count, current, stats, measured, accepted, feedback):
    rows = sorted(public_rows(measured), key=lambda r: (r["levels"], r["index"]))
    pending = {k: list(v) for k, v in stats.items()}
    fmt, teacher = arm.split('-')
    rule = ("Return {\"patches\":[{\"when\":observable_condition,\"set\":{one_parameter:integer}}]}. "
            "Inherit all base controls. This patch changes one control only when its condition matches. "
            if fmt == "local" else
            "Return defaults for all eleven parameters in their listed order, then one conditional override, "
            "using the defaults/rules schema. This is the global-format control. ")
    common = ("Repair ECHO v5.8 using observed training episodes. JSON only. " + rule +
              "Bounds: " + canonical(patch.LIMITS) + ". Native defaults: " + canonical(patch.DEFAULTS) + ". "
              "Feature bounds: " + canonical(patch.FEATURES if fmt == "local" else global_policy.FEATURES) + ". "
              "Operators: eq/ge/le. HOLD waits at reset/mode; MIN_EVIDENCE identifies body; BABBLE tries keys; "
              "WALL_MIN requires wall evidence. ENTRY_PROBE_LIMIT bounds entries; ORDER_MIN_SUPPORT/COUNT_MIN_SUPPORT "
              "require episodes of support; ORDER_ENABLED/COUNT_ENABLED enable memories; AFTER_EFFECT_POLICY "
              "0 explores markers, 1 favors goal evidence, 2 takes shortest goal routes; PROBE_STRATEGY "
              "0 balances, 1 favors reentry, 2 favors ordered pairs. "
              "Each game has five levels and 2000 decisions. A useful repair gains at least two total levels "
              "without any individual level or score loss in A and without any individual loss in unseen B. "
              "Object labels are local observed aliases, not game identifiers. No task IDs, seeds, families, "
              "solver or reserved exams are available. Current strategy: " + canonical(current["program"]) + ". ")
    batch = []
    for j in range(count):
        if teacher == "fijo":
            typ, selected, ask = "P4", rows[:3], "Here are three failures. Propose a useful general repair."
        else:
            eligible = old.TYPES if accepted else ("P1", "P2", "P4")
            typ = max(eligible, key=lambda t: (pending[t][1] * 1000 // (pending[t][0] + 1)
                      + 300 // (pending[t][0] + 1), -((old.TYPES.index(t) - round_id - j) % 4)))
            pending[typ][0] += 1
            if typ == "P1":
                selected = [max((r for r in rows if r["levels"] < 5), key=lambda r: r["levels"], default=rows[0])]
                ask = "Repair this almost-completed episode. Preserve the successful earlier behavior."
            elif typ == "P2":
                anchor = next((r for r in rows if r["levels"] < 5), rows[0])
                selected = [r for r in rows if r["levels"] < 5 and episode_pattern(r) == episode_pattern(anchor)][:3]
                ask = "Repair the shared observable failure pattern in these related episodes."
            elif typ == "P3":
                selected = rows[:2]
                ask = "Generalize the last verified repair: " + canonical(accepted[-1]["proposal"])
            else:
                selected = rows[:2]
                ask = "Choose a repair from the observed diary; use the rejection counterexamples to avoid damaging prior skills."
        data = {"failures": selected, "verification_feedback": feedback[-2:], "type_statistics": stats}
        batch.append({"id": first_id + j, "type": typ, "prompt": common + ask + " Evidence: " + canonical(data)})
    return batch


def status(arm, stage, **fields):
    atomic(ROOT / arm / "status.json", {"stage": stage, **fields, "updated": datetime.now(timezone.utc).isoformat()})


def verify(arm, round_id, reqs, answers):
    path = ROOT / arm / "journal.jsonl"
    done = {e["id"] for e in events(path) if e["kind"] == "verdict"}
    work = ROOT / "measurements" / arm
    fmt = arm.split('-')[0]
    for req, answer in zip(reqs, answers):
        if req["id"] in done:
            continue
        current, _, _, _ = reconstruct(arm)
        event = {"kind": "verdict", "id": req["id"], "round": round_id, "type": req["type"],
                 "prompt_sha256": sha(req["prompt"]), "answer": answer["answer"], "usage": answer["usage"]}
        status(arm, "VERIFY_PROPOSAL", call=req["id"] + 1, of=FULL_CALLS if fmt == "local" else PILOT_CALLS)
        try:
            proposal = (patch if fmt == "local" else global_policy).parse(answer["answer"])
            candidate = strategy(fmt, patch.append(current["program"], proposal) if fmt == "local" else proposal)
        except ValueError as exc:
            event.update(verdict="V1", reason=str(exc))
        else:
            event.update(proposal=proposal, candidate=candidate)
            before_a = measure(work, current, A)
            try:
                after_a = measure(work, candidate, A)
                repeat = measure(ROOT / "determinism" / arm / Execution.digest(candidate), candidate, A)
            except Exception as exc:
                event.update(verdict="V2", reason=type(exc).__name__)
            else:
                event.update(prior_A=before_a["levels"], trial_A=after_a["levels"],
                             prior_A_score=before_a["score"], trial_A_score=after_a["score"],
                             trial_trace=after_a["trace_digest"], counterexamples=counterexamples(before_a, after_a))
                if repeat["trace_digest"] != after_a["trace_digest"]:
                    event.update(verdict="V2", reason="non deterministic")
                elif after_a["levels"] < before_a["levels"] + 2 or not no_regressions(before_a, after_a):
                    event.update(verdict="V3", reason="under two A levels gain or individual A regression")
                else:
                    before_b, after_b = measure(work, current, B), measure(work, candidate, B)
                    event.update(prior_B=before_b["levels"], trial_B=after_b["levels"],
                                 prior_B_score=before_b["score"], trial_B_score=after_b["score"])
                    if not no_regressions(before_b, after_b):
                        # B feedback discloses only failure of the protected check.
                        event.update(verdict="V4", reason="protected B regression; no B task evidence disclosed")
                    else:
                        event.update(verdict="accepted", reason="V1-V4 pass")
        journal(path, event)
        print(canonical({"arm": arm, "call": req["id"] + 1, "verdict": event["verdict"],
                         "prior_A": event.get("prior_A"), "trial_A": event.get("trial_A")}), flush=True)
        integrity()


def round_run(round_id, first_id, count, arms):
    from importlib.util import spec_from_file_location, module_from_spec
    batches = {}
    for arm in arms:
        path = ROOT / arm / "journal.jsonl"
        old_events = events(path)
        saved = next((e for e in old_events if e["kind"] == "requests" and e["round"] == round_id), None)
        if saved:
            batches[arm] = saved["requests"]
        else:
            current, stats, accepted, feedback = reconstruct(arm)
            measured = measure(ROOT / "measurements" / arm, current, A)
            batches[arm] = requests(arm, round_id, first_id, count, current, stats, measured, accepted, feedback)
            journal(path, {"kind": "requests", "round": round_id, "requests": batches[arm]})
    spec = spec_from_file_location("_b4_generate", BASE / "generate.py")
    generator = module_from_spec(spec)
    spec.loader.exec_module(generator)
    generated = generator.propose(round_id, batches)
    for arm in arms:
        path = ROOT / arm / "journal.jsonl"
        if not any(e["kind"] == "answers" and e["round"] == round_id for e in events(path)):
            journal(path, {"kind": "answers", "round": round_id, "requests": batches[arm],
                           "answers": generated["arms"][arm], "model_profile": generated["profile"]})
    # Keep four workers per verification arm; two arms at a time bound CPU/RAM.
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(verify, arm, round_id, batches[arm], generated["arms"][arm]) for arm in arms]
        for future in futures:
            future.result()


def pilot_report(baseline):
    summaries = {}
    for arm in ARMS:
        current, stats, accepted, _ = reconstruct(arm)
        assert sum(v[0] for v in stats.values()) == PILOT_CALLS
        measured = measure(ROOT / "measurements" / arm, current, A)
        summaries[arm] = {"levels_A": measured["levels"], "score_A": measured["score"], "accepted": len(accepted)}
    e = summaries["local-echo"]
    promote = e["accepted"] >= 1 and e["levels_A"] >= baseline["local"]["levels"] + 2
    result = {"pilot_complete": True, "continue_campaign": promote, "summaries": summaries,
              "calls": 24, "green": None, "cost_usd": 0, "closed": datetime.now(timezone.utc).isoformat()}
    atomic(ROOT / "pilot.json", result)
    lines = ["# S6-B4 · piloto de desarrollo", "", result["closed"][:10], "",
             "| Brazo/formato | Niveles A /200 | Score total A | Aceptadas /6 |", "|---|---:|---:|---:|"]
    for arm, t in summaries.items():
        lines.append(f"| {arm} | {t['levels_A']} | {t['score_A']:.6f} | {t['accepted']} |")
    lines.extend(["", "Continuación automática: " + ("SÍ" if promote else "NO: falta mejora aceptada de ECHO"),
                  "El piloto no es un examen ni certifica S6 VERDE. La comparación de formatos", 
                  "incluye su historial de feedback; no aísla por sí sola todos los factores.", "",
                  "[Contrato](ECHO45-S6-B4-DESIGN.md) ·",
                  "[Recibo](../lab/seed/s6b4-20260928/pilot.json).", ""])
    (REPO / "docs/ECHO45-S6-B4-PILOT-RESULTS.md").write_text("\n".join(lines))
    return promote


def export():
    strategies = {"semilla": strategy("local")}
    for arm in ("fijo", "echo"):
        current, stats, _, _ = reconstruct("local-" + arm)
        assert sum(v[0] for v in stats.values()) == FULL_CALLS
        strategies[arm] = current
    raw = strategy("local")
    for e in events(ROOT / "local-echo/journal.jsonl"):
        if e["kind"] == "verdict" and e["verdict"] not in ("V1", "V2"):
            raw = e["candidate"]
    strategies["sinfiltro"] = raw
    integrity()
    atomic(ROOT / "strategies.json", strategies)
    atomic(ROOT / "completed.json", {"strategies_sha256": sha(strategies), "sources": hashes(),
                                     "calls_per_arm": FULL_CALLS, "completed": datetime.now(timezone.utc).isoformat()})


def run():
    prepare()
    baseline = {}
    for fmt in ("local", "global"):
        candidate = strategy(fmt)
        baseline[fmt] = measure(ROOT / "baseline" / fmt, candidate, A)
        b = measure(ROOT / "baseline" / fmt, candidate, B)
        assert all({r["family"] for r in m["rows"]} == {"K1", "K2", "K3", "K4", "C1", "C2", "M1", "H1", "H2", "H3", "H4"}
                   for m in (baseline[fmt], b))
        atomic(ROOT / ("baseline-" + fmt + ".json"), baseline[fmt])
        for teacher in ("fijo", "echo"):
            arm = fmt + "-" + teacher
            shutil.copytree(ROOT / "baseline" / fmt / "cache", ROOT / "measurements" / arm / "cache", dirs_exist_ok=True)
            status(arm, "PILOT_STARTING", calls=0, of=PILOT_CALLS)
    for i in range(PILOT_CALLS):
        round_run(i, i, 1, ARMS)
    if not pilot_report(baseline):
        atomic(ROOT / "stopped-after-pilot.json", {"reason": "no accepted improvement by local ECHO",
               "exam_opened": False, "sources": hashes(), "closed": datetime.now(timezone.utc).isoformat()})
        print(canonical({"stage": "PILOT_CLOSED", "continue_campaign": False, "exam_opened": False}), flush=True)
        return
    for rid, first in enumerate(range(PILOT_CALLS, FULL_CALLS, 3), start=PILOT_CALLS):
        round_run(rid, first, 3, ("local-fijo", "local-echo"))
    export()


if __name__ == "__main__":
    assert __debug__
    if sys.argv[1:] == ["prepare"]:
        print(canonical({"prepared": True, "sources": len(prepare()["sources"])}))
    else:
        run()
