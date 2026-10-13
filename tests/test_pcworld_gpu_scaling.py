"""A larger model must be pinned, split explicitly and actually offloaded."""
from pathlib import Path
import runpy
import unittest

ROOT=Path(__file__).resolve().parents[1]
class GPUScaling(unittest.TestCase):
    def setUp(self):
        self.worker=runpy.run_path(str(ROOT/'ECHO-5.1/scripts/kaggle_repair_worker.py'))
    def test_32b_uses_two_devices_and_fixed_context(self):
        profile=self.worker['model_profile']('qwen25-coder32b')
        cmd=self.worker['server_command']('/bin/llama-server','/weights/model.gguf',profile)
        self.assertEqual(cmd[cmd.index('--device')+1],'CUDA0,CUDA1')
        self.assertEqual(cmd[cmd.index('--split-mode')+1],'layer')
        self.assertEqual(cmd[cmd.index('--tensor-split')+1],'1,1')
        self.assertEqual(cmd[cmd.index('--ctx-size')+1],'4096')
        self.assertEqual(cmd[cmd.index('--fit')+1],'off')
        self.assertEqual(profile['layers'],65)
        self.assertEqual(profile['bytes'],19851335872)
    def test_partial_or_one_device_offload_cannot_start_32b_pilot(self):
        p=self.worker['model_profile']('qwen25-coder32b')
        good='offloaded 65/65 layers to GPU\nCUDA0 model buffer size = 9000.00 MiB\nCUDA1 model buffer size = 9000.00 MiB'
        evidence=self.worker['verify_offload'](good,p)
        self.assertEqual(evidence['gpu_offload'],[('65','65')])
        for bad in (good.replace('65/65','40/65'),good.replace('CUDA1','CUDA0'),good.replace('9000.00','100.00')):
            with self.assertRaises(RuntimeError):self.worker['verify_offload'](bad,p)
    def test_14b_profile_preserves_original_identity(self):
        p=self.worker['model_profile']('qwen25-coder14b')
        self.assertEqual(p['sha256'],self.worker['MODEL_SHA'])
        self.assertEqual(p['revision'],self.worker['MODEL_REV'])
        self.assertEqual(p['devices'],['CUDA0'])
        with self.assertRaises(ValueError):self.worker['model_profile']('arbitrary/download')
    def test_provider_identity_mismatch_is_rejected_before_inference(self):
        p=self.worker['model_profile']('qwen25-coder32b')
        config={'model':p['alias'],'revision':p['revision'],'tokenizer':'embedded GGUF '+p['sha256'],
                'context_tokens':4096,'quantization':'Q4_K_M'}
        self.worker['validate_provider_profile'](config,p)
        for k,v in [('model','14b'),('revision','main'),('context_tokens',8192),('quantization','Q8_0')]:
            with self.assertRaises(ValueError):self.worker['validate_provider_profile']({**config,k:v},p)
