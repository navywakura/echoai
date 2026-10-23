import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

from echoai.echo58 import wspfiles as w


class ArchiveTests(unittest.TestCase):
    def sample(self):
        return w.Archive('wsp16-session-v1', {'source': 'dev', 'time': None}, (
            w.Record(bytes(range(16)), {'n': 0, 'flag': False, 'time': None, 'str': 'á|\n'}),
            w.Record(bytes([255]) * 16, {'sender': 0}),
        ), {'order': 'source'})

    def resign(self, raw):
        return bytes(raw[:-32]) + hashlib.sha256(raw[:-32]).digest()

    def test_exact_bytes_and_metadata_roundtrip(self):
        a = self.sample()
        self.assertEqual(w.decode(w.encode(a)), a)
        self.assertEqual(w.from_json(w.to_json(a)), a)
        self.assertNotIn('time', w.decode(w.encode(a)).records[1].metadata)

    def test_empty_archive(self):
        a = w.Archive('wsp16-session-v1', {}, ())
        self.assertEqual(w.decode(w.encode(a)), a)

    def test_selective_packet_and_bounds(self):
        raw = w.encode(self.sample())
        self.assertEqual(w.packet_at(raw, 1), bytes([255])*16)
        for index in (-1, 2, True, '0'):
            with self.subTest(index=index), self.assertRaises(ValueError):
                w.packet_at(raw, index)

    def test_every_truncation_rejected(self):
        raw = w.encode(self.sample())
        for end in range(len(raw)):
            with self.subTest(end=end), self.assertRaises(ValueError):
                w.decode(raw[:end])

    def test_each_corrupted_byte_rejected(self):
        raw = w.encode(self.sample())
        for index in range(len(raw)):
            bad = bytearray(raw); bad[index] ^= 1
            with self.subTest(index=index), self.assertRaises(ValueError):
                w.decode(bytes(bad))

    def test_version_flags_magic_and_sobrantes_even_rehashed(self):
        raw = w.encode(self.sample())
        for offset in (0, 8, 10):
            bad = bytearray(raw); bad[offset] ^= 8
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                w.decode(self.resign(bad))
        with self.assertRaises(ValueError):
            w.decode(self.resign(raw[:-32]+b'x'+raw[-32:]))

    def test_declared_lengths_and_record_count_rejected(self):
        raw = w.encode(self.sample())
        for offset in (12, 16, 20):
            bad = bytearray(raw); struct.pack_into('<I', bad, offset, 2**32-1)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                w.decode(self.resign(bad))

    def test_profile_and_packet_validation(self):
        for a in (w.Archive('unknown', {}, ()),
                  w.Archive('wsp16-session-v1', {}, (w.Record(b'x', {}),)),
                  w.Archive('wsp16-session-v1', {}, (w.Record(bytearray(16), {}),)),
                  w.Archive('wsp16-session-v1', {}, (w.Record(bytes(16), []),))):
            with self.subTest(a=a), self.assertRaises(ValueError): w.encode(a)

    def test_json_duplicate_unknown_bool_hex_and_nonfinite(self):
        for text in ('[true,"wsp16-session-v1",{},{},[]]',
                     '[1,"wsp16-session-v1",{"x":1,"x":2},{},[]]',
                     '[1,"wsp16-session-v1",{},{},[["00",{}]]]',
                     '[1,"wsp16-session-v1",{},{"n":NaN},[]]',
                     '[1,"wsp16-session-v1",{},{},[]] trailing',
                     '[2,"wsp16-session-v1",{},{},[]]'):
            with self.subTest(text=text), self.assertRaises(ValueError): w.from_json(text)

    def test_metadata_nonfinite_depth_and_keys_rejected(self):
        deep = {}
        for _ in range(34): deep = {'x': deep}
        for meta in ({'n': float('inf')}, {1: 'key'}, deep, {'x': object()}, {'s': '\ud800'}):
            with self.subTest(meta=repr(meta)[:60]), self.assertRaises(ValueError):
                w.encode(w.Archive('wsp16-session-v1', {}, (), meta))

    def test_limits_applied_before_allocation(self):
        from unittest.mock import patch
        a = self.sample()
        for limit, value in (('MAX_FILE', 16), ('MAX_RECORDS', 1),
                             ('MAX_DESCRIPTOR', 4), ('MAX_METADATA', 4)):
            with self.subTest(limit=limit), patch.object(w.codec, limit, value), self.assertRaises(ValueError):
                w.encode(a)
        with self.assertRaises(ValueError): w.decompress(zlib.compress(b'x' * 1000), limit=32)
        with self.assertRaises(ValueError): w.decompress(zlib.compress(b'x')+b'trailing')
        with self.assertRaises(ValueError): w.decompress(zlib.compress(b'x')[:-1])

    def test_compressed_roundtrip(self):
        raw = w.encode(self.sample())
        self.assertEqual(w.decompress(zlib.compress(raw)), raw)

    def test_exclusive_write_and_read(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'a.wsp'
            w.write(path, self.sample()); self.assertEqual(w.read(path), self.sample())
            with self.assertRaises(FileExistsError): w.write(path, self.sample())

    def test_cli_inspect_export_import_and_verify(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'a.wsp'; out=Path(root)/'b.json'; restored=Path(root)/'b.wsp'
            w.write(path,self.sample())
            def cli(*args):
                p=subprocess.run([sys.executable,'-m','echoai.echo58.wspfiles',*map(str,args)],
                                 capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr); return p.stdout
            info=json.loads(cli('inspect',path)); self.assertEqual(info['records'],2)
            self.assertTrue(json.loads(cli('verify',path))['valid'])
            cli('export-json',path,out); cli('import-json',out,restored)
            self.assertEqual(path.read_bytes(),restored.read_bytes())


class MemoryTests(unittest.TestCase):
    def memory(self):
        from echoai.echo58.memx.memory import Memory
        m=Memory(3,85)
        for _ in range(4):
            m.observe(7,0,'ENTER',0,'HURT')
            m.observe(8,4,'ENTER',0,'PASS')
        return m

    def test_memory_history_rules_queries_and_agent_decisions_identical(self):
        with tempfile.TemporaryDirectory() as root:
            m=self.memory(); path=Path(root)/'memory.wsp'
            w.export_memory(m,path,provenance={'source':'test'})
            restored=w.load_memory(path)
            self.assertEqual((m.records,m.head,m.l1,m.l2),(restored.records,restored.head,restored.l1,restored.l2))
            r=w.compare_decisions(m,restored)
            self.assertGreater(r['decisions'],0); self.assertEqual(r['mismatches'],0)
            self.assertGreater(r['source_queries'],0)
            self.assertGreater(r['source_hits'],0)
            self.assertGreater(r['different_from_empty'],0)
            self.assertTrue(w.codec.dumps(r))

    def test_memory_changed_history_postcards_and_thresholds_rejected(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'a.wsp'; w.export_memory(self.memory(),path)
            a=w.read(path)
            for kind in ('chain','postcard','bound','profile'):
                b=w.from_json(w.to_json(a))
                if kind=='chain': b.metadata['history'][0]['o']='GOAL'
                if kind=='postcard': b=replace(b,records=(replace(b.records[0],packet=bytes(16)),)+b.records[1:])
                if kind=='bound': b.metadata['n_min']=True
                if kind=='profile': b=replace(b,profile='wsp16-session-v1')
                out=Path(root)/(kind+'.wsp'); w.write(out,b)
                with self.subTest(kind=kind), self.assertRaises(ValueError):w.load_memory(out)


class ControlTests(unittest.TestCase):
    def test_four_controls_identical_and_selective_with_no_receipt_bypass(self):
        from echoai.echo58.wspfiles import bench
        a=ArchiveTests().sample()
        for arm in bench.ARMS:
            with self.subTest(arm=arm):
                raw=bench.encode_arm(a,arm)
                self.assertEqual(bench.decode_arm(raw,arm),a)
                self.assertEqual(bench.selective_packet(raw,arm,1),a.records[1].packet)
                bad=bytearray(raw);bad[len(bad)//2]^=1
                with self.assertRaises(ValueError):bench.decode_arm(bytes(bad),arm)
                with self.assertRaises(ValueError):bench.selective_packet(bytes(bad),arm,1)

    def test_timing_derived_values_and_audit_root_bounds(self):
        from echoai.echo58.wspfiles.bench import summary
        from echoai.echo58.wspfiles.audit import inside
        samples=[{'wall_ns':i,'process_ns':i*2} for i in range(9)]
        self.assertEqual(summary(samples), {'wall_ns':{'median':4,'p95':8},'process_ns':{'median':8,'p95':16}})
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):inside(Path(root),'../escape')

    def test_offline_audit_detects_metrics_source_and_artifact_changes(self):
        from echoai.echo58.wspfiles import bench, audit
        from echoai.echo58.wspfiles.memory import memory_archive
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'corpus').mkdir();(root/'artifacts').mkdir()
            memory=MemoryTests().memory();memory.save(root/'corpus/training.jsonl')
            source={'source':'training.jsonl','snapshot':'corpus/training.jsonl',
                    'sha256':bench.sha((root/'corpus/training.jsonl').read_bytes()),'name':'memory-training-m01'}
            a=memory_archive(memory,{'source':source['source'],'source_sha256':source['sha256'],
                'source_kind':'training memory; postcards generated at export'})
            manifest={'sources':[source],'code':[],'replicas':9,'arms':list(bench.ARMS),
                      'operations':list(bench.OPERATIONS),'artifacts':{}}
            dataset={'records':len(a.records),'lossless':True,'json_without_receipt_bytes':len(w.to_json(a).encode()),'arms':{}}
            for arm in bench.ARMS:
                name='artifacts/memory-training-m01'+('.wsp' if arm=='wsp' else '.'+arm)
                raw=bench.encode_arm(a,arm);(root/name).write_bytes(raw)
                manifest['artifacts'][name]={'dataset':'memory-training-m01','arm':arm,'bytes':len(raw),'sha256':bench.sha(raw)}
                samples={op:[{'replica':i,'wall_ns':i,'process_ns':i} for i in range(9)] for op in bench.OPERATIONS}
                dataset['arms'][arm]={'bytes':len(raw),'samples':samples,'timing':{op:bench.summary(v) for op,v in samples.items()}}
            result={'datasets':{'memory-training-m01':dataset},'integration':w.compare_decisions(memory,w.load_memory(root/'artifacts/memory-training-m01.wsp'))}
            def put(name,value):(root/name).write_bytes(w.codec.dumps(value))
            put('manifest.json',manifest);put('preflight.json',manifest);put('results.json',result)
            self.assertTrue(audit.audit(root)['valid'])
            saved=(root/'results.json').read_bytes()
            result['datasets']['memory-training-m01']['arms']['json']['timing']['decode']['wall_ns']['median']+=1
            put('results.json',result)
            with self.assertRaises(ValueError):audit.audit(root)
            (root/'results.json').write_bytes(saved)
            source_path=root/'corpus/training.jsonl';raw=source_path.read_bytes();source_path.write_bytes(raw+b'x')
            with self.assertRaises(ValueError):audit.audit(root)
            source_path.write_bytes(raw)
            path=root/'artifacts/memory-training-m01.wsp';raw=path.read_bytes();path.write_bytes(raw[:-1])
            with self.assertRaises(ValueError):audit.audit(root)


if __name__=='__main__':unittest.main()
