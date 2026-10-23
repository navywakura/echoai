"""Strong JSON controls: stdlib fixtures only, no worlds, model or old measurements."""
import base64
import hashlib
from pathlib import Path
import tempfile
import unittest
import zlib
from unittest.mock import patch

from echoai.echo58.wspfiles import codec as original
try:
    from echoai.echo58.wspstrongjson import codec
except ImportError:
    codec=None


def fixture(empty=False):
    records=() if empty else (original.Record(bytes(range(16)),{'source':'sí','none':None}),
        original.Record(b'\xff'*16,{'float':1.0,'int':1,'bool':True,'nested':[False,0,'😀']}))
    return original.Archive('wsp16-session-v1',{'origin':'fixture','missing':None},records,{'notes':['α',1.0,True]})


class StrongJSONTests(unittest.TestCase):
    def setUp(self):self.assertIsNotNone(codec,'strong JSON codec missing')

    def test_all_layouts_preserve_exact_wsp_bytes_and_empty_archive(self):
        for empty in (False,True):
            a=fixture(empty)
            for layout in codec.LAYOUTS:
                for integrity in (False,True):
                    for compressed in (False,True):
                        raw=codec.encode(a,layout,integrity=integrity,compressed=compressed)
                        got=codec.decode(raw,layout,integrity=integrity,compressed=compressed)
                        self.assertEqual(original.encode(got),original.encode(a))

    def test_every_small_integrity_corruption_truncation_and_suffix_rejected(self):
        for layout in codec.LAYOUTS:
            raw=codec.encode(fixture(),layout)
            for i in range(len(raw)):
                changed=bytearray(raw);changed[i]^=1
                with self.assertRaises(ValueError):codec.decode(bytes(changed),layout)
            for i in range(len(raw)):
                with self.assertRaises(ValueError):codec.decode(raw[:i],layout)
            with self.assertRaises(ValueError):codec.decode(raw+b'x',layout)

    def test_sha_is_exactly_32_bytes_for_same_payload(self):
        for layout in codec.LAYOUTS:
            payload=codec.encode(fixture(),layout,integrity=False)
            full=codec.encode(fixture(),layout)
            self.assertEqual(full,payload+hashlib.sha256(payload).digest())
            self.assertEqual(codec.encode(fixture(),layout,compressed=True),zlib.compress(full,9))

    def test_rehashed_invalid_schemas_are_rejected(self):
        for layout in codec.LAYOUTS:
            data=original.loads(codec.encode(fixture(),layout,integrity=False))
            cases=[]
            for index,value in ((0,True),(0,2),(1,'unknown-profile'),(2,[]),(3,None)):
                changed=list(data);changed[index]=value;cases.append(changed)
            if layout=='b64-rows':
                changed=list(data);changed[4]=[['AA==',{}]];cases.append(changed)
                changed=list(data);changed[4]=[[base64.b64encode(b'x'*16).decode(),[]]];cases.append(changed)
            else:
                changed=list(data);changed[5]=[];cases.append(changed)
                changed=list(data);changed[4]='0' if layout=='b85-columns' else base64.b64encode(b'x'*17).decode();cases.append(changed)
            for bad in cases:
                with self.assertRaises(ValueError):codec.decode(original.dumps(bad),layout,integrity=False)

    def test_base64_noncanonical_padding_bits_and_whitespace_rejected(self):
        a=original.Archive('wsp16-session-v1',{},(original.Record(b'\x00'*16,{}),),{})
        data=original.loads(codec.encode(a,'b64-rows',integrity=False));text=data[4][0][0]
        for bad in (text[:-3]+'B==',text+'=',text+'\n',text.replace('A','!',1)):
            data[4][0][0]=bad
            with self.assertRaises(ValueError):codec.decode(original.dumps(data),'b64-rows',integrity=False)

    def test_invalid_json_and_unknown_layout_fail(self):
        for raw in (b'\xff',b'[NaN]',b'[1e999]',b'{"x":1,"x":2}',b'[]'):
            with self.assertRaises(ValueError):codec.decode(raw,'b64-columns',integrity=False)
        with self.assertRaises(ValueError):codec.encode(fixture(),'new-layout')
        with self.assertRaises(ValueError):codec.decode(b'','new-layout')

    def test_compressed_truncation_suffix_and_expansion_rejected(self):
        for layout in codec.LAYOUTS:
            raw=codec.encode(fixture(),layout,compressed=True)
            for bad in (raw[:-1],raw+b'junk'):
                with self.assertRaises(ValueError):codec.decode(bad,layout,compressed=True)
        with patch.object(original,'MAX_FILE',128):
            with self.assertRaises(ValueError):codec.decode(zlib.compress(b'x'*1024),'b64-rows',compressed=True)

    def test_base85_noncanonical_alias_and_invalid_alphabet_rejected(self):
        data=original.loads(codec.encode(fixture(),'b85-columns',integrity=False))
        for bad in ('0','~'*40,data[4]+'\n','é'):
            data[4]=bad
            with self.assertRaises(ValueError):codec.decode(original.dumps(data),'b85-columns',integrity=False)

    def test_fixture_only_freeze_measure_fresh_reconstruct_and_exclusive_writes(self):
        from echoai.echo58.wspstrongjson import bench,audit
        with tempfile.TemporaryDirectory() as temp:
            old=Path(temp)/'old';(old/'artifacts').mkdir(parents=True)
            manifest={'artifacts':{}}
            for name in bench.NAMES:
                raw=original.encode(fixture())
                for suffix,blob in (('.wsp',raw),('.wsp.zlib',zlib.compress(raw,9))):
                    rel='artifacts/'+name+suffix
                    (old/rel).write_bytes(blob)
                    manifest['artifacts'][rel]={'sha256':bench.sha(blob),'bytes':len(blob)}
            manifest_raw=bench.packed(manifest);(old/'manifest.json').write_bytes(manifest_raw)
            root=Path(temp)/'run'
            with patch.object(bench,'OLD',old),patch.object(bench,'MANIFEST_SHA',bench.sha(manifest_raw)):
                bench.prepare(root)
                with self.assertRaises(FileExistsError):bench.prepare(root)
                bench.measure(root)
                with self.assertRaises(ValueError):bench.measure(root)
                self.assertTrue(audit.audit(root)['passed'])
                with self.assertRaises(FileExistsError):audit.audit(root)
                artifact=next((root/'artifacts').iterdir());saved=artifact.read_bytes()
                artifact.write_bytes(saved+b'x')
                with self.assertRaises(ValueError):audit.audit(root)
                artifact.write_bytes(saved)
                result=root/'results.json';saved_result=result.read_bytes();result.write_bytes(b'{}')
                with self.assertRaises(ValueError):audit.audit(root)
                result.write_bytes(saved_result)
                frozen=root/'frozen'/bench.SOURCES[0]
                frozen.write_bytes(frozen.read_bytes()+b'x')
                with self.assertRaises(ValueError):bench.verify_freeze(root)

if __name__=='__main__':unittest.main()
