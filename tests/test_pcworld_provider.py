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
