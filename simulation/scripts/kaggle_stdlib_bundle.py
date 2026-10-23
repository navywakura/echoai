"""Build a small private CPU notebook from an explicit reviewed hash manifest.

Does not authenticate or submit. The manifest must name the frozen files and
explicit unittest selections. Original test source bytes are never rewritten.
Example manifest: {"files": {"simulation/src/echo5/sitl_recovery.py": "<sha256>",
"simulation/tests/test_sitl_recovery.py": "<sha256>"},
"tests": ["test_sitl_recovery.RecoveryTests"]}.
"""

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "simulation/artifacts/kaggle-sitl-20261011-r1"
ALLOWED = {
    "simulation/src/echo5/sitl_recovery.py",
    "simulation/tests/test_sitl_recovery.py",
    "nexus0/drone3/assets/runner.py",
    "simulation/src/echo5/sitl_parameters.py",
    "simulation/tests/test_sitl_parameters.py",
}

CHILD = r'''
import hashlib, importlib, json, platform, sys, time, unittest
from pathlib import Path
root = Path(__file__).resolve().parent
project = root / "stdlib-project"
manifest = json.loads((root / "source-manifest.json").read_text())
assert platform.python_version() == "3.12.13", "exact project Python pin required"
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
sys.path.insert(0, str(project / "simulation/src"))
sys.path.insert(0, str(project / "simulation/tests"))
def hashes():
    return {name: hashlib.sha256((project / name).read_bytes()).hexdigest()
            for name in manifest["files"]}
assert hashes() == manifest["files"], "frozen source mismatch before tests"
def ids(suite):
    output = []
    for item in suite:
        output.extend(ids(item) if isinstance(item, unittest.TestSuite) else [item.id()])
    return output
loader = unittest.TestLoader()
available = []
for name in sorted({name.split(".")[0] for name in manifest["tests"]}):
    available.extend(ids(loader.loadTestsFromModule(importlib.import_module(name))))
suite = loader.loadTestsFromNames(manifest["tests"])
selected = ids(suite)
if not selected or loader.errors:
    raise RuntimeError("test selection did not load cleanly: " + repr(loader.errors))
started = time.monotonic()
result = unittest.TextTestRunner(verbosity=2).run(suite)
after = hashes()
unchanged = after == manifest["files"]
passed = result.wasSuccessful() and result.testsRun > 0 and unchanged and not result.skipped
receipt = dict(
    schema="echo5.kaggle.stdlib-regression.v1",
    scope="explicitly selected stdlib unit tests; not Gazebo/PX4 or physical confirmation",
    python=platform.python_version(), full_python=sys.version,
    interpreter=sys.executable, isolated=bool(sys.flags.isolated),
    no_site=bool(sys.flags.no_site), dont_write_bytecode=sys.dont_write_bytecode,
    simulator_tested=False, gpu_requested=False, passed=passed,
    sources_before=manifest["files"], sources_after=after, sources_unchanged=unchanged,
    requested_tests=manifest["tests"], selected_test_ids=selected,
    available_test_ids=available, unselected_test_ids=sorted(set(available)-set(selected)),
    tests_run=result.testsRun, failures=[(test.id(), text) for test,text in result.failures],
    errors=[(test.id(), text) for test,text in result.errors],
    skipped=[(test.id(), reason) for test,reason in result.skipped],
    expected_failures=[test.id() for test,_ in result.expectedFailures],
    unexpected_successes=[test.id() for test in result.unexpectedSuccesses],
    elapsed_seconds=round(time.monotonic()-started, 6),
)
with (root / "stdlib-tests.json").open("x") as stream:
    json.dump(receipt, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps(receipt, sort_keys=True), flush=True)
raise SystemExit(0 if passed else 1)
'''

REMOTE = r'''
import base64, hashlib, importlib.util, json, os, signal, subprocess, sys, time
from pathlib import Path
root = Path("/kaggle/working")
if not root.is_dir():
    raise SystemExit("this generated notebook is for Kaggle only")
files = __FILES__
manifest = __MANIFEST__
receipt = dict(schema="echo5.kaggle.stdlib-execution.v1",
               started_unix=time.time(), simulator_tested=False, gpu_requested=False,
               session_timeout_seconds=300, python_setup_budget_seconds=180,
               unittest_budget_seconds=75, status="preparing")
def save():
    temp = root / "execution.json.partial"
    temp.write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n")
    temp.replace(root / "execution.json")
def timeout_handler(_signal, _frame):
    raise TimeoutError("private regression notebook hard wall timeout")
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(270)
process = None
try:
    project = root / "stdlib-project"
    project.mkdir(exist_ok=False)
    for name, encoded in files.items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(encoded, validate=True)
        assert hashlib.sha256(data).hexdigest() == manifest["files"][name]
        path.write_bytes(data)
    (root / "source-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
    helper = root / "pinned_python.py"
    helper.write_bytes(base64.b64decode(__PYTHON_HELPER__, validate=True))
    spec = importlib.util.spec_from_file_location("echo5_kaggle_python_runtime", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executable, identity = module.ensure_python(root / "portable-runtime")
    receipt["python_runtime"] = identity
    child = root / "execute_tests.py"
    child.write_text(__CHILD__)
    temporary = root / "test-tmp"
    temporary.mkdir()
    command = [executable, "-I", "-S", "-B", str(child)]
    receipt.update(status="running_selected_tests", argv=command)
    save()
    with (root / "unittest.log").open("x") as log:
        process = subprocess.Popen(command, cwd=project, env=dict(os.environ, TMPDIR=str(temporary)),
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        process.wait(timeout=75)
    receipt.update(returncode=process.returncode,
                   status="passed" if process.returncode == 0 else "tests_failed")
except Exception as exc:
    receipt.update(status="execution_failed", error=type(exc).__name__+": "+str(exc))
finally:
    signal.alarm(0)
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2)
        receipt["returncode"] = process.returncode
    receipt["finished_unix"] = time.time()
    save()
    print(json.dumps(receipt, sort_keys=True), flush=True)
raise SystemExit(0 if receipt["status"] == "passed" else 1)
'''


def build(manifest_path, output_name):
    if not re.fullmatch(r"stdlib-r[1-9][0-9]*", output_name):
        raise ValueError("output name must be stdlib-rN under the assigned artifact directory")
    manifest = json.loads(Path(manifest_path).read_text())
    if set(manifest) != {"files", "tests"}:
        raise ValueError("manifest requires exactly files (hash mapping) and tests (selection)")
    expected = manifest["files"]
    if not isinstance(expected, dict) or not expected or not set(expected) <= ALLOWED:
        raise ValueError("unreviewed source path in manifest")
    tests = manifest["tests"]
    if (not isinstance(tests, list) or not tests or len(set(tests)) != len(tests)
            or any(not re.fullmatch(r"test_sitl_(?:recovery|parameters)(?:\.[A-Za-z_][A-Za-z0-9_]*){0,2}", name)
                   for name in tests)):
        raise ValueError("explicit recovery/parameter unittest names required")
    payload = {}
    total = 0
    for name, wanted in expected.items():
        if not re.fullmatch(r"[a-f0-9]{64}", wanted):
            raise ValueError("a SHA256 freeze is required for every source")
        path = ROOT / name
        if path.is_symlink() or path.resolve() != path:
            raise ValueError("source symlinks are not accepted")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != wanted:
            raise ValueError("source changed after freeze: " + name)
        compile(data, name, "exec")
        total += len(data)
        if total > 1024 * 1024:
            raise ValueError("source payload must stay below 1 MiB")
        payload[name] = base64.b64encode(data).decode()
    helper = Path(__file__).with_name("kaggle_pinned_python.py").read_bytes()
    substitutions = {
        "__FILES__": repr(payload), "__MANIFEST__": repr(manifest),
        "__PYTHON_HELPER__": repr(base64.b64encode(helper).decode()),
        "__CHILD__": repr(CHILD),
    }
    remote = REMOTE
    for key, value in substitutions.items():
        assert remote.count(key) == 1
        remote = remote.replace(key, value)
    compile(remote, "run.py", "exec")
    output = ARTIFACTS / output_name
    output.mkdir(exist_ok=False)
    notebook = output / "notebook"
    notebook.mkdir()
    slug = "echo5-sitl-" + output_name + "-20261011"
    metadata = dict(
        id="navywakura/" + slug, title=slug, code_file="run.py",
        language="python", kernel_type="script", is_private=True,
        enable_gpu=False, enable_tpu=False, enable_internet=True,
        dataset_sources=[], kernel_sources=[], competition_sources=[], model_sources=[])
    (notebook / "run.py").write_text(remote)
    (notebook / "kernel-metadata.json").write_text(json.dumps(metadata, sort_keys=True, indent=2)+"\n")
    (output / "source-manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2)+"\n")
    receipt = dict(
        source_bytes=total, source_count=len(payload), session_timeout_seconds=300,
        python_pin="3.12.13", private=True, gpu=False,
        tests=tests, run_sha256=hashlib.sha256(remote.encode()).hexdigest(),
        runtime_helper_sha256=hashlib.sha256(helper).hexdigest())
    (output / "bundle.json").write_text(json.dumps(receipt, sort_keys=True, indent=2)+"\n")
    print(json.dumps(dict(notebook=str(notebook), ref=metadata["id"], receipt=receipt), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    build(args.manifest, args.out)
