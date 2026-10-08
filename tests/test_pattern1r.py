"""PATTERN-1R: the survey, the signature, and what identity claims.

Structure: the runner, channel, session and consumer differ from their
sources only where declared; the protocol validates; the world family really
does separate the two objects of every world; earlier locks stay intact.
Signature: Gray code, integers only, and silhouettes measured from a scan.
Evaluator: forged signature streams turn the right case red, and a learner
that studies during the exam is caught. Dev: the kept flights rejudge as
recorded. Reads real evidence; writes nothing into lab.
"""
import difflib
import json
import math
import tempfile
import unittest
from pathlib import Path

from echoai.nexus0.flight1s.v3 import campaign as c
from echoai.nexus0.sensor1s import contract as s1
from echoai.nexus0.sensor1s_v3 import evaluate as sev
from echoai.nexus0.sim3.generate import generate_suite
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.ground1 import evaluate as gev, session as gs1
from echoai.nexus0.ground1_v2 import campaign as g2, session as gs2
from echoai.nexus0.pattern1r import campaign as p1, contract as p1r, evaluate as ev, session as ps
from echoai.nexus0.pattern1 import InvariantPatternMemory

DEV = c.ECHOAI/'lab/pattern1r/dev'
G = ev.G


def code(path):
    return Path(path).read_text().split('"""', 2)[2].splitlines()


def changed(a, b):
    return [x for x in difflib.unified_diff(code(a), code(b), n=0, lineterm='')
            if x[:1] in '+-' and not x.startswith(('+++', '---'))]


def red(groups):
    return {k for k, v in groups.items() if not (v and all(x['ok'] for x in v))}


def scan_of(hits):
    """A full scan of misses with `hits` = {beam: range_m} filled in."""
    return [hits.get(i, float('inf')) for i in range(len(G.COS))]


class SignatureTests(unittest.TestCase):
    def test_tracking_accumulates_the_widest_view(self):
        """A wall seen edge-on then face-on keeps its largest size."""
        g = G.Ground('')
        narrow = {i: 5.0 for i in range(175, 181)}
        wide = {i: 5.0 for i in range(160, 196)}
        g.record('lidar', 1, 'ok', 0, True, scan_of(narrow))
        first = g.sightings[-1][1]
        g.record('lidar', 2, 'ok', 0, True, scan_of(wide))
        second = g.sightings[-1][1]
        self.assertGreater(second, first)
        g.record('lidar', 3, 'ok', 0, True, scan_of(narrow))
        self.assertEqual(g.sightings[-1][1], second)        # the size it has shown

    def test_signature_distance_is_the_size_difference(self):
        """Thermometer code: Hamming distance == buckets apart (amendment 1)."""
        for a_mm, b_mm, buckets in ((1000, 1300, 1), (1000, 1900, 3), (2700, 4200, 5)):
            d = bin(G.signature(a_mm) ^ G.signature(b_mm)).count('1')
            self.assertEqual(d, buckets, (a_mm, b_mm))
        self.assertEqual(G.signature(1000), G.signature(1100))      # inside one bucket
        self.assertTrue(0 <= G.signature(9999) <= 0xFFFF)

    def test_silhouette_measures_a_wall(self):
        # A flat wall 3 m wide, 4 m ahead: beams within +-21 deg of the nose.
        hits = {}
        for i in range(len(G.COS)):
            a = math.radians(-180 + i)
            if abs(math.degrees(a)) < 21:
                hits[i] = 4.0 / math.cos(a)
        runs = G.silhouettes(scan_of(hits))
        self.assertEqual(len(runs), 1)
        first, count, width = runs[0]
        self.assertEqual(count, 41)
        self.assertAlmostEqual(width/1000.0, 2*4.0*math.tan(math.radians(20.5)), delta=0.15)

    def test_two_objects_are_two_silhouettes(self):
        hits = {i: 5.0 for i in range(150, 161)}
        hits.update({i: 7.0 for i in range(200, 211)})
        self.assertEqual(len(G.silhouettes(scan_of(hits))), 2)


class StructureTests(unittest.TestCase):
    def test_consumer_keeps_ground1s_checks_and_adds_its_own(self):
        text = Path(ps.CONSUMER).read_text()
        for kept in ("payload_sha256", "set(h) != KEYS", "seq_breaks", "non_monotonic", "wsp"):
            self.assertIn(kept, text, kept)          # GROUND-1 still runs inside the cage
        for added in ("def silhouettes", "def signature", "sightings", "TRACK_BEAMS"):
            self.assertIn(added, text, added)
        self.assertNotIn("import numpy", text)

    def test_runner_and_channel_are_declared_copies(self):
        runner = changed(c.ECHOAI/'nexus0/flight1s/assets/flightrunner.py', ps.SURVEY_RUNNER)
        self.assertTrue(any('DO_REPOSITION' in x or 'reposition' in x for x in runner))
        self.assertTrue(any('survey' in x for x in runner))
        channel = changed(c.ECHOAI/'nexus0/ground1_v2/assets/sensor_runner.py', ps.TAP)
        for line in channel:
            self.assertTrue('flightrunner' in line or 'Driver' in line, line)

    def test_session_is_ground1_v2s_with_this_slices_paths(self):
        lines = changed(gs2.__file__, ps.__file__)
        self.assertLessEqual(len(lines), 12, lines)
        text = Path(ps.__file__).read_text()
        self.assertIn("assets/flightrunner_survey.py", text)
        self.assertIn("assets/consumer.py", text)

    def test_protocol_and_lock_scope(self):
        p = p1.protocol()
        p1.validate(p)
        self.assertEqual(p['slice'], 'PATTERN-1R')
        self.assertEqual(p['family']['id'], p1r.FAMILY)
        self.assertEqual(p['family']['sha256'],
                         __import__('hashlib').sha256((c.ECHOAI/p1r.FAMILY_PATH).read_bytes()).hexdigest())
        self.assertEqual(sorted(p['school_poses'] + p['exam_poses']), list(range(p1r.ARC['poses'])))
        self.assertFalse(set(p['school_poses']) & set(p['exam_poses']))
        inv = p1.inventory()['files']
        for need in ('nexus0/pattern1r/assets/flightrunner_survey.py', 'nexus0/pattern1r/assets/consumer.py',
                     'nexus0/pattern1r/evaluate.py', 'docs/PATTERN1R-DESIGN.md', p1r.FAMILY_PATH,
                     'nexus0/pattern1.py', 'tests/test_pattern1r.py', 'core/cam.py'):
            self.assertIn(need, inv)

    def test_earlier_locks_are_untouched(self):
        lock = json.loads((c.ECHOAI/'lab/ground1-v2/lock.json').read_text())
        self.assertEqual(g2.inventory(), lock['inventory'])
        self.assertEqual(g2.history()['sha256'], lock['history_sha256'])
        self.assertFalse(any('pattern1r' in f for f in g2.inventory()['files']))

    def test_the_worlds_separate_their_two_objects(self):
        with tempfile.TemporaryDirectory() as d:
            pk = generate_suite(Path(d), load_protocol(c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                                [(p1r.WORLD_SPLIT, i, s) for i, s in zip(p1r.WORLD_INDEX, p1r.WORLD_SEEDS)],
                                family_path=c.ECHOAI/p1r.FAMILY_PATH)
            self.assertEqual(len(pk), 12)
            for r in pk:
                boxes = sev.boxes(r.package)
                bars = [(hi[1]-lo[1], hi[2]-lo[2]) for i, (lo, hi) in enumerate(boxes)
                        if r.package.roles[sorted(r.package.roles)[i]] == 'barrier']
                self.assertEqual(len(bars), 2, r.package_id)
                # Amendment 2: both walls are tall enough to be seen at any survey
                # altitude, and what separates them is their length.
                self.assertGreaterEqual(abs(bars[0][0]-bars[1][0]), 1.2, r.package_id)
                self.assertGreaterEqual(min(bars[0][1], bars[1][1]), 2.2, r.package_id)


class ArcTests(unittest.TestCase):
    def test_the_arc_rings_the_objects_and_starts_by_the_spawn(self):
        import math, tempfile
        with tempfile.TemporaryDirectory() as d:
            pk = generate_suite(Path(d), load_protocol(c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                                [(p1r.WORLD_SPLIT, i, s) for i, s in zip(p1r.WORLD_INDEX, p1r.WORLD_SEEDS)],
                                family_path=c.ECHOAI/p1r.FAMILY_PATH)
            for r in pk:
                vp = p1r.arc_viewpoints(r.package)
                self.assertEqual(len(vp), p1r.ARC['poses'])
                boxes = [b for i, b in enumerate(sev.boxes(r.package))
                         if r.package.roles[sorted(r.package.roles)[i]] == 'barrier']
                cx = sum((lo[0]+hi[0])/2 for lo, hi in boxes)/len(boxes)*1000
                cy = sum((lo[1]+hi[1])/2 for lo, hi in boxes)/len(boxes)*1000
                for x, y in vp:
                    self.assertAlmostEqual(math.hypot(x-cx, y-cy), p1r.ARC['radius_mm'], delta=2)
                    self.assertLess(max(abs(x), abs(y)), 5900)        # inside the room
                sx, sy = r.package.spawn_mm[0], r.package.spawn_mm[1]
                first = math.hypot(vp[0][0]-sx, vp[0][1]-sy)
                self.assertLessEqual(first, min(math.hypot(x-sx, y-sy) for x, y in vp) + 1)

    def test_school_and_exam_are_disjoint_arcs(self):
        self.assertEqual(set(p1r.SCHOOL_POSES) & set(p1r.EXAM_POSES), set())
        self.assertGreaterEqual(len(p1r.EXAM_POSES), 6)


class LearnerTests(unittest.TestCase):
    """The learner is PATTERN-1's memory, and the exam does not write."""

    def test_exam_writes_nothing(self):
        mem = InvariantPatternMemory()
        for k in range(8):
            mem.observe(G.signature(2000), 0)
            mem.observe(G.signature(4000), 0)
        before = mem.snapshot_hash()
        for k in range(5):
            mem.predict(G.signature(2000))
        self.assertEqual(before, mem.snapshot_hash())
        mem.observe(G.signature(2000), 0)
        self.assertNotEqual(before, mem.snapshot_hash())

    def test_predict_takes_only_a_signature(self):
        import inspect
        self.assertEqual(list(inspect.signature(InvariantPatternMemory.predict).parameters)[1:], ['signature'])


class DevTests(unittest.TestCase):
    """PATTERN-1R closed red in development: the evidence of that is kept."""

    def test_the_dev_evidence_is_there(self):
        flights = sorted(d for d in DEV.iterdir() if d.is_dir() and (d/'sensors.json').exists())
        self.assertGreaterEqual(len(flights), 6)
        for d in flights:
            s = json.loads((d/'sensors.json').read_text())
            self.assertIn('sightings', s['consumer'])
        self.assertTrue((c.ECHOAI/'docs/PATTERN1R-RESULTS.md').exists())

    def test_no_lock_was_taken(self):
        self.assertFalse((c.ECHOAI/'lab/pattern1r/lock.json').exists())


if __name__ == '__main__':
    unittest.main()
