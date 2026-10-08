"""ECHO-2's first slices: real terminal turns and object consequences."""
import copy
import unittest
from unittest.mock import patch

from echoai.core.wsp import unpack
from echoai.nexus0 import body3d as cube
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import RingEnv, KIND_EMPTY, KIND_OBJECT
from echoai.nexus0.food1 import FoodEnv
from echoai.nexus0.loop import Agent
from echoai.nexus0.obj1 import ITEM_XYZ
from echoai.nexus0.vita1 import VitalEnv


def empty_world():
    world = RingEnv()
    world.kind = [KIND_EMPTY] * len(world.kind)
    return world


class TestVita1(unittest.TestCase):
    def test_clock_terminal_and_no_postmortem_writes(self):
        a = Agent(env=VitalEnv(empty_world(), drain=2), initial_h=5,
                  ask=False, pattern_memory=True, trace=True)
        with patch.object(a.q, "select", return_value=2):
            a.run(100)
        self.assertEqual((a.H, a.life_turns, a.deaths), (0, 3, 1))
        self.assertTrue(a.episode_terminal)
        self.assertIsNone(a.prev_slot)
        self.assertEqual(a.q._active, [])
        frozen = copy.deepcopy((a.q.q, a.t.__dict__, a.metrics, a.env.i))
        with self.assertRaises(RuntimeError):
            a.turn(4)
        self.assertEqual((a.q.q, a.t.__dict__, a.metrics, a.env.i), frozen)

    def test_last_transition_is_terminal_not_respawn(self):
        a = Agent(env=VitalEnv(empty_world()), initial_h=1, ask=False)
        origin = a.env.cell().index
        with patch.object(a.q, "update", wraps=a.q.update) as update:
            a.turn(0)
        args = update.call_args
        self.assertEqual(args.kwargs, {"terminal": True})
        slot, action, reward, successor = args.args
        self.assertEqual(reward, -16)
        self.assertEqual(a.t.predict(slot, action), successor)
        self.assertEqual(unpack(a.cam.slot[successor].wsp)["E"]["U"], 100)
        self.assertNotEqual(a.env.i, origin)
        identities = (a.cam, a.q, a.t)
        learned = copy.deepcopy((a.q.q, a.t.__dict__))
        occupied = sum(s.occupied != 0 for s in a.cam.slot)
        a.respawn()
        self.assertEqual((a.H, a.life_turns, a.life_id, a.env.i), (1, 0, 1, 0))
        self.assertTrue(all(x is y for x, y in zip(identities, (a.cam, a.q, a.t))))
        self.assertEqual((a.q.q, a.t.__dict__), learned)
        self.assertEqual(sum(s.occupied != 0 for s in a.cam.slot), occupied)

    def test_pattern_does_not_learn_across_lives(self):
        a = Agent(env=VitalEnv(empty_world()), initial_h=3, ask=False,
                  pattern_memory=True)
        a.run(3)
        memory = a.pattern_memory
        learned = copy.deepcopy(memory.__dict__)
        a.respawn()
        self.assertIs(a.pattern_memory, memory)
        self.assertEqual(memory.__dict__, learned)
        a.turn(3)
        self.assertEqual(memory.observations, learned["observations"])

    def test_vitality_changes_only_urgency_and_slots_are_distinct(self):
        a = Agent(env=VitalEnv(empty_world()), initial_h=127, ask=False)
        base = encode_cell(0, KIND_EMPTY)
        for h, urgency in ((127, 0), (96, 30), (64, 60), (32, 90), (0, 100)):
            packet = encode_cell(0, KIND_EMPTY, vitality=h)
            self.assertEqual(len(packet), 16)
            self.assertEqual(packet[:8] + packet[9:], base[:8] + base[9:])
            self.assertEqual(unpack(packet)["E"]["U"], urgency)
            a.H = h
            a.greedy_on(0)  # Exercise the same observation path.
        self.assertEqual(sum(s.occupied != 0 for s in a.cam.slot), 5)

    def test_opt_in_and_invalid_configurations(self):
        self.assertFalse(hasattr(Agent(), "H"))
        for value in (0, -1, 128, True, 1.5):
            with self.assertRaises(ValueError):
                Agent(env=VitalEnv(empty_world()), initial_h=value)
        with self.assertRaises(ValueError):
            Agent(initial_h=32)
        with self.assertRaises(ValueError):
            Agent(env=VitalEnv(empty_world()), initial_h=32, cortex=True)
        with self.assertRaises(RuntimeError):
            Agent().respawn()
        with self.assertRaises(RuntimeError):
            Agent(env=VitalEnv(empty_world()), initial_h=32).respawn()

    def test_clock_costs_every_action_and_never_pays_for_waiting(self):
        for action in range(3):
            env = VitalEnv(empty_world(), drain=3)
            r, _, h = env.step_vital(action, 7)
            self.assertEqual((r, h), (0, 4))
        for bad in (True, -1, 128, 1.5):
            with self.assertRaises(ValueError):
                encode_cell(0, KIND_EMPTY, vitality=bad)
        a = Agent(env=VitalEnv(empty_world()), initial_h=5, ask=False)
        with patch.object(a.env, "step_vital", return_value=(0, a.env.cell(), 128)):
            with self.assertRaises(ValueError):
                a.turn(0)


class TestFood1(unittest.TestCase):
    def test_consume_is_an_object_interaction_and_only_once(self):
        for nutrition, expected_h, reward in ((24, 39, 16), (-24, 0, -16), (0, 15, 0)):
            w = FoodEnv(nutrition)
            w.teleport(cube.index_of(*ITEM_XYZ, 0))
            self.assertEqual(w.cell().kind, KIND_OBJECT)
            env = VitalEnv(w)
            r, cell, h = env.step_vital(0, 16)
            self.assertEqual((h, r), (expected_h, reward))
            self.assertEqual(cell.kind, KIND_EMPTY)
            self.assertIsNone(w.obj)
            self.assertFalse(w.coupled)
            self.assertEqual(w.consumed, 1)
            w.step(0)
            self.assertEqual((w.last_nutrition, w.consumed), (0, 1))

    def test_wait_does_not_eat_and_food_is_not_a_threat_label(self):
        packets = []
        for nutrition in (24, -24):
            w = FoodEnv(nutrition)
            w.teleport(cube.index_of(*ITEM_XYZ, 0))
            packets.append(encode_cell(w.i, w.cell().kind))
            _, _, h = VitalEnv(w).step_vital(2, 16)
            self.assertEqual((h, w.consumed), (15, 0))
            self.assertTrue(w.coupled)
        self.assertEqual(*packets)

    def test_clamp_and_respawn_restore_object_not_memory(self):
        w = FoodEnv()
        a = Agent(env=VitalEnv(w), initial_h=127, ask=False)
        w.teleport(cube.index_of(*ITEM_XYZ, 0))
        a.turn(0)
        self.assertEqual(a.H, 127)
        with patch.object(a.q, "select", return_value=2):
            a.run(127)
        a.respawn()
        self.assertEqual((w.obj, w.consumed), (ITEM_XYZ, 0))
        self.assertGreater(sum(s.occupied != 0 for s in a.cam.slot), 0)

    def test_q_learns_consumption_from_consequences(self):
        from echoai.nexus0.echo2 import food_probe
        report = food_probe()
        self.assertEqual(report["food"]["action"], 0)
        self.assertNotEqual(report["poison"]["action"], 0)
        self.assertNotEqual(report["inert"]["action"], 0)
        self.assertGreater(report["food"]["h_after"], report["food"]["h_before"])
        for row in report.values():
            self.assertEqual(row["false_facts"], 0)
            self.assertEqual(row["destroyed"], 0)
            self.assertEqual(row["cortex_calls"], 0)


class TestSurv1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from echoai.nexus0.echo2 import experiment
        cls.report = experiment()

    def test_survival_and_no_nutrition_control(self):
        from echoai.nexus0.echo2 import green
        self.assertTrue(green(self.report))
        self.assertEqual(len(self.report["survival"]), 3)
        for row in self.report["survival"]:
            self.assertGreater(row["persist"]["median"], row["reset"]["median"])
            for arm in ("persist", "reset"):
                self.assertEqual(len(row[arm]["lives"]), 50)
                self.assertEqual(row[arm]["deaths"], 50)
        self.assertEqual(self.report["inert"]["persist"]["median"], 16)
        self.assertEqual(self.report["inert"]["reset"]["median"], 16)

    def test_false_green_mutations(self):
        from echoai.nexus0.echo2 import green
        mutations = (
            lambda r: r["survival"][0]["persist"].update(median=999),
            lambda r: r["survival"][0]["persist"]["lives"][0].update(terminal=False),
            lambda r: r["survival"][0]["persist"]["lives"][0].update(h=1),
            lambda r: r["survival"][0]["persist"]["lives"][0].update(turns=999),
            lambda r: r["survival"][0]["reset"]["lives"].pop(),
            lambda r: r["survival"][0]["persist"].update(respawn_preserves_memory=False),
            lambda r: r["survival"][0]["persist"]["lives"][0].update(living_bonus_turns=1),
            lambda r: r["survival"][0]["reset"]["lives"][0].update(phase=-1),
            lambda r: r["survival"][0]["persist"].update(cortex_calls=1),
            lambda r: r["food"]["food"].update(consumed=0),
            lambda r: r["food"]["poison"].update(action=0),
        )
        for i, mutate in enumerate(mutations):
            with self.subTest(mutant=i):
                report = copy.deepcopy(self.report)
                mutate(report)
                report["green"] = True
                self.assertFalse(green(report))

    def test_seed_is_reproducible(self):
        from echoai.nexus0.echo2 import survival_arm, SEEDS
        self.assertEqual(survival_arm(SEEDS[0], True), self.report["survival"][0]["persist"])

    def test_living_reward_mutant_is_rejected_even_if_it_learns(self):
        from echoai.nexus0.echo2 import survival_arm, SEEDS, green
        original = VitalEnv.step_vital

        def pays_for_living(env, action, h):
            reward, cell, next_h = original(env, action, h)
            return reward + int(next_h > 0), cell, next_h

        with patch.object(VitalEnv, "step_vital", pays_for_living):
            mutant = survival_arm(SEEDS[0], True)
        self.assertGreater(sum(row["living_bonus_turns"] for row in mutant["lives"]), 0)
        report = copy.deepcopy(self.report)
        report["survival"][0]["persist"] = mutant
        self.assertFalse(green(report))


if __name__ == "__main__":
    unittest.main()
