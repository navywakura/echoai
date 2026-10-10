"""Validate the exact R1 ZIP with system Python and no native/network operations."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not sys.flags.dont_write_bytecode or not sys.flags.isolated:
        raise RuntimeError("run with system python3 -I -B")
    package = json.loads((HERE / "package.json").read_text())
    bundle = HERE / "dataset/echo-b24-r1-private.zip"
    if digest(bundle) != package["sha256"]:
        raise RuntimeError("R1 package changed")
    checks = HERE / "checks"
    checks.mkdir(exist_ok=True)
    project = Path(tempfile.mkdtemp(prefix="isolated-r1-", dir=checks))
    with zipfile.ZipFile(bundle) as z:
        for name in z.namelist():
            dest = project / name
            if not dest.resolve().is_relative_to(project.resolve()):
                raise RuntimeError("unsafe ZIP member")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(name))
    tmp = checks / "tmp"
    tmp.mkdir(exist_ok=True)
    tempfile.tempdir = str(tmp)
    os.environ["TMPDIR"] = str(tmp)
    os.environ["B24_R1_TEST_PROJECT"] = str(project)
    os.environ.pop("B23_GBNF_VALIDATOR", None)
    os.environ.pop("ECHO_B24_ROOT", None)
    os.environ.pop("ECHO_B24_INPUT", None)
    sys.path.insert(0, str(project))
    os.chdir(project)

    def offline_only(event, args):
        if event.startswith(("subprocess.", "os.system", "socket.")):
            raise AssertionError("offline ZIP verification forbids " + event)
    sys.addaudithook(offline_only)

    test_path = REPO / "tests/test_s6b24_r1_package.py"
    spec = importlib.util.spec_from_file_location("r1_package_checks", test_path)
    checks_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks_module)
    loader = unittest.defaultTestLoader
    focused = loader.loadTestsFromModule(checks_module)
    inherited = loader.loadTestsFromNames([
        "tests.test_s6b23r4", "tests.test_s6b24_search", "tests.test_s6b24_model",
        "tests.test_s6b24_runner", "tests.test_s6b24_review"])
    results = {}
    for name, suite in (("r1-package", focused), ("inherited-b24", inherited)):
        print("Running " + name + " from " + str(project), flush=True)
        output = io.StringIO()
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
        log = checks / (name + ".log")
        log.write_text(output.getvalue())
        results[name] = dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                             skipped=[dict(test=str(test), reason=reason) for test, reason in result.skipped],
                             log=str(log.relative_to(HERE)), log_sha256=digest(log))
        print(output.getvalue(), flush=True)
    original = json.loads((HERE / "original-source-hashes.json").read_text())
    changed = [name for name, expected in original.items() if digest(REPO / name) != expected]
    receipt = dict(package_sha256=package["sha256"], recovery_sha256=package["recovery_sha256"],
        validation_command="/usr/bin/python3 -I -B lab/kaggle/s6b24-r1-20261009/validate.py",
        system_python=sys.version, isolated_project=str(project),
        suites=results, changed_original_sources=changed, source_count=len(original),
        tests_source_sha256=digest(test_path), validator_sha256=digest(Path(__file__).resolve()),
        new_model_calls=0, new_games=0, cloud_operations=0,
        native_validation="not run; inherited native grammar checks explicitly skipped",
        ready_for_main_review=not changed and all(not x["failures"] and not x["errors"] for x in results.values()))
    (HERE / "local-validation.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    if not receipt["ready_for_main_review"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
