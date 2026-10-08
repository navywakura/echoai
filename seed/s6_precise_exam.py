"""B5 examination: policies frozen first, no observer, independent replay/audit."""
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import signal
from types import FunctionType, SimpleNamespace

from seed import game_selfimprove_b5 as s
from seed import s6_precise_capacity as c

definition = spec_from_file_location("_b5_previous_exam", s.REPO / "lab/kaggle/s6b4-20260928/evaluate.py")
previous = module_from_spec(definition)
definition.loader.exec_module(previous)


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    value, spec, visible = item
    version, seed, rep, budget = spec
    assert visible is None, "no reserved observer"
    assert version in (2, 3) and seed in range(24200, 24260) and rep in (0, 1, 2) and budget == 2000
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    try:
        env = _gym_env(version, seed)
        counted = s.old.accounting().ResetCounter(env)
        rec = s.Execution.play(counted, budget, runner.seed_for(env.game_id, rep), value)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=s.Execution.digest(value), automatic_reset_indices=counted.automatic,
                   origin="RESERVED_EXAM_S6B5")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        assert counted.emitted == len(rec["actions"])
        s.old.accounting().check_record(rec)
        return rec
    finally:
        signal.alarm(0)


measure = FunctionType(c.measure.__code__, dict(c.measure.__globals__, ROOT=s.ROOT / "exam/measurements",
                       integrity=s.integrity, play_one=play_one, status=s.status),
                       c.measure.__name__, c.measure.__defaults__)
audit_measure = FunctionType(c.measure.__code__, dict(c.measure.__globals__, ROOT=s.ROOT / "independent-training-audit",
                       integrity=s.integrity, status=s.status), c.measure.__name__, c.measure.__defaults__)


def development_one(item):
    worker = FunctionType(previous.development_one.__code__, dict(previous.development_one.__globals__, s=s),
                          previous.development_one.__name__, previous.development_one.__defaults__)
    return worker(item)


development = FunctionType(previous.development.__code__, dict(previous.development.__globals__,
                          s=s, development_one=development_one), previous.development.__name__, previous.development.__defaults__)


def checks(totals, dev, audit_valid):
    echo, base = totals["echo"], totals["semilla"]
    return {"B1": echo["levels"] * 100 >= base["levels"] * 105 and echo["score"] >= base["score"],
            "B2": echo["levels"] > totals["fijo"]["levels"],
            "B3": echo["levels"] > totals["sinfiltro"]["levels"],
            "B4": all(dev["echo"][k] >= dev["semilla"][k] for k in ("levels", "score")),
            "B5": audit_valid}


def audit_model_payloads():
    generator = s.generator()
    for stage in ("pilot", "r0", "r1", "r2", "r3", "r4", "r5"):
        folder = s.BASE / stage
        payload = json.loads((folder / "payload.json").read_text())
        result = json.loads((folder / "answers.json").read_text())
        generator.check(result, payload)
        assert payload["source_digest"] == s.sha(s.integrity())
        assert payload["requests_sha256"] == s.sha(payload["requests"])
        assert payload["sources"] == {p: (s.REPO / p).read_text() for p in generator.CODE}
        # Rebuild executable wrapper from frozen sources and exact payload.
        import base64
        code = generator.template().replace("PAYLOAD", repr(base64.b64encode(json.dumps(payload).encode()).decode()))
        assert (folder / "notebook/run.py").read_text() == code
        submitted = json.loads((folder / "submission.json").read_text())
        import hashlib
        assert submitted["wrapper_sha256"] == hashlib.sha256(code.encode()).hexdigest()
    return True


def audit_training(policies):
    # Fresh worker/cache namespace; reconstruct every prompt and every verifier outcome.
    stub = SimpleNamespace(measure=audit_measure, result=c.result)
    verifier = FunctionType(s.verify.__code__, dict(s.verify.__globals__, c=stub),
                            s.verify.__name__, s.verify.__defaults__)
    base_a = audit_measure("baseline/A", s.strategy(), s.A)
    base_b = audit_measure("baseline/B", s.strategy(), s.B)
    historical_a, historical_b = s.baseline()
    assert base_a["trace_digest"] == historical_a["trace_digest"]
    assert base_b["trace_digest"] == historical_b["trace_digest"]
    expected_raw = s.strategy()
    raw_events = {e["id"]: e for e in s.events(s.ROOT / "sinfiltro/journal.jsonl")}
    for arm in ("local-fijo", "local-echo"):
        current, a, b = s.strategy(), base_a, base_b
        stats = {typ: [0, 0] for typ in s.old.TYPES}
        accepted, feedback, reqs, answers = [], [], {}, {}
        count = 0
        for event in s.events(s.ROOT / arm / "journal.jsonl"):
            if event["kind"] == "requests":
                expected = s.requests(arm, event["round"], event["round"] * 5, 5, current, stats, a, accepted, feedback)
                assert expected == event["requests"], "prompt reconstruction differs"
                reqs.update({r["id"]: r for r in expected})
            elif event["kind"] == "answers":
                assert event["model_profile"]["revision"] == s.REVISION
                assert event["model_profile"]["source_digest"] == s.sha(s.integrity())
                answers.update({r["id"]: r for r in event["answers"]})
            elif event["kind"] == "verdict":
                index = event["id"]
                assert event["prompt_sha256"] == s.sha(reqs[index]["prompt"])
                assert event["answer"] == answers[index]["answer"] and event["usage"] == answers[index]["usage"]
                candidate, next_a, next_b, replayed = verifier("verification/" + arm + "/" + str(index),
                                                             event["answer"], current, a, b)
                for key, value in replayed.items():
                    assert s.canonical(event[key]) == s.canonical(value), (arm, index, key)
                if event["verdict"] == "accepted":
                    current, a, b = candidate, next_a, next_b
                    stats[event["type"]][1] += 1
                    accepted.append(event)
                stats[event["type"]][0] += 1
                feedback.append({k: event[k] for k in ("id", "verdict", "reason", "proposal", "counterexamples") if k in event})
                count += 1
                if arm == "local-echo":
                    raw_event = raw_events[index]
                    assert raw_event["source_answer_sha256"] == s.sha(event["answer"])
                    if raw_event["verdict"] == "EXECUTABLE":
                        proposed = s.patch.parse(event["answer"])
                        expected_raw = s.strategy(program=s.patch.append(expected_raw["program"], proposed))
                        raw_a = audit_measure("raw/" + str(index), expected_raw, s.A)
                        raw_b = audit_measure("raw-replay/" + str(index), expected_raw, s.A, replay=True)
                        assert raw_a["trace_digest"] == raw_b["trace_digest"]
                    assert raw_event["strategy"] == expected_raw
                    assert raw_event["V3"] == raw_event["V4"] == "OMITTED"
        assert count == 30 and current == policies[arm.removeprefix("local-")]
    assert expected_raw == policies["sinfiltro"]
    assert policies["semilla"] == s.strategy()
    s.atomic(s.ROOT / "independent-training-audit/audit.json", {"valid": True, "all_verdicts_recomputed": 60,
                                                             "strategies_sha256": s.sha(policies)})
    return True


def run():
    assert __debug__
    s.integrity()
    assert json.loads((s.ROOT / "pilot.json").read_text())["promote"]
    completed = json.loads((s.ROOT / "completed.json").read_text())
    policies = json.loads((s.ROOT / "strategies.json").read_text())
    assert completed["sources"] == s.hashes() and completed["strategies_sha256"] == s.sha(policies)
    assert completed["profile_sha256"] == s.sha(s.integrity())
    out = s.ROOT / "exam"
    assert not (out / "opened.json").exists(), "exam already opened; never optimize/reopen"
    s.atomic(out / "opened.json", {"at": c.now(), "strategies_sha256": s.sha(policies), "sources": s.hashes()})
    from seed import arc3gym as gym
    validation = {}
    for version in (2, 3):
        gym.VERSION = version
        validation[version] = gym.validate(list(range(24200, 24260)))
    s.atomic(out / "validation.json", validation)
    totals, replays, families = {}, {}, {}
    specs = [(v, seed, rep, 2000) for v in (2, 3) for seed in range(24200, 24260) for rep in range(3)]
    for arm, policy in policies.items():
        s.status("EXAM", arm=arm)
        result = measure(arm, policy, specs, observed=False)
        repeat = measure(arm + "-replay", policy, [spec for spec in specs if spec[2] == 0], observed=False, replay=True)
        replays[arm] = s.sha([row for row in result["rows"] if row["rep"] == 0]) == repeat["trace_digest"]
        totals[arm] = {"levels": result["levels"], "score": result["score"] / 360,
                       "policy_sha256": s.Execution.digest(policy)}
        families[arm] = {family: sum(row["levels_completed"] for row in result["rows"] if row["family"] == family)
                         for family in sorted({row["family"] for row in result["rows"]})}
    dev = {arm: development(policies[arm], out / ("development-" + arm)) for arm in ("semilla", "echo")}
    model_ok = audit_model_payloads()
    training_ok = audit_training(policies)
    verdicts = checks(totals, dev, model_ok and training_ok and all(replays.values()) and
                      all(row["solver_levels"] == row["levels"] == 300 for row in validation.values()))
    s.integrity()
    s.atomic(out / "audit.json", {"at": c.now(), "green": all(verdicts.values()), "checks": verdicts,
             "totals": totals, "families": families, "development": dev, "replays": replays,
             "training_audit": training_ok, "model_payload_audit": model_ok,
             "strategies_sha256": s.sha(policies), "sources": s.hashes(), "cost_usd": 0})
