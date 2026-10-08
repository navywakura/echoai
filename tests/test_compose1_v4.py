"""Sample-design regressions, including the discrete red that motivated V4."""
import unittest
from echoai.nexus0.compose1_v3 import bench as previous
from echoai.nexus0.compose1_v4 import bench
from echoai.nexus0.compose1_v4.power import critical_wins, power


class TestSampleDesign(unittest.TestCase):
    def test_no_rounding_a_near_threshold_result_to_green(self):
        self.assertEqual(critical_wins(32), 23)
        self.assertGreater(previous.sign_test([1]*22+[-1]*10)['one_sided_p'], .025)
        self.assertLess(previous.sign_test([1]*23+[-1]*9)['one_sided_p'], .025)

    def test_only_sample_counts_seeds_and_version_change(self):
        altered = {k for k in bench.PROTOCOL if bench.PROTOCOL[k] != previous.PROTOCOL[k]}
        self.assertEqual(altered, {'version', 'functional_validation', 'functional_confirmation'})
        b, c = map(set, (bench.PROTOCOL['functional_validation'], bench.PROTOCOL['functional_confirmation']))
        self.assertEqual((len(b), len(c)), (512, 512))
        self.assertFalse(b & c)
        self.assertFalse((b | c) & set(previous.PROTOCOL['functional_validation']))
        self.assertIs(bench.mission, previous.mission)
        self.assertIs(bench.run, previous.run)
        self.assertIs(bench.audit_session, previous.audit_session)
        self.assertIs(bench.metrics, previous.metrics)

    def test_power_calculation_checks_null_and_observed_alternative(self):
        self.assertLess(power(64, .5), .025)
        self.assertLess(power(64), .51)
        self.assertGreater(power(256), .98)


if __name__ == '__main__':
    unittest.main()
