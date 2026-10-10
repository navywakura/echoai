"""Read-only B24 v1 transport regression; no inference, tokenizer or games.

Fixtures are the unchanged private receipts extracted for the R1 investigation.
These tests preserve the observed rejection; they do not implement a recovery.
"""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from seed import s6b24_model as model, s6b24_preflight as preflight
from seed.game_selfimprove import sha


EVIDENCE = (Path(__file__).resolve().parents[1] / "lab/seed"
            / "s6b24-r1-investigation-20261009/b24-results")


@unittest.skipUnless((EVIDENCE / "input/manifest.json").is_file(),
                     "requires the private v1 receipts from the B24 R1 forensics report")
class RecordedB24Transport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((EVIDENCE / "input/manifest.json").read_text())
        cls.registry = json.loads((EVIDENCE / "input/models.json").read_text())
        cls.profile = sha(cls.manifest)
        cls.format_root = EVIDENCE / "format-preflight"
        cls.cases = preflight.all_cases()
        cls.failed = cls.format_root / "calls/FORMAT-ID/001"

    def setUp(self):
        guard = patch.object(model.subprocess, "run",
                             side_effect=AssertionError("forensic tests forbid subprocesses"))
        self.no_process = guard.start()
        self.addCleanup(guard.stop)

    def test_marker_only_stdout_is_empty_content_not_a_recoverable_choice(self):
        raw = (self.failed / "stdout.txt").read_bytes()
        self.assertEqual(raw, b" [end of text]\n\n\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         "ef9ea7f6620ab14103f8da54b436115262606a0d462faea70dd1661d3d554df8")
        with patch.object(model.search, "reconstruct") as reconstruct:
            with self.assertRaises(json.JSONDecodeError) as caught:
                model.answer(raw.decode(), self.cases[5]["request"])
            reconstruct.assert_not_called()
        self.assertEqual(caught.exception.doc, "")
        self.assertEqual(caught.exception.pos, 0)
        self.assertEqual(str(caught.exception),
                         "Expecting value: line 1 column 1 (char 0)")

    def test_the_same_decoration_already_parses_on_all_five_successes(self):
        for case in self.cases[:5]:
            with self.subTest(arm=case["arm"], index=case["index"]):
                folder = self.format_root / "calls" / case["arm"] / f'{case["index"]:03d}'
                raw = (folder / "stdout.txt").read_text()
                self.assertTrue(raw.endswith(" [end of text]\n\n\n"))
                self.assertEqual(model.answer(raw, case["request"]), case["expected"])

    def test_six_receipts_match_frozen_requests_prompts_grammars_and_commands(self):
        self.assertEqual(self.profile,
                         "de1c1dc9c7206ebde60a3a9de2756d3ae6c8ac1eb6d4fe7904a333553c43b488")
        calls = []
        for case in self.cases[:6]:
            arm, index, req = case["arm"], case["index"], case["request"]
            call = f"{arm}/{index:03d}"
            with self.subTest(call=call):
                folder = self.format_root / "calls" / call
                result = model.load(folder, req, arm, preflight.SEED + index, self.profile)
                runtime_prompt = (Path(self.manifest["execution_root"])
                                  / "format-preflight/calls" / call / "prompt.txt")
                self.assertEqual(json.loads((folder / "command.json").read_text()),
                                 model.command(self.registry["N7"], runtime_prompt,
                                               preflight.SEED + index, req))
                self.assertEqual(result["usage"]["model_calls"], 1)
                self.assertEqual(result["returncode"], 0)
                self.assertTrue(result["transport_ok"])
                self.assertEqual(result["proposal"],
                                 None if call == "FORMAT-ID/001" else case["expected"])
                calls.append(call)
        ledger = json.loads((self.format_root / "model-budget.json").read_text())
        self.assertEqual(ledger["calls"], calls)

    def test_failed_prompt_puts_input_eog_at_the_first_native_batch_boundary(self):
        tokens = json.loads((self.failed / "tokens.json").read_text())["N7"]
        command = json.loads((self.failed / "command.json").read_text())
        batch = int(command[command.index("-b") + 1])
        self.assertEqual(batch, 128)
        self.assertEqual(len(tokens), 132)
        end_marker = self.registry["N7"]["prompt_protocol"]["markers"]["<|im_end|>"]
        self.assertEqual(end_marker, 151645)
        self.assertEqual(tokens[batch - 1], end_marker)
        self.assertEqual(tokens[batch:], [198, 151644, 77091, 198])
        self.assertIn("--no-conversation", command)
        self.assertIn("--no-display-prompt", command)
        stderr = (self.failed / "stderr.txt").read_text()
        self.assertIn("EOG token        = 151645 '<|im_end|>'", stderr)
        self.assertIn("sampling time =       0.02 ms /   128 runs", stderr)
        # Controls use the same native command and never end a prompt chunk on EOG.
        for case in self.cases[:5]:
            folder = self.format_root / "calls" / case["arm"] / f'{case["index"]:03d}'
            control = json.loads((folder / "tokens.json").read_text())["N7"]
            self.assertNotIn(end_marker, control[batch - 1::batch])

    def test_saved_failure_cannot_be_retried_or_rewritten_by_resume(self):
        receipt = self.failed / "result.json"
        ledger = self.format_root / "model-budget.json"
        before = (receipt.read_bytes(), ledger.read_bytes())
        with self.assertRaisesRegex(RuntimeError,
                                    "^prior failed model call; explicit recovery required$"):
            model.propose(self.format_root, self.registry, "FORMAT-ID", 1,
                          self.cases[5]["request"], preflight.SEED + 1, self.profile)
        self.assertEqual((receipt.read_bytes(), ledger.read_bytes()), before)
        self.no_process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
