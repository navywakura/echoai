"""V6: pessimistic transfer of unsampled planar actions. Public development."""
import unittest
from pathlib import Path

from echoai.nexus0.compose1.model import state_packet
from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.transfer3 import policy, school_v6, screen_v6
from echoai.nexus0.transfer3.rehearsal import ROOT
from echoai.nexus0.transfer3 import rehearsal_v4

HISTORY = ROOT/'lab/transfer3/rehearsal-v4.json'


def code_of(feature_hex):
    return next(c for c in range(1728) if state_packet(c, 3).hex() == feature_hex)


def row(payload, code):
    return next(r['values'] for r in payload['q'] if r['feature'] == code)


class Export(unittest.TestCase):
    def setUp(self):
        self.code = 5
        self.key = state_packet(self.code, 3).hex()

    def payload(self, values):
        return dict(schema=policy.SCHEMA, q=[dict(feature=self.code, values=values)])

    def test_unsampled_ranks_below_every_sampled_action(self):
        out = school_v6.export_pessimistic(
            self.payload([-5, 9, 0, 0, 0, 0, 0]), {self.key: [2, 1, 0, 0]})
        values = row(out, self.code)
        self.assertEqual(values[:2], [-5, 9])
        self.assertTrue(all(v < min(-5, 9) for v in values[2:4]), values)
        self.assertEqual(values[4:], [0, 0, 0])

    def test_sampled_values_are_never_modified(self):
        base = self.payload([7, -3, 21, -1, 0, 0, 0])
        out = school_v6.export_pessimistic(base, {self.key: [1, 1, 1, 1]})
        self.assertEqual(row(out, self.code), [7, -3, 21, -1, 0, 0, 0])

    def test_missing_row_is_read_as_learned_zeros(self):
        out = school_v6.export_pessimistic(policy.scratch(), {self.key: [1, 0, 0, 0]})
        self.assertEqual(row(out, self.code), [0, -1, -1, -1, 0, 0, 0])

    def test_floor_clamps_at_int8_rail(self):
        out = school_v6.export_pessimistic(
            self.payload([-127, 0, 0, 0, 0, 0, 0]), {self.key: [4, 0, 0, 0]})
        self.assertEqual(row(out, self.code), [-127, -127, -127, -127, 0, 0, 0])

    def test_all_zero_row_is_omitted_like_the_standard_export(self):
        out = school_v6.export_pessimistic(policy.scratch(), {self.key: [1, 1, 1, 1]})
        self.assertEqual(out['q'], [])

    def test_unsampled_feature_is_not_exported(self):
        out = school_v6.export_pessimistic(policy.scratch(), {self.key: [0, 0, 0, 0]})
        self.assertEqual(out['q'], [])

    def test_output_passes_the_frozen_schema(self):
        out = school_v6.export_pessimistic(
            self.payload([-5, 9, 0, 0, 0, 0, 0]), {self.key: [2, 1, 0, 0]})
        policy.validate(out)
        self.assertEqual(out['schema'], 'transfer3-relative-q-v2')

    def test_export_is_a_pure_function_of_payload_and_counts(self):
        base, counts = self.payload([-5, 9, 0, 0, 0, 0, 0]), {self.key: [2, 1, 0, 0]}
        self.assertEqual(school_v6.export_pessimistic(base, counts),
                         school_v6.export_pessimistic(base, counts))

    def test_feature_outside_the_planar_enumeration_is_refused(self):
        with self.assertRaises(ValueError):
            school_v6.export_pessimistic(policy.scratch(), {'00'*16: [1, 0, 0, 0]})


class School(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = loads_strict(HISTORY.read_bytes())
        cls.seeds = [r['seed'] for r in cls.history['school_rooms']]
        cls.school = school_v6.train(cls.seeds, 128)

    def test_spends_exactly_its_budget(self):
        self.assertEqual(self.school['moves'], 128)
        self.assertEqual(sum(sum(r) for r in self.school['counts'].values()), 128)

    def test_one_executed_move_is_one_sample(self):
        self.assertEqual(sum(e['moves'] for e in self.school['episodes']), 128)

    def test_registered_prediction_repairs_do_not_move_these_rooms(self):
        self.assertEqual(self.school['payload'],
                         self.history['schools']['corrected']['payload'])

    def test_no_failure_occurs_so_the_bonus_never_fires(self):
        self.assertEqual(self.school['failure_bonus_applied'], 0)
        self.assertTrue(self.school['terminal_updates'] > 0)

    def test_school_is_clean(self):
        for episode in self.school['episodes']:
            self.assertEqual(episode['collisions'], 0)
            self.assertEqual(episode['reserve_violations'], 0)
            self.assertEqual(episode['ingestions'], episode['visits'])

    def test_budget_must_be_spendable(self):
        with self.assertRaises(ValueError):
            school_v6.train([], 128)
        with self.assertRaises(ValueError):
            school_v6.train(self.seeds, 0)

    def test_pessimistic_export_keeps_every_sampled_entry(self):
        base = self.school['payload']
        out = school_v6.export_pessimistic(base, self.school['counts'])
        for r in base['q']:
            sampled = self.school['counts'][state_packet(r['feature'], 3).hex()]
            floored = row(out, r['feature'])
            for action in range(4):
                if sampled[action]:
                    self.assertEqual(floored[action], r['values'][action])

    def test_pessimistic_export_orders_unknown_last(self):
        out = school_v6.export_pessimistic(self.school['payload'], self.school['counts'])
        checked = 0
        for r in out['q']:
            sampled = self.school['counts'][state_packet(r['feature'], 3).hex()]
            known = [r['values'][a] for a in range(4) if sampled[a]]
            unknown = [r['values'][a] for a in range(4) if not sampled[a]]
            if unknown and min(known) > -127:
                checked += 1
                self.assertTrue(max(unknown) < min(known), r)
        self.assertTrue(checked > 0)


class Harness(unittest.TestCase):
    def test_criterion_is_imported_not_copied(self):
        self.assertIs(screen_v6.screen, rehearsal_v4.screen)
        self.assertEqual(screen_v6.PROTOCOL['budget'], rehearsal_v4.PROTOCOL['budget'])

    def test_protocol_declares_no_exam_learning_and_no_campaign(self):
        self.assertFalse(screen_v6.PROTOCOL['learning_in_exam'])
        self.assertFalse(screen_v6.PROTOCOL['campaign_ready'])
        self.assertEqual(screen_v6.PROTOCOL['arms'], ['scratch', 'baseline', 'pessimistic'])

    def test_audit_refuses_a_report_without_isolation_field(self):
        with self.assertRaises(ValueError):
            screen_v6.audit({'isolated': 'yes'})


if __name__ == '__main__':
    unittest.main()
