import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from echo5 import efficiency_runner as r


class EfficiencyRunnerTests(unittest.TestCase):
    def test_no_promotion_or_unregistered_stage(self):
        plan = json.loads(r.PROTOCOL.read_text())
        self.assertEqual(r.validate_protocol(plan), plan)
        for changed in ({**plan, 'automatic_promotion': True},
                        {**plan, 'stages': {'search_fresh': {}}}):
            with self.assertRaises(ValueError):
                r.validate_protocol(changed)

    def test_failure_to_freeze_is_recorded_as_instrument_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(r, 'freeze', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    r.run(Path(directory))
            status = json.loads((Path(directory)/'status.json').read_text())
            self.assertEqual(status['phase'], 'instrument_error')
            self.assertFalse(status['promotion'])

    def test_native_audit_rejects_smaller_cohort_before_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root/'exploration'
            folder.mkdir()
            (root/'sources.json').write_text(json.dumps({'own': {'sha256': 'fake'}}))
            (root/'plan.json').write_text(r.PROTOCOL.read_text())
            (folder/'result.json').write_text(json.dumps({'config': {'cases_per_profile': 1}}))
            with patch.object(r, 'preserve'), patch.object(r, 'verify_archive'), \
                 patch.object(r, 'measure', side_effect=AssertionError('must use native replay')):
                with self.assertRaises(ValueError):
                    r.worker(folder, 'exploration', 'audit')


if __name__ == '__main__':
    unittest.main()
