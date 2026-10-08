import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import random

from echoai.seed import selfimprove as s6
from echoai.seed.learn import Library


class ProposalSafetyTests(unittest.TestCase):
    def test_module_execution_is_rejected(self):
        self.assertTrue(s6.check_code("def op(grid):\n    return grid\nwhile True:\n    pass"))
        self.assertTrue(s6.check_code("def op(grid, c=sum(range(1000000000))):\n    return grid"))

    def test_deadline_cannot_be_swallowed_by_except_exception(self):
        code = "def op(grid):\n    try:\n        while True:\n            pass\n    except Exception:\n        return grid"
        fn, _ = s6.compile_op(code)
        with self.assertRaisesRegex(ValueError, "ProposalTimeout"):
            fn(((1,),))

    def test_computed_exception_types_and_persistent_attributes_are_rejected(self):
        code = "def op(grid):\n    try:\n        while True:\n            pass\n    except ValueError.mro()[2]:\n        return grid"
        self.assertTrue(s6.check_code(code))
        self.assertTrue(s6.check_code(code.replace("try:", "Exception = ValueError.mro()[2]\n    try:").replace("except ValueError.mro()[2]", "except Exception")))
        self.assertTrue(s6.check_code("def helper(Exception):\n    return 1\ndef op(grid):\n    return grid"))
        self.assertTrue(s6.check_code("def op(grid):\n    op.calls = 1\n    return grid"))

    def test_unsafe_initialization_is_rejection(self):
        with self.assertRaises(ValueError):
            s6.compile_op("def op(grid, c=missing):\n    return grid")

    def test_output_is_bounded_and_rectangular(self):
        for expr in ("[[1] * 31]", "[[1], [1, 2]]", "[[10]]"):
            fn, _ = s6.compile_op("def op(grid):\n    return " + expr)
            with self.assertRaises(ValueError):
                fn(((1,),))

    def test_operation_that_always_fails_is_v2_failure(self):
        with self.assertRaises(ValueError):
            s6.deterministic("def op(grid):\n    raise ValueError('no')", [((1,),)])

    def test_isolated_check_accepts_identity_and_rejects_large_allocation(self):
        ok, reason = s6.deterministic_check("def op(grid):\n    return grid", [((1,),)])
        self.assertTrue(ok, reason)
        ok, _ = s6.deterministic_check("def op(grid):\n    return [[1] * 1000000000]", [((1,),)])
        self.assertFalse(ok)


class RecoveryTests(unittest.TestCase):
    def test_v3_does_not_credit_tasks_the_base_already_solves(self):
        state = {'failed_A': {'a', 'b', 'c'}}
        with patch.object(s6, 'compile_op'), patch.object(s6, 'deterministic_check', return_value=(True, '')), \
             patch.object(s6.gym, 'load', return_value={'train': [{'input': [[1]]}]}), \
             patch.object(s6, 'solve_many', side_effect=[{'a'}, {'a', 'b'}, {'a', 'b'}]):
            verdict, why, new = s6.verify('def op(grid):\n    return grid', 'candidate', ['a'], state,
                                        [], Library(), 1, random.Random(0), [], 0)
        self.assertEqual(verdict, 'rejected')
        self.assertEqual(new, set())
        self.assertIn('only 0 new', why)

    def test_baseline_measures_current_library_instead_of_old_journal(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(s6, 'ROOT', Path(td)), \
                 patch.object(s6, 'partition', return_value={'A': ['a'], 'B': ['b']}), \
                 patch.object(s6.sandbox, 'load_library', return_value=Library()), \
                 patch.object(s6, 'solve_many', side_effect=[{'a'}, {'b'}]), \
                 patch.object(s6.sandbox, 'verified_programs', side_effect=AssertionError('old journal used')):
                s6.baseline(1)
                row = json.loads((Path(td) / 'baseline.json').read_text())
        self.assertEqual(row['A_solved'], ['a'])
        self.assertEqual(row['B_solved'], ['b'])

    def test_generalization_screens_the_unsolved_task_shown_in_the_prompt(self):
        state = {"failed_A": {"pending"}, "accepted": [("old", "def op(grid):\n    return grid", ["solved1", "solved2"])]}
        with patch.object(s6, "task_text", side_effect=lambda t: "task " + t):
            prompt, tids = s6.build_request("P3", state, random.Random(0))
        self.assertIn("task pending", prompt)
        self.assertEqual(tids, ["pending"])

    def harness(self, root, proposer, verifier):
        stack = ExitStack()
        stubs = {
            "ROOT": root, "V4_SAMPLE": 2, "mock_proposer": proposer,
            "partition": lambda: {"A": ["a", "b", "c"], "B": ["d", "e"]},
            "shape_key": lambda t: "same", "protected_hashes": lambda: {"fixed": "abc"},
            "solve_many": lambda *a: set(), "verify": verifier,
            "build_request": lambda k, st, rng: ("%s:%s:%s" % (k, rng.random(), sorted(st["asked"])), ["a"]),
            "near_miss": lambda *a: (1., []),
        }
        for name, value in stubs.items():
            stack.enter_context(patch.object(s6, name, value))
        stack.enter_context(patch.object(s6.sandbox, "load_library", return_value=Library()))
        stack.enter_context(patch.object(s6.sandbox, "level_of", return_value="S0"))
        stack.enter_context(patch.object(s6.sandbox, "_set_level"))
        stack.enter_context(patch.object(s6.sandbox, "verified_programs", return_value={}))
        stack.enter_context(patch.object(s6.gym, "load", return_value={}))
        root.mkdir(parents=True, exist_ok=True)
        (root / "baseline.json").write_text(json.dumps({"A_solved": [], "B_solved": []}))
        return stack

    def test_missing_answer_and_exact_resume_without_regeneration(self):
        def make_proposer():
            calls = []
            def proposer(prompt):
                calls.append(prompt)
                return None if len(calls) == 1 else "```python\ndef op(grid):\n    return grid\n```"
            return proposer, calls
        reject = lambda *a: ("rejected", "V3: no new tasks", set())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            normal, normal_calls = make_proposer()
            with self.harness(root / "normal", normal, reject):
                s6.run("echo", "mock", 4, 2, 1, "test")
                expected = s6._events("echo")
            interrupted, interrupted_calls = make_proposer()
            attempts = []
            def fail_once(*args):
                attempts.append(1)
                if len(attempts) == 2:
                    raise RuntimeError("simulated verifier interruption")
                return reject(*args)
            with self.harness(root / "resumed", interrupted, fail_once):
                with self.assertRaises(RuntimeError):
                    s6.run("echo", "mock", 4, 2, 1, "test")
            with self.harness(root / "resumed", interrupted, reject):
                s6.run("echo", "mock", 4, 2, 1, "test")
                actual = s6._events("echo")
                self.assertEqual(json.loads((s6.ROOT / "echo/completed.json").read_text())["calls"], 4)
            self.assertEqual(normal_calls, interrupted_calls)
            scrub = lambda rows: [{k: v for k, v in e.items() if k not in ("hash", "prev", "t")} for e in rows]
            self.assertEqual(scrub(expected), scrub(actual))
            self.assertEqual(actual[0]["verdict"], "no answer")


if __name__ == "__main__":
    unittest.main()
