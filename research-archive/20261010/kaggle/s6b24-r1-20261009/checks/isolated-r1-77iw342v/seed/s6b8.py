"""B8: frozen adaptive repair experiment; no gate or reserved answer changes."""
from datetime import datetime, timezone
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import FunctionType, SimpleNamespace

from seed import s6b7 as prior, game_selfimprove_b5 as base, s6_precise_capacity as capacity
from seed.game_selfimprove import atomic, canonical, sha, journal, events
from echo_arc import repair_diagnostics as diagnostics

REPO = base.REPO
ROOT = REPO / "lab/seed/s6b8-20260929"
BASE = REPO / "lab/kaggle/s6b8-20260929"
LIVE = REPO / "lab/observability/s6b8-20260929"
A = base.A
B = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(24420, 24440)]
EXAM_SEEDS = tuple(range(24500, 24560))
SEEDS = (615001, 615017, 615029)
CAMPAIGN_SEEDS = (625001,)
MODEL, REVISION = base.MODEL, base.REVISION
Execution, strategy, patch, old = base.Execution, base.strategy, base.patch, base.old
GPU_JOB_CAP = 300
SOURCES = list(dict.fromkeys(prior.SOURCES + [
    "echo_arc/repair_diagnostics.py", "seed/s6b8.py", "seed/s6b8_exam.py",
    "tests/test_s6b8.py", "lab/kaggle/s6b8-20260929/generate.py",
    "lab/kaggle/s6b8-20260929/transport.py", "docs/ECHO45-S6-B8-DESIGN.md"]))


def config():
    return {"A": A, "B": B, "exam_seeds": EXAM_SEEDS, "pilot_seeds": SEEDS,
            "pilot_rounds": 3, "pilot_calls_per_arm_round": 1, "campaign_seeds": CAMPAIGN_SEEDS,
            "campaign_rounds": 6, "campaign_calls_per_arm_round": 5,
            "calls_with_calibration": 82, "max_jobs": 9, "gpu_job_seconds": GPU_JOB_CAP,
            "paid": False, "max_cpu_games": 40000, "workers": 4,
            "promotion": "ECHO accepts >=1 and paired A sum > FIJO",
            "criteria": "original V1-V4 and B1-B5", "previous_proposals_in_prompts": False}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def integrity():
    p = json.loads((ROOT / "profile.json").read_text())
    assert p["sources"] == hashes(), "B8 frozen source changed"
    assert p["configuration"] == json.loads(canonical(config()))
    return p


def prepare():
    prior.integrity()
    profile = {"sources": hashes(), "configuration": config(), "runtime": capacity.previous.runtime()}
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == json.loads(canonical(profile))
    else:
        for name in SOURCES:
            target = ROOT / "source-archive" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / name).read_bytes())
        atomic(ROOT / "profile.json", profile)
        atomic(ROOT / "prepared.json", {"at": now(), "profile_sha256": sha(profile), "pid": os.getpid()})
    return integrity()


def now():
    return datetime.now(timezone.utc).isoformat()


def status(stage, **fields):
    value = dict(at=now(), stage=stage, **fields)
    atomic(ROOT / "status.json", value)
    print(canonical(value), flush=True)


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    value, spec, record_dir = item
    version, seed, rep, budget = spec
    reserved = seed in EXAM_SEEDS
    assert version in (2, 3) and budget == 2000
    assert (reserved and rep in (0, 1, 2)) or (rep == 0 and (seed < 20 or seed in range(24420, 24440)))
    assert record_dir is None or (0 <= seed < 20 and not reserved)
    if reserved:
        assert (ROOT / "exam/opened.json").exists(), "exam not authorized by promotion"
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    recorder = None
    try:
        env = _gym_env(version, seed)
        counted = old.accounting().ResetCounter(env)
        if record_dir:
            # A recovery of interrupted development creates a new trace, never overwrites one.
            path = Path(record_dir) / "arc-decisions.jsonl"
            if path.exists():
                path = path.with_name(f"arc-decisions-recovery-{os.getpid()}.jsonl")
            recorder = diagnostics.DiagnosticRecorder(Journal(path))
            recorder.write(kind="start", origin="DEVELOPMENT", agent="s6b8", budget=budget)
            recorder.write(kind="game", game=env.game_id)
        rec = Execution.play(counted, budget, runner.seed_for(env.game_id, rep), value, recorder)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=Execution.digest(value), automatic_reset_indices=counted.automatic,
                   origin="RESERVED_EXAM_S6B8" if reserved else "DEVELOPMENT_A" if seed < 20 else "PROTECTED_B")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        if recorder:
            rec["episodes"] = recorder.episodes()
            rec["diagnostics"] = recorder.summary()
        assert counted.emitted == len(rec["actions"])
        old.accounting().check_record(rec)
        return rec
    finally:
        if recorder:
            recorder.write(kind="end", status="closed")
            recorder.close()
        signal.alarm(0)


measure = FunctionType(capacity.measure.__code__, dict(capacity.measure.__globals__, ROOT=ROOT,
    LIVE=LIVE, integrity=integrity, status=status, play_one=play_one), "measure", capacity.measure.__defaults__)


def verifier(measurement):
    native = FunctionType(base.verify.__code__, dict(base.verify.__globals__, A=A, B=B,
        c=SimpleNamespace(measure=measurement, result=capacity.result)), "verify", base.verify.__defaults__)

    def checked(label, answer, current, before_a, before_b):
        hint = None
        try:
            hint = diagnostics.applicability(patch.parse(answer), current["program"], before_a["rows"])
        except ValueError:
            pass  # Native V1 records the parse rejection, including its cost.
        candidate, a, b, verdict = native(label, answer, current, before_a, before_b)
        verdict["applicability"] = hint
        return candidate, a, b, verdict
    return checked


verify = verifier(measure)


def requests(arm, round_id, count, current, measured, history):
    common = ("Improve ECHO with ONE bounded JSON patch. Three AND guards at most and one integer parameter. "
              "Need >=2 extra training levels with no individual level/score losses. "
              "Format {\"patches\":[{\"when\":{FEATURE:[OP,INT]},\"set\":{PARAM:INT}}]}. "
              "Bounds " + canonical(patch.LIMITS) + "; native defaults " + canonical(patch.DEFAULTS) +
              "; observable guards " + canonical(patch.FEATURES) + ". Operators eq/ge/le. "
              "HOLD sets FUTURE waits during deliberate reset trials, never reduces a running wait. "
              "COOLDOWN_CAP clamps an ACTIVE wait and only affects it BELOW its current value. "
              "Native defaults do not change a native policy. Matching a guard does not prove it affects an action. "
              "MIN_EVIDENCE is body identification evidence; BABBLE is key exploration; WALL_MIN is wall support. "
              "ENTRY_PROBE_LIMIT bounds temporal probes; ORDER/COUNT controls govern sequence/count hypotheses. "
              "AFTER_EFFECT_POLICY 0 explore/1 strongest evidence/2 shortest goal route. "
              "PROBE_STRATEGY 0 balanced/1 reentry/2 order. Preserve learned mechanisms. "
              "No task IDs, private states, coordinates, solver or reserved data. "
              "Current accepted program: " + canonical(current["program"]) +
              ". Your previous measured attempts: " + canonical(diagnostics.feedback(history)) + ". ")
    result = []
    for offset in range(count):
        index = round_id * count + offset
        cases, focus = diagnostics.select_evidence(measured["rows"], arm, history, index)
        if arm == "fijo":
            ask = "Here are three incomplete tasks. Propose a general repair that helps solve them. "
            typ = "GENERIC"
        else:
            ask = ("Diagnose the observed state-action-outcome sequences. Focus: " + focus + ". "
                   "Choose a control whose consumption is possible in these observations. "
                   "If your prior attempt changed no actions, correct that mechanism or choose another. "
                   "If it gained levels but was rejected, refine scope/magnitude using ONLY training evidence. "
                   "Do not repeat an ineffective or accepted patch; improve the current program. "
                   "A protected rejection supplies no private details. ")
            typ = "EVIDENCE_" + focus.upper()
        result.append({"id": index, "type": typ, "prompt": common + ask + canonical(cases) + " Return JSON only."})
    return result


def generator():
    spec = spec_from_file_location("_b8_generator", BASE / "generate.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight():
    integrity()
    value = strategy()
    observed = measure("baseline/A", value, A)
    historical = json.loads((capacity.ROOT / "measurements/baseline/A.json").read_text())
    assert all(capacity.same_behavior(a, b) for a, b in zip(observed["rows"], historical["rows"]))
    plain = measure("preflight/plain", value, [(3, 19, 0, 2000)], observed=False)
    counterpart = next(r for r in observed["rows"] if r["version"] == 3 and r["seed"] == 19)
    assert capacity.same_behavior(plain["rows"][0], counterpart)
    measure("baseline/B", value, B, observed=False)
    atomic(ROOT / "preflight.json", {"pass": True, "native_parity": True, "observer_parity": True,
                                    "profile_sha256": sha(integrity())})


def load_phase(phase, round_id):
    return json.loads((ROOT / phase / f"round-{round_id}.json").read_text())


def phase_shape(phase):
    assert phase in ("pilot", "campaign")
    return (3, 1, SEEDS) if phase == "pilot" else (6, 5, CAMPAIGN_SEEDS)


def run_phase(phase, audit=False):
    rounds, count, seeds = phase_shape(phase)
    if audit:
        measurement = FunctionType(capacity.measure.__code__, dict(measure.__globals__,
            ROOT=ROOT / (phase + "-audit"), LIVE=LIVE / (phase + "-audit")), "measure", capacity.measure.__defaults__)
    else:
        measurement = measure
    verify_one = verifier(measurement)
    base_a, base_b = measurement("baseline/A", strategy(), A), measurement("baseline/B", strategy(), B, observed=False)
    actors = {f"local-{arm}-{seed}": {"current": strategy(), "a": base_a, "b": base_b, "history": []}
              for seed in seeds for arm in ("fijo", "echo")}
    all_verdicts, raw_history, raw = [], [], strategy()
    for r in range(rounds):
        stage = ("p" if phase == "pilot" else "c") + str(r)
        batches = {key: requests(key.split('-')[1], r, count, value["current"], value["a"], value["history"])
                   for key, value in actors.items()}
        saved_path = ROOT / phase / f"round-{r}.json"
        if audit or saved_path.exists():
            saved = load_phase(phase, r)
            assert saved["requests"] == batches
            response = audit_model(stage, batches)
        else:
            journal(ROOT / "live/journal.jsonl", {"kind": "requests", "phase": phase, "round": r,
                                                  "requests": batches})
            response = generator().propose(stage, batches, {key: int(key.rsplit('-', 1)[-1]) + r * 1000 for key in batches})
            saved = None
            journal(ROOT / "live/journal.jsonl", {"kind": "answers", "phase": phase, "round": r,
                                                  "answers": response})
        round_verdicts, round_raw = [], []
        for key, state in actors.items():
            arm, seed = key.split('-')[1], int(key.rsplit('-', 1)[-1])
            for req, answer in zip(batches[key], response["arms"][key]):
                label = f"{phase}/{key}/{req['id']}"
                state["current"], state["a"], state["b"], verdict = verify_one(
                    label, answer["answer"], state["current"], state["a"], state["b"])
                event = dict(verdict, arm=arm, seed=seed, id=req["id"], type=req["type"],
                             answer=answer["answer"], prompt_sha256=sha(req["prompt"]), usage=answer["usage"])
                state["history"].append(event)
                round_verdicts.append(event)
                if not audit and not saved:
                    journal(ROOT / "live/journal.jsonl", dict(kind="verdict", phase=phase, **event))
                    status("VERDICT", phase=phase, arm=arm, seed=seed, call=req["id"], verdict=event["verdict"])
                if phase == "campaign" and arm == "echo":
                    raw, raw_event = raw_step(label, raw, answer["answer"], measurement)
                    round_raw.append(raw_event)
        record = {"requests": batches, "verdicts": round_verdicts, "raw": round_raw,
                  "profile_sha256": sha(integrity())}
        if saved:
            assert canonical(saved) == canonical(record), "independent reconstruction differs"
        elif not audit:
            atomic(saved_path, record)
        all_verdicts.extend(round_verdicts)
        raw_history.extend(round_raw)
    finals = [{"arm": key.split('-')[1], "seed": int(key.rsplit('-', 1)[-1]), "strategy": v["current"],
               "A": v["a"]["levels"], "B": v["b"]["levels"]} for key, v in actors.items()]
    totals = {arm: sum(r["A"] for r in finals if r["arm"] == arm) for arm in ("fijo", "echo")}
    accepted = sum(v["arm"] == "echo" and v["verdict"] == "accepted" for v in all_verdicts)
    result = {"promote": bool(accepted and totals["echo"] > totals["fijo"]), "accepted_echo": accepted,
              "paired_A": totals, "verdicts": all_verdicts, "finals": finals, "raw": raw,
              "calls": rounds * count * 2 * len(seeds) + 2, "profile_sha256": sha(integrity()),
              "exam_opened": False}
    path = ROOT / (phase + ".json")
    if audit:
        assert result == json.loads(path.read_text())
        measured_pid = json.loads((ROOT / (phase + "-process.json")).read_text())["pid"]
        assert measured_pid != os.getpid(), "audit must be a different process"
        atomic(ROOT / (phase + "-audit.json"), {"valid": True, "verdicts_rebuilt": len(all_verdicts),
              "profile_sha256": sha(integrity()), "audit_pid": os.getpid(), "exam_opened": False})
    else:
        atomic(path, result)
    return result


def raw_step(label, current, answer, measurement):
    verdict = "V1"
    try:
        candidate = strategy(program=patch.append(current["program"], patch.parse(answer)))
        verdict = "V2"
        a = measurement(label + "/raw-A", candidate, A)
        replay = measurement(label + "/raw-replay", candidate, A, replay=True)
        if a["trace_digest"] == replay["trace_digest"]:
            current, verdict = candidate, "EXECUTABLE"
    except (ValueError, RuntimeError):
        pass
    return current, {"source_answer_sha256": sha(answer), "verdict": verdict, "strategy": current,
                     "V3": "OMITTED", "V4": "OMITTED"}


def audit_model(stage, requests_expected=None):
    import ast
    import base64
    folder, gen = BASE / stage, generator()
    payload = json.loads((folder / "payload.json").read_text())
    if requests_expected is not None:
        assert payload["requests"] == requests_expected
    assert payload["requests_sha256"] == sha(payload["requests"])
    assert payload["source_digest"] == sha(integrity())
    assert payload["sources"] == {p: (REPO / p).read_text() for p in gen.CODE}
    code = (folder / "notebook/run.py").read_text()
    parsed = ast.parse(code)
    encoded = next(n.value.args[0].args[0].value for n in parsed.body
                   if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "payload" for t in n.targets))
    assert json.loads(base64.b64decode(encoded)) == payload
    assert code == gen.template().replace("PAYLOAD", repr(encoded))
    assert hashlib.sha256(code.encode()).hexdigest() == json.loads((folder / "submission.json").read_text())["wrapper_sha256"]
    result = gen.check(json.loads((folder / "answers.json").read_text()), payload)
    return result


def publish(state):
    path = ROOT / "pilot.json"
    p = json.loads(path.read_text()) if path.exists() else None
    path = ROOT / "exam/audit.json"
    audit = json.loads(path.read_text()) if path.exists() else None
    green = bool(audit and audit["green"])
    lines = ["# S6-B8 · aplicabilidad y consecuencias", "", f"Estado: **{state}**. S6 VERDE: **{green}**.", "",
             "Mismos V1–V4 y B1–B5; propuestas inactivas consumen presupuesto y se verifican.", ""]
    if p:
        lines += [f"Piloto: ECHO {p['paired_A']['echo']}, FIJO {p['paired_A']['fijo']}; "
                  f"aceptaciones ECHO {p['accepted_echo']}; promoción {p['promote']}.", ""]
        audit_path = ROOT / "pilot-audit.json"
        lines += [f"Auditoría independiente del piloto: {'completa' if audit_path.exists() else 'pendiente'}.", ""]
    if audit:
        lines += ["| Brazo | Niveles /1800 | Score medio |", "|---|---:|---:|"]
        for arm, r in audit["totals"].items():
            lines.append(f"| {arm} | {r['levels']} | {r['score']:.6f} |")
        lines += ["", "Criterios: " + canonical(audit["checks"]), ""]
    lines += ["[Contrato](ECHO45-S6-B8-DESIGN.md) · [Estado](../lab/seed/s6b8-20260929/status.json) · "
              "[Piloto](../lab/seed/s6b8-20260929/pilot.json).", "",
              "La transferencia a ARC-1/2/3 se mide aparte; este piloto no cambia sus puntuaciones publicadas.", ""]
    (REPO / "docs/ECHO45-S6-B8-RESULTS.md").write_text("\n".join(lines))


def follow():
    prepare()
    if (ROOT / "closed.json").exists():
        return json.loads((ROOT / "closed.json").read_text())
    preflight()
    for phase in ("pilot", "campaign"):
        if not (ROOT / (phase + ".json")).exists():
            atomic(ROOT / (phase + "-process.json"), {"pid": os.getpid(), "at": now()})
            result = run_phase(phase)
        else:
            result = json.loads((ROOT / (phase + ".json")).read_text())
        if not (ROOT / (phase + "-audit.json")).exists():
            status("AUDIT", phase=phase)
            with (ROOT / (phase + "-audit-process.log")).open("a") as stream:
                subprocess.run([sys.executable, "-m", "seed.s6b8", "audit", phase],
                               check=True, stdout=stream, stderr=subprocess.STDOUT)
        if phase == "pilot" and not result["promote"]:
            value = {"stage": "CLOSED", "result": "PILOT_NO_PROMOTION", "s6_green": False,
                     "exam_opened": False, "pilot": result["paired_A"], "at": now()}
            atomic(ROOT / "closed.json", value)
            publish(value["result"])
            status("CLOSED", result=value["result"], s6_green=False, exam_opened=False)
            return value
    policies = {"semilla": strategy(), "sinfiltro": result["raw"]}
    policies.update({r["arm"]: r["strategy"] for r in result["finals"]})
    atomic(ROOT / "strategies.json", policies)
    atomic(ROOT / "completed.json", {"strategies_sha256": sha(policies), "profile_sha256": sha(integrity()),
                                      "sources": hashes(), "at": now()})
    from seed import s6b8_exam
    s6b8_exam.run()
    final = json.loads((ROOT / "exam/audit.json").read_text())
    atomic(ROOT / "closed.json", {"stage": "CLOSED", "result": "EXAM_CLOSED", "s6_green": final["green"],
                                  "checks": final["checks"], "at": now()})
    publish("EXAM_CLOSED")
    status("CLOSED", s6_green=final["green"], checks=final["checks"])


def main(args):
    try:
        if args == ["prepare"]:
            prepare()
        elif len(args) == 2 and args[0] == "audit":
            run_phase(args[1], audit=True)
        elif args == ["follow"]:
            follow()
        else:
            raise SystemExit("use prepare, follow or audit pilot/campaign")
    except Exception as exc:
        status("PENDING_ERROR", error=type(exc).__name__, message=str(exc))
        publish("PENDING_ERROR")
        raise


if __name__ == "__main__":
    from seed import s6b8
    s6b8.main(sys.argv[1:])
