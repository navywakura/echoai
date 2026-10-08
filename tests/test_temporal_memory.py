"""Semantic properties of order/count memory, runnable with system Python."""
import unittest

from echo_arc.temporal_memory import CountMemory, OrderMemory


class OrderTests(unittest.TestCase):
    def test_order_is_directed_and_requires_observed_effect(self):
        m = OrderMemory()
        m.enter(8)
        m.enter(4)
        self.assertEqual(m.candidates(), [])
        m.reset()
        m.enter(4)
        m.enter(8, effect=True)
        self.assertEqual(m.candidates(), [(4, 8)])
        self.assertEqual(m.report()[0]["status"], "proposed")

    def test_repeated_support_is_from_distinct_episodes_and_conflicts_are_kept(self):
        m = OrderMemory()
        for _ in range(3):
            m.enter(4)
            m.enter(8, effect=True)
        self.assertEqual(m.report()[0]["supports"], 1)
        m.reset()
        m.enter(4)
        m.enter(8, effect=True)
        self.assertEqual(m.report()[0]["status"], "repeated")
        m.reset()
        m.enter(4)
        m.enter(8)
        self.assertEqual(m.report()[0]["conflicts"], 1)
        self.assertEqual(list(m.history), [4, 8])
        m.reset()
        m.enter(4)
        m.enter(8)
        self.assertEqual(m.candidates(), [])

    def test_rule_storage_is_bounded_and_reset_retains_rules_only(self):
        m = OrderMemory()
        for k in range(m.MAX_RULES + 10):
            m.reset()
            m.enter(k)
            m.enter(k + 1, effect=True)
        self.assertEqual(len(m.rules), m.MAX_RULES)
        m.reset()
        self.assertEqual(list(m.history), [])
        self.assertEqual(len(m.rules), m.MAX_RULES)


class CountTests(unittest.TestCase):
    def test_standing_and_blocked_actions_do_not_count_as_entries(self):
        m = CountMemory()
        self.assertEqual(m.position((10, 20), 7), 1)
        for _ in range(20):
            self.assertIsNone(m.position((10, 20), 7))
        m.position(None)
        self.assertEqual(m.position((10, 20), 7), 2)

    def test_threshold_is_learned_for_two_four_and_five_entries(self):
        for threshold in (2, 4, 5):
            with self.subTest(threshold=threshold):
                m = CountMemory()
                self.assertIsNone(m.threshold(7))
                for n in range(1, threshold + 1):
                    m.position(None)
                    m.position((10, 20), 7, effect=n == threshold)
                self.assertEqual(m.threshold(7), threshold)
                m.reset()
                self.assertEqual(m.counts, {})
                self.assertEqual(m.threshold(7), threshold)

    def test_instances_are_separate_and_mixed_entries_do_not_prove_a_threshold(self):
        m = CountMemory()
        m.position((10, 20), 7)
        m.position((30, 40), 7)
        m.position((10, 20), 7, effect=True)
        self.assertEqual(m.counts[(10, 20)], 2)
        self.assertEqual(m.counts[(30, 40)], 1)
        self.assertIsNone(m.threshold(7))
        m.reset()
        m.position((10, 20), 4)
        m.position((30, 40), 7, effect=True)
        self.assertIsNone(m.threshold(7))

    def test_partial_coverage_cannot_certify_a_threshold_and_contradiction_abstains(self):
        m = CountMemory(complete=False)
        m.position((1, 2), 7, effect=True)
        self.assertIsNone(m.threshold(7))
        m.reset()
        m.position((1, 2), 7)
        m.position(None)
        m.position((1, 2), 7, effect=True)
        self.assertEqual(m.threshold(7), 2)
        m.reset()
        m.position((1, 2), 7)
        m.position(None)
        m.position((1, 2), 7)
        self.assertIsNone(m.threshold(7))
        self.assertEqual(m.report()[0]["conflicts"], 1)


if __name__ == "__main__":
    unittest.main()
