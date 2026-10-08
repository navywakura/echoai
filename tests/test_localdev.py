"""Engineering contracts; these tests neither open sealed exams nor call a model."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer

from harness.localdev.common import digest, safe_path, snapshot
from harness.localdev.engine import allowed_paths, apply_proposal, bounded_proposal, demo, http_proposer, repair
from harness.localdev.inventory import inspect_tree
from harness.localdev.runner import diagnostics, execute, validate


class LocalDevelopment(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()

    def put(self, name, content):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def run_case(self, spec, *, workspace=None):
        workspace = workspace or self.root / "work/echoai"
        if not workspace.exists():
            snapshot(self.source, workspace)
        with redirect_stdout(io.StringIO()):
            return execute(workspace, self.root / "job", spec)

    def command(self, code, **limits):
        return self.run_case({"mode": "command", "command": ["/usr/bin/python3", "-c", code], **limits})

    def test_ast_inventory_never_imports_and_resolves_cycles(self):
        self.put("a.py", "import b\nraise RuntimeError('must not import')\ndef todo():\n    pass\n")
        self.put("b.py", "import a\n")
        self.put("bad.py", "def oops(:\n")
        self.put("ui.jsx", "const A = () => <main/>;")
        result = inspect_tree(self.source, self.root/"map")
        data = json.loads((self.root/"map/inventory.json").read_text())
        self.assertEqual(result["python_files"], 3)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["cycles"], [["a", "b"]])
        self.assertEqual(data["modules"][0]["stub_candidates"], [3])
        self.assertEqual(data["other_code"], ["ui.jsx"])

    def test_snapshot_excludes_artifacts_secrets_models_and_links(self):
        self.put("app.py", "x=1")
        for name in ("lab/exam.json", ".env", "credentials.json", "model.gguf", "echo-discord/no.py"):
            self.put(name, "secret")
        (self.source/"alias.py").symlink_to(self.source/"app.py")
        receipt = snapshot(self.source, self.root/"copy")
        self.assertEqual(list(receipt), ["app.py"])
        self.assertEqual(list((self.root/"copy").iterdir()), [self.root/"copy/app.py"])

    def test_path_escape_and_symlink_are_rejected(self):
        (self.source/"escape").symlink_to(self.root, target_is_directory=True)
        for name in ("../x.py", "/tmp/x.py", "lab/x.py", ".secret", "escape/x.py"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(self.source, name)

    def test_frozen_source_tests_and_harness_cannot_be_repair_targets(self):
        self.put("lab/seed/frozen/profile.json", json.dumps({"sources": {"seed/critical.py": "hash"}}))
        for name in ("seed/critical.py", "tests/test_a.py", "harness/localdev/worker.py", "docs/contract.md"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                allowed_paths(self.source, [name])
        self.assertEqual(allowed_paths(self.source, ["new.py"]), ["new.py"])

    def test_invalid_batch_is_atomic_and_stale_edits_are_rejected(self):
        path = self.put("app.py", "x=1\n")
        good = {"path": "app.py", "expected_sha256": digest(path.read_bytes()), "content": "x=2\n"}
        for bad in ({**good, "path": "test_a.py"}, {**good, "expected_sha256": "stale"}, good):
            with self.assertRaises(ValueError):
                apply_proposal(self.source, ["app.py"], {"edits": [good, bad]})
            self.assertEqual(path.read_text(), "x=1\n")

    def test_noop_and_oversized_patch_are_rejected(self):
        path = self.put("app.py", "x=1\n")
        for content in (path.read_text(), "x"*65537):
            with self.assertRaises(ValueError):
                apply_proposal(self.source, ["app.py"], {"edits": [{"path": "app.py",
                    "expected_sha256": digest(path.read_bytes()), "content": content}]})

    def test_sandbox_blocks_host_credentials_network_and_source_writes(self):
        self.put("app.py", "x=1\n")
        secret = self.root/"private-key"
        secret.write_text("not for workers")
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen()
            port = server.getsockname()[1]
            code = f'''import os, socket
from pathlib import Path
assert "TEST_PRIVATE_TOKEN" not in os.environ
assert not Path({str(secret)!r}).exists()
assert not Path("/home/roger").exists()
assert not Path("/dev/dri").exists()
try: Path("app.py").write_text("damaged")
except OSError: pass
else: raise AssertionError("source writable")
s=socket.socket(); s.settimeout(.2)
try: s.connect(("127.0.0.1", {port}))
except OSError: pass
else: raise AssertionError("host network accessible")
Path("/out/ok").write_text("isolated")
'''
            with patch.dict(os.environ, {"TEST_PRIVATE_TOKEN": "secret"}):
                result = self.command(code)
        self.assertEqual(result["status"], "PASSED", (self.root/"job/stderr.log").read_text())
        self.assertEqual((self.root/"work/echoai/app.py").read_text(), "x=1\n")
        self.assertEqual(secret.read_text(), "not for workers")

    def test_timeout_kills_descendants(self):
        result = self.command('''import subprocess, time
subprocess.Popen(["/usr/bin/python3", "-c", "import time; from pathlib import Path; time.sleep(1); Path('/out/escaped').write_text('bad')"])
time.sleep(30)
''', timeout_s=.2)
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertLess(result["wall_seconds"], 3)
        time.sleep(1.1)
        self.assertFalse((self.root/"job/out/escaped").exists())

    def test_output_is_bounded(self):
        result = self.command("print('x'*1000000)", output_kb=2)
        self.assertEqual(result["status"], "OUTPUT_LIMIT")
        self.assertLessEqual((self.root/"job/stdout.log").stat().st_size +
                             (self.root/"job/stderr.log").stat().st_size, 2048)

    def test_memory_limit_yields_real_failure(self):
        result = self.command("huge=bytearray(512*1024*1024)", memory_mb=256)
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("MemoryError", (self.root/"job/stderr.log").read_text())
        self.assertTrue(result["max_process_rss_kib"])

    def test_memory_metric_measures_worker_allocation(self):
        result = self.command("import time; data=bytearray(80*1024*1024); time.sleep(.25)", memory_mb=1024)
        self.assertEqual(result["status"], "PASSED")
        self.assertGreater(result["max_process_rss_kib"], 80*1024)
        self.assertGreater(result["peak_tree_rss_kib_sampled"], 80*1024)
        self.assertGreater(result["cpu_seconds"], 0)

    def test_aggregate_disk_limit_stops_worker(self):
        result = self.command('''from pathlib import Path
import time
for i in range(5): Path('/out/'+str(i)).write_bytes(b'x'*(8*1048576))
time.sleep(10)
''')
        self.assertEqual(result["status"], "DISK_LIMIT")

    def test_structured_failure_and_executed_lines(self):
        self.put("test_case.py", "import unittest\nclass A(unittest.TestCase):\n def test_bad(self): self.assertEqual(1, 2)\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_case"], "coverage": True})
        self.assertEqual(result["status"], "FAILED")
        error = result["details"]["cases"][0]["error"]
        self.assertEqual(error["type"], "AssertionError")
        self.assertTrue(any(f["file"].endswith("test_case.py") and f["line"] == 3 for f in error["frames"]))
        self.assertIn(3, result["details"]["executed_lines"]["test_case.py"])

    def test_empty_suite_cannot_pass(self):
        self.put("test_empty.py", "x=1\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_empty"]})
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["details"]["tests_run"], 0)

    def test_skipped_suite_cannot_pass(self):
        self.put("test_case.py", "import unittest\nclass A(unittest.TestCase):\n @unittest.skip('no hardware')\n def test_skip(self): pass\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_case"]})
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["details"]["skipped"], 1)

    def test_expected_failure_cannot_pass(self):
        self.put("test_case.py", "import unittest\nclass A(unittest.TestCase):\n @unittest.expectedFailure\n def test_skip(self): self.fail('known bug')\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_case"]})
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["details"]["expected_failures"], 1)

    def test_exit_zero_without_receipt_cannot_pass(self):
        self.put("test_case.py", "import os\nos._exit(0)\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_case"]})
        self.assertEqual(result["status"], "MISSING_RECEIPT")

    def test_malformed_receipt_cannot_pass(self):
        self.put("test_case.py", "from pathlib import Path\nimport os\nPath('/out/details.json').write_text('{')\nos._exit(0)\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_case"]})
        self.assertEqual(result["status"], "INVALID_RECEIPT")

    def test_zero_exit_with_empty_json_cannot_pass(self):
        self.put("test_case.py", "from pathlib import Path\nimport os\nPath('/out/details.json').write_text('{}')\nos._exit(0)\n")
        result = self.run_case({"mode": "unittest", "tests": ["test_case"]})
        self.assertEqual(result["status"], "INVALID_RECEIPT")

    def test_syntax_diagnostic(self):
        self.put("bad.py", "def oops(:\n")
        result = self.run_case({"mode": "syntax"})
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["details"]["errors"][0]["line"], 1)

    def test_compiler_diagnostics_and_empty_profile(self):
        result = diagnostics("src.c:5:9: error: invalid expression\n")
        self.assertEqual(result[0]["line"], 5)
        self.assertEqual(result[0]["column"], 9)
        self.assertEqual(validate(self.source, self.root/"empty", [])["status"], "FAILED")

    def test_actual_compiler_error_is_captured(self):
        self.put("broken.c", "int main(void) { return missing_name; }\n")
        result = self.run_case({"mode": "command", "command": ["/usr/bin/gcc", "-fsyntax-only", "broken.c"]})
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any(d.get("kind") == "compiler" and d.get("line") == 1 for d in result["diagnostics"]))

    def test_actual_closed_loop_repairs_without_touching_original(self):
        with redirect_stdout(io.StringIO()):
            result = demo(self.root/"demo")
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["calls_reserved"], 2)
        self.assertEqual([a["status"] for a in result["attempts"]], ["FAILED", "PASSED"])
        self.assertTrue(result["source_unchanged"])
        self.assertFalse(result["scientific_gate"])
        self.assertIn("min(lower, value)", (self.root/"demo/fixture/clamp.py").read_text())
        self.assertIn("min(upper, value)", (self.root/"demo/loop/candidate.patch").read_text())

    def test_invalid_proposals_exhaust_budget_and_preserve_red(self):
        self.put("app.py", "value=0\n")
        self.put("test_case.py", "import unittest\nclass A(unittest.TestCase):\n def test_bad(self): self.fail('repair required')\n")
        checks = [{"id": "test", "mode": "unittest", "tests": ["test_case"]}]
        with redirect_stdout(io.StringIO()):
            result = repair(self.source, self.root/"loop", ["app.py"], checks,
                            lambda _: {"edits": []}, max_attempts=2)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["calls_reserved"], 2)
        self.assertEqual(len(result["attempts"]), 2)
        self.assertFalse(result["patch_validated"])

    def test_loop_deadline_includes_test_execution(self):
        self.put("app.py", "value=0\n")
        self.put("test_case.py", "import unittest,time\nclass A(unittest.TestCase):\n def test_sleep(self): time.sleep(10)\n")
        with redirect_stdout(io.StringIO()):
            result = repair(self.source, self.root/"loop", ["app.py"],
                            [{"id": "test", "mode": "unittest", "tests": ["test_case"]}],
                            lambda _: self.fail("must not request proposal"), max_seconds=1)
        self.assertEqual(result["status"], "BUDGET_EXHAUSTED")
        self.assertEqual(result["calls_reserved"], 0)
        self.assertLess(result["wall_seconds"], 3)

    def test_real_http_adapter_with_declared_mock_server(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                body = json.dumps({"choices": [{"message": {"content": '{"edits": []}'}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args): pass
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            propose = http_proposer(f"http://127.0.0.1:{server.server_port}/v1/chat/completions", "mock-fixture")
            self.assertEqual(propose({"files": {}, "failures": []})["edits"], [])
            self.assertEqual(requests[0]["model"], "mock-fixture")
            self.assertEqual(requests[0]["max_tokens"], 2048)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_provider_rejects_remote_http_or_embedded_credentials(self):
        for endpoint in ("http://example.org/api", "https://key:secret@example.org/api", "https://example.org/?key=secret"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                http_proposer(endpoint, "model")

    def test_proposal_wall_limit_interrupts_stalled_provider(self):
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            bounded_proposal(lambda _: time.sleep(5), {}, .05)
        self.assertLess(time.monotonic()-start, 1)


if __name__ == "__main__":
    unittest.main()
