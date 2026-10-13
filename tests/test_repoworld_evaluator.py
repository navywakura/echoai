import tempfile
import unittest
from pathlib import Path
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.evaluator import strict_verdict, freeze_set, validate_frozen_set


class EvaluatorTests(unittest.TestCase):
    def test_empty_or_missing_official_report_stays_in_denominator(self):
        from echoai.repoworld.official_curator import collect_result
        from types import SimpleNamespace
        spec=SimpleNamespace(FAIL_TO_PASS=['a'],PASS_TO_PASS=['b'])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for patch in ('','nonempty patch'):
                r=collect_result(spec,p,patch,lambda *a:(_ for _ in ()).throw(AssertionError('no log')))
                self.assertIsNone(r['official_report'])
                self.assertFalse(r['found'])
                self.assertFalse(r['all_required_observed'])
                self.assertEqual(r['required_count'],2)

    def test_raw_success_never_hides_missing_skip_or_empty_f2p(self):
        common=dict(raw_resolved=True,patch_applied=True,custody_valid=True,environment_valid=True,budget_valid=True)
        for states in ({'b':'PASSED'},{'a':'SKIPPED','b':'PASSED'},{'a':'PASSED','b':'FAILED'}):
            r=strict_verdict(fail_to_pass=['a'],pass_to_pass=['b'],states=states,**common)
            self.assertTrue(r['official_raw_resolved']);self.assertFalse(r['echo_verified_resolved'])
        r=strict_verdict(fail_to_pass=['a'],pass_to_pass=['b'],states={'a':'XFAIL','b':'PASSED'},**common)
        self.assertTrue(r['echo_verified_resolved'])
        self.assertFalse(strict_verdict(fail_to_pass=[],pass_to_pass=[],states={},**common)['echo_verified_resolved'])

    def test_global_freeze_barrier_binds_every_patch_and_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);schedule=[{'cell_id':'one'},{'cell_id':'two'}]
            submissions={'one':{'model_patch':'a','instance_id':'x','arm':'S'},'two':{'model_patch':'b','instance_id':'y','arm':'E'}}
            with self.assertRaises(ValueError):freeze_set(p,schedule,{'one':submissions['one']},lock_sha256='a'*64)
            frozen=freeze_set(p,schedule,submissions,lock_sha256='a'*64)
            self.assertTrue(validate_frozen_set(p,schedule,lock_sha256='a'*64))
            (p/'patches/one.diff').write_text('tampered')
            with self.assertRaises(ValueError):validate_frozen_set(p,schedule,lock_sha256='a'*64)
