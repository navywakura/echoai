"""Plan A1 v2: the amended controls must not be degenerate."""
import unittest

from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.transfer3 import calib_a1, screen_a1, screen_a1_v2
from echoai.nexus0.transfer3.body_a1 import CostBody
from echoai.nexus0.transfer3.rehearsal import ROOT

HISTORY = ROOT/'lab/transfer3/rehearsal-v4.json'


class Amendment(unittest.TestCase):
    def test_the_old_permutation_really_was_the_identity_on_a_uniform_base(self):
        payload = dict(calib_a1.nominal(), base=[4, 4, 4, 4], turn=4)
        self.assertEqual(calib_a1.permuted(payload)['base'], payload['base'])

    def test_turn_ablation_is_never_the_identity_when_a_turn_exists(self):
        for turn in range(1, 9):
            payload = dict(calib_a1.nominal(), base=[4, 4, 4, 4], turn=turn)
            self.assertNotEqual(screen_a1_v2.turn_ablated(payload), payload)

    def test_turn_ablation_keeps_the_learned_base(self):
        payload = dict(calib_a1.nominal(), base=[3, 5, 4, 4], turn=6)
        out = screen_a1_v2.turn_ablated(payload)
        self.assertEqual(out['base'], [3, 5, 4, 4])
        self.assertEqual(out['turn'], calib_a1.NOMINAL_TURN)
        calib_a1.validate(out)

    def test_turn_ablation_is_the_identity_only_on_the_flat_condition(self):
        payload = dict(calib_a1.nominal(), base=[4, 4, 4, 4], turn=0)
        self.assertEqual(screen_a1_v2.turn_ablated(payload), payload)

    def test_crossed_source_is_never_the_condition_itself(self):
        for name, source in screen_a1_v2.CROSSED_SOURCE.items():
            self.assertNotEqual(name, source)

    def test_crossed_source_is_never_flat(self):
        """`flat` calibration equals the nominal prior, so it would duplicate an arm."""
        self.assertNotIn('flat', screen_a1_v2.CROSSED_SOURCE.values())
        flat = CostBody.named('flat')
        self.assertEqual(list(flat.base), calib_a1.nominal()['base'])
        self.assertEqual(flat.turn, calib_a1.nominal()['turn'])

    def test_every_crossed_source_is_a_declared_condition(self):
        for source in screen_a1_v2.CROSSED_SOURCE.values():
            self.assertIn(source, screen_a1_v2.CONDITIONS)

    def test_alpha_is_tightened_not_loosened(self):
        self.assertEqual(screen_a1_v2.ALPHA_DENOMINATOR, 240)
        self.assertGreater(screen_a1_v2.ALPHA_DENOMINATOR, screen_a1.ALPHA_DENOMINATOR)


class Protocol(unittest.TestCase):
    def test_permuted_is_reported_but_not_a_criterion(self):
        self.assertIn('permuted', screen_a1_v2.PROTOCOL['reported_but_not_criterion'])
        self.assertNotIn('permuted', screen_a1_v2.PROTOCOL['content_controls'])

    def test_oracle_is_a_ceiling_not_an_arm(self):
        self.assertEqual(screen_a1_v2.PROTOCOL['ceiling'], 'oracle')
        self.assertNotIn('oracle', screen_a1_v2.PROTOCOL['arms'])

    def test_diagnostic_is_declared_non_candidate(self):
        diagnostic = screen_a1_v2.PROTOCOL['diagnostic']
        self.assertFalse(diagnostic['candidate'])
        self.assertFalse(diagnostic['counted_in_multiplicity'])

    def test_diagnostic_varies_only_the_base_asymmetry(self):
        asymmetries = sorted(max(b)-min(b) for b in screen_a1_v2.DIAGNOSTIC.values())
        self.assertEqual(asymmetries, [0, 1, 2])

    def test_unchanged_parameters_are_inherited_not_redeclared(self):
        self.assertEqual(screen_a1_v2.PROTOCOL['school_budget'], screen_a1.SCHOOL_BUDGET)
        self.assertEqual(screen_a1_v2.PROTOCOL['reserve_constant'], screen_a1.RESERVE)

    def test_audit_refuses_a_report_without_campaigns(self):
        with self.assertRaises(ValueError):
            screen_a1_v2.audit({'isolated': True})


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        history = loads_strict(HISTORY.read_bytes())
        cls.seeds = [r['seed'] for r in history['school_rooms']]

    def test_no_content_control_is_degenerate_in_a_turning_condition(self):
        schools = screen_a1_v2.taught_payloads(self.seeds)
        for name in screen_a1_v2.CONDITIONS:
            if CostBody.named(name).turn == 0:
                continue
            learned = schools[name]['payload']
            crossed = schools[screen_a1_v2.CROSSED_SOURCE[name]]['payload']
            self.assertNotEqual(screen_a1_v2.turn_ablated(learned), learned, name)
            self.assertNotEqual(crossed, learned, name)

    def test_crossed_is_never_the_nominal_prior(self):
        schools = screen_a1_v2.taught_payloads(self.seeds)
        for name in screen_a1_v2.CONDITIONS:
            crossed = schools[screen_a1_v2.CROSSED_SOURCE[name]]['payload']
            self.assertNotEqual((crossed['base'], crossed['turn']),
                                (calib_a1.nominal()['base'], calib_a1.nominal()['turn']), name)


if __name__ == '__main__':
    unittest.main()
