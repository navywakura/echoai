"""One manual infrastructure recovery; original B8 sources and receipts intact."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import FunctionType, SimpleNamespace

from seed import s6b8 as s

BASE = s.REPO / "lab/kaggle/s6b8-recovery-20260929"
REF = "rogeernavarro/echo45-s6b8-recovery-p2-20260929"
SOURCES = ("seed/s6b8_recovery.py", "lab/kaggle/s6b8-recovery-20260929/transport.py",
           "docs/ECHO45-S6-B8-INFERENCE-RECOVERY.md", "tests/test_s6b8_recovery.py")


def profile():
    original = s.BASE / "p2"
    return {"original_profile_sha256": s.sha(s.integrity()), "sources": {
        p: s.hashlib.sha256((s.REPO / p).read_bytes()).hexdigest() for p in SOURCES},
        "failed_attempt": {p: s.hashlib.sha256((original / p).read_bytes()).hexdigest() for p in
                           ("payload.json", "notebook/run.py", "answers.json", "output/echo45-s6b8-p2-20260929.log")},
        "max_new_jobs": 1, "gpu_seconds_cap": 600, "paid": False, "ref": REF}


def integrity():
    assert json.loads((BASE / "profile.json").read_text()) == profile()
    return s.integrity()


def prepare():
    value = profile()
    original = json.loads((s.BASE / "p2/answers.json").read_text())
    assert not original["complete"] and not any(original["arms"].values())
    if (BASE / "profile.json").exists():
        integrity()
    else:
        s.atomic(BASE / "profile.json", value)
        for source in SOURCES:
            path = BASE / "source-archive" / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((s.REPO / source).read_bytes())


def transport(stage, *values):
    result = subprocess.run(["/home/roger/.venvs/kaggle/bin/python", str(BASE / "transport.py"),
                             stage, *map(str, values)], check=True, capture_output=True, text=True, timeout=180)
    return json.loads(result.stdout.splitlines()[-1])


def recovered_propose(stage, requests, seeds):
    integrity()
    if stage != "p2":
        return s.generator().propose(stage, requests, seeds)
    source, folder = s.BASE / "p2", BASE / "p2"
    payload = json.loads((source / "payload.json").read_text())
    assert requests == payload["requests"] and seeds == payload["model"]["seeds"]
    if (folder / "answers.json").exists():
        return audit_model(stage, requests)
    s.atomic(folder / "payload.json", payload)
    notebook = folder / "notebook"
    notebook.mkdir(parents=True, exist_ok=True)
    code = (source / "notebook/run.py").read_bytes()
    (notebook / "run.py").write_bytes(code)
    metadata = json.loads((source / "notebook/kernel-metadata.json").read_text())
    metadata.update(id=REF, title=REF.split('/')[1])
    s.atomic(notebook / "kernel-metadata.json", metadata)
    if not (folder / "submission.json").exists():
        quota = transport("quota")
        s.atomic(folder / "quota.json", quota)
        assert not quota["paid"] and quota["remaining_seconds"] >= 600
        s.atomic(folder / "submission.json", {"ref": REF, "wrapper_sha256": s.hashlib.sha256(code).hexdigest(),
                                              "recovery_profile_sha256": s.sha(profile())})
        s.atomic(folder / "submitted.json", transport("push", notebook))
    failures = 0
    while True:
        try:
            state = transport("status", REF)["status"]
            failures = 0
        except (subprocess.SubprocessError, ValueError):
            failures += 1
            if failures >= 5:
                raise
            time.sleep(30)
            continue
        s.status("GPU_RECOVERY", job="p2", status=state)
        if state in ("COMPLETE", "ERROR", "CANCELLED", "CANCEL_ACKNOWLEDGED"):
            break
        time.sleep(30)
    transport("output", REF, folder / "output")
    s.atomic(folder / "terminal.json", {"status": state, "at": s.now()})
    s.atomic(folder / "answers.json", json.loads((folder / "output/answers.json").read_text()))
    assert state == "COMPLETE", "single recovery failed; no further submission authorized here"
    return audit_model(stage, requests)


def audit_model(stage, requests_expected=None):
    integrity()
    if stage != "p2":
        return s.audit_model(stage, requests_expected)
    folder = BASE / "p2"
    assert json.loads((folder / "terminal.json").read_text())["status"] == "COMPLETE"
    assert (folder / "notebook/run.py").read_bytes() == (s.BASE / "p2/notebook/run.py").read_bytes()
    audit = FunctionType(s.audit_model.__code__, dict(s.audit_model.__globals__, BASE=BASE))
    return audit(stage, requests_expected)


def generator():
    return SimpleNamespace(propose=recovered_propose)


run_phase = FunctionType(s.run_phase.__code__, dict(s.run_phase.__globals__,
    integrity=integrity, generator=generator, audit_model=audit_model),
    "run_phase", s.run_phase.__defaults__)


def follow():
    prepare()
    for phase in ("pilot", "campaign"):
        path = s.ROOT / (phase + ".json")
        if path.exists():
            result = json.loads(path.read_text())
        else:
            s.atomic(s.ROOT / (phase + "-recovery-process.json"), {"pid": os.getpid(), "at": s.now()})
            result = run_phase(phase)
        if not (s.ROOT / (phase + "-audit.json")).exists():
            s.status("AUDIT", phase=phase)
            with (s.ROOT / (phase + "-audit-process.log")).open("a") as log:
                subprocess.run([sys.executable, "-m", "seed.s6b8_recovery", "audit", phase],
                               check=True, stdout=log, stderr=subprocess.STDOUT)
        if phase == "pilot" and not result["promote"]:
            outcome = {"stage": "CLOSED", "result": "PILOT_NO_PROMOTION", "s6_green": False,
                       "exam_opened": False, "pilot": result["paired_A"], "at": s.now(),
                       "recovery_profile_sha256": s.sha(profile())}
            s.atomic(s.ROOT / "closed.json", outcome)
            s.publish(outcome["result"])
            s.status("CLOSED", result=outcome["result"], s6_green=False, exam_opened=False)
            return
    policies = {"semilla": s.strategy(), "sinfiltro": result["raw"]}
    policies.update({r["arm"]: r["strategy"] for r in result["finals"]})
    s.atomic(s.ROOT / "strategies.json", policies)
    s.atomic(s.ROOT / "completed.json", {"strategies_sha256": s.sha(policies),
             "profile_sha256": s.sha(integrity()), "sources": s.hashes(), "at": s.now()})
    from seed import s6b8_exam
    proxy = SimpleNamespace(**dict(vars(s), integrity=integrity, audit_model=audit_model))
    exam = FunctionType(s6b8_exam.run.__code__, dict(s6b8_exam.run.__globals__, s=proxy))
    exam()
    audit = json.loads((s.ROOT / "exam/audit.json").read_text())
    s.atomic(s.ROOT / "closed.json", {"stage": "CLOSED", "result": "EXAM_CLOSED", "s6_green": audit["green"],
             "checks": audit["checks"], "recovery_profile_sha256": s.sha(profile()), "at": s.now()})
    s.publish("EXAM_CLOSED")
    s.status("CLOSED", s6_green=audit["green"], checks=audit["checks"])


def main(args):
    try:
        if args == ["prepare"]:
            prepare()
        elif len(args) == 2 and args[0] == "audit":
            receipt = json.loads((s.ROOT / (args[1] + "-recovery-process.json")).read_text())
            assert receipt["pid"] != os.getpid(), "recovery auditor must be another process"
            run_phase(args[1], audit=True)
            s.atomic(s.ROOT / (args[1] + "-recovery-audit.json"), {"valid": True,
                      "original_sources_intact": True, "recovery_profile_sha256": s.sha(profile())})
        elif args == ["follow"]:
            follow()
        else:
            raise SystemExit("use prepare, follow, or audit pilot/campaign")
    except Exception as exc:
        s.status("PENDING_RECOVERY_ERROR", error=type(exc).__name__, message=str(exc))
        s.publish("PENDING_RECOVERY_ERROR")
        raise


if __name__ == "__main__":
    from seed import s6b8_recovery
    s6b8_recovery.main(sys.argv[1:])
