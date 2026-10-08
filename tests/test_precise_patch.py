import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from echo_arc import precise_patch as p
from echo_arc.precise_patch_grammar import Grammar


class Boundary(unittest.TestCase):
    def test_reject_private_data_code_duplicates_and_wrong_types(self):
        valid = {"patches": [{"when": {"reset_known": ["eq", 1], "pending_effect": ["eq", 0],
                                       "stagnation": ["ge", 8]}, "set": {"COOLDOWN_CAP": 20}}]}
        p.validate(valid)
        for key in ("seed", "family", "reward", "solver", "password"):
            bad = copy.deepcopy(valid)
            bad["patches"][0]["when"] = {key: ["eq", 1]}
            with self.assertRaises(ValueError):
                p.validate(bad)
        for value in (True, -1, 101, "exec('x')"):
            bad = copy.deepcopy(valid)
            bad["patches"][0]["set"]["COOLDOWN_CAP"] = value
            with self.assertRaises(ValueError):
                p.validate(bad)
        with self.assertRaises(ValueError):
            p.parse('{"patches":[],"patches":[]}')

    def test_cooldown_operation_never_increases_wait_or_changes_unrelated_memory(self):
        actor = SimpleNamespace(hold=40, pending="trial", rule={1: [0, 2]})
        p.apply_cooldown(actor, {})
        self.assertEqual(actor.hold, 40)
        p.apply_cooldown(actor, {"COOLDOWN_CAP": 20})
        self.assertEqual(actor.hold, 20)
        p.apply_cooldown(actor, {"COOLDOWN_CAP": 80})
        self.assertEqual(actor.hold, 20)
        self.assertEqual(actor.pending, "trial")
        self.assertEqual(actor.rule, {1: [0, 2]})

    def test_composition_changes_only_matching_parameters(self):
        one = {"patches": [{"when": {"reset_known": ["eq", 1], "pending_effect": ["eq", 0]},
                             "set": {"HOLD": 20}}]}
        two = {"patches": [{"when": {"reset_known": ["eq", 1], "stagnation": ["ge", 8]},
                             "set": {"COOLDOWN_CAP": 10}}]}
        joined = p.append(one, two)
        self.assertEqual(p.settings(joined, {"reset_known": 0, "pending_effect": 0, "stagnation": 9}), ({}, []))
        self.assertEqual(p.settings(joined, {"reset_known": 1, "pending_effect": 1, "stagnation": 9}),
                         ({"COOLDOWN_CAP": 10}, [1]))

    def test_model_can_express_three_guards_and_new_operation(self):
        text = '{"patches":[{"when":{"pending_effect":["eq",0],"reset_known":["eq",1],"stagnation":["ge",8]},"set":{"COOLDOWN_CAP":20}}]}'
        tokens = list(text.encode())
        grammar = Grammar(lambda value: list(value.encode()), 256)
        for i, token in enumerate(tokens):
            self.assertIn(token, grammar.allowed(tokens[:i]))
            self.assertNotIn(256, grammar.allowed(tokens[:i]))
        self.assertIn(256, grammar.allowed(tokens))
        self.assertEqual(p.parse(text)["patches"][0]["set"], {"COOLDOWN_CAP": 20})


@unittest.skipUnless(importlib.util.find_spec("numpy") and importlib.util.find_spec("arcengine"), "managed ARC environment")
class Native(unittest.TestCase):
    def test_native_inactive_and_active_passive_parity(self):
        from echo_arc import agent, runner
        from echo_arc.temporal_runner import play
        from echo_arc.observe import Journal
        from echo_arc.precise_observe import PreciseRecorder, PreciseObservedAgent
        from echo_arc.temporal_bench import _gym_env
        from types import FunctionType
        inactive = {"patches": [{"when": {"level": ["ge", 100]}, "set": {"COOLDOWN_CAP": 0}}]}
        active = {"patches": [{"when": {"reset_known": ["eq", 1]}, "set": {"COOLDOWN_CAP": 20}}]}
        for program in (p.EMPTY, inactive, active):
            def factory(_):
                return p.agent_class(program)
            native = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=factory),
                                  runner.play.__name__, runner.play.__defaults__)
            agent._COMP_CACHE.clear()
            actual = native(_gym_env(3, 19), 240, 12345, agent_name="precise")
            if program in (p.EMPTY, inactive):
                agent._COMP_CACHE.clear()
                self.assertEqual(actual, play(_gym_env(3, 19), 240, 12345))
            with tempfile.TemporaryDirectory() as temp:
                recorder = PreciseRecorder(Journal(Path(temp) / "arc-decisions.jsonl"))
                def observed_factory(_):
                    def create(*args, **kwargs):
                        actor = p.agent_class(program)(*args, **kwargs)
                        recorder.bind_actor(actor)
                        return PreciseObservedAgent(actor, recorder)
                    return create
                observed = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=observed_factory),
                                        runner.play.__name__, runner.play.__defaults__)
                agent._COMP_CACHE.clear()
                try:
                    replay = observed(_gym_env(3, 19), 240, 12345, agent_name="precise")
                finally:
                    recorder.close()
                self.assertEqual(actual, replay)
                records = [json.loads(line) for line in (Path(temp) / "arc-decisions.jsonl").read_text().splitlines()]
                decisions = [r for r in records if r["kind"] == "decision"]
                self.assertTrue(decisions)
                self.assertIn("pending_effect", decisions[-1]["repair_features"])
                if program == active:
                    self.assertGreater(sum(recorder.actor.patch_hits), 0)
