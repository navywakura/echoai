import importlib
from pathlib import Path
import tempfile
import unittest


class PacingTests(unittest.TestCase):
    def test_calls_share_persisted_spacing_and_respect_retry_after(self):
        p=importlib.import_module('echoai.echo58.crece.pacing')
        now=[1000.0];calls=[]
        def sleep(seconds):now[0]+=seconds
        def call(*args,**kwargs):
            calls.append(now[0])
            return {'status':429 if len(calls)==1 else 200,'rate_headers':{'retry-after':'80'}}
        with tempfile.TemporaryDirectory() as d:
            for _ in range(2):
                p.paced_complete('m','prompt',Path(d)/'cache',state_dir=Path(d)/'state',
                                 call=call,clock=lambda:now[0],sleep=sleep)
            self.assertEqual(calls,[1000,1080])

    def test_http_date_retry_defers_without_reserving_another_call(self):
        p=importlib.import_module('echoai.echo58.crece.pacing')
        sent=[];reserved=[]
        def call(*args,**kwargs):
            kwargs['before_call']();sent.append(1)
            return {'status':429,'rate_headers':{'retry-after':'Thu, 01 Jan 1970 01:00:00 GMT'}}
        with tempfile.TemporaryDirectory() as d:
            kwargs=dict(state_dir=Path(d),call=call,clock=lambda:1000,before_call=lambda:reserved.append(1))
            receipt=p.paced_complete('m','prompt',Path(d)/'cache',**kwargs)
            self.assertEqual(receipt['deferred_until'],3600)
            for _ in range(4):
                with self.assertRaises(p.QuotaDeferred):p.paced_complete('m','prompt',Path(d)/'cache',**kwargs)
            self.assertEqual((len(sent),len(reserved)),(1,1))
