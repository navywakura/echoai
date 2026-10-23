"""The proposer supplies data; authority and execution remain local."""
import unittest

from echo5.budget import Budget, BudgetExceeded
from echo5 import programs as p


class ProgramTests(unittest.TestCase):
    def test_geometry_composition(self):
        result = p.execute({'steps': [{'op': 'rot90'}, {'op': 'fliplr'}]},
                           [[1, 2, 3], [4, 5, 6]], budget=Budget(10000))
        self.assertEqual(result, ((1, 4), (2, 5), (3, 6)))

    def test_relational_extract_then_geometry(self):
        rows = [[0]*6, [0, 2, 0, 4, 0, 0], [0, 2, 2, 0, 0, 0], [0]*6]
        proposal = {'steps': [{'op': 'relate', 'role': 'largest', 'relation': 'all', 'effect': 'extract'}, {'op': 'rot90'}]}
        self.assertEqual(p.execute(proposal, rows, budget=Budget(10000)), ((2, 2), (2, 0)))

    def test_unsupported_authority_fields_rejected_at_every_level(self):
        for proposal in (
            {'steps': [{'op': 'rot90'}], 'test_verified': True},
            {'steps': [{'op': 'rot90', 'verified': True}]},
            {'steps': [{'op': 'exec', 'code': 'raise RuntimeError()'}]},
            {'steps': [{'op': 'relate', 'role': 'color_2', 'relation': 'right', 'effect': 'recolor'}]},
            {'steps': [{'op': 'call', 'name': '__import__', 'authority': 'judge'}]},
        ):
            budget = Budget(10000)
            with self.assertRaises(ValueError):
                p.parse_program(proposal, budget=budget)
            self.assertGreater(budget.used, 0)

    def test_expansion_rejects_cycles_and_limits(self):
        class Definitions:
            def resolve(self, name, *, budget):
                return {'steps': [{'op': 'call', 'name': name}]}
        with self.assertRaises(ValueError):
            p.expand({'steps': [{'op': 'call', 'name': 'loop'}]}, library=Definitions(), budget=Budget(10000))
        with self.assertRaises(ValueError):
            p.parse_program({'steps': [{'op': 'rot90'}]*1000}, budget=Budget(10000))

    def test_unknown_concept_and_failed_execution_are_charged(self):
        budget = Budget(10000)
        with self.assertRaises(ValueError):
            p.execute({'steps': [{'op': 'call', 'name': 'missing'}]}, [[0]], budget=budget)
        self.assertGreater(budget.used, 0)
        before = budget.used
        with self.assertRaises(ValueError):
            p.execute({'steps': [{'op': 'relate', 'role': 'smallest', 'relation': 'all', 'effect': 'extract'}]},
                      [[0, 0, 0, 0, 0], [0, 2, 0, 3, 0], [0]*5], budget=budget)
        self.assertGreater(budget.used, before)

    def test_exhaustion_is_not_converted_to_invalid_program(self):
        with self.assertRaises(BudgetExceeded):
            p.execute({'steps': [{'op': 'rot90'}]}, [[1, 2]], budget=Budget(0))

    def test_serializable_proposal_roundtrip(self):
        proposal = {'steps': [{'op': 'rot90'}]}
        self.assertEqual(p.parse_program(proposal, budget=Budget(1000)).to_dict(), proposal)


if __name__ == '__main__':
    unittest.main()
