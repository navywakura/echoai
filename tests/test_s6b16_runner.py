import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from seed import s6b16 as r, s6b16_micro as micro
from tests.test_s6b16_policy import pair, target
from tests.test_s6b14_policy import measured_row


class RunnerTests(unittest.TestCase):
    def setUp(self): r.configure()
    def tearDown(self): r.configure()

    def test_paired_first_requests_are_identical_and_have_no_B15_attempts(self):
        policy,measured,history=micro.reference()
        first=micro.request('previous',0,policy,measured,history)
        second=micro.request('updated',0,policy,measured,history)
        self.assertEqual(first,second)
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['verdict'],'accepted')
        self.assertEqual(first['requested_operator'],'HOLD')

    def test_micro_pass_is_not_protected_acceptance_or_policy_promotion(self):
        before,after=pair()
        for a,b in zip(after['rows'],before['rows']):
            a['levels_completed']=max(a['levels_completed'],b['levels_completed'])
            a['score']=max(a['score'],b['score'])
        after.update(levels=sum(a['levels_completed'] for a in after['rows']),trace_digest=r.b.sha(after['rows']))
        current=r.b.strategy()
        req=r.prompts.request('fijo',1,current,before,[])
        response=dict(answer=r.prompts.random_answer(req,41),usage={'input_tokens':10})
        with patch.object(r.b,'reproduced',return_value=after):
            event,summary=micro.evaluate(None,'fixture',req,response,current,before,[],'updated',0)
        self.assertTrue(summary['passes_A'])
        self.assertEqual(event['verdict'],'A_ONLY_PASS')
        self.assertNotIn('B',event)
        self.assertEqual(current['program'],r.b.patch.EMPTY)

    def test_gate_checks_outcomes_not_just_pass_flag(self):
        cell=dict(arm='updated',gain=5,loss_indices=[],levels=383,reproduced=True,
                  actual_operator='HOLD',requested_operator='HOLD')
        self.assertTrue(micro.gate([cell]))
        for change in ({'arm':'previous'},{'loss_indices':[51]},{'gain':1,'levels':379},{'reproduced':False}):
            self.assertFalse(micro.gate([dict(cell,**change)]))

    def test_new_audit_dispatch_workers_and_budget(self):
        self.assertEqual(r.b.MAX_CALLS,120)
        self.assertEqual(r.b.MAX_GAMES,64000)
        self.assertEqual(r.b.subprocess.STDOUT,subprocess.STDOUT)
        with patch.object(r.subprocess,'run') as run:
            r.b.subprocess.run(['python','-m','seed.s6b13','audit','pilot'],stderr=subprocess.STDOUT)
            self.assertEqual(run.call_args.args[0][-3:],['seed.s6b16','audit','pilot'])
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'ROOT',Path(tmp)):
            m=r.measurement('pilot-independent')
            self.assertEqual(m.__globals__['ROOT'],Path(tmp)/'pilot-independent')
            self.assertIs(m.__globals__['old'].worker_init,r.worker_init)

    def test_negative_micro_stops_chain_and_viewer_has_existing_journal(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'ROOT',Path(tmp)), \
                patch.object(r,'previous_closed',return_value=True),patch.object(r.b,'prepare'), \
                patch.object(r,'status'),patch.object(r,'publish'),patch.object(micro,'run'), \
                patch.object(r,'micro_gate',return_value=False), \
                patch.object(r.b,'follow',side_effect=AssertionError('no pilot')):
            with patch.object(r.subprocess,'Popen',side_effect=lambda cmd,**kw:self.assertTrue(Path(cmd[-1]).exists())):
                r.dispatch(['follow'])
            self.assertFalse(json.loads((Path(tmp)/'closed.json').read_text())['exam_opened'])

    def test_phase_results_reconstruct_with_updated_feedback(self):
        rows=[measured_row(i) for i in range(2)]
        for row in rows:
            row.update(frames=['f'],actions_per_level=[1],resets=0,automatic_reset_indices=[])
        value=dict(rows=rows,levels=6,score=2,trace_digest=r.b.sha(rows))
        responses={}
        def generate(call,req,*a,**kw):
            response=dict(answer=r.prompts.random_answer(req,41),usage={'input_tokens':1,'max_output_tokens':160})
            responses[call]=response
            return response
        with tempfile.TemporaryDirectory() as tmp,patch.object(r.b,'ROOT',Path(tmp)),patch.object(r.b,'_journal',None), \
                patch.object(r.b,'integrity',return_value={}),patch.object(r.b,'phase_shape',return_value=(3,1,(1,))), \
                patch.object(r.b,'measurement',return_value=lambda *a,**kw:copy.deepcopy(value)), \
                patch.object(r.model,'propose',side_effect=generate), \
                patch.object(r.model,'load',side_effect=lambda call,*a,**kw:responses[call]), \
                patch.object(r.b,'status'),patch.object(r.b,'publish'):
            result=r.b.run_phase('pilot')
            self.assertEqual(len(result['verdicts']),9)
            self.assertTrue(all('gross_level_gain' in e['development'] for e in result['verdicts']))
            r.b.atomic(Path(tmp)/'pilot-process.json',{'pid':-1})
            self.assertEqual(result,r.b.run_phase('pilot',audit=True))

    def test_old_condition_sources_and_new_partitions(self):
        old=json.loads((r.PREVIOUS/'profile.json').read_text())
        for name,expected in old['sources'].items():
            self.assertEqual(r.model.digest_file(r.REPO/name),expected,name)
        self.assertFalse(set(r.b.EXAM_SEEDS)&set(old['configuration']['exam_seeds']))
        self.assertFalse(set(map(tuple,r.b.B))&set(map(tuple,old['configuration']['B'])))


if __name__=='__main__': unittest.main()
