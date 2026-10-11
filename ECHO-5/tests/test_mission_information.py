"""Bounded active observation never converts unknown space into permission."""
from collections import Counter
from copy import deepcopy
import unittest

from echo5.budget import Budget
from echo5.legacy import module
from echo5.mission import MissionBridge, goal_request
from echo5.mission_reasoning import audit_information
from test_mission import raw_frame


def obstructed(now=10_000_000_000, remaining=950):
    raw = raw_frame(now=now, remaining=remaining)
    for sensor in [raw["lidar"], *raw["depth"]]:
        sensor["ranges_mm"] = [1000]*len(sensor["ranges_mm"])
    return raw


class InformationProbeTests(unittest.TestCase):
    def actor(self, mode="echo32"):
        return MissionBridge(goal_request((4,0,0)), budget=Budget(2_000_000), mode=mode)

    def test_missing_current_path_requests_new_observation_instead_of_claiming_free(self):
        actor = self.actor(); raw = obstructed()
        response = actor.decide(raw, sequence=0, now_ns=raw["now_ns"])
        self.assertEqual(response["status"], "inspect_information")
        self.assertEqual(response["prediction"], [0,0,0])
        self.assertEqual(response["reasoning"]["proposal"]["actions"], [])
        self.assertFalse(response["has_fact"])
        self.assertFalse(response["returning"])
        self.assertIsNone(actor.stopped)
        self.assertTrue(response["energy_check"]["allowed"])
        frame = module("nexus0.compose1_v3.perception").project({k:v for k,v in raw.items() if k!="battery"},240)
        self.assertEqual(audit_information(frame, response, Counter(), "echo32"), 1)

    def test_four_views_are_bounded_and_no_progress_eventually_aborts(self):
        actor = self.actor()
        for i in range(5):
            raw=obstructed(now=10_000_000_000+i*100_000_000)
            response=actor.decide(raw, sequence=i, now_ns=raw["now_ns"])
            if i<4:
                self.assertEqual(module("nexus0.drone3.contract").intention(response["wsp"]),("inspect",7+i))
            else:
                self.assertEqual(module("nexus0.drone3.contract").intention(response["wsp"])[0],"stop")
        self.assertEqual(sum(actor.information_probes.values()),4)

    def test_power_stop_and_conventional_control_cannot_be_replaced(self):
        for mode, remaining in (("echo32",150),("conventional",950)):
            actor=self.actor(mode);raw=obstructed(remaining=remaining)
            response=actor.decide(raw,sequence=0,now_ns=raw["now_ns"])
            self.assertNotEqual(response["status"],"inspect_information")
            self.assertEqual(sum(actor.information_probes.values()),0)

    def test_new_evidence_resumes_planning_and_low_battery_still_stops(self):
        for remaining, expected in ((950,"moving"),(150,"land_home")):
            actor=self.actor();raw=obstructed()
            actor.decide(raw,sequence=0,now_ns=raw["now_ns"])
            raw=raw_frame(now=10_100_000_000,remaining=remaining)
            response=actor.decide(raw,sequence=1,now_ns=raw["now_ns"])
            self.assertEqual(response["status"],expected)

    def test_auditor_rejects_unbounded_moving_or_fake_information_claim(self):
        actor=self.actor();raw=obstructed()
        response=actor.decide(raw,sequence=0,now_ns=raw["now_ns"])
        frame=module("nexus0.compose1_v3.perception").project({k:v for k,v in raw.items() if k!="battery"},240)
        for field,value in (("index",4),("total",13),("reason","guess")):
            changed=deepcopy(response);changed["information"][field]=value
            with self.assertRaises(ValueError):audit_information(frame,changed,Counter(),"echo32")
        changed=deepcopy(response);changed["prediction"]=[1,0,0]
        with self.assertRaises(ValueError):audit_information(frame,changed,Counter(),"echo32")
