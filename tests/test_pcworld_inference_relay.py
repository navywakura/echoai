"""Real loopback transport tests; no model, tunnel, or candidate execution."""
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'ECHO-5.1/scripts/inference_relay.py'
spec = importlib.util.spec_from_file_location('inference_relay', SCRIPT)
relay = importlib.util.module_from_spec(spec) if SCRIPT.exists() else None
if relay:
    spec.loader.exec_module(relay)

CLIENT = 'client-' + 'c' * 40
WORKER = 'worker-' + 'w' * 40


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(relay, 'inference relay implementation is missing')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.log = Path(self.temp.name) / 'audit.jsonl'
        self.server = relay.RelayServer(('127.0.0.1', 0), client_token=CLIENT,
                                        worker_token=WORKER, request_timeout=.5,
                                        poll_timeout=.1, audit_log=self.log)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .01})
        self.thread.start()
        self.addCleanup(self.close_server)

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def request(self, method, path, token=CLIENT, data=None, raw=None, headers=None):
        conn = http.client.HTTPConnection(*self.server.server_address, timeout=3)
        hdr = {'Content-Type': 'application/json'}
        if token is not None:
            hdr['Authorization'] = 'Bearer ' + token
        hdr.update(headers or {})
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        try:
            conn.request(method, path, body, hdr)
            response = conn.getresponse()
            content = response.read()
            return response.status, json.loads(content) if content else None
        finally:
            conn.close()

    def submit(self, path='/completion', data=None):
        result = queue.Queue()
        def send():
            try:
                result.put(self.request('POST', path, data=data or {'prompt': [1], 'stream': False}))
            except Exception as exc:
                result.put(exc)
        thread = threading.Thread(target=send)
        thread.start()
        self.addCleanup(thread.join, 3)
        return result

    def next_job(self):
        until = time.monotonic() + 2
        while time.monotonic() < until:
            status, value = self.request('GET', '/worker/next', WORKER)
            self.assertEqual(status, 200)
            if value.get('id'):
                return value
        self.fail('worker never received job')

    def finish(self, job, data=None, status=200):
        return self.request('POST', '/worker/result', WORKER,
                            {'id': job['id'], 'status': status, 'data': data or {'content': 'answer'}})

    def test_roles_and_exact_routes_are_enforced(self):
        for method, path, token, want in (
            ('GET', '/health', None, 401), ('GET', '/health', 'wrong', 401),
            ('POST', '/completion', WORKER, 403), ('GET', '/worker/next', CLIENT, 403),
            ('POST', '/worker/result', CLIENT, 403), ('POST', '/stop', WORKER, 403),
            ('GET', '/health', WORKER, 403), ('GET', '/etc/passwd', CLIENT, 404),
            ('POST', '/v1/chat/completions', CLIENT, 404),
            ('POST', '/completion?url=http://example.com', CLIENT, 404),
            ('POST', 'http://example.com/completion', CLIENT, 404),
            ('GET', '/completion', CLIENT, 405), ('PUT', '/completion', CLIENT, 405),
        ):
            with self.subTest(method=method, path=path, token=token):
                self.assertEqual(self.request(method, path, token, {})[0], want)
        self.assertEqual(self.request('GET', '/health')[0], 200)

    def test_roundtrip_preserves_payload_and_hash_and_rejects_replay(self):
        for path, payload, answer in (
            ('/apply-template', {'messages': [{'role': 'user', 'content': 'secret prompt'}]}, {'prompt': 'templated'}),
            ('/tokenize', {'content': 'templated', 'add_special': False}, {'tokens': [5, 9]}),
            ('/completion', {'prompt': [5, 9], 'stream': False}, {'content': 'secret result'}),
        ):
            pending = self.submit(path, payload)
            job = self.next_job()
            self.assertEqual((job['path'], job['data']), (path, payload))
            canonical = json.dumps({'path': path, 'data': payload}, sort_keys=True,
                                   separators=(',', ':'), ensure_ascii=True).encode()
            self.assertEqual(job['request_sha256'], hashlib.sha256(canonical).hexdigest())
            self.assertEqual(self.finish(job, answer)[0], 200)
            self.assertEqual(pending.get(timeout=2), (200, answer))
            self.assertEqual(self.finish(job, answer)[0], 409)
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(set(row), {'request_sha256', 'response_sha256', 'status', 'elapsed_ms'})
        for secret in ('secret', 'templated', CLIENT, WORKER):
            self.assertNotIn(secret, self.log.read_text())

    def test_single_pending_slot_timeout_cleanup_and_stale_result(self):
        pending = self.submit()
        job = self.next_job()
        self.assertEqual(self.request('POST', '/completion', data={})[0], 429)
        self.assertEqual(self.request('GET', '/worker/next', WORKER)[1], {'status': 'idle'})
        self.assertEqual(pending.get(timeout=2)[0], 504)
        newer = self.submit()
        new_job = self.next_job()
        self.assertNotEqual(new_job['id'], job['id'])
        self.assertEqual(self.finish(job)[0], 409)
        self.assertEqual(self.finish(new_job)[0], 200)
        self.assertEqual(newer.get(timeout=2)[0], 200)

    def test_undelivered_request_times_out_without_later_delivery(self):
        self.assertEqual(self.submit().get(timeout=2)[0], 504)
        self.assertEqual(self.request('GET', '/worker/next', WORKER)[1], {'status': 'idle'})

    def test_stop_wakes_client_and_worker_and_rejects_future_work(self):
        pending = self.submit()
        job = self.next_job()
        self.assertEqual(self.request('POST', '/stop', data={})[0], 200)
        self.assertEqual(pending.get(timeout=2)[0], 503)
        self.assertEqual(self.request('GET', '/worker/next', WORKER)[1], {'status': 'stop'})
        self.assertEqual(self.finish(job)[0], 409)
        self.assertEqual(self.request('POST', '/completion', data={})[0], 503)

    def test_invalid_json_framing_streaming_and_size_are_rejected(self):
        for raw in (b'{', b'[]', b'{"a":1,"a":2}', b'{"a":NaN}'):
            self.assertEqual(self.request('POST', '/completion', raw=raw)[0], 400)
        self.assertEqual(self.request('POST', '/completion', data={'stream': True})[0], 400)
        self.assertEqual(self.request('POST', '/completion', raw=b'{}',
                                     headers={'Content-Length': str(2 * 1024 * 1024 + 1)})[0], 413)
        self.assertEqual(self.request('POST', '/completion', raw=b'{}',
                                     headers={'Transfer-Encoding': 'chunked'})[0], 400)
        pending = self.submit()
        job = self.next_job()
        for status in (True, 101, 302, 600):
            self.assertEqual(self.finish(job, status=status)[0], 400)
        self.assertEqual(self.finish(job, status=422)[0], 200)
        self.assertEqual(pending.get(timeout=2)[0], 422)

    def test_provider_key_env_works_without_provider_changes(self):
        from echoai.pcworld.provider import HTTPProvider
        base = 'http://127.0.0.1:' + str(self.server.server_port)
        provider = HTTPProvider({'endpoint': base + '/completion',
            'tokenize_endpoint': base + '/tokenize', 'model': 'fake', 'revision': 'test',
            'quantization': 'none', 'tokenizer': 'fake', 'max_output_tokens': 32,
            'timeout_seconds': 2, 'key_env': 'ECHO_RELAY_TEST_CLIENT'})
        result = queue.Queue()
        def serve():
            job = self.next_job()
            result.put(self.finish(job, {'tokens': [3, 7]}))
        worker = threading.Thread(target=serve)
        worker.start()
        with patch.dict(os.environ, ECHO_RELAY_TEST_CLIENT=CLIENT):
            self.assertEqual(provider._post(base + '/tokenize', {'content': 'hi'}, timeout=2),
                             {'tokens': [3, 7]})
        worker.join(2)
        self.assertEqual(result.get(timeout=1)[0], 200)

    def test_worker_forwards_only_verified_inference_job_and_stops(self):
        job={'id':'opaque','path':'/tokenize','data':{'content':'hello'}}
        job['request_sha256']=hashlib.sha256(relay.encoded({'path':job['path'],'data':job['data']})).hexdigest()
        calls=[]
        answers=iter([(200,{}),(200,job),(200,{'tokens':[1,2]}),(200,{}),(200,{'status':'stop'})])
        def fetch(url,**kw):calls.append((url,kw));return next(answers)
        with patch.object(relay,'fetch',fetch):
            result=relay.run_worker('https://broker.example',WORKER,max_seconds=10,ready_metadata={'gpu':'test'})
        self.assertEqual(result,{'requests':1,'stopped':True})
        self.assertEqual(calls[2],('http://127.0.0.1:8785/tokenize',{'data':{'content':'hello'},'timeout':calls[2][1]['timeout']}))
        self.assertEqual(calls[3][1]['data'],{'id':'opaque','status':200,'data':{'tokens':[1,2]}})
        self.assertNotIn('token',calls[2][1])

    def test_worker_rejects_unapproved_target_before_forwarding(self):
        for path in ('http://attacker.example/','/etc/passwd'):
            with patch.object(relay,'fetch',side_effect=[(200,{}),(200,{'id':'opaque','path':path,'data':{},'request_sha256':'bad'})]) as call:
                with self.assertRaises(ValueError):relay.run_worker('https://broker.example',WORKER,max_seconds=10)
                self.assertEqual(call.call_count,2)

    def test_configuration_rejects_unbounded_or_shared_credentials(self):
        for overrides in ({'request_timeout': 301}, {'request_timeout': float('nan')},
                          {'poll_timeout': 21}, {'client_token': WORKER},
                          {'worker_token': ''}):
            args = {'client_token': CLIENT, 'worker_token': WORKER, **overrides}
            with self.assertRaises(ValueError):
                relay.RelayServer(('127.0.0.1', 0), **args)
        with self.assertRaises(ValueError):
            relay.RelayServer(('0.0.0.0', 0), client_token=CLIENT, worker_token=WORKER)


if __name__ == '__main__':
    unittest.main()
