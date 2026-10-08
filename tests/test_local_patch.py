import importlib.util
import json
import tempfile
from pathlib import Path
import unittest

from echo_arc import local_patch as p
from echo_arc.local_patch_grammar import Grammar


class Boundary(unittest.TestCase):
    def test_invalid_data_and_global_defaults_are_rejected(self):
        invalid = [{"defaults": {}, "rules": []}, {"patches": [{"when": {}, "set": {"HOLD": 20}}]},
                   {"patches": [{"when": {"seed": ["eq", 0]}, "set": {"HOLD": 20}}]},
                   {"patches": [{"when": {"motor_ready": ["eq", 1]}, "set": {"HOLD": True}}]},
                   {"patches": [{"when": {"motor_ready": ["eq", 1]}, "set": {"HOLD": 20, "BABBLE": 2}}]}]
        for value in invalid:
            with self.assertRaises(ValueError):
                p.validate(value)
        with self.assertRaises(ValueError):
            p.parse('{"patches":[],"patches":[]}')

    def test_append_and_conditional_composition_preserve_earlier_repairs(self):
        one = {"patches": [{"when": {"motor_ready": ["eq", 1]}, "set": {"HOLD": 10}}]}
        two = {"patches": [{"when": {"stagnation": ["ge", 8]}, "set": {"HOLD": 20}}]}
        joined = p.append(one, two)
        self.assertEqual(one["patches"], joined["patches"][:1])
        self.assertEqual(p.settings(joined, {"motor_ready": 0, "stagnation": 0}), ({}, []))
        self.assertEqual(p.settings(joined, {"motor_ready": 1, "stagnation": 9}), ({"HOLD": 20}, [0, 1]))

    def test_grammar_is_complete_and_one_parameter_only(self):
        value = {"patches": [{"when": {"motor_ready": ["eq", 1], "stagnation": ["ge", 8]},
                              "set": {"PROBE_STRATEGY": 2}}]}
        tokens = list(json.dumps(value, separators=(',', ':')).encode())
        grammar = Grammar(lambda t: list(t.encode()), 256)
        for i, token in enumerate(tokens):
            self.assertIn(token, grammar.allowed(tokens[:i]))
            self.assertNotIn(256, grammar.allowed(tokens[:i]))
        self.assertIn(256, grammar.allowed(tokens))
        self.assertEqual(p.parse(bytes(tokens).decode()), p.validate(value))


@unittest.skipUnless(importlib.util.find_spec("numpy") and importlib.util.find_spec("arcengine"),
                     "requires managed ARC environment")
class NativeParity(unittest.TestCase):
    def test_empty_inactive_and_active_observer_parity(self):
        from echo_arc import runner, agent
        from echo_arc.temporal_runner import play
        from echo_arc.observe import Journal
        from seed import arc3gym as gym
        registry = dict(runner.AGENTS)
        version = gym.VERSION
        try:
            inactive = {"patches": [{"when": {"level": ["ge", 100]}, "set": {"PROBE_STRATEGY": 2}}]}
            active = {"patches": [{"when": {"motor_ready": ["eq", 1]}, "set": {"PROBE_STRATEGY": 1}}]}
            for v, seed in ((2, 0), (3, 0), (3, 4)):
                gym.VERSION = v
                agent._COMP_CACHE.clear()
                expected = play(gym.GymEnv(seed), 160, 12345)
                for program in (p.EMPTY, inactive):
                    agent._COMP_CACHE.clear()
                    actual = p.play(gym.GymEnv(seed), 160, 12345, program)
                    actual.pop("patch_hits", None)
                    self.assertEqual(actual, expected)
            with tempfile.TemporaryDirectory() as temp:
                gym.VERSION = 3
                agent._COMP_CACHE.clear()
                direct = p.play(gym.GymEnv(0), 180, 12345, active)
                agent._COMP_CACHE.clear()
                log = Journal(Path(temp) / "arc-decisions.jsonl")
                try:
                    observed = p.play(gym.GymEnv(0), 180, 12345, active, log)
                finally:
                    log.close()
                self.assertEqual(direct, observed)
                self.assertGreater(sum(direct["patch_hits"]), 0)
            self.assertEqual(registry, runner.AGENTS)
        finally:
            gym.VERSION = version
            agent._COMP_CACHE.clear()
