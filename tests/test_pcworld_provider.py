"""Connector contract tests with local stubs; zero model calls or paid traffic."""
import time
import unittest
from unittest.mock import patch

from echoai.pcworld.provider import HTTPProvider,ProviderFailure
from echoai.pcworld.tasks import development_tasks

CONFIG={'endpoint':'http://127.0.0.1:8000/v1/chat/completions',
        'tokenize_endpoint':'http://127.0.0.1:8000/tokenize',
        'model':'test-model','revision':'fixed-test-revision','quantization':'none',
        'tokenizer':'test-tokenizer','max_output_tokens':2048,'timeout_seconds':5}

class ProviderContract(unittest.TestCase):
    def test_prompt_count_is_reserved_before_generation(self):
        provider=HTTPProvider(CONFIG);sent=[]
        def post(endpoint,payload,**kwargs):
            sent.append((endpoint,payload))
            if endpoint.endswith('/tokenize'): return {'count':500}
            return {'model':'test-model','usage':{'prompt_tokens':500,'completion_tokens':500,'total_tokens':1000},
                    'choices':[{'message':{'content':'{"content":"pass"}'}}]}
        with patch.object(provider,'_post',side_effect=post):
            _,usage=provider.call('propose',development_tasks(1)[0],{},total_token_budget=1000)
        self.assertEqual(len(sent),2)
        self.assertEqual(sent[1][1]['max_tokens'],500)
        self.assertEqual(usage['tokens'],1000)
    def test_no_room_for_completion_refuses_generation(self):
        provider=HTTPProvider(CONFIG)
        with patch.object(provider,'_post',return_value={'count':1000}) as post:
            with self.assertRaises(ProviderFailure):
                provider.call('propose',development_tasks(1)[0],{},total_token_budget=1000)
        self.assertEqual(post.call_count,1)
    def test_deadline_bounds_inflight_call(self):
        provider=HTTPProvider(CONFIG)
        def slow(*args,**kwargs): time.sleep(.2);return {'count':50}
        start=time.monotonic()
        with patch.object(provider,'_post',side_effect=slow):
            with self.assertRaises(ProviderFailure):
                provider.call('propose',development_tasks(1)[0],{},total_token_budget=1000,
                              deadline=start+.03)
        self.assertLess(time.monotonic()-start,.17)
    def test_tokenizer_must_share_generation_origin(self):
        with self.assertRaises(ValueError):
            HTTPProvider({**CONFIG,'tokenize_endpoint':'https://unrelated.invalid/tokenize'})

class LlamaConnector(unittest.TestCase):
    def provider(self,**extra):
        return HTTPProvider({**CONFIG,'backend':'llama_cpp',
            'endpoint':'http://127.0.0.1:8000/completion',
            'template_endpoint':'http://127.0.0.1:8000/apply-template',
            'context_tokens':4096,'seed':73,'temperature_milli':200,**extra})
    def test_native_tokens_are_passed_without_retokenizing(self):
        provider=self.provider();sent=[]
        def post(endpoint,payload,**kwargs):
            sent.append((endpoint,payload))
            if endpoint.endswith('/apply-template'): return {'prompt':'templated'}
            if endpoint.endswith('/tokenize'): return {'tokens':[11,22,33]}
            return {'model':'test-model','tokens_evaluated':3,'tokens_predicted':9,
                    'truncated':False,'content':'{"content":"pass"}'}
        with patch.object(provider,'_post',side_effect=post):
            value,usage=provider.call('propose',development_tasks(1)[0],{},total_token_budget=100)
        self.assertEqual(value,{'content':'pass'})
        self.assertEqual(sent[-1][1]['prompt'],[11,22,33])
        self.assertEqual(sent[-1][1]['n_predict'],97)
        self.assertEqual(usage['tokens'],12)
        self.assertEqual(usage['tokenization_requests'],2)
    def test_context_overflow_prevents_inference(self):
        provider=self.provider(context_tokens=512)
        with patch.object(provider,'_post',side_effect=[{'prompt':'x'},{'tokens':[1]*512}]) as post:
            with self.assertRaises(ProviderFailure):
                provider.call('propose',development_tasks(1)[0],{},total_token_budget=1000)
        self.assertEqual(post.call_count,2)
    def test_template_origin_is_checked(self):
        with self.assertRaises(ValueError): self.provider(template_endpoint='https://elsewhere.invalid/apply-template')
    def test_native_usage_mismatch_is_charged(self):
        provider=self.provider()
        with patch.object(provider,'_post',side_effect=[{'prompt':'x'},{'tokens':[1,2]},
            {'model':'test-model','tokens_evaluated':3,'tokens_predicted':4,'truncated':False,'content':'{}'}]):
            with self.assertRaises(ProviderFailure) as caught:
                provider.call('propose',development_tasks(1)[0],{},total_token_budget=100)
        self.assertEqual(caught.exception.usage['tokens'],100)
        self.assertEqual(caught.exception.usage['provider_usage']['total_tokens'],7)
    def test_false_zero_usage_burns_reservation(self):
        for native in (True,False):
            provider=self.provider() if native else HTTPProvider(CONFIG)
            replies=([{'prompt':'x'},{'tokens':[1]*400},
                      {'model':'test-model','tokens_evaluated':0,'tokens_predicted':0,'truncated':False,'content':'{}'}]
                     if native else [{'count':400},{'model':'test-model','usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0},
                                                   'choices':[{'message':{'content':'{}'}}]}])
            with patch.object(provider,'_post',side_effect=replies):
                with self.assertRaises(ProviderFailure) as caught:
                    provider.call('propose',development_tasks(1)[0],{},total_token_budget=1000)
            self.assertEqual(caught.exception.usage['tokens'],1000)
    def test_critic_wire_schema_requires_direct_input_array(self):
        provider=self.provider();requests=[]
        def post(url,payload,**kw):
            requests.append(payload)
            if url.endswith('/apply-template'): return {'prompt':'x'}
            if url.endswith('/tokenize'): return {'tokens':[1]}
            return {'model':'test-model','tokens_evaluated':1,'tokens_predicted':3,'truncated':False,
                    'content':'{"abstention":"NO_COUNTEREXAMPLE_FOUND"}'}
        with patch.object(provider,'_post',side_effect=post):
            provider.call('critic',development_tasks(1)[0],{},total_token_budget=100)
        domain=requests[-1]['json_schema']['oneOf'][1]['properties']['input']
        self.assertEqual(domain['type'],'array')
        self.assertEqual(domain['items']['type'],'integer')
        self.assertEqual(domain['maxItems'],64)
