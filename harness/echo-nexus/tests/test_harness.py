import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from echo_nexus.backend import Runner, Tail, read_manifest
from echo_nexus.config import redact, save_config
from echo_nexus.transport import Cortex, LocalModel, MCP, endpoint


class Boundaries(unittest.TestCase):
    def test_no_plaintext_remote_credentials_or_redirects(self):
        for url in ("http://example.org/v1", "https://key@example.org", "https://a.test/v1?key=secret", "file:///tmp/api"):
            with self.assertRaises(ValueError):
                endpoint(url)
        self.assertEqual(endpoint("http://127.0.0.1:1234/v1/"), "http://127.0.0.1:1234/v1")
        with self.assertRaises(ValueError):
            Cortex("https://api.example.org/v1", "model", "sk-raw-secret")

    def test_redaction_and_private_config(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"ECHO_NEXUS_HOME": root, "PROVIDER_KEY": "test-secret-value"}):
            self.assertEqual(redact("\x1b[31mtest-secret-value"), "[REDACTED]")
            save_config({"backend": "/example/manifest.json"})
            self.assertEqual((Path(root) / "config.json").stat().st_mode & 0o777, 0o600)

    def test_tail_partial_writes_and_rotation(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "events.jsonl"
            file.write_bytes(b'{"turn":')
            tail = Tail(file)
            self.assertEqual(tail.read(), [])
            with file.open("ab") as f:
                f.write(b'1}\n')
            self.assertEqual(tail.read(), [{"turn": 1}])
            self.assertEqual(tail.read(), [])
            file.rename(file.with_suffix(".old"))
            file.write_text('{"turn":2}\n')
            self.assertEqual(tail.read(), [{"turn": 2}])

    def test_manifest_rejects_duplicate_tests_and_shell_strings(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            for tests in ([{"id": "x", "kind": "development", "argv": "echo unsafe"}],
                          [{"id": "x", "kind": "sealed"}, {"id": "x", "kind": "sealed"}]):
                path.write_text(json.dumps({"schema": "echo-nexus-backend-v1", "tests": tests}))
                with self.assertRaises(ValueError):
                    read_manifest(path)


class Processes(unittest.IsolatedAsyncioTestCase):
    async def test_sealed_exam_never_starts(self):
        with tempfile.TemporaryDirectory() as root:
            sentinel = Path(root) / "should-not-exist"
            runner = Runner()
            test = {"id": "sealed", "kind": "sealed", "argv": [sys.executable, "-c", f"open({str(sentinel)!r},'w')"]}
            with self.assertRaises(ValueError):
                await runner.run(test, lambda _: None)
            self.assertFalse(sentinel.exists())

    async def test_real_child_stream_and_timeout(self):
        runner = Runner()
        events = []
        rc = await runner.run({"id": "smoke", "kind": "development", "argv": [sys.executable, "-c",
            "import json; print(json.dumps({'kind':'result','text':'real output'}))"]}, events.append)
        self.assertEqual(rc, 0)
        self.assertEqual(events[0]["text"], "real output")
        with self.assertRaises(asyncio.TimeoutError):
            await runner.run({"id": "timeout", "kind": "development", "timeout": 0.1,
                              "argv": [sys.executable, "-c", "import time; time.sleep(60)"]}, events.append)
        self.assertIsNone(runner.process)

    async def test_mcp_handshake_pagination_call_and_shutdown(self):
        script = '''import json,sys
for line in sys.stdin:
 r=json.loads(line)
 if 'id' not in r: continue
 method=r['method']
 if method=='initialize': data={'protocolVersion':'2025-06-18','capabilities':{'tools':{}}}
 elif method=='tools/list':
  data={'tools':[{'name':'echo','inputSchema':{'type':'object'}}]} if r.get('params',{}).get('cursor') else {'tools':[], 'nextCursor':'two'}
 else: data={'content':[{'type':'text','text':r['params']['arguments']['message']}], 'isError':False}
 print(json.dumps({'jsonrpc':'2.0','id':r['id'],'result':data}),flush=True)
'''
        client = MCP()
        try:
            await client.connect([sys.executable, "-u", "-c", script])
            self.assertEqual(client.tools[0]["name"], "echo")
            response = await client.call("echo", {"message": "verified mock roundtrip"})
            self.assertEqual(response["content"][0]["text"], "verified mock roundtrip")
            with self.assertRaises(ValueError):
                await client.call("unlisted", {})
        finally:
            await client.close()
        self.assertIsNone(client.process)

    async def test_invalid_gguf_cannot_launch(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "bad.gguf"
            file.write_bytes(b"NOT_A_MODEL")
            model = LocalModel()
            with self.assertRaises(ValueError):
                await model.start(file)
            self.assertIsNone(model.process)

    async def test_cortex_request_preserves_message_and_does_not_execute(self):
        import httpx
        seen = []
        def handle(request):
            seen.append(json.loads(request.content))
            return httpx.Response(200, json={"choices": [{"message": {"content": "Propuesta sin verificar"}}]})
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch("echo_nexus.transport.httpx.AsyncClient", return_value=client):
            cortex = Cortex("https://example.org/v1", "test-model")
            result = await cortex.ask("Hola ECHO")
        self.assertEqual(seen[0]["messages"][-1]["content"], "Hola ECHO")
        self.assertNotIn("tools", seen[0])
        self.assertEqual(result, "Propuesta sin verificar")


class Interface(unittest.IsolatedAsyncioTestCase):
    async def test_command_completion_small_terminal_and_real_demo(self):
        from echo_nexus.app import Nexus
        from textual.widgets import Input
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"ECHO_NEXUS_HOME": root, "ECHO_NEXUS_STATE": root}):
            app = Nexus(stars=False)
            async with app.run_test(size=(80, 30)) as pilot:
                prompt = app.query_one(Input)
                prompt.value = "/connect l"
                await pilot.press("tab")
                self.assertEqual(prompt.value, "/connect local ")
                await app.execute("/demo")
                self.assertIsNotNone(app.grid)
                self.assertFalse(app.cortex)
                self.assertNotIn("lif_a", app.row)
                self.assertTrue(app.has_class("narrow"))
                await pilot.press("f2")
                self.assertTrue(app.has_class("expanded"))
                await app.execute("/stars off")
                self.assertFalse(app.stars_enabled)


if __name__ == "__main__":
    unittest.main()
