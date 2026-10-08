"""B5: precise repair pilot, adaptive campaign and one sealed examination."""
from datetime import datetime, timezone
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys
import time
from types import FunctionType

from seed import s6_precise_capacity as c
from seed import game_selfimprove_b4 as previous
from seed import s6_prompt_pilot as pilot_gate
from seed.game_selfimprove import atomic, canonical, sha, journal, events

REPO = c.REPO
ROOT = REPO / "lab/seed/s6b5-20260928"
BASE = REPO / "lab/kaggle/s6b5-20260928"
A, B = c.A, c.B
SEEDS = (612001, 612017, 612029)
MODEL, REVISION = previous.MODEL, previous.REVISION
FULL_CALLS = 30
patch = c.patch
Execution = c.Execution
old = previous.old
no_regressions = previous.no_regressions
SOURCES = list(dict.fromkeys(c.SOURCES + ["seed/game_selfimprove_b5.py",
    "lab/kaggle/s6b5-20260928/generate.py", "lab/kaggle/s6b5-20260928/transport.py",
    "seed/s6_precise_exam.py", "tests/test_s6b5.py", "docs/ECHO45-S6-B5-DESIGN.md"]))


def strategy(fmt="local", program=None):
    if fmt != "local":
        raise ValueError("B5 local format only")
    return c.candidate(program)


def config():
    return {"base": "v5.8", "A": A, "B": B, "pilot_sampling_seeds": SEEDS,
            "pilot_calls_per_arm_per_seed": 2, "campaign_calls_per_arm": 30,
            "campaign_rounds": 6, "campaign_calls_per_round_per_arm": 5,
            "max_llm_calls_including_calibration": 76, "max_gpu_jobs": 7,
            "max_cpu_games_including_capacity": 32000,
            "max_gpu_job_seconds": 900, "paid": False, "model": MODEL, "revision": REVISION,
            "temperature": .7, "top_p": .95, "max_new_tokens": 900,
            "max_patches": 32, "exam_seeds": list(range(24200, 24260)),
            "exam_versions": [2, 3], "exam_reps": [0, 1, 2], "budget": 2000,
            "raw": "accumulate every ECHO proposal passing V1/V2; no V3/V4",
            "promote": "positive human control; pilot ECHO accepts >=1 and paired A sum > FIJO",
            "green": "original B1-B5; no changed threshold"}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == hashes(), "B5 sources changed"
    assert profile["configuration"] == json.loads(canonical(config()))
    assert profile["capacity_profile_sha256"] == sha(c.integrity())
    assert profile["runtime"] == c.previous.runtime()
    return profile


def prepare():
    profile = {"sources": hashes(), "configuration": config(),
               "capacity_profile_sha256": sha(c.integrity()), "runtime": c.previous.runtime()}
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == json.loads(canonical(profile))
    else:
        for source in SOURCES:
            target = ROOT / "source-archive" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as f:
                f.write((REPO / source).read_bytes())
        atomic(ROOT / "profile.json", profile)
        atomic(ROOT / "prepared.json", {"at": c.now(), "profile_sha256": sha(profile), "exam_opened": False})
    return integrity()


def status(stage, **data):
    row = dict(at=c.now(), stage=stage, **data)
    atomic(ROOT / "status.json", row)
    print(canonical(row), flush=True)


_native_requests = FunctionType(previous.requests.__code__, dict(previous.requests.__globals__, patch=patch),
                                previous.requests.__name__, previous.requests.__defaults__)


def requests(arm, round_id, first_id, count, current, stats, measured, accepted, feedback):
    batch = _native_requests(arm, round_id, first_id, count, current, stats, measured, accepted, feedback)
    for item in batch:
        item["prompt"] += (" B5 supports one to three observable conditions joined by AND and one parameter. "
            "COOLDOWN_CAP clamps the current remaining wait; HOLD changes future waits. "
            "reset_pending means next exploration key is a known reset and no wait is active; "
            "pending_effect means the result of a touched marker is still being observed; "
            "reset_useful means a touched marker has yielded useful evidence, not proven reset causation; "
            "path_pending and trial_pending report existing plans/trials. pred_error means more wrong "
            "than correct body predictions. hold_remaining is the current wait, capped at 100. "
            "Use actual episode features to protect useful effects. No human repair is available. "
            "Matching a guard is not proof of useful action changes.")
    return batch


def baseline():
    integrity()
    a = json.loads((c.ROOT / "measurements/baseline/A.json").read_text())
    b = json.loads((c.ROOT / "measurements/baseline/B.json").read_text())
    assert a["trace_digest"] == sha(a["rows"]) and b["trace_digest"] == sha(b["rows"])
    assert all(r["policy_sha256"] == Execution.digest(strategy()) for r in a["rows"] + b["rows"])
    return a, b


def verify(label, answer, current, before_a, before_b):
    try:
        proposal = patch.parse(answer)
        value = strategy(program=patch.append(current["program"], proposal))
    except ValueError as exc:
        return current, before_a, before_b, {"verdict": "V1", "reason": str(exc)}
    verdict = {"proposal": proposal, "candidate": value}
    try:
        a = c.measure(label + "/A", value, A)
        repeat = c.measure(label + "/replay-A", value, A, replay=True)
        verdict.update(A=c.result(before_a, a), counterexamples=previous.counterexamples(before_a, a))
        if a["trace_digest"] != repeat["trace_digest"]:
            verdict.update(verdict="V2", reason="full A replay differs")
        elif a["levels"] < before_a["levels"] + 2 or not no_regressions(before_a, a):
            verdict.update(verdict="V3", reason="under +2 A levels or individual A regression")
        else:
            b = c.measure(label + "/B", value, B)
            repeat_b = c.measure(label + "/replay-B", value, B, replay=True)
            verdict["B"] = c.result(before_b, b)
            if b["trace_digest"] != repeat_b["trace_digest"]:
                verdict.update(verdict="V2", reason="full B replay differs")
            elif not no_regressions(before_b, b):
                verdict.update(verdict="V4", reason="protected B regression")
            else:
                verdict.update(verdict="accepted", reason="unchanged V1-V4 pass")
                return value, a, b, verdict
    except Exception as exc:
        verdict.update(verdict="V2", reason="execution failed: " + type(exc).__name__)
    return current, before_a, before_b, verdict


def generator():
    definition = spec_from_file_location("_s6b5_generator", BASE / "generate.py")
    module = module_from_spec(definition)
    definition.loader.exec_module(module)
    return module


def pilot():
    saved = ROOT / "pilot.json"
    if saved.exists():
        result = json.loads(saved.read_text())
        assert result["profile_sha256"] == sha(integrity())
        return result
    base_a, base_b = baseline()
    batches = {}
    for repetition, seed in enumerate(SEEDS):
        for arm in ("fijo", "echo"):
            stats = {t: [0, 0] for t in old.TYPES}
            batches[f"local-{arm}-{seed}"] = requests("local-" + arm, repetition, 0, 2,
                                    strategy(), stats, base_a, [], [])
    path = ROOT / "pilot-requests.json"
    if path.exists():
        assert json.loads(path.read_text()) == batches
    else:
        atomic(path, batches)
    answers = generator().propose("pilot", batches, {key: int(key.rsplit('-', 1)[-1]) for key in batches})
    finals, verdicts = [], []
    for seed in SEEDS:
        for arm in ("fijo", "echo"):
            key = f"local-{arm}-{seed}"
            current, a, b = strategy(), base_a, base_b
            visible = ROOT / "pilot" / key / "journal.jsonl"
            if not events(visible):
                journal(visible, {"kind": "requests", "requests": batches[key]})
                journal(visible, {"kind": "answers", "requests": batches[key], "answers": answers["arms"][key],
                                  "model_profile": answers["profile"]})
            for request, answer in zip(batches[key], answers["arms"][key]):
                current, a, b, verdict = verify("pilot/" + key + "/" + str(request["id"]),
                                               answer["answer"], current, a, b)
                verdict.update(arm=arm, seed=seed, id=request["id"], type=request["type"],
                     prompt_sha256=sha(request["prompt"]), answer=answer["answer"], usage=answer["usage"])
                verdicts.append(verdict)
                if not any(e["kind"] == "verdict" and e["id"] == request["id"] for e in events(visible)):
                    journal(visible, dict(kind="verdict", **verdict))
                status("PILOT_VERDICT", arm=arm, seed=seed, id=request["id"], verdict=verdict["verdict"])
            finals.append({"arm": arm, "seed": seed, "strategy": current, "A": a["levels"], "B": b["levels"]})
    accepted = sum(v["arm"] == "echo" and v["verdict"] == "accepted" for v in verdicts)
    echo_a = sum(row["A"] for row in finals if row["arm"] == "echo")
    fijo_a = sum(row["A"] for row in finals if row["arm"] == "fijo")
    result = {"at": c.now(), "profile_sha256": sha(integrity()), "promote": bool(accepted and echo_a > fijo_a),
              "accepted_echo": accepted, "paired_A_echo": echo_a, "paired_A_fijo": fijo_a,
              "final": finals, "verdicts": verdicts, "llm_calls": 14, "exam_opened": False}
    atomic(saved, result)
    return result


def reconstruct(arm):
    current = strategy()
    stats = {t: [0, 0] for t in old.TYPES}
    accepted, feedback = [], []
    for e in events(ROOT / arm / "journal.jsonl"):
        if e["kind"] != "verdict":
            continue
        stats[e["type"]][0] += 1
        if e["verdict"] == "accepted":
            current = Execution.validate(e["candidate"])
            stats[e["type"]][1] += 1
            accepted.append(e)
        feedback.append({k: e[k] for k in ("id", "verdict", "reason", "proposal", "counterexamples") if k in e})
    return current, stats, accepted, feedback


def raw_program():
    current = strategy()
    saved = events(ROOT / "sinfiltro/journal.jsonl")
    if saved:
        current = saved[-1]["strategy"]
    return current


def raw_step(event):
    path = ROOT / "sinfiltro/journal.jsonl"
    if any(e["id"] == event["id"] for e in events(path)):
        return
    current = raw_program()
    verdict = "V1"
    try:
        proposal = patch.parse(event["answer"])
        value = strategy(program=patch.append(current["program"], proposal))
        try:
            first = c.measure("raw/" + str(event["id"]) + "/A", value, A)
            repeat = c.measure("raw/" + str(event["id"]) + "/replay-A", value, A, replay=True)
            assert first["trace_digest"] == repeat["trace_digest"]
            current, verdict = value, "EXECUTABLE"
        except Exception:
            verdict = "V2"
    except ValueError:
        pass
    journal(path, {"kind": "raw", "id": event["id"], "verdict": verdict, "strategy": current,
                   "source_answer_sha256": sha(event["answer"]), "V3": "OMITTED", "V4": "OMITTED"})


def full_campaign():
    base_a, base_b = baseline()
    for round_id in range(6):
        batches = {}
        for arm in ("local-fijo", "local-echo"):
            path = ROOT / arm / "journal.jsonl"
            saved = next((e for e in events(path) if e["kind"] == "requests" and e["round"] == round_id), None)
            if saved:
                batches[arm] = saved["requests"]
            else:
                current, stats, accepted, feedback = reconstruct(arm)
                a = c.measure("campaign/" + arm + "/current-A", current, A)
                batches[arm] = requests(arm, round_id, round_id * 5, 5, current, stats, a, accepted, feedback)
                journal(path, {"kind": "requests", "round": round_id, "requests": batches[arm]})
        answers = generator().propose("r" + str(round_id), batches,
                                      {arm: 622001 + round_id for arm in batches})
        for arm in ("local-fijo", "local-echo"):
            path = ROOT / arm / "journal.jsonl"
            if not any(e["kind"] == "answers" and e["round"] == round_id for e in events(path)):
                journal(path, {"kind": "answers", "round": round_id, "requests": batches[arm],
                              "answers": answers["arms"][arm], "model_profile": answers["profile"]})
            for req, answer in zip(batches[arm], answers["arms"][arm]):
                event = next((e for e in events(path) if e["kind"] == "verdict" and e["id"] == req["id"]), None)
                if event is None:
                    current, _, _, _ = reconstruct(arm)
                    a = c.measure("campaign/current/A", current, A)
                    b = c.measure("campaign/current/B", current, B)
                    _, _, _, event = verify("campaign/" + arm + "/" + str(req["id"]), answer["answer"], current, a, b)
                    event.update(kind="verdict", round=round_id, id=req["id"], type=req["type"],
                         prompt_sha256=sha(req["prompt"]), answer=answer["answer"], usage=answer["usage"])
                    journal(path, event)
                    status("CAMPAIGN_VERDICT", arm=arm, call=req["id"] + 1, verdict=event["verdict"])
                if arm == "local-echo":
                    raw_step(event)
    policies = {"semilla": strategy(), "fijo": reconstruct("local-fijo")[0],
                "echo": reconstruct("local-echo")[0], "sinfiltro": raw_program()}
    for arm in ("local-fijo", "local-echo"):
        assert len([e for e in events(ROOT / arm / "journal.jsonl") if e["kind"] == "verdict"]) == FULL_CALLS
    assert len(events(ROOT / "sinfiltro/journal.jsonl")) == FULL_CALLS
    path = ROOT / "strategies.json"
    if path.exists():
        assert json.loads(path.read_text()) == policies
    else:
        atomic(path, policies)
        atomic(ROOT / "completed.json", {"at": c.now(), "sources": hashes(), "strategies_sha256": sha(policies),
                                         "profile_sha256": sha(integrity()), "llm_calls": 76})
    return policies


def publish(state, **details):
    path = ROOT / "exam/audit.json"
    audit = json.loads(path.read_text()) if path.exists() else None
    green = bool(audit and audit["green"])
    lines = ["# S6-B5: estado y resultado", "", "Estado: **" + state + "**. S6: **" + ("VERDE" if green else "ROJO/PENDIENTE") + "**.", "",
             "Base v5.8, condiciones precisas y límite de espera restante; control humano, piloto y campaña separados.", "",
             "Detalles: " + canonical(details), ""]
    pilot_path = ROOT / "pilot.json"
    if pilot_path.exists():
        p = json.loads(pilot_path.read_text())
        lines += [f"Piloto: ECHO acepta {p['accepted_echo']}; suma A ECHO {p['paired_A_echo']}, FIJO {p['paired_A_fijo']}.", ""]
    if audit:
        lines += ["| Brazo | Niveles /1800 | Score medio |", "|---|---:|---:|"]
        lines += [f"| {arm} | {v['levels']} | {v['score']:.6f} |" for arm, v in audit["totals"].items()]
        lines += ["", "| Criterio | Pasa |", "|---|---|"]
        lines += [f"| {k} | {'✅' if v else '❌'} |" for k, v in audit["checks"].items()]
    lines += ["", "[Contrato](ECHO45-S6-B5-DESIGN.md) · [Estado](../lab/seed/s6b5-20260928/status.json)", ""]
    (REPO / "docs/ECHO45-S6-B5-RESULTS.md").write_text("\n".join(lines))


def follow():
    integrity()
    status("WAIT_CAPACITY", llm_calls=0)
    while not (c.ROOT / "summary.json").exists():
        path = c.ROOT / "status.json"
        if path.exists() and json.loads(path.read_text()).get("stage") == "FAILED":
            publish("SKIPPED_CAPACITY_FAILURE", llm_calls=0, exam_opened=False)
            status("SKIPPED", reason="capacity failed", llm_calls=0)
            return
        time.sleep(15)
    summary = json.loads((c.ROOT / "summary.json").read_text())
    if summary["status"] != "POSITIVE_CONTROL":
        publish("SKIPPED_NO_POSITIVE_CONTROL", llm_calls=0, exam_opened=False)
        status("SKIPPED", reason="no positive manual control", llm_calls=0)
        return
    pilot_gate.positive_gate(summary, sha(c.integrity()))
    if not pilot()["promote"]:
        publish("PILOT_NO_PROMOTION", llm_calls=14, exam_opened=False)
        status("CLOSED", result="PILOT_NO_PROMOTION", llm_calls=14)
        return
    full_campaign()
    from seed import s6_precise_exam
    s6_precise_exam.run()
    audit = json.loads((ROOT / "exam/audit.json").read_text())
    publish("EXAM_CLOSED", green=audit["green"], llm_calls=76)
    status("CLOSED", green=audit["green"], checks=audit["checks"], llm_calls=76)


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["prepare"]:
            prepare()
        elif sys.argv[1:] == ["follow"]:
            follow()
        else:
            raise SystemExit("use prepare or follow")
    except BaseException as exc:
        status("FAILED", error=type(exc).__name__, message=str(exc))
        publish("FAILED_INCOMPLETE", error=type(exc).__name__, message=str(exc))
        raise
