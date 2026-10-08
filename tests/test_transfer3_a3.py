"""Plan A3: mission-completion endpoint, McNemar, hand-set prior controls."""
import unittest

from echoai.nexus0.transfer3 import confirm_a2, confirm_a3, costs_a2, space_a2


def rows(flags, seeds=None):
    seeds = seeds or list(range(len(flags)))
    return [dict(seed=s, reached=bool(f)) for s, f in zip(seeds, flags)]


class McNemar(unittest.TestCase):
    def test_only_discordant_pairs_carry_information(self):
        out = confirm_a3.mcnemar(rows([1, 1, 0, 0]), rows([1, 1, 0, 0]))
        self.assertEqual((out['gained'], out['lost'], out['discordant']), (0, 0, 0))
        self.assertEqual(out['p_one_sided'], dict(numerator=1, denominator=1))

    def test_counts_gains_and_losses_in_the_right_direction(self):
        out = confirm_a3.mcnemar(rows([1, 1, 0]), rows([0, 1, 1]))
        self.assertEqual(out['gained'], 1)
        self.assertEqual(out['lost'], 1)

    def test_reproduces_the_a2_observation(self):
        """A2 saw 16 gained and 5 lost; the exact test must give about 1/75."""
        out = confirm_a3.mcnemar(rows([1]*16+[0]*5), rows([0]*16+[1]*5))
        p = out['p_one_sided']
        self.assertEqual((out['gained'], out['lost']), (16, 5))
        self.assertAlmostEqual(p['numerator']/p['denominator'], 0.0133, places=4)

    def test_that_observation_would_not_clear_the_threshold(self):
        out = confirm_a3.mcnemar(rows([1]*16+[0]*5), rows([0]*16+[1]*5))
        p = out['p_one_sided']
        self.assertGreater(p['numerator']*confirm_a3.ALPHA_DENOMINATOR, p['denominator'])

    def test_a_larger_sample_with_the_same_rate_would(self):
        out = confirm_a3.mcnemar(rows([1]*32+[0]*10), rows([0]*32+[1]*10))
        p = out['p_one_sided']
        self.assertLessEqual(p['numerator']*confirm_a3.ALPHA_DENOMINATOR, p['denominator'])

    def test_unpaired_trials_are_refused(self):
        with self.assertRaises(ValueError):
            confirm_a3.mcnemar(rows([1], [7]), rows([1], [9]))


class Protocol(unittest.TestCase):
    def test_second_endpoint_is_declared_in_the_protocol(self):
        self.assertTrue(confirm_a3.PROTOCOL['second_primary_endpoint_on_this_mechanism'])

    def test_alpha_is_not_loosened(self):
        self.assertEqual(confirm_a3.ALPHA_DENOMINATOR, confirm_a2.ALPHA_DENOMINATOR)

    def test_reserve_was_raised_and_is_shared(self):
        self.assertEqual(confirm_a3.RESERVE, 6)
        self.assertGreater(confirm_a3.RESERVE, confirm_a2.RESERVE)
        self.assertIn('nominal arm only', confirm_a3.PROTOCOL['reserve_chosen_with'])

    def test_guesses_bracket_the_true_turn_without_equalling_it(self):
        true_turn = confirm_a3.PROTOCOL['condition']['turn']
        values = sorted(confirm_a3.GUESSES.values())
        self.assertNotIn(true_turn, values)
        self.assertLess(values[0], true_turn)
        self.assertGreater(values[-1], true_turn)

    def test_guessed_arms_carry_no_learning(self):
        for turn in confirm_a3.GUESSES.values():
            payload = confirm_a3.guessed(turn)
            self.assertEqual(payload['samples']['straight'], [0]*4)
            self.assertEqual(payload['samples']['turning'], [0]*4)

    def test_sample_size_is_large_enough_for_the_declared_effect(self):
        self.assertGreaterEqual(confirm_a3.EXAM_ROOMS, 256)

    def test_negative_control_tautology_is_declared_not_hidden(self):
        self.assertTrue(confirm_a3.PROTOCOL['negative_control_is_tautological_for_this_candidate'])
        flat = costs_a2.turn_only(costs_a2.nominal())
        self.assertEqual(flat, costs_a2.nominal())

    def test_rooms_are_disjoint_across_school_exam_and_control(self):
        spent = []
        school, _ = space_a2.suite(confirm_a3.SCHOOL_SEED, 4, spent)
        taken = [r['shape'] for r in school]
        exam, _ = space_a2.suite(confirm_a3.EXAM_SEED, 8, taken)
        taken += [r['shape'] for r in exam]
        control, _ = space_a2.suite(confirm_a3.CONTROL_SEED, 4, taken)
        shapes = taken+[r['shape'] for r in control]
        self.assertEqual(len(set(shapes)), len(shapes))


class Verdict(unittest.TestCase):
    def _clean(self):
        return dict(collisions=0, reserve_violations=0, false_facts=0, imagined_writes=0,
                    calibrations_unchanged=True, energy=100)

    def test_a_dirty_negative_control_invalidates_the_run(self):
        primary = dict(reached=[60, 40], p_one_sided=dict(numerator=1, denominator=10**9))
        good = dict(gained=0, lost=0)
        bad = dict(gained=5, lost=0)
        taught = dict(energy=10)
        nominal = dict(energy=1000)
        guesses = {'guessed_low': dict(gained=5, lost=0)}
        self.assertTrue(confirm_a3.judge(primary, good, taught, self._clean(), nominal, guesses)
                        ['plan_a3_confirmation_pass'])
        self.assertFalse(confirm_a3.judge(primary, bad, taught, self._clean(), nominal, guesses)
                         ['plan_a3_confirmation_pass'])

    def test_reserve_violations_fail_the_hard_constraints(self):
        primary = dict(reached=[60, 40], p_one_sided=dict(numerator=1, denominator=10**9))
        dirty = dict(self._clean(), reserve_violations=1)
        verdict = confirm_a3.judge(primary, dict(gained=0, lost=0), dict(energy=10),
                                   dirty, dict(energy=1000), {})
        self.assertFalse(verdict['hard_constraints'])
        self.assertFalse(verdict['plan_a3_confirmation_pass'])

    def test_beating_a_hand_set_prior_is_reported_but_not_a_pass_criterion(self):
        primary = dict(reached=[60, 40], p_one_sided=dict(numerator=1, denominator=10**9))
        guesses = {'guessed_low': dict(gained=0, lost=5), 'guessed_high': dict(gained=0, lost=5)}
        verdict = confirm_a3.judge(primary, dict(gained=0, lost=0), dict(energy=10),
                                   self._clean(), dict(energy=1000), guesses)
        self.assertFalse(verdict['learning_beyond_a_prior'])
        self.assertTrue(verdict['plan_a3_confirmation_pass'])

    def test_more_missions_is_strict(self):
        primary = dict(reached=[40, 40], p_one_sided=dict(numerator=1, denominator=10**9))
        verdict = confirm_a3.judge(primary, dict(gained=0, lost=0), dict(energy=10),
                                   self._clean(), dict(energy=1000), {})
        self.assertFalse(verdict['more_missions'])

    def test_audit_refuses_a_report_without_a_verdict(self):
        with self.assertRaises(ValueError):
            confirm_a3.audit({'primary': {}})


if __name__ == '__main__':
    unittest.main()
