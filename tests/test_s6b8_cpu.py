import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seed import s6b8_cpu as s


def transport_module():
    spec=importlib.util.spec_from_file_location('_test_cpu_transport',s.BASE/'transport.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class CPUContinuation(unittest.TestCase):
    def test_inherited_runner_keeps_defaults_and_reads_its_own_rounds(self):
        self.assertIs(s.run_phase.__code__,s.parent.run_phase.__code__)
        self.assertEqual(s.run_phase.__defaults__,(False,))
        self.assertIs(s.run_phase.__globals__['load_phase'],s.load_phase)
        with tempfile.TemporaryDirectory() as directory,patch.object(s,'ROOT',Path(directory)):
            s.atomic(s.ROOT/'pilot/round-2.json',{'own_round':2})
            self.assertEqual(s.load_phase('pilot',2),{'own_round':2})
        self.assertEqual(s.parent.config()['calls_with_calibration'],82)

    def test_transport_rejects_gpu_public_unrelated_and_extra_data(self):
        gen=s.generator();module=transport_module()
        meta=gen.metadata('p2');module.validate_metadata(meta)
        for key,value in [('enable_gpu',True),('enable_tpu',True),('is_private',False),
                          ('id','someone/other'),('kernel_sources',[]),('dataset_sources',['extra'])]:
            bad=copy.deepcopy(meta);bad[key]=value
            with self.assertRaises(AssertionError):module.validate_metadata(bad)
        for stage in ('p0','p1','c6'):
            with self.assertRaises(AssertionError):gen.metadata(stage)

    def test_wrapper_preserves_model_revision_dtype_and_generation_limits(self):
        code=s.generator().template().replace('PAYLOAD',repr('e30='))
        compile(code,'cpu-wrapper','exec')
        self.assertIn("torch_dtype=torch.float16,device_map={'':'cpu'}",code)
        self.assertIn("prefill_chunk_size=512,cache_implementation='dynamic'",code)
        self.assertIn("generate(payload['requests'][arm],fmt,cfg['seeds'][arm])",code)
        self.assertIn(s.REVISION,code)
        self.assertIn("os.environ['HF_HUB_OFFLINE']='1'",code)
        self.assertNotIn("device_map='auto'",code)
        self.assertNotIn('model.hf_device_map',code)
        self.assertIn('model.named_parameters()',code)

    def test_cached_weight_mount_verifies_all_bytes_before_inference(self):
        namespace={};exec(s.generator().CACHE_SETUP.split('\nreceipt=')[0],namespace)
        mount=namespace['mount_weights']
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=root/'input/kernel';weights=data/'qwen-pinned'
            weights.mkdir(parents=True)
            files={}
            shards=[f'model-{i}.safetensors' for i in range(4)]
            content={n:b'test-only synthetic shard '+n.encode() for n in shards}
            content['model.safetensors.index.json']=json.dumps({'weight_map':dict(enumerate(shards))}).encode()
            for name,blob in content.items():
                (weights/name).write_bytes(blob)
                files[name]={'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),
                             'lfs_sha256_checked':name in shards}
            manifest={'complete':True,'model':s.MODEL,'revision':s.REVISION,'weight_shards':4,
                      'files':files,'total_bytes':sum(x['bytes'] for x in files.values())}
            blob=json.dumps(manifest).encode();(data/'manifest.json').write_bytes(blob)
            digest=hashlib.sha256(blob).hexdigest()
            receipt=mount(root/'input',root/'cache',digest,s.MODEL,s.REVISION)
            self.assertEqual(receipt['weight_shards'],4)
            link=root/'cache'/('models--'+s.MODEL.replace('/','--'))/'snapshots'/s.REVISION/shards[0]
            self.assertTrue(link.is_symlink())
            (weights/shards[0]).write_bytes(b'x'*files[shards[0]]['bytes'])
            with self.assertRaises(AssertionError):mount(root/'input',root/'cache',digest,s.MODEL,s.REVISION)
            with self.assertRaises(AssertionError):mount(root/'input',root/'cache','wrong',s.MODEL,s.REVISION)

    def test_cpu_result_requires_backend_weight_and_source_receipts(self):
        gen=s.generator();profile={'cache_manifest_sha256':'weights'}
        payload={'round':2,'requests':{'local-echo-1':[{'id':2}]},'requests_sha256':'reqs',
                 'source_digest':'original','cpu_profile_sha256':s.sha(profile)}
        result={'complete':True,'requests_sha256':'reqs','calibration':[],
                'arms':{'local-echo-1':[{'id':2}]},'profile':{'model':s.MODEL,'revision':s.REVISION,
                'source_digest':'original','backend':'cpu-float16','threads':4,'devices':{'':'cpu'},
                'cpu_profile_sha256':s.sha(profile),'weights':{'manifest_sha256':'weights','weight_shards':4}}}
        with patch.object(s,'profile',return_value=profile):
            self.assertIs(gen.check(result,payload),result)
            for key,value in [('devices',{'':'cuda:0'}),('devices',{}),('cpu_profile_sha256','changed'),
                              ('weights',{'manifest_sha256':'other','weight_shards':4})]:
                bad=copy.deepcopy(result);bad['profile'][key]=value
                with self.assertRaises(AssertionError):gen.check(bad,payload)
            bad=copy.deepcopy(result);bad['complete']=False
            with self.assertRaises(AssertionError):gen.check(bad,payload)

    def test_failed_round_is_never_accepted_by_audit(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(s,'BASE',Path(directory)),patch.object(s,'integrity'):
            s.atomic(s.BASE/'p2/terminal.json',{'status':'ERROR'})
            with self.assertRaises(AssertionError):s.audit_model('p2',{})


if __name__=='__main__':unittest.main()
