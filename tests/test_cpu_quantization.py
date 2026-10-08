import importlib.util
from pathlib import Path
import unittest
import warnings


@unittest.skipUnless(importlib.util.find_spec('torch'),'optional separately installed CPU torch')
class CPUQuantization(unittest.TestCase):
    def test_conversion_is_explicit_cpu_finite_and_complete(self):
        import torch
        spec=importlib.util.spec_from_file_location('_cpu_support',Path(__file__).resolve().parents[1]/'lab/kaggle/cpu_inference_support.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        torch.set_num_threads(2);torch.manual_seed(41)
        model=torch.nn.Sequential(torch.nn.Embedding(16,8),torch.nn.Sequential(torch.nn.Linear(8,16),
            torch.nn.ReLU(),torch.nn.Linear(16,8)),torch.nn.LayerNorm(8)).half().eval()
        with torch.no_grad():
            original=model(torch.tensor([[1,2,3]])).float()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',DeprecationWarning)
                receipt=module.dynamic_int8(model)
            actual=model(torch.tensor([[1,2,3]]))
        self.assertEqual(len(receipt['linears']),2)
        self.assertFalse(receipt['bit_equivalent_to_float16'])
        self.assertEqual(actual.shape,original.shape)
        self.assertTrue(torch.isfinite(actual).all().item())
        self.assertLess((original-actual).abs().mean().item(),0.1)
        self.assertTrue(all(p.dtype==torch.float32 for p in model.parameters()))
        with self.assertRaises(ValueError):module.dynamic_int8(torch.nn.Sequential(torch.nn.Linear(2,2)))


if __name__=='__main__':unittest.main()
