import importlib
from pathlib import Path
import tempfile
import unittest


class GenerationsTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'echo58/crece/generations.py'
        self.assertTrue(path.exists(), 'generation runner missing')
        self.g = importlib.import_module('echoai.echo58.crece.generations')

    def test_prompt_bytes_survive_persisted_failure_fiches(self):
        import json
        fiche = {'episodes': [{'signals': ['idle'], 'result': {'success': 0, 'harm': 0},
                                'tail': [{'step': 3, 'pos': (1, 2)}]}]}
        previous = [{'source': 'piece', 'mechanical': {'green': False, 'stage': 'AST'}}]
        restored = json.loads(json.dumps(fiche, sort_keys=True))
        restored_previous = json.loads(json.dumps(previous, sort_keys=True))
        self.assertEqual(self.g.prompt_for(fiche, previous),
                         self.g.prompt_for(restored, restored_previous))

    def test_changed_prompt_or_model_rejected_before_resume_call(self):
        from echoai.echo58.crece.pacing import QuotaDeferred
        calls = []
        def deferred(model, prompt, *args, **kwargs):
            kwargs['before_call']()
            calls.append((model, prompt))
            return {'status': 429, 'content': '', 'deferred_until': 9999999999}
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            with self.assertRaises(QuotaDeferred):
                self.g.bounded_call(folder, 'model', 'prompt', call=deferred, pause=lambda n: None)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            for model, prompt in (('model', 'changed prompt'), ('other-model', 'prompt')):
                with self.assertRaisesRegex(ValueError, 'immutable artifact differs'):
                    self.g.bounded_call(folder, model, prompt, call=deferred, pause=lambda n: None)
            self.assertEqual(calls, [('model', 'prompt')])
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_attempt_history_without_request_identity_cannot_resume(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder/'attempt-0.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'request identity missing'):
                self.g.bounded_call(folder, 'model', 'prompt',
                    call=lambda *a, **k: self.fail('no network before identity check'), pause=lambda n: None)

    def test_failed_calls_are_not_repeated_after_resume(self):
        calls = []
        def fail(*args, **kwargs):
            kwargs['before_call']()
            calls.append(1)
            return {'status':503, 'content':'', 'cached':False}
        with tempfile.TemporaryDirectory() as d:
            for _ in range(2):
                self.g.bounded_call(Path(d), 'model', 'prompt', call=fail, pause=lambda n: None)
            self.assertEqual(len(calls), 3)

    def test_quota_wait_does_not_consume_unsent_attempts(self):
        from echoai.echo58.crece import pacing as p
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            def deferred(*args,**kwargs):
                raise p.QuotaDeferred(9999999999)
            for _ in range(4):
                with self.assertRaises(p.QuotaDeferred):
                    self.g.bounded_call(folder,'model','prompt',call=deferred,pause=lambda n:None)
            self.assertEqual(list(folder.glob('attempt-*.json')),[])

    def test_last_quota_response_is_saved_and_suspends(self):
        from echoai.echo58.crece import pacing as p
        import json
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            self.g.save_new(folder/'request.json', {'model':'model', 'prompt':'prompt',
                'prompt_sha256':self.g.hashlib.sha256(b'prompt').hexdigest()})
            for i in range(2):
                (folder/f'attempt-{i}-result.json').write_text(json.dumps({'status':503,'content':''}))
            def quota(*args,**kwargs):
                kwargs['before_call']()
                return {'status':429,'content':'','deferred_until':9999999999}
            with self.assertRaises(p.QuotaDeferred):
                self.g.bounded_call(folder,'model','prompt',call=quota,pause=lambda n:None)
            self.assertEqual(json.loads((folder/'attempt-2-result.json').read_text())['status'],429)

    def test_pending_attempts_count_as_consumed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.g.save_new(folder/'request.json', {'model':'model', 'prompt':'prompt',
                'prompt_sha256':self.g.hashlib.sha256(b'prompt').hexdigest()})
            for i in range(3):
                (folder/f'attempt-{i}.json').write_text('{}')
            def forbidden(*args, **kwargs):
                self.fail('pending attempt was repeated')
            result = self.g.bounded_call(folder, 'model', 'prompt', call=forbidden, pause=lambda n: None)
            self.assertEqual(result['status'], 0)

    def test_development_curve_requires_consecutive_gains(self):
        self.assertTrue(self.g.curve_green([10,9,8,8,8,8]))
        self.assertFalse(self.g.curve_green([10,9,9,8,8,7]))
        self.assertFalse(self.g.curve_green([10,10,10,10,10,10]))

    def test_random_control_samples_occurrences_including_duplicates(self):
        trials = [{'generation':g,'accepted':g == 2,'spec':{'sha256':'a','name':'a'}} for g in (1,2,3)]
        seen = set()
        for seed in range(100):
            selection = self.g.random_selection(trials, seed)
            self.assertEqual(selection['pool'], [1,2,3])
            self.assertEqual(len(selection['selected_generations']), 1)
            seen.update(selection['selected_generations'])
        self.assertEqual(seen, {1,2,3})
        first = self.g.random_instance(trials[0])
        second = self.g.random_instance(trials[1])
        self.assertNotEqual(first['name'], second['name'])
        self.assertEqual(first['sha256'], second['sha256'])

    def test_rejected_code_and_measured_reason_reach_model_without_family_or_seed(self):
        import json
        trial={'source':'def piece(moment, v, c):\n    return ()\n','source_sha256':'a'*64,
               'accepted':False,'mechanical':{'green':True,'states':200},'seeds':[123456],
               'base':{'private-family':{'success':2,'harm':0,'plug_errors':0}},
               'candidate':{'private-family':{'success':2,'harm':0,'plug_errors':0}}}
        with tempfile.TemporaryDirectory() as d:
            directory=Path(d)
            (directory/'crece').mkdir()
            (directory/'crece/trial-1.json').write_text(json.dumps(trial))
            feedback=self.g.rejected_feedback(directory,'crece',2)
            self.assertEqual(feedback[0]['source'],trial['source'])
            self.assertIn('no_global_success_gain',feedback[0]['reasons'])
            self.assertNotIn('private-family',json.dumps(feedback))
            self.assertNotIn('123456',json.dumps(feedback))
            self.assertEqual(self.g.rejected_feedback(directory,'sin_fichas',2),[])

    def test_effect_window_uses_real_action_ordinals_and_symbolic_effects(self):
        from unittest.mock import patch
        from echoai.echo58.crece import runtime as R
        agent=self.g.TrainingAgent(source=None)
        agent.trace=[];agent.audit_effects=[];agent.plug_events=[];agent.steps_n=9999
        effects={R.DECIDE:R.BAN(7,R.PICK,R.HAND),R.DROP:R.DROP_AT((1,2)),
                 R.IDLE:R.GOTO((2,3)),R.OUTCOME:R.BAN_UNTIL_PROGRESS(7,R.PICK)}
        def dispatch(self,moment,*args):
            self.plug_events.append((self.steps_n,'piece',moment,effects[moment]))
        with patch.object(R.HAgent,'_dispatch',dispatch):
            for step in (9,10,29):
                agent.trace=[None]*(step-1)
                for hook in (R.DECIDE,R.DROP,R.IDLE):agent._dispatch(hook,None,None,None)
                agent.trace.append(None)
                agent._dispatch(R.OUTCOME,None,None,None)
        rows=self.g.recent_effects(agent)
        self.assertEqual([row['step'] for row in rows],[10]*4+[29]*4)
        self.assertEqual({r['hook'] for r in rows},{'DECIDE','DROP','IDLE','OUTCOME'})
        self.assertEqual(rows[0]['effect'],{'type':'BAN','id':7,'action':'PICK','scope':'HAND'})

    def test_complete_generation_wiring_with_synthetic_receipts_and_no_network(self):
        import json,re,hashlib
        from unittest.mock import patch
        from echoai.echo58.acumula.config import Config,ConfMemory
        prompts=[]
        noop='def piece(moment, v, c):\n    return ()\n'
        noop_sha=hashlib.sha256(noop.encode()).hexdigest()
        def call(model,prompt,cache,**kwargs):
            kwargs['before_call']();prompts.append(prompt)
            generation=int(re.search(r'generation=(\d+)',prompt).group(1))
            source=noop if generation==1 else f'def piece(moment, v, c):\n    return (NOTE({generation}),)\n'
            return {'status':200,'content':source,'cached':False,'request_sha256':'test-receipt'}
        def score(root,memory,specs,seeds):
            # Synthetic oracle for plumbing only; never reported as experiment data.
            successes=sum(s['sha256']!=noop_sha for s in specs)
            return {'private-fixture-family':{'success':successes,'episodes':12,'harm':0,'plug_errors':0}}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'f1-training.json').write_text('{"states":[]}')
            with patch('builtins.print'), patch.multiple(self.g,LAB=root,log=lambda *a,**k:None,
                                build_memory=lambda macro:ConfMemory(Config()),
                                training_fiches=lambda *a:{'fiches':[{'signals':['fixture_failure']}],'episodes':[]},
                                check=lambda *a:{'green':True,'states':200},score=score,paced_complete=call):
                report=self.g.one_job((str(root/'run'),'openai/gpt-oss-20b',1))
            self.assertEqual(len(prompts),15)
            second=[p for p in prompts if 'generation=2.' in p]
            self.assertEqual(len(second),3)
            for prompt in second:
                self.assertNotIn('private-fixture-family',prompt)
                if 'No failure observations' in prompt:
                    self.assertNotIn('no_global_success_gain',prompt)
                else:
                    self.assertIn('no_global_success_gain',prompt)
                    self.assertIn(noop.strip().replace('\n','\\n'),prompt)
            self.assertEqual(set(report['curves']),set(self.g.ARMS))
            self.assertEqual(len(report['random_selection']),4)

    def test_training_observer_preserves_actions_and_results(self):
        from echoai.echo58.crece.equiv import observed,digest
        from echoai.echo58.crece.runtime import HAgent
        from echoai.echo58.crece.pieces_b3 import PLUGS
        from echoai.echo58.acumula3 import bench as B3
        runs=[]
        for kind in (observed(HAgent),self.g.TrainingAgent):
            agent=kind(source=None,plugs=PLUGS)
            world=B3.W.make_world('BlockedUnlockPickup',7_000_010,'A2')
            try:result=agent.run(world,max_steps=80)
            finally:world.close()
            runs.append((digest(agent.trace),result))
        self.assertEqual(runs[0],runs[1])
        self.assertTrue(all(1<=e['step']<=len(agent.trace) for e in agent.audit_effects))

    def test_failure_fiche_uses_public_action_symbols_without_changing_trace(self):
        from copy import deepcopy
        from unittest.mock import Mock,patch
        from echoai.echo58.crece import runtime as R
        observation={'pos':(1,1),'hand':0,'dir':0,'reward':0,'terminated':False,
                     'truncated':True,'grid':((1,2),(3,4))}
        agent=Mock()
        agent.trace=[('D',('DROP',(1,0),7,9,0),'NOOP',observation),
                     ('P',('PICK',(0,1),3,0,0),'PICK',observation),
                     ('L',None,None,observation)]
        agent.picked={};agent.opened={};agent.progress=0;agent.audit_effects=[]
        agent.run.return_value={'success':0,'harm':0,'steps':3,'wasted':1,'signals':['blockdrop']}
        original=deepcopy(agent.trace)
        memory=Mock();world=Mock()
        with patch.object(self.g,'TrainingAgent',return_value=agent), \
             patch.object(self.g,'FAMILIES',('fixture',)), \
             patch.object(self.g.B3.W,'make_world',return_value=world):
            data=self.g.training_fiches(memory,(),(123,))
        intent=data['fiches'][0]['tail'][0]['intent']
        self.assertEqual(intent,('DROP_ACTION',(1,0),7,9,0))
        self.assertEqual(data['fiches'][0]['tail'][1]['outcome'],'PICKED')
        self.assertEqual(data['fiches'][0]['tail'][2]['outcome'],'UNKNOWN')
        self.assertEqual(data['fiches'][0]['tail'][2]['intent'],())
        self.assertEqual(agent.trace,original)
        self.assertEqual(data['episodes'][0]['trace_sha256'],self.g.digest(original))
        effect=self.g.symbolic_effect(R.BAN_UNTIL_PROGRESS(7,R.DROP_ACTION))
        self.assertEqual(effect['action'],'DROP_ACTION')
        prompt=self.g.prompt_for({'episodes':data['fiches']})
        self.assertIn('DROP is a hook; DROP_ACTION is an action.',prompt)


if __name__ == '__main__':
    unittest.main()
