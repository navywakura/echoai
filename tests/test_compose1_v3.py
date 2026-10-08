"""Behavioral regressions for composition, evidence and the physical boundary."""
import copy
import unittest

from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1.space import DIRECTIONS
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.compose1_v3.functional import mission
from echoai.nexus0.compose1_v3.perception import classify, project
from echoai.nexus0.compose1_v3.development import train
from echoai.nexus0.fusion1.core import packet


class TestComposeV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = train()

    def test_horizon_changes_cost_with_same_information(self):
        full = mission(self.snapshot, 20261902, 'dynamic', 'echo32')
        short = mission(self.snapshot, 20261902, 'dynamic', 'one_step')
        self.assertTrue(full['reached'] and short['reached'])
        self.assertLess(full['steps'], short['steps'])
        self.assertEqual(full['model_initial_sha256'], short['model_initial_sha256'])
        self.assertEqual(full['collisions']+short['collisions'], 0)

    def test_unknown_effects_do_not_become_motion(self):
        agent = Composer(Effects().snapshot(), (2, 0, 0))
        frame = dict(now_ns=0, odometry=[0, 0, 0], energy=240,
                     station_observed=False, cells=[])
        response = agent.decide(frame)
        self.assertEqual(bytes.fromhex(response['wsp'])[1], 14)
        self.assertNotEqual(response['status'], 'reached')

    def test_search_does_not_write_model(self):
        for mode in ('echo8', 'echo32', 'one_step', 'conventional'):
            result = mission(self.snapshot, 20261901, 'static', mode)
            self.assertTrue(result['model_unchanged'])
            self.assertEqual(result['imagined_writes'], 0)
            self.assertLessEqual(result['depth_max'], 1 if mode == 'one_step' else 4)
            self.assertLessEqual(result['expansions_max'], 8 if mode == 'echo8' else 32)

    def test_low_energy_aborts_at_home(self):
        row = mission(self.snapshot, 20261904, 'low_energy', 'echo32')
        self.assertTrue(row['ended_home'])
        self.assertEqual(row['steps'], 0)
        self.assertFalse(row['reached'])

    def test_new_access_replaces_an_old_but_still_admissible_plan(self):
        agent = Composer(self.snapshot, (2, 0, 0))
        agent.pending = [2]  # Old northward alternative remains clear.
        frame = dict(now_ns=0, odometry=[0, 0, 0], energy=240,
                     station_observed=False, cells=[dict(position=list(p),
                     depth=packet(0, 40).hex(), lidar=packet(0, 40).hex())
                     for p in ((0, 0, 0), (0, 1, 0), (1, 0, 0), (2, 0, 0))])
        reply = agent.decide(frame)
        self.assertEqual(reply['prediction'], [1, 0, 0])
        self.assertEqual(reply['plan'], [0, 0])

    def test_negative_software_controls_are_observable(self):
        from echoai.nexus0.compose1_v3.controls import software
        checks = software()
        self.assertTrue(all(checks.values()), checks)

    def test_wall_boundary_does_not_occupy_free_target_disc(self):
        rays = dict(angles_mrad=list(range(-400, 401, 10)), ranges_mm=[4050]*81)
        # Wall is 1050 mm beyond target centre, outside its 900 mm envelope.
        self.assertEqual(classify((3000, 0), (0, 0), 0, rays), 0)
        rays['ranges_mm'] = [3500]*81
        self.assertEqual(classify((3000, 0), (0, 0), 0, rays), 1)

    def test_no_return_and_incomplete_coverage_are_unknown(self):
        rays = dict(angles_mrad=list(range(-400, 401, 10)), ranges_mm=[-1]*81)
        self.assertEqual(classify((3000, 0), (0, 0), 0, rays), -1)
        rays = dict(angles_mrad=[0], ranges_mm=[6000])
        self.assertEqual(classify((3000, 0), (0, 0), 0, rays), -1)

    def test_private_world_field_rejected(self):
        with self.assertRaises(ValueError):
            project(dict(world_id=7), 240)

    def test_physical_capture_is_not_refreshed_by_query(self):
        agent = Composer(self.snapshot, (2, 0, 0))
        frame = dict(physical=True, now_ns=1_000_000_000, odometry=[0, 0, 0],
                     energy=240, station_observed=False, cells=[dict(position=[1, 0, 0], sources=[
                         dict(source=s, wsp=packet(0, 40).hex(), capture_ns=1,
                              delivered_ns=1, raw_sha256='a'*64) for s in ('depth', 'lidar')])])
        agent.update(frame)
        self.assertFalse(agent.free((1, 0, 0)))
        frame['cells'][0]['sources'] = [dict(r, capture_ns=1_000_000_000,
                                            delivered_ns=1_000_000_000)
                                      for r in frame['cells'][0]['sources']]
        agent.update(frame)
        self.assertTrue(agent.free((1, 0, 0)))
        self.assertEqual(len(agent.cells[(1, 0, 0)].records), 4)


if __name__ == '__main__':
    unittest.main()
