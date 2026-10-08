import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from seed import s6b15 as r, s6b15_micro as micro
from tests.test_s6b14_policy import measured_row


class RunnerTests(unittest.TestCase):
    def setUp(self):
        r.configure()

    def tearDown(self):
        r.configure()

    def test_STDOUT_and_new_audit_subprocess(self):
        self.assertEqual(r.b.subprocess.STDOUT, subprocess.STDOUT)
        with patch.object(r.subprocess, 'run', return_value='child') as run:
            r.b.subprocess.run(['python', '-m', 'seed.s6b13', 'audit', 'pilot'], stderr=r.b.subprocess.STDOUT)
            self.assertEqual(run.call_args.args[0], ['python', '-m', 'seed.s6b15', 'audit', 'pilot'])

    def test_new_partitions_and_bounded_budget(self):
        old = json.loads((r.PREVIOUS / 'profile.json').read_text())['configuration']
        self.assertFalse(set(map(tuple, r.b.B)) & set(map(tuple, old['B'])))
        self.assertFalse(set(r.b.EXAM_SEEDS) & set(old['exam_seeds']))
        self.assertEqual(r.b.MAX_CALLS, 108)
        self.assertEqual(r.b.MAX_GAMES, 64000)
        self.assertEqual(r.b._play.__globals__['ROOT'], r.ROOT)
        self.assertIs(r.measurement('pilot-independent').__globals__['old'].worker_init, r.worker_init)

    def test_micro_promotion_requires_correct_cell_gain_replay_and_no_loss(self):
        good = dict(binding=True, numeric=True, passes_A=True, reproduced=True,
                    actual_operator='HOLD', requested_operator='HOLD', levels=383, gain=5, loss_indices=[])
        self.assertTrue(micro.gate([good]))
        for key in ('binding', 'numeric', 'passes_A', 'reproduced'):
            self.assertFalse(micro.gate([dict(good, **{key: False})]))
        self.assertFalse(micro.gate([dict(good, actual_operator='REVALIDATE_NOOP')]))
        self.assertFalse(micro.gate([dict(good, loss_indices=[51])]))
        self.assertFalse(micro.gate([dict(good, gain=1, levels=379)]))

    def test_invalid_micro_answer_is_counted_without_replaying_or_retrying(self):
        request = r.prompts.request('fijo', 1, r.b.strategy(), {'rows': [measured_row()]}, [])
        with patch.object(r.b, 'reproduced', side_effect=AssertionError('invalid proposal must not run')):
            result = micro.evaluate(None, 'fixture', {'answer': '{', 'usage': {'input_tokens': 12}},
                                    request, r.b.strategy(), {})
        self.assertEqual(result['verdict'], 'V1')
        self.assertFalse(result['passes_A'])

    def test_negative_micro_stops_before_pilot_and_protected_games(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(r, 'ROOT', Path(tmp)), \
                patch.object(r, 'previous_closed', return_value={'valid': True}), \
                patch.object(r.b, 'prepare'), patch.object(r, 'publish'), patch.object(r, 'status'), \
                patch.object(r.subprocess, 'Popen'), patch.object(micro, 'run'), \
                patch.object(r, 'micro_gate', return_value=False), \
                patch.object(r.b, 'follow', side_effect=AssertionError('pilot must not run')):
            r.dispatch(['follow'])
            result = json.loads((Path(tmp) / 'closed.json').read_text())
            self.assertEqual(result['result'], 'MICRO_NO_PROMOTION')
            self.assertFalse(result['exam_opened'])

    def test_phase_audit_reconstructs_actual_operator_telemetry(self):
        rows = [measured_row(i) for i in range(2)]
        for row in rows:
            row.update(frames=['fixture'], actions_per_level=[1], resets=0, automatic_reset_indices=[])
        value = dict(levels=6, score=2, trace_digest=r.b.sha(rows), rows=rows)
        responses = {}
        def generate(call, request, *args, **kwargs):
            response = dict(answer=r.prompts.random_answer(request, 41),
                            usage=dict(input_tokens=1, max_output_tokens=160))
            responses[call] = response
            return response
        with tempfile.TemporaryDirectory() as tmp, patch.object(r.b, 'ROOT', Path(tmp)), \
                patch.object(r.b, '_journal', None), patch.object(r.b, 'integrity', return_value={}), \
                patch.object(r.b, 'phase_shape', return_value=(3, 1, (1,))), \
                patch.object(r.b, 'measurement', return_value=lambda *a, **kw: copy.deepcopy(value)), \
                patch.object(r.model, 'propose', side_effect=generate), \
                patch.object(r.model, 'load', side_effect=lambda call, *a, **kw: responses[call]), \
                patch.object(r.b, 'publish'), patch.object(r.b, 'status'):
            result = r.b.run_phase('pilot')
            self.assertEqual(len(result['verdicts']), 9)
            for event in result['verdicts']:
                telemetry = event['experiment']
                self.assertEqual(telemetry['requested_operator'], telemetry['measured_operator'])
            for arm in ('echo', 'fijo', 'random'):
                self.assertEqual([e['experiment']['measured_operator'] for e in result['verdicts'] if e['arm'] == arm],
                                 ['REVALIDATE_NOOP', 'HOLD', 'COOLDOWN_CAP'])
            r.b.atomic(Path(tmp) / 'pilot-process.json', {'pid': -1})
            self.assertEqual(result, r.b.run_phase('pilot', audit=True))
            self.assertTrue(json.loads((Path(tmp) / 'pilot-audit.json').read_text())['valid'])

    def test_closed_negative_pilot_is_still_audited_before_stopping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pilot.json').write_text(json.dumps({'promote': False}))
            def child(command, **kwargs):
                self.assertEqual(command[-3:], ['seed.s6b15', 'audit', 'pilot'])
                (root / 'pilot-audit.json').write_text(json.dumps({'valid': True}))
            with patch.object(r.b, 'ROOT', root), patch.object(r.b, 'prepare'), \
                    patch.object(r.b, 'preflight'), patch.object(r.b, 'publish'), \
                    patch.object(r.b, 'status'), patch.object(r.subprocess, 'run', side_effect=child), \
                    patch.object(r.b, 'run_phase', side_effect=AssertionError('must reuse completed pilot')):
                r.b.follow()
            self.assertEqual(json.loads((root / 'closed.json').read_text())['result'], 'PILOT_NO_PROMOTION')

    def test_B14_frozen_sources_unchanged(self):
        for name, expected in json.loads((r.PREVIOUS / 'profile.json').read_text())['sources'].items():
            self.assertEqual(r.model.digest_file(r.REPO / name), expected, name)


if __name__ == '__main__':
    unittest.main()
