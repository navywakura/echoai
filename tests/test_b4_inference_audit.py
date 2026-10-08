import base64
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import unittest


class PayloadAuditTests(unittest.TestCase):
    def test_equivalent_key_order_passes_but_payload_or_wrapper_tampering_fails(self):
        path = Path(__file__).resolve().parents[1] / "lab/kaggle/s6b4-runtime2-20260928/closure.py"
        spec = spec_from_file_location("_audit_test", path)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        template = "import base64,json\npayload=json.loads(base64.b64decode(PAYLOAD))\nx=1\n"
        payload = {"z": 1, "a": 2}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        script = template.replace("PAYLOAD", repr(encoded))
        mod.verify_wrapper(script, template, {"a": 2, "z": 1})
        with self.assertRaises(AssertionError):
            mod.verify_wrapper(script, template, {"a": 2, "z": 3})
        with self.assertRaises(AssertionError):
            mod.verify_wrapper(script.replace("x=1", "x=2"), template, payload)
