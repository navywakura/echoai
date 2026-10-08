"""SENSOR-1S: the rig, the consumer, the geometry, the evaluator, and the
lying adapters an independent reviewer built before the lock.

No flight here. Real development evidence in lab/sensor1s/dev is read,
never written. Synthetic frames go through the real consumer script.
"""
import copy
import hashlib
import json
import math
import subprocess
import sys
import unittest

from echoai.nexus0.sensor1s import campaign, contract, evaluate as ev, model, session
from echoai.nexus0.flight1s_v6 import contract as v6
from echoai.nexus0.flight1s_v6 import campaign as v6c
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy

DEV = c.ECHOAI/'lab/sensor1s/dev'
SOURCES = tuple(contract.SOURCES)


def frame(header, payload):
    hb = json.dumps(header, sort_keys=True).encode()
    return len(hb).to_bytes(4, 'big') + hb + len(payload).to_bytes(4, 'big') + payload


def header(source, seq, capture, delivered, payload, gap=0, status='ok', **extra):
    h = dict(v=2, source=source, seq=seq, capture_ns=capture, delivered_ns=delivered, gap=gap,
             status=status, noise_ref='x', shape=[len(payload)], format='u8',
             payload_len=len(payload), payload_sha256=hashlib.sha256(payload).hexdigest())
    h.update(extra)
    return h


def consume(data):
    pr = subprocess.run([sys.executable, str(model.HERE/'assets/consumer.py')], input=data,
                        capture_output=True, timeout=60)
    return json.loads(pr.stderr.decode().strip().splitlines()[-1])


class Packages:
    tmp = byid = None

    @classmethod
    def get(cls, pid):
        if cls.byid is None:
            cls.tmp, pk = legacy.generate_suite_unique()
            cls.byid = {g.package_id: g for g in pk}
        return cls.byid[pid]


def load(label):
    d = DEV/label
    s = json.loads((d/'sensors.json').read_text())
    return dict(s=s, trace=json.loads((d/'episode.json').read_text()),
                P=ev.load_private(d/'private'/(label+'.jsonl')),
                T=ev.load_transcript(d/'transcript'/(label+'.jsonl')))


def evaluate(E, cond, P=None, T=None, tally=None, fwd=None):
    g = ev.episode(E['trace'], P or E['P'], T if T is not None else E['T'], tally or E['s']['consumer'],
                   fwd or E['s']['forwarder'], Packages.get(E['s']['package_id']).package,
                   E['s']['spec'], condition=cond, bounds=contract.LATENCY_P99_BOUND_NS)
    return ev.summarize(g)


def status(summary):
    return {k: v['status'] for k, v in summary.items()}


class RigTests(unittest.TestCase):
    def test_rig_is_the_stock_x500_plus_sensor_elements(self):
        chk = model.check()
        self.assertTrue(chk['ok'], chk)
        rig = (model.OUT/'x500_sensor1s/model.sdf').read_text()
        stock = (model.STOCK/'x500/model.sdf').read_text()
        self.assertEqual(rig.replace('x500_sensor1s_base', 'x500_base').replace(
            "name='x500_sensor1s'", "name='x500'"), stock)
        self.assertEqual(model.BLOCK.count('<sensor '), 3)
        self.assertNotIn('<mass>', model.BLOCK)
        self.assertNotIn('<link', model.BLOCK)

    def test_flight_is_v6_but_for_the_body_name(self):
        cfg, old = contract.configuration(), v6.protocol()['configuration']
        self.assertEqual({k for k in cfg if cfg[k] != old[k]}, {'body', 'disturbance', 'profile'})
        self.assertEqual(dict(cfg['body'], model='x500'), old['body'])
        self.assertEqual(dict(cfg['disturbance'], link='x500_0::base_link'), old['disturbance'])

    def test_schedule_is_deterministic_and_private(self):
        self.assertEqual(contract.schedule(7, True), contract.schedule(7, True))
        self.assertNotEqual(contract.schedule(7, True), contract.schedule(8, True))
        self.assertEqual(contract.schedule(7, False), {s: [] for s in contract.SOURCES})
        for items in contract.schedule(7, True).values():
            self.assertEqual(sorted(i['kind'] for i in items), sorted(contract.FAULTS))
        with self.assertRaises(ValueError):
            contract.spec({}, 'invented')


class ConsumerTests(unittest.TestCase):
    def test_counts_what_it_is_told_and_checks_what_it_can(self):
        p = [bytes([i]) * 8 for i in range(6)]
        data = b''.join([
            frame(header('imu', 0, 0, 1, p[0]), p[0]),
            frame(header('imu', 1, 12, 13, p[1], gap=2), p[1]),
            frame(header('imu', 2, 12, 14, p[1], status='stale'), p[1]),
            frame(header('imu', 3, 16, 17, p[2]), b'\xff' + p[2][1:]),         # corrupt on the wire
            frame(header('imu', 5, 20, 21, p[3]), p[3]),                        # seq break
            frame(header('imu', 6, 18, 22, p[4]), p[4]),                        # time goes back
            frame(header('imu', 7, 24, 25, p[5], pose=[1, 2, 3]), p[5]),        # extra field
        ])
        t = consume(data)
        imu = t['sources']['imu']
        self.assertEqual((t['frames'], t['schema_errors'], t['truncated']), (7, 1, False))
        self.assertEqual((imu['n'], imu['gap_sum'], imu['stale'], imu['invalid']), (6, 2, 1, 1))
        self.assertEqual((imu['seq_breaks'], imu['non_monotonic']), (1, 1))

    def test_truncated_stream_is_reported(self):
        p = b'abcd'
        t = consume(frame(header('rgb', 0, 0, 0, p), p)[:-2])
        self.assertTrue(t['truncated'])

    def test_real_tallies_are_what_the_transcript_implies(self):
        for label in ('devA3', 'devA4', 'devM-leak_pose'):
            E = load(label)
            self.assertEqual(ev.mirror_tally(E['T']), E['s']['consumer'], label)


class GeometryTests(unittest.TestCase):
    solids = [((1.0, -1.0, -1.0), (2.0, 1.0, 1.0))]

    def test_cast_hits_face_and_refuses_edges_and_grazing(self):
        self.assertAlmostEqual(ev.cast((0, 0, 0), (1, 0, 0), self.solids), 1.0)
        self.assertIsNone(ev.cast((0, 0.99, 0), (1, 0, 0), self.solids))           # 10 mm from an edge
        self.assertEqual(ev.cast((0, 0, 0), (-1, 0, 0), self.solids), math.inf)
        d = (0.1/math.hypot(0.1, 0.995), 0.995/math.hypot(0.1, 0.995), 0)
        self.assertIsNone(ev.cast((0.9, -0.5, 0), d, self.solids))                 # grazes x=1

    def test_residuals_are_zero_for_exact_measurements(self):
        body = [0, -0.12, -0.03, -0.242, 0.0, 0.0, 0.0]         # sensor origin at the world origin
        ranges = [ev.cast((0, 0, 0), (math.cos(a), math.sin(a), 0), self.solids) for a in (0.0, 0.1)]
        lidar = dict(sample=dict(angle_min=0.0, angle_step=0.1, ranges=ranges), body=body)
        self.assertEqual([round(r, 9) for r in ev.lidar_residuals(lidar, self.solids)], [0.0, 0.0])
        f = 80 / math.tan(0.6)
        vals = []
        for u in range(160):
            cam = (1.0, -(u + 0.5 - 80) / f, -0.5 / f)
            n = math.sqrt(sum(x*x for x in cam))
            t = ev.cast((0, 0, 0), tuple(x/n for x in cam), self.solids)
            vals.append(t / n if t is not None and math.isfinite(t) else math.inf)
        res = ev.depth_residuals(dict(sample=dict(row=60, values=vals), body=body), self.solids)
        self.assertGreater(len(res), 50)
        self.assertLess(max(abs(r) for r in res), 1e-9)

    def test_within_beam_scatter_ignores_a_constant_geometric_error(self):
        # 3 beams with 7 mm of fixed error each, plus +-10 mm alternating noise.
        samples = [(b, t + 0.007 + (0.01 if k % 2 else -0.01), t)
                   for b, t in ((0, 2.0), (1, 3.0), (2, 4.0)) for k in range(40)]
        acc = ev.within_beam(samples)
        ok, st = ev.noise_verdict(acc, 0.01, ev.LIMITS, 50)
        self.assertTrue(ok)
        self.assertAlmostEqual(st['bias_m'], 0.007)
        self.assertAlmostEqual(st['ratio'], math.sqrt(40/39), places=6)


class EvidenceTests(unittest.TestCase):
    def test_real_faulted_flight_and_force_free_control_pass(self):
        self.assertEqual(set(status(evaluate(load('devA3'), 'perturbed')).values()), {'pass'})
        self.assertEqual(set(status(evaluate(load('devA4'), 'nominal')).values()), {'pass'})

    def test_real_mutants_fail_their_specific_case(self):
        for name, target in campaign.TARGET.items():
            summary = evaluate(load(f'devM-{name}'), 'perturbed')
            self.assertTrue(campaign.mutant_caught(name, summary[target]['cases']), name)
            self.assertEqual(summary['execution']['status'], 'pass', name)


class AttackTests(unittest.TestCase):
    """The reviewer's lying adapters, rebuilt from real devA3/devA4 evidence:
    headers are rewritten, the transcript, adapter log and consumer tally
    follow, and the real evaluator judges."""

    @classmethod
    def setUpClass(cls):
        cls.A3, cls.A4 = load('devA3'), load('devA4')

    def rebuild(self, E, frames, cond, P=None):
        T, sends = [], []
        marks = session.canaries(Packages.get(E['s']['package_id']))
        hits = set()
        for f in frames:
            hb = json.dumps(f['send']['header'], sort_keys=True, separators=(',', ':'))
            T.append(dict(h=hb, wire=f['wire'],
                          len=contract.EXPECTED.get(f['send']['src'], {}).get('payload_len', 0)))
            sends.append(f['send'])
            hits |= {m for m in marks if m in hb}
        tally = ev.mirror_tally(T)
        fwd = dict(frames=len(T), header_digest=tally['header_digest'], canary_hits=sorted(hits), error=None)
        P = dict(P or E['P'], sends=sends)
        return status(evaluate(E, cond, P=P, T=T, tally=tally, fwd=fwd))

    @staticmethod
    def frames(E):
        return [dict(send=copy.deepcopy(s), wire=t['wire']) for s, t in zip(E['P']['sends'], E['T'])]

    @staticmethod
    def renumber(frames):
        seq = {}
        for f in frames:
            h = f['send']['header']
            h['seq'] = seq.get(h['source'], 0)
            seq[h['source']] = h['seq'] + 1
        return frames

    def red(self, st, *groups):
        self.assertTrue(any(st[g] == 'fail' for g in groups), st)

    def test_honest_rebuild_passes(self):
        self.assertEqual(set(self.rebuild(self.A3, self.frames(self.A3), 'perturbed').values()), {'pass'})

    def test_noise_ref_lies_after_the_first_record(self):
        F, seen = self.frames(self.A3), set()
        for f in F:
            s = f['send']['src']
            if s in ('depth', 'lidar'):
                if s in seen:
                    f['send']['header']['noise_ref'] = s + ':gauss-5mm'
                seen.add(s)
        self.red(self.rebuild(self.A3, F, 'perturbed'), 'schema')

    def test_truth_in_allowed_fields(self):
        F = self.frames(self.A3)
        for f in F:
            f['send']['header']['shape'] = f['send']['header']['shape'] + [-3100, -792, -13]
            f['send']['header']['format'] += '/5a3661423bcd0e37'
        self.red(self.rebuild(self.A3, F, 'perturbed'), 'schema')

    def test_delivery_claimed_before_arrival(self):
        F = self.frames(self.A3)
        for f in F:
            h = f['send']['header']
            if h['status'] == 'ok':
                h['delivered_ns'] = h['capture_ns']
        self.red(self.rebuild(self.A3, F, 'perturbed'), 'latency')

    def test_covert_timing_on_half_the_imu(self):
        F = self.frames(self.A3)
        for f in F:
            if f['send']['src'] == 'imu' and f['send']['n'] % 2:
                f['send']['header']['delivered_ns'] += 5_000_000
        self.red(self.rebuild(self.A3, F, 'perturbed'), 'latency')

    def test_duplicates_sent_as_fresh(self):
        out = []
        for f in self.frames(self.A3):
            out.append(f)
            if f['send']['src'] == 'lidar' and f['send']['n'] % 10 == 0 and not f['send']['frozen'] \
                    and not f['send']['corrupt']:
                out.append(copy.deepcopy(f))
        self.red(self.rebuild(self.A3, self.renumber(out), 'perturbed'), 'validity')

    def test_fabricated_frames(self):
        out = []
        for k, f in enumerate(self.frames(self.A3)):
            out.append(f)
            if f['send']['src'] == 'imu' and f['send']['n'] % 500 == 7 and not f['send']['frozen']:
                h = copy.deepcopy(f['send']['header'])
                fake = hashlib.sha256(b'phantom%d' % k).hexdigest()
                h.update(capture_ns=h['capture_ns'] + 2_000_000, payload_sha256=fake)
                out.append(dict(send=dict(k='send', src='ghost', n=-1, frozen=False, corrupt=False,
                                          header=h), wire=fake))
        self.red(self.rebuild(self.A3, self.renumber(out), 'perturbed'), 'source')

    def test_silent_loss_at_either_end(self):
        for where in ('head', 'tail'):
            F = self.frames(self.A3)
            idx = {s: [k for k, f in enumerate(F) if f['send']['src'] == s] for s in SOURCES}
            cut = {k for s in SOURCES for k in (idx[s][:25] if where == 'head' else idx[s][-25:])}
            keep = self.renumber([f for k, f in enumerate(F) if k not in cut])
            self.red(self.rebuild(self.A3, keep, 'perturbed'), 'loss')

    def test_seq_offset_and_invented_rgb_noise(self):
        F = self.frames(self.A4)
        for f in F:
            f['send']['header']['seq'] += 1000
            if f['send']['src'] == 'rgb':
                f['send']['header']['noise_ref'] = 'rgb:gauss-50mm'
        self.red(self.rebuild(self.A4, F, 'nominal'), 'schema')

    def test_honest_natural_loss_in_the_first_interval_passes(self):
        # devA3's lidar starts 1182, 1200, 1300, 1400 ms: the first interval is
        # a short startup frame. Gazebo never delivering #1 and #2 leaves 218 ms
        # between #0 and #3, which the honest adapter reports as gap 1 in the
        # first interval of the span, where the reviewer found the old red.
        E = self.A3
        P = copy.deepcopy(E['P'])
        raw = P['raw']['lidar']
        s0, s3 = raw[0]['stamp'], raw[3]['stamp']
        del raw[1], raw[2]
        honest = max(0, round((s3 - s0) / contract.SOURCES['lidar']['period_ns']) - 1)
        self.assertEqual(honest, 1)
        F = []
        for f in self.frames(E):
            if f['send']['src'] == 'lidar' and f['send']['n'] in (1, 2):
                continue
            if f['send']['src'] == 'lidar' and f['send']['n'] == 3 and not f['send']['frozen']:
                f['send']['header']['gap'] = honest
            F.append(f)
        st = self.rebuild(E, self.renumber(F), 'perturbed', P=P)
        self.assertEqual(set(st.values()), {'pass'}, st)


class CampaignTests(unittest.TestCase):
    def test_protocol_and_denominators(self):
        p = campaign.protocol()
        campaign.validate(p)
        bad = campaign.protocol()
        bad['limits']['noise_band'] = [0.5, 2.0]
        with self.assertRaises(ValueError):
            campaign.validate(bad)
        tmp, pk = legacy.generate_suite_unique()
        try:
            a = campaign.jobs(pk[:4], 'validation', p)
            b = campaign.jobs(pk[:12], 'bench', p)
        finally:
            tmp.cleanup()
        self.assertEqual((len(a), len(b)), (20, 31))
        self.assertEqual(sum(j[2] == 'control' for j in a), 4)
        self.assertEqual(sorted(j[5] for j in b if j[5]), sorted(contract.MUTANTS))
        # Labels are unique within a stage; stages live in separate directories.
        self.assertEqual((len({j[0] for j in a}), len({j[0] for j in b})), (20, 31))
        # Every mutant has an honest faulted twin in the same bench world.
        faulted = {j[0] for j in b if j[2] == 'faulted'}
        for j in b:
            if j[5]:
                self.assertIn(f'faulted-{pk[j[1]].package_id}-r1', faulted)

    def test_mutation_tests_survive_an_error_record(self):
        r = dict(records=[dict(label='x', error='boom')], passed=False, groups={'a': dict(status='fail')},
                 agent_in_gazebo=False, stage='validation')
        lock = dict(protocol=campaign.protocol(), sha256='0')
        res = campaign.mutations(campaign.seal(r), lock)
        self.assertEqual(res['status'], 'fail')          # no crash; nothing counted as detected

    def test_frozen_namespaces_do_not_see_sensor1s(self):
        for inv in (c.inventory(), v6c.inventory()):
            self.assertFalse(any('sensor1s' in f for f in inv['files']))
        lock = json.loads((c.ECHOAI/'lab/flight1s-v6/lock.json').read_text())
        self.assertEqual(v6c.inventory(), lock['inventory'])


if __name__ == '__main__':
    unittest.main()
