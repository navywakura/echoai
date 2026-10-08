import copy
import json
import unittest

from echoai.seed import dsl
from echoai.seed.refinement import RefinementLibrary, solver_input, execute
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from seed.arc_memory import ArcMemory
from seed.integrated_grid import solve


def task(program=(("rot90",),)):
    lib=RefinementLibrary()
    grids=[[[1,0,2],[0,3,0]], [[4,0],[5,6],[0,7]], [[0,3,1],[4,0,0]]]
    pairs=[{"input":g,"output":[list(r) for r in execute(dsl.G(g),program,lib)]} for g in grids]
    return {"train":pairs[:2],"test":pairs[2:]}


class ArcIntegration(unittest.TestCase):
    def setUp(self):
        self.lib=RefinementLibrary()

    def test_test_output_is_never_read(self):
        class Forbidden:
            def __iter__(self): raise AssertionError("private output inspected")
            def __deepcopy__(self,memo): raise AssertionError("private output copied")
        a=task(); b=copy.deepcopy(a); b['test'][0]['output']=Forbidden()
        self.assertEqual(solve(a,self.lib,max_trials=100),solve(b,self.lib,max_trials=100))

    def test_only_verified_demonstrations_enter_memory(self):
        m=ArcMemory()
        with self.assertRaises(ValueError):m.remember(task(),[("flipud",)],self.lib,"development")
        self.assertEqual(m.actor.diary,[])
        m.remember(task(),[("rot90",)],self.lib,"development")
        m.verify(self.lib)
        self.assertNotIn('test',json.dumps(m.state()))

    def test_replay_restore_and_tamper_rejection(self):
        m=ArcMemory();m.remember(task(),[("rot90",)],self.lib,"train")
        restored=ArcMemory.restore(json.loads(json.dumps(m.state())),self.lib)
        self.assertEqual(json.dumps(restored.state(),sort_keys=True),json.dumps(m.state(),sort_keys=True))
        bad=copy.deepcopy(m.state());next(iter(bad['payloads'].values()))['program']=[['flipud']]
        with self.assertRaises(ValueError):ArcMemory.restore(bad,self.lib)

    def test_suppression_reuses_3e_evidence_path(self):
        m=ArcMemory();key=m.remember(task(),[("rot90",)],self.lib,"train")
        self.assertEqual(len(m.candidates(solver_input(task()))),1)
        removed=m.ablate([key])
        self.assertEqual(removed.candidates(solver_input(task())),[])
        self.assertEqual(len(m.actor.diary),1)

    def test_memory_capacity(self):
        m=ArcMemory(limit=1)
        self.assertIsNotNone(m.remember(task(),[("rot90",)],self.lib,"one"))
        self.assertIsNone(m.remember(task(),[("rot90",)],self.lib,"two"))

    def test_recalled_program_still_has_to_fit_current_examples(self):
        m=ArcMemory();m.remember(task(),[("rot90",)],self.lib,"train")
        r=solve(task((("flipud",),)),self.lib,memory=m,max_trials=160,views=False)
        self.assertEqual(r['metrics']['memory_verified'],0)
        self.assertTrue(r['metrics']['memory_reads'])
        self.assertEqual(r['test_ok'],None)

    def test_memory_has_causal_effect_on_first_solution_cost(self):
        case=task((("flipud",),))
        m=ArcMemory();m.remember(case,[("flipud",)],self.lib,"train")
        with_memory=solve(case,self.lib,memory=m,max_trials=160,views=False)
        empty=solve(case,self.lib,max_trials=160,views=False)
        self.assertLess(with_memory['metrics']['first_solution_trial'],empty['metrics']['first_solution_trial'])
        self.assertEqual(with_memory['predictions'],empty['predictions'])

    def test_budget_determinism_and_prefix_cache(self):
        a=solve(task(),self.lib,max_trials=200)
        b=solve(task(),self.lib,max_trials=200)
        self.assertEqual(a,b)
        self.assertLessEqual(a['metrics']['trials'],200)
        self.assertGreater(a['metrics']['cache_hits'],0)
        for p in a['programs']:
            for pair in task()['train']:
                self.assertEqual(execute(dsl.G(pair['input']),p,self.lib),dsl.G(pair['output']))

    def test_solver_does_not_change_guide_or_library(self):
        guide=SparsePrimitiveGuide(640);guide.observe(task(),[("rot90",)],self.lib)
        original=bytes(guide.weights),copy.deepcopy(vars(self.lib))
        solve(task(),self.lib,guide=guide,max_trials=100)
        self.assertEqual(original,(bytes(guide.weights),vars(self.lib)))


if __name__=='__main__':unittest.main()
