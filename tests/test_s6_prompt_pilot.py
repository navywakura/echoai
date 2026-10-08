import copy
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

from seed import s6_prompt_pilot as pilot


class Readiness(unittest.TestCase):
    def positive(self):
        return {"status": "POSITIVE_CONTROL", "profile_sha256": "profile", "winner": "one",
                "verdicts": [{"name": "one", "verdict": "POSITIVE_CONTROL",
                              "A": {"gain": 2, "loss_indices": []}, "B": {"loss_indices": []}}]}

    def test_gate_rejects_pending_changed_profile_and_hidden_losses(self):
        valid = self.positive()
        pilot.positive_gate(valid, "profile")
        mutations = [("status", "NO_POSITIVE_IN_BOUNDED_SEARCH"), ("profile_sha256", "other"),
                     ("winner", "missing")]
        for key, value in mutations:
            changed = copy.deepcopy(valid)
            changed[key] = value
            with self.assertRaises(ValueError):
                pilot.positive_gate(changed, "profile")
        for cohort in ("A", "B"):
            changed = copy.deepcopy(valid)
            changed["verdicts"][0][cohort]["loss_indices"] = [1]
            with self.assertRaises(ValueError):
                pilot.positive_gate(changed, "profile")
        changed = copy.deepcopy(valid)
        changed["verdicts"][0]["A"]["gain"] = 1
        with self.assertRaises(ValueError):
            pilot.positive_gate(changed, "profile")

    def test_sampling_wrapper_keeps_full_prompts_and_tested_cache_recovery(self):
        path = Path(__file__).resolve().parents[1] / "lab/kaggle/s6-prompt-pilot-20260928/generate.py"
        definition = spec_from_file_location("_test_prompt_generator", path)
        generator = module_from_spec(definition)
        definition.loader.exec_module(generator)
        code = generator.wrapper()
        compile(code.replace("PAYLOAD", "'e30='"), "test.py", "exec")
        self.assertIn("truncation=False", code)
        self.assertIn("refusing prompt truncation", code)
        self.assertIn("prefill_chunk_size=512,cache_implementation='dynamic',use_cache=True", code)
        self.assertIn("generate(payload['requests'][arm],fmt,cfg['seeds'][arm])", code)
        self.assertNotIn("590000+payload['round']", code)
        self.assertEqual(code.count("model=AutoModelForCausalLM.from_pretrained"), 1)
        self.assertIn("len(result['calibration'])==2", code)


if __name__ == "__main__":
    unittest.main()
