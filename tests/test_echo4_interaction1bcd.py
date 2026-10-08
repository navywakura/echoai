"""INTERACTION B/C/D native learning, adverse observations and custody checks."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.spoke import encode_event
from echoai.nexus0.loop import Agent
from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.continuity import canonical
from echoai.echo4.dream_bench import persist
from echoai.echo4.other_model import decode, context
from echoai.echo4.interaction_learning import belief, BeliefAgent, BELIEF_SOURCE
from echoai.echo4.interaction_social import SocialSession, settled
from echoai.echo4 import interaction_cases as cases
from echoai.echo4 import interaction_final as b


class Beliefs(unittest.TestCase):
    def test_integer_wsp16_uses_existing_atoms_and_namespace(self):
        packet = belief(2, 4096, (None, 0, 0))
        self.assertEqual(len(packet), 16)
        self.assertEqual(packet[:3], bytes((2, 29, 3)))
        self.assertEqual(packet[11:], bytes((9, 8, 8, 5, 5)))

    def test_unknown_and_conflicting_predictions_abstain(self):
        for columns in ((None,) * 3, (0, 1, None), (2, 0, 1)):
            self.assertEqual(belief(1, 3, columns)[15], 1)

    def test_own_resource_band_is_visible_not_peer_resource(self):
        self.assertEqual([belief(0, r, (0, 0, 0))[14] for r in (0, 1, 4, 5, 8192)], [0, 1, 4, 5, 5])

    def test_bad_belief_inputs_reject_coercions(self):
        for args in ((True, 8, (0, 0, 0)), (0, 1.0, (0, 0, 0)), (0, -1, (0, 0, 0)),
                     (0, 8, [0, 0, 0]), (0, 8, (False, 0, 0)), (0, 8, (3, 0, 0)), (0, 8, (None,))):
            with self.assertRaises(ValueError):
                belief(*args)

    def test_uses_original_turn_and_update_loop(self):
        self.assertIs(BeliefAgent.turn, Agent.turn)

    def test_prediction_cannot_acquire_factual_extract(self):
        s = SocialSession((0,), (1,))
        s.step()
        row = s.focal.cam.slot[s.focal.cam.get(s.focal.belief_packet)]
        self.assertEqual((row.has_fact, row.extract, row.source), (0, "", BELIEF_SOURCE))
        self.assertTrue(s.invariant())

    def test_capacity_failure_never_falls_back_to_slot_zero(self):
        s = SocialSession((0,), (1,))
        p = belief(0, 8, (None,) * 3)
        with patch("echoai.echo4.interaction_learning.allocate", return_value=(-1, 0)):
            with self.assertRaises(RuntimeError):
                s.focal._slot_for(p, encode_event(p)[0], "not a fact", (0,) * 6)

    def test_no_decision_before_observation(self):
        s = SocialSession((0,), (1,))
        with self.assertRaises(RuntimeError):
            s.focal.observation(Cell(0, KIND_OBJECT))

    def test_settlement_is_not_a_prediction(self):
        s = SocialSession((0,), (1,))
        s.step()
        packet = s.focal.observation(settled())
        row = s.focal.cam.slot[s.focal.cam.get(packet)]
        self.assertTrue(row.has_fact)
        self.assertEqual(row.extract, "own action settled")
        self.assertEqual(s.focal.q.q[s.focal.cam.get(packet)], [0, 0, 0])


class NativeSocial(unittest.TestCase):
    def make(self, n=30, **kw):
        return SocialSession((0, 1, 2) * (n // 3), (1, 2, 1) * (n // 3), **kw)

    def test_private_memories_and_exact_turn_budget(self):
        s = self.make()
        for _ in range(30):
            s.step()
        self.assertTrue(s.invariant())
        self.assertEqual([a.metrics.turns for a in s.all_agents], [30, 260, 250])
        for name in ("cam", "t", "q", "env"):
            self.assertEqual(len({id(getattr(a, name)) for a in s.all_agents}), 3)

    def test_pretrained_peers_are_distinct_native_greedy_policies(self):
        for swapped in (False, True):
            s = SocialSession((0, 0, 1, 1, 2, 2), (1, 2, 1, 2, 1, 2), swapped=swapped)
            preferred = ((0, 1, 2), (1, 2, 0))[::-1 if swapped else 1]
            rows = [s.step() for _ in range(6)]
            self.assertEqual([r["actions"][1] for r in rows], [preferred[r["handle"]-1][r["cue"]] for r in rows])

    def test_full_arm_uses_q_not_a_join_rule(self):
        s = SocialSession((0,), (1,))
        with patch.object(s.focal.q, "select", return_value=2) as select:
            row = s.step(greedy=True)
        self.assertTrue(select.called)
        self.assertEqual(row["actions"][0], 2)

    def test_native_reward_is_physical_net_not_private_bonus(self):
        s = SocialSession((0,), (1,), arm="always_join")
        with patch.object(s.focal.q, "update", wraps=s.focal.q.update) as own, \
                patch.object(s.partners[0].q, "update", wraps=s.partners[0].q.update) as peer:
            row = s.step()
        self.assertEqual(own.call_args.args[2], row["net"][0])
        self.assertEqual(peer.call_args.args[2], row["net"][1] + row["private_credit"])
        self.assertEqual(cases.summary([row])["joint_net"], 14)
        self.assertEqual(cases.summary([row])["private_credit_excluded"], [0, 16, 0])

    def test_forecasts_and_belief_precede_both_actions(self):
        s = self.make(3)
        original = s.focal._propose
        def proposal(*args, **kwargs):
            self.assertIsNotNone(s.observer.pending)
            self.assertIsNotNone(s.peer_models[s.active_handle-1].pending)
            self.assertIsNone(s._event)
            self.assertIsNotNone(s.focal.belief_packet)
            return original(*args, **kwargs)
        with patch.object(s.focal, "_propose", side_effect=proposal):
            s.step()

    def test_both_action_orders_and_public_replay(self):
        direct, reverse = cases.execute(71, "identity"), cases.execute(71, "identity", reverse=True)
        self.assertEqual(canonical(direct), canonical(reverse))
        self.assertTrue(all(direct["checks"].values()))

    def test_development_beats_ablations_without_using_test_seeds(self):
        result = cases.cohort((83,))
        self.assertTrue(result["passed"], result["checks"])
        self.assertGreater(result["totals"]["identity"]["focal_net"], result["totals"]["no_history"]["focal_net"])

    def test_moving_partner_does_not_refill_resources(self):
        s = SocialSession((0,) * 6, (1, 2) * 3, arm="solo", resources=(20, 20, 20))
        rows = [s.step() for _ in range(6)]
        self.assertEqual(s.ledger, [14, 11, 17])
        self.assertEqual(cases.summary(rows)["paid"], [6, 9, 3])

    def test_handle_routing_is_exact_and_does_not_relabel_actuals(self):
        s = SocialSession((0,), (2,))
        row = s.step()
        self.assertEqual(decode(bytes.fromhex(row["contexts"][0][1]))[:2], (2, 0))
        self.assertEqual(decode(bytes.fromhex(row["outcomes"][0][1]), action=True), (2, 0, row["actions"][1]))

    def test_resource_changes_do_not_disclose_other_private_q(self):
        a, c = self.make(3), self.make(3, resources=(4096, 17, 29))
        self.assertEqual(a.step()["belief"], c.step()["belief"])
        self.assertEqual(a.focal.q.q, c.focal.q.q)

    def test_native_veto_is_sticky_and_not_bypassed(self):
        s = self.make(9, arm="always_join")
        rows = [s.step(veto=(i == 0, False)) for i in range(9)]
        self.assertTrue(all(r["actions"][0] == 2 for r in rows))
        self.assertTrue(any(r["proposals"][0] == 0 for r in rows))
        self.assertTrue(any(slot.flags & SLOT_FLAG_INHIBIT for slot in s.focal.cam.slot if slot.occupied))

    def test_all_adverse_witnesses(self):
        result = cases.adverse()
        self.assertEqual(len(result["cases"]), 11)
        self.assertTrue(result["passed"], {k: v["checks"] for k, v in result["cases"].items()})


class FailClosed(unittest.TestCase):
    def test_invalid_construction(self):
        for kw in ({"arm": "oracle"}, {"swapped": 1}, {"resources": [1, 1, 1]},
                   {"resources": (1, 1, True)}, {"resources": (1, -1, 0)}, {"resources": (8193, 8, 8)}):
            with self.assertRaises(ValueError):
                SocialSession((0,), (1,), **kw)
        for schedule in ((True,), (0,), (3,), (), [1]):
            with self.assertRaises(ValueError):
                SocialSession((0,), schedule)

    def test_bad_step_is_rejected_before_memory_or_physics_mutation(self):
        s = SocialSession((0,), (1,))
        before = copy.deepcopy(vars(s.world))
        bad = ({"order": (True, 0)}, {"order": (1, 1)}, {"tracked": 1}, {"greedy": 1},
               {"outcomes": [True, True]}, {"visible": (1, True)}, {"veto": (True,)})
        for args in bad:
            with self.assertRaises(ValueError):
                s.step(**args)
            self.assertEqual(vars(s.world), before)
            self.assertEqual(s.observer.count, 0)
            self.assertIsNone(s.observer.pending)

    def test_failure_before_settlement_latches_stop(self):
        s = SocialSession((0, 0), (1, 2))
        with patch.object(s.world, "advance", side_effect=RuntimeError("physical failure")):
            with self.assertRaises(RuntimeError):
                s.step()
        self.assertTrue(s.failed and s.stopped)
        self.assertEqual(s.world.tick, 0)
        self.assertTrue(all(m.stopped for m in (s.observer, *s.peer_models)))
        with self.assertRaises(RuntimeError):
            s.step()

    def test_receipt_failure_preserves_executed_costs_without_retry(self):
        s = SocialSession((0, 0), (1, 2), arm="always_join")
        with patch.object(s.peer_models[0], "finish", side_effect=RuntimeError("receipt failure")):
            with self.assertRaises(RuntimeError):
                s.step()
        self.assertTrue(s.failed and s.stopped)
        self.assertEqual((s.world.tick, s.ledger), (1, [4093, 4093, 4096]))
        self.assertIsNone(s.observer.pending)
        with self.assertRaises(RuntimeError):
            s.step()

    def test_out_of_turn_port_cannot_execute(self):
        s = SocialSession((0,), (1,))
        with self.assertRaises(RuntimeError):
            s.focal.env.step(0)
        self.assertEqual(s.world.tick, 0)

    def test_no_partial_payment_or_free_output_at_zero(self):
        s = SocialSession((0, 0), (1, 1), arm="always_join", resources=(2, 3, 8))
        first, second = s.step(), s.step()
        self.assertEqual(first["paid"], (0, 3))
        self.assertEqual(first["output"], (0, 0))
        self.assertEqual(second["paid"], (0, 0))
        self.assertEqual(second["output"], (0, 0))

    def test_maximum_512_rounds_no_implicit_reset(self):
        s = SocialSession((0,) * 512, (1,) * 512, arm="solo")
        for _ in range(512):
            s.step()
        with self.assertRaises(RuntimeError):
            s.step()
        self.assertEqual(s.observer.count, 512)
        self.assertTrue(s.invariant())

    def test_own_memory_conflict_marks_entire_belief_unknown(self):
        s = SocialSession((0,) * 90, (1,) * 90)
        for t in range(72):
            s.step(greedy=t >= 48)
        s.step(greedy=True, veto=(False, True))
        row = s.step(greedy=True)
        slot = s.focal.cam.get(context(1, 0))
        self.assertTrue(any(s.focal.t.alt_n[slot]))
        self.assertEqual(bytes.fromhex(row["belief"])[15], 0)


class Custody(unittest.TestCase):
    def test_parent_is_a_not_an_invented_green(self):
        self.assertTrue(b.parent())
        self.assertEqual(len(b.a.sources()), 104)
        self.assertEqual(len(b.sources()), 110)

    def test_development_and_holdouts_disjoint(self):
        self.assertEqual(len(set(cases.DEVELOPMENT + cases.COHORTS[0] + cases.COHORTS[1])), 19)
        self.assertEqual((cases.FORMATION, cases.ROUNDS, cases.MARGIN), (288, 480, 32))

    def test_runtime_has_no_float_constants_or_second_turn_loop(self):
        for name in ("interaction_learning.py", "interaction_social.py"):
            tree = ast.parse((b.ROOT / "echo4" / name).read_text())
            self.assertFalse(any(isinstance(n, ast.Constant) and type(n.value) is float for n in ast.walk(tree)))
            self.assertFalse(any(isinstance(n, ast.FunctionDef) and n.name == "turn" for n in ast.walk(tree)))

    def test_missing_evidence_cannot_grant_green(self):
        with tempfile.TemporaryDirectory() as temp:
            receipt = b.verify(Path(temp))
        self.assertFalse(receipt["valid"])
        self.assertFalse(receipt["interaction1_green"])

    def test_bad_report_digest_rejected_before_reexecution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            persist(path, "report.json", {"schema": b.SCHEMA, "reproduction_sha256": "0" * 64}, False)
            with patch.object(b, "campaign", side_effect=AssertionError("must not execute")):
                self.assertFalse(b.verify(path)["valid"])

    def test_tampered_artifact_source_and_parent_rejected(self):
        for mutant in ("artifact", "source", "parent", "path", "missing"):
            with self.subTest(mutant=mutant), tempfile.TemporaryDirectory() as temp:
                path = Path(temp)
                files = {name: persist(path, name, {"value": 1}, False) for name in
                         ("lock.json", "b-development.json", "c-limits.json", "c-tests.json")}
                report = {"schema": b.SCHEMA, "sources": {"fixed": "hash"}, "parent": {"fixed": "hash"},
                          "d_opened": False, "artifacts": files}
                if mutant == "artifact":
                    files["lock.json"] = "0" * 64
                elif mutant == "path":
                    files["../outside.json"] = files.pop("lock.json")
                elif mutant == "missing":
                    files.pop("lock.json")
                else:
                    report["sources" if mutant == "source" else "parent"] = {"modified": "hash"}
                report["reproduction_sha256"] = b.a.sha(report)
                persist(path, "report.json", report, False)
                with patch.object(b, "sources", return_value={"fixed": "hash"}), \
                        patch.object(b, "parent", return_value={"fixed": "hash"}), \
                        patch.object(b, "campaign", side_effect=AssertionError("must not execute")):
                    self.assertFalse(b.verify(path)["valid"])

    def test_duplicate_json_keys_and_floats_rejected(self):
        for raw in (b'{"schema":1,"schema":2}', b'{"value":1.5}', b'{"value":NaN}'):
            with patch.object(Path, "read_bytes", return_value=raw), \
                    patch.object(b, "campaign", side_effect=AssertionError("must not execute")):
                self.assertFalse(b.verify(Path("unused"))["valid"])

    def test_audit_cannot_promote_report_without_reconstruction(self):
        with patch.object(b, "check_header", return_value={"reproduction_sha256": "x"}), \
                patch.object(b, "campaign", side_effect=ValueError("reconstruction mismatch")):
            receipt = b.verify(Path("unused"))
        self.assertFalse(receipt["valid"])
        self.assertFalse(receipt["interaction1_green"])


if __name__ == "__main__":
    unittest.main()
