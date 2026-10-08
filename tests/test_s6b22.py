import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import Future
from unittest.mock import patch

from echo_arc import s6b22_search as s
from seed import s6b22 as r, s6b22_build as build
from seed.s6b22_review import paired_summary
from tests.test_s6b18 import fixture


def data():
    policy,rows,event,*_=fixture()
    event.update(id=1,target_id=None,schedule=dict(phase='global',global_index=0))
    event['proposal']['patches'][0]['set']['HOLD']=4
    event['development']['case_effects'][0]['level_delta']=4
    for case in event['development']['candidate_consumers']:
        for reading in case:reading['value']=4
    return policy,dict(rows=rows),event


def child(template,request,gain=4,loss=-0.4):
    e=copy.deepcopy(template)
    e.update(id=request['id'],target_id=request['target_id'],proposal=request['proposal'],schedule=request['schedule'])
    e['development']['case_effects'][0]['level_delta']=gain
    e['development']['case_effects'][1]['score_delta']=loss
    for case in e['development']['candidate_consumers']:
        for reading in case:reading['value']=e['proposal']['patches'][0]['set']['HOLD']
    return e


class SearchTests(unittest.TestCase):
    def setUp(self):self.policy,self.base,self.parent=data()

    def test_plus_four_one_loss_reserves_two_guard_repairs(self):
        first=s.request('M22',1,5,self.policy,self.base,[self.parent])
        h=[self.parent,child(self.parent,first,gain=0,loss=0)]
        second=s.request('M22',2,5,self.policy,self.base,h)
        for n,req in enumerate((first,second),1):
            self.assertEqual(req['schedule']['phase'],'repair')
            self.assertEqual(req['schedule']['child'],n)
            self.assertEqual(req['target_id'],1)
            self.assertEqual(req['proposal']['patches'][0]['set'],{'HOLD':4})
            self.assertNotEqual(req['proposal']['patches'][0]['when'],self.parent['proposal']['patches'][0]['when'])
        self.assertNotEqual(first['proposal'],second['proposal'])

    def test_failed_child_does_not_inherit_parent_gain(self):
        req=s.request('M22',1,5,self.policy,self.base,[self.parent])
        failed=child(self.parent,req,gain=0,loss=0)
        self.assertEqual(s.effects(failed),(0,[]))
        self.assertNotIn(failed,s.eligible([self.parent,failed]))
        self.assertIsNone(req['measured_effect']);self.assertIsNone(req['predicted_gain'])
        self.assertEqual(req['loss_risk'],'unknown')
        self.assertEqual(req['antecedent']['parent_gain'],4)

    def test_repair_budget_preserves_ten_global_attempts(self):
        history=[]
        with patch.object(s,'base_pool',return_value=(([{'level':['le',4]}]),{})):
            for index in range(18):
                req=s.request('M22',index,23,self.policy,self.base,history)
                history.append(child(self.parent,req))
        repairs=[e for e in history if e['schedule']['phase']=='repair']
        self.assertEqual(len(repairs),8)
        self.assertEqual(len(history)-len(repairs),10)
        self.assertEqual([e['schedule']['child'] for e in repairs],[1,2]*4)
        self.assertTrue(any(e['schedule']['unserved'] for e in history))

    def test_final_slot_does_not_promise_two_repairs(self):
        history=[]
        with patch.object(s,'base_pool',return_value=(([{'level':['le',4]}]),{})):
            for index in range(17):
                req=s.request('R22',index,1,self.policy,self.base,history)
                history.append(child(self.parent,req,gain=4 if index==16 else 0,loss=-0.4 if index==16 else 0))
            req=s.request('M22',17,1,self.policy,self.base,history)
        self.assertEqual(req['schedule']['phase'],'global')
        self.assertIn({'parent_id':17,'reason':'remaining slots'},req['schedule']['unserved'])

    def test_exhausted_neighborhood_returns_slots(self):
        with patch.object(s,'neighbors',return_value=[]),patch.object(s,'base_pool',return_value=((),{})):
            req=s.request('M22',1,1,self.policy,self.base,[self.parent])
        self.assertEqual(req['schedule']['phase'],'global')
        self.assertEqual(req['schedule']['unserved'][0]['parent_id'],1)

    def test_random_proposal_ignores_own_outcome_and_observations(self):
        changed=copy.deepcopy(self.parent)
        changed['development']['case_effects'][0]['level_delta']=99
        changed['development']['candidate_consumers'][0][0]['features']['level']=3
        with patch.object(s,'base_pool',return_value=(([{'level':['le',4]}]),{})):
            a=s.request('R22',1,71,self.policy,self.base,[self.parent])
            b=s.request('R22',1,71,self.policy,self.base,[changed])
        self.assertEqual(a,b)

    def test_global_stream_paired_by_global_counter_not_slot(self):
        with patch.object(s,'base_pool',return_value=((),{})):
            a=s.global_candidate(71,0,self.policy,self.base['rows'])
            b=s.request('M22',0,71,self.policy,self.base,[])
            c=s.request('R22',0,71,self.policy,self.base,[])
        self.assertEqual(a[0],b['proposal']);self.assertEqual(c['proposal'],b['proposal'])

    def test_order_is_reproducible(self):
        a=s.request('M22',1,9,self.policy,self.base,[self.parent])
        b=s.request('M22',1,9,self.policy,json.loads(json.dumps(self.base,sort_keys=True)),[self.parent])
        self.assertEqual(a,b)
        with self.assertRaisesRegex(ValueError,'history'):
            s.request('M22',1,9,self.policy,self.base,[])

    def test_neighbors_are_legal_single_literal_edits(self):
        g={'level':['le',4],'pred_error':['eq',0],'pending_effect':['eq',0]}
        for other in s.neighbors(g):
            self.assertTrue(s.language.legal(other));self.assertLessEqual(len(other),3)
            old=set((k,*v) for k,v in g.items());new=set((k,*v) for k,v in other.items())
            self.assertLessEqual(max(len(old-new),len(new-old)),1)

    def test_case_length_does_not_multiply_ranking_weight(self):
        g={'pred_error':['eq',0]}
        before=s.overlap(g,self.parent,self.policy)
        changed=copy.deepcopy(self.parent)
        changed['development']['candidate_consumers'][1]*=100
        for reading in changed['development']['candidate_consumers'][0]:reading['count']=999999
        self.assertEqual(before,s.overlap(g,changed,self.policy))

    def test_no_observed_context_means_unknown_overlap(self):
        self.parent['development']['candidate_consumers'][1]=[]
        self.assertIsNone(s.overlap({'pred_error':['eq',0]},self.parent,self.policy)[0])

    def test_legal_variants_survive_observational_equivalence(self):
        neighbors=s.neighbors({'reset_known':['eq',1]})
        self.assertIn({'reset_known':['eq',1],'pred_error':['eq',0]},neighbors)
        self.assertIn({'reset_known':['eq',1],'pending_effect':['eq',0]},neighbors)

    def test_task_identifier_guard_and_multiple_patches_rejected(self):
        p={'patches':[{'when':{'seed':['eq',822101]},'set':{'HOLD':4}}]}
        with self.assertRaises(ValueError):s.validate_proposal(p)
        p=self.parent['proposal'];p=copy.deepcopy(p);p['patches']*=2
        with self.assertRaises(ValueError):s.validate_proposal(p)

    def test_protected_foreign_and_incomplete_history_rejected(self):
        for change in ('protected','base','cases'):
            e=copy.deepcopy(self.parent)
            if change=='protected':e['development']['origin']='PROTECTED_B'
            if change=='base':e['base_sha256']='other'
            if change=='cases':e['development']['case_effects'].pop()
            with self.assertRaises(ValueError):s.request('M22',1,1,self.policy,self.base,[e])

    def test_input_surface_excludes_winner_future_and_documents(self):
        obj=dict(policy=self.policy,base=self.base,own_history=[],kind='R22',index=0,seed=10)
        for name in ('winner','future_cohort','research_pdf'):
            with self.assertRaisesRegex(ValueError,'surface'):s.from_bytes(json.dumps(dict(obj,**{name:True})).encode())
        with patch('builtins.open',side_effect=AssertionError('file')),patch('pathlib.Path.open',side_effect=AssertionError('file')),patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.Popen',side_effect=AssertionError('process')),patch.object(s,'base_pool',return_value=((),{})):
            self.assertIn('proposal',s.from_bytes(json.dumps(obj).encode()))


class RunnerTests(unittest.TestCase):
    def test_budget_partition_and_disabled_later_stages(self):
        self.assertEqual(r.MAX_GAMES,15336)
        self.assertEqual(len(r.CELLS),16)
        self.assertFalse(set(r.V_NEW)&set(r.S_NEW))
        self.assertFalse(set(r.DEVELOPMENT)&set(r.V_NEW+r.S_NEW))
        self.assertEqual(r.config()['model_calls_cap'],0)
        self.assertFalse(r.config()['exam_allowed'])

    def test_random_winner_selected_without_M_winner(self):
        winner={'slot':2,'policy':{'example':True}}
        selection=r.select_finalists({f'R22-{r.SEEDS[2]}':winner})
        self.assertEqual(set(selection),{'R22'})

    def test_finalists_use_seed_priority_not_finish_time_or_score(self):
        winners={f'M22-{r.SEEDS[5]}':dict(slot=1,policy='fast'),f'M22-{r.SEEDS[0]}':dict(slot=18,policy='first')}
        self.assertEqual(r.select_finalists(winners)['M22']['policy'],'first')

    def test_individual_score_loss_vetoes_aggregate_gain(self):
        self.assertFalse(r.passes(dict(gain=8,loss_indices=[2])))
        self.assertFalse(r.passes(dict(gain=1,loss_indices=[])))
        self.assertTrue(r.passes(dict(gain=0,loss_indices=[]),True))

    def test_replay_mismatch_blocks_before_audit(self):
        with patch.object(r,'measure',side_effect=[{'levels':1},{'levels':2}]),patch.object(r.subprocess,'run') as process:
            with self.assertRaisesRegex(RuntimeError,'replay'):r.triple('v-micro','x',{},r.A)
            process.assert_not_called()

    def test_audit_difference_blocks(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'integrity',return_value={}),patch.object(r,'measure',return_value={'levels':2}):
            r.atomic(Path(d)/'task.json',dict(namespace='v-micro',label='x',policy={},specs=r.A))
            r.atomic(Path(d)/'v-micro/measurements/x.json',{'levels':1})
            with self.assertRaisesRegex(RuntimeError,'independent trajectory'):r.audit_measure(Path(d)/'task.json')

    def test_protected_measure_requires_permit_and_policy(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'integrity',return_value={}):
            with self.assertRaisesRegex(ValueError,'closed'):r.check_permit({},r.V_NEW)
            r.atomic(Path(d)/'permits/v-new.json',dict(profile_sha256=r.sha({}),policies=['other'],cohort_sha256=r.sha(r.V_NEW)))
            with self.assertRaisesRegex(ValueError,'unregistered'):r.check_permit({},r.V_NEW)

    def test_protected_observation_refused_before_execution(self):
        with self.assertRaisesRegex(ValueError,'protected'):r.play_one(({},r.V_NEW[0],'viewer','unused',{}))

    def test_finalists_frozen_before_protection(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'):
            r.atomic(Path(d)/'input/baseline.json',dict(policy={}))
            with self.assertRaisesRegex(RuntimeError,'freeze'):r.permit('v-new',[{}],{})

    def test_reservation_is_durable_and_stage_cap_cannot_borrow(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            tasks=[dict(task_id=str(i)) for i in range(r.CAPS['V'])]
            first=r.reserve_tasks(tasks,'v-micro','failed')
            again=r.reserve_tasks(tasks,'v-micro','resume')
            self.assertEqual(first,again)
            with self.assertRaisesRegex(RuntimeError,'allocation'):r.reserve_tasks([dict(task_id='new')],'v-micro','retry')
            self.assertEqual(r.read(Path(d)/'budget.json')['scheduled_games'],1512)

    def test_input_bytes_persist_and_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r.search,'from_bytes',return_value={}):
            _,digest=r.persist_input({'data':True})
            path=Path(d)/'investigator-inputs'/(digest+'.json.gz')
            path.write_bytes(gzip.compress(b'changed'))
            with self.assertRaisesRegex(RuntimeError,'bytes changed'):r.persist_input({'data':True})

    def test_runtime_excludes_controls_and_research_documents(self):
        files=build.closure()
        self.assertIn('echo_arc/s6b22_search.py',files)
        self.assertNotIn('seed/s6b20_capacity.py',files)
        self.assertFalse(any(x.startswith(('docs/','tests/')) for x in files))

    def test_instrument_failure_cannot_be_scientific_fail(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'follow',side_effect=RuntimeError('broken')),patch.object(r,'status') as status:
            with self.assertRaises(RuntimeError):r.main(['follow'])
            self.assertEqual(status.call_args.args[0],'INVALID')

    def test_measure_resume_replay_and_audit_use_correct_caches_and_budget(self):
        class Pool:
            def __init__(self,**kw):pass
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def submit(self,fn,job):
                future=Future()
                try:future.set_result(fn(job))
                except Exception as exc:future.set_exception(exc)
                return future
        def fake_game(job):
            policy,spec,directory,dest,task=job
            record=dict(version=spec[0],seed=spec[1],rep=spec[2],budget=spec[3],levels_completed=1,score=1)
            r.atomic(r.ROOT/'executions/started'/f"{task['job_id']:06d}.json",dict(task_id=task['task_id']))
            r.atomic(Path(dest),dict(key=task['key'],record=record,digest=r.sha(record),job_id=task['job_id']))
            r.atomic(r.ROOT/'executions/completed'/f"{task['job_id']:06d}.json",dict(task_id=task['task_id']))
            return record,{}
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'integrity',return_value={}),patch.object(r,'ProcessPoolExecutor',Pool),patch.object(r,'play_one',side_effect=fake_game) as worker,patch.object(r,'status'):
            a=r.measure('v-micro','baseline',{},r.A)
            self.assertEqual(worker.call_count,12)
            self.assertEqual(a,r.measure('v-micro','baseline',{},r.A))
            self.assertEqual(worker.call_count,12)
            self.assertEqual(a,r.measure('v-micro','baseline/replay',{},r.A,True))
            self.assertEqual(a,r.measure('v-micro-audit','baseline',{},r.A))
            self.assertEqual(worker.call_count,36)
            self.assertEqual(r.read(Path(d)/'budget.json')['scheduled_games'],36)
            cache=next((Path(d)/'v-micro/cache/main').glob('*.json'))
            broken=r.read(cache);broken['record']['score']=999;r.atomic(cache,broken)
            with self.assertRaisesRegex(RuntimeError,'checksum'):r.measure('v-micro','baseline',{},r.A)

    def test_interrupted_game_blocks_without_free_retry(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'integrity',return_value={}):
            spec=r.A[0]
            key=r.sha(dict(profile=r.sha({}),namespace='v-micro',policy={},spec=spec,observed=True))
            task=dict(task_id=r.sha(['v-micro','main',key]),key=key,spec=spec,policy_sha256=r.sha({}),cache='x',journal=None)
            job=r.reserve_tasks([task],'v-micro','baseline')[0]
            r.atomic(Path(d)/'executions/started'/f"{job['job_id']:06d}.json",{})
            with patch.object(r,'ProcessPoolExecutor') as pool:
                with self.assertRaisesRegex(RuntimeError,'interrupted game'):r.measure('v-micro','baseline',{},r.A)
                pool.assert_not_called()

    def test_protected_permit_requires_audited_broad_pass(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'),patch.object(r,'integrity',return_value={}):
            r.atomic(Path(d)/'input/baseline.json',dict(policy={}))
            r.atomic(Path(d)/'finalists.json',dict(selection={}))
            result=dict(passed=False,audited=True,policy_sha256=r.sha({'p':1}))
            r.atomic(Path(d)/'v-broad.json',result)
            with self.assertRaisesRegex(RuntimeError,'qualification'):r.permit('v-new',[{'p':1}],{'v-broad':r.sha(result)})
            result['passed']=True;r.atomic(Path(d)/'v-broad.json',result)
            r.permit('v-new',[{'p':1}],{'v-broad':r.sha(result)})
            r.check_permit({'p':1},r.V_NEW)


class StatisticsTests(unittest.TestCase):
    def test_no_discordance_and_all_failures_are_retained(self):
        result=paired_summary({},list(range(8)))
        self.assertEqual(result['mcnemar_exact_two_sided'],1)
        self.assertEqual(result['outcomes']['neither'],8)
        self.assertEqual(result['capped_rank_to_first_pass']['M22'],[19]*8)

    def test_exact_paired_test_and_direction(self):
        winners={f'M22-{s}':dict(slot=2) for s in range(8)}
        result=paired_summary(winners,list(range(8)))
        self.assertEqual(result['mcnemar_exact_two_sided'],2/256)
        self.assertTrue(result['directional_pilot_evidence'])
        reverse=paired_summary({k.replace('M22','R22'):v for k,v in winners.items()},list(range(8)))
        self.assertFalse(reverse['directional_pilot_evidence'])
        self.assertFalse(result['generalization_confirmed'])


if __name__=='__main__':unittest.main()
