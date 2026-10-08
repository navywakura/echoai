import copy
import json
import unittest

from echoai.seed import dsl
from echoai.seed.refinement import solver_input, execute
from seed.arc_memory import ArcMemory
from seed.arc_delayed_policy import ArcPolicy
from seed.relational_dsl import (Work, Exhausted, RelationalLibrary, Scene,
                                 objects, relate, bind, map_objects, render)
from seed.relational_solver import solve
from seed.relational_tasks import task, correct, ambiguous
from seed.verified_program_guide import ProgramGuide, motif, execute as bank_execute, solve as bank_solve
from seed.program_guide_campaign import reference, item
import random


class Relational(unittest.TestCase):
    def test_roles_rebind_after_color_permutation_and_translation(self):
        lib = RelationalLibrary()
        step = ('rel', 'largest', 'all', 'paint')
        for seed in range(47000, 47004):
            t = task('paint', seed)
            for p in t['train'] + t['test']:
                self.assertEqual(lib.apply(dsl.G(p['input']), step), dsl.G(p['output']))

    def test_stamp_matches_independent_judge(self):
        lib = RelationalLibrary()
        for p in task('stamp', 47000)['train']:
            self.assertEqual(lib.apply(dsl.G(p['input']), ('rel', 'largest', 'all', 'stamp')), dsl.G(p['output']))

    def test_object_order_does_not_change_binding(self):
        w = Work();s = objects(task('paint', 47000)['train'][0]['input'], w)
        reverse = Scene(s.grid, s.background, tuple(reversed(s.objects)))
        def apply(scene):
            b = bind(scene, relate(scene, 'all', w), 'largest', w)
            return render(scene, map_objects(b, 'paint', w), 'original', w)
        self.assertEqual(apply(s), apply(reverse))

    def test_ambiguous_role_rejected(self):
        w = Work();s = objects([[0,0,0,0,0], [0,1,0,2,0], [0,0,0,0,0]], w)
        with self.assertRaises(ValueError):bind(s, relate(s,'all',w),'largest',w)

    def test_budget_never_exceeded_even_on_failed_operation(self):
        w = Work(10)
        with self.assertRaises(Exhausted):objects([[0]*5 for _ in range(5)], w)
        self.assertLessEqual(w.used, 10)
        r = solve(task('paint',47000),budget=1000)
        self.assertLessEqual(r['metrics']['work'],1000)

    def test_private_output_not_read(self):
        class Secret:
            def __iter__(self):raise AssertionError('read private label')
            def __deepcopy__(self,memo):raise AssertionError('copied private label')
        a=task('paint',47000);b=copy.deepcopy(a)
        for p in b['test']:p['output']=Secret()
        self.assertEqual(solve(a),solve(b))

    def test_receipt_replay_and_tampering(self):
        lib=RelationalLibrary();m=ArcMemory()
        m.remember(task('paint',47000),[('rel','largest','all','paint')],lib,'unit-test')
        restored=ArcMemory.restore(json.loads(json.dumps(m.state())),lib)
        self.assertEqual(restored.candidates(solver_input(task('paint',47001)))[0]['program'],
                         [['rel','largest','all','paint']])
        bad=m.state();next(iter(bad['payloads'].values()))['program']=[['rot90']]
        with self.assertRaises(ValueError):ArcMemory.restore(bad,lib)

    def test_consistency_exposes_ambiguity(self):
        a=solve(ambiguous(47001),consistency=True)
        b=solve(ambiguous(47001),consistency=False)
        self.assertEqual(a['status'],'AMBIGUOUS')
        self.assertIsNone(a['predictions'])
        self.assertIsNotNone(b['predictions'])
        self.assertEqual(a['metrics'],b['metrics'])


class DelayedPolicy(unittest.TestCase):
    def test_credit_only_matures_at_horizon_and_handles_late_cost(self):
        p=ArcPolicy();p.begin('a','single',0,10,0);p.charge('a',5,'x')
        p.mature(63);self.assertEqual(p.q['single'][0],[0,0])
        p.mature(64);self.assertEqual(p.q['single'][0],[-15,1])
        p.charge('a',7,'late');self.assertEqual(p.q['single'][0],[-22,1])
        with self.assertRaises(ValueError):p.charge('a',7,'late')

    def test_resume_including_rng_pending_costs_and_decisions(self):
        p=ArcPolicy();p.begin('a','single',1,50,3)
        q=ArcPolicy.restore(json.loads(json.dumps(p.state())))
        for obj in (p,q):
            obj.charge('a',3,'later');obj.mature(67)
        self.assertEqual(p.canonical_state(),q.canonical_state())
        self.assertEqual([p.choose('single') for _ in range(50)],[q.choose('single') for _ in range(50)])

    def test_read_only_evaluation_does_not_learn(self):
        p=ArcPolicy();before=p.canonical_state()
        solve(task('paint',47000),policy=p)
        self.assertEqual(before,p.canonical_state())

    def test_actor_accounts_real_work_and_has_no_test_reward(self):
        p=ArcPolicy();r=solve(task('paint',47000),policy=p,learn=True,episode=0)
        self.assertEqual(p.tickets['development:0']['cost'],r['metrics']['work'])
        self.assertEqual(p.matured,0)
        self.assertEqual(p.tickets['development:0']['verified'],bool(r['programs']))


class ProgramBank(unittest.TestCase):
    def test_all_32_programs_match_independent_pixel_judge(self):
        rng=random.Random(47000)
        g=[[rng.randrange(3) for _ in range(8)] for _ in range(6)]
        for i in range(32):
            self.assertEqual(bank_execute(dsl.G(g),i,Work()),dsl.G(reference(g,i)))

    def test_encoder_color_and_position_invariance(self):
        shape=[[int((x+y)%3==0) for x in range(7)] for y in range(7)]
        case=item(shape,11,random.Random(47000))
        self.assertEqual(motif(case['train'][0]['input'],Work()),motif(case['test'][0]['input'],Work()))

    def test_guide_verified_learning_roundtrip_and_no_label_access(self):
        shape=[[int((x*3+y*7)%5<2) for x in range(7)] for y in range(7)]
        case=item(shape,11,random.Random(47000));g=ProgramGuide()
        with self.assertRaises(ValueError):g.observe(case,0,Work())
        self.assertEqual(g.examples,0)
        g.observe(case,11,Work());restored=ProgramGuide.restore(json.loads(json.dumps(g.state())))
        a=bank_solve(case,g);b=bank_solve(solver_input(case),restored)
        self.assertEqual(a,b);self.assertEqual(a['program'],11)
        self.assertTrue(correct(a,case))

    def test_memory_removal_never_changes_remaining_evidence(self):
        m=ArcMemory();lib=RelationalLibrary()
        key=m.remember(task('paint',47000),[('rel','largest','all','paint')],lib,'unit')
        s=m.state();removed=m.ablate([key])
        self.assertEqual(removed.state()['payloads'],s['payloads'])
        self.assertFalse(removed.candidates(solver_input(task('paint',47001))))


if __name__ == '__main__':unittest.main()
