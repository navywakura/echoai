"""GROUND-1: the translation, its evaluator and its chain, before any lock.

Structure: the consumer's packer and atoms are echoai.core.wsp's; the packet set
is closed; SENSOR-1S v3's evaluator and channel are imported, not copied;
the protocol changes only where declared; earlier locks stay intact; the
lock covers the core the evaluator runs.
Attacks: forged reports, packets and cable counts turn the right case red;
a crashed or absent report is never counted as a caught mutant.
Cable: a consumer that writes to stdout or a second stderr line is seen,
through the real cage.
Retrospective: SENSOR-1S v3's honest flights, packets recomputed from the
raw samples, pass every grounding group; each mutant, fed the same records,
turns its own case red. Dev: the kept batch-3 dev flights, rejudged from
their files. Reads real evidence; writes nothing into lab.
"""
import itertools
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import echoai.core.wsp
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.sensor1s import campaign as v1, contract
from echoai.nexus0.sensor1s_v2 import campaign as v2, session as s2
from echoai.nexus0.sensor1s_v3 import campaign as v3, evaluate as ev3
from echoai.nexus0.sim3 import runtime as sim3runtime, sandbox
from echoai.nexus0.ground1 import campaign as g1, evaluate as ev, session as gs

G = ev.G
V3LAB = c.ECHOAI/'lab/sensor1s-v3'
DEV = c.ECHOAI/'lab/ground1/dev'
GROUNDING = ('sensors_only', 'single_cable', 'pinned', 'cam', 'distance', 'push', 'certainty')
BATCH = 'b3-'


def honest_cable(T, packets):
    """The cable of a consumer that wrote exactly the predicted line for these
    packets. SENSOR-1S v3 recorded no cable counts: its flights are judged as if it had."""
    return dict(stderr_lines=1, back_bytes=0, returncode=0, stderr_sha256=ev.canonical_sha256(T, packets))


def load(stage, label):
    r = json.loads((V3LAB/stage/'sensors'/(label+'.json')).read_text())
    trace = json.loads((c.ECHOAI/r['trace']).read_text())
    return r, trace, ev.load_private(c.ECHOAI/r['private']), ev.load_transcript(c.ECHOAI/r['transcript'])


def translate(records, mutant=''):
    g = G.Ground(mutant)
    for r in records:
        ev.feed(g, r)
    g.close()
    return g.packets


def red(groups):
    return {k for k, v in groups.items() if not (v and all(x['ok'] for x in v))}


def ok(cases):
    return bool(cases) and all(x['ok'] for x in cases)


def key_for(rel, dst, c_):
    return next(k for k, v in ev.CLOSED.items() if v == (rel, dst, c_))


class StructureTests(unittest.TestCase):
    def test_atoms_and_packer_are_navi10_wsps(self):
        for name in ('YO', 'AHORA', 'CAMBIAR', 'OBSERVAR', 'DESCONOCIDO', 'ALLI', 'FUERA'):
            self.assertEqual(getattr(G, name), echoai.core.wsp.atom_id(name), name)
        self.assertEqual(G.E_NAMES, echoai.core.wsp.E_NAMES)
        for args in itertools.product((2, 255), (13, 31), (5, 7), (8,), (dict(C=100, U=40, A=80), dict(V=-300, B=7)),
                                      (0, 3), (7,), (6,), (0, 9), (0, 200), (0, 256)):
            src, rel, dst, t, e, flags, dom, gen, style, slot, seq = args
            kw = dict(flags=flags, domain=dom, generator=gen, style=style, slot=slot, seq=seq)
            self.assertEqual(G.pack(src, rel, dst, t, e, **kw), echoai.core.wsp.pack(src, rel, dst, t, e, **kw))

    def test_packet_set_is_closed_and_fixed(self):
        self.assertEqual(len(ev.CLOSED), 10)
        self.assertEqual(len(set(ev.CLOSED.values())), 10)
        for k in ev.CLOSED:
            f = struct.unpack('<BBBBbbbbbbBBBBBB', bytes.fromhex(k))
            self.assertEqual((f[0], f[3], f[10:]), (G.YO, G.AHORA, (0, 7, 0x06, 0, 0, 0)))
            self.assertEqual((f[4], f[6], f[9]), (0, 0, 0))           # V, D, B carry nothing

    def test_true_sensor_pose_uses_base_link(self):
        self.assertEqual(ev.BASE_LINK_IN_MODEL, (0.0, 0.0, 0.24))

    def test_sensor_side_is_imported(self):
        self.assertIs(ev.sev, ev3)
        self.assertIs(ev.LIMITS, ev3.LIMITS)
        self.assertIs(ev.summarize, ev3.summarize)
        self.assertIs(g1.evaluate, ev)
        self.assertIs(g1.session, gs)
        def code(module):             # stripped lines after the module docstring
            return {x.strip() for x in Path(module.__file__).read_text().split('"""', 2)[2].splitlines()}
        gone = code(s2) - code(gs)
        self.assertTrue(gone)
        for line in gone:
            self.assertTrue(any(t in line for t in ('TAP =', 'CONSUMER', 'communicate(timeout=60)',
                                                    'consumer_returncode=')), line)

    def test_protocol_changes_only_where_declared(self):
        a, b = g1.protocol(), v3.protocol()
        self.assertEqual(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
                         ['grounding', 'mutant_cases', 'mutant_targets', 'mutants', 'slice', 'stages', 'version'])
        for stage, seed in (('validation', 20261101), ('bench', 20261102)):
            self.assertEqual(a['stages'][stage]['seed'], seed)
        self.assertEqual(dict(a['stages']['validation'], seed=0), dict(b['stages']['validation'], seed=0))
        self.assertEqual(a['stages']['bench'], dict(b['stages']['bench'], seed=20261102, mutants=6))
        self.assertEqual(set(a['mutants']), {'constant_percept', 'imu_blind', 'certainty_lie', 'seq_counter',
                                             'lookahead', 'extra_channel'})
        self.assertEqual(set(a['mutant_targets']), set(a['mutants']))
        self.assertEqual(set(a['mutant_targets'].values()) - set(GROUNDING), set())
        self.assertEqual(a['grounding']['limits'], ev.GROUND_LIMITS)
        g1.validate(a)

    def test_earlier_locks_are_untouched(self):
        for mod, lab in ((v1, 'lab/sensor1s/lock.json'), (v2, 'lab/sensor1s-v2/lock.json'),
                         (v3, 'lab/sensor1s-v3/lock.json')):
            lock = json.loads((c.ECHOAI/lab).read_text())
            self.assertEqual(mod.inventory(), lock['inventory'], lab)
            self.assertEqual(mod.history()['sha256'], lock['history_sha256'], lab)
            self.assertFalse(any('ground1' in f for f in mod.inventory()['files']), lab)
        hist = g1.history()['files']
        for need in ('lab/echo3_sensor1s_v3_report.json', 'lab/sensor1s-v3/lock.json',
                     'lab/sensor1s-v3-run.log', 'docs/SENSOR1S-V2-RESULTS.md', 'docs/SENSOR1S-V3-RESULTS.md'):
            self.assertIn(need, hist)

    def test_lock_covers_the_core_the_evaluator_runs(self):
        inv = g1.inventory()['files']
        for need in ('docs/GROUND1-DESIGN.md', 'nexus0/loop.py', 'nexus0/ground1/assets/consumer.py',
                     'nexus0/sensor1s_v2/assets/sensor_runner.py', 'nexus0/sim3/sandbox.py',
                     'core/cam.py', 'core/dag.py', 'core/qn.py', 'core/spoke.py',
                     'core/wsp.py'):
            self.assertIn(need, inv)


class CamTests(unittest.TestCase):
    def test_agent_slot_path_separates_by_exact_packet(self):
        keys = list(ev.CLOSED)
        cases = ev.cam_group(keys + keys[::-1])
        self.assertTrue(cases[0]['ok'], cases)
        self.assertEqual((cases[0]['percepts'], cases[0]['slots'], cases[0]['destroyed']), (10, 10, 0))
        self.assertTrue(cases[0]['structural'])
        # Declared limit (amendment 1): vertices collide inside the closed set.
        self.assertLessEqual(cases[0]['vertex_min_bits_closed'], ev.HAM_LIMIT)

    def test_it_is_structural(self):
        """Amendment 3: any stream under 4097 distinct packets passes."""
        rnd = [bytes([i % 256, i // 256] + [0]*14).hex() for i in range(300)]
        self.assertTrue(ev.cam_group(rnd + rnd)[0]['ok'])
        self.assertTrue(ev.cam_group([])[0]['ok'])

    def test_malformed_packets_are_red(self):
        for bad in (['zz'], [[1]], ['00'*15], None):
            self.assertFalse(ev.cam_group(bad)[0]['ok'], bad)


class AttackTests(unittest.TestCase):
    """One real flight (faulted, pushed, near wall), then forged reports."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, pk = legacy.generate_suite_unique()
        cls.byid = {g.package_id: g for g in pk}
        cls.r, cls.trace, cls.P, cls.T = load('validation', 'faulted-73e0dcb3241663a5-r1')
        cls.pkg = cls.byid[cls.r['package_id']].package
        cls.records = ev.rebuild(cls.T, cls.P)
        cls.lidar = [x for x in cls.records if x['source'] == 'lidar']
        cls.honest = translate(cls.records)
        cls.td = ev.touchdown(cls.trace)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def judge(self, report, trace=None, cable='honest', condition='perturbed'):
        cable = honest_cable(self.T, report.get('wsp') or []) if cable == 'honest' else cable
        return ev.grounding(trace or self.trace, self.P, self.T, report, self.pkg, condition=condition, cable=cable)

    def report(self, packets, **extra):
        return dict(self.r['consumer'], wsp=packets, **extra)

    def with_change_at(self, t_ns):
        i = next(i for i, x in enumerate(self.lidar) if x['capture_ns'] >= t_ns)
        rel, dst, c_ = ev.CLOSED[self.honest[i]]
        self.assertNotEqual(rel, G.DESCONOCIDO)
        forged = list(self.honest)
        forged[i] = key_for(G.CAMBIAR, dst, c_)
        return forged

    def test_honest_is_green(self):
        g = self.judge(self.report(self.honest))
        self.assertEqual(red(g), set())
        self.assertGreater(g['distance'][0]['unusable'], 0)       # faults reach the judged set

    def test_forged_reports(self):
        h = self.honest
        swap = list(h)
        swap[len(h)//2] = next(k for k in ev.CLOSED if k != h[len(h)//2])
        self.assertIn('sensors_only', red(self.judge(self.report(swap))))
        self.assertIn('single_cable', red(self.judge(self.report(h, debug=1))))
        self.assertTrue({'single_cable', 'sensors_only', 'pinned'} <= red(self.judge(dict(self.r['consumer']))))
        outside = list(h)
        outside[3] = G.pack(G.YO, G.OBSERVAR, G.FUERA, G.AHORA, dict(C=100, A=10), domain=7, generator=6, seq=3).hex()
        self.assertIn('pinned', red(self.judge(self.report(outside))))
        self.assertTrue({'sensors_only', 'distance', 'push', 'certainty'} <= red(self.judge(self.report(h[:-1]))))
        self.assertIn('cam', red(self.judge(self.report(h[:-1] + [[0]]))))

    def test_absent_or_misaligned_report_is_not_a_catch(self):
        for report in (dict(self.r['consumer']), self.report(self.honest[:-1])):
            g = self.judge(report)
            for mutant in g1.MUTANTS:
                if g1.TARGET[mutant] in ('distance', 'push', 'certainty', 'sensors_only', 'pinned'):
                    self.assertFalse(g1.mutant_caught(mutant, g[g1.TARGET[mutant]]), mutant)
        crashed = dict(execution=[dict(name='flight', ok=True)], schema=[dict(name='x', ok=False)])
        self.assertFalse(g1.sound(crashed))
        # A flight that lost its force event, or had nothing judged, catches nothing.
        no_wrench = dict(self.trace, events=[e for e in self.trace['events'] if e.get('ev') != 'wrench_applied'])
        g = self.judge(self.report(translate(self.records, 'imu_blind')), no_wrench)
        self.assertFalse(ok(g['push']))
        self.assertFalse(g1.mutant_caught('imu_blind', g['push']))
        self.assertTrue(g1.mutant_caught('imu_blind', self.judge(self.report(translate(self.records, 'imu_blind')))['push']))
        self.assertFalse(g1.mutant_caught('constant_percept', [dict(name='front_band', ok=False, judged=0)]))

    def test_cable_counts(self):
        h = self.report(self.honest)
        base = honest_cable(self.T, self.honest)
        for cable in (dict(base, stderr_lines=2), dict(base, back_bytes=4), dict(base, back_bytes=-1),
                      dict(base, returncode=3), dict(base, stderr_sha256='0'*64), None, {}):
            g = self.judge(h, cable=cable)
            self.assertEqual(red(g), {'single_cable'}, cable)

    def test_causality_of_the_translation_itself(self):
        self.assertTrue(ev.causal_prefix(self.records))
        honest_ground = G.Ground

        class Lookahead(honest_ground):
            def __init__(self, mutant=''):
                honest_ground.__init__(self, 'lookahead')
        with mock.patch.object(G, 'Ground', Lookahead):
            self.assertFalse(ev.causal_prefix(self.records))
            g = self.judge(self.report(translate(self.records, 'lookahead')))
            self.assertIn('sensors_only', red(g))

    def test_coverage_cannot_be_dodged(self):
        h = self.honest
        unknown = [key_for(G.DESCONOCIDO, G.DESCONOCIDO, ev.CLOSED[p][2]) for p in h]
        self.assertIn('distance', red(self.judge(self.report(unknown))))
        seq = [G.pack(G.YO, *ev.CLOSED[p][:2], G.AHORA, dict(C=100), domain=7, generator=6, seq=1).hex() for p in h]
        self.assertIn('distance', red(self.judge(self.report(seq))))
        i = next(i for i, x in enumerate(self.lidar) if not (x['valid'] and x['status'] == 'ok'))
        near = list(h)
        near[i] = key_for(G.OBSERVAR, G.ALLI, ev.CLOSED[h[i]][2])
        d0, d1 = self.judge(self.report(h))['distance'][0], self.judge(self.report(near))['distance'][0]
        self.assertEqual((d1['hits'], d1['judged']), (d0['hits'] - 1, d0['judged']))

    def test_push_needs_the_force_event(self):
        no_wrench = dict(self.trace, events=[e for e in self.trace['events'] if e.get('ev') != 'wrench_applied'])
        self.assertFalse(ok(self.judge(self.report(self.honest), no_wrench)['push']))
        nominal = self.judge(self.report(translate(self.records, 'imu_blind')), condition='nominal')
        self.assertFalse(ok(nominal['push']))            # a wrench event in a flight declared without force

    def test_touchdown_window(self):
        self.assertIsNotNone(self.td)
        for dt, want in ((-50_000_000, True), (1_500_000_000, True), (-300_000_000, False), (2_500_000_000, False)):
            g = self.judge(self.report(self.with_change_at(self.td + dt)))
            self.assertEqual(ok(g['push']), want, dt)
        hover = self.judge(self.report(self.with_change_at(self.trace['stage_marks']['plan'][2][1] + 1_000_000_000)))
        self.assertFalse(ok(hover['push']))
        # Without a truth touchdown, the honest landing change is a stray.
        blind = dict(self.trace, stage_marks=dict(self.trace['stage_marks'], rest_z_um=-10**9))
        self.assertIsNone(ev.touchdown(blind))
        self.assertFalse(ok(self.judge(self.report(self.honest), blind)['push']))


class CableTests(unittest.TestCase):
    """Through the real cage: every byte the consumer sends back is counted."""

    def run_consumer(self, path):
        cage = sim3runtime.preflight(write=False)
        consumer = sandbox.spawn(cage, probe_path=path)
        return gs.collect(consumer, timeout=30)

    def variant(self, old, new):
        src = gs.CONSUMER.read_text()
        self.assertEqual(src.count(old), 1)
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name)/'consumer.py'
        p.write_text(src.replace(old, new))
        return p

    def test_honest_consumer_uses_one_cable(self):
        report, cable = self.run_consumer(gs.CONSUMER)
        self.assertEqual((cable['stderr_lines'], cable['back_bytes'], cable['returncode']), (1, 0, 0), report[-300:])
        tally = json.loads(report)
        self.assertEqual(tally['wsp'], [])
        self.assertEqual(cable['stderr_sha256'], ev.canonical_sha256([], []))

    def test_hidden_separator_and_exit_code_are_seen(self):
        line = "    sys.stderr.write(json.dumps(out, sort_keys=True) + '\\n')\n"
        hidden = self.variant(line, "    sys.stderr.write('SECOND:1\\x1c' + json.dumps(out, sort_keys=True) + '\\n')\n")
        report, cable = self.run_consumer(hidden)
        tally = json.loads(report.decode().strip().splitlines()[-1])   # how the session parses it
        self.assertEqual(cable['stderr_lines'], 1)
        self.assertEqual(tally['wsp'], [])
        self.assertNotEqual(cable['stderr_sha256'], ev.canonical_sha256([], []))
        _, cable = self.run_consumer(self.variant("    sys.stderr.flush()\n    return 0\n",
                                                  "    sys.stderr.flush()\n    return 3\n"))
        self.assertEqual(cable['returncode'], 3)

    def test_type_channel_is_seen(self):
        typed = self.variant("    ground.close()\n    out['wsp'] = ground.packets\n",
                             "    ground.close()\n    out['frames'] = float(out['frames'])\n    out['wsp'] = ground.packets\n")
        report, cable = self.run_consumer(typed)
        self.assertEqual(json.loads(report), dict(ev.sev.mirror_tally([]), wsp=[]))   # == is blind to 0.0
        self.assertNotEqual(cable['stderr_sha256'], ev.canonical_sha256([], []))

    def test_second_cable_is_seen(self):
        src = gs.CONSUMER.read_text()
        tail = "    sys.stderr.flush()\n    return 0\n"
        self.assertEqual(src.count(tail), 1)
        leak = src.replace(tail, "    sys.stderr.flush()\n    sys.stdout.buffer.write(b'leak')\n    sys.stdout.flush()\n"
                                 "    sys.stderr.write('second\\n')\n    return 0\n")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'consumer.py'
            p.write_text(leak)
            _, cable = self.run_consumer(p)
        self.assertEqual((cable['stderr_lines'], cable['back_bytes']), (2, 4))


class RetrospectiveTests(unittest.TestCase):
    """SENSOR-1S v3's honest flights: the translation recomputed from raw
    samples, judged by GROUND-1's groups. Post hoc and declared so."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, pk = legacy.generate_suite_unique()
        cls.byid = {g.package_id: g for g in pk}
        cls.flights = {}
        for stage in ('validation', 'bench'):
            for f in sorted((V3LAB/stage/'sensors').glob('*.json')):
                r = json.loads(f.read_text())
                if r['arm'] != 'mutant' and 'error' not in r:
                    cls.flights[(stage, r['label'])] = r

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def judge(self, stage, label, mutant='', extra=None):
        r, trace, P, T = load(stage, label)
        packets = translate(ev.rebuild(T, P), mutant)
        report = dict(r['consumer'], wsp=packets, **(extra or {}))
        return ev.grounding(trace, P, T, report, self.byid[r['package_id']].package,
                            condition=r['condition'], cable=honest_cable(T, packets))

    def test_honest_flights_pass_every_grounding_group(self):
        self.assertEqual(len(self.flights), 44)
        hits = judged = 0
        for (stage, label) in self.flights:
            g = self.judge(stage, label)
            self.assertEqual(red(g), set(), label)
            self.assertTrue(g['push'][0]['touchdown_found'], label)
            d = g['distance'][0]
            self.assertGreaterEqual(d['judged'], 0.5 * d['turns'], label)
            hits += d['hits']
            judged += d['judged']
        self.assertGreaterEqual(hits/judged, ev.GROUND_LIMITS['accuracy_stage'])

    def test_each_mutant_turns_its_case_red(self):
        cases = dict(constant_percept='faulted-73e0dcb3241663a5-r1', lookahead='faulted-eddc87870377f61b-r1',
                     imu_blind='faulted-02083ef67737f6d9-r1', certainty_lie='faulted-ef7f22a49738b970-r1',
                     seq_counter='clean-02083ef67737f6d9-r1')
        self.assertEqual(set(cases) | {'extra_channel'}, set(g1.MUTANTS))
        for mutant, label in cases.items():
            g = self.judge('validation', label, mutant)
            self.assertTrue(g1.mutant_caught(mutant, g[g1.TARGET[mutant]]), mutant)
        g = self.judge('validation', 'clean-02083ef67737f6d9-r1', '', extra=dict(debug=dict(turns=1)))
        self.assertEqual(red(g), {'single_cable'})
        self.assertTrue(g1.mutant_caught('extra_channel', g['single_cable']))

    def test_lookahead_differs_only_by_the_future(self):
        r, trace, P, T = load('validation', 'faulted-eddc87870377f61b-r1')
        records = ev.rebuild(T, P)
        a, b = translate(records), translate(records, 'lookahead')
        self.assertEqual(len(a), len(b))
        diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
        self.assertTrue(diff)
        for i in diff:
            self.assertEqual(ev.CLOSED[a[i]][0], ev.CLOSED[b[i]][0])
            # dst is the next scan's; an unusable next scan has no near beam.
            nxt = ev.CLOSED[a[i+1]]
            self.assertEqual(ev.CLOSED[b[i]][1], G.FUERA if nxt[0] == G.DESCONOCIDO else nxt[1])


class DevTests(unittest.TestCase):
    """The kept batch-3 dev flights (final code): rejudged from their files, as recorded."""

    def test_dev_flights(self):
        dirs = sorted(p for p in DEV.iterdir() if p.is_dir() and p.name.startswith(BATCH))
        self.assertGreaterEqual(len(dirs), 10)
        tmp, pk = legacy.generate_suite_unique()
        byid = {g.package_id: g for g in pk}
        try:
            seen = set()
            for d in dirs:
                s = json.loads((d/'sensors.json').read_text())
                trace = json.loads((d/'episode.json').read_text())
                groups = ev.episode(trace, ev.load_private(c.ECHOAI/s['private']),
                                    ev.load_transcript(c.ECHOAI/s['transcript']), s['consumer'], s['forwarder'],
                                    byid[s['package_id']].package, s['spec'], condition=s['condition'],
                                    bounds=contract.LATENCY_P99_BOUND_NS, cable=s.get('cable'))
                summary = json.loads(json.dumps(ev.summarize(groups)))
                self.assertEqual(summary, json.loads((d/'evaluation.json').read_text()), d.name)
                mutant = s['spec'].get('ground_mutant')
                if mutant:
                    seen.add(mutant)
                    self.assertTrue(g1.sound(groups), d.name)
                    self.assertTrue(g1.mutant_caught(mutant, groups[g1.TARGET[mutant]]), d.name)
                else:
                    self.assertEqual(red(groups), set(), d.name)
            self.assertEqual(seen, set(g1.MUTANTS))
        finally:
            tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
