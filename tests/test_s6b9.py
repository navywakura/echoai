import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from echo_arc import repair_loop_requests as prompts,stale_transition as p
from echo_arc.repair_loop_grammar import Grammar
from seed import s6b9 as s


def row(levels=0,contradictions=0,reads=0):
    features={k:lo for k,(lo,_) in p.FEATURES.items()}
    return {'origin':'DEVELOPMENT_A','levels_completed':levels,'seed':'secret-id',
            'diagnostics':{'counts':{'contradictory_noop':contradictions},
             'contradictory_noop_examples':[{'features':features,'state':'private-state-hash'}] if contradictions else [],
             'consumers':[{'parameter':'HOLD','value':40,'remaining_before':0,'count':reads,'features':features}] if reads else [],
             'witnesses':{}}}


class Contract(unittest.TestCase):
    def test_guarded_transition_revision_is_model_expressible(self):
        text='{"patches":[{"set":{"REVALIDATE_NOOP":3},"when":{"stagnation":["ge",32]}}]}'
        grammar=Grammar(lambda x:list(x.encode()),256);tokens=list(text.encode())
        for i,token in enumerate(tokens):self.assertIn(token,grammar.allowed(tokens[:i]))
        self.assertIn(256,grammar.allowed(tokens));p.parse(text)

    def test_selector_adapts_to_remaining_mechanisms_without_private_ids(self):
        observed=[row(0,0,0),row(2,100,0),row(1,0,10)]
        cases,focus=prompts.evidence(observed,'echo',[],0)
        self.assertEqual(focus,'transition');self.assertEqual(cases['cases'][0]['levels'],2)
        changed=[row(0,0,0),row(5,0,0),row(1,0,10)]
        self.assertEqual(prompts.evidence(changed,'echo',[],1)[1],'wait')
        fixed,_=prompts.evidence(observed,'fijo',[],0)
        self.assertEqual(fixed['cases'][0]['levels'],0)
        text=str(prompts.requests('echo',0,1,s.strategy(),{'rows':observed},[
            {'verdict':'V4','B':{'secret':'protected-map'},'reason':'protected-reason'}]))
        for value in ('secret-id','private-state-hash','protected-map','protected-reason'):
            self.assertNotIn(value,text)
        with self.assertRaises(ValueError):prompts.evidence([dict(row(),origin='PROTECTED_B')],'echo',[],0)

    def test_runner_bindings_budget_and_cpu_wrapper(self):
        self.assertEqual(s.run_phase.__defaults__,(False,))
        self.assertIs(s.run_phase.__globals__['verifier'],s.verifier)
        self.assertIs(s.run_phase.__globals__['requests'],s.requests)
        self.assertEqual(s.config()['calls_including_calibration'],82)
        self.assertNotEqual(s.EXAM_SEEDS,s.parent.EXAM_SEEDS)
        generator=s.generator();code=generator.template().replace('PAYLOAD',repr('e30='))
        compile(code,'b9-wrapper','exec')
        self.assertIn('repair_loop_grammar import Grammar',code)
        self.assertIn('stale_transition as local_patch',code)
        self.assertFalse(generator.metadata('p0')['enable_gpu'])
        self.assertEqual(generator.metadata('c5')['kernel_sources'],[s.CACHE_REF])
        with self.assertRaises(AssertionError):generator.metadata('p3')

    def test_raw_accepts_executable_new_operation_without_utility_gate(self):
        proposal={'patches':[{'when':{'stagnation':['ge',32]},'set':{'REVALIDATE_NOOP':3}}]}
        policy,event=s.raw_step('raw',s.strategy(),json.dumps(proposal),lambda *a,**kw:{'trace_digest':'same'})
        self.assertEqual(policy['program'],p.validate(proposal));self.assertEqual(event['verdict'],'EXECUTABLE')
        self.assertEqual(event['V3'],'OMITTED');self.assertEqual(event['V4'],'OMITTED')

    def test_exam_uses_extended_execution_for_official_conservation(self):
        from seed import s6b9_exam
        self.assertIs(s6b9_exam.run.__globals__['s'],s)
        self.assertIs(s6b9_exam.development.__globals__['s'],s)
        self.assertIs(s6b9_exam.development.__globals__['development_one'],s6b9_exam.development_one)


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('arcengine'),'managed ARC runtime')
class Native(unittest.TestCase):
    def test_combined_observer_preserves_native_and_new_operation_behavior(self):
        from echo_arc import agent
        from echo_arc.observe import Journal
        from echo_arc.temporal_bench import _gym_env
        from echo_arc.repair_loop_observe import Recorder
        for program in (p.EMPTY,{'patches':[{'when':{'stagnation':['ge',8]},'set':{'REVALIDATE_NOOP':2}}]}):
            value=s.strategy(program)
            agent._COMP_CACHE.clear()
            native=s.Execution.play(_gym_env(3,11),300,12345,value)
            with tempfile.TemporaryDirectory() as directory:
                recorder=Recorder(Journal(Path(directory)/'arc-decisions.jsonl'),origin='DEVELOPMENT_A',program=program)
                agent._COMP_CACHE.clear()
                try:observed=s.Execution.play(_gym_env(3,11),300,12345,value,recorder)
                finally:recorder.close()
                self.assertEqual(native,observed)
                self.assertIn('consumers',recorder.summary())
                self.assertIn('contradictory_noop_examples',recorder.summary())


if __name__=='__main__':unittest.main()
