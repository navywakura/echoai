from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest
from unittest.mock import patch

from seed import game_selfimprove_b5 as s


class B5Tests(unittest.TestCase):
    def test_same_budget_fresh_exam_and_no_manual_prompts(self):
        cfg = s.config()
        self.assertEqual(cfg["max_llm_calls_including_calibration"], 76)
        self.assertEqual(cfg["exam_seeds"], list(range(24200, 24260)))
        stats = {t: [0, 0] for t in s.old.TYPES}
        measured = {"rows": [{"levels_completed": 3, "actions_per_level": [10], "episodes": []}]}
        for arm in ("local-fijo", "local-echo"):
            requests = s.requests(arm, 0, 0, 2, s.strategy(), stats, measured, [], [])
            self.assertTrue(all("COOLDOWN_CAP" in item["prompt"] for item in requests))
            self.assertTrue(all("hold20_after_level" not in item["prompt"] for item in requests))

    def test_scoped_gpu_and_wrapper_preserves_cache_fix(self):
        for filename in ("generate", "transport"):
            definition = spec_from_file_location("_test_b5_" + filename, s.BASE / (filename + ".py"))
            module = module_from_spec(definition)
            definition.loader.exec_module(module)
            if filename == "generate":
                template = module.template()
                compile(template.replace("PAYLOAD", repr("e30=")), "wrapper.py", "exec")
                self.assertIn("precise_patch_grammar", template)
                self.assertIn("cache_implementation='dynamic'", template)
                self.assertIn("prefill_chunk_size=512", template)
                self.assertNotIn("samples=model.generate(**enc,max_new_tokens=", template)
            else:
                self.assertTrue(module.valid_ref("rogeernavarro/echo45-s6b5-pilot-20260928"))
                self.assertFalse(module.valid_ref("rogeernavarro/unrelated"))
                self.assertFalse(module.valid_ref("rogeernavarro/echo45-s6b5-r6-20260928"))

    def test_unchanged_green_criteria(self):
        from seed.s6_precise_exam import checks
        totals = {"semilla": {"levels": 100, "score": 1}, "echo": {"levels": 105, "score": 1},
                  "fijo": {"levels": 104}, "sinfiltro": {"levels": 104}}
        dev = {"echo": {"levels": 10, "score": 1}, "semilla": {"levels": 10, "score": 1}}
        self.assertTrue(all(checks(totals, dev, True).values()))
        totals["fijo"]["levels"] = 105
        self.assertFalse(checks(totals, dev, True)["B2"])
        self.assertFalse(checks(totals, dev, False)["B5"])

    def test_raw_accumulates_even_rejected_echo_proposals(self):
        saved = []
        first = {"patches": [{"when": {"reset_known": ["eq", 1]}, "set": {"HOLD": 20}}]}
        second = {"patches": [{"when": {"body_known": ["eq", 0]}, "set": {"BABBLE": 4}}]}
        def measure(*args, **kwargs):
            return {"trace_digest": "same"}
        with patch.object(s, "events", side_effect=lambda path: list(saved)), \
             patch.object(s, "journal", side_effect=lambda path, event: saved.append(event)), \
             patch.object(s.c, "measure", side_effect=measure):
            s.raw_step({"id": 0, "answer": s.canonical(first), "verdict": "V3"})
            s.raw_step({"id": 1, "answer": s.canonical(second), "verdict": "V4"})
            s.raw_step({"id": 1, "answer": s.canonical(second), "verdict": "V4"})
        self.assertEqual(len(saved), 2)
        self.assertEqual(len(saved[-1]["strategy"]["program"]["patches"]), 2)
        self.assertEqual(saved[-1]["V3"], "OMITTED")

    def test_positive_a_does_not_override_protected_regression(self):
        base_a = {"rows": [{"levels_completed": 2, "score": 1, "actions": [], "frames": [], "patch_hits": []}],
                  "levels": 2, "trace_digest": "before-A"}
        after_a = {"rows": [{"levels_completed": 4, "score": 1, "actions": [], "frames": [], "patch_hits": [1]}],
                   "levels": 4, "trace_digest": "after-A"}
        base_b = {"rows": [{"levels_completed": 4, "score": 1, "actions": [], "frames": [], "patch_hits": []}],
                  "levels": 4, "trace_digest": "before-B"}
        after_b = {"rows": [{"levels_completed": 4, "score": .9, "actions": [], "frames": [], "patch_hits": [1]}],
                   "levels": 4, "trace_digest": "after-B"}
        for result in (base_a, after_a, base_b, after_b):
            for row in result["rows"]:
                row.update(version=3, seed=0, rep=0, budget=2000)
        answer = s.canonical({"patches": [{"when": {"reset_known": ["eq", 1]}, "set": {"HOLD": 20}}]})
        with patch.object(s.c, "measure", side_effect=[after_a, after_a, after_b, after_b]):
            current, a, b, verdict = s.verify("test", answer, s.strategy(), base_a, base_b)
        self.assertEqual(verdict["verdict"], "V4")
        self.assertEqual(current, s.strategy())
        self.assertEqual(a, base_a)
        self.assertEqual(b, base_b)


if __name__ == "__main__":
    unittest.main()
