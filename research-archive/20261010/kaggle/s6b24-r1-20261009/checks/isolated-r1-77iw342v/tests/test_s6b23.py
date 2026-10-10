import copy
from concurrent.futures import Future
import gzip
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from echo_arc import s6b23_search as s, s6b22_search as old, precise_patch
from seed import s6b23 as r, s6b23_model as model, s6b23_build as build
from seed.s6b23_report import report


def fixture():
    policy=r.engine.strategy()
    features={k:lo for k,(lo,hi) in precise_patch.FEATURES.items()}
    features.update(reset_known=1,level=7,world_events=32)
    reads=[dict(features=features,count=1,value=40,parameter='HOLD')]
    rows=[dict(origin='DEVELOPMENT_A',levels_completed=1,score=2.0,actions_per_level=[5],
               diagnostics=dict(consumers=copy.deepcopy(reads))) for _ in range(2)]
    proposal={'patches':[{'when':{'reset_known':['eq',1]},'set':{'HOLD':4}}]}
    event=dict(id=1,target_id=None,base_sha256=r.sha(policy),proposal=proposal,verdict='V3',
               schedule=dict(phase='global',global_index=0),actions_per_level=[[4],[6]],
               development=dict(origin='DEVELOPMENT_A',consumer_parameter='HOLD',
                    candidate_consumers=[[dict(features=features,count=1,value=4)] for _ in rows],
                    case_effects=[dict(case_index=0,level_delta=4,score_delta=1.0),
                                  dict(case_index=1,level_delta=0,score_delta=-0.4)]))
    return policy,dict(rows=rows),event


def descendant(parent,req,gain=4,loss=-0.2):
    event=copy.deepcopy(parent)
    event.update(id=req['id'],target_id=req['target_id'],proposal=req['proposal'],schedule=req['schedule'])
    event['development']['case_effects'][0]['level_delta']=gain
    event['development']['case_effects'][1]['score_delta']=loss
    return event


class SearchTests(unittest.TestCase):
    def setUp(self):self.policy,self.base,self.parent=fixture()

    def test_original_controls_unchanged(self):
        for kind in ('R22','M22'):
            obj=dict(policy=self.policy,base=self.base,own_history=[self.parent],kind=kind,index=1,seed=9)
            with patch.object(old,'base_pool',return_value=(({'reset_known':['eq',1]},),{})):
                self.assertEqual(s.from_bytes(json.dumps(obj)),old.from_bytes(json.dumps(obj)))

    def test_safe_plus_one_is_investigated_but_not_accepted(self):
        self.parent['development']['case_effects'][0]['level_delta']=1
        self.parent['development']['case_effects'][1]['score_delta']=0
        self.assertEqual(s.parents([self.parent]),[self.parent])
        req=s.adaptive(1,9,self.policy,self.base,[self.parent])
        self.assertEqual(req['schedule']['phase'],'repair')
        self.assertFalse(r.passes(dict(gain=1,loss_indices=[])))

    def test_best_descendant_selected_instead_of_mandatory_sibling(self):
        first=s.adaptive(1,9,self.policy,self.base,[self.parent])
        child=descendant(self.parent,first,gain=4,loss=0)
        req=s.adaptive(2,9,self.policy,self.base,[self.parent,child])
        self.assertEqual(req['target_id'],2)
        self.assertEqual(req['proposal']['patches'][0]['set'],{'HOLD':4})

    def test_failed_child_does_not_inherit_gain(self):
        req=s.adaptive(1,9,self.policy,self.base,[self.parent])
        child=descendant(self.parent,req,gain=0,loss=0)
        self.assertNotIn(child,s.parents([self.parent,child]))
        self.assertIsNone(req['predicted_gain'])

    def test_repairs_bounded_and_global_slots_preserved(self):
        history=[]
        with patch.object(old,'base_pool',return_value=(({'reset_known':['eq',1]},),{})):
            for index in range(18):
                req=s.adaptive(index,23,self.policy,self.base,history)
                history.append(descendant(self.parent,req))
        self.assertLessEqual(sum(e['schedule']['phase']=='repair' for e in history),8)
        self.assertGreaterEqual(sum(e['schedule']['phase']=='global' for e in history),10)
        for e in history:
            if e['schedule']['phase']=='repair':
                self.assertEqual(e['proposal']['patches'][0]['set'],history[e['target_id']-1]['proposal']['patches'][0]['set'])

    def test_inactive_filter_uses_baseline_consumptions(self):
        p=copy.deepcopy(self.parent['proposal']);p['patches'][0]['when']={'reset_known':['eq',0]}
        self.assertTrue(s.inactive(p,self.base['rows']))
        p['patches'][0]['when']={'reset_known':['eq',1]}
        self.assertFalse(s.inactive(p,self.base['rows']))

    def test_global_filter_bounded_and_costs_recorded(self):
        p=copy.deepcopy(self.parent['proposal']);p['patches'][0]['when']={'reset_known':['eq',0]}
        with patch.object(old,'global_candidate',return_value=(p,{'distribution':'general'})) as sampler:
            req=s.adaptive(0,9,self.policy,self.base,[])
        self.assertEqual(sampler.call_count,64)
        self.assertTrue(req['schedule']['exhausted']);self.assertEqual(len(req['schedule']['rejected']),64)

    def test_protected_foreign_and_partial_evidence_rejected(self):
        for kind in ('M23','N7','N14'):
            obj=dict(policy=self.policy,base=self.base,own_history=[self.parent],kind=kind,index=1,seed=9)
            obj=copy.deepcopy(obj);obj['own_history'][0]['development']['origin']='PROTECTED_B'
            with self.assertRaises(ValueError):s.from_bytes(json.dumps(obj))
        self.parent['development']['candidate_consumers'].pop()
        with self.assertRaises(ValueError):s.adaptive(1,9,self.policy,self.base,[self.parent])

    def test_researcher_surface_and_no_filesystem(self):
        obj=dict(policy=self.policy,base=self.base,own_history=[],kind='M23',index=0,seed=9)
        with self.assertRaisesRegex(ValueError,'surface'):s.from_bytes(json.dumps(dict(obj,winner={})))
        with patch('builtins.open',side_effect=AssertionError),patch('pathlib.Path.open',side_effect=AssertionError),patch.object(old,'base_pool',return_value=(({'reset_known':['eq',1]},),{})):
            self.assertIn('proposal',s.from_bytes(json.dumps(obj)))

    def test_both_models_receive_same_prompt_and_preserve_losses(self):
        a=s.model_request('N7',1,9,self.policy,self.base,[self.parent])
        b=s.model_request('N14',1,9,self.policy,self.base,[self.parent])
        self.assertEqual(a['prompt'],b['prompt'])
        payload=json.loads(a['prompt']);self.assertEqual(len(payload['history']),1)
        self.assertEqual(payload['history'][0][5][1][2],'-0.4')
        self.assertEqual(payload['history'][0][5][1][3],1)

    def test_numeric_context_extremes(self):
        reads=[dict(features={'world_events':v},count=1,value=4) for v in [104,89,14]]
        shown=s.read_summary(reads,2)
        self.assertEqual([x['features']['world_events'] for x in shown['reads']],[14,104])
        self.assertEqual(shown['omitted'],1)

    def test_rounding_never_hides_individual_loss_or_changes_judge(self):
        self.parent['development']['case_effects'][1]['score_delta']=-1.00001e-10
        req=s.model_request('N7',1,9,self.policy,self.base,[self.parent])
        payload=json.loads(req['prompt'])
        self.assertEqual(payload['history'][0][5][1][3],1)
        self.assertEqual(payload['history'][0][5][1][2],'-1e-10')
        self.assertEqual(self.parent['development']['case_effects'][1]['score_delta'],-1.00001e-10)

    def test_context_dictionary_preserves_feature_values(self):
        req=s.model_request('N7',0,9,self.policy,self.base,[]);p=json.loads(req['prompt'])
        item=p['base'][0][4][3][0]
        vector=dict(zip(p['context_columns'],p['contexts'][item[0]]))
        self.assertEqual(vector,self.base['rows'][0]['diagnostics']['consumers'][0]['features'])

    def test_cycle_or_future_parent_rejected(self):
        self.parent['target_id']=1
        with self.assertRaises(ValueError):s.root_id(self.parent,[self.parent])


class ModelTests(unittest.TestCase):
    def protocol_tokenizer(self, spec, path, *, add_special=False):
        text = Path(path).read_text()
        if text == '<|im_start|>': return [101]
        if text == '<|im_end|>': return [102]
        return [101,1,102,101,2,102,101,3]

    def test_effective_chatml_checks_special_tokens_and_default_bos(self):
        with patch.object(model,'tokenize',side_effect=self.protocol_tokenizer) as tokenizer:
            receipt=model.prompt_protocol({})
        self.assertFalse(receipt['embedded_template_used'])
        self.assertTrue(receipt['automatic_special_tokens_match'])
        self.assertEqual(tokenizer.call_count,4)
        self.assertEqual(tokenizer.call_args.kwargs,{'add_special':True})

    def test_effective_chatml_rejects_ordinary_text_markers(self):
        with patch.object(model,'tokenize',return_value=[1,2]):
            with self.assertRaisesRegex(ValueError,'special token'):model.prompt_protocol({})

    def test_effective_chatml_rejects_colliding_markers(self):
        with patch.object(model,'tokenize',return_value=[1]):
            with self.assertRaisesRegex(ValueError,'collide'):model.prompt_protocol({})

    def test_effective_chatml_rejects_implicit_bos(self):
        def tokens(spec,path,*,add_special=False):
            ids=self.protocol_tokenizer(spec,path)
            return [999]+ids if add_special else ids
        with patch.object(model,'tokenize',side_effect=tokens):
            with self.assertRaisesRegex(ValueError,'special-token handling'):model.prompt_protocol({})

    def test_pair_uses_effective_protocol_and_preserves_metadata_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'cli').write_text('binary');registry={};metadata={}
            with patch.object(model,'tokenize',side_effect=self.protocol_tokenizer):
                for arm,size in [('N7',7),('N14',14)]:
                    path=root/arm;path.write_text(arm)
                    info=dict(parameters=size*10**9,architecture='qwen2',file_type=15,
                              template_sha256=model.sha(arm))
                    metadata[str(path)]=info
                    spec=dict(family='Qwen2.5-Coder-Instruct',quantization='Q4_K_M',
                        repo=f'Qwen/Qwen2.5-Coder-{size}B-Instruct-GGUF',revision='a'*40,
                        backend='cpu',gpu_layers=0,tensor_split='1',gguf=copy.deepcopy(info))
                    for key,p in [('model',path),('cli',root/'cli'),('tokenizer',root/'cli')]:
                        spec[key]=str(p);spec[key+'_sha256']=model.digest_file(p)
                    spec['prompt_protocol']=model.prompt_protocol(spec);registry[arm]=spec
                with patch.object(model,'gguf_info',side_effect=lambda p:metadata[str(p)]):
                    self.assertTrue(model.verify_pair(registry))
                    registry['N14']['gguf']['template_sha256']='tampered'
                    with self.assertRaisesRegex(ValueError,'metadata changed'):model.verify_pair(registry)
                    registry['N14']['gguf']=copy.deepcopy(metadata[registry['N14']['model']])
                    registry['N14']['prompt_protocol']['probe_tokens'].append(99)
                    with self.assertRaisesRegex(ValueError,'protocol changed'):model.verify_pair(registry)

    def test_cli_receives_explicit_prompt_without_automatic_chat(self):
        cmd=model.command(dict(cli='/cli',model='/model',backend='cpu'),'/prompt',1)
        self.assertIn('--no-conversation',cmd)
        self.assertIn('--no-escape',cmd)
        self.assertEqual(cmd[-2:],['-f','/prompt'])

    def test_strict_json_duplicate_keys_and_outside_language_rejected(self):
        for text in ('{"patches":[],"patches":[]}', 'prefix {"patches":[]}',
                     '{"patches":[{"when":{"seed":["eq",1]},"set":{"HOLD":4}}]}'):
            with self.assertRaises(ValueError):model.strict_answer(text)
        p=fixture()[2]['proposal'];self.assertEqual(model.strict_answer(json.dumps(p)),p)

    def test_gguf_size_comes_from_tensors_not_filename(self):
        def st(value):
            b=value.encode();return struct.pack('<Q',len(b))+b
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fake-14b.gguf'
            p.write_bytes(b'GGUF'+struct.pack('<IQQ',3,1,2)+st('general.architecture')+struct.pack('<I',8)+st('qwen2')+
                          st('general.file_type')+struct.pack('<II',4,15)+st('weight')+struct.pack('<IQIQ',1,1234,0,0))
            self.assertEqual(model.gguf_info(p)['parameters'],1234)

    def test_truncated_gguf_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad';p.write_bytes(b'GGUF')
            with self.assertRaises(ValueError):model.gguf_info(p)

    def test_no_implicit_model_fallback(self):
        with self.assertRaises(ValueError):model.verify_pair({'N7':{}})

    def transport(self,root,response=None,timeout=False):
        spec=dict(cli='/cli',model='/model',backend='cpu',gpu_layers=0,tensor_split='1')
        registry={'N7':spec,'N14':dict(spec)};req=dict(prompt='experiment')
        def run(cmd,**kw):
            if timeout:raise subprocess.TimeoutExpired(cmd,1)
            kw['stdout'].write(response or json.dumps(fixture()[2]['proposal']))
            return subprocess.CompletedProcess(cmd,0)
        with patch.object(model,'tokenize',return_value=[1,2]),patch.object(model.subprocess,'run',side_effect=run):
            return model.propose(root,registry,'N7',0,req,9,'profile')

    def test_call_resume_does_not_generate_again(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);first=self.transport(root)
            with patch.object(model.subprocess,'run',side_effect=AssertionError('repeat')):
                again=model.propose(root,{},'N7',0,dict(prompt='experiment'),9,'profile')
            self.assertEqual(first,again);self.assertEqual(r.read(root/'model-budget.json')['calls'],['N7/000'])

    def test_invalid_generation_and_timeout_consume_budget(self):
        for timeout,response in ((False,'bad JSON'),(True,None)):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);result=self.transport(root,response,timeout)
                self.assertIsNone(result['proposal']);self.assertEqual(result['usage']['model_calls'],1)
                self.assertEqual(len(r.read(root/'model-budget.json')['calls']),1)

    def test_prompt_overflow_stops_before_inference(self):
        with tempfile.TemporaryDirectory() as d,patch.object(model,'tokenize',return_value=[1]*8193),patch.object(model.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'context'):
                model.propose(Path(d),{'N7':{},'N14':{}},'N7',0,dict(prompt='x'),9,'p')
            run.assert_not_called();self.assertFalse((Path(d)/'model-budget.json').exists())

    def test_interrupted_call_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d,patch.object(model,'tokenize',return_value=[1]),patch.object(model.subprocess,'run') as run:
            root=Path(d);r.atomic(root/'model-budget.json',dict(calls=['N7/000']))
            with self.assertRaisesRegex(RuntimeError,'interrupted'):
                model.propose(root,{'N7':{},'N14':{}},'N7',0,dict(prompt='x'),9,'p')
            run.assert_not_called()

    def test_saved_answer_tampering_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.transport(root)
            (root/'calls/N7/000/stdout.txt').write_text('{}')
            with self.assertRaisesRegex(RuntimeError,'artifact'):
                model.load(root/'calls/N7/000',dict(prompt='experiment'),'N7',9,'profile')

    def test_usage_tampering_detected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.transport(root);p=root/'calls/N7/000/result.json'
            value=r.read(p);value['usage']['model_calls']=0;r.atomic(p,value)
            with self.assertRaisesRegex(RuntimeError,'usage'):
                model.load(p.parent,dict(prompt='experiment'),'N7',9,'profile')


class RunnerTests(unittest.TestCase):
    def test_five_arms_fixed_budgets_and_protected_split(self):
        self.assertEqual(len(r.CELLS),5);self.assertEqual(len(r.A),14)
        self.assertEqual(r.MAX_GAMES,8310);self.assertEqual(len(r.V_NEW),80)
        self.assertFalse(set(r.DEVELOPMENT)&set(r.V_NEW));self.assertFalse(r.config()['exam_allowed'])
        self.assertEqual([r.allocation('s-'+k+'-audit') for k in s.KINDS],['S-'+k for k in s.KINDS])

    def test_individual_loss_and_plus_one_still_rejected(self):
        self.assertFalse(r.passes(dict(gain=8,loss_indices=[3])))
        self.assertFalse(r.passes(dict(gain=1,loss_indices=[])))
        self.assertTrue(r.passes(dict(gain=0,loss_indices=[]),True))

    def test_no_protected_observation(self):
        with self.assertRaisesRegex(ValueError,'protected'):
            r.play_one(({},r.V_NEW[0],'viewer','unused',{}))

    def test_spawn_worker_receives_explicit_execution_directory(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'):
            task=r.reserve_tasks([dict(task_id='one')],'s-M23','baseline')[0]
            self.assertEqual(task['execution_root'],d)
            # Model a freshly imported worker with the wrong default globals.
            with patch.object(r,'ROOT',Path('/tmp/wrong-default')),patch.object(r,'INPUT',Path('/tmp/wrong-input')),patch.object(r,'reuse',side_effect=lambda *args:(r.ROOT,r.INPUT)):
                self.assertEqual(r.play_one(({},r.A[0],None,str(Path(d)/'cache.json'),task)),(Path(d),Path(d)/'input'))

    def test_worker_rejects_cache_outside_its_root(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'):
            task=r.reserve_tasks([dict(task_id='one')],'s-M23','baseline')[0]
            with self.assertRaisesRegex(ValueError,'outside'):
                r.play_one(({},r.A[0],None,'/tmp/unrelated-cache',task))

    def test_undeclared_partition_or_namespace_rejected(self):
        with self.assertRaises(ValueError):r.partition_name(r.A[:1])
        with self.assertRaises(ValueError):r.allocation('exam')

    def test_replay_mismatch_blocks(self):
        with patch.object(r,'measure',side_effect=[{'score':1},{'score':2}]),patch.object(r.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'replay'):r.triple('s-M23','x',{},r.A)
            run.assert_not_called()

    def test_protection_closed_until_finalists_and_qualification(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            with self.assertRaisesRegex(ValueError,'closed'):r.check_permit({},r.V_NEW)
            with self.assertRaises(FileNotFoundError):r.permit(['M23'])

    def test_per_arm_budgets_cannot_borrow_and_reserve_once(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)):
            tasks=[dict(task_id=str(i)) for i in range(798)]
            self.assertEqual(r.reserve_tasks(tasks,'s-M23','x'),r.reserve_tasks(tasks,'s-M23','x'))
            with self.assertRaisesRegex(RuntimeError,'allocation'):r.reserve_tasks([dict(task_id='overflow')],'s-M23','x')
            self.assertEqual(r.read(Path(d)/'budget.json')['scheduled_games'],798)

    def test_resume_replay_audit_isolated_and_accounted(self):
        class Pool:
            def __init__(self,**kw):pass
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def submit(self,fn,job):
                future=Future()
                try:future.set_result(fn(job))
                except Exception as exc:future.set_exception(exc)
                return future
        def fake(job):
            policy,spec,directory,dest,task=job
            row=dict(version=spec[0],seed=spec[1],rep=spec[2],budget=spec[3],levels_completed=1,score=1)
            r.atomic(r.ROOT/'executions/started'/f"{task['job_id']:06d}.json",{})
            r.atomic(Path(dest),dict(key=task['key'],record=row,digest=r.sha(row),job_id=task['job_id']))
            r.atomic(r.ROOT/'executions/completed'/f"{task['job_id']:06d}.json",{})
            return row,{}
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'integrity',return_value={}),patch.object(r.old,'ProcessPoolExecutor',Pool),patch.object(r,'play_one',side_effect=fake) as worker,patch.object(r,'status'):
            first=r.measure('s-M23','baseline',{},r.A)
            self.assertEqual(first,r.measure('s-M23','baseline',{},r.A));self.assertEqual(worker.call_count,14)
            self.assertEqual(first,r.measure('s-M23','baseline/replay',{},r.A,True))
            self.assertEqual(first,r.measure('s-M23-audit','baseline',{},r.A));self.assertEqual(worker.call_count,42)
            self.assertEqual(r.read(Path(d)/'budget.json')['scheduled_games'],42)

    def test_started_game_blocks_retry(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'integrity',return_value={}):
            key=r.sha(dict(profile=r.sha({}),namespace='s-M23',policy={},spec=r.A[0],observed=True))
            task=dict(task_id=r.sha(['s-M23','main',key]),key=key,spec=r.A[0],policy_sha256=r.sha({}),cache='x',journal=None)
            job=r.reserve_tasks([task],'s-M23','x')[0]
            r.atomic(r.ROOT/'executions/started'/f"{job['job_id']:06d}.json",{})
            with self.assertRaisesRegex(RuntimeError,'interrupted'):r.measure('s-M23','baseline',{},r.A)

    def test_input_tamper_is_detected(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r.search,'from_bytes',return_value={}):
            _,h=r.persist_input({'x':1});(Path(d)/'investigator-inputs'/(h+'.json.gz')).write_bytes(gzip.compress(b'changed'))
            with self.assertRaises(RuntimeError):r.persist_input({'x':1})

    def test_runtime_excludes_known_controls_and_forensics(self):
        files=build.closure()
        self.assertIn('echo_arc/s6b23_search.py',files)
        self.assertNotIn('seed/s6b20_capacity.py',files)
        self.assertFalse(any('forensics' in x or 'probe' in x for x in files))

    def test_instrument_failure_never_scientific_failure(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'follow',side_effect=RuntimeError('broken')),patch.object(r,'status') as status:
            with self.assertRaises(RuntimeError):r.main(['follow'])
            self.assertEqual(status.call_args.args[0],'INSTRUMENT_BLOCKED')

    def test_no_winners_closes_without_opening_broad_or_protection(self):
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'),patch.object(r,'integrity',return_value={}),patch.object(r.model,'verify_pair'),patch.object(r,'micro',return_value=dict(winners={},cells=[])),patch.object(r,'validate_finalist') as evaluate,patch.object(r,'permit') as gate,patch('seed.s6b23_review.review',return_value=dict(completed_games=42,model_calls=0)),patch.object(r,'status'):
            r.atomic(r.INPUT/'models.json',{})
            result=r.follow();evaluate.assert_not_called();gate.assert_not_called()
            self.assertFalse(result['s6_green']);self.assertFalse(result['exam_opened'])
            self.assertTrue((Path(d)/'finalists.json').exists())

    def test_finalists_freeze_before_broad_and_only_passers_get_retention(self):
        winners={k:dict(policy={'name':k},slot=1,policy_sha256=r.sha({'name':k})) for k in ('R22','M23')}
        calls=[]
        def evaluate(arm,policy,specs,retention=False):
            self.assertTrue((r.ROOT/'finalists.json').exists())
            calls.append((arm,retention));return dict(passed=arm=='M23')
        with tempfile.TemporaryDirectory() as d,patch.object(r,'ROOT',Path(d)),patch.object(r,'INPUT',Path(d)/'input'),patch.object(r,'integrity',return_value={}),patch.object(r.model,'verify_pair'),patch.object(r,'micro',return_value=dict(winners=winners,cells=[])),patch.object(r,'validate_finalist',side_effect=evaluate),patch.object(r,'permit') as gate,patch('seed.s6b23_review.review',return_value=dict(completed_games=42,model_calls=0)),patch.object(r,'status'):
            r.atomic(r.INPUT/'models.json',{});result=r.follow()
            self.assertEqual(calls,[('R22',False),('M23',False),('M23',True)])
            gate.assert_called_once_with(['M23']);self.assertEqual(result['transfer']['R22']['retention'],'NOT_RUN')


class ReportingTests(unittest.TestCase):
    def test_orphan_receipt_does_not_count_as_experiment_progress(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);r.atomic(root/'executions/completed/000000.json',dict(task_id='other'))
            value=report(root)
            self.assertEqual(value['completed_games'],0)
            self.assertEqual(value['orphan_completion_receipts'],['000000.json'])

    def test_completion_must_match_reserved_task(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);r.atomic(root/'budget.json',dict(scheduled_games=1,jobs=[dict(job_id=0,task_id='same')]))
            r.atomic(root/'executions/completed/000000.json',dict(task_id='same'))
            value=report(root)
            self.assertEqual(value['completed_games'],1);self.assertFalse(value['orphan_completion_receipts'])


if __name__=='__main__':unittest.main()
