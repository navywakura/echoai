import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch as mock_patch

from echo_arc import repair_diagnostics as d, precise_patch as p
from seed import s6b8 as s
from seed.s6b8_exam import checks


def proposal(parameter="HOLD", value=40, **guards):
    return {"patches": [{"when": guards or {"reset_pending": ["eq", 1]}, "set": {parameter: value}}]}


def row(**features):
    f = {key: 0 for key in p.FEATURES}
    f.update(features)
    return {"origin": "DEVELOPMENT_A", "levels_completed": 4,
            "diagnostics": {"feature_counts": [{"features": f, "count": 10}],
                            "counts": {"reset_trial": 2}, "witnesses": {}}}


class Diagnostics(unittest.TestCase):
    def test_native_value_and_inactive_guard_are_distinct_no_effects(self):
        native = d.applicability(proposal(), p.EMPTY, [row(reset_pending=1)])
        inactive = d.applicability(proposal(value=10), p.EMPTY, [row()])
        self.assertEqual(native["matching_decisions"], 10)
        self.assertEqual(native["setting_changes"], 0)
        self.assertEqual(inactive["matching_decisions"], 0)

    def test_active_clamp_compares_with_current_policy_and_wait(self):
        current = proposal("COOLDOWN_CAP", 10, body_known=["eq", 1])
        rows = [row(body_known=1, hold_remaining=8)]
        self.assertEqual(d.applicability(proposal("COOLDOWN_CAP", 20, body_known=["eq", 1]), current, rows)["setting_changes"], 0)
        self.assertEqual(d.applicability(proposal("COOLDOWN_CAP", 4, body_known=["eq", 1]), current, rows)["setting_changes"], 10)
        self.assertEqual(d.applicability(proposal(value=40), proposal(value=20), [row(reset_pending=1)])["setting_changes"], 10)

    def test_future_hold_difference_is_not_consumption_during_active_wait(self):
        value = d.applicability(proposal(value=10, body_known=["eq", 1]), p.EMPTY,
                                [row(body_known=1, hold_remaining=30)])
        self.assertEqual(value["setting_changes"], 10)
        self.assertEqual(value["possible_consumption"], 0)

    def test_protected_rows_cannot_become_evidence(self):
        private = dict(row(), origin="PROTECTED_B", secret="reserved-label")
        with self.assertRaises(AssertionError):
            d.applicability(proposal(), p.EMPTY, [private])
        with self.assertRaises(AssertionError):
            d.select_evidence([private], "echo", [], 0)

    def test_feedback_drops_protected_details_and_freeform_reason(self):
        event = {"verdict": "V4", "proposal": proposal(value=0), "A": {"gain": 8},
                 "B": {"secret_grid": [[9]], "loss_indices": [12]}, "reason": "reserved-label"}
        out = d.feedback([event])
        self.assertEqual(out[0]["training"], {"gain": 8})
        self.assertTrue(out[0]["protected_rejection"])
        self.assertNotIn("secret", str(out))
        self.assertNotIn("reserved-label", str(out))

    def test_selector_prioritizes_observed_opportunities_without_private_ids(self):
        blocked = dict(row(), levels_completed=0, seed=99, family="secret-family")
        blocked["diagnostics"]["counts"] = {}
        near = dict(row(reset_pending=1), seed=777, family="secret-family")
        echo, _ = d.select_evidence([blocked, near], "echo", [], 0)
        fixed, _ = d.select_evidence([blocked, near], "fijo", [], 0)
        self.assertEqual(echo[0]["levels"], 4)
        self.assertEqual(fixed[0]["levels"], 0)
        self.assertNotIn("seed", str(echo))
        self.assertNotIn("secret-family", str(echo))

    def test_no_effect_diagnostic_does_not_skip_original_verifier(self):
        # An invalid native measurement is deliberately observed: even a default
        # proposal reaches execution instead of being silently discarded.
        visited = []
        def failing_measure(*args, **kwargs):
            visited.append(args[0])
            raise RuntimeError("synthetic execution failure")
        _, _, _, verdict = s.verifier(failing_measure)("test", json.dumps(proposal()), s.strategy(),
                                                       {"rows": [row(reset_pending=1)]}, {})
        self.assertTrue(visited)
        self.assertEqual(verdict["verdict"], "V2")
        self.assertEqual(verdict["applicability"]["setting_changes"], 0)

    def test_raw_keeps_executable_ineffective_proposal_without_utility_gate(self):
        calls = []
        def measurement(*args, **kwargs):
            calls.append(kwargs.get("replay", False))
            return {"trace_digest": "same"}
        current, event = s.raw_step("raw", s.strategy(), json.dumps(proposal()), measurement)
        self.assertEqual(current["program"], proposal())
        self.assertEqual(event["verdict"], "EXECUTABLE")
        self.assertEqual(calls, [False, True])

    def test_prompts_equal_call_budget_and_scientific_gates_unchanged(self):
        for arm in ("fijo", "echo"):
            reqs = s.requests(arm, 1, 5, s.strategy(), {"rows": [row()]}, [])
            self.assertEqual([r["id"] for r in reqs], list(range(5, 10)))
        self.assertEqual(s.config()["calls_with_calibration"], 82)
        totals = {k: {"levels": 105, "score": 1} for k in ("echo", "semilla", "fijo", "sinfiltro")}
        totals["semilla"]["levels"] = 100
        dev = {k: {"levels": 10, "score": 1} for k in ("echo", "semilla")}
        result = checks(totals, dev, True)
        self.assertTrue(result["B1"])
        self.assertFalse(result["B2"])
        self.assertFalse(result["B3"])
        totals["echo"]["score"] = 0.9
        self.assertFalse(checks(totals, dev, True)["B1"])


@unittest.skipUnless(importlib.util.find_spec("numpy") and importlib.util.find_spec("arcengine"), "managed ARC runtime")
class Native(unittest.TestCase):
    def test_passive_diagnostics_preserve_native_and_patched_actions(self):
        from echo_arc import agent, runner
        from echo_arc.temporal_bench import _gym_env
        from echo_arc.observe import Journal
        for value in (s.strategy(), s.strategy(program=proposal(value=20))):
            with tempfile.TemporaryDirectory() as folder:
                recorder = d.DiagnosticRecorder(Journal(Path(folder) / "arc-decisions.jsonl"))
                agent._COMP_CACHE.clear()
                plain = s.Execution.play(_gym_env(3, 19), 240, 12345, value)
                agent._COMP_CACHE.clear()
                try:
                    actual = s.Execution.play(_gym_env(3, 19), 240, 12345, value, recorder)
                finally:
                    recorder.close()
                self.assertEqual(plain, actual)
                summary = recorder.summary()
                self.assertGreater(summary["counts"]["decisions"], 0)
                self.assertEqual(sum(r["count"] for r in summary["feature_counts"]), summary["counts"]["decisions"])


if __name__ == "__main__":
    unittest.main()
