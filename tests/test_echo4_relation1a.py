"""RELATION-A observed history, isolation, limits and reconstructive custody."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.core.wsp import pack
from echoai.echo4.continuity import canonical
from echoai.echo4.dream_bench import persist
from echoai.echo4.other_model import context, outcome
from echoai.echo4.relation_memory import RelationMemory, SOURCE, episode_key, replay
from echoai.echo4.relation_session import RelationSession
from echoai.echo4.interaction_social import SocialSession
from echoai.echo4 import relation_bench as b


def observed(memory, tick, peer=1, own=0, remote=0, cue=0):
    contexts = (context(0, cue), context(peer, cue) if peer else None)
    outcomes = (outcome(0, cue, own), outcome(peer, cue, remote) if peer and remote is not None else None)
    paid = (3 if cue != 1 else 5) if own == 0 else int(own == 1)
    output = (10, 6, 0)[cue] if own == remote == 0 else 5 if own == 1 else 0
    return memory.append(tick, contexts, outcomes, paid, output)


class EpisodicHistory(unittest.TestCase):
    def test_wsp16_no_tick_wrap_or_affect_hijack(self):
        for tick in (0, 255, 256, 511):
            raw = episode_key(tick, 2)
            self.assertEqual(len(raw), 16)
            self.assertEqual(raw[:4], bytes((2, 19, 3, 9)))
            self.assertEqual(raw[4:10], bytes(6))
            self.assertEqual((raw[13]-32)*256+raw[15], tick)
        self.assertNotEqual(episode_key(255, 1), episode_key(511, 1))

    def test_wsp_key_rejects_invalid_or_coerced_values(self):
        for tick, peer in ((True, 1), (1.0, 1), (-1, 1), (512, 1), (0, False), (0, 3)):
            with self.assertRaises(ValueError):
                episode_key(tick, peer)

    def test_history_and_pair_links_live_in_cam_not_an_episode_list(self):
        memory = RelationMemory(Cam())
        keys = [observed(memory, 2, 1), observed(memory, 5, 2), observed(memory, 9, 1)]
        rows = memory.history()
        self.assertEqual([r["wsp"] for r in rows], [k.hex() for k in keys])
        self.assertEqual(rows[2]["previous"], keys[1].hex())
        self.assertEqual(rows[2]["pair_previous"], keys[0].hex())
        self.assertEqual([r["observation"]["tick"] for r in memory.history(1)], [2, 9])
        self.assertEqual(set(vars(memory)), {"cam", "count", "last_tick", "head", "peer_heads", "stopped"})
        self.assertTrue(memory.invariant())

    def test_unidentified_encounters_do_not_invent_a_dyad(self):
        memory = RelationMemory(Cam())
        observed(memory, 0, peer=0, own=1, remote=None)
        observed(memory, 1, peer=0, own=1, remote=None)
        self.assertEqual(memory.summary(0)["encounters"], 2)
        self.assertEqual(memory.summary(1)["encounters"], 0)
        self.assertTrue(all(r["pair_previous"] is None for r in memory.history(0)))
        self.assertEqual(memory.peer_heads[0], -1)

    def test_missing_action_remains_unknown_not_wait_or_agreement(self):
        memory = RelationMemory(Cam())
        observed(memory, 0, remote=None)
        summary = memory.summary(1)
        self.assertEqual(summary["peer_action_unknown"], 1)
        self.assertEqual(summary["observed_joint_attempts"], 0)
        self.assertIsNone(memory.history()[0]["observation"]["outcomes"][1])

    def test_joint_attempt_is_not_joint_success(self):
        memory = RelationMemory(Cam())
        observed(memory, 0, cue=2)
        summary = memory.summary(1)
        self.assertEqual(summary["observed_joint_attempts"], 1)
        self.assertEqual(summary["confirmed_joint_successes"], 0)
        self.assertEqual(summary["net"], -3)

    def test_physical_output_without_peer_receipt_not_confirmed_shared_success(self):
        memory = RelationMemory(Cam())
        memory.append(0, (context(0, 0), context(1, 0)), (outcome(0, 0, 0), None), 3, 10)
        self.assertEqual(memory.summary(1)["net"], 7)
        self.assertEqual(memory.summary(1)["confirmed_joint_successes"], 0)

    def test_conflicting_executions_kept_not_erased_or_renamed(self):
        memory = RelationMemory(Cam())
        observed(memory, 0, remote=0)
        observed(memory, 1, remote=2)
        self.assertEqual(memory.count, 2)
        self.assertEqual(memory.summary(1)["confirmed_joint_successes"], 1)
        self.assertEqual(memory.summary(1)["net"], 4)
        self.assertEqual(memory.cam.destroyed, 0)

    def test_different_order_same_totals_different_history_digest(self):
        a, c = RelationMemory(Cam()), RelationMemory(Cam())
        for tick, remote in enumerate((0, 2)):
            observed(a, tick, remote=remote)
            observed(c, tick, remote=2-remote)
        self.assertEqual(a.summary(1), c.summary(1))
        self.assertNotEqual(a.digest(), c.digest())

    def test_summaries_are_derived_not_written_as_facts(self):
        memory = RelationMemory(Cam())
        observed(memory, 0)
        used, digest = memory.cam.used, memory.digest()
        result = memory.summary(1)
        result["net"] = 10000
        self.assertEqual(memory.cam.used, used)
        self.assertEqual(memory.digest(), digest)
        self.assertEqual(memory.summary(1)["net"], 7)

    def test_views_are_copies_not_mutable_memory_aliases(self):
        memory = RelationMemory(Cam())
        observed(memory, 0)
        row = memory.history()[0]
        row["observation"]["paid"] = 0
        self.assertEqual(memory.history()[0]["observation"]["paid"], 3)

    def test_exact_replay_with_different_cam_addresses(self):
        cam = Cam()
        raw = episode_key(0, 1)
        # Deliberately occupy the original key's hash bucket with an unrelated row.
        with patch.object(cam, "_probe", return_value=cam._probe(raw)):
            cam.put(pack(src=1), 1, 0)
        memory = RelationMemory(cam)
        observed(memory, 0)
        result = replay([e["observation"] for e in memory.history()])
        self.assertEqual(result["memory_sha256"], memory.digest())
        self.assertTrue(result["valid"])

    def test_two_views_need_not_know_the_same_thing(self):
        s = RelationSession((0,), (1,), arm="always_join")
        s.step(outcomes=(False, True))
        self.assertEqual(s.relations[0].summary(1)["confirmed_joint_successes"], 0)
        self.assertEqual(s.relations[1].summary(1)["confirmed_joint_successes"], 1)
        self.assertIsNot(s.relations[0].cam, s.relations[1].cam)


class Integrity(unittest.TestCase):
    def test_invalid_receipt_rejected_before_mutation(self):
        memory = RelationMemory(Cam())
        good = [0, (context(0, 0), context(1, 0)), (outcome(0, 0, 0), outcome(1, 0, 0)), 3, 10]
        variants = []
        for index, value in ((0, True), (3, 3.0), (4, 20), (3, 0),
                             (1, (context(0, 0), context(0, 0))),
                             (2, (outcome(0, 1, 0), outcome(1, 0, 0))),
                             (2, (outcome(0, 0, 0), outcome(2, 0, 0))),
                             (2, (outcome(0, 0, 0), outcome(1, 0, 1))),
                             (2, (None, outcome(1, 0, 0))),
                             (1, (context(0, 0), None)), (1, [context(0, 0), context(1, 0)])):
            args = good.copy()
            args[index] = value
            variants.append(args)
        for args in variants:
            with self.assertRaises(ValueError):
                memory.append(*args)
            self.assertEqual((memory.count, memory.cam.used), (0, 0))

    def test_unknown_own_cue_and_free_solo_output_rejected(self):
        m = RelationMemory(Cam())
        with self.assertRaises(ValueError):
            m.append(0, (context(0, None), None), (outcome(0, None, 2), None), 0, 0)
        with self.assertRaises(ValueError):
            m.append(0, (context(0, 0), None), (outcome(0, 0, 1), None), 0, 5)

    def test_duplicate_and_backwards_ticks_do_not_overwrite(self):
        memory = RelationMemory(Cam())
        observed(memory, 5)
        before = memory.digest()
        for tick in (5, 4):
            with self.assertRaises(ValueError):
                observed(memory, tick)
            self.assertEqual(memory.digest(), before)

    def test_capacity_failure_has_no_fallback_or_partial_metadata(self):
        memory = RelationMemory(Cam())
        before = memory.digest()
        with patch("echoai.echo4.relation_memory.allocate", return_value=(-1, "full")):
            with self.assertRaises(RuntimeError):
                observed(memory, 0)
        self.assertEqual(memory.digest(), before)

    def test_cannot_restart_existing_journal_and_lose_its_heads(self):
        memory = RelationMemory(Cam())
        observed(memory, 0)
        with self.assertRaises(ValueError):
            RelationMemory(memory.cam)

    def test_exact_512_and_high_tick_boundary(self):
        memory = RelationMemory(Cam())
        for tick in range(512):
            observed(memory, tick, peer=1 + tick % 2)
        self.assertEqual(len(memory.history()), 512)
        self.assertEqual(memory.summary(1)["encounters"], 256)
        self.assertEqual(memory.summary(2)["encounters"], 256)
        self.assertTrue(memory.invariant())
        with self.assertRaises(RuntimeError):
            observed(memory, 512)

    def test_stop_latched_without_erasing_history(self):
        memory = RelationMemory(Cam())
        observed(memory, 0)
        history = memory.history()
        memory.stop()
        with self.assertRaises(RuntimeError):
            observed(memory, 1)
        self.assertEqual(memory.history(), history)
        self.assertTrue(memory.invariant())

    def test_malformed_transcript_rejected(self):
        for records in ({}, [None], [{}], [{"tick": 0, "contexts": [], "outcomes": [], "paid": 0, "output": 0}], [None]*513):
            with self.assertRaises(ValueError):
                replay(records)

    def test_corrupt_metadata_and_provenance_detected(self):
        for field, value in (("has_fact", 0), ("source", "untrusted"), ("extract", "{}"), ("see", [999])):
            memory = RelationMemory(Cam())
            observed(memory, 0)
            setattr(memory.cam.slot[memory.head], field, value)
            self.assertFalse(memory.invariant())

    def test_corrupt_link_order_detected(self):
        memory = RelationMemory(Cam())
        raw = observed(memory, 0)
        entry = memory.history()[0]
        entry.pop("wsp")
        entry["previous"] = raw.hex()
        memory.cam.slot[memory.head].extract = canonical(entry).decode("ascii")
        self.assertFalse(memory.invariant())

    def test_bad_head_types_not_coerced(self):
        for field, value in (("head", False), ("head", -2), ("count", 1.0), ("last_tick", True), ("peer_heads", [1]), ("stopped", 1)):
            memory = RelationMemory(Cam())
            setattr(memory, field, value)
            self.assertFalse(memory.invariant())


class NativeWiring(unittest.TestCase):
    def test_order_parity_baseline_and_replay(self):
        result = b.native(113)
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(sum(len(m["history"]) for m in result["memories"]), 288)

    def test_partial_observation_does_not_leak_executor_identity(self):
        result = b.partial()
        self.assertTrue(result["passed"], result["checks"])
        unidentified = [e for e in result["memories"][0]["history"] if bytes.fromhex(e["wsp"])[14] == 0]
        self.assertTrue(all(e["observation"]["contexts"][1] is None for e in unidentified))

    def test_episode_written_after_native_execution_and_receipts(self):
        session = RelationSession((0,), (1,))
        original = session.relations[0].append
        def append(*args):
            self.assertEqual(session.world.tick, 1)
            self.assertTrue(all(m.pending is None for m in session.models))
            self.assertEqual(session.focal.metrics.turns, 1)
            self.assertEqual(session.partners[0].metrics.turns, 241)
            return original(*args)
        with patch.object(session.relations[0], "append", side_effect=append):
            session.step()

    def test_private_credits_excluded_and_no_private_fields_in_memory(self):
        session = RelationSession((0,), (1,), arm="always_join")
        frame = session.step()
        self.assertEqual(frame["private_credit"], 16)
        for index in (0, 1):
            memory = session.relations[index]
            obs = memory.history()[0]["observation"]
            self.assertEqual(set(obs), {"tick", "contexts", "outcomes", "paid", "output"})
            self.assertEqual(memory.summary(1)["net"], 7)

    def test_gate_outcome_not_proposal_is_recorded(self):
        s = RelationSession((0,), (1,), arm="always_join")
        row = s.step(veto=(True, False))
        self.assertEqual(row["proposals"][0], 0)
        self.assertEqual(row["actions"][0], 2)
        self.assertEqual(s.relations[0].summary(1)["observed_joint_attempts"], 0)

    def test_recording_failure_stops_without_erasing_executed_costs(self):
        session = RelationSession((0, 0), (1, 1), arm="always_join")
        with patch.object(session.relations[1], "append", side_effect=RuntimeError("full")):
            with self.assertRaises(RuntimeError):
                session.step()
        self.assertTrue(session.failed and session.stopped)
        self.assertEqual(session.ledger, [4093, 4093, 4096])
        self.assertEqual([m.count for m in session.relations], [1, 0, 0])
        self.assertTrue(all(m.stopped for m in session.relations))
        with self.assertRaises(RuntimeError):
            session.step()

    def test_native_receipt_failure_does_not_invent_relational_confirmation(self):
        session = RelationSession((0,), (1,), arm="always_join")
        with patch.object(session.peer_models[0], "finish", side_effect=RuntimeError("missing receipt")):
            with self.assertRaises(RuntimeError):
                session.step()
        self.assertTrue(session.failed and session.stopped)
        self.assertEqual(session.ledger, [4093, 4093, 4096])
        self.assertEqual([m.count for m in session.relations], [0, 0, 0])
        self.assertTrue(all(m.stopped for m in session.relations))

    def test_invalid_call_does_not_stop_or_change_memory(self):
        session = RelationSession((0,), (1,))
        before = [m.digest() for m in session.relations]
        with self.assertRaises(ValueError):
            session.step(greedy=1)
        self.assertFalse(session.stopped)
        self.assertEqual([m.digest() for m in session.relations], before)


class Audit(unittest.TestCase):
    def test_parent_green_bound_and_110_sources_unchanged(self):
        self.assertEqual(len(b.parent_module.sources()), 110)
        self.assertEqual(len(b.sources()), 115)
        self.assertTrue(b.parent())

    def test_no_second_agent_turn_or_float_runtime(self):
        for name in ("relation_memory.py", "relation_session.py"):
            tree = ast.parse((b.ROOT / "echo4" / name).read_text())
            self.assertFalse(any(isinstance(n, ast.FunctionDef) and n.name == "turn" for n in ast.walk(tree)))
            self.assertFalse(any(isinstance(n, ast.Constant) and type(n.value) is float for n in ast.walk(tree)))
        self.assertIs(RelationSession._execute, SocialSession._execute)

    def test_missing_evidence_never_grants_phase_green(self):
        with tempfile.TemporaryDirectory() as temp:
            result = b.verify(Path(temp))
        self.assertFalse(result["valid"])
        self.assertFalse(result["phase_a_valid"])
        self.assertFalse(result["relation1_green"])

    def test_mutated_sources_artifacts_and_report_rejected(self):
        for mutant in ("sources", "parent", "artifact", "path", "digest"):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)
                artifacts = {name: persist(path, name, {}, False) for name in
                             ("lock.json", "native.json", "partial.json", "tests.json")}
                report = {"schema": b.SCHEMA, "sources": {"fixed": "hash"}, "parent": {"fixed": "hash"}, "artifacts": artifacts}
                if mutant in ("sources", "parent"):
                    report[mutant] = {"changed": "hash"}
                elif mutant == "artifact":
                    artifacts["native.json"] = "0" * 64
                elif mutant == "path":
                    artifacts["../elsewhere"] = artifacts.pop("native.json")
                report["reproduction_sha256"] = "0" * 64 if mutant == "digest" else b.sha(report)
                persist(path, "report.json", report, False)
                with patch.object(b, "sources", return_value={"fixed": "hash"}), \
                        patch.object(b, "parent", return_value={"fixed": "hash"}), \
                        patch.object(b, "campaign", side_effect=AssertionError("must reject before executing")):
                    self.assertFalse(b.verify(path)["valid"])


if __name__ == "__main__":
    unittest.main()
