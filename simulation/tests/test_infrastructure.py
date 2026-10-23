import tempfile
import unittest
import subprocess
import sys
from pathlib import Path

from echo5.budget import Budget, BudgetExceeded
from echo5.legacy import module
from echo5.trace import Recorder, verify_journal


class InfrastructureTests(unittest.TestCase):
    def test_cli_starts_under_isolated_pinned_python(self):
        root = Path(__file__).resolve().parents[1]
        run = subprocess.run([sys.executable, '-I', str(root / 'scripts/run.py'), '--help'],
                             cwd=root, capture_output=True, text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('bench', run.stdout)

    def test_budget_charges_before_overflow_and_rejects_invalid_units(self):
        b = Budget(5)
        b.consume('segment', 3)
        with self.assertRaises(BudgetExceeded):
            b.consume('search', 3)
        self.assertEqual((b.used, b.counts), (3, {'segment': 3}))
        for n in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                b.consume('invalid', n)
        b.add('search', 2)
        self.assertEqual(b.used, 5)

    def test_legacy_has_single_identity_and_no_campaign_import(self):
        import sys
        a = module('seed.relational_dsl')
        b = module('echoai.seed.relational_dsl')
        self.assertIs(a, b)
        self.assertIs(a.Object, b.Object)
        self.assertNotIn('echoai.seed.s6b24', sys.modules)
        with self.assertRaises(ValueError):
            module('os')

    def test_same_installation_through_symlink_is_not_a_foreign_package(self):
        from unittest.mock import patch
        from echo5.legacy import ROOT
        module('seed.relational_dsl')
        import echoai
        with tempfile.TemporaryDirectory() as folder:
            alias = Path(folder) / 'package'
            alias.symlink_to(ROOT, target_is_directory=True)
            with patch.object(echoai, '__path__', [str(alias)]):
                self.assertIs(module('seed.relational_dsl'), module('echoai.seed.relational_dsl'))
            with patch.object(echoai, '__path__', [folder]):
                with self.assertRaises(RuntimeError):
                    module('seed.relational_dsl')

    def test_existing_journal_detects_tampering_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'thought.jsonl'
            with Recorder(p) as trace:
                trace.write(kind='observation', observed={'objects': 2})
                trace.write(kind='result', success=False)
            self.assertEqual(verify_journal(p)['events'], 2)
            with self.assertRaises(FileExistsError):
                Recorder(p)
            p.write_text(p.read_text().replace('"success": false', '"success": true'))
            with self.assertRaises(ValueError):
                verify_journal(p)

    def test_journal_envelope_cannot_be_overridden(self):
        with tempfile.TemporaryDirectory() as folder:
            with Recorder(Path(folder) / 'thought.jsonl') as trace:
                for key in ('schema', 'index', 'time', 'prev', 'hash', 'agent'):
                    with self.assertRaises(ValueError):
                        trace.write(kind='result', **{key: 'forged'})


if __name__ == '__main__':
    unittest.main()
