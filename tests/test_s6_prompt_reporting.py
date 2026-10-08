from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import tempfile
import unittest


class Reporting(unittest.TestCase):
    def load(self, root):
        path = Path(__file__).resolve().parents[1] / "lab/seed/s6-prompt-pilot-20260928/background.py"
        spec = spec_from_file_location("_test_s6_reporting", path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        module.REPO = Path(root)
        module.ROOT = Path(root) / "pilot"
        module.BASE = Path(root) / "gpu"
        module.ROOT.mkdir()
        module.BASE.mkdir()
        return module

    def test_mirror_is_idempotent_and_preserves_actual_requests_and_verdict(self):
        with tempfile.TemporaryDirectory() as temp:
            module = self.load(temp)
            batch = {"local-echo-602001": [{"id": 0, "type": "P1", "prompt": "actual prompt"}]}
            (module.ROOT / "requests.json").write_text(json.dumps(batch))
            (module.BASE / "answers.json").write_text(json.dumps({"complete": True,
                "arms": {"local-echo-602001": [{"id": 0, "answer": "actual answer"}]}}))
            verdict = {"arm": "echo", "seed": 602001, "id": 0, "verdict": "V3",
                       "A": {"before_levels": 178, "after_levels": 184}}
            (module.ROOT / "verdicts.json").write_text(json.dumps([verdict]))
            module.mirror()
            journal = module.ROOT / "visible/local-echo-602001/journal.jsonl"
            first = journal.read_bytes()
            module.mirror()
            self.assertEqual(first, journal.read_bytes())
            events = module.events(journal)
            self.assertEqual([e["kind"] for e in events], ["requests", "answers", "verdict"])
            self.assertEqual(events[0]["requests"], batch["local-echo-602001"])
            self.assertEqual(events[1]["answers"][0]["answer"], "actual answer")
            self.assertEqual(events[2]["trial_A"], 184)
            self.assertEqual(json.loads((module.ROOT / "verdicts.json").read_text()), [verdict])

    def test_skipped_report_declares_zero_calls_and_keeps_S6_red(self):
        with tempfile.TemporaryDirectory() as temp:
            module = self.load(temp)
            docs = module.REPO / "docs"
            docs.mkdir()
            (docs / "NOW.md").write_text("# NOW\n\nPrevious state.\n")
            (module.ROOT / "status.json").write_text(json.dumps({"stage": "SKIPPED", "llm_calls": 0,
                                                              "reason": "no positive"}))
            module.report()
            text = (docs / "ECHO45-S6-PROMPT-PILOT-RESULTS.md").read_text()
            self.assertIn("Cero llamadas LLM", text)
            self.assertIn("S6 sigue ROJO", text)
            self.assertIn("Previous state", (docs / "NOW.md").read_text())


if __name__ == "__main__":
    unittest.main()
