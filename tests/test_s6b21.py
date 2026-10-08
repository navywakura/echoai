import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echo_arc import s6b21_search as s, s6b21_archive as archive
from seed import s6b21 as r
from seed import s6b21_build as build
from tests.test_s6b18 import fixture,features


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.policy,self.rows,self.event,self.schema,_,_=fixture()
        self.event['proposal']['patches'][0]['set']['HOLD']=1
        for case in self.event['development']['candidate_consumers']:
            for read in case:read['value']=1
        self.measured={'rows':self.rows}

    def test_without_parent_all_durations_are_available_before_repetition(self):
        guards=[{'level':['le',4]},{'world_events':['ge',8]}]
        with patch.object(s.baseline,'pool',return_value=(guards,{})):
            proposals=[s.request('balanced',i,71,self.policy,self.measured,[])['proposal'] for i in range(10)]
        self.assertEqual(set(s.VALUES),{p['patches'][0]['set']['HOLD'] for p in proposals})
        self.assertEqual(len({p['patches'][0]['set']['HOLD'] for p in proposals}),10)

    def test_agenda_has_five_general_five_diversity_then_four_repairs(self):
        a=s.agenda(51)
        self.assertEqual(sum(x['mode']=='general' for x in a[:10]),5)
        self.assertEqual(sum(x['mode']=='diversity' for x in a[:10]),5)
        self.assertEqual(sum(x['phase']=='repair' for x in a[10:]),4)
        self.assertEqual([x['mode'] for x in a[10:] if x['phase']=='repair'],['scope','duration','scope','duration'])
        self.assertEqual(a,s.agenda(51));self.assertNotEqual(a[:10],s.agenda(52)[:10])

    def test_general_distribution_does_not_require_baseline_activation(self):
        draws=[s.general_guard(25,i) for i in range(100)]
        self.assertTrue(all(s.baseline.legal(g) for g in draws))
        self.assertEqual({1,2,3},{len(g) for g in draws})
        self.assertTrue(any(not any(s.matches(g,x['features']) for row in self.rows for x in row['diagnostics']['consumers']) for g in draws))

    def test_reordering_library_does_not_change_seeded_decision(self):
        guards=[{'level':['le',4]},{'world_events':['ge',8]}]
        with patch.object(s.baseline,'pool',return_value=(guards,{})):
            a=s.diversity_guard(12,0,self.rows,self.policy,[])[0]
        with patch.object(s.baseline,'pool',return_value=(list(reversed(guards)),{})):
            b=s.diversity_guard(12,0,self.rows,self.policy,[])[0]
        self.assertEqual(a,b)

    def test_new_observation_splits_previously_equal_guard_signatures(self):
        a={'reset_known':['eq',1]};b={'reset_known':['eq',1],'pred_error':['eq',0]}
        old=s.baseline.points_for(self.rows,[],self.policy)
        new=s.baseline.points_for(self.rows,[self.event],self.policy)
        self.assertEqual(s.signature(a,old),s.signature(b,old))
        self.assertNotEqual(s.signature(a,new),s.signature(b,new))

    def test_random_control_is_not_driven_by_outcome_score(self):
        changed=copy.deepcopy(self.event)
        changed['development']['case_effects'][0]['level_delta']=100
        changed['development']['case_effects'][1]['score_delta']=-99
        with patch.object(s.baseline,'pool',return_value=([{'reset_known':['eq',1]}],{})):
            for i in range(4):
                a=s.request('random',i,45,self.policy,self.measured,[self.event])
                b=s.request('random',i,45,self.policy,self.measured,[changed])
                self.assertEqual(a['proposal'],b['proposal'])

    def test_repair_can_reduce_duration(self):
        self.event['proposal']['patches'][0]['set']['HOLD']=32
        req=s.request('balanced',12,45,self.policy,self.measured,[self.event])
        self.assertEqual(req['schedule']['mode'],'duration')
        self.assertLess(req['proposal']['patches'][0]['set']['HOLD'],32)
        self.assertEqual(req['proposal']['patches'][0]['when'],self.event['proposal']['patches'][0]['when'])

    def test_scope_repair_can_change_guard_without_inheriting_an_anchor(self):
        guards=[{'pred_error':['eq',0]},{'level':['le',4]}]
        with patch.object(s.baseline,'pool',return_value=(guards,{})):
            req=s.request('balanced',10,45,self.policy,self.measured,[self.event])
        self.assertNotEqual(req['proposal']['patches'][0]['when'],self.event['proposal']['patches'][0]['when'])
        self.assertEqual(req['proposal']['patches'][0]['set']['HOLD'],1)
        self.assertNotIn('accepted',req)

    def test_no_parent_fallback_still_consumes_the_scheduled_slot(self):
        req=s.request('balanced',10,8,self.policy,self.measured,[])
        self.assertEqual(req['id'],11);self.assertIn('fallback',req['schedule'])
        self.assertIsNone(req['target_id'])

    def test_foreign_base_and_protected_data_block(self):
        bad=copy.deepcopy(self.event);bad['base_sha256']='foreign'
        with self.assertRaisesRegex(ValueError,'foreign'):s.request('balanced',0,7,self.policy,self.measured,[bad])
        bad=copy.deepcopy(self.event);bad['development']['origin']='PROTECTED_B'
        with self.assertRaisesRegex(ValueError,'protected'):s.request('balanced',0,7,self.policy,self.measured,[bad])
        badrows=copy.deepcopy(self.rows);badrows[0]['origin']='PROTECTED_B'
        with self.assertRaises(ValueError):s.request('random',0,7,self.policy,{'rows':badrows},[])

    def test_serialized_surface_rejects_extra_research_document(self):
        data=dict(policy=self.policy,base=self.measured,own_history=[],accepted_history=[],kind='random',index=0,seed=9,document='human control')
        with self.assertRaisesRegex(ValueError,'surface'):s.from_bytes(json.dumps(data).encode())

    def test_researcher_uses_only_serialized_input_no_files_or_network(self):
        data=dict(policy=self.policy,base=self.measured,own_history=[],accepted_history=[],kind='balanced',index=0,seed=9)
        with patch('builtins.open',side_effect=AssertionError('file read')),patch('pathlib.Path.open',side_effect=AssertionError('file read')),patch('socket.socket',side_effect=AssertionError('network')),patch('subprocess.Popen',side_effect=AssertionError('subprocess')),patch.object(s.baseline,'pool',return_value=([{'level':['ge',1]}],{})):
            self.assertIn('proposal',s.from_bytes(json.dumps(data).encode()))

    def test_known_solution_is_never_a_required_output(self):
        # Generic validator invariants; no fixture asserting a human repair.
        for seed in range(20):
            g=s.general_guard(seed,1)
            self.assertEqual(s.validate_proposal({'patches':[{'when':g,'set':{'HOLD':s.VALUES[seed%10]}}]})['patches'][0]['when'],g)

    def test_candidate_cannot_contain_task_identifier_or_multiple_patches(self):
        for p in ({'patches':[{'when':{'seed':['eq',1]},'set':{'HOLD':1}}]},
                  {'patches':[{'when':{'level':['ge',1]},'set':{'HOLD':1}}]*2}):
            with self.assertRaises(ValueError):s.validate_proposal(p)

    def test_parent_limit_and_two_objectives(self):
        positive=copy.deepcopy(self.event);positive['id']=12
        positive['development']['case_effects']=[dict(case_index=0,level_delta=1,score_delta=1),dict(case_index=1,level_delta=0,score_delta=0)]
        positive['development'].update(gross_level_gain=1,losses=0,score_loss=0)
        self.assertEqual(archive.parent(self.policy,[self.event,positive],'repair-loss')['id'],11)
        self.assertEqual(archive.parent(self.policy,[self.event,positive],'increase-gain')['id'],12)
        children=[]
        for n in (13,14):
            e=copy.deepcopy(positive);e.update(id=n,target_id=11);children.append(e)
        self.assertNotEqual(archive.parent(self.policy,[self.event,positive]+children,'repair-loss')['id'],11)

    def test_b20_control_calls_the_frozen_controller(self):
        with patch.object(s.baseline,'request',return_value={'marker':'frozen'}) as f:
            self.assertEqual(s.request('b20',0,0,self.policy,self.measured,[]),{'marker':'frozen'})
            self.assertEqual(f.call_args.args[0],'new')


class RunnerTests(unittest.TestCase):
    def test_budget_and_partitions(self):
        self.assertEqual(len(r.CELLS),7);self.assertEqual(r.config()['model_calls_cap'],0)
        self.assertEqual(len(r.A),12);self.assertEqual(len(r.DEVELOPMENT),160);self.assertEqual(len(r.B),80)
        self.assertFalse(set(r.B)&set(r.DEVELOPMENT));self.assertFalse(r.config()['exam_allowed'])

    def test_reservations_are_never_refunded_after_failed_work(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'):
            r.reserve(r.MAX_GAMES,'x','failed')
            with self.assertRaises(RuntimeError):r.reserve(1,'x','retry')

    def test_replay_mismatch_blocks(self):
        with patch.object(r,'measure',side_effect=[{'levels':1},{'levels':2}]):
            with self.assertRaisesRegex(RuntimeError,'replay'):r.reproduced('x','y',{},r.A)

    def test_protected_partition_cannot_be_measured_without_permit(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            with self.assertRaisesRegex(ValueError,'protection'):r.measure('x','y',{},r.B)

    def test_protected_case_cannot_be_instrumented(self):
        with self.assertRaisesRegex(ValueError,'protected'):r.play_one(({},r.B[0],'viewer'))

    def test_existing_permit_cannot_be_reused_for_another_policy(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'):
            r.atomic(Path(d)/'retention-opened.json',dict(policies={'x':'registered'},profile_sha256='x'))
            r.atomic(Path(d)/'input/baseline.json',dict(policy={'baseline':True}))
            with self.assertRaisesRegex(ValueError,'unregistered'):r.measure('x','y',{'other':True},r.B)

    def test_plus_one_or_score_loss_never_passes(self):
        self.assertFalse(r.previous.a_pass(dict(gain=1,loss_indices=[])))
        self.assertFalse(r.previous.a_pass(dict(gain=8,loss_indices=[1])))
        self.assertTrue(r.previous.a_pass(dict(gain=2,loss_indices=[])))

    def test_retention_requires_audited_qualification(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            r.atomic(Path(d)/'qualification.json',dict(valid=True,winners={'balanced-1':{}}))
            r.atomic(Path(d)/'qualification-audit.json',dict(valid=True,qualification_sha256='wrong'))
            with self.assertRaisesRegex(RuntimeError,'audit'):r.qualify('retention')
            self.assertFalse((Path(d)/'retention-opened.json').exists())

    def test_exact_input_bytes_preserved_and_tampering_blocks(self):
        data={'not':'experiment data'}
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r.search,'from_bytes',return_value={'req':True}):
            request,digest=r.investigator(data)
            p=Path(d)/'investigator-inputs'/(digest+'.json.gz')
            self.assertEqual(gzip.decompress(p.read_bytes()),r.canonical(data).encode())
            self.assertEqual(r.investigator(data,True),(request,digest))
            p.write_bytes(gzip.compress(b'altered'))
            with self.assertRaisesRegex(RuntimeError,'bytes changed'):r.investigator(data,True)

    def test_missing_input_record_is_not_recreated_by_auditor(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            with self.assertRaisesRegex(RuntimeError,'bytes missing'):r.investigator({},True)

    def test_runtime_excludes_human_controls_papers_and_tests(self):
        paths=build.closure()
        self.assertIn('echo_arc/s6b21_search.py',paths)
        self.assertNotIn('seed/s6b20_capacity.py',paths)
        self.assertFalse(any(p.startswith(('docs/','tests/')) or p.endswith('.pdf') for p in paths))

    def test_builder_does_not_launch_before_b20_closure(self):
        with patch.object(build,'check_intent',return_value={}),patch.object(build,'b20_gate',return_value=None),patch.object(build.subprocess,'run') as process:
            self.assertFalse(build.launch());process.assert_not_called()

    def test_micro_reconstructs_inputs_and_freezes_first_passer(self):
        policy,rows,*_=fixture();base=dict(rows=rows,levels=2)
        seedfixture=dict(policy=policy,history=[],screen_trace_sha256=r.sha(rows))
        def req(data):
            obj=json.loads(data)
            return dict(id=obj['index']+1,type='WAIT',prior=len(obj['own_history']))
        def evaluate(ns,label,request,*args):
            passed=request['id']==2
            return dict(id=request['id'],base_sha256=r.sha(policy),levels=4 if passed else 2,
                        A=dict(gain=2 if passed else 0,loss_indices=[]),candidate={'accepted':True},
                        verdict='A_ONLY_PASS' if passed else 'V3')
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'),patch.object(r,'CELLS',[('balanced-7','balanced',7)]),patch.object(r,'integrity',return_value={}),patch.object(r,'reproduced',return_value=base),patch.object(r,'measure',return_value=base),patch.object(r.timeline,'legacy_rows',side_effect=lambda x:x),patch.object(r.search,'from_bytes',side_effect=req),patch.object(r,'evaluate',side_effect=evaluate),patch.object(r,'journal'),patch.object(r,'status'):
            r.atomic(Path(d)/'input/baseline.json',seedfixture)
            r.atomic(Path(d)/'micro-balanced-7/measurements/baseline.json',base)
            original=r.micro();audited=r.micro(True)
            self.assertEqual(len(original['cells']),2)
            self.assertEqual(original['winners']['balanced-7']['slot'],2)
            self.assertEqual(audited['micro_sha256'],r.sha(original))
            receipt=r.read(Path(d)/'steps/balanced-7/001.json')
            self.assertEqual(receipt['request']['prior'],1)
            receipt['event']['levels']=999;r.atomic(Path(d)/'steps/balanced-7/001.json',receipt)
            with self.assertRaisesRegex(RuntimeError,'independent event'):r.micro(True)


if __name__=='__main__':unittest.main()
