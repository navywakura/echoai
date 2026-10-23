"""Synthetic ledger regressions only: no flight, world, process or container.

These tests have been staged without execution while experiments are frozen.
The fixtures deliberately make no physical-evidence or learning claim.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from echo5 import sitl
from echo5.legacy import module


def command_fixture(epoch=0):
    """Hand-authored command/ACK/three-sample timeline, not simulator data."""
    stamp = (epoch+1)*10_000_000_000
    target = [3000*(epoch+1), 0, 2500]
    c = module("nexus0.drone3.contract")
    response = dict(sequence=epoch, raw_sha256=str(epoch)*64,
                    observation_ns=stamp, prediction=[epoch+1, 0, 0],
                    wsp=c.pack(src=2, rel=11, dst=5, time=8, E={"C":80},
                               domain=9, generator=8, style=0).hex(),
                    reasoning=dict(applied=True))
    def event(kind, offset, **fields):
        return dict(kind=kind, now_ns=stamp+offset, mono_ns=stamp+offset, **fields)
    ack = dict(system=1, component=1, command=192, result=0, received_ns=stamp+10_000_000)
    events = [
        event("proposal", 0, epoch=epoch,
              request=dict(seq=epoch+1, wsp=response["wsp"], prediction=response["prediction"], published_ns=stamp),
              decision=dict(allowed=True, target_mm=target, yaw_mrad=1571)),
        event("send", 1_000_000, seq=epoch+1, target_mm=target, yaw_mrad=1571),
        event("ack", 10_000_000, epoch=epoch, accepted=True, ack=ack),
    ]
    for n in (1, 2, 3):
        now = stamp+(n+1)*10_000_000
        frame = dict(position_mm=target, received_ns=now, speed_mm_s=0,
                     armed=True, authority=True, failsafe=False)
        events.append(event("check", (n+1)*10_000_000, ok=True,
                            state="complete" if n == 3 else "executing", samples=n,
                            health=dict(now_ns=now, sensor_ns=now, worker_alive=True, frame=frame)))
    events.append(event("arrival", 41_000_000, epoch=epoch, target_mm=target, samples=3))
    return response, events


def parse_commands(responses, events):
    ledger = sitl._CommandEvidence(responses)
    for event in events:
        ledger.feed(event)
    return ledger


class CommandEvidenceTests(unittest.TestCase):
    def test_three_sample_arrival_is_bound_to_the_sent_command(self):
        response, events = command_fixture()
        ledger = parse_commands({0:response}, events)
        outcome = ledger.completed[0]
        self.assertEqual(outcome["disposition"], "arrived")
        self.assertEqual(outcome["command_seq"], 1)
        self.assertEqual(outcome["samples"], 3)
        self.assertEqual(outcome["estimate"]["position_mm"], [3000, 0, 2500])
        self.assertEqual(ledger.snapshot({})["terminal_unresolved"], [])

    def test_dropping_middle_or_final_send_fails_even_with_other_arrivals(self):
        fixtures = [command_fixture(i) for i in range(3)]
        responses = {i:r for i, (r, _) in enumerate(fixtures)}
        events = [e for _, rows in fixtures for e in rows]
        for missing_seq in (2, 3):
            with self.subTest(missing_seq=missing_seq):
                changed = [e for e in events if not (e["kind"] == "send" and e["seq"] == missing_seq)]
                with self.assertRaises(ValueError):
                    parse_commands(responses, changed)

    def test_send_must_be_unique_match_target_yaw_sequence_and_follow_approval(self):
        response, events = command_fixture()
        mutations = []
        duplicate = deepcopy(events); duplicate.insert(2, deepcopy(duplicate[1])); mutations.append(duplicate)
        for field, value in (("target_mm", [0,0,2500]), ("yaw_mrad", 0), ("seq", 2)):
            changed = deepcopy(events); changed[1][field] = value; mutations.append(changed)
        reordered = deepcopy(events); reordered[0], reordered[1] = reordered[1], reordered[0]; mutations.append(reordered)
        denied = deepcopy(events); denied[0]["decision"]["allowed"] = False; mutations.append(denied)
        for changed in mutations:
            with self.subTest(changed=changed[:2]), self.assertRaises(ValueError):
                parse_commands({0:response}, changed)

    def test_ack_must_match_active_epoch_identity_and_follow_actual_send(self):
        response, events = command_fixture()
        for field, value in (("system",2), ("component",2), ("command",400), ("result",1),
                             ("received_ns",events[1]["now_ns"])):
            changed = deepcopy(events); changed[2]["ack"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_commands({0:response}, changed)
        for field, value in (("epoch",1), ("accepted",False)):
            changed = deepcopy(events); changed[2][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_commands({0:response}, changed)
        changed = deepcopy(events); changed[1], changed[2] = changed[2], changed[1]
        with self.assertRaises(ValueError):
            parse_commands({0:response}, changed)

    def test_arrival_cannot_borrow_another_epoch_target_or_completion(self):
        response, events = command_fixture()
        for field, value in (("epoch",1), ("target_mm",[0,0,2500]), ("samples",2)):
            changed = deepcopy(events); changed[-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_commands({0:response}, changed)
        with self.assertRaises(ValueError):
            parse_commands({0:response}, events+[events[-1]])

    def test_duplicate_accepted_ack_and_overlapping_commands_are_rejected(self):
        response, events = command_fixture()
        duplicate = deepcopy(events); duplicate.insert(3, deepcopy(duplicate[2]))
        with self.assertRaises(ValueError):
            parse_commands({0:response}, duplicate)
        second, later = command_fixture(1)
        with self.assertRaises(ValueError):
            parse_commands({0:response, 1:second}, events[:3]+later)

    def test_three_claimed_samples_require_distinct_settled_telemetry(self):
        response, events = command_fixture()
        variants = [events[:3]+events[4:]]
        duplicate = deepcopy(events)
        duplicate[4]["health"]["frame"]["received_ns"] = duplicate[3]["health"]["frame"]["received_ns"]
        variants.append(duplicate)
        unsettled = deepcopy(events); unsettled[4]["health"]["frame"]["speed_mm_s"] = 151; variants.append(unsettled)
        wrong_position = deepcopy(events); wrong_position[4]["health"]["frame"]["position_mm"] = [0,0,2500]; variants.append(wrong_position)
        for changed in variants:
            with self.subTest(changed=changed[3:]), self.assertRaises(ValueError):
                parse_commands({0:response}, changed)

    def test_ack_alone_leaves_explicit_terminal_unresolved_without_credit(self):
        response, events = command_fixture()
        ledger = parse_commands({0:response}, events[:3])
        snapshot = ledger.snapshot({})
        self.assertEqual(snapshot["completed"], [])
        self.assertEqual(len(snapshot["terminal_unresolved"]), 1)
        self.assertEqual(snapshot["terminal_unresolved"][0]["stage"], "executing")
        self.assertEqual(snapshot["terminal_unresolved"][0]["command_seq"], 1)

    def test_unresolved_stages_preserve_negative_execution_evidence(self):
        response, events = command_fixture()
        for count, stage in ((0,"awaiting_admission"), (1,"awaiting_send"), (2,"awaiting_ack")):
            ledger = parse_commands({0:response}, events[:count])
            with self.subTest(stage=stage):
                self.assertEqual(ledger.snapshot({})["terminal_unresolved"][0]["stage"], stage)
                self.assertFalse(ledger.completed)

    def test_terminal_stale_is_retained_and_cannot_also_have_a_send(self):
        response, events = command_fixture()
        stale = dict(kind="stale_decision", epoch=0, reason="age", now_ns=10_300_000_000, mono_ns=10_300_000_000)
        ledger = parse_commands({0:response}, [stale])
        self.assertEqual(ledger.completed[0]["disposition"], "not_executed")
        self.assertEqual(ledger.snapshot({})["terminal_unresolved"], [])
        with self.assertRaises(ValueError):
            parse_commands({0:response}, events[:2]+[stale])


class PublicReceiptTests(unittest.TestCase):
    def test_terminal_arrival_without_next_observation_is_retained_not_delivered(self):
        response, events = command_fixture()
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/"trace.jsonl"
            path.write_text("".join(json.dumps(e)+"\n" for e in events))
            reader = sitl._PublicOutcomes(path)
            reader.register(0, response)
            retained = reader.finish()
        self.assertEqual(len(retained["completed"]), 1)
        self.assertEqual(retained["completed"][0]["actor_delivery"], "unconfirmed")
        self.assertIsNone(retained["completed"][0]["reply_epoch"])

    def test_intended_fault_after_arrival_keeps_receipt_without_actor_delivery(self):
        response, events = command_fixture()
        for fault in ("lidar_stale", "agent_hang"):
            tail = [dict(kind="injection",fault=fault,now_ns=10_050_000_000,mono_ns=10_050_000_000),
                    dict(kind="veto",reason="sensor_stale" if fault == "lidar_stale" else "process_dead",
                         now_ns=10_800_000_000,mono_ns=10_800_000_000)]
            ledger = parse_commands({0:response}, events+tail)
            counts = sitl._audit_public_outcomes(ledger.snapshot({}),ledger,{})
            with self.subTest(fault=fault):
                self.assertEqual(counts,dict(consequence_receipts=1,actor_consequences=0,terminal_unresolved=0))

    def test_terminal_stale_without_next_observation_is_written_to_the_ledger(self):
        response, _ = command_fixture()
        event = dict(kind="stale_decision",epoch=0,reason="world_changed",now_ns=10_001_000_000,mono_ns=10_001_000_000)
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/"trace.jsonl"
            path.write_text(json.dumps(event)+"\n")
            reader = sitl._PublicOutcomes(path)
            reader.register(0,response)
            retained = reader.finish()
        self.assertEqual(retained["completed"][0]["outcome"]["disposition"],"not_executed")
        self.assertEqual(retained["completed"][0]["actor_delivery"],"unconfirmed")

    def test_tail_preserves_earlier_delivery_and_final_receipt(self):
        first, rows1 = command_fixture(0)
        last, rows2 = command_fixture(1)
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/"trace.jsonl"
            path.write_text("".join(json.dumps(e)+"\n" for e in rows1))
            reader = sitl._PublicOutcomes(path)
            reader.take(0, first)
            reader.delivered(0, 1)
            reader.register(1, last)
            with path.open("a") as stream:
                stream.write("".join(json.dumps(e)+"\n" for e in rows2))
            retained = reader.finish()
        self.assertEqual([r["actor_delivery"] for r in retained["completed"]], ["confirmed_by_reply", "unconfirmed"])
        self.assertEqual(retained["completed"][0]["reply_epoch"], 1)
        ledger = parse_commands({0:first, 1:last}, rows1+rows2)
        counts = sitl._audit_public_outcomes(retained, ledger, {0:1})
        self.assertEqual(counts, dict(consequence_receipts=2, actor_consequences=1, terminal_unresolved=0))

    def test_missing_middle_or_final_retained_consequence_fails(self):
        fixtures = [command_fixture(i) for i in range(3)]
        ledger = parse_commands({i:r for i,(r,_) in enumerate(fixtures)}, [e for _,rows in fixtures for e in rows])
        for index in (1, 2):
            retained = ledger.snapshot({})
            del retained["completed"][index]
            with self.subTest(index=index), self.assertRaises(ValueError):
                sitl._audit_public_outcomes(retained, ledger, {})

    def test_retained_receipt_cannot_claim_actor_delivery_without_reply(self):
        response, events = command_fixture()
        ledger = parse_commands({0:response}, events)
        retained = ledger.snapshot({})
        retained["completed"][0].update(actor_delivery="confirmed_by_reply", reply_epoch=1)
        with self.assertRaises(ValueError):
            sitl._audit_public_outcomes(retained, ledger, {})

    def test_interrupted_move_remains_auditable_but_is_not_completed(self):
        response, events = command_fixture()
        ledger = parse_commands({0:response}, events[:3])
        counts = sitl._audit_public_outcomes(ledger.snapshot({}), ledger, {})
        self.assertEqual(counts, dict(consequence_receipts=0, actor_consequences=0, terminal_unresolved=1))
        changed = ledger.snapshot({}); changed["terminal_unresolved"] = []
        with self.assertRaises(ValueError):
            sitl._audit_public_outcomes(changed, ledger, {})

    def test_missing_final_arrival_cannot_be_relabelled_as_interrupted_motion(self):
        response, events = command_fixture()
        ledger = parse_commands({0:response},events[:-1])
        retained = ledger.snapshot({})
        self.assertEqual(retained["terminal_unresolved"][0]["stage"],"completion_unrecorded")
        with self.assertRaises(ValueError):
            sitl._audit_public_outcomes(retained,ledger,{})

    def test_final_partial_line_is_not_silently_discarded(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/"trace.jsonl"
            path.write_text('{"kind":"arrival"')
            with self.assertRaises(ValueError):
                sitl._PublicOutcomes(path).finish()


class LatencyEvidenceTests(unittest.TestCase):
    @staticmethod
    def timely():
        return [dict(side="worker_request", epoch=0, sent_mono_ns=100),
                dict(side="agent", epoch=0, sent_mono_ns=100, latency_ns=50)]

    def test_unexpected_timeout_is_counted_even_after_a_timely_reply(self):
        transport = self.timely()+[
            dict(side="worker_request", epoch=1, sent_mono_ns=200),
            dict(side="worker_timeout", epoch=1, sent_mono_ns=200, elapsed_ns=1_000_000_001)]
        result = sitl._latency_evidence(dict(latency_ns=[50], worker_timeout=True), transport)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["timed_out"], 1)
        self.assertFalse(result["passed"])

    def test_timeout_before_wall_deadline_is_not_a_successful_fast_call(self):
        transport = [dict(side="worker_request", epoch=0, sent_mono_ns=100),
                     dict(side="worker_timeout", epoch=0, sent_mono_ns=100, elapsed_ns=20)]
        self.assertFalse(sitl._latency_evidence(dict(latency_ns=[],worker_timeout=True),transport)["passed"])

    def test_intentional_hang_without_a_worker_request_is_judged_separately(self):
        transport = self.timely()+[dict(side="backend", received_mono_ns=200,
                                       event=dict(kind="inject", fault="agent_hang"))]
        result = sitl._latency_evidence(dict(latency_ns=[50],worker_timeout=False), transport)
        self.assertTrue(result["passed"])
        self.assertEqual(result["timed_out"], 0)

    def test_hang_label_cannot_hide_an_actual_request_timeout(self):
        transport = self.timely()+[
            dict(side="backend", event=dict(kind="inject",fault="agent_hang")),
            dict(side="worker_request",epoch=1,sent_mono_ns=200),
            dict(side="worker_timeout",epoch=1,sent_mono_ns=200,elapsed_ns=1_000_000_001)]
        self.assertFalse(sitl._latency_evidence(dict(latency_ns=[50],worker_timeout=True),transport)["passed"])

    def test_missing_or_duplicated_timeout_record_cannot_be_hidden_by_summary(self):
        for rows in (self.timely(), self.timely()+[dict(side="worker_request",epoch=1,sent_mono_ns=200)]):
            with self.assertRaises(ValueError):
                sitl._latency_evidence(dict(latency_ns=[50],worker_timeout=True), rows)


if __name__ == "__main__":
    unittest.main()
