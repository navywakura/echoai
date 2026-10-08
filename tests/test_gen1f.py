"""GEN-1f: inherited local evidence and its final certificate."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from echoai.nexus0 import gen1f
from echoai.nexus0.constants import GATE_BLOCK
from echoai.nexus0.loop import Agent
from echoai.core.qn import SLOT_FLAG_INHIBIT


class TestEvidenceBudget(unittest.TestCase):
    def test_validation_and_historical_default(self):
        for value in (0, 1, 2, 4, 8, 16):
            self.assertEqual(Agent(ask=False, evidence_budget=value)
                             .evidence_budget, value)
        for value in (True, -1, 3, 7, 1.0, "8", None):
            with self.assertRaises(ValueError):
                Agent(ask=False, evidence_budget=value)
        for value in (0, 1, None, "yes"):
            with self.assertRaises(ValueError):
                Agent(ask=False, evidence_greedy=value)

    def test_local_counts_then_q_takes_control(self):
        agent = gen1f.new_agent(2, 6, 12345)
        actions = []
        evidence = []
        for life in range(7):
            if life:
                agent.respawn()
            if life == 6:
                wsp = gen1f.encode_cell(6, gen1f.KIND_OBJECT,
                                        vitality=gen1f.INITIAL_H)
                slot = agent.cam.get(wsp)
                q_choice = agent.q.best(slot)
            actions.append(agent.turn(life * gen1f.PHASE_MODULUS))
            evidence.append(agent.last_evidence_explore)
        wsp = gen1f.encode_cell(6, gen1f.KIND_OBJECT,
                                vitality=gen1f.INITIAL_H)
        slot = agent.cam.get(wsp)
        self.assertEqual(sorted(agent.t.n[slot]), [2, 2, 3])
        self.assertEqual(sorted(actions[:6]), [0, 0, 1, 1, 2, 2])
        self.assertEqual(evidence, [True] * 6 + [False])
        self.assertEqual(actions[-1], q_choice)

    def test_greedy_exam_bypasses_evidence(self):
        agent = gen1f.new_agent(8, 4, 99)
        action = agent.turn(0, greedy=True)
        self.assertEqual(action, gen1f.ACTION_WAIT)
        self.assertFalse(agent.last_evidence_explore)

    def test_gate_keeps_last_word_over_evidence(self):
        agent = gen1f.new_agent(2, 4, 99)
        agent.turn(0, greedy=True)
        agent.respawn()
        wsp = gen1f.encode_cell(4, gen1f.KIND_OBJECT,
                                vitality=gen1f.INITIAL_H)
        slot = agent.cam.get(wsp)
        agent.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        action = agent.turn(gen1f.PHASE_MODULUS)
        self.assertTrue(agent.last_evidence_explore)
        self.assertEqual(agent.last_proposed_action, 0)
        self.assertEqual(agent.last_gate_decision, GATE_BLOCK)
        self.assertEqual(action, gen1f.ACTION_WAIT)

    def test_child_receives_integer_but_no_memory(self):
        parent = gen1f.new_agent(8, 3, 7)
        parent.turn(0)
        child = gen1f.spawn_child(parent, 9, 11)
        self.assertEqual(child.evidence_budget, 8)
        self.assertEqual(gen1f._memory_fingerprint(child)["cam_occupied"], 0)
        self.assertEqual(gen1f._memory_fingerprint(child)["q_nonzero"], 0)
        self.assertTrue(all(a is not b for a, b in
                            zip((parent.cam, parent.q, parent.t),
                                (child.cam, child.q, child.t))))

    def test_noise_is_independent_of_chosen_action(self):
        a = gen1f.CalibrationEnv(7, 123)
        b = gen1f.CalibrationEnv(7, 123)
        a.step_vital(0, gen1f.INITIAL_H)
        b.step_vital(1, gen1f.INITIAL_H)
        self.assertEqual(abs(a.last_reward), abs(b.last_reward))
        flipped = gen1f.noisy(123, 7, 0)
        self.assertEqual(a.last_reward > 0,
                         ((0 == a.best_action) != flipped))
        self.assertEqual(b.last_reward > 0,
                         ((1 == b.best_action) != flipped))


class TestGen1fCertificate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(gen1f.__file__).resolve().parents[1] / "lab" / \
            "echo2_gen1f_report.json"
        cls.report = json.loads(path.read_text(encoding="utf-8"))

    def test_published_report_is_green_and_recomputed(self):
        self.assertTrue(self.report["green"])
        self.assertTrue(gen1f.green(self.report))
        self.assertEqual(self.report["transmitted_budget"], 8)

    def test_measured_advantage_and_controls(self):
        h = self.report["headline"]
        self.assertEqual(h["inherited_late_errors"], 360)
        self.assertEqual(h["naive_late_errors"], 602)
        self.assertEqual(h["historical_late_errors"], 470)
        self.assertEqual((h["strict_wins"], h["strict_losses"]), (52, 24))
        self.assertEqual(h["reached"], 126)
        for row in self.report["exam"]:
            self.assertEqual(row["inherited"]["rows"],
                             row["direct"]["rows"])
            self.assertEqual(row["inherited"]["final"],
                             row["direct"]["final"])
            self.assertEqual(row["naive"]["rows"],
                             row["erase_b"]["rows"])
            self.assertEqual(row["naive"]["final"],
                             row["erase_b"]["final"])
            self.assertEqual(row["no_q"]["successes"], 0)
            self.assertTrue(row["no_q"]["censored"])
            self.assertEqual(row["no_q"]["final"]["q_nonzero"], 0)
            self.assertEqual(row["no_q"]["final"]["rem_nonzero"], 0)

    def test_auditor_rejects_forged_summary(self):
        mutant = dict(self.report)
        mutant["headline"] = dict(self.report["headline"])
        mutant["headline"]["inherited_late_errors"] -= 1
        self.assertFalse(gen1f.green(mutant))

    def test_auditor_rejects_changed_sequence(self):
        mutant = dict(self.report)
        mutant["exam"] = list(self.report["exam"])
        mutant["exam"][0] = dict(mutant["exam"][0])
        mutant["exam"][0]["inherited"] = dict(
            mutant["exam"][0]["inherited"])
        mutant["exam"][0]["inherited"]["rows"] = list(
            mutant["exam"][0]["inherited"]["rows"])
        mutant["exam"][0]["inherited"]["rows"][0] = dict(
            mutant["exam"][0]["inherited"]["rows"][0])
        mutant["exam"][0]["inherited"]["rows"][0]["phase"] += 1
        self.assertFalse(gen1f.green(mutant))


if __name__ == "__main__":
    unittest.main()
