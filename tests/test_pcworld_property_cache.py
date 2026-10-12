import tempfile
from pathlib import Path
import unittest
from echoai.pcworld.property_cache import PropertyCache

class PureCache(unittest.TestCase):
    def test_restart_reuses_exact_pure_check_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);calls=[]
            cache=PropertyCache(root)
            key={'runtime':'a'*64,'snapshot':'b'*64,'checker':'c'*64,'input':[1],
                 'observed':'1','seed':0,'policy':'fixed'}
            def compute(): calls.append(1);return {'status':'supported'}
            self.assertFalse(cache.check(key,compute)[1]['hit'])
            value,meta=PropertyCache(root).check(key,compute)
            self.assertEqual(value,{'status':'supported'});self.assertTrue(meta['hit'])
            self.assertEqual(len(calls),1);self.assertGreater(meta['lookup_ns'],0)
            for field in ('runtime','snapshot','checker','seed','policy','input','observed'):
                changed={**key,field:'different'}
                self.assertFalse(cache.check(changed,compute)[1]['hit'])
    def test_tampered_cache_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);cache=PropertyCache(root)
            cache.check({'a':1},lambda:{'status':'supported'})
            journal=root/'receipts/receipts.jsonl'
            raw=journal.read_bytes();journal.write_bytes(raw.replace(b'supported',b'contradicted'))
            with self.assertRaises((RuntimeError,ValueError)):
                PropertyCache(root).check({'a':1},lambda:{'status':'supported'})
