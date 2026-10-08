"""HEAT-1b: two-variable homeostasis and causal certificate."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from echoai.core.wsp import unpack

from echoai.nexus0 import heat1, heat1b
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT
from echoai.nexus0.loop import Agent


class TestThermalState(unittest.TestCase):
    def test_encoder_uses_existing_wsp_b_byte(self):
        cold = encode_cell(0, KIND_OBJECT, vitality=32, temperature=16,
                           temperature_bands=8)
        hot = encode_cell(0, KIND_OBJECT, vitality=32, temperature=112,
                          temperature_bands=8)
        self.assertEqual((len(cold), len(hot)), (16, 16))
        self.assertEqual(unpack(cold)["E"]["U"], unpack(hot)["E"]["U"])
        self.assertEqual((unpack(cold)["E"]["B"], unpack(hot)["E"]["B"]),
                         (-88, 63))
        self.assertNotEqual(cold, hot)

    def test_encoder_and_agent_reject_invalid_thermal_values(self):
        for value in (True, -1, 128, 1.0, "64"):
            with self.assertRaises(ValueError):
                encode_cell(0, KIND_OBJECT, temperature=value)
        for bands in (True, 0, 2, 16, 4.0):
            with self.assertRaises(ValueError):
                encode_cell(0, KIND_OBJECT, temperature=64,
                            temperature_bands=bands)
        with self.assertRaises(ValueError):
            Agent(initial_temperature=64)
        for value in (True, 0, 127, 128, 64.0):
            with self.assertRaises(ValueError):
                Agent(env=heat1b.ThermalDockEnv(), initial_h=32,
                      initial_temperature=value, ask=False)

    def test_dock_tradeoff_and_thermal_death(self):
        env = heat1b.ThermalDockEnv()
        self.assertEqual(env.step_homeostatic(0, 32, 64)[2:], (35, 88))
        self.assertEqual(env.step_homeostatic(1, 32, 64)[2:], (28, 40))
        self.assertEqual(env.step_homeostatic(2, 32, 64)[2:], (31, 80))

        agent = heat1b.new_agent()
        with patch.object(agent, "_propose", return_value=0):
            for turn in range(3):
                agent.turn(turn, greedy=True)
        self.assertTrue(agent.episode_terminal)
        self.assertEqual((agent.H, agent.temperature, agent.last_reward),
                         (41, 127, -16))
        self.assertEqual(agent.env.last_cause, "heat")
        agent.respawn()
        self.assertEqual((agent.H, agent.temperature),
                         (heat1b.INITIAL_H, heat1b.INITIAL_TEMPERATURE))

    def test_blind_ablation_aliases_temperature(self):
        agent = heat1b.new_agent(observe_temperature=False)
        agent.temperature = 80
        temperate = agent.observation(agent.env.cell())
        agent.temperature = 112
        hot = agent.observation(agent.env.cell())
        self.assertEqual(temperate, hot)


class TestHeat1bCertificate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(heat1b.__file__).resolve().parents[1]
        cls.report = json.loads(
            (root / "lab" / "echo2_heat1b_report.json").read_text())
        cls.first_report = json.loads(
            (root / "lab" / "echo2_heat1_report.json").read_text())

    def test_first_contract_stays_red(self):
        self.assertFalse(self.first_report["green"])
        self.assertFalse(heat1.green(self.first_report))

    def test_final_report_is_green_and_recomputed(self):
        self.assertTrue(self.report["green"])
        self.assertTrue(heat1b.green(self.report))
        self.assertEqual(self.report["protocol"]["seeds_hash"],
                         "d9b122f8d30e51d79d0e2e24c58e9b109762d92a3c40c47de3e22362da4e56b8")

    def test_measured_tradeoff_and_controls(self):
        totals = {mode: sum(row[mode]["total_turns"]
                            for row in self.report["rows"])
                  for mode in ("joint", "blind", "reset", "no_q")}
        self.assertEqual(totals, {"joint": 20786, "blind": 7221,
                                  "reset": 5293, "no_q": 7186})
        self.assertTrue(all(totals["joint"] >= 2 * totals[mode]
                            for mode in ("blind", "reset", "no_q")))
        for row in self.report["rows"]:
            self.assertEqual([probe["action"]
                              for probe in row["joint"]["probe"]["rows"]],
                             [0, 1])
            self.assertTrue(row["no_q"]["q_unchanged"])
            self.assertEqual(row["no_q"]["final_state"]["q_nonzero"], 0)
            self.assertEqual(row["reset"]["q_t_resets"], 59)

    def test_auditor_rejects_mutated_action_and_summary(self):
        summary = dict(self.report)
        summary["protocol"] = dict(self.report["protocol"])
        summary["protocol"]["wait_delta"] = [-1, 0, 0]
        self.assertFalse(heat1b.green(summary))

        mutant = dict(self.report)
        mutant["rows"] = list(self.report["rows"])
        mutant["rows"][0] = dict(mutant["rows"][0])
        mutant["rows"][0]["joint"] = dict(mutant["rows"][0]["joint"])
        mutant["rows"][0]["joint"]["lives"] = list(
            mutant["rows"][0]["joint"]["lives"])
        mutant["rows"][0]["joint"]["lives"][0] = dict(
            mutant["rows"][0]["joint"]["lives"][0])
        mutant["rows"][0]["joint"]["lives"][0]["actions"] = list(
            mutant["rows"][0]["joint"]["lives"][0]["actions"])
        mutant["rows"][0]["joint"]["lives"][0]["actions"][0] ^= 1
        self.assertFalse(heat1b.green(mutant))


if __name__ == "__main__":
    unittest.main()
