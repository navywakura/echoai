import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


class RecoveryTests(unittest.TestCase):
    def test_runtime_change_is_only_chunking_and_explicit_provenance(self):
        path = Path(__file__).resolve().parents[1] / "lab/kaggle/s6b4-runtime-20260928/generate.py"
        spec = spec_from_file_location("_test_recovery", path)
        g = module_from_spec(spec)
        spec.loader.exec_module(g)
        new = g.wrapper("abc")
        compile(new.replace("PAYLOAD", "'e30='"), "run.py", "exec")
        recovered = new.replace("prefill_chunk_size=512,", "").replace(
            ",'runtime_digest':'abc'", "")
        self.assertEqual(recovered, g.old.WRAPPER)
        self.assertIn("truncation=False", new)
        self.assertIn("refusing prompt truncation", new)


if __name__ == "__main__":
    unittest.main()
