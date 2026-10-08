import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seed import rsi1_recovery1 as recovery


class RecoveryCustody(unittest.TestCase):
    def fixture(self, root):
        for name, data in [('status.json', {'stage': 'BLOCKED', 'message': 'local model process exited -6; no automatic retry'}),
                           ('budget.json', {'model_calls_reserved': 1, 'reserved_call_ids': ['311-llm_only-1']}),
                           ('profile.json', {'runtime': recovery.sys.version, 'configuration': recovery.BASE_CONFIGURATION,
                             'sources': {}, 'model_sha256': 'model', 'llama_cli_sha256': 'backend', 'model_path': '/fixture'})]:
            (root / name).write_text(json.dumps(data))

    def test_original_evidence_receipt_detects_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            before = recovery.original_receipt(root)
            (root / 'diagnosis.txt').write_text('changed original evidence')
            self.assertNotEqual(before, recovery.original_receipt(root))

    def test_successful_model_output_cannot_be_restarted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            (root / 'calls').mkdir(); (root / 'calls/one.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'model or exam'):
                recovery.original_receipt(root)

    def test_open_exam_cannot_be_restarted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            (root / 'exam-freeze.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'model or exam'):
                recovery.original_receipt(root)

    def test_additional_original_calls_cannot_be_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.fixture(root)
            (root / 'budget.json').write_text(json.dumps({'model_calls_reserved': 2}))
            with self.assertRaisesRegex(RuntimeError, 'call history'):
                recovery.original_receipt(root)

    def test_aggregate_budget_includes_failed_and_preflight_calls(self):
        with tempfile.TemporaryDirectory() as d, patch.object(recovery, 'ROOT', Path(d)):
            root = Path(d)
            (root / 'recovery.json').write_text(json.dumps({'prior_calls': 1, 'preflight_calls': 1,
                      'original': {'generations_saved': 10}}))
            (root / 'budget.json').write_text(json.dumps({'model_calls_reserved': 57}))
            self.assertEqual(recovery.accounting()['total_calls_reserved'], 59)
            (root / 'budget.json').write_text(json.dumps({'model_calls_reserved': 58}))
            with self.assertRaisesRegex(RuntimeError, 'budget exceeded'):
                recovery.accounting()


if __name__ == '__main__':
    unittest.main()
