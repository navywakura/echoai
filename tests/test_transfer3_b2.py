import ast
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from echoai.nexus0.transfer3 import calib_b2, school_b2, bench_b2
from echoai.nexus0.transfer3.transport_b2 import MODULES
from echoai.nexus0.transfer3.gain_b1 import GainRoom, declared_body
from echoai.nexus0.transfer3.planner_b2 import Planner
from echoai.nexus0.transfer3 import costs_a2
from echoai.nexus0.fusion1.core import packet


class Learning(unittest.TestCase):
    def test_identifies_all_conditions_from_frames(self):
        for g in (1,2,3,4):
            s = school_b2.train((g,1,1,1))
            self.assertEqual(s['payload']['gains'],[g,1,1,1])
            self.assertEqual(s['energy'],32)
            self.assertEqual(s['moves'],8)
            self.assertEqual(s['collisions'],0)
            self.assertEqual(school_b2.replay(s),s['payload'])

    def test_strict_schema_and_types(self):
        p = calib_b2.prior(2)
        bad = [dict(p,seed=1),dict(p,schema='old'),dict(p,gains=[True,1,1,1]),
               dict(p,gains=[2,2,1,1]),dict(p,samples=[1,0,0,0]),dict(p,gains=[5,1,1,1])]
        for v in bad:
            with self.assertRaises(ValueError):calib_b2.validate(v)

    def test_restore_is_abstract_and_has_zero_q(self):
        m = calib_b2.restore(calib_b2.prior(3))
        self.assertEqual(m.predict(0),(3,0,0))
        self.assertEqual(m.cam.used,5)
        self.assertTrue(all(not s.has_fact for s in m.cam.slot if s.occupied))
        self.assertTrue(all(not any(r) for r in m.snapshot()['q'].values()))

    def test_capacity_failure_is_closed(self):
        from echoai.core.cam import Cam
        with patch.object(Cam,'put',return_value=-1):
            with self.assertRaises(ValueError):calib_b2.restore(calib_b2.prior(2))

    def test_no_private_world_import_in_learner(self):
        raw = Path(calib_b2.__file__).read_text()
        self.assertNotIn('gain_b1',raw)
        self.assertNotIn('space_a2',raw)

    def test_censored_or_missing_evidence_is_rejected(self):
        s = school_b2.train((2,1,1,1));r=s['traces'][0]
        for value in (1,-1):
            frame = copy.deepcopy(r['before'])
            for c in frame['cells']:
                if c['position']==[4,0,0]:
                    c['depth']=c['lidar']=packet(value,40).hex()
            with self.assertRaises(ValueError):
                calib_b2.Learner().observe(frame,bytes.fromhex(r['wsp']),r['after'])

    def test_trace_or_payload_corruption_is_detected(self):
        s=school_b2.train((2,1,1,1))
        s['payload']['gains'][0]=3
        with self.assertRaises(ValueError):school_b2.replay(s)

    def test_conflicting_sample_does_not_update_t(self):
        s=school_b2.train((2,1,1,1));a,b=s['traces'][:2]
        l=calib_b2.Learner();l.observe(a['before'],bytes.fromhex(a['wsp']),a['after'])
        before=l.model.fingerprint()
        after=copy.deepcopy(b['after']);after['odometry'][0]+=1
        with self.assertRaises(ValueError):l.observe(b['before'],bytes.fromhex(b['wsp']),after)
        self.assertEqual(l.model.fingerprint(),before)

    def test_repeated_capture_and_incomplete_school(self):
        s=school_b2.train((2,1,1,1));r=s['traces'][0]
        l=calib_b2.Learner()
        with self.assertRaises(ValueError):l.observe(r['before'],bytes.fromhex(r['wsp']),r['before'])
        with self.assertRaises(ValueError):l.export()


class SafetyAndManifest(unittest.TestCase):
    def test_real_return_is_directional(self):
        w=school_b2.Gym((3,1,1,1),0)
        h=bench_b2.true_home_costs(w)
        self.assertEqual(h[(3,0,0)],12)
        self.assertEqual(h[(-3,0,0)],4)

    def test_safe_reserve_never_discounts_other_directions(self):
        a=Planner(calib_b2.restore(calib_b2.prior(3)).snapshot(),(4,0,0),costs_a2.nominal(),reserve=6,safe=True)
        self.assertEqual(a.per_cell_reserve(),6)
        a.safe=False
        self.assertEqual(a.per_cell_reserve(),2)

    def test_manifest_is_explicit_and_source_sensitive(self):
        m=bench_b2.manifest()
        self.assertIn('nexus0/transfer3/consumer_b2.py',m)
        self.assertIn('nexus0/transfer3/calib_b2.py',m)
        self.assertNotIn('docs/NOW.md',m)
        bench_b2.verify_manifest(m)
        m['nexus0/transfer3/calib_b2.py']='0'*64
        with self.assertRaises(ValueError):bench_b2.verify_manifest(m)

    def test_dependency_closure_does_not_include_unrelated_files(self):
        with TemporaryDirectory(dir=bench_b2.ROOT/'tests') as directory:
            # apply_patch-only restriction concerns agent edits, not test fixtures.
            p=Path(directory)/'empty.py';p.write_text('value = 1\n')
            q=Path(directory)/'unrelated.py';q.write_text('value = 2\n')
            self.assertEqual(bench_b2.dependency_paths([p]),[p.resolve()])

    def test_cage_does_not_mount_evaluator(self):
        for s in ('gain_b1.py','space_a2.py','school_b2.py','bench_b2.py'):
            self.assertFalse(any(m.endswith(s) for m in MODULES))
        for rel in MODULES:
            tree=ast.parse((bench_b2.ROOT/'nexus0'/rel).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):
                    self.assertFalse(any(s in (node.module or '') for s in ('gain_b1','space_a2','school_b2','bench_b2')))

    def test_confirmation_requires_passed_pilot(self):
        with self.assertRaises(ValueError):bench_b2.run('confirm',False,pilot=None)

    def test_falsified_report_rejected(self):
        report=dict(inventory={},stage='pilot',safe=False,isolated=False,pilot=None,excluded=[])
        with patch.object(bench_b2,'run',return_value={}):
            with self.assertRaises(ValueError):bench_b2.audit(report)

    def test_missing_pairs_rejected(self):
        row=dict(seed=1,reached=True,energy=8,collisions=0,reserve_violations=0,
                 false_facts=0,imagined_writes=0,unobserved_segments=0,model_unchanged=True)
        arms={a:[dict(row)] for a in ('nominal','prior2','prior3','learned')}
        arms['nominal'][0]['seed']=2
        with self.assertRaises(ValueError):bench_b2.evaluate({'1':arms},{'1':dict(energy=32)},confirm=False)

    def test_cheaper_joint_failures_cannot_pass(self):
        row=dict(seed=1,reached=False,energy=8,collisions=0,reserve_violations=0,
                 false_facts=0,imagined_writes=0,unobserved_segments=0,model_unchanged=True)
        arms={a:[dict(row)] for a in ('nominal','prior2','prior3','learned')}
        arms['learned'][0]['energy']=0
        result=bench_b2.evaluate({'1':arms},{'1':dict(energy=32)},confirm=True)
        self.assertFalse(result['passes'])


if __name__=='__main__':unittest.main()
