import copy
import unittest
from unittest.mock import patch
from echoai.nexus0.transfer3.budget_school import train
from echoai.nexus0.transfer3.school_v3 import VARIANTS
from echoai.nexus0.transfer3.rehearsal_v4 import significance, screen, audit
from echoai.nexus0.transfer3.rehearsal_v2 import suite


class BudgetTests(unittest.TestCase):
    def test_exact_budget_including_mid_episode_cut(self):
        for variant in VARIANTS:
            s=train([20264401,20264402],variant,7)
            self.assertEqual(s['moves'],7)
            self.assertEqual(s['sim_u'],28)
            self.assertEqual(sum(e['moves'] for e in s['episodes']),7)
            self.assertEqual(sum(sum(v) for v in s['counts'].values()),7)
            for e in s['episodes']:
                self.assertEqual(e['ingestions'],e['moves']+1)
                self.assertEqual(e['visits'],e['ingestions'])
                self.assertEqual(e['collisions'],0)
                self.assertEqual(e['reserve_violations'],0)
            self.assertEqual(s['episodes'][-1]['status'],'training_budget_cut')

    def test_budget_one_does_not_execute_extra_steps(self):
        s=train([20264401],'corrected',1)
        self.assertEqual(len(s['episodes']),1)
        self.assertEqual(len(s['episodes'][0]['rows']),1)

    def test_bad_budget(self):
        for budget in (True,0,-1,4097,1.0):
            with self.assertRaises(ValueError):train([1],'corrected',budget)
        with self.assertRaises(ValueError):train([],'corrected',2)

    def test_sign_exact(self):
        self.assertEqual(significance(0,0),dict(numerator=1,denominator=1))
        self.assertEqual(significance(6,0),dict(numerator=1,denominator=64))
        self.assertEqual(significance(4,1),dict(numerator=6,denominator=32))

    def rows(self, n=6):
        return [dict(seed=i,reached=True,moves=10,collisions=0,reserve_violations=0,
            false_facts=0,model_unchanged=True,rows=[dict(decision=dict(imagined_writes=0))]) for i in range(n)]

    def test_screen_requires_advantage_and_no_new_failure(self):
        b=self.rows();a=copy.deepcopy(b)
        for r in a:r['moves']=8
        self.assertTrue(screen(a,b,dict(moves=128))['development_screen_pass'])
        a[0]['reached']=False
        self.assertFalse(screen(a,b,dict(moves=128))['development_screen_pass'])

    def test_screen_rejects_safety_or_learning_mutations(self):
        b=self.rows();a=copy.deepcopy(b)
        for r in a:r['moves']=8
        for key,value in [('collisions',1),('reserve_violations',1),('false_facts',1),('model_unchanged',False)]:
            bad=copy.deepcopy(a);bad[0][key]=value
            self.assertFalse(screen(bad,b,dict(moves=128))['development_screen_pass'])
        a[0]['rows'][0]['decision']['imagined_writes']=1
        self.assertFalse(screen(a,b,dict(moves=128))['development_screen_pass'])

    def test_no_victory_for_cheap_joint_failure(self):
        b=self.rows();a=copy.deepcopy(b)
        for r in a:r.update(moves=1,reached=False)
        for r in b:r['reached']=False
        s=screen(a,b,dict(moves=128))
        self.assertEqual(s['wins'],0)
        self.assertEqual(s['joint_success_saved_moves'],0)
        self.assertFalse(s['development_screen_pass'])

    def test_new_rooms_distinct_and_exclude_previous(self):
        a,_=suite(20264401,4)
        old,_=suite(20264501,16,[r['shape'] for r in a])
        new,_=suite(20264601,64,[r['shape'] for r in a+old])
        self.assertEqual(len({r['shape'] for r in a+old+new}),84)

    def test_audit_rejects_tampering(self):
        expected=dict(isolated=False,trace=[1],transfer3_green=False)
        with patch('echoai.nexus0.transfer3.rehearsal_v4.run',return_value=expected):
            self.assertTrue(audit(expected)['replay_valid'])
            with self.assertRaises(ValueError):audit(dict(expected,trace=[]))


if __name__=='__main__':unittest.main()
