import importlib.util
import tempfile
import unittest
import threading
import queue
import time
from unittest.mock import patch
from pathlib import Path
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
spec=importlib.util.spec_from_file_location('repo_relay',ROOT/'repository/scripts/inference_relay.py')
relay=importlib.util.module_from_spec(spec);spec.loader.exec_module(relay)


class RelayTests(unittest.TestCase):
    def test_lost_result_ack_retries_delivery_without_regenerating(self):
        calls=[]
        job=dict(id='stable',path='/completion',data={'prompt':'x'})
        job['request_sha256']=relay.hashlib.sha256(relay.encoded({'path':job['path'],'data':job['data']})).hexdigest()
        polls=deliveries=0
        def fetch(url,**kw):
            nonlocal polls,deliveries
            calls.append(url)
            if url.endswith('/worker/ready'):return 200,{}
            if url.endswith('/worker/next'):
                polls+=1;return (200,job) if polls==1 else (200,{'status':'stop'})
            if url.endswith('/worker/result'):
                deliveries+=1
                if deliveries==1:raise TimeoutError('ack lost')
                return 200,{}
            return 200,{'content':'answer'}
        with patch.object(relay,'fetch',fetch),patch.object(relay.time,'sleep'):
            result=relay.run_worker('https://example.invalid','worker',max_seconds=60)
        self.assertTrue(result['stopped'])
        self.assertEqual(deliveries,2)
        self.assertEqual(sum(url.startswith('http://127.0.0.1:8785') for url in calls),1)

    def test_durable_id_replay_restart_and_conflicting_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=relay.DurableJobs(Path(tmp)/'jobs','s'*48)
            job={'job':{'id':'request-1','path':'/completion','data':{'prompt':'x'},'request_sha256':'a'*64},'delivered':True,'result':None}
            store.save(job)
            self.assertEqual(relay.DurableJobs(Path(tmp)/'jobs','s'*48).load('request-1'),job)
            job['result']=[200,{'content':'ok'}];store.save(job)
            self.assertEqual(store.load('request-1')['result'][1]['content'],'ok')
            path=next((Path(tmp)/'jobs').glob('*.json'))
            path.write_text(path.read_text().replace('"ok"','"forged"'))
            with self.assertRaises(ValueError): store.load('request-1')

    def test_late_response_frees_slot_and_replays_exactly(self):
        from tests.test_pcworld_inference_relay import RelayTests as Helpers
        h=Helpers();h.setUp()
        self.addCleanup(h.doCleanups)
        h.server.jobs=relay.DurableJobs(Path(h.temp.name)/'jobs',h.server.client_token)
        q=h.submit(data={'prompt':'one','request_id':'one'})
        job=h.next_job()
        self.assertEqual(q.get(timeout=2)[0],504)
        self.assertEqual(h.finish(job)[0],200)
        self.assertEqual(h.request('POST','/completion',data={'prompt':'one','request_id':'one'})[0],200)
        q=h.submit(data={'prompt':'two','request_id':'two'})
        second=h.next_job();self.assertEqual(second['id'],'two')
        h.finish(second);self.assertEqual(q.get(timeout=2)[0],200)
