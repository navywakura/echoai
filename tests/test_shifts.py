"""SHIFT-S: preserved memory, changed physics, measurable adaptation."""
import copy
import unittest
from unittest.mock import patch

from echoai.nexus0 import shifts
from echoai.nexus0.echo2 import new_agent
from echoai.nexus0.obj1 import ITEM_XYZ
from echoai.nexus0 import body3d as cube


class TestShiftS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = shifts.experiment()

    def test_adapts_without_claiming_positive_transfer(self):
        self.assertTrue(shifts.green(self.report))
        for row in self.report["rows"]:
            self.assertGreater(row["gain_vs_frozen"], 0)
            # Real negative transfer remains visible, not turned into a win.
            self.assertLess(row["gain_vs_scratch"], 0)
            self.assertEqual(row["adapt"]["median_last_10"], 16)

    def test_boundary_preserves_all_memories_and_observation(self):
        for row in self.report["rows"]:
            b = row["boundary"]
            self.assertTrue(b["identity_preserved"])
            self.assertEqual(b["before"], b["after"])
            self.assertEqual(b["after"], b["frozen_initial"])
            self.assertEqual(b["observation_before"], b["observation_after"])

    def test_same_object_new_consequence_no_hint(self):
        a = new_agent()
        a.env.teleport(cube.index_of(*ITEM_XYZ, 0))
        old = a.observation(a.env.cell())
        memories = shifts.memories(a)
        a.env.world.nutrition = -24
        self.assertEqual(a.observation(a.env.cell()), old)
        self.assertEqual(shifts.memories(a), memories)
        a.turn(0)
        self.assertEqual((a.H, a.last_reward, a.episode_terminal), (0, -16, True))
        self.assertEqual(a.env.consumed, 1)

    def test_disabled_learning_really_freezes_q_and_remainders(self):
        a = new_agent(-24)
        with patch.object(shifts, "LIVES", 2):
            result = shifts.run_lives(a, 17, 0, freeze_q=True)
        self.assertEqual(result["q_before"], result["q_after"])
        self.assertGreater(a.metrics.turns, 0)
        self.assertGreater(sum(s.occupied != 0 for s in a.cam.slot), 0)

    def test_certificate_rejects_broken_evidence(self):
        mutations = (
            lambda r: r["rows"][0]["boundary"]["after"].update(q="reset"),
            lambda r: r["rows"][0]["boundary"].update(identity_preserved=False),
            lambda r: r["rows"][0]["boundary"].update(observation_after="repainted"),
            lambda r: r["rows"][0]["adapt"].update(total_turns=999),
            lambda r: r["rows"][0]["adapt"]["lives"][0].update(terminal=False),
            lambda r: r["rows"][0]["adapt"]["lives"][0].update(turns=True),
            lambda r: r["rows"][0]["adapt"]["lives"][0].update(entry=-1),
            lambda r: r["rows"][0]["frozen"].update(q_after="learned"),
            lambda r: r["rows"][0]["scratch"]["lives"].pop(),
            lambda r: r["rows"][0].update(gain_vs_scratch=100),
            lambda r: r["rows"][0]["adapt"].update(cortex_calls=1),
            lambda r: r["rows"][0].update(adapt=copy.deepcopy(r["rows"][0]["frozen"])),
            lambda r: [arm["lives"][0].update(phase=99999) for arm in
                       (r["rows"][0][k] for k in ("adapt", "frozen", "scratch"))],
        )
        for i, mutation in enumerate(mutations):
            with self.subTest(mutant=i):
                report = copy.deepcopy(self.report)
                mutation(report)
                report["green"] = True
                self.assertFalse(shifts.green(report))


if __name__ == "__main__":
    unittest.main()
