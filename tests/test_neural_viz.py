"""NEURAL-VIZ-1 observes the live loop without becoming a decision path."""
from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from echoai.nexus0 import neural_viz, thought
from echoai.nexus0.neural_viz_gui import RuntimeEngine, TaskSpec, discover_tasks
from echoai.nexus0.loop import Agent


class TestNeuralViz(unittest.TestCase):
    def test_real_wsp_drives_a_256_cell_read_only_monitor(self):
        agent = Agent(ask=False)
        wsp = agent.observation(agent.env.cell())
        monitor = neural_viz._spoke(wsp)
        self.assertEqual(len(wsp), 16)
        self.assertEqual(len(monitor["counts"]), 256)
        self.assertGreater(monitor["spikes"], 0)
        self.assertEqual(len(neural_viz._raster(monitor["counts"])), 16)
        before = (agent.metrics.turns, agent.cam.destroyed)
        neural_viz.render(agent, 0, agent.env.cell(), wsp, 2, monitor,
                          neural_viz.LAB / "does-not-exist.jsonl")
        self.assertEqual((agent.metrics.turns, agent.cam.destroyed), before)

    def test_native_tasks_are_declarative_and_emit_exact_gui35_thought(self):
        tasks = discover_tasks()
        self.assertGreaterEqual(len(tasks), 4)
        body = next(task for task in tasks if task.ident == "body3d-learn")
        self.assertEqual(body.agent["factory"], "echoai.nexus0.loop:Agent")
        with tempfile.TemporaryDirectory() as tmp:
            engine = RuntimeEngine(body, thought_log=Path(tmp) / "thought.jsonl",
                                   cortex_log=Path(tmp) / "cortex.jsonl")
            engine._tick()
            row = engine.out.get_nowait()
        self.assertEqual(len(row["lif_a"]), 256)
        self.assertEqual(len(row["lif_b"]), 256)
        self.assertEqual(len(row["wsp_bytes"]), 16)
        self.assertEqual(row["wsp_decoded"]["rel"], 14)
        self.assertEqual(row["kind"], "EMPTY")
        self.assertIn("attend_reason_name", row)
        self.assertEqual(set(row["thought"]), set(thought.KEYS))
        self.assertEqual(row["thought"]["turn"], row["turn"])
        self.assertEqual(row["thought"]["action"], row["action"])
        self.assertEqual(row["thought"]["wsp"], row["wsp"])

    def test_gen1f_live_birth_uses_real_spawn_child_contract(self):
        task = TaskSpec.load(Path(__file__).resolve().parents[1] /
                             "viz_tasks" / "03-gen1f-live.json")
        with tempfile.TemporaryDirectory() as tmp:
            engine = RuntimeEngine(task, thought_log=Path(tmp) / "thought.jsonl",
                                   cortex_log=Path(tmp) / "cortex.jsonl")
            for _ in range(49):
                engine._tick()
        self.assertEqual(engine.generation, 1)
        self.assertEqual(engine.total_deaths, 48)
        self.assertEqual(engine.agent.evidence_budget, 8)
        # The child has acted once. Two slots are the observed origin and
        # terminal successor; parent memories were not copied into it.
        self.assertLessEqual(engine.agent.cam.used, 2)


if __name__ == "__main__":
    unittest.main()
