"""Reasoning goals -> inherited MissionAgent -> independent SAFE/PX4 gates.

No hardware or process launch lives here. The evaluator's rays, ACKs and
motion are *software fixtures*, never evidence that PX4 or Gazebo ran.
Historical code is imported, not modified; no historical campaign is loaded.
"""

from copy import deepcopy
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

from .budget import Budget, BudgetExceeded
from .legacy import module
from .mission_reasoning import MissionReasoner, OUTCOME_SCHEMA, audit_reasoning, audit_information, validate_outcome


GOAL_SCHEMA = "echo5.mission.goal.v1"
PLAN_SCHEMA = "echo5.mission.plan.v1"
MODES = ("echo32", "one_step", "conventional")
CONDITIONS = ("static", "dynamic", "closed", "low_energy", "sensor_stale", "authority_loss")
TTL_NS = 250_000_000
MAX_DECISIONS = 64
RAW_KEYS = {"now_ns", "estimate", "lidar", "depth", "rgb", "battery"}
VECTORS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _int(value, low=0, high=2**63-1):
    return type(value) is int and low <= value <= high


def _keys(value, keys, reason):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(reason)


def _point(value, limit=4):
    if (type(value) not in (tuple, list) or len(value) != 3 or value[2] != 0
            or any(not _int(v, -limit, limit) for v in value)):
        raise ValueError("bounded_planar_cell")
    return list(value)


def _note(journal, kind, **facts):
    if journal is not None:
        journal.write(kind=kind, **deepcopy(facts))


class _EpisodeJournal:
    """An in-report copy of factual receipts, using the existing event shape."""
    def __init__(self, external):
        self.events = []
        self.external = external

    def write(self, **event):
        self.events.append(deepcopy(event))
        if self.external is not None:
            self.external.write(**deepcopy(event))


def goal_request(target_cell, *, goal_id="mission", max_decisions=MAX_DECISIONS):
    """Public reasoning-to-mission payload. A goal is a request, never a fact."""
    value = dict(schema=GOAL_SCHEMA, goal_id=goal_id, target_cell=list(target_cell),
                 return_home=True, require_marker=True, max_decisions=max_decisions)
    return validate_goal(value)


def validate_goal(value):
    _keys(value, {"schema", "goal_id", "target_cell", "return_home", "require_marker",
                  "max_decisions"}, "goal_schema")
    if (value["schema"] != GOAL_SCHEMA or type(value["goal_id"]) is not str
            or re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", value["goal_id"]) is None
            or value["return_home"] is not True or value["require_marker"] is not True
            or not _int(value["max_decisions"], 1, MAX_DECISIONS)):
        raise ValueError("goal_contract")
    _point(value["target_cell"])
    return deepcopy(value)


def synthetic_models(budget=None):
    """Declared priors, not learned flight/calibration evidence.

    POWER's schema requires n>=8. Those counts label a synthetic prior here;
    they must never be described as eight consumption measurements.
    """
    if budget:
        budget.consume("mission.model_init")
    effects = module("nexus0.compose1.model").Effects()
    for action, delta in enumerate(VECTORS):
        for _ in range(2):
            if budget:
                budget.consume("mission.synthetic_effect")
            effects.observe_effect(True, action, delta)
    power = {"unit": "sim_u", "costs": {
        "0": {"n": 8, "nominal": 12, "maximum": 15, "upper": 19},
        "1": {"n": 8, "nominal": 12, "maximum": 15, "upper": 19},
        "land": {"n": 8, "nominal": 24, "maximum": 27, "upper": 34}}}
    return effects.snapshot(), power


def validate_raw(raw, now_ns):
    """Strict bounded raw public data; retain capture times, reject private keys."""
    _keys(raw, RAW_KEYS, "raw_schema")
    if not _int(now_ns) or not _int(raw["now_ns"]) or not 0 <= now_ns-raw["now_ns"] <= TTL_NS:
        raise ValueError("observation_clock")

    def stamp(record):
        capture, delivered = record["capture_ns"], record["delivered_ns"]
        if (not _int(capture) or not _int(delivered)
                or not capture <= delivered <= raw["now_ns"] <= now_ns
                or now_ns-capture > TTL_NS):
            raise ValueError("sensor_stale_or_future")

    estimate = raw["estimate"]
    _keys(estimate, {"position_mm", "yaw_mrad", "received_ns", "px4_boot_ms",
                     "tilt_mrad", "speed_mm_s"}, "estimate_schema")
    if (type(estimate["position_mm"]) is not list or len(estimate["position_mm"]) != 3
            or any(not _int(v, -13500, 13500) for v in estimate["position_mm"])
            or not 1800 <= estimate["position_mm"][2] <= 3200
            or not _int(estimate["yaw_mrad"], -3142, 3142)
            or not _int(estimate["received_ns"]) or not _int(estimate["px4_boot_ms"])
            or not _int(estimate["tilt_mrad"], 0, 100)
            or not _int(estimate["speed_mm_s"], 0, 250)
            or not 0 <= now_ns-estimate["received_ns"] <= TTL_NS):
        raise ValueError("estimate_bounds_or_freshness")
    if type(raw["depth"]) is not list or len(raw["depth"]) != 4:
        raise ValueError("four_depth_views_required")
    for sensor in [raw["lidar"], *raw["depth"]]:
        _keys(sensor, {"capture_ns", "delivered_ns", "angles_mrad", "ranges_mm"}, "range_schema")
        stamp(sensor)
        angles, ranges = sensor["angles_mrad"], sensor["ranges_mm"]
        if (type(angles) is not list or type(ranges) is not list
                or not 2 <= len(angles) == len(ranges) <= 1024
                or any(not _int(v, -3142, 3142) for v in angles)
                or len(set(angles)) != len(angles)
                or any(not _int(v, -1, 30000) or v == 0 for v in ranges)):
            raise ValueError("bounded_measured_rays")
    rgb = raw["rgb"]
    _keys(rgb, {"capture_ns", "delivered_ns", "pixels_hex", "width", "height"}, "rgb_schema")
    stamp(rgb)
    if (not _int(rgb["width"], 1, 320) or not _int(rgb["height"], 1, 240)
            or type(rgb["pixels_hex"]) is not str
            or len(rgb["pixels_hex"]) != rgb["width"]*rgb["height"]*6):
        raise ValueError("rgb_bounds")
    if len(bytes.fromhex(rgb["pixels_hex"])) != rgb["width"]*rgb["height"]*3:
        raise ValueError("rgb_encoding")
    battery = raw["battery"]
    _keys(battery, {"capture_ns", "delivered_ns", "voltage_mv", "empty_mv", "full_mv"}, "battery_schema")
    stamp(battery)
    if (any(not _int(battery[k], 1, 65534) for k in ("voltage_mv", "empty_mv", "full_mv"))
            or battery["empty_mv"] >= battery["full_mv"]):
        raise ValueError("battery_bounds")
    return raw


def _mission_agent(*args, **kwargs):
    """Instance-local hook into the inherited already-projected compose phase.

    POWER, raw projection, registration, return and inspection are executed
    by the original MissionAgent. No imported class/global is monkeypatched.
    """
    class PlanningMissionAgent(module("nexus0.drone3.agent").MissionAgent):
        plan_hook = None

        def _compose(self, frame):
            if self.plan_hook is None:
                return super()._compose(frame)
            composer = self.composer
            composer.search = lambda target: self.plan_hook(frame, target)
            try:
                return super()._compose(frame)
            finally:
                del composer.search

    return PlanningMissionAgent(*args, **kwargs)


class MissionBridge:
    """Public ECHO-5 reasoning feeds one inherited MissionAgent by default.

    The plan is a hypothesis for this observation only. Each imagined cell
    must have current independent evidence; POWER and the external supervisor
    still veto the executable step. Neither a hint nor a goal writes CAM.
    """

    def __init__(self, goal, *, budget, mode="echo32", journal=None):
        self.goal = validate_goal(goal)
        if not isinstance(budget, Budget) or mode not in MODES:
            raise ValueError("mode_or_budget")
        self.budget, self.journal, self.mode = budget, journal, mode
        model, self.power_model = synthetic_models(budget)
        budget.consume("mission.agent_init")
        self.agent = _mission_agent(
            model, self.goal["target_cell"], [0, 0], self.power_model,
            mode="echo32" if mode == "conventional" else mode)
        # The inherited MissionAgent does not expose this supported Composer
        # mode in its constructor. Selecting it changes Q scoring only.
        self.agent.composer.mode = mode
        self.sequence = self.turns = 0
        self.last_now = -1
        self.position = None
        self.stopped = None
        self.initial_fingerprint = self.agent.fingerprint()
        self.reasoner = MissionReasoner()
        self.pending_response = None
        self.information_probes = Counter()
        _note(journal, "mission_goal", request=self.goal, mode=mode, has_fact=False,
              effects_prior="synthetic", power_prior="synthetic", offset_cells=[0, 0],
              model_sha256=self.initial_fingerprint)

    def _stop(self, reason):
        self.stopped = reason
        c = module("nexus0.drone3.contract")
        out = dict(wsp=c.pack(src=2, rel=14, dst=5, time=8, E={}, domain=9, generator=8, style=6).hex(),
                   prediction=deepcopy(self.position), action=6, status=reason,
                   goal_id=self.goal["goal_id"], sequence=self.sequence,
                   plan=[], has_fact=False, budget=self.budget.snapshot(),
                   reasoning=dict(called=False, applied=False, proposal=None), plan_source="bridge_stop")
        _note(self.journal, "mission_rejection", response=out)
        return out

    def _plan(self, plan, frame, sequence):
        _keys(plan, {"schema", "goal_id", "based_on_sequence", "start_cell", "actions"}, "plan_schema")
        actions = plan["actions"]
        if (plan["schema"] != PLAN_SCHEMA or plan["goal_id"] != self.goal["goal_id"]
                or not _int(plan["based_on_sequence"]) or plan["based_on_sequence"] != sequence
                or _point(plan["start_cell"]) != frame["odometry"]
                or type(actions) is not list or not 1 <= len(actions) <= 4
                or any(not _int(a, 0, 3) for a in actions)):
            raise ValueError("plan_contract")
        gates = module("nexus0.drone3.gates")
        point = list(frame["odometry"])
        seen = {tuple(point)}
        for action in actions:
            self.budget.consume("mission.plan_validation")
            delta = self.agent.composer.model.predict(action)
            if delta is None:
                raise ValueError("plan_effect_unknown")
            point = [a+b for a, b in zip(point, delta)]
            _point(point)
            if tuple(point) in seen or not gates.epistemic(frame, "move", point[:2], frame["now_ns"], [0, 0])["allowed"]:
                raise ValueError("plan_not_admitted")
            seen.add(tuple(point))
        return list(actions)

    def observe_consequence(self, outcome):
        checked = self.reasoner.consequence(outcome, self.pending_response, self.budget)
        _note(self.journal, "mission_execution_outcome", outcome=checked)
        self.pending_response = None
        return checked

    def _information_probe(self, raw, response, reasoning, prior):
        """Replace an uncommitted retreat proposal with a bounded yaw probe.

        POWER has already run once inside MissionAgent. Never undo an energy
        return, prior stop, completed goal or veto. The external supervisor
        still checks the actual emitted inspection and its energy reserve.
        """
        p = reasoning.get("proposal") or {}
        no_path = (reasoning["called"] and not p.get("actions") and not prior["returning"]
                   and self.agent.return_reason == "compose_access_not_found")
        return_gap = response["status"] == "return_not_admitted" and not no_path
        power = response.get("power") or {}
        cell = tuple(self.agent.pos[:2])
        index = self.information_probes[cell]
        if (self.mode == "conventional" or prior["stopped"] is not None
                or not (no_path or return_gap) or power.get("reason") not in ("continue", "return")
                or (no_path and power["reason"] != "continue")
                or index >= 4 or sum(self.information_probes.values()) >= 12):
            return response
        energy = module("nexus0.drone3.energy")
        gates = module("nexus0.drone3.gates")
        check = gates.energy(self.power_model, energy.battery_sample(raw["battery"]), raw["now_ns"],
                             self.agent.visited, cell, self.agent.home[:2])
        if not check["allowed"]:
            return response
        blocked = None
        if return_gap:
            route = self.agent.back_route()
            if not route:
                return response
            dx, dy = module("nexus0.drone3.contract").VECTORS[route[0]]
            blocked = [cell[0]+dx, cell[1]+dy]
            rays = sum(len(s["ranges_mm"]) for s in [raw["lidar"], *raw["depth"]])
            self.budget.consume("mission.information_perception", rays+raw["rgb"]["width"]*raw["rgb"]["height"])
            frame = module("nexus0.compose1_v3.perception").project(
                {k:v for k,v in raw.items() if k != "battery"}, 240)
            if gates.epistemic(frame, "move", blocked, raw["now_ns"], [0, 0])["allowed"]:
                return response
        self.budget.consume("mission.information_probe")
        self.information_probes[cell] += 1
        # These are prospective controller fields, before any WSP is emitted.
        # Keep a genuine return latch; defer only a just-proposed no-path abort.
        if no_path:
            self.agent.returning, self.agent.return_reason = prior["returning"], prior["return_reason"]
        self.agent.stopped = prior["stopped"]
        self.agent.composer.pending = []
        self.agent.composer.last_prediction = self.agent.pos
        info = dict(reason="no_supported_current_path" if no_path else "return_step_not_admitted",
                    prior_status=response["status"], cell=list(cell), index=index,
                    total=sum(self.information_probes.values()), blocked_return_cell=blocked)
        return self.agent.respond(module("nexus0.drone3.contract").inspect_wsp(index), self.agent.pos,
                                  "inspect_information", "inspect", plan=[], candidates=0,
                                  power=power, attribution=response.get("attribution"),
                                  energy_check=check, information=info)

    def decide(self, raw, *, sequence, now_ns, plan=None):
        if self.stopped:
            return self._stop(self.stopped)
        try:
            self.budget.consume("mission.validation")
            validate_raw(raw, now_ns)
            if not _int(sequence) or sequence != self.sequence or now_ns <= self.last_now:
                raise ValueError("sequence_or_clock")
            if self.turns >= self.goal["max_decisions"]:
                return self._stop("decision_limit")
            rays = sum(len(s["ranges_mm"]) for s in [raw["lidar"], *raw["depth"]])
            self.budget.consume("mission.perception", (2 if plan is not None else 1)*(rays+raw["rgb"]["width"]*raw["rgb"]["height"]))
            perception = module("nexus0.compose1_v3.perception")
            proposed_plan = None
            if plan is not None:
                # Explicit untrusted external hints retain pre-agent validation.
                frame = perception.project({k: v for k, v in raw.items() if k != "battery"}, 240)
                proposed_plan = self._plan(plan, frame, sequence)
            self.budget.consume("mission.planning_reservation", 32)
            self.position = list(perception.grid(raw["estimate"]["position_mm"]))
            self.last_now = now_ns
            self.sequence += 1
            self.turns += 1
            _note(self.journal, "mission_observation", sequence=sequence, raw_sha256=digest(raw),
                  position=self.position)
            reasoning = dict(called=False, applied=False, proposal=None)
            override = proposed_plan is not None or self.mode != "conventional"
            def search(frame, target):
                if list(target) != self.goal["target_cell"]:
                    raise ValueError("reasoning_target_changed")
                if proposed_plan is not None:
                    return list(proposed_plan), len(proposed_plan)+1
                evidence = self.reasoner.propose(frame, self.goal, sequence=sequence,
                    raw_sha256=digest(raw), budget=self.budget, horizon=1 if self.mode == "one_step" else 4)
                reasoning.update(called=True, proposal=evidence)
                actions = evidence["actions"]
                if actions:
                    self._plan(dict(schema=PLAN_SCHEMA, goal_id=self.goal["goal_id"],
                        based_on_sequence=sequence, start_cell=list(frame["odometry"]), actions=actions), frame, sequence)
                return actions, len(evidence["candidates"])
            if override:
                self.agent.plan_hook = search
            prior = dict(returning=self.agent.returning, return_reason=self.agent.return_reason,
                         stopped=self.agent.stopped)
            try:
                response = self.agent.decide(deepcopy(raw))
            finally:
                if override:
                    self.agent.plan_hook = None
            if proposed_plan is None:
                response = self._information_probe(raw, response, reasoning, prior)
            kind, action = module("nexus0.drone3.contract").intention(response["wsp"])
            reasoning["applied"] = reasoning["called"] and response["status"] == "moving"
            source = ("echo5_information_probe" if response["status"] == "inspect_information" else
                      "echo5_reasoner" if reasoning["applied"] else
                      "reasoning_hypothesis" if proposed_plan is not None and response["status"] == "moving" else
                      "compose" if response["status"] == "moving" else "inherited_power_return_or_inspect")
            response.update(action=action, goal_id=self.goal["goal_id"], sequence=sequence,
                            raw_sha256=digest(raw), observation_ns=raw["now_ns"],
                            plan_source=source, reasoning=reasoning,
                            has_fact=False, budget=self.budget.snapshot())
            self.pending_response = deepcopy(response) if kind != "stop" else None
            if kind == "stop":
                self.stopped = response["status"]
            _note(self.journal, "mission_plan", response=response)
            return response
        except BudgetExceeded:
            return self._stop("budget_exhausted")
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            return self._stop("rejected:"+str(exc))


class MissionExecutor:
    """Independent public-evidence supervisor; emits no actuator commands.

    The caller forwards an allowed target through its own transport and feeds
    real ACKs/telemetry back here. In SITL the inherited runner owns this same
    MissionSupervisor instead; software fixtures never stand in for it.
    """

    def __init__(self, power_model, *, budget, journal=None):
        self.supervisor = module("nexus0.drone3.supervisor").MissionSupervisor(power_model, [0, 0], (0, 0))
        self.budget, self.journal = budget, journal
        self.last_sequence = -1

    def submit(self, response, raw, health):
        try:
            self.budget.consume("mission.supervision")
            validate_raw(raw, health["now_ns"])
            if (response.get("raw_sha256") != digest(raw)
                    or not _int(response.get("sequence")) or response["sequence"] <= self.last_sequence):
                raise ValueError("response_not_bound_to_observation")
            energy = module("nexus0.drone3.energy")
            frame = module("nexus0.compose1_v3.perception").project(
                {k: v for k, v in raw.items() if k != "battery"}, 240)
            self.supervisor.occupied(frame["odometry"][:2])
            request = dict(wsp=response["wsp"], prediction=response["prediction"],
                           seq=response["sequence"], published_ns=raw["now_ns"])
            decision = self.supervisor.submit(request, health, dict(frame=frame, battery=energy.battery_sample(raw["battery"])))
            self.last_sequence = response["sequence"]
        except (ValueError, TypeError, KeyError, BudgetExceeded) as exc:
            self.supervisor.trip("invalid_submission:"+str(exc))
            decision = dict(allowed=False, reason=self.supervisor.reason)
        _note(self.journal, "mission_gateway", decision=decision)
        return decision

    def acknowledge(self, ack, now_ns):
        self.budget.consume("mission.ack")
        accepted = self.supervisor.acknowledge(ack, now_ns)
        _note(self.journal, "mission_ack", ack=ack, now_ns=now_ns, accepted=accepted)
        return accepted

    def observe(self, health):
        self.budget.consume("mission.telemetry")
        ok = self.supervisor.check(health)
        state = self.supervisor.gateway.state
        _note(self.journal, "mission_consequence", health=health, allowed=ok,
              gateway_state=state, samples=self.supervisor.gateway.samples)
        return state


def _health(raw, *, authority=True, worker_alive=True, now_ns=None):
    """Software fixture only. Physical health comes from PX4 in the runner."""
    estimate = raw["estimate"]
    return dict(now_ns=raw["now_ns"] if now_ns is None else now_ns,
                sensor_ns=raw["lidar"]["capture_ns"], worker_alive=worker_alive,
                frame=dict(received_ns=estimate["received_ns"], position_mm=list(estimate["position_mm"]),
                           speed_mm_s=estimate["speed_mm_s"], armed=True, authority=authority, failsafe=False))


class _SoftwareWorld:
    """Evaluator-only new ray fixtures around a fresh inherited discrete world."""

    def __init__(self, seed, condition, budget):
        budget.consume("mission.world_init")
        self.world = module("nexus0.compose1_v3.space").Space(seed, condition)
        self.condition, self.budget = condition, budget
        self.remaining = 150 if condition == "low_energy" else 950
        self.now = 1_000_000_000
        self.moves = 0
        self.disarmed = False

    def raw(self):
        self.budget.consume("mission.ray_fixture", 360*len(self.world.solids))
        position = [self.world.pos[0]*3000, self.world.pos[1]*3000, 2500]
        sensor = [position[0]+120, position[1]+30]
        angles = [round(-math.pi*1000+i*2*math.pi*1000/360) for i in range(360)]
        ranges = []
        for angle in angles:
            direction = (math.cos(angle/1000), math.sin(angle/1000))
            nearest = 30000.0
            for x, y, _ in self.world.solids:
                enter, leave = 0.0, 30000.0
                for axis, centre in enumerate((x*3000, y*3000)):
                    d = direction[axis]
                    lo, hi = centre-1500, centre+1500
                    if abs(d) < 1e-12:
                        if not lo <= sensor[axis] <= hi:
                            enter, leave = 1.0, 0.0
                            break
                    else:
                        a, b = sorted(((lo-sensor[axis])/d, (hi-sensor[axis])/d))
                        enter, leave = max(enter, a), min(leave, b)
                if enter <= leave:
                    nearest = min(nearest, enter)
            ranges.append(max(1, round(nearest)))
        lidar = dict(capture_ns=self.now, delivered_ns=self.now, angles_mrad=angles, ranges_mm=ranges)
        depth = []
        for yaw in (0, math.pi/2, math.pi, -math.pi/2):
            pairs = [(a, r) for a, r in zip(angles, ranges) if abs((a/1000-yaw+math.pi) % (2*math.pi)-math.pi) <= .8]
            depth.append(dict(capture_ns=self.now, delivered_ns=self.now,
                              angles_mrad=[a for a, _ in pairs], ranges_mm=[r for _, r in pairs]))
        if self.condition == "sensor_stale" and self.moves >= 1:
            lidar["capture_ns"] -= TTL_NS+1
        marker = self.world.pos == self.world.goal
        return dict(now_ns=self.now,
                    estimate=dict(position_mm=position, yaw_mrad=0, received_ns=self.now,
                                  px4_boot_ms=self.now//1_000_000, tilt_mrad=0, speed_mm_s=0),
                    lidar=lidar, depth=depth,
                    rgb=dict(capture_ns=self.now, delivered_ns=self.now, width=8, height=8,
                             pixels_hex=("00ff00" if marker else "303030")*64),
                    battery=dict(capture_ns=self.now, delivered_ns=self.now,
                                 voltage_mv=12000+max(0, self.remaining)*4, empty_mv=12000, full_mv=16000))


def _software_episode(config, case, mode, journal):
    external_journal = journal
    journal = _EpisodeJournal(external_journal)
    budget = Budget(config["budget"])
    condition = CONDITIONS[case % len(CONDITIONS)]
    row = dict(case_id=f"mission-{case:04d}", condition=condition, mode=mode, seed=config["seed"]+case,
               evidence="software_fixture", success=False, status="not_started", collisions=0,
               reserve_violations=0, unsafe_commands=0, goal_observed=False, returned_home=False,
               disarmed=False, sensor_fault_exercised=False, fault_latched=False, steps=0,
               final_position=None, final_reserve=None, budget_exhausted=False, model_unchanged=None)
    world = actor = executor = None
    try:
        world = _SoftwareWorld(row["seed"], condition, budget)
        _note(journal, "mission_world_started", goal=list(world.world.goal), home=list(world.world.start),
              evidence="software_fixture")
        request = goal_request(world.world.goal, goal_id=row["case_id"], max_decisions=config["max_decisions"])
        actor = MissionBridge(request, budget=budget, mode=mode, journal=journal)
        executor = MissionExecutor(actor.power_model, budget=budget, journal=journal)
        for sequence in range(config["max_decisions"]):
            raw = world.raw()
            health = _health(raw, authority=not (condition == "authority_loss" and world.moves >= 1))
            _note(journal, "mission_sensor_frame", sequence=sequence, raw=raw, health=health)
            budget.consume("mission.health_check")
            if not executor.supervisor.check(health):
                row.update(status=executor.supervisor.reason, fault_latched=True,
                           sensor_fault_exercised=condition in ("sensor_stale", "authority_loss"))
                _note(journal, "mission_safe_veto", health=health, reason=executor.supervisor.reason,
                      evidence="software_fixture")
                break
            projected = module("nexus0.compose1_v3.perception").project({k: v for k, v in raw.items() if k != "battery"}, 240)
            row["goal_observed"] |= projected["station_observed"] and world.world.pos == world.world.goal
            response = actor.decide(raw, sequence=sequence, now_ns=world.now)
            row["steps"] += 1
            row["status"] = response["status"]
            kind, action = module("nexus0.drone3.contract").intention(response["wsp"])
            if kind == "stop":
                row["budget_exhausted"] = response["status"] == "budget_exhausted"
                break
            decision = executor.submit(response, raw, health)
            if not decision["allowed"]:
                row.update(status=decision["reason"], fault_latched=True)
                break
            row["unsafe_commands"] += int(any(decision["gates"][key].get("allowed") is not True
                                               for key in ("health", "epistemic", "energy", "gateway")))
            budget.consume("mission.software_step")
            if kind == "move":
                consequence = world.world.step(action)
                world.moves += 1
                row["collisions"] += int(consequence["blocked"])
            else:
                consequence = dict(before=list(world.world.pos), after=list(world.world.pos), blocked=False)
            world.remaining -= 15
            row["reserve_violations"] += int(world.remaining < 40)
            _note(journal, "mission_software_step", consequence=consequence, remaining=world.remaining,
                  evidence="software_fixture")
            ack_ns = world.now+10_000_000
            ack = dict(system=1, component=1, command=192, result=0, received_ns=ack_ns)
            executor.acknowledge(ack, ack_ns)
            for tick in (20_000_000, 30_000_000, 40_000_000):
                stamp = world.now+tick
                telemetry = dict(now_ns=stamp, sensor_ns=stamp, worker_alive=True,
                                 frame=dict(received_ns=stamp, position_mm=[world.world.pos[0]*3000, world.world.pos[1]*3000, 2500],
                                            speed_mm_s=0, armed=True, authority=True, failsafe=False))
                executor.observe(telemetry)
            released = executor.supervisor.gateway.release()
            _note(journal, "mission_arrival_release", released=released)
            if not released:
                row["status"] = "arrival_not_confirmed"
                break
            actor.observe_consequence(dict(schema=OUTCOME_SCHEMA, sequence=sequence,
                raw_sha256=response["raw_sha256"], wsp=response["wsp"], prediction=response["prediction"],
                disposition="arrived", command_seq=sequence, ack=ack, samples=3,
                estimate={k:telemetry["frame"][k] for k in ("position_mm", "received_ns", "speed_mm_s")},
                reason="gateway_complete"))
            world.now += 100_000_000
        else:
            row["status"] = "decision_limit"
    except BudgetExceeded:
        row.update(status="budget_exhausted", budget_exhausted=True)
    if world is not None:
        # Explicit software landing consequence, never a PX4 receipt.
        world.remaining -= 27
        world.disarmed = True
        row.update(final_position=list(world.world.pos), final_reserve=world.remaining,
                   returned_home=world.world.pos == world.world.start, disarmed=True)
        row["reserve_violations"] += int(world.remaining < 40)
        _note(journal, "mission_landing", position=list(world.world.pos), remaining=world.remaining,
              disarmed=True, evidence="software_fixture")
    if actor is not None:
        row["model_unchanged"] = actor.initial_fingerprint == actor.agent.fingerprint()
        row["cam_destroyed"] = actor.agent.composer.model.cam.destroyed
        row["prediction_errors"] = actor.agent.composer.prediction_errors
    row["success"] = bool(row["goal_observed"] and row["returned_home"] and row["disarmed"]
                          and not row["collisions"] and not row["reserve_violations"]
                          and not row["unsafe_commands"]
                          and not row["budget_exhausted"] and row["status"] not in ("decision_limit", "arrival_not_confirmed")
                          and not row["status"].startswith("rejected:"))
    row["costs"] = budget.snapshot()
    row["cost"] = budget.used
    decisions = [e["response"] for e in journal.events if e["kind"] == "mission_plan"]
    outcomes = [e["outcome"] for e in journal.events if e["kind"] == "mission_execution_outcome"]
    row["reasoner_calls"] = sum(r["reasoning"]["called"] for r in decisions)
    row["reasoner_actions"] = sum(r["reasoning"]["applied"] for r in decisions)
    used = {r["sequence"] for r in decisions if r["reasoning"]["applied"]}
    row["reasoner_executed"] = sum(o["disposition"] == "arrived" and o["sequence"] in used for o in outcomes)
    row["consequence_receipts"] = len(outcomes)
    _note(journal, "mission_terminal", status=row["status"], budget_exhausted=row["budget_exhausted"],
          costs=budget.snapshot())
    _note(external_journal, "mission_result", row=row)
    row["trace"] = journal.events
    return row


def summarize(rows):
    by_mode = {}
    for mode in MODES:
        subset = [r for r in rows if r["mode"] == mode]
        by_mode[mode] = dict(cases=len(subset), successes=sum(r["success"] for r in subset),
                             cost=sum(r.get("cost", 0) for r in subset),
                             collisions=sum(r.get("collisions", 0) or 0 for r in subset),
                             reserve_violations=sum(r.get("reserve_violations", 0) or 0 for r in subset))
    controls = {}
    principal = {r["case_id"]: r for r in rows if r["mode"] == "echo32"}
    for mode in MODES[1:]:
        pairs = [(principal[r["case_id"]], r) for r in rows if r["mode"] == mode and r["case_id"] in principal]
        wins = sum(a["success"] and not b["success"] for a, b in pairs)
        losses = sum(b["success"] and not a["success"] for a, b in pairs)
        controls[mode] = dict(wins=wins, losses=losses, ties=len(pairs)-wins-losses,
                             cost_delta=sum(a.get("cost", 0)-b.get("cost", 0) for a, b in pairs))
    return dict(modes=by_mode, controls=controls, cost=sum(r.get("cost", 0) for r in rows))


def run_benchmark(config, journal=None):
    """New deterministic software campaign. Does not import/launch SITL."""
    return _run_benchmark_config(normalize_config(config), journal)


def normalize_config(config):
    if type(config) is not dict or not set(config) <= {"seed", "cases", "budget", "max_decisions", "phase"}:
        raise ValueError("mission_config")
    cfg = dict(seed=51601, cases=12, budget=1000000, max_decisions=64, phase="development")
    cfg.update(config)
    if (not _int(cfg["seed"], 1, 2**31-1) or not _int(cfg["cases"], 1, 96)
            or not _int(cfg["budget"], 0, 100_000_000)
            or not _int(cfg["max_decisions"], 1, MAX_DECISIONS)
            or cfg["phase"] not in ("development", "confirmation")):
        raise ValueError("mission_config_bounds")
    if cfg["phase"] == "confirmation" and (cfg["seed"], cfg["cases"], cfg["budget"], cfg["max_decisions"]) != (61703, 12, 1000000, 64):
        raise ValueError("confirmation_contract")
    if cfg["phase"] == "development" and cfg["seed"] <= 61714 and cfg["seed"]+cfg["cases"]-1 >= 61703:
        raise ValueError("reserved_confirmation_seed_interval")
    return cfg


def _reasoning_gate(rows):
    nominal = [r for r in rows if r["mode"] == "echo32" and r["condition"] == "static"]
    return bool(nominal) and all(r.get("reasoner_calls", 0) > 0 and r.get("reasoner_executed", 0) > 0 for r in nominal)


def _run_benchmark_config(cfg, journal):
    cfg = normalize_config(cfg)
    rows = [_software_episode(cfg, case, mode, journal) for case in range(cfg["cases"]) for mode in MODES]
    summary = summarize(rows)
    safe = all(r["collisions"] == r["reserve_violations"] == r["unsafe_commands"] == 0
               and r["disarmed"] and not r["budget_exhausted"] for r in rows)
    faults = [r for r in rows if r["condition"] in ("sensor_stale", "authority_loss")]
    coverage = set(r["condition"] for r in rows) == set(CONDITIONS)
    static = [r for r in rows if r["mode"] == "echo32" and r["condition"] == "static"]
    integrity = all(r["model_unchanged"] is True and r.get("cam_destroyed") == 0 for r in rows)
    reasoning_used = _reasoning_gate(rows)
    correct = (coverage and safe and integrity and reasoning_used and bool(static) and all(r["success"] for r in static)
               and bool(faults) and all(r["sensor_fault_exercised"] and r["fault_latched"] for r in faults))
    control = summary["controls"]["conventional"]
    advantage = correct and control["losses"] == 0 and (control["wins"] > 0 or control["cost_delta"] < 0)
    return dict(schema="echo5.mission.software.v1", config=cfg, rows=rows, summary=summary,
                gates=dict(denominator=len(rows) == cfg["cases"]*len(MODES), safety=safe,
                           condition_coverage=coverage, model_integrity=integrity, software_correctness=correct,
                           reasoning_used=reasoning_used, advantage=advantage, sitl_valid=False, hardware_valid=False),
                limits=["Software rays, ACKs and landing only", "Synthetic untrained effects and power priors",
                        "No physical calibration, measured energy, hardware or SITL claim"],
                costs=dict(semantics="logical work per case and mode", used=summary["cost"],
                           limit=cfg["cases"]*len(MODES)*cfg["budget"]))


def _audit_episode(row, config, case, mode):
    """External judge: reconstruct the world and transport, never the actor."""
    def require(ok, reason):
        if not ok:
            raise ValueError(reason)

    condition = CONDITIONS[case % len(CONDITIONS)]
    require(row["case_id"] == f"mission-{case:04d}" and row["mode"] == mode
            and row["condition"] == condition and row["seed"] == config["seed"]+case,
            "case_identity_or_denominator")
    require(row["evidence"] == "software_fixture", "software_evidence_label")
    trace = row["trace"]
    require(type(trace) is list and len(trace) <= 1000, "bounded_trace_required")
    # Fresh evaluator geometry, not an actor's claimed goal or success flag.
    space = module("nexus0.compose1_v3.space").Space(config["seed"]+case, condition)
    model, power = synthetic_models()
    fingerprint = module("nexus0.compose1.model").Effects.restore(model).fingerprint()
    supervisor = module("nexus0.drone3.supervisor").MissionSupervisor(power, [0, 0], (0, 0))
    c = module("nexus0.drone3.contract")
    perception = module("nexus0.compose1_v3.perception")
    energy = module("nexus0.drone3.energy")
    raw = health = response = decision = terminal = None
    started = agent_created = goal_seen = landed = fault = False
    steps = moves = collisions = violations = unsafe = frames = 0
    last_clock = -1
    last_budget = 0
    remaining = 150 if condition == "low_energy" else 950
    model_unchanged = True
    executed = False
    release_pending = False
    outcome_due = False
    last_ack = last_telemetry = None
    reasoner_calls = reasoner_actions = reasoner_executed = consequence_receipts = 0
    reason_visits, reason_position = Counter(), None
    information_counts = Counter()
    for index, event in enumerate(trace):
        require(type(event) is dict and "kind" in event, "trace_schema")
        kind = event["kind"]
        require(not landed or kind == "mission_terminal", "events_after_landing")
        if kind == "mission_world_started":
            require(not started and index == 0 and event["goal"] == list(space.goal)
                    and event["home"] == list(space.start), "external_world_binding")
            started = True
        elif kind == "mission_goal":
            require(started and not agent_created and event["request"] == goal_request(
                space.goal, goal_id=row["case_id"], max_decisions=config["max_decisions"])
                and event["mode"] == mode and event["has_fact"] is False
                and event["model_sha256"] == fingerprint, "public_goal_binding")
            agent_created = True
        elif kind == "mission_sensor_frame":
            require(started and agent_created and not fault and not release_pending and not outcome_due, "observation_order")
            raw, health = event["raw"], event["health"]
            require(event["sequence"] == frames and frames < config["max_decisions"], "observation_sequence")
            frames += 1
            require(raw["now_ns"] > last_clock, "observation_clock")
            last_clock = raw["now_ns"]
            expected_authority = not (condition == "authority_loss" and moves >= 1)
            require(health == _health(raw, authority=expected_authority), "health_binding")
            require(raw["estimate"]["position_mm"] == c.cell_target(space.pos[:2]), "odometry_vs_external_world")
            sample = energy.battery_sample(raw["battery"])
            require(sample is not None and sample["remaining"] == max(0, remaining), "battery_vs_consequences")
            if condition == "sensor_stale" and moves >= 1:
                require(raw["now_ns"]-raw["lidar"]["capture_ns"] > TTL_NS, "fault_not_exercised")
            ok = supervisor.check(health)
            if ok:
                validate_raw(raw, raw["now_ns"])
                projected = perception.project({k: v for k, v in raw.items() if k != "battery"}, 240)
                goal_seen |= bool(space.pos == space.goal and projected["station_observed"])
            response = decision = None
            executed = False
        elif kind in ("mission_observation", "mission_plan", "mission_rejection"):
            require(raw is not None and not supervisor.tripped, "agent_after_fault_or_without_observation")
            if kind == "mission_observation":
                require(event["raw_sha256"] == digest(raw) and event["position"] == list(space.pos), "accepted_observation_binding")
                continue
            require(response is None, "duplicate_agent_decision")
            response = event["response"]
            action_kind, _ = c.intention(response["wsp"])
            require(response["goal_id"] == row["case_id"] and response["has_fact"] is False, "proposal_is_not_fact")
            if kind == "mission_plan":
                require(response["raw_sha256"] == digest(raw) and response["sequence"] == frames-1, "proposal_binding")
                model_unchanged &= response["model_sha256"] == fingerprint and response["imagined_writes"] == 0 and response["cam_destroyed"] == 0
                verified = audit_reasoning(projected, response, goal_request(space.goal, goal_id=row["case_id"],
                    max_decisions=config["max_decisions"]), mode)
                audit_information(projected, response, information_counts, mode)
                reasoner_calls += verified["called"]
                reasoner_actions += verified["applied"]
                if verified["called"]:
                    point = tuple(projected["odometry"])
                    if point != reason_position:
                        reason_visits[point] += 1
                        reason_position = point
                    proposal = response["reasoning"]["proposal"]
                    require(proposal["visits"] == [[list(p), n] for p, n in sorted(reason_visits.items())]
                            and proposal["consequence_count"] == consequence_receipts, "reasoning_history_binding")
            else:
                require(action_kind == "stop", "rejection_cannot_move")
            used = response["budget"]["used"]
            require(last_budget <= used <= config["budget"], "proposal_budget")
            last_budget = used
            steps += 1
        elif kind == "mission_gateway":
            require(raw is not None and response is not None and decision is None, "gateway_order")
            frame = perception.project({k: v for k, v in raw.items() if k != "battery"}, 240)
            supervisor.occupied(frame["odometry"][:2])
            request = dict(wsp=response["wsp"], prediction=response["prediction"], seq=response["sequence"], published_ns=raw["now_ns"])
            decision = supervisor.submit(request, health, dict(frame=frame, battery=energy.battery_sample(raw["battery"])))
            require(decision == event["decision"], "independent_power_safe_gateway")
            fault |= not decision["allowed"]
        elif kind == "mission_software_step":
            require(decision is not None and decision["allowed"] and not executed and not supervisor.tripped, "execution_without_permission")
            action_kind, action = c.intention(response["wsp"])
            require(action_kind in ("move", "inspect"), "stop_is_not_movement")
            if action_kind == "move":
                actual = space.step(action)
                moves += 1
                collisions += int(actual["blocked"])
            else:
                actual = dict(before=list(space.pos), after=list(space.pos), blocked=False)
            remaining -= 15
            violations += int(remaining < 40)
            unsafe += int(any(decision["gates"][key].get("allowed") is not True for key in ("health", "epistemic", "energy", "gateway")))
            require(event["consequence"] == actual and event["remaining"] == remaining, "external_action_consequence")
            executed = release_pending = True
        elif kind == "mission_ack":
            require(executed and release_pending, "ack_without_execution")
            require(supervisor.acknowledge(event["ack"], event["now_ns"]) == event["accepted"], "ack_identity_order")
            last_ack = event["ack"]
        elif kind == "mission_consequence":
            require(executed and release_pending, "telemetry_without_execution")
            require(event["health"]["frame"]["position_mm"] == c.cell_target(space.pos[:2]), "telemetry_vs_external_world")
            ok = supervisor.check(event["health"])
            require(event["allowed"] == ok and event["gateway_state"] == supervisor.gateway.state
                    and event["samples"] == supervisor.gateway.samples, "gateway_arrival_samples")
            last_telemetry = event["health"]["frame"]
        elif kind == "mission_arrival_release":
            require(release_pending, "release_without_execution")
            require(supervisor.gateway.release() == event["released"], "ack_is_not_arrival")
            release_pending = False
            outcome_due = bool(event["released"])
        elif kind == "mission_execution_outcome":
            require(outcome_due and executed and response is not None, "outcome_without_arrival")
            outcome = validate_outcome(event["outcome"], response)
            require(outcome["disposition"] == "arrived" and outcome["command_seq"] == response["sequence"]
                    and outcome["ack"] == last_ack and outcome["samples"] == 3
                    and outcome["estimate"] == {k:last_telemetry[k] for k in ("position_mm", "received_ns", "speed_mm_s")},
                    "outcome_vs_external_execution")
            consequence_receipts += 1
            reasoner_executed += int(response["reasoning"]["applied"])
            if c.intention(response["wsp"])[0] == "move":
                reason_position = tuple(response["prediction"])
                reason_visits[reason_position] += 1
            outcome_due = False
        elif kind == "mission_safe_veto":
            require(supervisor.tripped and event["reason"] == supervisor.reason and event["health"] == health, "safe_fault_witness")
            fault = True
        elif kind == "mission_landing":
            require(started and not landed, "landing_order")
            remaining -= 27
            violations += int(remaining < 40)
            require(event["position"] == list(space.pos) and event["remaining"] == remaining
                    and event["disarmed"] is True and event["evidence"] == "software_fixture", "external_landing")
            landed = True
        elif kind == "mission_terminal":
            require(index == len(trace)-1 and terminal is None, "terminal_order")
            terminal = event
        else:
            raise ValueError("unknown_trace_event:"+str(kind))
    require(terminal is not None, "terminal_receipt_missing")
    require(not outcome_due or terminal["budget_exhausted"], "execution_outcome_missing")
    costs = terminal["costs"]
    require(costs == row["costs"] and costs["limit"] == config["budget"]
            and type(costs["counts"]) is dict and all(type(v) is int and v >= 0 for v in costs["counts"].values())
            and sum(costs["counts"].values()) == costs["used"] == row["cost"]
            and costs["remaining"] == costs["limit"]-costs["used"] >= 0
            and costs["used"] >= last_budget, "cost_accounting")
    require(type(terminal["budget_exhausted"]) is bool and type(terminal["status"]) is str, "terminal_schema")
    status = terminal["status"]
    success = bool(goal_seen and landed and space.pos == space.start and not collisions and not violations
                   and not unsafe
                   and not terminal["budget_exhausted"] and status not in ("decision_limit", "arrival_not_confirmed")
                   and not status.startswith("rejected:"))
    derived = dict(case_id=row["case_id"], condition=condition, mode=mode, seed=config["seed"]+case,
                   evidence="software_fixture", success=success, status=status, collisions=collisions,
                   reserve_violations=violations, unsafe_commands=unsafe, goal_observed=goal_seen,
                   returned_home=landed and space.pos == space.start, disarmed=landed,
                   sensor_fault_exercised=fault and condition in ("sensor_stale", "authority_loss"),
                   fault_latched=fault, steps=steps, final_position=list(space.pos) if started else None,
                   final_reserve=remaining if started else None, budget_exhausted=terminal["budget_exhausted"],
                   model_unchanged=model_unchanged if agent_created else None, cost=costs["used"], costs=costs,
                   reasoner_calls=reasoner_calls, reasoner_actions=reasoner_actions,
                   reasoner_executed=reasoner_executed, consequence_receipts=consequence_receipts)
    if agent_created:
        derived["cam_destroyed"] = 0 if model_unchanged else None
    for key, value in derived.items():
        require(row.get(key) == value, "claimed_metric:"+key)
    return derived


def audit_report(report):
    """Independent consequence/gate adjudication PLUS a fresh-process replay.

    ``valid`` means an honest, reconstructible report, including a negative
    capability result. Only software_correctness describes that capability;
    sitl_valid and hardware_valid are always false for this instrument.
    """
    findings, derived = [], []
    replay = dict(valid=False, process_id=None, exact=False)
    gates = dict(denominator=False, safety=False, condition_coverage=False, model_integrity=False,
                 software_correctness=False, reasoning_used=False, advantage=False, sitl_valid=False, hardware_valid=False)
    try:
        if type(report) is not dict or report.get("schema") != "echo5.mission.software.v1":
            raise ValueError("software_report_schema")
        config = report["config"]
        expected_keys = {"seed", "cases", "budget", "max_decisions", "phase"}
        _keys(config, expected_keys, "audit_config")
        if normalize_config(config) != config:
            raise ValueError("audit_config_normalization")
        if (not _int(config["cases"], 1, 96) or not _int(config["seed"], 1, 2**31-1)
                or not _int(config["budget"], 0, 100_000_000) or not _int(config["max_decisions"], 1, 64)
                or config["phase"] not in ("development", "confirmation")):
            raise ValueError("audit_config_bounds")
        rows = report["rows"]
        if type(rows) is not list or len(rows) != config["cases"]*len(MODES):
            raise ValueError("scheduled_denominator")
        for case in range(config["cases"]):
            for index, mode in enumerate(MODES):
                try:
                    derived.append(_audit_episode(rows[case*len(MODES)+index], config, case, mode))
                except (ValueError, KeyError, TypeError, IndexError) as exc:
                    findings.append(f"case={case} mode={mode}: {exc}")
        if len(derived) == len(rows):
            summary = summarize(derived)
            if summary != report["summary"]:
                findings.append("summary_or_paired_controls")
            safe = all(r["collisions"] == r["reserve_violations"] == r["unsafe_commands"] == 0
                       and r["disarmed"] and not r["budget_exhausted"] for r in derived)
            coverage = {r["condition"] for r in derived} == set(CONDITIONS)
            integrity = all(r["model_unchanged"] is True and r.get("cam_destroyed") == 0 for r in derived)
            nominal = [r for r in derived if r["mode"] == "echo32" and r["condition"] == "static"]
            faults = [r for r in derived if r["condition"] in ("sensor_stale", "authority_loss")]
            reasoning_used = _reasoning_gate(derived)
            correct = (coverage and safe and integrity and reasoning_used and bool(nominal) and all(r["success"] for r in nominal)
                       and bool(faults) and all(r["sensor_fault_exercised"] and r["fault_latched"] for r in faults))
            compared = summary["controls"]["conventional"]
            gates.update(denominator=True, safety=safe, condition_coverage=coverage, model_integrity=integrity,
                         reasoning_used=reasoning_used, software_correctness=correct, advantage=correct and compared["losses"] == 0
                         and (compared["wins"] > 0 or compared["cost_delta"] < 0))
            if gates != report["gates"]:
                findings.append("claimed_gates")
            if report["costs"] != dict(semantics="logical work per case and mode", used=summary["cost"],
                                       limit=config["cases"]*len(MODES)*config["budget"]):
                findings.append("total_cost_accounting")
        # Comparison with the producer is additional evidence, not the judge
        # above. A fresh Python process imports no saved actor state or traces.
        code = ("import json,os,sys; sys.path.insert(0,sys.argv[1]); "
                "from echo5.mission import run_benchmark; "
                "print(json.dumps({'pid':os.getpid(),'report':run_benchmark(json.load(sys.stdin))},"
                "sort_keys=True,allow_nan=False))")
        process = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(Path(__file__).resolve().parents[1])],
                                 input=json.dumps(config), text=True, capture_output=True, timeout=180)
        if process.returncode:
            findings.append("fresh_replay_failed:"+process.stderr[-500:])
        else:
            output = json.loads(process.stdout)
            replay.update(process_id=output["pid"], exact=output["report"] == report,
                          valid=output["pid"] != os.getpid() and output["report"] == report)
            if not replay["valid"]:
                findings.append("fresh_replay_disagrees")
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.TimeoutExpired) as exc:
        findings.append(type(exc).__name__+": "+str(exc)[:500])
    return dict(schema="echo5.mission.audit.v1", valid=not findings and replay["valid"],
                config=deepcopy(report.get("config")) if type(report) is dict else None,
                rows=derived, summary=summarize(derived), gates=gates, findings=findings,
                replay=replay, auditor_pid=os.getpid(), adjudication="external_world_and_power_safe_gateway")
