"""Meaningful negative cases for the model/data boundary, without game dependencies."""
import copy
import unittest
from echo_arc import strategy as s


class StrategyBoundaryTests(unittest.TestCase):
    def test_no_code_or_hidden_identifiers(self):
        for key in ('__class__', 'game_id', 'seed', 'family', 'colour', 'position', 'open'):
            policy = copy.deepcopy(s.EMPTY)
            policy['defaults'][key] = 1
            with self.assertRaises(ValueError):
                s.validate(policy)
            policy = {'defaults': {}, 'rules': [{'when': {key: ['eq', 1]}, 'set': {'HOLD': 20}}]}
            with self.assertRaises(ValueError):
                s.validate(policy)

    def test_bounds_and_types(self):
        for value in (True, 1.0, -1, 101, '40', None):
            with self.assertRaises(ValueError):
                s.validate({'defaults': {'HOLD': value}, 'rules': []})
        with self.assertRaises(ValueError):
            s.parse('{"defaults":{},"defaults":{"HOLD":1},"rules":[]}')
        with self.assertRaises(ValueError):
            s.parse('import os; os.system("true")')
        with self.assertRaises(ValueError):
            s.validate({'defaults': {}, 'rules': [{'when': {'level': ['ge', -1]}, 'set': {}}]})

    def test_history_rule_expires_and_order_is_explicit(self):
        policy = s.validate({'defaults': {'HOLD': 40}, 'rules': [
            {'when': {'reset_known': ['eq', 1]}, 'set': {'HOLD': 70}},
            {'when': {'stagnation': ['ge', 20]}, 'set': {'HOLD': 10}}]})
        self.assertEqual(s.settings(policy, {'reset_known': 1, 'stagnation': 0}), {'HOLD': 70})
        self.assertEqual(s.settings(policy, {'reset_known': 1, 'stagnation': 30}), {'HOLD': 10})
        self.assertEqual(s.settings(policy, {'reset_known': 0, 'stagnation': 0}), {'HOLD': 40})

    def test_canonical_hash_and_no_mutable_alias(self):
        p = {'defaults': {'HOLD': 60, 'BABBLE': 2}, 'rules': []}
        v = s.validate(p)
        self.assertEqual(s.digest(p), s.digest({'rules': [], 'defaults': {'BABBLE': 2, 'HOLD': 60}}))
        p['defaults']['HOLD'] = 0
        self.assertEqual(v['defaults']['HOLD'], 60)


if __name__ == '__main__':
    unittest.main()
