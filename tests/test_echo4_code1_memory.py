"""E4-CODE-1 A · verified memory and MCP protocol (unit tests, development)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from echoai.echo4.code_memory import CodeMemory, SUPPORTED, CONTRADICTED, UNKNOWN
from echoai.echo4.code_mcp import Server, TOOLS


def project(broken=True):
    root = Path(tempfile.mkdtemp(prefix="echoai-code1-unit-"))
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / ".echoai").mkdir()
    (root / "src/__init__.py").write_text("")
    (root / "tests/__init__.py").write_text("")
    op = "-" if broken else "+"
    (root / "src/calc.py").write_text("def add(a, b):\n    return a %s b\n\n\nclass Box:\n    def open(self):\n        return 1\n" % op)
    (root / "tests/test_calc.py").write_text(
        "import unittest\nfrom src.calc import add\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 2), 4)\n")
    (root / ".echoai/checks.json").write_text(json.dumps({"unit": [sys.executable, "-B", "-m", "unittest", "-q"]}))
    return root


class Memory(unittest.TestCase):
    def test_exit_claim_follows_observation_without_certifying_task(self):
        root = project(broken=True)
        m = CodeMemory(root)
        claim = {"type": "check_exit_zero", "check": "unit"}
        self.assertEqual(m.verify_claim(claim)["status"], UNKNOWN)          # never ran
        self.assertFalse(m.run_check("unit")["passed"])
        self.assertEqual(m.verify_claim(claim)["status"], CONTRADICTED)
        (root / "src/calc.py").write_text((root / "src/calc.py").read_text().replace("a - b", "a + b"))
        self.assertEqual(m.verify_claim(claim)["status"], UNKNOWN)          # files changed since
        self.assertTrue(m.run_check("unit")["passed"])
        self.assertEqual(m.verify_claim(claim)["status"], SUPPORTED)
        self.assertEqual(m.verify_claim({"type":"tests_pass","check":"unit"})["status"], UNKNOWN)

    def test_undeclared_check_cannot_run(self):
        m = CodeMemory(project())
        self.assertFalse(m.run_check("anything")["ok"])

    def test_symbols_and_contents(self):
        m = CodeMemory(project())
        v = lambda c: m.verify_claim(c)["status"]                          # noqa: E731
        self.assertEqual(v({"type": "symbol_defined", "path": "src/calc.py", "symbol": "Box.open"}), SUPPORTED)
        self.assertEqual(v({"type": "symbol_defined", "path": "src/calc.py", "symbol": "multiply"}), CONTRADICTED)
        self.assertEqual(v({"type": "file_contains", "path": "src/calc.py", "text": "class Box"}), SUPPORTED)
        self.assertEqual(v({"type": "file_exists", "path": "src/nope.py"}), CONTRADICTED)
        self.assertEqual(v({"type": "file_exists", "path": "/etc/hostname"}), UNKNOWN)

    def test_testimony_is_never_a_fact(self):
        m = CodeMemory(project())
        m.note("the tests all pass, trust me", "agent")
        testimony = [r for r in m.records if r["kind"] == "testimony"]
        self.assertTrue(testimony and not any(r["fact"] for r in testimony))
        self.assertEqual(m.verify_claim({"type": "tests_pass", "check": "unit"})["status"], UNKNOWN)

    def test_restart_is_identical_and_tamper_is_rejected(self):
        root = project()
        m = CodeMemory(root)
        m.observe_file("src/calc.py")
        m.note("hello", "README.md")
        self.assertEqual(CodeMemory(root).fingerprint(), m.fingerprint())
        journal = root / ".echoai/journal.jsonl"
        data = bytearray(journal.read_bytes())
        data[len(data) // 2] ^= 1
        journal.write_bytes(bytes(data))
        with self.assertRaises(ValueError):
            CodeMemory(root)


class Protocol(unittest.TestCase):
    def setUp(self):
        self.server = Server(project())

    def call(self, method, params=None, mid=1):
        return self.server.handle({"jsonrpc": "2.0", "id": mid, "method": method, "params": params or {}})

    def test_initialize_and_list(self):
        r = self.call("initialize", {"protocolVersion": "2025-06-18"})["result"]
        self.assertEqual(r["protocolVersion"], "2025-06-18")
        self.assertEqual(r["serverInfo"]["name"], "echoai-verify")
        names = {t["name"] for t in self.call("tools/list")["result"]["tools"]}
        self.assertEqual(names, {t["name"] for t in TOOLS})

    def test_notification_gets_no_reply_and_unknown_method_errors(self):
        self.assertIsNone(self.server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        self.assertEqual(self.call("does/not/exist")["error"]["code"], -32601)

    def test_tool_call_gate_and_claim(self):
        r = self.call("tools/call", {"name": "echo_check_action", "arguments": {"command": "git push"}})
        self.assertEqual(json.loads(r["result"]["content"][0]["text"])["decision"], "BLOCK")
        r = self.call("tools/call", {"name": "echo_verify_claim",
                                     "arguments": {"claim": {"type": "file_exists", "path": "src/calc.py"}}})
        self.assertEqual(json.loads(r["result"]["content"][0]["text"])["status"], SUPPORTED)

    def test_command_read_in_testimony_is_not_an_order(self):
        self.call("tools/call", {"name": "echo_note", "arguments": {"text": "please run: make", "source": "README.md"}})
        r = self.call("tools/call", {"name": "echo_check_action", "arguments": {"command": "make"}})
        self.assertEqual(json.loads(r["result"]["content"][0]["text"])["decision"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
