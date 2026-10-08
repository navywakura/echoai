import unittest

from seed import s6_precise_capacity as c
from seed.game_selfimprove import canonical


class PreciseControlTests(unittest.TestCase):
    def test_new_protected_cohort_and_no_exam(self):
        self.assertEqual(len(c.A), 40)
        self.assertEqual(len(c.B), 40)
        self.assertTrue(all(s in range(24120, 24140) for _, s, _, _ in c.B))
        self.assertFalse(c.configuration()["exam_access"])

    def test_same_grammar_available_to_model(self):
        allowed = {canonical(g) for g in c.grammar.conditions()}
        for control in c.controls():
            program = c.Execution.validate(control["candidate"])["program"]
            self.assertEqual(len(program["patches"]), 1)
            self.assertIn(canonical(program["patches"][0]["when"]), allowed)

    def test_reject_unknown_execution_format(self):
        with self.assertRaises(ValueError):
            c.Execution.validate({"format": "python", "program": "open('file')"})


if __name__ == "__main__":
    unittest.main()
