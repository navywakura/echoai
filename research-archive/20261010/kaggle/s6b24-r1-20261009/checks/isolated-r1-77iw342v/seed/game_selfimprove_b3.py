"""B3: local observed verification, with short free GPU proposal jobs."""
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import multiprocessing
from pathlib import Path
import resource
import shutil
import signal
import sys

from echo_arc import temporal_policy as policy
from seed.game_selfimprove import atomic, canonical, events, journal, sha

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "lab/seed/s6b3-20260927"
BASE = REPO / "lab/kaggle/s6b3-20260927"
A = [(v, s, 0, 2000) for v in (2, 3) for s in range(20)]
B = [(v, s, 0, 2000) for v in (2, 3) for s in range(20, 40)]
TYPES = ("P1", "P2", "P3", "P4")
CALLS, ROUND_SIZE = 30, 5
MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
REVISION = "c03e6d358207e414f1eca0bb1891e29f1db0e242"
SOURCE_PATHS = ["echo_arc/__init__.py", "echo_arc/agent.py", "echo_arc/runner.py",
                "echo_arc/temporal_memory.py", "echo_arc/temporal_agent.py", "echo_arc/temporal_runner.py",
                "echo_arc/temporal_bench.py", "echo_arc/observe.py", "echo_arc/strategy.py",
                "echo_arc/strategy_grammar.py", "echo_arc/temporal_policy.py",
                "echo_arc/temporal_policy_grammar.py", "seed/__init__.py", "seed/arc3gym.py",
                "seed/game_selfimprove.py", "seed/game_selfimprove_b3.py",
                "docs/ECHO45-S6-B3-DESIGN.md", "tests/test_temporal_policy.py",
                "tests/test_temporal_campaign.py", "lab/temporal/h1h3-exam-20260927/evaluate.py",
                "lab/kaggle/s6b3-20260927/transport.py", "lab/kaggle/s6b3-20260927/generate.py",
                "lab/kaggle/s6b3-20260927/evaluate.py", "lab/kaggle/s6b3-20260927/background.py",
                "lab/kaggle/s6b3-20260927/preflight.py"]


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCE_PATHS}


def integrity(root=ROOT):
    profile = json.loads((Path(root) / "profile.json").read_text())
    assert profile["sources"] == hashes(), "B3 sources changed"
    assert profile["configuration"] == json.loads(canonical(configuration())), "B3 configuration changed"
    old = json.loads((REPO / "lab/temporal/h1h3-20260927/development-start.json").read_text())
    assert all(hashlib.sha256((REPO / p).read_bytes()).hexdigest() == h for p, h in old["protected"].items())
    return profile


def configuration():
    return {"A": A, "B": B, "calls_per_arm": CALLS, "round_size": ROUND_SIZE,
            "model": MODEL, "revision": REVISION, "temperature": .7, "top_p": .95,
            "max_new_tokens": 900, "workers": 4, "base": "v5.8", "paid": False,
            "exam_seeds": list(range(18000, 18060)), "exam_versions": [2, 3],
            "exam_reps": [0, 1, 2], "exam_budget": 2000}


def prepare():
    profile = {"sources": hashes(), "configuration": configuration(),
               "runtime": {p: importlib.metadata.version(p) for p in ("numpy", "arcengine", "arc-agi")}}
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == json.loads(canonical(profile))
    else:
        atomic(ROOT / "profile.json", profile)
        for p in SOURCE_PATHS:
            dst = ROOT / "source-archive" / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open("xb") as f:
                f.write((REPO / p).read_bytes())
    integrity()
    return profile


def worker_init():
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    def alarm(*_):
        raise TimeoutError("B3 game deadline")
    signal.signal(signal.SIGALRM, alarm)


_ACCOUNTING = None


def accounting():
    global _ACCOUNTING
    if _ACCOUNTING is None:
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("_s5f_accounting", REPO / "lab/temporal/h1h3-exam-20260927/evaluate.py")
        _ACCOUNTING = module_from_spec(spec)
        spec.loader.exec_module(_ACCOUNTING)
    return _ACCOUNTING


def play_one(item):
    candidate, spec, record_dir, observed = item
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    version, seed, rep, budget = spec
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    log = None
    try:
        env = _gym_env(version, seed)
        counted = accounting().ResetCounter(env)
        if observed:
            log = Journal(Path(record_dir) / "arc-decisions.jsonl")
            log.write(kind="start", origin="DEVELOPMENT", agent="s6b3", budget=budget,
                      policy_sha256=policy.digest(candidate))
            log.write(kind="game", game=env.game_id)
        rec = policy.play(counted, budget, runner.seed_for(env.game_id, rep), candidate, log)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=policy.digest(candidate), automatic_reset_indices=counted.automatic,
                   origin="DEVELOPMENT" if observed else "RESERVED_EXAM_S6B3")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        assert counted.emitted == len(rec["actions"])
        accounting().check_record(rec)
        return rec
    finally:
        if log is not None:
            log.write(kind="end", status="closed")
            log.close()
        signal.alarm(0)


def measure(root, candidate, specs, observed=True):
    profile = integrity()
    root = Path(root)
    candidate = policy.validate(candidate)
    records, jobs = {}, []
    for spec in specs:
        if observed:
            assert spec[1] in range(40), "training-only observation"
        key = sha({"profile": profile, "policy": candidate, "spec": spec})
        path = root / "cache" / (key + ".json")
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved["key"] == key and sha(saved["record"]) == saved["digest"]
            records[tuple(spec)] = saved["record"]
        else:
            jobs.append((candidate, spec, str(root / "decisions" / key), observed))
    if jobs:
        with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn"),
                                 initializer=worker_init) as pool:
            pending = [pool.submit(play_one, item) for item in jobs]
            for future in as_completed(pending):
                rec = future.result()
                spec = [rec["version"], rec["seed"], rec["rep"], rec["budget"]]
                key = sha({"profile": profile, "policy": candidate, "spec": spec})
                atomic(root / "cache" / (key + ".json"), {"key": key, "record": rec, "digest": sha(rec)})
                records[tuple(spec)] = rec
    rows = [records[tuple(spec)] for spec in specs]
    integrity()
    return {"levels": sum(r["levels_completed"] for r in rows),
            "score": sum(r["score"] for r in rows), "rows": rows, "trace_digest": sha(rows)}


def no_regressions(old, new):
    assert len(old["rows"]) == len(new["rows"])
    return all(n["levels_completed"] >= o["levels_completed"] and n["score"] + 1e-10 >= o["score"]
               for o, n in zip(old["rows"], new["rows"]))


def public_rows(result):
    rows = []
    for i, rec in enumerate(result["rows"]):
        model = rec.get("model", {})
        temporal = model.get("temporal", {})
        rows.append({"index": i, "levels": rec["levels_completed"], "resets": rec["resets"],
                     "actions_per_level": rec["actions_per_level"],
                     "predictions_right": model.get("predictions_right", 0),
                     "predictions_wrong": model.get("predictions_wrong", 0),
                     "world_events": model.get("world_events", 0),
                     "temporal_steps": temporal.get("steps", 0), "entries": temporal.get("entries", 0),
                     "coverage_complete": temporal.get("coverage_complete", False),
                     "order_evidence": [{k: r[k] for k in ("supports", "conflicts")}
                                         for r in temporal.get("orders", [])],
                     "count_evidence": [{k: r[k] for k in ("entries", "supports", "conflicts")}
                                         for r in temporal.get("thresholds", [])],
                     "last_actions": [[a[0], a[1]] for a in rec["actions"][-12:]]})
    return rows


def reconstruct(path):
    current, accepted = policy.EMPTY, []
    stats = {t: [0, 0] for t in TYPES}
    for event in events(path):
        if event["kind"] != "verdict":
            continue
        stats[event["type"]][0] += 1
        if event["verdict"] == "accepted":
            current = policy.parse(event["answer"])
            stats[event["type"]][1] += 1
            accepted.append(event)
    return current, stats, accepted


def unfiltered(path):
    current = policy.EMPTY
    for event in events(path):
        if event["kind"] == "verdict" and event["verdict"] not in ("V1", "V2"):
            current = policy.parse(event["answer"])
    return current


def requests(arm, round_id, current, stats, measured, accepted):
    rows = sorted(public_rows(measured), key=lambda r: (r["levels"], r["index"]))
    pending = {k: list(v) for k, v in stats.items()}
    common = ("Propose one bounded control policy for ECHO v5.8. Output JSON only. "
              "Complete defaults in the listed order, then exactly one observable condition and one override. "
              "Parameter bounds: " + canonical(policy.LIMITS) + ". Base defaults: " + canonical(policy.DEFAULTS) + ". "
              "HOLD waits between reset/mode presses; MIN_EVIDENCE identifies the body; BABBLE learns keys; "
              "WALL_MIN requires wall evidence. ENTRY_PROBE_LIMIT bounds unknown repeated entries. "
              "ORDER_MIN_SUPPORT/COUNT_MIN_SUPPORT require independent episodes before reusing a rule. "
              "ORDER_ENABLED/COUNT_ENABLED enable those memories. AFTER_EFFECT_POLICY: 0 explores unvisited "
              "markers first, 1 favors observed goal evidence, 2 favors shortest routes among goal candidates. "
              "PROBE_STRATEGY: 0 balances probes, 1 prefers repeated entries, 2 prefers ordered pairs. "
              "Feature bounds: " + canonical(policy.FEATURES) + ". Rules use eq/ge/le. "
              "Budget 2000 decisions. No game IDs, seeds, families, colors, coordinates, solver or exam. "
              "Improve levels and preserve scores of previously solved games. Current policy: " + canonical(current) + ". ")
    batch = []
    for j in range(ROUND_SIZE):
        if arm == "fijo":
            typ, data, ask = "P4", {"failures": rows[:3]}, "Here are three failures. Propose a better general policy."
        else:
            eligible = TYPES if accepted else ("P1", "P2", "P4")
            typ = max(eligible, key=lambda t: (pending[t][1] * 1000 // (pending[t][0] + 1)
                      + 300 // (pending[t][0] + 1), -((TYPES.index(t) - round_id - j) % 4)))
            pending[typ][0] += 1
            if typ == "P1":
                data = {"almost": max((r for r in rows if r["levels"] < 5), key=lambda r: r["levels"], default=rows[0])}
                ask = "Repair the almost-completed game using observed control evidence."
            elif typ == "P2":
                data, ask = {"failures": rows[:5]}, "Repair a common failure among these observed games."
            elif typ == "P3":
                data = {"last_accepted": accepted[-1]["policy"], "failures": rows[:3]}
                ask = "Generalize the last verified improvement."
            else:
                data = {"failures": rows[:3], "statistics": stats,
                        "accepted": [e["policy"] for e in accepted[-3:]]}
                ask = "Use the observed diary to choose the next useful policy."
        batch.append({"id": round_id * ROUND_SIZE + j, "type": typ,
                      "prompt": common + ask + " Evidence: " + canonical(data)})
    return batch


def arm_status(arm, stage, **fields):
    atomic(ROOT / arm / "status.json", {"arm": arm, "stage": stage, **fields,
           "updated": datetime.now(timezone.utc).isoformat()})


def verify_round(arm, round_id, batch):
    path = ROOT / arm / "journal.jsonl"
    work = ROOT / "measurements" / arm
    done = {e["id"] for e in events(path) if e["kind"] == "verdict"}
    for req, answer in zip(batch["requests"], batch["answers"]):
        if req["id"] in done:
            continue
        integrity()
        current, _, _ = reconstruct(path)
        arm_status(arm, "VERIFY_PROPOSAL", call=req["id"] + 1, of=CALLS)
        event = {"kind": "verdict", "id": req["id"], "round": round_id, "type": req["type"],
                 "prompt_sha256": sha(req["prompt"]), "answer": answer["answer"], "usage": answer["usage"]}
        try:
            candidate = policy.parse(answer["answer"])
        except ValueError as exc:
            event.update(verdict="V1", reason=str(exc))
        else:
            event["policy"] = candidate
            prior = measure(work, current, A)
            try:
                trial = measure(work, candidate, A)
                repeat = measure(ROOT / "determinism" / arm / policy.digest(candidate), candidate, A)
            except Exception as exc:
                event.update(verdict="V2", reason=type(exc).__name__)
            else:
                event.update(prior_A=prior["levels"], trial_A=trial["levels"],
                             prior_A_score=prior["score"], trial_A_score=trial["score"],
                             trial_trace=trial["trace_digest"])
                if trial["trace_digest"] != repeat["trace_digest"]:
                    event.update(verdict="V2", reason="non deterministic")
                elif trial["levels"] < prior["levels"] + 2 or not no_regressions(prior, trial):
                    event.update(verdict="V3", reason="A gain under two levels or an individual A regression")
                else:
                    before_b = measure(work, current, B)
                    after_b = measure(work, candidate, B)
                    event.update(prior_B=before_b["levels"], trial_B=after_b["levels"],
                                 prior_B_score=before_b["score"], trial_B_score=after_b["score"])
                    if not no_regressions(before_b, after_b):
                        event.update(verdict="V4", reason="individual B regression")
                    else:
                        event.update(verdict="accepted", reason="V1-V4 pass")
        journal(path, event)
        print(canonical({"arm": arm, "call": req["id"] + 1, "verdict": event["verdict"],
                         "prior_A": event.get("prior_A"), "trial_A": event.get("trial_A")}), flush=True)
        integrity()
    arm_status(arm, "ROUND_VERIFIED", round=round_id, calls=(round_id + 1) * ROUND_SIZE)


def run():
    from importlib.util import spec_from_file_location, module_from_spec
    prepare()
    for arm in ("semilla", "fijo", "echo", "sinfiltro"):
        arm_status(arm, "STARTING")
    baseline = {}
    for name, specs in (("A", A), ("B", B)):
        baseline[name] = measure(ROOT / "baseline", policy.EMPTY, specs)
        assert {r["family"] for r in baseline[name]["rows"]} == \
            {"K1", "K2", "K3", "K4", "C1", "C2", "M1", "H1", "H2", "H3", "H4"}, "incomplete A/B coverage"
        atomic(ROOT / ("baseline-" + name + ".json"), baseline[name])
    arm_status("semilla", "BASELINE_MEASURED", A=baseline["A"]["levels"], B=baseline["B"]["levels"])
    arm_status("sinfiltro", "TRACKING_ECHO_PROPOSALS")
    for arm in ("fijo", "echo"):
        work = ROOT / "measurements" / arm
        shutil.copytree(ROOT / "baseline/cache", work / "cache", dirs_exist_ok=True)
    spec = spec_from_file_location("s6b3_generate", BASE / "generate.py")
    generator = module_from_spec(spec)
    spec.loader.exec_module(generator)
    for round_id in range(CALLS // ROUND_SIZE):
        reqs, batches = {}, {}
        for arm in ("fijo", "echo"):
            path = ROOT / arm / "journal.jsonl"
            old = events(path)
            done = {e["id"] for e in old if e["kind"] == "verdict"}
            if all(round_id * ROUND_SIZE + j in done for j in range(ROUND_SIZE)):
                continue
            existing = next((e for e in old if e["kind"] == "requests" and e["round"] == round_id), None)
            if existing:
                reqs[arm] = existing["requests"]
            else:
                current, stats, accepted = reconstruct(path)
                observed = measure(ROOT / "measurements" / arm, current, A)
                reqs[arm] = requests(arm, round_id, current, stats, observed, accepted)
                journal(path, {"kind": "requests", "round": round_id, "requests": reqs[arm]})
            saved = next((e for e in old if e["kind"] == "answers" and e["round"] == round_id), None)
            if saved:
                batches[arm] = saved
        if not reqs:
            continue
        # Every GPU round contains both matched arms. Previously saved answers
        # are reused on resume; an arm that finished early never samples again.
        gpu_requests = {}
        for arm in ("fijo", "echo"):
            ev = next(e for e in events(ROOT / arm / "journal.jsonl")
                      if e["kind"] == "requests" and e["round"] == round_id)
            gpu_requests[arm] = ev["requests"]
        if len(batches) < len(reqs):
            generated = generator.propose(round_id, gpu_requests)
            for arm in reqs:
                if arm in batches:
                    continue
                batch = {"kind": "answers", "round": round_id, "requests": reqs[arm],
                         "answers": generated["arms"][arm], "model_profile": generated["profile"]}
                journal(ROOT / arm / "journal.jsonl", batch)
                batches[arm] = batch
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(verify_round, arm, round_id, batches[arm]) for arm in reqs]
            for future in futures:
                future.result()
        raw = unfiltered(ROOT / "echo/journal.jsonl")
        atomic(ROOT / "sinfiltro/current-policy.json", raw)
        arm_status("sinfiltro", "TRACKING_ECHO_PROPOSALS", round=round_id, policy_sha256=policy.digest(raw))
    export()


def export():
    strategies = {"semilla": policy.EMPTY}
    for arm in ("fijo", "echo"):
        current, stats, _ = reconstruct(ROOT / arm / "journal.jsonl")
        assert sum(v[0] for v in stats.values()) == CALLS
        strategies[arm] = current
    strategies["sinfiltro"] = unfiltered(ROOT / "echo/journal.jsonl")
    integrity()
    atomic(ROOT / "strategies.json", strategies)
    atomic(ROOT / "completed.json", {"strategies_sha256": sha(strategies), "sources": hashes(),
           "calls_per_arm": CALLS, "cost_usd": 0, "completed": datetime.now(timezone.utc).isoformat()})
    for arm in strategies:
        arm_status(arm, "FROZEN_FOR_EXAM", policy_sha256=policy.digest(strategies[arm]))


def audit_training(strategies):
    for arm in ("fijo", "echo"):
        current, accepted = policy.EMPTY, []
        stats = {t: [0, 0] for t in TYPES}
        path = ROOT / arm / "journal.jsonl"
        saved, saved_answers = {}, {}
        work = ROOT / "independent-training-audit" / arm
        for event in events(path):
            if event["kind"] == "requests":
                observed = measure(work, current, A)
                expected = requests(arm, event["round"], current, stats, observed, accepted)
                assert event["requests"] == expected, "request not reconstructible from A-only evidence"
                saved.update({r["id"]: r for r in expected})
            elif event["kind"] == "answers":
                assert event["model_profile"]["revision"] == REVISION
                assert event["model_profile"]["source_digest"] == sha(integrity())
                assert [a["id"] for a in event["answers"]] == [r["id"] for r in event["requests"]]
                saved_answers.update({a["id"]: a for a in event["answers"]})
            elif event["kind"] == "verdict":
                assert sha(saved[event["id"]]["prompt"]) == event["prompt_sha256"]
                assert event["answer"] == saved_answers[event["id"]]["answer"]
                assert event["usage"] == saved_answers[event["id"]]["usage"]
                stats[event["type"]][0] += 1
                if event["verdict"] == "accepted":
                    candidate = policy.parse(event["answer"])
                    before_a, after_a = measure(work, current, A), measure(work, candidate, A)
                    before_b, after_b = measure(work, current, B), measure(work, candidate, B)
                    assert after_a["levels"] >= before_a["levels"] + 2
                    assert no_regressions(before_a, after_a) and no_regressions(before_b, after_b)
                    assert event["prior_A"] == before_a["levels"] and event["trial_A"] == after_a["levels"]
                    assert event["prior_B"] == before_b["levels"] and event["trial_B"] == after_b["levels"]
                    current = candidate
                    stats[event["type"]][1] += 1
                    accepted.append(event)
        assert current == strategies[arm] and sum(v[0] for v in stats.values()) == CALLS
    assert strategies["semilla"] == policy.EMPTY
    assert strategies["sinfiltro"] == unfiltered(ROOT / "echo/journal.jsonl")
    atomic(ROOT / "independent-training-audit/audit.json", {"valid": True,
           "strategies_sha256": sha(strategies), "updated": datetime.now(timezone.utc).isoformat()})
    return True


if __name__ == "__main__":
    if not __debug__:
        raise RuntimeError("B3 requires assertions enabled")
    if len(sys.argv) == 2 and sys.argv[1] == "prepare":
        print(canonical({"prepared": True, "sources": len(prepare()["sources"])}))
    else:
        run()
