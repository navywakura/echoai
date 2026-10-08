"""GEN-1: one inherited integer, fresh memories, causal controls."""
from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from echoai.nexus0 import gen1
from echoai.nexus0.loop import Agent
from echoai.nexus0.qtable import QTable


class TestInheritedBContract(unittest.TestCase):
    def test_validation_periods_and_default_equivalence(self):
        for value in (True, False, -2, 2, 1.0, "0", None):
            with self.assertRaises(ValueError):
                QTable(inherited_b=value)
        self.assertEqual(
            [QTable(inherited_b=b).exploration_period() for b in (-1, 0, 1)],
            [4, 8, 16],
        )
        old = QTable(explore_flat=True)
        zero = QTable(explore_flat=True, inherited_b=0)
        for table in (old, zero):
            table.set(7, 0, -12)
            table.set(7, 1, 5)
        self.assertEqual([old.select(7, t) for t in range(64)],
                         [zero.select(7, t) for t in range(64)])

    def test_b_changes_only_settled_exploration(self):
        tables = [QTable(explore_flat=True, inherited_b=b)
                  for b in (-1, 0, 1)]
        for table in tables:
            self.assertEqual([table.select(3, t) for t in range(12)],
                             [t % 3 for t in range(12)])
            table.set(3, 0, -12)
            table.set(3, 1, 5)
        self.assertEqual([sum(q.is_explore(3, t) for t in range(64))
                          for q in tables], [16, 8, 4])
        for q in tables:
            self.assertEqual(q.select(3, 8, greedy=True), q.best(3))

    def test_four_action_rows_keep_all_gears(self):
        for b in (-1, 0, 1):
            q = QTable(n_actions=4, explore_flat=True, inherited_b=b)
            q.set(0, 0, -1)
            period = q.exploration_period()
            offered = {q.select(0, t) for t in range(0, period * 8, period)}
            self.assertEqual(offered, {0, 1, 2, 3})

    def test_q_update_is_independent_of_b(self):
        rows = []
        for b in (-1, 0, 1):
            q = QTable(remainder=True, inherited_b=b)
            deltas = [q.update(4, 0, reward, 5)
                      for reward in (-16, -16, 8, 8, 8)]
            rows.append((deltas, q.row(4), q.rem[4]))
        self.assertEqual(rows[0], rows[1])
        self.assertEqual(rows[1], rows[2])

    def test_birth_is_empty_independent_and_respawn_keeps_b(self):
        parent = gen1.new_agent(-1)
        parent.turn(0)
        child = gen1.spawn_child(parent)
        self.assertEqual(child.q.inherited_b, -1)
        self.assertEqual(gen1._memory_fingerprint(child)["cam_occupied"], 0)
        self.assertEqual(gen1._memory_fingerprint(child)["q_nonzero"], 0)
        self.assertTrue(all(x is not y for x, y in
                            zip((parent.cam, parent.q, parent.t),
                                (child.cam, child.q, child.t))))
        child.turn(1)
        parent_hash = gen1._memory_fingerprint(parent)
        child.run(40)
        child.respawn()
        self.assertEqual(child.q.inherited_b, -1)
        self.assertEqual(gen1._memory_fingerprint(parent), parent_hash)

    def test_agent_rejects_invalid_b(self):
        for value in (True, -2, 2, 0.5):
            with self.assertRaises(ValueError):
                Agent(inherited_b=value)


class TestGen1Experiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = gen1.experiment()

    def test_protocol_and_controls_are_auditable(self):
        r = self.report
        self.assertEqual(r["selection"]["winner_b"], 1)
        self.assertEqual(r["transmitted_b"], 1)
        for row in r["exam"]:
            self.assertEqual(row["inherited"]["lives"],
                             row["static_b"]["lives"])
            self.assertEqual(row["naive"]["lives"], row["erase_b"]["lives"])
        for row in r["no_q_control"]:
            self.assertEqual(row["inherited"]["lives"], row["naive"]["lives"])
            self.assertEqual(row["inherited"]["final"]["q_nonzero"], 0)
        for row in r["inert_control"]:
            for arm in (row["inherited"], row["naive"]):
                self.assertIsNone(arm["episodes_to_criterion"])
                self.assertEqual({life["turns"] for life in arm["lives"]}, {16})

    def test_measured_result_is_red_without_rewriting_protocol(self):
        r = self.report
        self.assertFalse(gen1.green(r))
        self.assertEqual(r["headline"]["inherited_median"], 34)
        self.assertEqual(r["headline"]["naive_median"], 27)
        self.assertEqual(r["headline"]["strict_pair_wins"], 0)

    @unittest.expectedFailure
    def test_gen1_closure_requires_child_to_learn_faster(self):
        self.assertTrue(gen1.green(self.report))

    def test_arm_auditor_rejects_mutated_evidence(self):
        arm = copy.deepcopy(self.report["exam"][0]["inherited"])
        phases = gen1.phase_schedule(gen1.EXAM_SEEDS[0])
        self.assertTrue(gen1._valid_arm(arm, phases))
        arm["lives"][0]["turns"] += 1
        self.assertFalse(gen1._valid_arm(arm, phases))

    def test_runner_publishes_red_result(self):
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / "nexus0" / "gen1.py"
            fake.parent.mkdir()
            fake.touch()
            with mock.patch.object(gen1, "__file__", str(fake)), \
                    mock.patch.object(gen1, "experiment",
                                      return_value=copy.deepcopy(self.report)), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(gen1.main([]), 1)
            written = json.loads((Path(td) / "lab" / "echo2_gen1_report.json")
                                 .read_text(encoding="utf-8"))
            self.assertFalse(written["green"])


if __name__ == "__main__":
    unittest.main()
