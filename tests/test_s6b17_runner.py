import copy
import json
from pathlib import Path
import pickle
import tempfile
import unittest
from unittest.mock import patch

from seed import s6b17 as r, s6b17_prompt as p
from echo_arc import consumption_timeline as timeline
from tests.test_s6b17_timeline import row


def measured(rows):
    return dict(rows=rows,levels=sum(x['levels_completed'] for x in rows),score=sum(x['score'] for x in rows),trace_digest=r.sha(rows))


class RunnerTests(unittest.TestCase):
    def test_same_initial_llm_request_and_separate_no_llm_arm(self):
        policy,base,initial=r.reference_module.reference()
        self.assertEqual(p.request('b16',0,policy,base,initial),p.request('hybrid',0,policy,base,initial))
        req=p.request('synth',0,policy,base,initial)
        answer=p.deterministic_answer(req)
        self.assertEqual(p.check_answer(answer,req)['patches'][0]['set'],{'HOLD':0})
        self.assertLessEqual(len(req['shortlist']),8)

    def test_worker_refuses_protected_games_before_running(self):
        with patch.object(r,'_native_play',side_effect=AssertionError('must not play')):
            with self.assertRaises(ValueError):r.play_one((r.core.strategy(),(2,99999,0,2000),None))
        pickle.dumps(r.play_one);pickle.dumps(r.worker_init)

    def test_evaluation_preserves_zero_individual_loss_gate(self):
        before=measured([row(0),row(1)])
        after=copy.deepcopy(before)
        after['rows'][0]['levels_completed']+=4
        after['rows'][1]['score']-=0.1
        after=measured(after['rows'])
        proposal={'patches':[{'set':{'HOLD':1},'when':{'reset_known':['eq',1]}}]}
        req=dict(type='WAIT',target_id=None,requested_operator='HOLD')
        response=dict(answer=r.canonical(proposal),usage={'input_tokens':1})
        with patch.object(p,'check_answer',return_value=proposal),patch.object(r,'measured',return_value=after):
            event,summary=r.evaluate(None,'fixture','hybrid',0,req,response,r.core.strategy(),before,[],False)
        self.assertEqual(summary['gain'],4)
        self.assertFalse(summary['passes_A'])
        self.assertEqual(event['verdict'],'V3')
        self.assertNotIn('B',event)

    def test_independent_result_difference_stops_instrument(self):
        before=measured([row()]);after=copy.deepcopy(before)
        proposal={'patches':[{'set':{'HOLD':1},'when':{'reset_known':['eq',1]}}]}
        req=dict(type='WAIT',target_id=None,requested_operator='HOLD')
        response=dict(answer=r.canonical(proposal),usage={})
        with patch.object(p,'check_answer',return_value=proposal),patch.object(r,'measured',return_value=after), \
                patch.object(r,'read',return_value={'corrupted':True}):
            with self.assertRaisesRegex(RuntimeError,'independent candidate'):
                r.evaluate(None,'fixture','hybrid',0,req,response,r.core.strategy(),before,[],True)

    def test_json_materialization_and_instrument_removal_preserve_reference(self):
        old=row();new=copy.deepcopy(old)
        old['diagnostics'].pop('control_timeline')
        self.assertEqual(timeline.legacy_rows([new]),[old])
        self.assertIn('control_timeline',new['diagnostics'])

    def test_equal_evaluation_caps_and_sealed_exam(self):
        cfg=r.config()
        self.assertEqual(cfg['per_arm_candidate_slots'],8)
        self.assertEqual(cfg['per_arm_candidate_game_cap'],1280)
        self.assertEqual(cfg['primary_game_cap'],160+3*1280)
        self.assertEqual(cfg['independent_audit_game_cap'],80+24*80)
        self.assertEqual(cfg['B'],[]);self.assertEqual(cfg['exam_seeds'],[])
        self.assertEqual(r.ARMS,('b16','synth','hybrid'))

    def test_full_micro_and_fresh_audit_rebuild_and_reject_tampered_verdict(self):
        # Transport fixture only: no environment or model is executed here.
        base=measured([row()]);base['rows'][0]['levels_completed']=378
        base=measured(base['rows']);old=measured(timeline.legacy_rows(base['rows']))
        req=dict(type='WAIT',target_id=None,requested_operator='HOLD',shortlist=[],
                 guard_schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],groups=[]))
        response=dict(answer='{"patches":[]}',usage=dict(input_tokens=0,max_output_tokens=0))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def factory(namespace):
                def measure(label,*args,**kwargs):
                    r.atomic(root/namespace/'measurements'/(label+'.json'),base)
                    return copy.deepcopy(base)
                return measure
            with patch.object(r,'ROOT',root),patch.object(r,'ROUNDS',1), \
                    patch.object(r,'integrity',return_value={}),patch.object(r,'measurement',side_effect=factory), \
                    patch.object(r.reference_module,'reference',return_value=(r.core.strategy(),old,[])), \
                    patch.object(p,'request',return_value=req),patch.object(r,'status'),patch.object(r,'visible'), \
                    patch.object(r.model,'propose',return_value=response) as generation, \
                    patch.object(r.model,'load',return_value=response) as loading:
                primary=r.run()
                self.assertEqual(generation.call_count,2)
                self.assertFalse(primary['promote'])
                self.assertEqual(r.run(audit=True)['cells'],primary['cells'])
                self.assertEqual(generation.call_count,2)
                self.assertEqual(loading.call_count,2)
                self.assertEqual(r.read(root/'micro-audit.json')['verdicts_rebuilt'],3)
                path=root/'steps/micro/b16/000.json';saved=r.read(path)
                saved['event']['verdict']='A_ONLY_PASS';r.atomic(path,saved)
                with self.assertRaisesRegex(RuntimeError,'verdict differs'):
                    r.run(audit=True)


if __name__=='__main__':unittest.main()
