"""V8: room diversity at fixed budget. Public diagnostic, not selection."""
import unittest

from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.transfer3 import rooms_v8, school_v6, rehearsal_v4
from echoai.nexus0.transfer3.rehearsal import ROOT
from echoai.nexus0.transfer3.rehearsal_v2 import suite

HISTORY = ROOT/'lab/transfer3/rehearsal-v4.json'


class Pool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.history = loads_strict(HISTORY.read_bytes())
        cls.spent = [r['shape'] for r in cls.history['school_rooms'] +
                     cls.history['exam_rooms'] + cls.history['excluded_rooms']]
        cls.extra, _ = suite(rooms_v8.NEW_ROOM_SEED,
                             max(rooms_v8.PROTOCOL['room_counts']) -
                             len(cls.history['school_rooms']), cls.spent)

    def test_new_rooms_are_disjoint_from_every_public_shape(self):
        self.assertTrue({r['shape'] for r in self.extra}.isdisjoint(self.spent))

    def test_new_rooms_are_disjoint_from_each_other(self):
        shapes = [r['shape'] for r in self.extra]
        self.assertEqual(len(set(shapes)), len(shapes))

    def test_run_consumes_exactly_the_declared_number_of_shapes(self):
        self.assertEqual(len(self.extra), 8)


class Nesting(unittest.TestCase):
    def test_room_counts_are_increasing_and_start_at_the_v3_school(self):
        counts = rooms_v8.PROTOCOL['room_counts']
        self.assertEqual(counts, sorted(set(counts)))
        self.assertEqual(counts[0], 4)

    def test_protocol_declares_fixed_budget_and_nesting(self):
        self.assertEqual(rooms_v8.PROTOCOL['budget'], rehearsal_v4.PROTOCOL['budget'])
        self.assertTrue(rooms_v8.PROTOCOL['nested_rooms'])

    def test_protocol_declares_the_tests_are_not_independent(self):
        self.assertFalse(rooms_v8.PROTOCOL['independent_tests'])
        self.assertFalse(rooms_v8.PROTOCOL['learning_in_exam'])
        self.assertFalse(rooms_v8.PROTOCOL['campaign_ready'])

    def test_criterion_is_imported_not_copied(self):
        self.assertIs(rooms_v8.screen, rehearsal_v4.screen)


class FixedBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        history = loads_strict(HISTORY.read_bytes())
        cls.base = [r['seed'] for r in history['school_rooms']]
        spent = [r['shape'] for r in history['school_rooms'] +
                 history['exam_rooms'] + history['excluded_rooms']]
        extra, _ = suite(rooms_v8.NEW_ROOM_SEED, 8, spent)
        cls.twelve = cls.base + [r['seed'] for r in extra]

    def test_every_room_count_spends_the_same_budget(self):
        for seeds in (self.base, self.twelve[:8], self.twelve):
            school = school_v6.train(seeds, rooms_v8.PROTOCOL['budget'])
            self.assertEqual(school['moves'], rooms_v8.PROTOCOL['budget'])

    def test_registered_prediction_four_rooms_is_the_v6_school(self):
        history = loads_strict(HISTORY.read_bytes())
        school = school_v6.train(self.base, rooms_v8.PROTOCOL['budget'])
        self.assertEqual(school['payload'],
                         history['schools']['corrected']['payload'])

    def test_more_rooms_do_not_reduce_coverage(self):
        from echoai.nexus0.transfer3.curve_v7 import coverage
        four = coverage(school_v6.train(self.base, rooms_v8.PROTOCOL['budget'])['counts'])
        twelve = coverage(school_v6.train(self.twelve, rooms_v8.PROTOCOL['budget'])['counts'])
        self.assertGreaterEqual(twelve['sampled_pairs'], four['sampled_pairs'])

    def test_audit_refuses_a_report_without_isolation_field(self):
        with self.assertRaises(ValueError):
            rooms_v8.audit({'isolated': None})


if __name__ == '__main__':
    unittest.main()
