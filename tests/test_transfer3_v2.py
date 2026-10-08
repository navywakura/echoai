import copy
import unittest
from unittest.mock import patch

from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.transfer3 import policy
from echoai.nexus0.transfer3.rehearsal_v2 import Space, shape, suite, episode, PROTOCOL


class TransferV2Tests(unittest.TestCase):
    def test_relative_feature_translation_invariant(self):
        a = Effects.feature((0, 0, 0), (5, 2, 0), [False]*6)
        b = Effects.feature((100, -40, 8), (105, -38, 8), [False]*6)
        self.assertEqual(a, b)

    def test_scratch_and_transfer_same_locomotion(self):
        model = policy.restore(policy.scratch())
        f = model.feature((0, 0, 0), (5, 2, 0), [False]*6)
        model.learn_reward(f, 0, 32, f)
        transferred = policy.restore(policy.export(model))
        scratch = policy.restore(policy.scratch())
        self.assertEqual([scratch.predict(a) for a in range(7)], [transferred.predict(a) for a in range(7)])
        self.assertNotEqual(scratch.values(f), transferred.values(f))

    def test_policy_roundtrip_and_nonfacts(self):
        model = policy.restore(policy.scratch())
        f = model.feature((0, 0, 0), (2, 1, 0), [True]*6)
        model.learn_reward(f, 0, -16, f)
        payload = policy.export(model)
        restored = policy.restore(payload)
        self.assertEqual(policy.export(restored), payload)
        self.assertTrue(all(not s.has_fact for s in restored.cam.slot if s.occupied))

    def test_reject_coordinate_and_private_channels(self):
        for key in ('map', 'seed', 'episodes', 'cam'):
            with self.assertRaises(ValueError):
                policy.restore(dict(policy.scratch(), **{key: []}))
        for code in (True, -1, 1728):
            with self.assertRaises(ValueError):
                policy.restore(dict(schema=policy.SCHEMA, q=[dict(feature=code, values=[1,0,0,0,0,0,0])]))

    def test_reject_bad_q(self):
        for values in ([128,0,0,0,0,0,0], [True,0,0,0,0,0,0], [1,0,0,0,1,0,0], [0]*7):
            with self.assertRaises(ValueError):
                policy.restore(dict(schema=policy.SCHEMA, q=[dict(feature=0, values=values)]))

    def test_shape_ignores_roles_translation_rotation_reflection(self):
        world = Space(1)
        expected = shape(world)
        world.goal = (99, 99, 99)
        self.assertEqual(shape(world), expected)
        for reflection in (-1, 1):
            other = copy.deepcopy(world)
            transform = lambda p: (reflection*p[1]+100, p[0]-50, p[2]+8)
            other.domain = {transform(p) for p in world.domain}
            other.solids = {transform(p) for p in world.solids}
            self.assertEqual(shape(other), expected)
        world.solids.remove(next(iter(world.solids)))
        self.assertNotEqual(shape(world), expected)

    def test_suite_excludes_duplicates_across_all_rooms(self):
        a, _ = suite(PROTOCOL['school_seed'], 4)
        e, ledger = suite(PROTOCOL['exam_seed'], 16, [r['shape'] for r in a])
        self.assertEqual(len({r['shape'] for r in a+e}), 20)
        self.assertTrue(all(Space(r['seed']).oracle_distance() is not None for r in a+e))
        self.assertTrue(all(row['reason'] in ('accepted', 'duplicate', 'invalid_geometry') for row in ledger))

    def test_generator_exhaustion_not_fallback(self):
        with patch('echoai.nexus0.transfer3.rehearsal_v2.shape', return_value='duplicate'):
            with self.assertRaises(ValueError):
                suite(1, 1, ['duplicate'])

    def test_scratch_moves_with_frozen_model(self):
        row, _ = episode(policy.restore(policy.scratch()).snapshot(), 20264501)
        self.assertGreater(row['moves'], 0)
        self.assertTrue(row['model_unchanged'])
        self.assertEqual(row['collisions'], 0)
        self.assertEqual(row['reserve_violations'], 0)

    def test_learning_uses_actual_consequences(self):
        row, payload = episode(policy.restore(policy.scratch()).snapshot(), 20264401, learn=True)
        self.assertTrue(payload['q'])
        self.assertTrue(any('learning' in r for r in row['rows']))
        for record in row['rows']:
            if record['consequence']:
                self.assertEqual(record['consequence']['before'], record['observation']['odometry'])


if __name__ == '__main__':
    unittest.main()
