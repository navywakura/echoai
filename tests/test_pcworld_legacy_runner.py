"""Adversarial checks of localdev's developer-only PCWorld boundary adapter."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.pcworld import runner as boundary
from harness.localdev import runner as localdev


DETAILS_MARKER = "ECHO_LOCALDEV_DETAILS_V1:"


class LegacyBoundary(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "work" / "echoai"
        self.workspace.mkdir(parents=True)
        self.job = self.root / "job"

    def run_case(self, **spec):
        with redirect_stdout(io.StringIO()):
            return localdev.execute(self.workspace, self.job, spec)

    def assert_unknown(self, result):
        self.assertEqual(result.get("claim_status"), "unknown", result)
        self.assertEqual(result.get("property_status"), "unknown", result)
        self.assertIs(result.get("task_success"), False, result)
        self.assertIs(result.get("scientific_gate"), False, result)
        self.assertEqual(result.get("attestation"), "untrusted", result)
        self.assertEqual(result.get("status_scope"), "developer_test_observations", result)

    def test_forged_passed_report_never_certifies_success(self):
        forged = {"mode": "unittest", "tests_run": 1, "failures": 0, "errors": 0,
                  "skipped": 0, "expected_failures": 0, "unexpected_successes": 0,
                  "cases": [{"test": "fake.test_pass", "outcome": "passed"}],
                  "status": "PASSED", "claim_status": "supported", "property_status": "supported",
                  "task_success": True, "scientific_gate": True, "attestation": "verified",
                  "resources": {"cpu_seconds": -999, "max_process_rss_kib": 10**30}}
        # No unittest is run: the candidate fabricates both the obsolete file
        # and the new diagnostic stream, then exits before worker bookkeeping.
        payload = json.dumps(forged)
        (self.workspace / "test_forgery.py").write_text(
            "import os\nfrom pathlib import Path\n"
            f"Path('/out/details.json').write_text({payload!r})\n"
            f"print({DETAILS_MARKER!r} + {payload!r}, flush=True)\nos._exit(0)\n")
        result = self.run_case(mode="unittest", tests=["test_forgery"])
        self.assertEqual(result["exit_code"], 0, result)
        self.assert_unknown(result)
        self.assertEqual(result["status"], "PASSED")  # Developer self-report only.
        self.assertEqual(result["execution_status"], "EXITED")
        self.assertTrue(result["details"]["task_success"])
        self.assertGreater(result["cpu_seconds"], 0)
        self.assertLess(result["max_process_rss_kib"], 10**20)
        self.assertEqual(json.loads((self.job / "result.json").read_text()), result)

    def test_sibling_and_private_metadata_are_inaccessible(self):
        sibling = self.workspace.parent / "sibling-secret"
        sibling.write_text("secret")
        (self.workspace / ".echoai").mkdir()
        (self.workspace / ".echoai/key").write_text("receipt key")
        (self.workspace / "app.py").write_text("original\n")
        code = f'''from pathlib import Path
assert Path.cwd() == Path('/workspace')
for name in ({str(sibling)!r}, '/work/sibling-secret', '/workspace/../sibling-secret',
             '/workspace/.echoai', '/spec.json', {str(self.job)!r}):
    assert not Path(name).exists(), name
try: Path('app.py').write_text('tampered')
except OSError: pass
else: raise AssertionError('workspace writable')
print('boundary-observed')
'''
        result = self.run_case(mode="command", command=["/usr/bin/python3", "-I", "-c", code])
        self.assertEqual(result["status"], "PASSED", result)
        self.assertIn("boundary-observed", (self.job / "stdout.log").read_text())
        self.assertFalse(result["isolation"]["parent_mounted"])
        self.assertEqual(result["isolation"]["backend"], "bubblewrap+cgroup-v2")
        self.assertTrue(result["isolation"]["workspace_readonly"])
        self.assert_unknown(result)
        self.assertEqual((self.workspace / "app.py").read_text(), "original\n")
        self.assertEqual(sibling.read_text(), "secret")

    def test_every_mode_uses_shared_runner_and_fails_closed(self):
        # Disable the real execution boundary. No legacy subprocess fallback is
        # permitted, even when a perfectly valid candidate would otherwise pass.
        (self.workspace / "test_ok.py").write_text(
            "import unittest\nclass Test(unittest.TestCase):\n def test_ok(self): pass\n")
        modes = [{"mode": "command", "command": ["/usr/bin/python3", "-c", "pass"]},
                 {"mode": "syntax"}, {"mode": "unittest", "tests": ["test_ok"]}]
        for index, spec in enumerate(modes):
            self.job = self.root / f"job-{index}"
            with self.subTest(mode=spec["mode"]), patch.object(
                    boundary, "execute", side_effect=RuntimeError("UNSUPPORTED_ENVIRONMENT: disabled")):
                with self.assertRaisesRegex(RuntimeError, "UNSUPPORTED_ENVIRONMENT"):
                    self.run_case(**spec)
                self.assertFalse((self.job / "result.json").exists())

    def test_diagnostic_flood_shares_stdout_stderr_budget(self):
        (self.workspace / "test_flood.py").write_text(
            "import os\n" + f"print({DETAILS_MARKER!r} + 'x'*1000000, flush=True)\nos._exit(0)\n")
        result = self.run_case(mode="unittest", tests=["test_flood"], output_kb=2)
        self.assertEqual(result["status"], "OUTPUT_LIMIT", result)
        self.assertLessEqual(sum((self.job / name).stat().st_size
                                 for name in ("stdout.log", "stderr.log")), 2048)
        self.assert_unknown(result)

    def test_old_details_file_is_not_a_receipt(self):
        (self.workspace / "test_old.py").write_text(
            "import os\nfrom pathlib import Path\n"
            "Path('/out/details.json').write_text('{\"task_success\": true}')\nos._exit(0)\n")
        result = self.run_case(mode="unittest", tests=["test_old"])
        self.assertEqual(result["status"], "MISSING_RECEIPT", result)
        self.assertIsNone(result["details"])
        self.assert_unknown(result)

    def test_oversized_real_test_diagnostics_are_bounded(self):
        (self.workspace / "test_large.py").write_text(
            "import unittest\nclass Test(unittest.TestCase):\n def test_many_lines(self):\n" +
            "  value = 1\n" * 1500)
        # The unittest console report fits. Only worker-generated executed-line
        # diagnostics exceed this budget; a separate details file would bypass it.
        result = self.run_case(mode="unittest", tests=["test_large"], coverage=True, output_kb=2)
        self.assertEqual(result["status"], "OUTPUT_LIMIT", result)
        self.assertLessEqual(sum((self.job / name).stat().st_size
                                 for name in ("stdout.log", "stderr.log")), 2048)
        self.assert_unknown(result)

    def test_validation_summary_keeps_developer_scope(self):
        with redirect_stdout(io.StringIO()):
            result = localdev.validate(self.workspace, self.job,
                [{"id": "ok", "mode": "command", "command": ["/usr/bin/true"]}])
        self.assertEqual(result["status"], "PASSED", result)
        self.assert_unknown(result)
        self.assert_unknown(result["checks"][0])

    def test_stdin_is_separate_from_the_worker_specification(self):
        result = self.run_case(mode="command", stdin="hello\n" * 20000,
            command=["/usr/bin/python3", "-I", "-c", "import sys; print(len(sys.stdin.buffer.read()))"])
        self.assertEqual(result["status"], "PASSED", result)
        self.assertIn("120000\n", (self.job / "stdout.log").read_text())

    def test_snapshot_rejects_sibling_symlinks_before_execution(self):
        sentinel = self.root / "secret"
        sentinel.write_text("private")
        (self.workspace / "escape.py").symlink_to(sentinel)
        with self.assertRaises(ValueError):
            self.run_case(mode="command", command=["/usr/bin/cat", "escape.py"])
        self.assertFalse((self.job / "result.json").exists())

    def test_malformed_report_cannot_crash_parent_feedback(self):
        forged = {"mode": "unittest", "tests_run": 1, "failures": 0, "errors": 0,
                  "skipped": 0, "expected_failures": 0, "unexpected_successes": 0,
                  "cases": [None]}
        payload = json.dumps(forged)
        (self.workspace / "test_bad_shape.py").write_text(
            "import os\nfrom pathlib import Path\n"
            f"Path('/out/details.json').write_text({payload!r})\n"
            f"print({DETAILS_MARKER!r} + {payload!r}, flush=True)\nos._exit(0)\n")
        result = self.run_case(mode="unittest", tests=["test_bad_shape"])
        self.assertEqual(result["status"], "INVALID_RECEIPT", result)
        self.assertIsNone(result["details"])
        self.assert_unknown(result)

    def test_empty_syntax_candidate_does_not_count_trusted_worker(self):
        result = self.run_case(mode="syntax")
        self.assertEqual(result["status"], "FAILED", result)
        self.assertEqual(result["details"]["files"], 0)
        self.assert_unknown(result)

    def test_cpu_limit_is_enforced_by_shared_runner(self):
        result = self.run_case(mode="command", command=["/usr/bin/python3", "-I", "-c", "while True: pass"],
                               timeout_s=5, cpu_ms=200)
        self.assertEqual(result["status"], "CPU_LIMIT", result)
        self.assertGreaterEqual(result["resources"]["cpu_us"], 200000)
        self.assertTrue(result["isolation"]["job_empty"])
        self.assert_unknown(result)

    def test_hostile_diagnostic_numbers_cannot_crash_parent(self):
        code = "print('source.c:' + '9'*10000 + ': error: invented'); print('source.c:3: error: reported')"
        result = self.run_case(mode="command", command=["/usr/bin/python3", "-I", "-c", code])
        self.assertEqual(result["exit_code"], 0, result)
        self.assertTrue(any(item.get("line") == 3 for item in result["diagnostics"]))
        self.assert_unknown(result)

    def test_namespaced_tests_run_without_modifying_original_workspace(self):
        (self.workspace / "__init__.py").write_text("from .example import value\n")
        (self.workspace / "example.py").write_text("value = 42\n")
        (self.workspace / "test_example.py").write_text(
            "import unittest, echoai\nclass Test(unittest.TestCase):\n"
            " def test_value(self): self.assertEqual(echoai.value, 42)\n")
        before = {p.name: p.read_bytes() for p in self.workspace.iterdir()}
        result = self.run_case(mode="unittest", tests=["echoai.test_example"], coverage=True)
        self.assertEqual(result["status"], "PASSED", result)
        self.assertEqual(result["details"]["tests_run"], 1)
        self.assertIn("untrusted", result["details"]["counts_scope"])
        self.assertEqual({p.name: p.read_bytes() for p in self.workspace.iterdir()}, before)
        self.assert_unknown(result)

    def test_reserved_worker_path_cannot_replace_trusted_worker(self):
        reserved = self.workspace / "__localdev_worker__"
        reserved.mkdir()
        (reserved / "worker.py").write_text("raise SystemExit(0)\n")
        with self.assertRaisesRegex(ValueError, "reserved"):
            self.run_case(mode="syntax")
        self.assertEqual((reserved / "worker.py").read_text(), "raise SystemExit(0)\n")
        self.assertFalse((self.job / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
