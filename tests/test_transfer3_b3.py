import unittest
from echoai.nexus0.transfer3 import bench_b2,bench_b3,calib_b2,costs_a2
from echoai.nexus0.transfer3.school_b2 import Gym
from echoai.nexus0.transfer3.planner_b3 import Planner
from echoai.nexus0.transfer3.planner_b2 import Planner as Previous
from echoai.nexus0.transfer3.gain_b1 import GainRoom,declared_body
from echoai.nexus0.fusion1.core import packet


class BrakingTests(unittest.TestCase):
    def fixture(self):
        w=Gym((3,1,1,1),0);w.solids.add((2,0,0));w.camera_solids=set(w.solids)
        a=Planner(calib_b2.restore(calib_b2.prior(3)).snapshot(),w.goal,costs_a2.nominal(),reserve=6,safe=True)
        a.update(w.scan())
        return w,a

    def test_observed_braking_predicts_actual_transition(self):
        w,a=self.fixture()
        predicted=a.advance(w.pos,0)
        self.assertEqual(predicted,(1,0,0))
        w.step(0)
        self.assertEqual(predicted,w.pos)

    def test_unknown_is_not_a_brake(self):
        w,a=self.fixture();del a.beliefs[(2,0,0)]
        self.assertIsNone(a.advance(w.pos,0))

    def test_weak_obstacle_is_not_a_brake(self):
        w,a=self.fixture();a.beliefs[(2,0,0)]=packet(1,40)
        self.assertIsNone(a.advance(w.pos,0))

    def test_blocked_first_cell_refuses_action(self):
        w,a=self.fixture();a.beliefs[(1,0,0)]=packet(1,80)
        self.assertIsNone(a.advance(w.pos,0))

    def test_output_and_wsp_reference_match_clipped_prediction(self):
        w,a=self.fixture();d=a.output(0,[0],'moving',1)
        self.assertEqual(d['prediction'],[1,0,0])
        self.assertEqual(bytes.fromhex(d['wsp'])[14],a.refs[(1,0,0)])

    def test_unit_gain_does_not_change_nominal_controller(self):
        w=GainRoom(20268001,declared_body(),(1,1,1,1),aligned=True)
        snapshot=calib_b2.restore(calib_b2.prior(1)).snapshot()
        a=Planner(snapshot,w.goal,costs_a2.nominal(),reserve=6,safe=True)
        b=Previous(snapshot,w.goal,costs_a2.nominal(),reserve=6,safe=True)
        for _ in range(65):
            f=w.scan();da,db=a.decide(f),b.decide(f)
            self.assertEqual(da,db)
            if da['status'] not in ('moving','returning'):break
            w.step(bytes.fromhex(da['wsp'])[13])

    def test_adapters_are_restored_on_failure(self):
        old=bench_b2.Planner,bench_b2.Caged,bench_b2.manifest
        with self.assertRaises(RuntimeError):
            with bench_b3.adapters():
                self.assertIs(bench_b2.Planner,Planner)
                raise RuntimeError('test')
        self.assertEqual((bench_b2.Planner,bench_b2.Caged,bench_b2.manifest),old)

    def test_bad_pilot_cannot_open_confirmation(self):
        for pilot in (None,dict(variant='b3-observed-braking',isolated=False,verdict=dict(passes=True)),
                      dict(variant='b3-observed-braking',isolated=True,verdict=dict(passes=False))):
            with self.assertRaises(ValueError):bench_b3.run('confirm',pilot=pilot)

    def test_manifest_contains_new_consumer_and_controller(self):
        m=bench_b3.manifest()
        self.assertIn('nexus0/transfer3/consumer_b3.py',m)
        self.assertIn('nexus0/transfer3/planner_b3.py',m)
        self.assertIn('docs/TRANSFER3-PLAN-B3-DESIGN.md',m)
        bench_b2.verify_manifest(m)


if __name__=='__main__':unittest.main()
