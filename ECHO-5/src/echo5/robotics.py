"""Bounded discrete robotics integration; this module does not launch flight.

The actor receives public WSP sensor receipts and estimated cell odometry.
The simulator is imported only inside the evaluator. COMPOSE/FUSION/DRONE-3
provide the controller, evidence reduction and independent movement admission.
Hashes bind receipts to their contents, not to an authenticated physical sensor.
"""

import hashlib
import json

from .budget import Budget, BudgetExceeded
from .legacy import module


SCHEMA = "echo5.robotics.observation.v1"
TTL_NS = 250_000_000
MAX_CELLS = 128
MAX_TURNS = 64
MODES = ("echo32", "one_step", "conventional")
CONDITIONS = ("static", "dynamic", "closed", "low_energy")
_SCAN_KEYS = {"now_ns", "odometry", "energy", "station_observed", "cells"}
_OBS_KEYS = {"schema", "sequence", "capture_ns", "delivered_ns", "odometry",
             "energy", "station_observed", "cells", "sha256"}
_SOURCE_KEYS = {"source", "wsp", "capture_ns", "delivered_ns", "raw_sha256"}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def _point(value):
    if (type(value) not in (list, tuple) or len(value) != 3
            or any(not _integer(v, -8, 8) for v in value) or value[2] != 0):
        raise ValueError("bounded_planar_position")
    return tuple(value)


def _keys(value, expected, reason):
    if type(value) is not dict or value.keys() != expected:
        raise ValueError(reason)


def _stamp(capture, delivered, now):
    if (not _integer(capture) or not _integer(delivered)
            or not capture <= delivered <= now or now - capture > TTL_NS):
        raise ValueError("stale_or_invalid_timestamp")


def _wsp(value):
    if type(value) is not str or len(value) != 32:
        raise ValueError("sensor_wsp")
    raw = bytes.fromhex(value)
    fusion = module("nexus0.fusion1.core")
    state, certainty, predicate, region, epoch = fusion.unpack(raw)
    if (predicate, region, epoch) != (fusion.BARRIER, 0, 0):
        raise ValueError("sensor_wsp_address")
    if certainty != (0 if state == fusion.UNKNOWN else 40):
        raise ValueError("sensor_certainty")
    return raw.hex()


def observation_from_scan(scan, *, sequence):
    """Wrap the *public* discrete Space.scan() result in timestamped receipts.

    This adapter attests software-generated readings only. Never use it to
    relabel stale physical samples with the current time; physical adapters
    must supply their original capture/delivery times and independent identity.
    """
    _keys(scan, _SCAN_KEYS, "public_scan_schema")
    if not _integer(sequence) or not _integer(scan["now_ns"]):
        raise ValueError("scan_sequence_or_time")
    _point(scan["odometry"])
    if (not _integer(scan["energy"], 0, 1000)
            or type(scan["station_observed"]) is not bool
            or type(scan["cells"]) is not list or len(scan["cells"]) > MAX_CELLS):
        raise ValueError("scan_bounds")
    cells = []
    for cell in scan["cells"]:
        _keys(cell, {"position", "depth", "lidar"}, "scan_cell_schema")
        position = list(_point(cell["position"]))
        sources = []
        for source in ("depth", "lidar"):
            record = dict(source=source, wsp=_wsp(cell[source]),
                          capture_ns=scan["now_ns"], delivered_ns=scan["now_ns"])
            record["raw_sha256"] = _digest(dict(position=position, **record))
            sources.append(record)
        cells.append(dict(position=position, sources=sources))
    result = dict(schema=SCHEMA, sequence=sequence, capture_ns=scan["now_ns"],
                  delivered_ns=scan["now_ns"], odometry=list(scan["odometry"]),
                  energy=scan["energy"], station_observed=scan["station_observed"], cells=cells)
    result["sha256"] = _digest(result)
    return result


def _controller(goal, mode, budget):
    budget.consume("robotics.model_init")
    effects = module("nexus0.compose1.model").Effects()
    # Explicit synthetic prior: two declared cell displacements per horizontal
    # primitive, no rewards, rooms, old school artifacts or flight receipts.
    for action, delta in enumerate(((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))):
        for _ in range(2):
            budget.consume("robotics.prior_observation")
            effects.observe_effect(True, action, delta)
    budget.consume("robotics.controller_init")
    return module("nexus0.compose1_v3.controller").Composer(effects.snapshot(), goal, mode)


class RoboticsBridge:
    """Public receipt -> existing WSP controller -> independent gate -> action.

    Rejection and budget exhaustion produce a canonical STOP without ingesting
    the rejected observation. `now_ns` is the receiver's clock, never taken
    from untrusted sensor claims. One instance owns one bounded mission.
    """

    def __init__(self, goal, *, budget, mode="echo32", journal=None):
        goal = _point(goal)
        if mode not in MODES or not isinstance(budget, Budget):
            raise ValueError("mode_or_budget")
        self.budget = budget
        self.controller = _controller(goal, mode, budget)
        self.journal = journal
        self.sequence = -1
        self.last_now = self.last_capture = -1
        self.position = None
        self.turns = 0

    def _validate(self, observation, now):
        self.budget.consume("robotics.validation")
        _keys(observation, _OBS_KEYS, "observation_schema")
        if (observation["schema"] != SCHEMA or not _integer(now)
                or not _integer(observation["sequence"])
                or observation["sequence"] != self.sequence + 1
                or now <= self.last_now):
            raise ValueError("schema_sequence_or_clock")
        _stamp(observation["capture_ns"], observation["delivered_ns"], now)
        if observation["capture_ns"] <= self.last_capture:
            raise ValueError("replayed_capture")
        position = _point(observation["odometry"])
        if (not _integer(observation["energy"], 0, 1000)
                or type(observation["station_observed"]) is not bool
                or type(observation["cells"]) is not list
                or len(observation["cells"]) > MAX_CELLS):
            raise ValueError("observation_bounds")
        seen = set()
        cells = []
        for cell in observation["cells"]:
            self.budget.consume("robotics.cell_validation")
            _keys(cell, {"position", "sources"}, "cell_schema")
            p = _point(cell["position"])
            if (p in seen or type(cell["sources"]) is not list
                    or not 1 <= len(cell["sources"]) <= 3):
                raise ValueError("duplicate_cell_or_source_bounds")
            seen.add(p)
            sources = set()
            records = []
            for record in cell["sources"]:
                self.budget.consume("robotics.source_validation")
                _keys(record, _SOURCE_KEYS, "provenance_schema")
                source = record["source"]
                if type(source) is not str or source not in ("depth", "rgb", "lidar") or source in sources:
                    raise ValueError("sensor_identity")
                sources.add(source)
                _stamp(record["capture_ns"], record["delivered_ns"], now)
                if record["delivered_ns"] > observation["delivered_ns"]:
                    raise ValueError("sensor_arrival_after_frame")
                wsp = _wsp(record["wsp"])
                payload = {k: v for k, v in record.items() if k != "raw_sha256"}
                if (type(record["raw_sha256"]) is not str or len(record["raw_sha256"]) != 64
                        or record["raw_sha256"] != _digest(dict(position=cell["position"], **payload))):
                    raise ValueError("sensor_digest")
                records.append(dict(record, wsp=wsp))
            cells.append(dict(position=list(p), sources=records))
        if len(seen | self.controller.cells.keys()) > 256:
            raise ValueError("spatial_capacity")
        if (type(observation["sha256"]) is not str or len(observation["sha256"]) != 64
                or observation["sha256"] != _digest({k: v for k, v in observation.items() if k != "sha256"})):
            raise ValueError("observation_digest")
        return dict(physical=True, now_ns=now, odometry=list(position),
                    energy=observation["energy"], station_observed=observation["station_observed"], cells=cells)

    def _stop(self, status, reason):
        c = module("nexus0.drone3.contract")
        return dict(action=c.STOP, wsp=c.pack(src=2, rel=c.OBSERVE, dst=5, time=8,
                    E={}, domain=9, generator=8, style=c.STOP).hex(),
                    prediction=None if self.position is None else list(self.position),
                    status=status, reason=reason, gate=dict(allowed=False, reason=reason),
                    candidates=0, budget_used=self.budget.used)

    def _record(self, **facts):
        if self.journal is not None:
            # Give the observer a copy. It never becomes policy input.
            self.journal.write(**json.loads(json.dumps(facts, allow_nan=False)))

    def decide(self, observation, *, now_ns):
        try:
            if self.turns >= MAX_TURNS:
                raise ValueError("turn_capacity")
            frame = self._validate(observation, now_ns)
            # Reserve worst-case candidate work before running the unmodified
            # controller. Other units denote bounded operations, not CPU cycles.
            self.budget.consume("robotics.controller_decision")
            self.budget.consume("robotics.search_reservation", self.controller.budget)
            self.budget.consume("robotics.gate_reservation", 2)
        except BudgetExceeded:
            result = self._stop("budget_exhausted", "work_limit")
        except ValueError as exc:
            result = self._stop("rejected", str(exc))
        else:
            self.sequence = observation["sequence"]
            self.last_now, self.last_capture = now_ns, observation["capture_ns"]
            self.position = tuple(frame["odometry"])
            self.turns += 1
            self._record(kind="robotics_observation", sequence=self.sequence,
                         observation=observation, receiver_now_ns=now_ns)
            proposal = self.controller.decide(frame)
            c = module("nexus0.drone3.contract")
            gates = module("nexus0.drone3.gates")
            try:
                kind, action = c.intention(proposal["wsp"])
                target = _point(proposal["prediction"])
                expected = (self.position[0] + c.VECTORS[action][0],
                            self.position[1] + c.VECTORS[action][1], 0) if kind == "move" else self.position
                if target != expected or kind not in ("move", "stop"):
                    raise ValueError("prediction_intention_mismatch")
                gate = gates.epistemic(frame, kind, target[:2], now_ns, (0, 0))
                if kind == "move":
                    back = gates.route_length([p[:2] for p in self.controller.visits],
                                              target[:2], self.controller.home[:2])
                    required = None if back is None else 4 + back * 4 + 10
                    gate["reserve_required"] = required
                    if required is None or frame["energy"] < required:
                        gate.update(allowed=False, reason="return_reserve")
                result = dict(proposal, action=action, gate=gate, budget_used=self.budget.used)
                if not gate["allowed"]:
                    result = dict(self._stop("vetoed", gate["reason"]), gate=gate,
                                  proposed_wsp=proposal["wsp"], proposed_prediction=proposal["prediction"])
                    self.controller.pending = []
                    self.controller.last_prediction = self.position
            except ValueError as exc:
                result = self._stop("vetoed", str(exc))
                self.controller.pending = []
                self.controller.last_prediction = self.position
        self._record(kind="robotics_action", response=result)
        return result


def _episode(seed, condition, mode, budget, journal):
    """Evaluator owns geometry and consequences; neither enters the actor."""
    result = dict(seed=seed, condition=condition, mode=mode, status="budget_exhausted", success=False,
                  collisions=0, reserve_violations=0, steps=0, candidates=0,
                  prediction_errors=0, model_unchanged=None, observations=0,
                  budget_limit=budget.limit, budget_exhausted=False,
                  final_position=None, goal=None, station_observed=None)
    start_used = budget.used
    world = actor = None
    try:
        budget.consume("robotics.world_init")
        world = module("nexus0.compose1_v3.space").Space(seed, condition)
        result["goal"] = list(world.goal)
        actor = RoboticsBridge(list(world.goal), budget=budget, mode=mode, journal=journal)
        before = actor.controller.model.fingerprint()
        for sequence in range(MAX_TURNS):
            budget.consume("robotics.simulator_scan")
            scan = world.scan()
            result["station_observed"] = scan["station_observed"]
            budget.consume("robotics.sensor_receipts", 2 * len(scan["cells"]))
            obs = observation_from_scan(scan, sequence=sequence)
            response = actor.decide(obs, now_ns=scan["now_ns"])
            result["observations"] += 1
            result["status"] = response["status"]
            result["candidates"] += response["candidates"]
            result["prediction_errors"] = actor.controller.prediction_errors
            if response["action"] == 6:
                # Recompute success against simulator state; actor flags alone
                # cannot certify arrival. A safety stop isn't task completion.
                budget.consume("robotics.adjudication")
                result["success"] = (response["status"] == "reached" and world.pos == world.goal
                                     and scan["station_observed"] is True and world.collisions == 0
                                     and result["reserve_violations"] == 0)
                break
            budget.consume("robotics.simulator_step")
            budget.consume("robotics.adjudication")
            consequence = world.step(response["action"])
            result["station_observed"] = None  # no post-step observation yet
            home = world.home_distance(world.pos)
            result["reserve_violations"] += int(home is None or world.energy < home * 4 + 10)
            if journal is not None:
                journal.write(kind="robotics_consequence", consequence=consequence)
        else:
            result["status"] = "turn_limit"
    except BudgetExceeded:
        result["status"] = "budget_exhausted"
        result["success"] = False
    if actor is not None:
        result["model_unchanged"] = before == actor.controller.model.fingerprint()
    if world is not None:
        result.update(collisions=world.collisions, steps=world.steps, energy_remaining=world.energy,
                      final_position=list(world.pos))
    result["cost"] = budget.used - start_used
    result["costs"] = dict(sorted(budget.counts.items()))
    result["budget_exhausted"] = result["status"] == "budget_exhausted"
    return result


def _summarize(rows):
    return dict(successes=sum(r["success"] for r in rows), denominator=len(rows),
                collisions=sum(r["collisions"] for r in rows),
                reserve_violations=sum(r["reserve_violations"] for r in rows),
                budget_exhausted=sum(r["budget_exhausted"] for r in rows),
                statuses={status: sum(r["status"] == status for r in rows)
                          for status in sorted({r["status"] for r in rows})},
                cost=sum(r["cost"] for r in rows))


class _PartitionBudget(Budget):
    """Equal episode ceiling, also charged to the caller *before* each operation."""

    def __init__(self, limit, parent):
        super().__init__(limit)
        self.parent = parent

    def consume(self, kind, amount=1):
        if amount > self.remaining:
            raise BudgetExceeded(f"{kind}: episode ceiling")
        self.parent.consume(kind, amount)
        super().consume(kind, amount)

    add = consume


def run_benchmark(seed=20261010, cases=8, budget=10_000, *, journal=None):
    """New deterministic development episodes, paired with two control modes.

    Integer `budget` is the limit PER CASE PER MODE, including setup, sensors,
    decisions, simulation and adjudication. A supplied Budget instead denotes
    a shared total: its remaining allowance is divided equally between episodes.
    Unstarted/exhausted cases remain in every denominator. No old benchmark,
    campaign, calibration artifact, or private exam is opened.
    """
    if not _integer(seed, 0, 2**32 - 1) or not _integer(cases, 1, 64):
        raise ValueError("bounded_seed_and_cases")
    if isinstance(budget, Budget):
        ledger = budget
        allowance = ledger.remaining // (len(MODES) * cases)
        semantics = "shared total divided equally across cases and modes"
    else:
        allowance = Budget(budget).limit
        ledger = Budget(allowance * len(MODES) * cases)
        semantics = "integer budget per case per mode"
    initial_used, initial_counts = ledger.used, dict(ledger.counts)
    arms = {}
    for mode in MODES:
        rows = []
        for index in range(cases):
            local = _PartitionBudget(allowance, ledger)
            row = _episode((seed + index) % 2**32, CONDITIONS[index % len(CONDITIONS)],
                           mode, local, journal)
            rows.append(row)
        arms[mode] = rows
    rows = arms["echo32"]
    controls = {mode: dict(_summarize(arms[mode]), cases=arms[mode],
                          wins=sum(a["success"] and not b["success"] for a, b in zip(rows, arms[mode])),
                          losses=sum(b["success"] and not a["success"] for a, b in zip(rows, arms[mode])),
                          ties=sum(a["success"] == b["success"] for a, b in zip(rows, arms[mode])))
                for mode in MODES[1:]}
    counts = {k: v - initial_counts.get(k, 0) for k, v in ledger.counts.items()
              if v != initial_counts.get(k, 0)}
    report = dict(schema="echo5.robotics.benchmark.v1", seed=seed, **_summarize(rows), cases=rows,
                  controls=controls, simulator="nexus0.compose1_v3.space.Space", sitl_executed=False,
                  scope="synthetic discrete planar development; no flight validation",
                  model_source="fixed synthetic displacement prior; no inherited flight training",
                  costs=dict(used=ledger.used - initial_used, counts=dict(sorted(counts.items())),
                             total_limit=allowance * len(MODES) * cases, budget_semantics=semantics,
                             per_case_per_mode_limit=allowance,
                             accounting="bounded logical operations and worst-case search reservations; not time or joules"))
    if journal is not None:
        journal.write(kind="robotics_result", report=report)
    return report


__all__ = ["RoboticsBridge", "observation_from_scan", "run_benchmark"]
