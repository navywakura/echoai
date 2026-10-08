"""B3 data boundary and private native policy integration."""
import importlib.util
import json
import unittest

from echo_arc import strategy
from echo_arc import temporal_policy as policy
from echo_arc.temporal_policy_grammar import Grammar


class PolicyBoundary(unittest.TestCase):
    def test_unknown_fields_bounds_boolean_and_duplicates_are_rejected(self):
        for defaults in ({"seed": 0}, {"ENTRY_PROBE_LIMIT": 17}, {"ORDER_ENABLED": True},
                         {"AFTER_EFFECT_POLICY": 3}, {"MIN_EVIDENCE": 1}):
            with self.assertRaises(ValueError):
                policy.validate({"defaults": defaults, "rules": []})
        with self.assertRaises(ValueError):
            policy.parse('{"defaults":{},"defaults":{},"rules":[]}')
        with self.assertRaises(ValueError):
            policy.validate({"defaults": {}, "rules": [{"when": {"family": ["eq", 1]}, "set": {}}]})
        self.assertNotIn("ENTRY_PROBE_LIMIT", strategy.LIMITS)
        self.assertEqual(policy.validate(policy.EMPTY), policy.EMPTY)

    def test_new_grammar_ends_only_after_complete_valid_data(self):
        grammar = Grammar(lambda s: list(s.encode()), 256)
        data = {"defaults": policy.DEFAULTS,
                "rules": [{"when": {"temporal_open": ["eq", 1]}, "set": {"AFTER_EFFECT_POLICY": 2}}]}
        raw = json.dumps(data, separators=(",", ":")).encode()
        prefix = []
        for token in raw:
            self.assertIn(token, grammar.allowed(prefix))
            self.assertNotIn(256, grammar.allowed(prefix))
            prefix.append(token)
        self.assertIn(256, grammar.allowed(prefix))
        self.assertEqual(policy.parse(raw.decode()), policy.validate(data))
        self.assertEqual(grammar.allowed(prefix + [256, 0]), [256])


@unittest.skipUnless(importlib.util.find_spec("arcengine") and importlib.util.find_spec("numpy"),
                     "requires separately managed ARC environment")
class NativePolicy(unittest.TestCase):
    def test_empty_policy_and_observation_leave_native_behavior_identical(self):
        from echo_arc import agent, runner
        from echo_arc.temporal_runner import play
        from echo_arc.temporal_agent import Arc3EchoV58
        from echo_arc.observe import Journal
        from seed import arc3gym as gym
        from pathlib import Path
        import tempfile
        old = gym.VERSION
        registry = dict(runner.AGENTS)
        try:
            gym.VERSION = 3
            self.assertIs(policy.agent_class(policy.EMPTY), Arc3EchoV58)
            for seed in (0, 4):
                agent._COMP_CACHE.clear()
                expected = play(gym.GymEnv(seed), 180, 12345)
                agent._COMP_CACHE.clear()
                actual = policy.play(gym.GymEnv(seed), 180, 12345, policy.EMPTY)
                self.assertEqual(actual, expected)
            candidate = {"defaults": {"ENTRY_PROBE_LIMIT": 4, "PROBE_STRATEGY": 1}, "rules": []}
            with tempfile.TemporaryDirectory() as tmp:
                agent._COMP_CACHE.clear()
                direct = policy.play(gym.GymEnv(0), 180, 12345, candidate)
                agent._COMP_CACHE.clear()
                journal = Journal(Path(tmp) / "decisions.jsonl")
                try:
                    observed = policy.play(gym.GymEnv(0), 180, 12345, candidate, journal)
                finally:
                    journal.close()
                self.assertEqual(observed, direct)
            self.assertEqual(registry, runner.AGENTS)
        finally:
            gym.VERSION = old


if __name__ == "__main__":
    unittest.main()
