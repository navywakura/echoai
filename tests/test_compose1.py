import copy
import unittest
from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1.controller import Composer
from echoai.nexus0.compose1.space import Space,DIRECTIONS
from echoai.nexus0.compose1.training import train


class ComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.snapshot,cls.training=train()

    def test_effects_are_learned_and_snapshot_restores(self):
        empty=Effects()
        self.assertTrue(all(empty.predict(a) is None for a in range(7)))
        model=Effects.restore(self.snapshot)
        self.assertEqual([model.predict(a) for a in range(7)],list(DIRECTIONS))
        self.assertEqual(model.snapshot(),self.snapshot)

    def test_rollouts_do_not_write_model(self):
        space=Space(20261801);agent=Composer(self.snapshot,space.goal)
        before=agent.model.fingerprint();out=agent.decide(space.scan())
        self.assertEqual(before,agent.model.fingerprint())
        self.assertEqual(out['imagined_writes'],0)
        self.assertLessEqual(out['candidates'],32);self.assertLessEqual(out['depth'],4)

    def test_rollout_mutant_changes_fingerprint(self):
        space=Space(20261801);agent=Composer(self.snapshot,space.goal,'write_rollout')
        self.assertGreater(agent.decide(space.scan())['imagined_writes'],0)

    def test_private_world_field_rejected(self):
        space=Space(20261801);frame=space.scan();frame['world_id']='hidden'
        with self.assertRaises(ValueError):Composer(self.snapshot,space.goal).decide(frame)

    def test_mission_coordinate_is_not_a_fact(self):
        space=Space(20261801);agent=Composer(self.snapshot,space.start)
        frame=space.scan();frame['station_observed']=False
        self.assertNotEqual(agent.decide(frame)['status'],'reached')
        liar=Composer(self.snapshot,space.start,'goal_is_fact')
        self.assertEqual(liar.decide(frame)['status'],'reached')

    def test_low_energy_abandons_at_home(self):
        space=Space(20261801,'low_energy')
        self.assertEqual(Composer(self.snapshot,space.goal).decide(space.scan())['status'],'abandoned_at_home')

    def test_no_prior_map_is_inherited(self):
        a=Space(20261801);agent=Composer(self.snapshot,a.goal);agent.decide(a.scan())
        b=Composer(self.snapshot,Space(20261802).goal)
        self.assertEqual(b.cells,{});self.assertEqual(b.visits,{})
        self.assertEqual(b.model.fingerprint(),Effects.restore(self.snapshot).fingerprint())

    def test_both_search_budgets(self):
        for mode,limit in (('echo8',8),('echo32',32)):
            space=Space(20261801);out=Composer(self.snapshot,space.goal,mode).decide(space.scan())
            self.assertLessEqual(out['candidates'],limit)

    def test_auditor_rejects_forged_results(self):
        from echoai.nexus0.compose1.bench import mission,tamper_tests,compare_record
        r=mission(self.snapshot,20261801,'static','echo32',isolated=False)
        self.assertEqual(compare_record(r,copy.deepcopy(r)),[])
        checks=tamper_tests(r,r)
        self.assertEqual(len(checks),6)
        self.assertTrue(all(c['caught'] for c in checks))


if __name__=='__main__':unittest.main()
