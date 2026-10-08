"""DRONE-3: gates, gateway, supervisor, calibration, energy and agent contracts."""
import json
import unittest
from pathlib import Path

from echoai.core.wsp import pack
from echoai.nexus0.drone3 import contract as c
from echoai.nexus0.drone3 import gates
from echoai.nexus0.drone3.calibration import provenance, reregister, abstract
from echoai.nexus0.drone3.energy import battery_sample, guard_frame, fit
from echoai.nexus0.drone3.gateway import CellGateway
from echoai.nexus0.drone3.supervisor import MissionSupervisor
from echoai.nexus0.fusion1.core import packet
from echoai.nexus0.power1.core import Guard

ECHOAI = Path(__file__).resolve().parents[1]
POWER = {'unit': 'sim_u', 'costs': {
    '0': {'n': 8, 'nominal': 12, 'maximum': 15, 'upper': 19},
    '1': {'n': 8, 'nominal': 12, 'maximum': 15, 'upper': 19},
    'land': {'n': 8, 'nominal': 24, 'maximum': 27, 'upper': 34}}}
NOW = 10_000_000_000


def move(action, slot=0):
    return pack(src=2, rel=11, dst=5, time=8, E=dict(C=80), domain=9, generator=8, style=action, slot=slot).hex()


def stop(slot=0):
    return pack(src=2, rel=14, dst=5, time=8, E=dict(C=0), domain=9, generator=8, style=6, slot=slot).hex()


def telemetry(position=(0, 0, 2500), received=NOW-10_000_000, speed=0, **flags):
    frame = dict(received_ns=received, position_mm=list(position), speed_mm_s=speed,
                 armed=True, authority=True, failsafe=False)
    frame.update(flags)
    return frame


def request(action=0, seq=1, published=NOW-50_000_000, prediction=(1, 0, 0), wsp=None):
    return dict(wsp=wsp or move(action), seq=seq, published_ns=published, prediction=list(prediction))


def ack(sent, delta=100_000_000, result=0, system=1, component=1, command=192):
    return dict(system=system, component=component, command=command, result=result, received_ns=sent+delta)


def physical(cell_values, now=NOW, capture=None, depth=None):
    """One projected physical frame: {cell: lidar_value} with optional camera values."""
    capture = NOW-40_000_000 if capture is None else capture
    cells = []
    for (x, y), value in cell_values.items():
        sources = [dict(source='lidar', wsp=packet(value, 40 if value != -1 else 0).hex(),
                        capture_ns=capture, delivered_ns=capture+5_000_000, raw_sha256='0'*64)]
        camera = value if depth is None else depth.get((x, y), value)
        sources.append(dict(source='depth', wsp=packet(camera, 40 if camera != -1 else 0).hex(),
                            capture_ns=capture, delivered_ns=capture+5_000_000, raw_sha256='1'*64))
        cells.append(dict(position=[x, y, 0], sources=sources))
    return dict(physical=True, now_ns=now, odometry=[0, 0, 0], energy=240, station_observed=False, cells=cells)


class Contract(unittest.TestCase):
    def test_executable_intentions(self):
        self.assertEqual(c.intention(move(2, slot=9)), ('move', 2))
        self.assertEqual(c.intention(c.inspect_wsp(1)), ('inspect', 8))
        self.assertEqual(c.intention(stop(slot=4)), ('stop', 6))

    def test_everything_else_is_refused(self):
        bad = [move(4), '00'*16, move(0)[:30], pack(src=2, rel=11, dst=5, time=8, E=dict(C=79), domain=9,
               generator=8, style=0).hex(), pack(src=2, rel=11, dst=5, time=8, E=dict(C=80), domain=9,
               generator=7, style=0).hex(), pack(src=2, rel=14, dst=5, time=8, E={}, domain=9, generator=8,
               style=7, slot=3).hex()]
        for w in bad:
            with self.assertRaises(ValueError):
                c.intention(w)


class Gateway(unittest.TestCase):
    def test_bounded_goal_then_ack_then_three_settled_samples(self):
        g = CellGateway()
        d = g.propose(request(), telemetry(), NOW)
        self.assertTrue(d['allowed'])
        self.assertEqual(d['target_mm'], [3000, 0, 2500])
        self.assertEqual(d['yaw_mrad'], 1571)
        self.assertTrue(g.acknowledge(ack(NOW), NOW+100_000_000))
        self.assertEqual(g.state, 'executing')
        t = NOW+200_000_000
        for i in range(2):
            self.assertEqual(g.observe(telemetry((3000, 0, 2500), received=t+i), t+i+1), 'executing')
        self.assertEqual(g.observe(telemetry((3000, 0, 2500), received=t+5), t+6), 'complete')
        self.assertTrue(g.release())
        self.assertEqual(g.state, 'ready')

    def test_ack_is_not_arrival(self):
        g = CellGateway()
        g.propose(request(), telemetry(), NOW)
        g.acknowledge(ack(NOW), NOW+100_000_000)
        self.assertEqual(g.observe(telemetry((1000, 0, 2500), received=NOW+150_000_000), NOW+160_000_000),
                         'executing')
        mutant = CellGateway(mutant='ack_is_arrival')
        mutant.propose(request(), telemetry(), NOW)
        mutant.acknowledge(ack(NOW), NOW+100_000_000)
        self.assertEqual(mutant.state, 'complete')

    def test_refusals(self):
        cases = [
            (request(published=NOW-300_000_000), telemetry(), 'expired'),
            (request(prediction=(0, 1, 0)), telemetry(), 'prediction_mismatch'),
            (request(wsp=stop()), telemetry(), 'not_a_goal'),
            (request(wsp='ff'*16), telemetry(), 'wsp'),
            (request(), telemetry(authority=False), 'authority'),
            (request(), telemetry(failsafe=True), 'authority'),
            (request(), telemetry(received=NOW-300_000_000), 'telemetry'),
            (request(prediction=(5, 0, 0)), telemetry((12000, 0, 2500)), 'envelope'),
            (request(), telemetry((0, 0, 1000)), 'envelope'),
        ]
        for req, frame, reason in cases:
            g = CellGateway()
            self.assertEqual(g.propose(req, frame, NOW)['reason'], reason, reason)

    def test_sequence_must_increase_and_one_goal_in_flight(self):
        g = CellGateway()
        self.assertTrue(g.propose(request(seq=5), telemetry(), NOW)['allowed'])
        self.assertEqual(g.propose(request(seq=6), telemetry(), NOW)['reason'], 'session_not_ready')
        g.state, g.pending = 'ready', None
        self.assertEqual(g.propose(request(seq=5), telemetry(), NOW)['reason'], 'sequence')

    def test_ack_identity_and_rejection_latch(self):
        g = CellGateway()
        g.propose(request(), telemetry(), NOW)
        self.assertFalse(g.acknowledge(ack(NOW, system=2), NOW+100_000_000))
        self.assertFalse(g.acknowledge(ack(NOW, command=176), NOW+100_000_000))
        self.assertFalse(g.acknowledge(ack(NOW, delta=-1), NOW+100_000_000))
        self.assertFalse(g.acknowledge(ack(NOW, result=4), NOW+100_000_000))
        self.assertEqual(g.state, 'fault')
        self.assertFalse(g.release())
        self.assertEqual(g.propose(request(seq=2), telemetry(), NOW)['reason'], 'session_not_ready')

    def test_timeouts_fault(self):
        g = CellGateway()
        g.propose(request(), telemetry(), NOW)
        self.assertEqual(g.observe(telemetry(received=NOW+2_100_000_000), NOW+2_100_000_001), 'fault')

    def test_inspection_holds_the_cell_and_turns(self):
        g = CellGateway()
        d = g.propose(request(wsp=c.inspect_wsp(2), prediction=(0, 0, 0)), telemetry(), NOW)
        self.assertEqual((d['kind'], d['target_mm'], d['yaw_mrad']), ('inspect', [0, 0, 2500], 3142))

    def test_mutants_accept_what_the_gateway_refuses(self):
        self.assertTrue(CellGateway(mutant='no_ttl').propose(request(published=NOW-900_000_000),
                                                             telemetry(), NOW)['allowed'])
        self.assertTrue(CellGateway(mutant='no_geofence').propose(request(prediction=(5, 0, 0)),
                                                                  telemetry((12000, 0, 2500)), NOW)['allowed'])


class Gates(unittest.TestCase):
    def test_epistemic_needs_two_fresh_families(self):
        free = physical({(1, 0): 0})
        self.assertTrue(gates.epistemic(free, 'move', (1, 0), NOW, [0, 0])['allowed'])
        conflict = physical({(1, 0): 0}, depth={(1, 0): 1})
        self.assertFalse(gates.epistemic(conflict, 'move', (1, 0), NOW, [0, 0])['allowed'])
        stale = physical({(1, 0): 0}, capture=NOW-300_000_000)
        self.assertFalse(gates.epistemic(stale, 'move', (1, 0), NOW, [0, 0])['allowed'])
        unseen = physical({(2, 0): 0})
        self.assertFalse(gates.epistemic(unseen, 'move', (1, 0), NOW, [0, 0])['allowed'])
        occupied = physical({(1, 0): 1})
        self.assertFalse(gates.epistemic(occupied, 'move', (1, 0), NOW, [0, 0])['allowed'])
        self.assertTrue(gates.epistemic(occupied, 'move', (1, 0), NOW, [0, 0], mutant='admit_unknown')['allowed'])
        self.assertTrue(gates.epistemic(unseen, 'inspect', (0, 0), NOW, [0, 0])['allowed'])

    def test_calibration_changes_which_camera_record_speaks(self):
        frame = physical({(1, 0): 0, (2, 0): 0}, depth={(1, 0): 1, (2, 0): 0})
        self.assertFalse(gates.epistemic(frame, 'move', (1, 0), NOW, [0, 0])['allowed'])
        # With a (1, 0) mount the camera record tagged (2, 0) describes (1, 0).
        self.assertTrue(gates.epistemic(frame, 'move', (1, 0), NOW, [1, 0])['allowed'])

    def test_energy_counts_step_return_landing_and_reserve(self):
        battery = dict(capture_ns=NOW-10_000_000, remaining=200, capacity=1000, unit='sim_u')
        visited = [(0, 0), (1, 0), (2, 0)]
        ok = gates.energy(POWER, battery, NOW, visited, (3, 0), (0, 0))
        self.assertEqual((ok['back_cells'], ok['required']), (3, 19+3*19+34+40))
        self.assertTrue(ok['allowed'])
        low = dict(battery, remaining=149)
        self.assertFalse(gates.energy(POWER, low, NOW, visited, (3, 0), (0, 0))['allowed'])
        self.assertEqual(gates.energy(POWER, dict(battery, capture_ns=NOW-300_000_000), NOW, visited,
                                      (3, 0), (0, 0))['reason'], 'battery_unknown')
        self.assertEqual(gates.energy(POWER, battery, NOW, visited, (5, 5), (0, 0))['reason'], 'return_unknown')
        self.assertTrue(gates.energy(POWER, low, NOW, visited, (3, 0), (0, 0), mutant='no_reserve')['allowed'])


class Supervision(unittest.TestCase):
    def health(self, **frame):
        return dict(now_ns=NOW, sensor_ns=NOW-30_000_000, frame=telemetry(**frame), worker_alive=True)

    def evidence(self, value=0, remaining=500):
        return dict(frame=physical({(1, 0): value}),
                    battery=dict(capture_ns=NOW-10_000_000, remaining=remaining, capacity=1000, unit='sim_u'))

    def test_all_gates_pass(self):
        s = MissionSupervisor(POWER, [0, 0], (0, 0))
        d = s.submit(request(), self.health(), self.evidence())
        self.assertTrue(d['allowed'])
        self.assertEqual([k for k, v in d['gates'].items() if v and v.get('allowed')],
                         ['health', 'epistemic', 'energy', 'gateway'])

    def test_each_refusal_latches(self):
        for evidence, health, reason in [(self.evidence(value=-1), self.health(), 'epistemic_block'),
                                          (self.evidence(remaining=100), self.health(), 'energy_block'),
                                          (self.evidence(), dict(self.health(), worker_alive=False), 'process_dead'),
                                          (self.evidence(), dict(self.health(), sensor_ns=NOW-400_000_000),
                                           'sensor_stale')]:
            s = MissionSupervisor(POWER, [0, 0], (0, 0))
            d = s.submit(request(), health, evidence)
            self.assertEqual((d['allowed'], s.reason), (False, reason))
            self.assertFalse(s.submit(request(seq=2), self.health(), self.evidence())['allowed'])

    def test_mutants_let_faults_through(self):
        s = MissionSupervisor(POWER, [0, 0], (0, 0), mutant='no_liveness')
        self.assertTrue(s.check(dict(self.health(), worker_alive=False)))
        s = MissionSupervisor(POWER, [0, 0], (0, 0), mutant='no_latch')
        s.check(dict(self.health(), sensor_ns=NOW-400_000_000))
        self.assertTrue(s.check(dict(self.health(), now_ns=NOW+1)))
        s = MissionSupervisor(POWER, [0, 0], (0, 0), mutant='no_energy')
        self.assertTrue(s.submit(request(), self.health(), self.evidence(remaining=100))['allowed'])


class Energy(unittest.TestCase):
    def test_voltage_band_to_per_mille(self):
        raw = dict(capture_ns=5, delivered_ns=5, voltage_mv=15300, empty_mv=14760, full_mv=16200)
        self.assertEqual(battery_sample(raw)['remaining'], (15300-14760)*1000//1440)
        self.assertEqual(battery_sample(dict(raw, voltage_mv=14000))['remaining'], 0)
        self.assertIsNone(battery_sample(dict(raw, voltage_mv=65535)))
        self.assertIsNone(battery_sample(dict(raw, extra=1)))

    def test_guard_frame_is_valid_for_power1(self):
        guard = Guard(POWER)
        battery = dict(capture_ns=NOW-1, remaining=900, capacity=1000, unit='sim_u')
        out = guard.decide(guard_frame(NOW, battery, (0, 0), (4, 0), (0, 0), 0, False))
        self.assertEqual(out['reason'], 'continue')
        guard = Guard(POWER)
        low = dict(battery, remaining=150)
        self.assertEqual(guard.decide(guard_frame(NOW, low, (0, 0), (4, 0), (0, 0), 0, False))['reason'],
                         'land_home')

    def test_fit_needs_eight_confirmed_receipts_per_phase(self):
        rows = [dict(phase=p, before=900, after=900-v, elapsed_ms=4000) for p in ('0', '1', 'land')
                for v in range(10, 18)]
        model = fit(rows)
        self.assertEqual(model['costs']['0'], dict(n=8, nominal=14, maximum=17, upper=22))


class Calibration(unittest.TestCase):
    def test_provenance_binds_the_certified_campaign(self):
        record = provenance()
        self.assertEqual(record['offset'], [0, 0])
        self.assertEqual(record['certificate_sha256'][:8], '8c77aead')

    def test_tampered_campaign_is_refused(self):
        import shutil
        import tempfile
        src = ECHOAI/'lab/transfer3/campaign-c1-v2'
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('certificate.json', 'freeze.json'):
                shutil.copyfile(src/name, Path(tmp)/name)
            data = json.loads((Path(tmp)/'freeze.json').read_text())
            data['payloads']['0,0']['offset'] = [1, 0]
            (Path(tmp)/'freeze.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                provenance(tmp)

    def test_reregister_moves_only_camera_records(self):
        frame = physical({(1, 0): 0, (2, 0): 1})
        same = reregister(frame, [0, 0])
        self.assertIs(same, frame)
        moved = reregister(frame, [1, 0])
        cells = {tuple(x['position']): sorted(r['source'] for r in x['sources']) for x in moved['cells']}
        self.assertEqual(cells[(0, 0, 0)], ['depth'])
        self.assertEqual(cells[(2, 0, 0)], ['lidar'])
        self.assertEqual(abstract(frame)['cells'][0]['lidar'], packet(0, 40).hex())
        with self.assertRaises(ValueError):
            reregister(frame, [2, 0])


if __name__ == '__main__':
    unittest.main()


class Probes(unittest.TestCase):
    FRAME = dict(received_ns=NOW-10_000_000, position_mm=[0, 0, 2500], speed_mm_s=0,
                 armed=True, authority=True, failsafe=False)

    def run_probes(self, **override):
        from echoai.nexus0.drone3 import probes
        return probes.run(self.FRAME, NOW, 1, model=POWER, offset=[0, 0], **override)

    def test_every_probe_is_refused(self):
        out = self.run_probes()
        from echoai.nexus0.drone3 import probes
        self.assertEqual([r['name'] for r in out], list(probes.NAMES))
        self.assertEqual([r['name'] for r in out if r['allowed']], [])

    def test_each_mutant_opens_a_probe(self):
        cases = {
            'no_ttl': dict(gateway=lambda s, k: CellGateway(s, k, mutant='no_ttl')),
            'no_geofence': dict(gateway=lambda s, k: CellGateway(s, k, mutant='no_geofence')),
            'ack_is_arrival': dict(gateway=lambda s, k: CellGateway(s, k, mutant='ack_is_arrival')),
            'no_sequence': dict(gateway=lambda s, k: CellGateway(s, k, mutant='no_sequence')),
            'admit_unknown': dict(epistemic=lambda *a, **k: gates.epistemic(*a, mutant='admit_unknown')),
            'no_reserve': dict(energy=lambda *a, **k: gates.energy(*a, mutant='no_reserve')),
            'no_epistemic': dict(supervisor=lambda *a: MissionSupervisor(*a, mutant='no_epistemic')),
            'no_energy': dict(supervisor=lambda *a: MissionSupervisor(*a, mutant='no_energy')),
        }
        for name, override in cases.items():
            self.assertTrue(any(r['allowed'] for r in self.run_probes(**override)), name)


class Protocol(unittest.TestCase):
    def test_rooms_are_fresh_geometries_and_blocks_are_paired(self):
        from echoai.nexus0.drone3 import protocol
        a = protocol.rooms('development')
        geoms = {protocol.geometry(s) for s in a}
        b = protocol.rooms('validation', excluded=geoms)
        self.assertEqual(len(geoms), 3)
        self.assertTrue(geoms.isdisjoint({protocol.geometry(s) for s in b}))
        plan = protocol.flights('validation', POWER, [0, 0], excluded=geoms)
        self.assertEqual(len(plan), 12)
        self.assertEqual([spec['physics_seed'] % 10 for _, spec in plan[:4]], [0, 1, 2, 3])
        self.assertEqual({spec['fault']['kind'] for _, spec in plan if spec['fault']}, set(protocol.FAULTS))
        low = [spec for _, spec in plan if spec['condition'] == 'low_reserve']
        self.assertTrue(all(0 < s['handover_remaining'] < protocol.oracle_cost(s['seed'], POWER) for s in low))


class Intervention(unittest.TestCase):
    def test_home_side_excludes_the_gap_and_the_far_side(self):
        from echoai.nexus0.compose1_v3.space import Space
        from echoai.nexus0.drone3.session import intervention
        for seed in (20266001, 20266002, 20266003, 20267001):
            space = Space(seed, 'dynamic')
            change = intervention(space)
            old_gap = [round(v/3) for v in change['target'][:2]]
            new_gap = list(space.rotate((space.wall_x, -space.gap_y, 0))[:2])
            self.assertNotIn(old_gap, change['home_side'], seed)
            self.assertNotIn(new_gap, change['home_side'], seed)
            self.assertIn([0, 0], change['home_side'], seed)
            for cell in change['home_side']:
                x, y = cell
                for _ in range(4-space.rotation):    # back to unrotated coordinates
                    x, y = y, -x
                self.assertLess(x, space.wall_x, (seed, cell))
            self.assertEqual(change['trigger'], 'first_admitted_from_home_side')

    def test_the_moved_barrier_is_the_one_that_opens_the_new_gap(self):
        from echoai.nexus0.compose1_v3.space import Space
        from echoai.nexus0.drone3.session import intervention
        space = Space(20266003, 'dynamic')
        change = intervention(space)
        index = int(change['entity'].split('_')[1])
        self.assertEqual(sorted(space.solids)[index], space.rotate((space.wall_x, -space.gap_y, 0)))
        self.assertEqual([round(v/3) for v in change['target'][:2]],
                         list(space.rotate((space.wall_x, space.gap_y, 0))[:2]))
