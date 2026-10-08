"""SENSATION first deliverable: bounded history and independent audit checks."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout
import io
from itertools import product
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4 import sensation
from echoai.echo4.__main__ import main
from echoai.echo4.audit import digest, observed
from echoai.echo4.demo import run_demo
from echoai.echo4.sensation import SensoryHistory
from echoai.echo4.sensation_audit import temporal_audit
from echoai.echo4.viability import analyze
from echoai.echo4.world import Body, DockRules, transition


def reference(starts, depth):
    """Independent Cartesian enumeration with literal lists, not bitsets/DFS."""
    graph = analyze()
    groups = {d: {} for d in (0, 2, 4) if d <= depth}
    survivors = 0
    for start in starts:
        for actions in product(range(3), repeat=depth):
            body = start
            packets = [observed(body)]
            for action in actions:
                body = transition(body, action, DockRules()).after
                if not body.alive:
                    break
                packets.append(observed(body))
            if len(packets) != depth + 1:
                continue
            survivors += 1
            for retained, arm in groups.items():
                key = packets[depth - retained]
                for j in range(depth - retained, depth):
                    key += bytes((actions[j],)) + packets[j + 1]
                arm.setdefault(key, []).append(body)
    summaries = {}
    for retained, arm in groups.items():
        summary = dict(groups=len(arm), prefixes=survivors,
                       ambiguous_joint_groups=0, prefixes_with_joint_ambiguity=0,
                       incompatible_viable_groups=0)
        for bodies in arm.values():
            ambiguous = any(len({
                (observed(step.after), step.after.alive)
                for body in bodies
                for step in (transition(body, action, DockRules()),)
            }) > 1 for action in range(3))
            summary["ambiguous_joint_groups"] += int(ambiguous)
            summary["prefixes_with_joint_ambiguity"] += len(bodies) if ambiguous else 0
            safe = [set(graph.safe_actions(body)) for body in bodies]
            summary["incompatible_viable_groups"] += int(
                all(safe) and not set.intersection(*safe))
        summaries[retained] = summary
    return summaries


class TestSensoryHistory(unittest.TestCase):
    def test_exact_payload_budgets(self):
        self.assertEqual([SensoryHistory(d).payload_bytes for d in (0, 2, 4)], [16, 50, 84])

    def test_empty_requires_explicit_start(self):
        history = SensoryHistory(2)
        for call in (history.snapshot, history.sensory_delta,
                     lambda: history.advance(0, observed(Body()))):
            with self.assertRaises(RuntimeError):
                call()

    def test_reject_bad_depths(self):
        for depth in (True, False, -1, 1, 3, 5, 4.0, "4", None):
            with self.subTest(depth=depth), self.assertRaises(ValueError):
                SensoryHistory(depth)

    def test_start_has_only_current_packet(self):
        history = SensoryHistory(4)
        packet = observed(Body())
        history.start(packet)
        self.assertEqual(history.snapshot(), packet)
        self.assertEqual(history.steps, 0)
        self.assertEqual(history.sensory_delta(), (0, 0))

    def test_window_matches_literal_suffix_over_long_stream(self):
        for depth in (0, 2, 4):
            history = SensoryHistory(depth)
            packet = observed(Body())
            history.start(packet)
            expected = packet
            storage = id(history._buffer)
            for step in range(1000):
                action = step % 3
                packet = observed(Body(step % 127 + 1, step % 126 + 1))
                expected = (expected + bytes((action,)) + packet)[-(16 + 17 * depth):]
                history.advance(action, packet)
                self.assertEqual(history.snapshot(), expected)
                self.assertEqual(history.steps, min(step + 1, depth))
                self.assertEqual(history.payload_bytes, 16 + 17 * depth)
                self.assertEqual(id(history._buffer), storage)

    def test_explicit_restart_clears_old_life(self):
        history = SensoryHistory(4)
        history.start(observed(Body()))
        history.advance(0, observed(Body(37, 80)))
        packet = observed(Body(1, 1))
        history.start(packet)
        self.assertEqual(history.snapshot(), packet)
        self.assertEqual(history.steps, 0)
        self.assertEqual(history._buffer[16:], bytes(68))

    def test_bad_actions_are_rejected_before_mutation(self):
        history = SensoryHistory(2)
        history.start(observed(Body()))
        for action in (True, False, -1, 3, 256, 0.0, "0", None):
            before = bytes(history._buffer), history.steps
            with self.subTest(action=action), self.assertRaises(ValueError):
                history.advance(action, observed(Body(37, 80)))
            self.assertEqual((bytes(history._buffer), history.steps), before)

    def test_bad_packets_cannot_mutate_or_reset(self):
        history = SensoryHistory(2)
        history.start(observed(Body()))
        history.advance(0, observed(Body(37, 80)))
        for packet in (b"", bytes(15), bytes(17), bytearray(16), "x" * 16, None):
            before = bytes(history._buffer), history.steps
            for call in (lambda: history.start(packet), lambda: history.advance(1, packet)):
                with self.assertRaises(ValueError):
                    call()
                self.assertEqual((bytes(history._buffer), history.steps), before)

    def test_terminal_observation_is_not_an_implicit_reset(self):
        history = SensoryHistory(2)
        history.start(observed(Body()))
        packet = observed(Body(0, 127))
        history.advance(0, packet)
        self.assertEqual(history.steps, 1)
        self.assertEqual(history.snapshot()[-16:], packet)

    def test_deltas_are_observable_codes_not_hidden_physiology(self):
        history = SensoryHistory(2)
        history.start(observed(Body(32, 64)))
        history.advance(0, observed(Body(37, 80)))
        self.assertEqual(history.sensory_delta(), (-30, 26))

    def test_identical_visible_streams_have_identical_history(self):
        first, second = Body(40, 70), Body(41, 71)
        left, right = SensoryHistory(4), SensoryHistory(4)
        left.start(observed(first))
        right.start(observed(second))
        for action in (0, 1, 0, 1):
            first = transition(first, action, DockRules()).after
            second = transition(second, action, DockRules()).after
            self.assertNotEqual(first, second)
            self.assertEqual(observed(first), observed(second))
            left.advance(action, observed(first))
            right.advance(action, observed(second))
        self.assertEqual(left.snapshot(), right.snapshot())

    def test_runtime_has_no_oracle_or_policy_dependency(self):
        tree = ast.parse(Path(sensation.__file__).read_text())
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertEqual(imports, ["__future__", "echoai.core.wsp", "echoai.nexus0.constants"])
        for node in ast.walk(tree):
            self.assertFalse(isinstance(node, ast.Constant) and isinstance(node.value, float))
            self.assertFalse(isinstance(node, ast.Div))

    def test_real_agent_trace_supplies_only_public_stream(self):
        report = run_demo(include_trace=True)
        history = SensoryHistory(4)
        history.start(bytes.fromhex(report["trace"][0]["wsp_before"]))
        for row in report["trace"]:
            self.assertEqual(history.snapshot()[-16:], bytes.fromhex(row["wsp_before"]))
            history.advance(row["executed_action"], bytes.fromhex(row["wsp_after"]))
        self.assertEqual(report["executed_turns"], 37)
        self.assertEqual((report["false_facts"], report["destroyed"], report["cortex_calls"]), (0, 0, 0))
        self.assertEqual(history.payload_bytes, 84)


class TestTemporalAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = temporal_audit()

    def test_full_prefix_accounting(self):
        report = self.report
        self.assertEqual(report["potential_action_strings"], 16002 * 3 ** 4)
        self.assertEqual(report["potential_action_strings"], report["accounted_action_strings"])
        self.assertEqual(report["complete_surviving_prefixes"], 947496)
        self.assertEqual(report["terminal_prefixes_by_depth"], [0, 5024, 9396, 23146, 59016])

    def test_original_domain_matches_world1_and_separates_conflicts(self):
        original = self.report["original_full_domain"]
        self.assertEqual(original["groups"], 32)
        self.assertEqual(original["ambiguous_joint_groups"], 32)
        self.assertEqual(original["different_viable_action_sets"], 14)
        self.assertEqual(original["mixed_viable_doomed_groups"], 2)
        self.assertEqual(original["incompatible_viable_groups"], 0)

    def test_matched_population_and_refinement(self):
        arms = self.report["arms"]
        self.assertTrue(self.report["same_population_in_all_arms"])
        self.assertTrue(self.report["ambiguity_nonincreasing"])
        self.assertEqual([a["history_steps"] for a in arms], [0, 2, 4])
        self.assertEqual([a["history_payload_bytes"] for a in arms], [16, 50, 84])
        for left, right in zip(arms, arms[1:]):
            self.assertEqual(left["prefixes"], right["prefixes"])
            for kind in ("observation", "terminal", "joint"):
                self.assertLessEqual(right[f"prefixes_with_{kind}_ambiguity"], left[f"prefixes_with_{kind}_ambiguity"])

    def test_no_full_identifiability_claim(self):
        for arm in self.report["arms"]:
            self.assertGreater(arm["prefixes_with_joint_ambiguity"], 0)
        self.assertFalse(self.report["sensation_phase_closed"])
        self.assertFalse(self.report["runtime_connected_to_policy"])
        self.assertEqual(self.report["learned_prediction_evaluation"], "not_run")
        self.assertEqual(self.report["boundary_acceptance"], "not_run")

    def test_witness_consequences_replay(self):
        for arm in self.report["arms"]:
            witness = arm["ambiguity_witness"]
            history = bytes.fromhex(witness["history_hex"])
            self.assertEqual(len(history), arm["history_payload_bytes"])
            self.assertEqual(history[-16:].hex(), witness["current_wsp_hex"])
            for body_data, expected in zip(witness["compatible_final_bodies"], witness["next_outcomes"]):
                body = Body(*body_data)
                self.assertEqual(observed(body).hex(), witness["current_wsp_hex"])
                step = transition(body, witness["executed_action_to_probe"], DockRules())
                self.assertEqual(observed(step.after).hex(), expected["wsp_hex"])
                self.assertEqual(not step.after.alive, expected["terminal"])
            self.assertNotEqual(*witness["next_outcomes"])

    def test_independent_small_domain_reference(self):
        starts = (Body(1, 1), Body(32, 64), Body(33, 65), Body(127, 126), Body(40, 70))
        for depth in (0, 2, 4):
            expected = reference(starts, depth)
            actual = temporal_audit(max_depth=depth, initial_states=starts)
            for arm in actual["arms"]:
                for field, value in expected[arm["history_steps"]].items():
                    self.assertEqual(arm[field], value, (depth, field))

    def test_witness_histories_reachable_from_compatible_initial_states(self):
        # Independent forward replay, not merely matching the final packet.
        for arm in self.report["arms"]:
            witness = arm["ambiguity_witness"]
            raw = bytes.fromhex(witness["history_hex"])
            packets = [raw[i:i + 16] for i in range(0, len(raw), 17)]
            actions = [raw[i] for i in range(16, len(raw), 17)]
            reached = set()
            for h in range(1, 128):
                for temperature in range(1, 127):
                    body = Body(h, temperature)
                    if observed(body) != packets[0]:
                        continue
                    for action, packet in zip(actions, packets[1:]):
                        body = transition(body, action, DockRules()).after
                        if not body.alive or observed(body) != packet:
                            break
                    else:
                        reached.add((body.h, body.temperature))
            for body in witness["compatible_final_bodies"]:
                self.assertIn(tuple(body), reached)

    def test_empty_surviving_population_is_reported(self):
        # No action can keep this body alive: heat, cold or energy failure.
        report = temporal_audit(max_depth=2, initial_states=(Body(1, 126),))
        self.assertEqual(report["complete_surviving_prefixes"], 0)
        self.assertEqual(report["accounted_action_strings"], 9)
        self.assertTrue(all(arm["groups"] == 0 for arm in report["arms"]))

    def test_invalid_configuration(self):
        for depth in (True, False, -1, 1, 3, 5, 4.0):
            with self.assertRaises(ValueError):
                temporal_audit(max_depth=depth)
        for states in ((), [], [Body()], (Body(), Body()), (Body(0, 64),), ("body",)):
            with self.assertRaises(ValueError):
                temporal_audit(initial_states=states)

    def test_report_hash_covers_content(self):
        report = dict(self.report)
        expected = report.pop("report_sha256")
        self.assertEqual(digest(report), expected)
        report["sensation_phase_closed"] = True
        self.assertNotEqual(digest(report), expected)

    def test_source_hashes_include_sensor_and_contract(self):
        import hashlib
        root = Path(__file__).resolve().parents[1]
        for name, expected in self.report["source_sha256"].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), expected)
        self.assertIn("nexus0/encoder.py", self.report["source_sha256"])
        self.assertIn("docs/ECHO4-SENSATION1-DESIGN.md", self.report["source_sha256"])

    def test_cli_dispatch(self):
        output = io.StringIO()
        with patch("echoai.echo4.sensation_audit.temporal_audit", return_value=self.report), redirect_stdout(output):
            self.assertEqual(main(["sensation-audit"]), 0)
        self.assertEqual(json.loads(output.getvalue()), self.report)

    def test_fresh_process_reproduces_without_diary_writes(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            diary = Path(directory) / "must-not-exist.jsonl"
            env = dict(os.environ, PYTHONPATH=str(root.parent), PYTHONDONTWRITEBYTECODE="1",
                       NAVI_THOUGHT_LOG=str(diary))
            result = subprocess.run([sys.executable, "-m", "echoai.echo4", "sensation-audit"],
                                    cwd=root, env=env, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), self.report)
            self.assertFalse(diary.exists())


if __name__ == "__main__":
    unittest.main()
