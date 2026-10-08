"""SITUATE-2: claim classification, belief firewall, profile, dream selection."""
import json
import unittest

from echoai.echo4 import situate2 as Z
from echoai.echo4 import situate2_bench as B


def receipt(claims):
    return {"request": {}, "transport_error": "", "model_sha256": "x",
            "raw_response": json.dumps({"content": json.dumps({"claims": claims})})}


class Firewall(unittest.TestCase):
    def setUp(self):
        _, self.me = B.build_me(5)

    def test_only_supported_claims_are_believed(self):
        rows = Z.classify(self.me, [("is_human", True), ("is_program", True), ("is_conscious", True),
                                    ("is_alive", False), ("has_gpu", True)])
        status = {r["atom"]: r["status"] for r in rows}
        self.assertEqual(status["is_human"], Z.CONTRADICTED)
        self.assertEqual(status["is_program"], Z.SUPPORTED)
        self.assertEqual((status["is_conscious"], status["is_alive"]), (Z.UNVERIFIABLE, Z.UNVERIFIABLE))
        self.assertEqual(Z.belief(rows), [("is_program", True)])

    def test_blind_agent_believes_nothing(self):
        _, blind = B.build_me(5, sensors=False)
        rows = Z.classify(blind, [("is_program", True), ("is_human", False)])
        self.assertTrue(all(r["status"] == Z.UNKNOWN for r in rows))
        self.assertEqual(Z.belief(rows), [])

    def test_strict_parsing_and_down_llm(self):
        self.assertEqual(B.claims_of(receipt([{"atom": "is_program", "value": True}]))[0], [("is_program", True)])
        for bad in ([{"atom": "is_god", "value": True}], [{"atom": "is_program", "value": "yes"}], []):
            self.assertTrue(B.claims_of(receipt(bad))[1].startswith("rejected"))
        down = B.down_receipt({"x": 1})
        self.assertTrue(down["transport_error"])
        self.assertTrue(B.claims_of(down)[1].startswith("rejected:transport"))

    def test_belief_is_hypothesis(self):
        out = B.interpret(self.me, receipt([{"atom": "is_program", "value": True}]), 9)
        rows = [s for s in self.me.cam.slot if s.occupied and s.source == Z.BELIEF_SOURCE]
        self.assertEqual(out["belief"], [("is_program", True)])
        self.assertTrue(rows and all(not s.has_fact and not s.extract for s in rows))


class ProfileAndDream(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traces = Z.reference_traces(5, rounds=96)

    def test_profile_never_verdict_and_trivials_checked(self):
        p = Z.profile(self.traces)
        self.assertIsNone(p["verdict"])
        for r in p["indicators"]:
            if "passes" in r:
                self.assertEqual(set(r["passes"]), set(Z.REFERENCE))
                if any(v for n, v in r["passes"].items() if n.startswith("trivial")):
                    self.assertEqual(r["status"], "no discrimina")

    def test_selection_never_sees_echo_full(self):
        without = {k: v for k, v in self.traces.items() if k != "echo_full"}
        accepted, sel = Z.select(("learning", ">", 5), without)
        self.assertNotIn("echo_full", sel)
        self.assertEqual(Z.select(("learning", ">", 5), self.traces), (accepted, sel))

    def test_trivial_has_no_model(self):
        self.assertEqual(Z.m_self_model(self.traces["trivial_random"]), 0)
        self.assertEqual(self.traces["trivial_constant"]["rows"], [])


if __name__ == "__main__":
    unittest.main()
