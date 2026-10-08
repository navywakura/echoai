import random
import unittest
from echo_arc.strategy import parse
from echo_arc.strategy_grammar import Grammar, PARAMETERS


class GrammarTests(unittest.TestCase):
    def test_every_generated_branch_is_complete_bounded_json(self):
        grammar = Grammar(lambda text: list(text.encode()), 999)
        rng = random.Random(51)
        seen_conditions, seen_parameters = set(), set()
        for _ in range(80):
            prefix = []
            for step in range(600):
                token = rng.choice(grammar.allowed(prefix))
                if token == 999:
                    break
                prefix.append(token)
            else:
                self.fail('grammar did not terminate within the generation cap')
            policy = parse(bytes(prefix).decode())
            self.assertEqual(grammar.allowed(prefix + [999, 998, 998]), [999])
            self.assertEqual(set(policy['defaults']), set(PARAMETERS))
            self.assertEqual(len(policy['rules']), 1)
            seen_conditions.update(policy['rules'][0]['when'])
            seen_parameters.update(policy['rules'][0]['set'])
        self.assertEqual(seen_parameters, set(PARAMETERS))
        self.assertGreaterEqual(len(seen_conditions), 5)

    def test_forbidden_prefix_and_premature_end_fail(self):
        grammar = Grammar(lambda text: list(text.encode()), 999)
        with self.assertRaises(ValueError):
            grammar.allowed([999])
        with self.assertRaises(ValueError):
            grammar.allowed(list(b'{"defaults":{"open":1}'))
        self.assertNotIn(999, grammar.allowed([]))


if __name__ == '__main__':
    unittest.main()
