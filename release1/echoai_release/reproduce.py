"""Reproduce sealed evidence with the installed (compiled) agent.

  integrate  re-run the INTEGRATE-1 exam campaign (16 seeds); the new report must
             carry the sealed digest e1492e22… and every artifact must match byte
             for byte. This is the strongest check: sources are verified through
             the build manifest, behaviour through the artifacts.
  nexus0     ECHO-1 core KPI suite (echoai.tests.test_nexus0) on the compiled core.
  tests      every compiled test module; reports pass/fail per module (informative).
  tamper     a copy of the install with one byte appended to the core binary must
             be refused an identity, and ECHO must fail closed instead of answering.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

INTEGRATE_DIGEST = "e1492e22131fc755f3f11bf47c3747edb42640c004fe3be479cd71c2c8952a05"


def _file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integrate(out):
    import echoai  # noqa: F401  (activates identity)
    from echoai_release import identity
    from echoai.echo4 import integrate_exam as X
    from echoai.echo4.continuity_final_audit import read_json
    sealed_dir = X.ROOT / "lab/echo4/integrate1-d-v1"
    sealed = read_json(sealed_dir / "report.json")
    directory = Path(out) / "integrate1-d-v1"
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = X.campaign(directory, X.EXAM)
    same_artifacts = {name: _file_sha(directory / name) == digest
                      for name, digest in sealed["artifacts"].items()}
    return {"check": "integrate", "identity": identity.status(),
            "reproduced_digest": report["reproduction_sha256"], "sealed_digest": sealed["reproduction_sha256"],
            "expected_digest": INTEGRATE_DIGEST,
            "digest_identical": report["reproduction_sha256"] == sealed["reproduction_sha256"] == INTEGRATE_DIGEST,
            "artifacts_identical": sum(same_artifacts.values()), "artifacts": len(same_artifacts),
            "differing": sorted(n for n, ok in same_artifacts.items() if not ok),
            "exam_passed": report["passed"], "seconds": int(time.monotonic() - started),
            "passed": bool(report["reproduction_sha256"] == INTEGRATE_DIGEST and all(same_artifacts.values()))}


def _category(tb):
    """Why a test cannot pass on a compiled install (anything else is behavioural)."""
    tail = "\n".join(tb.strip().splitlines()[-4:])
    missing = "No such file" in tail or "FileNotFoundError" in tail or "missing dependency:" in tail
    if (missing and ".py" in tail) or "could not get source code" in tail \
            or "test_the_hot_path_imports_no_model" in tb:
        return "reads_source"
    if missing and any(d in tail for d in ("/lab/", "/docs/", "/viz_tasks/", "legacy/")):
        return "reads_lab_or_docs"
    if "ModuleNotFoundError" in tail:
        return "external_dependency"
    return "behavioural"


def _source_reading(tb):
    return _category(tb) != "behavioural"


def _run_modules(names):
    rows = []
    for name in names:
        stream = io.StringIO()
        try:
            suite = unittest.defaultTestLoader.loadTestsFromName(name)
            result = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
            problems = result.errors + result.failures
            source = sum(1 for _, tb in problems if _source_reading(tb))
            cats = {}
            for _, tb in problems:
                cats[_category(tb)] = cats.get(_category(tb), 0) + 1
            rows.append({"module": name, "tests": result.testsRun, "failures": len(result.failures),
                         "source_or_repo_reading": source, "behavioural_problems": len(problems) - source,
                         "categories": cats,
                         "errors": len(result.errors), "skipped": len(result.skipped),
                         "passed": result.wasSuccessful(),
                         "first_problem": (result.errors + result.failures)[0][1][-400:]
                         if (result.errors or result.failures) else ""})
        except Exception as exc:  # a module that cannot even load is reported, not hidden
            rows.append({"module": name, "tests": 0, "failures": 0, "errors": 1, "skipped": 0,
                         "passed": False, "first_problem": repr(exc)[:400]})
    return rows


def nexus0(out):
    import echoai  # noqa: F401
    rows = _run_modules(["echoai.tests.test_nexus0"])
    return {"check": "nexus0", "rows": rows, "passed": all(r["passed"] and r["tests"] > 0 for r in rows)}


def tests(out):
    import echoai  # noqa: F401
    from echoai_release import identity
    names = sorted(m for m in identity.manifest()["test_modules"])
    rows = _run_modules(names)
    return {"check": "tests", "modules": len(rows), "tests": sum(r["tests"] for r in rows),
            "passed_modules": sum(r["passed"] for r in rows), "rows": rows,
            "passed": all(r["passed"] for r in rows)}


def tamper(out):
    from echoai_release import identity
    import echoai  # noqa: F401
    site = identity.site()
    copy = Path(tempfile.mkdtemp(prefix="echoai-tamper-"))
    try:
        for rel in identity.manifest()["binaries"]:
            shutil.copy2(site / rel, copy / rel)
        shutil.copytree(site / "echoai_release", copy / "echoai_release")
        if (site / "echoai").is_dir():
            shutil.copytree(site / "echoai", copy / "echoai")
        core = copy / identity.manifest()["core_binary"]
        with core.open("ab") as handle:
            handle.write(b"\0")
        probe = ("import echoai_release._hook, echoai, json\n"
                 "from echoai_release import identity\n"
                 "st = identity.status()\n"
                 "try:\n"
                 "    from echoai.echo4 import situate as S\n"
                 "    S.sense(); answered = True\n"
                 "except FileNotFoundError:\n"
                 "    answered = False\n"
                 "print(json.dumps({'status': st, 'answered_identity': answered}))\n")
        env = {**os.environ, "PYTHONPATH": str(copy)}
        run = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, env=env,
                             cwd=str(copy), timeout=300)
        data = json.loads(run.stdout.strip().splitlines()[-1]) if run.returncode == 0 else {}
        st = data.get("status", {})
        return {"check": "tamper", "child_rc": run.returncode, "stderr": run.stderr[-300:],
                "binaries_ok": st.get("binaries_ok"), "mismatch": st.get("mismatch"),
                "answered_identity": data.get("answered_identity"),
                "passed": bool(run.returncode == 0 and st.get("binaries_ok") is False
                               and data.get("answered_identity") is False)}
    finally:
        shutil.rmtree(copy, ignore_errors=True)


CHECKS = {"integrate": integrate, "nexus0": nexus0, "tests": tests, "tamper": tamper}


def main(what, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    result = CHECKS[what](out)
    result["python"] = sys.version.split()[0]
    result["executable"] = sys.executable
    (out / (what + "-result.json")).write_text(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=1, ensure_ascii=False))
    return 0 if result["passed"] else 1
