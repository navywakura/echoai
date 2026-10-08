"""Public functional development; not a reserved confirmation bank."""
import copy
import unittest
from unittest.mock import patch

from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.compose1_v3.space import Space
from echoai.nexus0.transfer3.model import export, restore, scratch, validate
from echoai.nexus0.transfer3.rehearsal import school, programmed, geometry, run, audit


class TransferTests(unittest.TestCase):
    def test_round_trip_only_abstract_effects(self):
        payload = programmed()
        model = restore(payload)
        self.assertEqual(export(model), payload)
        self.assertTrue(all(not s.has_fact for s in model.cam.slot if s.occupied))
        self.assertTrue(all(not any(row) for row in model.snapshot()['q'].values()))

    def test_q_and_episode_packets_do_not_transfer(self):
        model = restore(programmed())
        before = export(model)
        model.learn_reward(model.feature((999, 999, 0), (1, 1, 0), [False]*6),
                           0, 100, model.feature((0, 0, 0), (1, 1, 0), [True]*6))
        self.assertEqual(export(model), before)
        self.assertLess(restore(before).cam.used, model.cam.used)

    def test_scratch_has_no_effects(self):
        model = restore(scratch())
        self.assertEqual(model.cam.used, 0)
        self.assertTrue(all(model.predict(a) is None for a in range(7)))

    def test_unknown_or_single_observation_not_exported(self):
        model = Effects()
        model.observe_effect(True, 0, (1, 0, 0))
        self.assertEqual(export(model), scratch())

    def test_conflict_not_hidden(self):
        model = restore(programmed())
        model.observe_effect(True, 0, (-1, 0, 0))
        with self.assertRaises(ValueError):
            export(model)

    def test_private_fields_rejected(self):
        for key in ('cam', 'q', 'map', 'seed', 'world', 'episodes'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                restore(dict(programmed(), **{key: []}))

    def test_malformed_effects_rejected(self):
        for key, value in [('action', True), ('action', 4), ('count', True),
                           ('count', 1), ('count', 256), ('delta', [999, 0, 0]),
                           ('delta', [1.0, 0, 0]), ('delta', [0, 0, 1])]:
            payload = programmed()
            payload['effects'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate(payload)

    def test_duplicates_and_unsorted_rejected(self):
        for rows in ([programmed()['effects'][0]]*2, programmed()['effects'][::-1]):
            payload = scratch()
            payload['effects'] = rows
            with self.assertRaises(ValueError):
                restore(payload)

    def test_school_reconstructs_from_measured_consequences(self):
        result = school()
        model = Effects()
        for episode in result['episodes']:
            for row in episode['rows']:
                delta = tuple(b-a for a, b in zip(row['before']['odometry'], row['after']['odometry']))
                self.assertEqual(list(delta), row['consequence']['delta'])
                model.observe_effect(True, row['action'], delta)
        self.assertEqual(export(model), result['transfer'])
        self.assertEqual(result['training_moves'], 96)
        self.assertEqual(result['training_cost_sim_u'], 384)

    def test_new_episode_resets_spatial_state_and_keeps_learning_frozen(self):
        snapshot = restore(programmed()).snapshot()
        world = Space(20264301)
        agent = Composer(snapshot, world.goal)
        before = agent.model.fingerprint()
        agent.decide(world.scan())
        self.assertTrue(agent.cells)
        self.assertEqual(agent.model.fingerprint(), before)
        other = Composer(snapshot, world.goal)
        self.assertEqual(other.cells, {})
        self.assertEqual(other.visits, {})
        self.assertIsNone(other.home)

    def test_frame_cannot_carry_world_identity(self):
        world = Space(20264301)
        agent = Composer(restore(programmed()).snapshot(), world.goal)
        with self.assertRaises(ValueError):
            agent.decide(dict(world.scan(), seed=20264301))

    def test_geometry_ignores_translation_and_reflection(self):
        world = Space(20264301)
        expected = geometry(world)
        def change(p):
            return -p[1]+100, p[0]-50, p[2]
        world.domain = {change(p) for p in world.domain}
        world.solids = {change(p) for p in world.solids}
        world.start = change(world.start)
        world.goal = change(world.goal)
        self.assertEqual(geometry(world), expected)
        world.solids.remove(next(p for p in sorted(world.solids) if p not in (world.start, world.goal)))
        self.assertNotEqual(geometry(world), expected)

    def test_report_corruption_rejected(self):
        expected = dict(isolated=False, transfer3_green=False, trace=[1, 2])
        with patch('echoai.nexus0.transfer3.rehearsal.run', return_value=expected):
            self.assertTrue(audit(expected)['replay_valid'])
            changed = copy.deepcopy(expected)
            changed['transfer3_green'] = True
            with self.assertRaises(ValueError):
                audit(changed)


if __name__ == '__main__':
    unittest.main()
