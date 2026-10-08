"""WORLD-1 physics, feasibility, observation limits and unchanged-agent wiring."""
from __future__ import annotations

import ast
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import asdict, replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.wsp import unpack

from echoai.echo4 import adapter, demo, viability, world
from echoai.echo4.__main__ import main
from echoai.echo4.adapter import DockEnv, new_agent
from echoai.echo4.audit import observation_audit, observed, world_audit
from echoai.echo4.demo import run_demo
from echoai.echo4.viability import STATE_COUNT, analyze, indexed_body, state_index
from echoai.echo4.world import Body, DockRules, DockWorld, transition
from echoai.nexus0.heat1b import ThermalDockEnv
from echoai.nexus0.loop import Agent


class TestPhysics(unittest.TestCase):
    def test_default_transitions_and_no_shaping(self):
        for action, expected in enumerate((Body(37, 80), Body(29, 48), Body(31, 68))):
            with self.subTest(action=action):
                step = transition(Body(), action, DockRules())
                self.assertEqual(step.after, expected)
                self.assertEqual(step.reward, 0)
                self.assertTrue(step.balanced)

    def test_resource_spill_is_not_hidden(self):
        step = transition(Body(126, 64), 0, DockRules())
        self.assertEqual((step.after.h, step.resource_in, step.resource_spill),
                         (127, 5, 4))
        self.assertTrue(step.balanced)

    def test_exhaustion_spends_only_available_resources(self):
        step = transition(Body(1, 64), 1, DockRules())
        self.assertEqual((step.after.h, step.resource_used, step.reward), (0, 1, -16))
        self.assertEqual(step.after.cause, "energy")
        self.assertTrue(step.balanced)

    def test_heat_and_cold_are_terminal(self):
        for body, action, expected, cause in (
            (Body(32, 126), 0, Body(37, 127), "heat"),
            (Body(32, 1), 1, Body(29, 0), "cold"),
            (Body(1, 126), 2, Body(0, 127), "heat"),
        ):
            with self.subTest(cause=cause):
                step = transition(body, action, DockRules())
                self.assertEqual(step.after, expected)
                self.assertEqual(step.after.cause, cause)
                self.assertEqual(step.reward, -16)

    def test_terminal_bodies_cannot_act(self):
        for body in (Body(0, 64), Body(32, 0), Body(32, 127)):
            with self.assertRaises(RuntimeError):
                transition(body, 0, DockRules())

    def test_invalid_body_values(self):
        for value in (True, False, -1, 128, 1.0, "32", None):
            for name in ("h", "temperature"):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    Body(**{name: value})

    def test_invalid_rule_values(self):
        for name in asdict(DockRules()):
            for value in (True, False, -1, 128, 1.0, "5", None):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    DockRules(**{name: value})
            if name != "charge_input":
                with self.assertRaises(ValueError):
                    DockRules(**{name: 0})

    def test_zero_external_input_is_an_explicit_control(self):
        rules = DockRules(charge_input=0)
        step = transition(Body(), 0, rules)
        self.assertEqual(step.after.h, Body().h)
        self.assertEqual(step.resource_in, 0)

    def test_bad_commands_do_not_mutate_world(self):
        dock = DockWorld()
        before = dict(vars(dock))
        for action in (True, False, -1, 3, 200, 0.0, "0", None):
            with self.subTest(action=action), self.assertRaises(ValueError):
                dock.advance(action)
            self.assertEqual(vars(dock), before)

    def test_wrong_argument_types_rejected(self):
        for body, rules in (({}, DockRules()), (Body(), {})):
            with self.assertRaises(ValueError):
                transition(body, 0, rules)
        with self.assertRaises(ValueError):
            DockWorld(initial=Body(0, 64))
        with self.assertRaises(ValueError):
            DockWorld(rules={})

    def test_manual_renewable_cycle_and_cumulative_accounting(self):
        dock = DockWorld(initial=Body(124, 64))
        for _ in range(1000):
            dock.advance(0)
            dock.advance(1)
            self.assertEqual(dock.body, Body(124, 64))
            self.assertTrue(dock.balanced)
        self.assertEqual((dock.life_steps, dock.total_steps, dock.resets), (2000, 2000, 0))
        self.assertEqual((dock.resource_in, dock.resource_used, dock.resource_spill),
                         (5000, 3000, 2000))

    def test_wait_is_not_free_survival(self):
        dock = DockWorld()
        while dock.body.alive:
            dock.advance(2)
        self.assertEqual((dock.life_steps, dock.body), (16, Body(16, 127)))
        self.assertTrue(dock.balanced)

    def test_failed_terminal_step_leaves_ledger_unchanged(self):
        dock = DockWorld(initial=Body(1, 64))
        dock.advance(1)
        before = dict(vars(dock))
        with self.assertRaises(RuntimeError):
            dock.advance(0)
        self.assertEqual(vars(dock), before)

    def test_reset_is_explicit_counted_and_does_not_erase_total_steps(self):
        dock = DockWorld(initial=Body(1, 64))
        dock.advance(1)
        dock.reset()
        self.assertEqual(dock.body, dock.initial)
        self.assertEqual((dock.resets, dock.total_steps, dock.life_steps), (1, 1, 0))
        self.assertEqual((dock.resource_in, dock.resource_used, dock.resource_spill), (0, 0, 0))
        self.assertIsNone(dock.last_transition)
        self.assertTrue(dock.balanced)

    def test_transition_is_pure(self):
        body, rules = Body(), DockRules()
        expected = transition(body, 0, rules)
        self.assertEqual(transition(body, 0, rules), expected)
        self.assertEqual((body, rules), (Body(), DockRules()))


class TestViability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = analyze()
        cls.closed_rules = DockRules(charge_input=3, charge_heat=24,
                                    cooling_cost=4, cooling_drop=24, wait_heat=16)
        cls.closed = analyze(cls.closed_rules)

    def test_index_roundtrip_exhaustive(self):
        self.assertEqual(STATE_COUNT, 16002)
        for index in range(STATE_COUNT):
            self.assertEqual(state_index(indexed_body(index)), index)

    def test_invalid_graph_indices_and_dead_states(self):
        for index in (-1, STATE_COUNT, True, 1.0, "0"):
            with self.assertRaises(ValueError):
                indexed_body(index)
        with self.assertRaises(ValueError):
            state_index(Body(0, 64))
        with self.assertRaises(ValueError):
            analyze({})

    def test_kernel_is_nonempty_and_contains_initial(self):
        self.assertEqual(sum(self.graph.kernel), 15954)
        self.assertTrue(self.graph.contains(Body()))
        self.assertIsNone(self.graph.max_steps(Body()))

    def test_all_edges_match_physics_and_balance(self):
        for index, row in enumerate(self.graph.successors):
            for action, nxt in enumerate(row):
                step = transition(indexed_body(index), action, self.graph.rules)
                expected = state_index(step.after) if step.after.alive else -1
                self.assertEqual(nxt, expected)
                self.assertTrue(step.balanced)

    def test_kernel_is_a_fixed_point_and_finite_ranks_are_consistent(self):
        graph = self.graph
        for index, row in enumerate(graph.successors):
            self.assertEqual(graph.kernel[index], any(
                nxt >= 0 and graph.kernel[nxt] for nxt in row))
            if not graph.kernel[index]:
                self.assertEqual(graph.finite_lifetime[index], max(
                    1 if nxt < 0 else 1 + graph.finite_lifetime[nxt] for nxt in row))

    def test_independent_finite_horizon_iteration_matches_ranks(self):
        graph = self.closed
        survivors = set(range(STATE_COUNT))
        for horizon in range(1, 9):
            survivors = {i for i in survivors
                         if any(nxt in survivors for nxt in graph.successors[i])}
            self.assertEqual(survivors, {
                i for i in range(STATE_COUNT)
                if graph.kernel[i] or graph.finite_lifetime[i] > horizon
            })

    def test_witness_replays_and_closes_a_nonempty_cycle(self):
        witness = self.graph.witness(Body())
        self.assertIsNotNone(witness)
        self.assertEqual(witness.states[0], Body())
        self.assertTrue(witness.valid(self.graph.rules))
        self.assertEqual(witness.cycle_length, 2)
        self.assertGreater(witness.prefix_length, 0)
        self.assertEqual(witness, self.graph.witness(Body()))

    def test_witness_corruptions_are_rejected(self):
        witness = self.graph.witness(Body())
        mutants = (
            replace(witness, actions=()),
            replace(witness, cycle_start=True),
            replace(witness, cycle_start=-1),
            replace(witness, cycle_start=len(witness.actions)),
            replace(witness, actions=(True,) + witness.actions[1:]),
            replace(witness, states=witness.states[:-1]),
            replace(witness, states=(Body(0, 64),) + witness.states[1:]),
            replace(witness, states=(Body(33, 64),) + witness.states[1:]),
        )
        for mutant in mutants:
            with self.subTest(mutant=mutant.cycle_start):
                self.assertFalse(mutant.valid(self.graph.rules))

    def test_no_source_has_no_viable_kernel(self):
        graph = analyze(DockRules(charge_input=0))
        self.assertEqual(sum(graph.kernel), 0)
        self.assertIsNone(graph.witness(Body()))
        self.assertIsInstance(graph.max_steps(Body()), int)

    def test_historical_dynamics_remain_finite(self):
        self.assertEqual(sum(self.closed.kernel), 0)
        self.assertEqual(self.closed.max_steps(Body()), 71)
        self.assertEqual(max(self.closed.finite_lifetime), 276)
        self.assertIsNone(self.closed.witness(Body()))

    def test_historical_comparison_uses_actual_heat1b_exhaustively(self):
        historical = ThermalDockEnv()
        for index in range(STATE_COUNT):
            body = indexed_body(index)
            for action in range(3):
                _, _, h, temperature = historical.step_homeostatic(
                    action, body.h, body.temperature)
                step = transition(body, action, self.closed_rules)
                self.assertEqual(step.after, Body(h, temperature))

    def test_every_full_state_action_has_an_integer_result(self):
        for index in range(STATE_COUNT):
            row = self.graph.successors[index]
            self.assertEqual(len(row), 3)
            self.assertTrue(all(type(nxt) is int for nxt in row))

    def test_observation_limits_are_reported_not_assumed_solved(self):
        report = observation_audit(self.graph)
        self.assertEqual(report["living_packets"], 32)
        self.assertEqual(report["all_body_packets"], 45)
        self.assertEqual(report["terminal_packets_aliasing_live"], 4)
        self.assertEqual(report["non_markov_groups"], 32)
        self.assertEqual(report["groups_mixing_viable_and_doomed_states"], 2)
        self.assertFalse(report["partial_observation_control_proven"])

    def test_equal_packets_can_have_different_observed_successors(self):
        low, high = Body(1, 64), Body(32, 64)
        self.assertEqual(observed(low), observed(high))
        self.assertNotEqual(observed(transition(low, 0, DockRules()).after),
                            observed(transition(high, 0, DockRules()).after))

    def test_audit_keeps_feasibility_and_maintenance_separate(self):
        report = world_audit()
        self.assertTrue(report["initial_viable"])
        self.assertTrue(report["witness"]["valid"])
        self.assertEqual(report["checked_transitions"], 48006)
        self.assertEqual(report["maintenance_acceptance"], "not_run")
        self.assertNotIn("echo4_green", report)


class TestExistingAgentIntegration(unittest.TestCase):
    def test_reuses_original_agent_observation_and_memories(self):
        agent = new_agent()
        self.assertIs(type(agent), Agent)
        self.assertIs(agent.observation.__func__, Agent.observation)
        self.assertIs(agent.turn.__func__, Agent.turn)
        self.assertFalse(agent.cortex_enabled)
        self.assertFalse(agent.ask_enabled)
        self.assertEqual(agent.plan_depth, 0)
        self.assertEqual(agent.n_actions, 3)
        self.assertEqual(len(agent.cam.slot), 4096)
        self.assertEqual(agent.cam.used, 0)
        self.assertFalse(any(value for row in agent.q.q for value in row))

    def test_uses_the_existing_16_byte_packet(self):
        agent = new_agent()
        packet = agent.observation(agent.env.cell())
        self.assertEqual(packet, observed(Body()))
        decoded = unpack(packet)
        self.assertEqual(len(packet), 16)
        self.assertEqual(decoded["ext"]["seq"], 0)
        self.assertEqual(decoded["E"]["U"], 90)
        self.assertEqual(decoded["E"]["B"], -13)

    def test_mismatched_body_cannot_refill_the_agent(self):
        env = DockEnv()
        before = dict(vars(env))
        for h, t in ((127, 64), (32, 65), (True, 64), (32, 64.0)):
            with self.subTest(h=h, t=t), self.assertRaises(ValueError):
                env.step_homeostatic(0, h, t)
            self.assertEqual(vars(env), before)

    def test_world_forbids_shortcuts(self):
        env = DockEnv()
        with self.assertRaises(RuntimeError):
            env.step(0)
        with self.assertRaises(RuntimeError):
            env.teleport(0)
        self.assertFalse(env.reveal("refill"))
        self.assertEqual(env.body, Body())

    def test_one_life_stops_at_death_without_rescue(self):
        report = run_demo(256)
        self.assertEqual((report["executed_turns"], report["stop_reason"]), (37, "heat"))
        self.assertTrue(report["terminal"])
        self.assertEqual((report["resets"], report["deaths"]), (0, 1))
        self.assertTrue(report["resource_balance_ok"])
        self.assertEqual((report["destroyed"], report["false_facts"], report["cortex_calls"]),
                         (0, 0, 0))
        self.assertLessEqual(report["cam_used"], 45)
        self.assertEqual(report["maintenance_acceptance"], "not_run")

    def test_short_run_stops_at_horizon(self):
        report = run_demo(2)
        self.assertEqual(report["executed_turns"], 2)
        self.assertFalse(report["terminal"])
        self.assertEqual(report["stop_reason"], "horizon")
        self.assertEqual(report["resets"], 0)

    def test_greedy_is_explicitly_still_learning(self):
        report = run_demo(256, greedy=True)
        self.assertTrue(report["greedy"])
        self.assertFalse(report["learning_frozen"])
        self.assertGreater(report["q_nonzero"], 0)
        self.assertEqual(report["executed_turns"], 16)

    def test_physics_trace_is_reproducible_and_replayable(self):
        report = run_demo(256, include_trace=True)
        self.assertEqual(report, run_demo(256, include_trace=True))
        dock = DockWorld()
        for turn, row in enumerate(report["trace"]):
            self.assertEqual(row["turn"], turn)
            self.assertEqual(row["wsp_before"], observed(dock.body).hex())
            self.assertEqual(row["before"], asdict(dock.body))
            result = dock.advance(row["executed_action"])
            self.assertEqual(row["after"], asdict(dock.body))
            self.assertEqual(row["wsp_after"], observed(dock.body).hex())
            self.assertEqual(row["reward"], result.reward)
            self.assertEqual(row["terminal"], not dock.body.alive)
            for name in ("resource_in", "resource_used", "resource_spill"):
                self.assertEqual(row[name], getattr(result, name))
        self.assertEqual(report["final"], asdict(dock.body))
        self.assertEqual(len(report["trace"]), report["executed_turns"])

    def test_horizon_and_flags_are_bounded_and_strict(self):
        for turns in (0, -1, 10001, True, 2.0, "2"):
            with self.subTest(turns=turns), self.assertRaises(ValueError):
                run_demo(turns)
        for kwargs in ({"greedy": 1}, {"include_trace": "yes"}):
            with self.assertRaises(ValueError):
                run_demo(2, **kwargs)

    def test_inherited_log_environment_cannot_write_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "must_not_exist.jsonl"
            with patch.dict(os.environ, {"NAVI_THOUGHT_LOG": str(log)}):
                run_demo(2)
            self.assertFalse(log.exists())

    def test_capacity_guard_fails_before_world_changes(self):
        agent = new_agent()
        agent.cam.used = 4095
        with patch.object(demo, "new_agent", return_value=agent):
            with self.assertRaisesRegex(RuntimeError, "capacity"):
                run_demo(2)
        self.assertEqual(agent.env.life_steps, 0)
        self.assertEqual(agent.env.body, Body())


class TestInterfaceAndIsolation(unittest.TestCase):
    def test_cli_returns_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["demo", "--turns", "2", "--trace"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["executed_turns"], 2)
        self.assertEqual(len(report["trace"]), 2)

    def test_cli_rejects_unbounded_run(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["demo", "--turns", "10001"])
        self.assertEqual(caught.exception.code, 2)

    def test_new_process_audit_reproduces_graph_and_witness(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "-m", "echoai.echo4", "audit"], cwd=root,
            env={**os.environ, "PYTHONPATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True, text=True, check=True, timeout=30,
        )
        self.assertEqual(json.loads(result.stdout), world_audit())

    def test_no_float_arithmetic_or_forbidden_imports_in_new_runtime(self):
        for module in (world, adapter, viability):
            tree = ast.parse(Path(module.__file__).read_text())
            for node in ast.walk(tree):
                self.assertFalse(isinstance(node, ast.Constant) and type(node.value) is float)
                self.assertNotIsInstance(node, ast.Div)
        for module in (world, adapter, demo):
            tree = ast.parse(Path(module.__file__).read_text())
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
                elif isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
            self.assertFalse(any(
                forbidden in name for name in imports
                for forbidden in ("metaverse", "px4", "echo4.viability", "echo4.audit")
            ), imports)


if __name__ == "__main__":
    unittest.main()
