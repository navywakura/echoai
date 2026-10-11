import unittest
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from echo5 import remediation as r
from echo5.exploration_study import normalize_config
from echo5.remediation import validate_protocol, STAGES


class RemediationContractTests(unittest.TestCase):
    def test_runner_cannot_turn_pilot_into_promotion(self):
        plan = {'schema': 'echo5.remediation.pilot.v1',
                'stage': 'development_pilot_not_confirmation', 'automatic_promotion': False,
                **{s:{} for s in STAGES}}
        self.assertEqual(validate_protocol(plan), plan)
        with self.assertRaises(ValueError):
            validate_protocol({**plan, 'automatic_promotion': True})
        with self.assertRaises(ValueError):
            validate_protocol({**plan, 'stage': 'confirmation'})


class RemediationCustodyTests(unittest.TestCase):
    def plan(self):
        return json.loads(r.PROTOCOL.read_text())

    def test_audit_cannot_shrink_the_registered_exploration_cohort(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root/'exploration'
            folder.mkdir()
            (root/'sources.json').write_text(json.dumps({'own': {'sha256': 'fake'}}))
            (root/'plan.json').write_text(json.dumps(self.plan()))
            (folder/'result.json').write_text(json.dumps({'config': normalize_config(
                {'profiles':['objects_small'], 'cases_per_profile':1})}))
            with patch.object(r, 'preserve', return_value={}), \
                 patch.object(r, 'verify_archive', return_value=None, create=True), \
                 patch.object(r, 'verify_journal', return_value={}), \
                 patch('echo5.exploration_study.audit_benchmark', return_value={'valid': True}):
                with self.assertRaises(ValueError):
                    r.worker(folder, 'exploration', 'audit')

    def test_aggregation_rejects_replaced_report_despite_valid_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_process(argv, log, **kw):
                folder = Path(argv[argv.index('--output')+1])
                action = argv[argv.index('--action')+1]
                if action == 'measure':
                    (folder/'result.json').write_text(json.dumps({'instrument_valid': True}))
                else:
                    (folder/'audit.json').write_text(json.dumps({'valid': True, 'result_sha256': 'wrong'}))
                return {'exit_code':0, 'timed_out':False}
            with patch.object(r, 'freeze', return_value={'own': {'sha256':'fake'}}), \
                 patch.object(r, 'preserve', return_value={}), \
                 patch.object(r, 'verify_archive', return_value=None, create=True), \
                 patch.object(r, 'run_process', side_effect=fake_process):
                with self.assertRaises(ValueError):
                    r.run(root)

    def test_snapshot_failure_has_a_structured_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(r, 'freeze', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    r.run(root)
            self.assertEqual(json.loads((root/'status.json').read_text())['phase'], 'instrument_error')

    def test_launch_failure_is_visible_without_a_running_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            folder=root/'artifacts'/'failed'
            with patch.object(r, 'ROOT', root), patch.object(r.subprocess, 'Popen', side_effect=OSError('spawn failed')):
                with self.assertRaises(OSError):
                    r.launch(folder)
            self.assertEqual(json.loads((folder/'status.json').read_text())['phase'], 'launch_error')
