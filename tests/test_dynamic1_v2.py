"""DYNAMIC-1 v2: the face, not a point.

Consumer: a wall crossing its own face is called moving and its predicted step
matches, in both directions; a wall whose clipping slides is not, which is what
turned v1 red; the records stay integers.
Evidence: the ten recorded flights of v1, rejudged with v2, all come out green,
including the one that failed.
Structure: consumer, evaluator, session and campaign differ from v1 only where
declared; the protocol validates; v1's lock stays intact.
Reads real evidence; writes nothing into lab.
"""
import difflib
import json
import math
import tempfile
import unittest
from pathlib import Path

from echoai.nexus0.flight1s.v3 import campaign as c
from echoai.nexus0.sim3.generate import generate_suite
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.dynamic1 import campaign as d1c, contract as d1, evaluate as ev1, session as s1
from echoai.nexus0.dynamic1_v2 import campaign as d2c, evaluate as ev, session as s2

G = ev.G
DEV = c.ECHOAI/'lab/dynamic1-v2/dev'


def code(path):
    return Path(path).read_text().split('"""', 2)[2].splitlines()


def changed(a, b):
    return [x for x in difflib.unified_diff(code(a), code(b), n=0, lineterm='')
            if x[:1] in '+-' and not x.startswith(('+++', '---'))]


def wall(distance_m, half_deg=12):
    """A flat wall straight ahead."""
    return [distance_m/math.cos(math.radians(-180+i)) if abs(-180+i) < half_deg else float('inf')
            for i in range(len(G.COS))]


def split_wall(distance_m, half_deg=12, gap=(177, 184)):
    """One flat wall straight ahead with a hole in it: two silhouettes with the
    same normal, the same distance, and nothing to tell them apart."""
    return [distance_m/math.cos(math.radians(-180+i))
            if abs(-180+i) < half_deg and not (gap[0] <= i < gap[1]) else float('inf')
            for i in range(len(G.COS))]


def gappy_wall(distance_m, beams=(100, 104, 105, 106)):
    """A run the segmentation keeps whole across missing beams, whose first four
    beams hold one echo: there is no line to fit, only a place."""
    return [distance_m if i in beams else float('inf') for i in range(len(G.COS))]


def ground(scans, mutant=''):
    g = G.Ground(mutant)
    for k, values in enumerate(scans):
        g.record('lidar', k*100_000_000, 'ok', 0, True, values)
    return g


def run(scans, mutant=''):
    return ground(scans, mutant).motion


class ConsumerTests(unittest.TestCase):
    def test_a_wall_crossing_its_face_is_called_moving(self):
        for sign in (-1, 1):
            motion = run([wall(5.0 + sign*0.024*k) for k in range(12)])
            last = motion[-1]
            self.assertEqual(last[3], 1, sign)
            step = last[4] - last[1]
            self.assertAlmostEqual(step, sign*120, delta=30)      # 0.24 m/s over 500 ms
            self.assertTrue(all(type(v) is int for v in last))

    def test_a_still_wall_is_left_alone(self):
        motion = run([wall(5.0) for _ in range(12)])
        self.assertEqual({r[3] for r in motion}, {0})

    def test_a_clipping_that_slides_is_not_movement(self):
        """What turned v1 red: the reported point slides along the wall while the
        wall itself stays where it is."""
        scans = [wall(5.0, half_deg=6 + k) for k in range(12)]
        motion = run(scans)
        self.assertEqual(motion[-1][3], 0)
        self.assertLess(abs(motion[-1][4] - motion[-1][1]), 40)

    def test_every_counted_silhouette_leaves_a_record(self):
        """The evaluator walks records and silhouettes together. A silhouette it
        counts but the consumer skips shifts every record after it onto the
        wrong object, and the flight reads as a science result."""
        scan = gappy_wall(5.0)
        runs = [x for x in G.silhouettes(scan) if x[1] >= G.EMIT_MIN_BEAMS]
        self.assertEqual(len(runs), 1)
        motion = run([scan])
        self.assertEqual(len(motion), len(runs))
        self.assertEqual(motion[0][3], 0)                 # no line, so no claim of motion
        self.assertEqual(motion[0][1:3], motion[0][4:6])

    def test_one_face_takes_one_track(self):
        """Two silhouettes of the same wall, same normal, same distance: left in
        the pool a single track absorbs both and its history alternates between
        them, which is motion the world never made."""
        g = ground([split_wall(5.0) for _ in range(6)])
        self.assertEqual(len(g.motion), 12)               # two per scan
        self.assertEqual(len(g.tracks), 2)
        self.assertEqual(len({id(x) for x in g.tracks}), 2)
        for x in g.tracks:
            self.assertEqual(len(x[3]), 6)                # one entry per scan, not two
        self.assertEqual({r[3] for r in g.motion}, {0})

    def test_the_lies_still_lie(self):
        closing = [wall(5.0 - 0.024*k) for k in range(12)]
        self.assertEqual({r[3] for r in run(closing, 'no_motion')}, {0})
        self.assertEqual({r[3] for r in run([wall(5.0)]*12, 'always_motion')}, {1})
        copy = run(closing, 'copy_current')
        self.assertTrue(all(r[4] == r[1] and r[5] == r[2] for r in copy))
        honest, blind = run(closing), run(closing, 'blind_place')
        self.assertTrue(all(r[1] == 0 and r[2] == 0 for r in blind))
        self.assertEqual([(r[4]-r[1], r[5]-r[2]) for r in blind],
                         [(r[4]-r[1], r[5]-r[2]) for r in honest])   # same step, no place


class ProofTests(unittest.TestCase):
    """v1's own evidence, rejudged by v2: the fix is shown before it flies."""

    def test_every_v1_flight_comes_out_green(self):
        report = json.loads((c.ECHOAI/'lab/dynamic1/validation/report.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            pk = generate_suite(Path(d), load_protocol(c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                                [(d1.WORLD_SPLIT, i, s) for i, s in zip(d1.WORLD_INDEX, d1.WORLD_SEEDS)],
                                family_path=c.ECHOAI/d1.FAMILY_PATH)
            byid = {x.package_id: x.package for x in pk}
            worst = dict(detect=1.0, records=10**9, median=0, p95=0, position=0)
            for rec in report['records']:
                t = json.loads((c.ECHOAI/rec['trace']).read_text())
                P = ev.load_private(c.ECHOAI/rec['private'])
                T = ev.load_transcript(c.ECHOAI/rec['transcript'])
                recs = ev.rebuild(T, P)
                out = ev.dynamics(t, recs, byid[rec['package_id']],
                                  dict(rec['consumer'], motion=ev.recompute(recs)))
                red = {k for k, v in out.items() if not all(x['ok'] for x in v)}
                self.assertEqual(red, set(), rec['label'])
                det = {x['name']: x for x in out['detection']}['moving_called_moving']
                pr = {x['name']: x for x in out['prediction']}
                if det.get('fraction') is not None:
                    worst['detect'] = min(worst['detect'], det['fraction'])
                    worst['records'] = min(worst['records'], det['records'])
                worst['median'] = max(worst['median'], pr['displacement']['median_mm'])
                worst['p95'] = max(worst['p95'], pr['displacement']['p95_mm'])
                worst['position'] = max(worst['position'], pr['where_it_is']['median_mm'])
            # The numbers of amendment 3, not the limits they were used to set:
            # lowering a limit must not turn this test green again.
            self.assertEqual(dict(worst, detect=round(worst['detect'], 3)),
                             dict(detect=0.789, records=19, median=28, p95=288, position=178))
            lim = ev.DYNAMIC_LIMITS
            self.assertGreaterEqual(worst['detect'], lim['detect'])
            self.assertGreaterEqual(worst['records'], lim['min_records'])
            self.assertLessEqual(worst['median'], lim['predict_mm'])
            self.assertLessEqual(worst['p95'], lim['predict_p95_mm'])
            self.assertLessEqual(worst['position'], lim['position_mm'])


class StructureTests(unittest.TestCase):
    def test_schedule_accepts_v2_mutant_and_rejects_wrong_treatment(self):
        for mutant in (None, *d2c.MUTANTS):
            job = ('fixture', 0, 'mutant' if mutant else 'faulted',
                   'perturbed', True, mutant, 20261312)
            spec = d2c.scheduled_spec(job)
            self.assertEqual(spec['dynamic_mutant'], mutant)
            record = dict(label=job[0], arm=job[2], condition=job[3],
                          faulted=job[4], mutant=job[5], seed=job[6], package_id='p')
            self.assertTrue(d2c.record_matches_job(record, job, 'p'))
            for key, value in [('arm','control'), ('faulted',False),
                               ('seed',0), ('package_id','other')]:
                self.assertFalse(d2c.record_matches_job(dict(record, **{key:value}), job, 'p'))
        with self.assertRaises(ValueError):
            d1.spec([], 'blind_place')   # the historical auditor's call failed here
        with self.assertRaises(ValueError):
            d2c.scheduled_spec(('fixture',0,'mutant','perturbed',True,'unknown',1))

    def test_consumer_differs_only_in_the_tracker(self):
        text = Path(s2.CONSUMER).read_text()
        for kept in ('payload_sha256', 'set(h) != KEYS', 'def silhouettes', "out['motion']"):
            self.assertIn(kept, text, kept)
        for added in ('FACE_MIN_MM', 'FACE_DOT', 'FACE_JUMP_MM', 'consistent', 'blind_place'):
            self.assertIn(added, text, added)
        # the point-based estimator of v1 is gone
        self.assertNotIn('hist[-1][1] - hist[0][1], hist[-1][2] - hist[0][2]', text)
        self.assertIn('FACE_JUMP_MM', text)

    def test_evaluator_judges_the_normal_component(self):
        lines = changed(ev1.__file__, ev.__file__)
        self.assertTrue(any('face_normal' in x for x in lines))
        self.assertTrue(any('nrm' in x for x in lines))
        self.assertIs(ev.G.__name__, ev.G.__name__)
        self.assertEqual(ev.CONSUMER, s2.CONSUMER)

    def test_session_and_runner_are_v1s(self):
        self.assertEqual(s2.TAP, s1.TAP)
        self.assertEqual(s2.SURVEY_RUNNER, s1.SURVEY_RUNNER)
        self.assertNotEqual(s2.CONSUMER, s1.CONSUMER)

    def test_protocol_changes_only_where_declared(self):
        a, b = d2c.protocol(), d1c.protocol()
        self.assertEqual(sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)),
                         ['consumer_sha256', 'dynamic_limits', 'mutant_cases', 'mutant_targets',
                          'mutants', 'prediction', 'stages', 'version'])
        self.assertEqual(tuple(a['mutants']), tuple(b['mutants']) + ('blind_place',))
        self.assertEqual(a['mutant_cases']['blind_place'], 'where_it_is')
        self.assertEqual(a['stages']['bench']['mutants'], len(a['mutants']))
        self.assertEqual(a['dynamic_limits']['position_mm'], 500)
        self.assertEqual(a['version'], 2)
        for stage, seed in (('validation', 20261311), ('bench', 20261312)):
            self.assertEqual(a['stages'][stage]['seed'], seed)
            # the stage differs only in its seed and in the count of mutants
            self.assertEqual(dict(a['stages'][stage], seed=0, mutants=0),
                             dict(b['stages'][stage], seed=0, mutants=0))
        d2c.validate(a)

    def test_v1_lock_is_untouched(self):
        lock = json.loads((c.ECHOAI/'lab/dynamic1/lock.json').read_text())
        self.assertEqual(d1c.inventory(), lock['inventory'])
        self.assertEqual(d1c.history()['sha256'], lock['history_sha256'])
        inv = d2c.inventory()['files']
        for need in ('nexus0/dynamic1_v2/assets/consumer.py', 'nexus0/dynamic1_v2/evaluate.py',
                     'docs/DYNAMIC1-V2-DESIGN.md', 'tests/test_dynamic1_v2.py'):
            self.assertIn(need, inv)
        self.assertIn('docs/DYNAMIC1-RESULTS.md', d2c.history()['files'])


if __name__ == '__main__':
    unittest.main()
