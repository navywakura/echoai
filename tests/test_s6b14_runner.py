import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import copy

from seed import s6b14 as r


class RunnerTests(unittest.TestCase):
    def tearDown(self):
        r.configure()

    def test_transport_has_STDOUT_and_routes_the_audit(self):
        self.assertEqual(r.b.subprocess.STDOUT, subprocess.STDOUT)
        with patch.object(r.subprocess, 'run', return_value='child') as run:
            self.assertEqual(r.b.subprocess.run(['python', '-m', 'seed.s6b13', 'audit', 'pilot'],
                stdout='log', stderr=r.b.subprocess.STDOUT, check=True), 'child')
            self.assertEqual(run.call_args.args[0], ['python', '-m', 'seed.s6b14', 'audit', 'pilot'])
            self.assertEqual(run.call_args.kwargs['stderr'], subprocess.STDOUT)

    def test_completed_negative_pilot_launches_audit_then_closes_without_campaign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pilot.json').write_text(json.dumps({'promote': False}))
            def child(command, **kwargs):
                self.assertEqual(command[-3:], ['seed.s6b14', 'audit', 'pilot'])
                self.assertEqual(kwargs['stderr'], subprocess.STDOUT)
                (root / 'pilot-audit.json').write_text(json.dumps({'valid': True}))
            with patch.object(r.b, 'ROOT', root), patch.object(r.b, 'prepare'), \
                    patch.object(r.b, 'preflight'), patch.object(r.b, 'publish'), \
                    patch.object(r.b, 'status'), patch.object(r.subprocess, 'run', side_effect=child), \
                    patch.object(r.b, 'run_phase', side_effect=AssertionError('must reuse completed pilot')):
                r.b.follow()
            value = json.loads((root / 'closed.json').read_text())
            self.assertEqual(value['result'], 'PILOT_NO_PROMOTION')
            self.assertFalse(value['s6_green'])
            self.assertFalse((root / 'exam').exists())

    def test_protected_and_reserved_partitions_are_new(self):
        previous = json.loads((r.PREVIOUS / 'profile.json').read_text())['configuration']
        self.assertFalse(set(map(tuple, r.b.B)) & set(map(tuple, previous['B'])))
        self.assertFalse(set(r.b.EXAM_SEEDS) & set(previous['exam_seeds']))
        self.assertEqual(r.b.MAX_CALLS, 96)
        self.assertEqual(r.b.MAX_GAMES, 64000)

    def test_workers_and_cache_use_new_root(self):
        self.assertEqual(r.b._play.__globals__['ROOT'], r.ROOT)
        self.assertEqual(r.b.reserve_games.__globals__['ROOT'], r.ROOT)
        with tempfile.TemporaryDirectory() as tmp, patch.object(r, 'ROOT', Path(tmp)):
            measure = r.measurement('pilot-independent')
            self.assertEqual(measure.__globals__['ROOT'], Path(tmp) / 'pilot-independent')
            self.assertIs(measure.__globals__['old'].worker_init, r.worker_init)

    def test_new_receipts_certificates_and_requests_reconstruct_in_audit(self):
        from tests.test_s6b14_policy import measured_row
        rows = [measured_row(i) for i in range(2)]
        for row in rows:
            row.update(frames=['fixture'], actions_per_level=[1], resets=0,
                       automatic_reset_indices=[])
        value = dict(levels=6, score=2, trace_digest=r.b.sha(rows), rows=rows)
        responses = {}
        def generate(call, request, *args, **kwargs):
            response = dict(answer=r.prompts.random_answer(request, 41),
                            usage=dict(input_tokens=1, max_output_tokens=160))
            responses[call] = response
            return response
        with tempfile.TemporaryDirectory() as tmp, patch.object(r.b, 'ROOT', Path(tmp)), \
                patch.object(r.b, 'integrity', return_value={}), \
                patch.object(r.b, 'phase_shape', return_value=(2, 1, (1,))), \
                patch.object(r.b, 'measurement', return_value=lambda *a, **kw: copy.deepcopy(value)), \
                patch.object(r.model, 'propose', side_effect=generate), \
                patch.object(r.model, 'load', side_effect=lambda call, *a, **kw: responses[call]), \
                patch.object(r.b, 'publish'), patch.object(r.b, 'status'):
            result = r.b.run_phase('pilot')
            self.assertEqual(len(result['verdicts']), 6)
            self.assertTrue(any('decision_certificate' in e for e in result['verdicts']))
            r.b.atomic(Path(tmp) / 'pilot-process.json', {'pid': -1})
            self.assertEqual(result, r.b.run_phase('pilot', audit=True))
            receipt = json.loads((Path(tmp) / 'pilot-audit.json').read_text())
            self.assertTrue(receipt['valid'])

    def test_missing_previous_audit_cannot_start_new_games(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(r, 'PREVIOUS', Path(tmp)):
            self.assertFalse(r.previous_closed())
            with patch.object(r.b, 'main', side_effect=AssertionError('must not start audit')):
                with self.assertRaisesRegex(RuntimeError, 'close first'):
                    r.dispatch(['audit', 'pilot'])

    def test_original_sources_unchanged(self):
        for name, expected in json.loads((r.PREVIOUS / 'profile.json').read_text())['sources'].items():
            self.assertEqual(r.hashlib.sha256((r.REPO / name).read_bytes()).hexdigest(), expected, name)


if __name__ == '__main__':
    unittest.main()
