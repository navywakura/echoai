"""Native restart wiring. No games and no model generations."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock

from seed import s6b13_runtime1 as r
from seed import s6b13_prompt as prompts


class RuntimeTests(unittest.TestCase):
    def test_same_scientific_functions_and_budgets(self):
        self.assertIs(r.b.prompts.request, prompts.request)
        self.assertEqual(r.b.MAX_CALLS, 96)
        self.assertEqual(r.b.MAX_GAMES, 64000)
        self.assertEqual(r.m.MAX_INPUT, 3072)
        self.assertEqual(r.m.MAX_OUTPUT, 160)
        self.assertEqual(r.m.TIMEOUT, 1800)
        self.assertEqual(r.b.phase_shape('pilot'), (6, 1, (697001, 697017, 697029)))

    def test_all_mutable_destinations_are_new(self):
        self.assertNotEqual(r.b.ROOT, r.ORIGINAL)
        self.assertEqual(r.b.reserve_games.__globals__['ROOT'], r.ROOT)
        self.assertEqual(r.b._play.__globals__['ROOT'], r.ROOT)
        with tempfile.TemporaryDirectory() as folder, mock.object(r, 'ROOT', Path(folder)):
            measure = r.measurement('pilot-independent')
            self.assertEqual(measure.__globals__['ROOT'], Path(folder) / 'pilot-independent')
            self.assertIs(measure.__globals__['old'].worker_init, r.worker_init)

    def test_audit_uses_restart_entrypoint(self):
        with mock.object(r, 'ORIGINAL_RUN', return_value='ok') as run:
            self.assertEqual(r.audit_dispatch(['python', '-u', '-m', 'seed.s6b13', 'audit', 'pilot']), 'ok')
            self.assertIn('seed.s6b13_runtime1', run.call_args.args[0])
        with self.assertRaises(RuntimeError):
            r.audit_dispatch(['unrelated-command'])

    def test_worker_initialization_restores_binding(self):
        with mock.object(r.ORIGINAL_OLD, 'worker_init') as init:
            r.worker_init()
            init.assert_called_once()
        self.assertEqual(r.b.ROOT, r.ROOT)
        self.assertEqual(r.b._play.__globals__['ROOT'], r.ROOT)

    def test_original_source_hashes_remain_valid(self):
        original = json.loads((r.ORIGINAL / 'profile.json').read_text())
        for path, expected in original['sources'].items():
            self.assertEqual(r.hashlib.sha256((r.REPO / path).read_bytes()).hexdigest(), expected, path)


if __name__ == '__main__':
    unittest.main()
