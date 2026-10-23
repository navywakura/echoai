import importlib
import json
from pathlib import Path
import tempfile
import unittest


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((Path(__file__).resolve().parents[1] / 'echo58/crece/api.py').exists(), 'API client missing')
        self.api = importlib.import_module('echoai.echo58.crece.api')

    def test_invalid_credentials_do_not_reserve_http_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=root/'key';key.write_text('')
            reservations=[]
            with self.assertRaisesRegex(ValueError,'empty credential'):
                self.api.complete('model','prompt',root/'cache',key_path=key,
                                  before_call=lambda:reservations.append(1))
            self.assertEqual(reservations,[])

    def test_cache_identity_includes_model_and_contains_no_credential(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            key = folder / 'credential'
            key.write_text('synthetic-secret-for-test')
            calls = []
            def transport(request, timeout):
                calls.append(json.loads(request.data))
                self.assertNotIn('synthetic-secret-for-test', request.data.decode())
                return 200, {}, {'model': calls[-1]['model'], 'choices': [{'message': {'content': 'def piece(moment, v, c):\n    return ()\n'}}], 'usage': {}}
            a = self.api.complete('model-a', 'prompt', folder / 'cache', key_path=key, transport=transport)
            b = self.api.complete('model-a', 'prompt', folder / 'cache', key_path=key, transport=transport)
            c = self.api.complete('model-b', 'prompt', folder / 'cache', key_path=key, transport=transport)
            self.assertFalse(a['cached'])
            self.assertTrue(b['cached'])
            self.assertNotEqual(a['request_sha256'], c['request_sha256'])
            self.assertEqual(len(calls), 2)
            for p in (folder / 'cache').glob('*.json'):
                self.assertNotIn(key.read_text(), p.read_text())

    def test_transport_echo_of_key_is_redacted(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d) / 'credential'
            key.write_text('synthetic-secret-for-test')
            def transport(request, timeout):
                return 200, {}, {'choices': [{'message': {'content': key.read_text()}}]}
            got = self.api.complete('model', 'prompt', Path(d) / 'cache', key_path=key, transport=transport)
            self.assertEqual(got['content'], '[REDACTED]')
            self.assertNotIn(key.read_text(), json.dumps(got))

    def test_malformed_success_still_has_failed_attempt_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d) / 'credential'
            key.write_text('synthetic-secret-for-test')
            def transport(request, timeout):
                return 200, {}, {'choices': [{'message': None}]}
            got = self.api.complete('model', 'prompt', Path(d) / 'cache', key_path=key, transport=transport)
            self.assertEqual(got['error_type'], 'MalformedResponse')
            self.assertEqual(got['content'], '')
            self.assertEqual(len(list((Path(d) / 'cache').glob('*-failed-*.json'))), 1)

    def test_provider_selects_endpoint_and_cache_identity_without_mixing_keys(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); key=root/'key'; key.write_text('synthetic-groq-key')
            seen=[]
            def transport(request, timeout):
                seen.append((request.full_url,json.loads(request.data),dict(request.header_items())))
                return 200,{}, {'choices':[{'message':{'content':'1'},'finish_reason':'stop'}]}
            google=self.api.complete('model','prompt',root/'cache',key_path=key,transport=transport)
            groq=self.api.complete('model','prompt',root/'cache',key_path=key,transport=transport,
                                   provider='groq',max_tokens=2048,reasoning_effort='low')
            self.assertNotEqual(google['request_sha256'],groq['request_sha256'])
            self.assertEqual(seen[1][0],'https://api.groq.com/openai/v1/chat/completions')
            self.assertEqual(seen[1][1]['max_completion_tokens'],2048)
            self.assertEqual(seen[1][1]['reasoning_effort'],'low')
            self.assertNotIn('max_tokens',seen[1][1])
            self.assertIn('User-agent',seen[1][2])

    def test_daily_quota_details_survive_list_error_envelope(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=root/'key';key.write_text('synthetic-secret-for-test')
            def transport(request,timeout):
                return 429,{},[{'error':{'status':'RESOURCE_EXHAUSTED','details':[
                    {'violations':[{'quotaId':'DailyFree','quotaValue':'20'}]}, {'retryDelay':'8107s'}]}}]
            got=self.api.complete('model','prompt',root/'cache',key_path=key,transport=transport)
            self.assertEqual(got['provider_errors'][0]['violations'][0]['quotaValue'],'20')
            self.assertEqual(got['provider_errors'][0]['retry_delay'],'8107s')


if __name__ == '__main__':
    unittest.main()
