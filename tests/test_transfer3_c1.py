"""Plan C1: camera extrinsic calibration under two-family fusion."""
import ast
import unittest
from pathlib import Path

from echoai.nexus0.fusion1.core import UNKNOWN, unpack
from echoai.nexus0.transfer3 import bench_c1, calib_c1, camera_c1, costs_a2, policy, school_c1
from echoai.nexus0.transfer3 import space_a2, transport_c1
from echoai.nexus0.transfer3.planner_a2 import CostPlanner
from echoai.nexus0.transfer3.planner_c1 import CalibratedPlanner

SEED = bench_c1.PROTOCOL['development_seed']


def room(offset, seed=SEED):
    return camera_c1.OffsetRoom(seed, camera_c1.declared_body(), offset)


class Camera(unittest.TestCase):
    def test_zero_offset_reproduces_the_historical_scan(self):
        historical = space_a2.Room(SEED, camera_c1.declared_body())
        self.assertEqual(room((0, 0)).scan(), historical.scan())

    def test_the_camera_only_reports_cells_it_saw(self):
        world = room((1, 1))
        seen = {p for p in world.domain if world.visible(p)}
        frame = world.scan()
        for c in frame['cells']:
            depth = unpack(bytes.fromhex(c['depth']))[0]
            if depth == UNKNOWN:
                continue
            source = (c['position'][0]-1, c['position'][1]-1, c['position'][2])
            self.assertIn(source, seen)

    def test_lidar_is_truthful_and_untagged(self):
        world = room((1, -1))
        for c in world.scan()['cells']:
            lidar = unpack(bytes.fromhex(c['lidar']))[0]
            if lidar != UNKNOWN:
                self.assertEqual(lidar, int(tuple(c['position']) in world.solids))

    def test_offsets_outside_the_declared_family_are_refused(self):
        with self.assertRaises(ValueError):
            room((2, 0))

    def test_agent_candidates_match_the_declared_family(self):
        self.assertEqual(set(calib_c1.CANDIDATES), set(camera_c1.OFFSETS))


class Calibration(unittest.TestCase):
    def test_a_single_frame_identifies_every_offset(self):
        for offset in camera_c1.OFFSETS:
            for seed in range(SEED, SEED+6):
                estimate = calib_c1.estimate([room(offset, seed).scan()])
                self.assertEqual(estimate['offset'], list(offset), (offset, seed))

    def test_reregistration_never_touches_the_lidar(self):
        frame = room((1, 1)).scan()
        registered = calib_c1.reregister(frame, (1, 1))
        self.assertEqual([c['lidar'] for c in frame['cells']],
                         [c['lidar'] for c in registered['cells']])

    def test_zero_offset_is_the_identity(self):
        frame = room((0, 1)).scan()
        self.assertIs(calib_c1.reregister(frame, (0, 0)), frame)

    def test_payload_carries_no_map_or_geometry_channel(self):
        calib_c1.validate(calib_c1.nominal())
        with self.assertRaises(ValueError):
            calib_c1.validate(dict(calib_c1.nominal(), cells=[1]))
        with self.assertRaises(ValueError):
            calib_c1.validate(dict(calib_c1.nominal(), offset=[2, 0]))

    def test_estimate_needs_evidence(self):
        with self.assertRaises(ValueError):
            calib_c1.estimate([])


class Safety(unittest.TestCase):
    def run_agent(self, true_offset, believed, steps=40, seed=SEED):
        world = room(true_offset, seed)
        agent = CalibratedPlanner(policy.restore(policy.scratch()).snapshot(), world.goal,
                                  calib_c1.prior(believed), reserve=6)
        free = world.domain-world.solids
        for _ in range(steps):
            decision = agent.decide(world.scan())
            for p in agent.admitted():
                self.assertIn(tuple(p), free, (true_offset, believed))
            if decision['status'] not in ('moving', 'returning'):
                break
            world.step(bytes.fromhex(decision['wsp'])[13])
        return world

    def test_no_calibration_right_or_wrong_admits_an_occupied_cell(self):
        for true_offset in ((1, 1), (0, 1), (-1, 0)):
            for believed in ((0, 0), true_offset, (-true_offset[0], -true_offset[1])):
                world = self.run_agent(true_offset, believed)
                self.assertEqual(world.collisions, 0)

    def test_nominal_on_a_true_camera_is_the_historical_planner(self):
        for seed in range(SEED, SEED+4):
            traces = []
            for factory in ('historical', 'c1'):
                world = room((0, 0), seed)
                model = policy.restore(policy.scratch()).snapshot()
                agent = (CostPlanner(model, world.goal, costs_a2.nominal(), reserve=6)
                         if factory == 'historical' else
                         CalibratedPlanner(model, world.goal, calib_c1.nominal(), reserve=6))
                trace = []
                for _ in range(40):
                    decision = agent.decide(world.scan())
                    trace.append(decision['wsp'])
                    if decision['status'] not in ('moving', 'returning'):
                        break
                    world.step(bytes.fromhex(decision['wsp'])[13])
                traces.append(trace)
            self.assertEqual(traces[0], traces[1], seed)


class School(unittest.TestCase):
    def test_school_identifies_every_declared_offset(self):
        for offset in camera_c1.OFFSETS:
            school = school_c1.train(offset)
            self.assertTrue(school['identified'], offset)
            self.assertEqual(school_c1.replay(school), school['payload'])

    def test_replay_rejects_a_payload_that_does_not_follow_the_frames(self):
        school = school_c1.train((1, 1))
        school['payload'] = calib_c1.prior((0, 1))
        with self.assertRaises(ValueError):
            school_c1.replay(school)


class Isolation(unittest.TestCase):
    def test_agent_import_closure_never_reaches_the_world(self):
        here = Path(camera_c1.__file__).parent
        forbidden = {'camera_c1', 'school_c1', 'bench_c1', 'space_a2', 'rehearsal_v2',
                     'transport_c1', 'policy', 'rehearsal'}
        seen, queue = set(), ['planner_c1', 'calib_c1']
        while queue:
            name = queue.pop()
            if name in seen:
                continue
            seen.add(name)
            for node in ast.walk(ast.parse((here/f'{name}.py').read_text())):
                targets = []
                if isinstance(node, ast.ImportFrom):
                    targets = [(node.module or '').split('.')[-1]]+[a.name for a in node.names]
                elif isinstance(node, ast.Import):
                    targets = [a.name.split('.')[-1] for a in node.names]
                for target in targets:
                    self.assertNotIn(target, forbidden, f'{name} imports {target}')
                    if (here/f'{target}.py').exists():
                        queue.append(target)

    def test_transport_mounts_no_world(self):
        for forbidden in transport_c1.FORBIDDEN:
            self.assertFalse(any(m.endswith(forbidden) for m in transport_c1.MODULES), forbidden)
        mounted = sorted(m for m in transport_c1.MODULES if m.startswith('transfer3/'))
        self.assertEqual(mounted, ['transfer3/__init__.py', 'transfer3/calib_c1.py',
                                   'transfer3/costs_a2.py', 'transfer3/planner_a2.py',
                                   'transfer3/planner_c1.py'])


class Bench(unittest.TestCase):
    def rows(self, flags, energy=10):
        return [dict(seed=i, reached=bool(f), energy=energy, collisions=0, reserve_violations=0,
                     unsafe_admissions=0, false_facts=0, imagined_writes=0,
                     calibration_unchanged=True) for i, f in enumerate(flags)]

    def conditions(self, learned, nominal, prior=None):
        prior = prior or nominal
        return {'c': dict(nominal=self.rows(nominal), learned=self.rows(learned),
                          prior_x=self.rows(prior), prior_d=self.rows(prior))}

    def test_a_learned_arm_that_only_gains_passes_the_pilot(self):
        verdict = bench_c1.evaluate(self.conditions([1, 1, 1], [0, 0, 1]),
                                    {'s': dict(energy=0)}, confirm=False)
        self.assertTrue(verdict['passes'])
        self.assertFalse(verdict['significance_applied'])

    def test_a_single_new_failure_fails(self):
        verdict = bench_c1.evaluate(self.conditions([1, 1, 0], [0, 0, 1]),
                                    {'s': dict(energy=0)}, confirm=False)
        self.assertFalse(verdict['checks']['no_new_failures'])

    def test_amortisation_counts_the_school(self):
        verdict = bench_c1.evaluate(self.conditions([1, 1, 1], [0, 0, 1]),
                                    {'s': dict(energy=1)}, confirm=False)
        self.assertFalse(verdict['checks']['amortised'])

    def test_an_unsafe_admission_fails_the_hard_constraints(self):
        conditions = self.conditions([1, 1, 1], [0, 0, 1])
        conditions['c']['learned'][0]['unsafe_admissions'] = 1
        verdict = bench_c1.evaluate(conditions, {'s': dict(energy=0)}, confirm=False)
        self.assertFalse(verdict['checks']['hard_constraints'])

    def test_matching_a_fixed_prior_is_not_enough(self):
        verdict = bench_c1.evaluate(self.conditions([1, 1, 1], [0, 0, 1], prior=[1, 1, 1]),
                                    {'s': dict(energy=0)}, confirm=False)
        self.assertFalse(verdict['checks']['beyond_fixed_priors'])

    def test_confirmation_requires_a_passing_isolated_pilot(self):
        with self.assertRaises(ValueError):
            bench_c1.run('confirm', pilot=None)
        with self.assertRaises(ValueError):
            bench_c1.run('confirm', pilot=dict(stage='pilot', isolated=False,
                                                verdict=dict(passes=True)))

    def test_protocol_keeps_alpha_and_fixed_priors(self):
        self.assertEqual(bench_c1.PROTOCOL['alpha_denominator'], 240)
        self.assertFalse(bench_c1.PROTOCOL['learning_in_exam'])
        self.assertFalse(bench_c1.PROTOCOL['campaign_enabled'])
        self.assertEqual(set(bench_c1.PRIORS.values()), {(1, 0), (1, 1)})

    def test_true_home_costs_are_uniform_and_start_at_zero(self):
        world = room((0, 0))
        home = bench_c1.true_home_costs(world)
        self.assertEqual(home[world.start], 0)
        self.assertTrue(all(v % 4 == 0 for v in home.values()))

    def test_probe_rooms_are_excluded_from_confirmation(self):
        probes = bench_c1.probe_shapes()
        self.assertTrue(probes)
        self.assertTrue(probes <= set(bench_c1.past_shapes()))


if __name__ == '__main__':
    unittest.main()
