"""Public relational mission reasoning, sharing ECHO-5's finite planner.

This module has no world, seed, transport, battery-policy or actuator access.
Unknown cells are excluded from a temporary planning graph, not asserted to
be walls. Nominal motor effects remain declared priors, never learned facts.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json

from . import grounding
from .budget import Budget, BudgetExceeded
from .interaction import HypothesisAgent
from .legacy import module


ENGINE = "echo5.interaction.HypothesisAgent.plan"
SCHEMA = "echo5.mission.reasoning.v2"
OUTCOME_SCHEMA = "echo5.mission.outcome.v2"
VECTORS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0))
# Grid row grows with mission y; grid column grows with mission x.
EFFECT_PRIOR = ((0, 1), (0, -1), (1, 0), (-1, 0))
MAX_OBJECTS = 32
MAX_TARGETS = 8
MAX_WORK = 30_000


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


class _Allowance(Budget):
    """Per-decision cap charged to the episode before each operation."""
    def __init__(self, parent):
        super().__init__(min(MAX_WORK, parent.remaining))
        self.parent = parent

    def consume(self, kind, amount=1):
        if type(amount) is not int or not 0 <= amount <= self.remaining:
            raise BudgetExceeded("mission reasoning allowance")
        self.parent.consume("mission.reasoning."+kind, amount)
        super().consume(kind, amount)

    add = consume


def _grid(point):
    return [point[1]+4, point[0]+4]


def _point(point):
    return [point[1]-4, point[0]-4, 0]


def public_cells(frame, budget):
    """Resolve each cell against only this frame's original sensor captures."""
    gates = module("nexus0.drone3.gates")
    start = tuple(frame["odometry"])
    if len(start) != 3 or start[2] != 0 or any(type(v) is not int or abs(v) > 4 for v in start):
        raise ValueError("reasoning_position_bounds")
    free = {start}
    states = []
    for cell in sorted(frame["cells"], key=lambda c: c["position"]):
        p = tuple(cell["position"])
        if p[2] != 0 or any(abs(v) > 4 for v in p):
            continue
        budget.consume("source_resolution", 1+len(cell["sources"]))
        # A single-cell frame avoids scanning all other records on each query.
        current = dict(frame, cells=[cell])
        gate = gates.epistemic(current, "move", p[:2], frame["now_ns"], [0, 0])
        states.append(dict(position=list(p), allowed=gate["allowed"],
                           value=gate["value"], certainty=gate["certainty"],
                           sources_sha256=_hash(cell["sources"])))
        if gate["allowed"]:
            free.add(p)
    if len(states) > 80 or len({tuple(s["position"]) for s in states}) != len(states):
        raise ValueError("reasoning_cell_capacity")
    return free, states


def _distance(a, b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def validate_outcome(value, pending):
    """Validate public execution evidence; the auditor checks its origin too."""
    keys = {"schema", "sequence", "raw_sha256", "wsp", "prediction", "disposition",
            "command_seq", "ack", "samples", "estimate", "reason"}
    if type(value) is not dict or set(value) != keys or value["schema"] != OUTCOME_SCHEMA:
        raise ValueError("outcome_schema")
    if pending is None or any(value[k] != pending[k] for k in ("sequence", "raw_sha256", "wsp", "prediction")):
        raise ValueError("outcome_not_bound_to_proposal")
    if type(value["sequence"]) is not int or type(value["samples"]) is not int:
        raise ValueError("outcome_integer_fields")
    if value["disposition"] == "not_executed":
        if (value["reason"] not in ("age", "world_changed") or value["samples"] != 0
                or any(value[k] is not None for k in ("command_seq", "ack", "estimate"))):
            raise ValueError("nonexecution_receipt")
        return deepcopy(value)
    if value["disposition"] != "arrived" or value["reason"] != "gateway_complete":
        raise ValueError("outcome_disposition")
    ack, estimate = value["ack"], value["estimate"]
    if (type(value["command_seq"]) is not int or value["command_seq"] < 0
            or not 3 <= value["samples"] <= 10000
            or type(ack) is not dict or set(ack) != {"system", "component", "command", "result", "received_ns"}
            or any(type(v) is not int for v in ack.values())
            or ack["system"] != 1 or ack["component"] != 1 or ack["command"] != 192 or ack["result"] != 0
            or type(estimate) is not dict or set(estimate) != {"position_mm", "received_ns", "speed_mm_s"}):
        raise ValueError("outcome_ack_or_samples")
    xyz = estimate["position_mm"]
    if (type(xyz) is not list or len(xyz) != 3 or any(type(v) is not int for v in xyz)
            or type(estimate["received_ns"]) is not int
            or not pending["observation_ns"] <= ack["received_ns"] < estimate["received_ns"]
            or type(estimate["speed_mm_s"]) is not int or not 0 <= estimate["speed_mm_s"] <= 150):
        raise ValueError("outcome_telemetry_order")
    target = pending["prediction"]
    if ((xyz[0]-3000*target[0])**2+(xyz[1]-3000*target[1])**2 > 350**2
            or abs(xyz[2]-2500) > 300):
        raise ValueError("outcome_arrival_tolerance")
    return deepcopy(value)


class MissionReasoner:
    def __init__(self):
        self.planner = HypothesisAgent(mode="active")
        self.visits = Counter()
        self.last_position = None
        self.consequences = []
        self.resolved_sequences = set()

    def consequence(self, outcome, pending, budget):
        budget.consume("mission.consequence_validation")
        checked = validate_outcome(outcome, pending)
        if checked["sequence"] in self.resolved_sequences or len(self.consequences) >= 64:
            raise ValueError("outcome_duplicate_or_capacity")
        self.resolved_sequences.add(checked["sequence"])
        if (checked["disposition"] == "arrived"
                and module("nexus0.drone3.contract").intention(checked["wsp"])[0] == "move"):
            actual = tuple(checked["prediction"])
            self.visits[actual] += 1
            self.last_position = actual
        # No call to observe(): an ACK/proposal is not a learned motor effect.
        self.consequences.append(checked)
        return checked

    def propose(self, frame, goal, *, sequence, raw_sha256, budget, horizon=4):
        work = _Allowance(budget)
        start, target = tuple(frame["odometry"]), tuple(goal["target_cell"])
        free, states = public_cells(frame, work)
        if start != self.last_position:
            work.consume("observed_position")
            self.visits[start] += 1
            self.last_position = start
        # A bounded shortlist, with immediate admitted neighbours retained.
        neighbours = sorted(p for p in free if _distance(p, start) == 1)
        ranked = sorted(free-{start}, key=lambda p: (_distance(p, target)*10+self.visits[p]*20, p))
        points = list(dict.fromkeys(([target] if target in free and target != start else [])+neighbours+ranked))[:30]
        work.consume("candidate_objects", len(points)+2)
        grid = tuple(tuple(0 for _ in range(9)) for _ in range(9))
        anchor = grounding.Object(9, (tuple(_grid(target)),))  # requested, not observed marker
        body = grounding.Object(4, (tuple(_grid(start)),))
        objects = [grounding.Object(1, (tuple(_grid(p)),)) for p in points]
        scene = grounding.Scene(grid, 0, tuple([anchor, body, *objects]))
        aligned = set(grounding.targets(scene, anchor, "same_row", work))
        aligned.update(grounding.targets(scene, anchor, "same_col", work))
        relations = {p: int(o in aligned) for p, o in zip(points, objects)}
        ordered = sorted(points, key=lambda p: (_distance(p, target)*10+self.visits[p]*20-relations[p], p))
        # Four near-term alternatives remain available even if a distant
        # candidate is disconnected by unknown evidence.
        targets = list(dict.fromkeys(ordered[:4]+neighbours+ordered))[:MAX_TARGETS]
        excluded = [[y, x] for y in range(9) for x in range(9) if (x-4, y-4, 0) not in free]
        candidates = []
        for endpoint in targets:
            obs = dict(schema="echo5.interaction.observation.v1", width=9, height=9,
                       walls=excluded, position=_grid(start), goal=_grid(endpoint),
                       actions=[0, 1, 2, 3], tick=sequence)
            result = self.planner.plan(obs, budget=work, max_depth=horizon, effect_prior=EFFECT_PRIOR)
            if result.get("reason") == "budget_exhausted":
                raise BudgetExceeded("mission shared planner")
            if result["status"] != "planned":
                continue
            positions = [_point(p) for p in result["positions"]]
            revisit = sum(self.visits[tuple(p)]*20 for p in positions[1:])
            score = (-10000+len(result["actions"]) if endpoint == target else
                     10*_distance(endpoint, target)+horizon+revisit-relations[endpoint])
            candidates.append(dict(actions=result["actions"], positions=positions, score=score,
                                   aligned=bool(relations[endpoint]), edge_sources=result["edge_sources"]))
        chosen = min(candidates, key=lambda c: (c["score"], -len(c["actions"]), c["actions"])) if candidates else None
        return dict(schema=SCHEMA, engine=ENGINE, goal_id=goal["goal_id"], sequence=sequence,
                    raw_sha256=raw_sha256, frame_sha256=_hash(frame), horizon=horizon,
                    start_cell=list(start), requested_target=list(target), cells=states,
                    planning_exclusions="unknown_or_not_admitted; not observed walls",
                    effects_basis="declared_nominal_prior", has_fact=False,
                    visits=[[list(p), n] for p, n in sorted(self.visits.items())],
                    targets=[list(p) for p in targets], candidates=candidates,
                    selected=deepcopy(chosen), actions=[] if chosen is None else chosen["actions"],
                    consequence_count=len(self.consequences), work=work.snapshot())


def audit_information(frame, response, counts, mode):
    """Bound information gathering independently from planner and controller."""
    info = response.get("information")
    if info is None:
        if response.get("status") == "inspect_information":
            raise ValueError("missing_information_receipt")
        return 0
    if (type(info) is not dict or set(info) != {"reason", "prior_status", "cell", "index", "total", "blocked_return_cell"}
            or mode == "conventional" or response["status"] != "inspect_information"
            or response["plan_source"] != "echo5_information_probe"
            or response["prediction"] != frame["odometry"] or info["cell"] != frame["odometry"][:2]
            or response["power"]["reason"] not in ("continue", "return")
            or response["energy_check"]["allowed"] is not True):
        raise ValueError("information_input_binding")
    point = tuple(info["cell"])
    if (type(info["index"]) is not int or not 0 <= info["index"] < 4 or info["index"] != counts[point]
            or type(info["total"]) is not int or info["total"] != sum(counts.values())+1 or info["total"] > 12
            or module("nexus0.drone3.contract").intention(response["wsp"]) != ("inspect", 7+info["index"])):
        raise ValueError("information_budget_or_action")
    if info["reason"] == "no_supported_current_path":
        proposal = response["reasoning"].get("proposal")
        if (not response["reasoning"]["called"] or not proposal or proposal["actions"]
                or response["power"]["reason"] != "continue" or response["returning"]
                or info["blocked_return_cell"] is not None):
            raise ValueError("information_missing_path_witness")
    elif info["reason"] == "return_step_not_admitted":
        cell = info["blocked_return_cell"]
        if (info["prior_status"] != "return_not_admitted" or not response["returning"]
                or type(cell) is not list or len(cell) != 2
                or sum(abs(a-b) for a, b in zip(point, cell)) != 1
                or module("nexus0.drone3.gates").epistemic(frame, "move", cell, frame["now_ns"], [0, 0])["allowed"]):
            raise ValueError("information_missing_return_witness")
    else:
        raise ValueError("information_reason")
    counts[point] += 1
    return 1


def audit_reasoning(frame, response, goal, mode):
    """Check path witnesses, their score and independent current admission.

    Does not call MissionReasoner, the shared planner, or run_benchmark. A
    fresh logical producer replay remains an additional, separate check.
    """
    evidence = response.get("reasoning")
    if type(evidence) is not dict or set(evidence) != {"called", "applied", "proposal"}:
        raise ValueError("reasoning_evidence_required")
    if type(evidence["called"]) is not bool or type(evidence["applied"]) is not bool:
        raise ValueError("reasoning_flags")
    if not evidence["called"]:
        if evidence["applied"] or evidence["proposal"] is not None:
            raise ValueError("reasoning_false_attribution")
        if mode != "conventional" and response["status"] == "moving":
            raise ValueError("new_reasoner_bypassed")
        return dict(called=0, applied=0)
    if mode == "conventional":
        raise ValueError("conventional_reasoning_contamination")
    p = evidence["proposal"]
    if (p["schema"] != SCHEMA or p["engine"] != ENGINE or p["goal_id"] != goal["goal_id"]
            or p["sequence"] != response["sequence"] or p["raw_sha256"] != response["raw_sha256"]
            or p["frame_sha256"] != _hash(frame) or p["has_fact"] is not False
            or p["start_cell"] != frame["odometry"] or p["requested_target"] != goal["target_cell"]
            or p["horizon"] != (1 if mode == "one_step" else 4)
            or p["effects_basis"] != "declared_nominal_prior"):
        raise ValueError("reasoning_input_binding")
    work = p["work"]
    if (type(work) is not dict or set(work) != {"limit", "used", "remaining", "counts"}
            or any(type(work[k]) is not int for k in ("limit", "used", "remaining"))
            or not 0 <= work["used"] <= work["limit"] <= MAX_WORK
            or work["remaining"] != work["limit"]-work["used"]
            or type(work["counts"]) is not dict
            or any(type(v) is not int or v < 0 for v in work["counts"].values())
            or sum(work["counts"].values()) != work["used"]):
        raise ValueError("reasoning_work_bound")
    free, cells = public_cells(frame, Budget(MAX_WORK))
    if cells != p["cells"] or not 0 <= len(p["candidates"]) <= MAX_TARGETS or len(p["targets"]) > MAX_TARGETS:
        raise ValueError("reasoning_scene_or_bound")
    visits = {tuple(point): count for point, count in p["visits"]}
    if len(visits) > 81 or any(type(n) is not int or not 1 <= n <= 64 for n in visits.values()):
        raise ValueError("reasoning_visits")
    for candidate in p["candidates"]:
        actions, positions = candidate["actions"], candidate["positions"]
        if (not 1 <= len(actions) <= p["horizon"] or len(positions) != len(actions)+1
                or positions[0] != frame["odometry"] or len(set(map(tuple, positions))) != len(positions)):
            raise ValueError("reasoning_path_bounds")
        for before, action, after in zip(positions, actions, positions[1:]):
            if (type(action) is not int or not 0 <= action <= 3 or tuple(after) not in free
                    or after != [a+b for a, b in zip(before, VECTORS[action])]):
                raise ValueError("reasoning_path_consequence")
        end, target = positions[-1], goal["target_cell"]
        aligned = end[0] == target[0] or end[1] == target[1]
        expected = (-10000+len(actions) if end == target else
                    10*(abs(end[0]-target[0])+abs(end[1]-target[1]))+p["horizon"]
                    +sum(visits.get(tuple(v), 0)*20 for v in positions[1:])-int(aligned))
        if (candidate["score"] != expected or candidate["aligned"] != aligned
                or end not in p["targets"] or candidate["edge_sources"] != ["declared_prior"]*len(actions)):
            raise ValueError("reasoning_objective_or_prior")
    selected = min(p["candidates"], key=lambda c: (c["score"], -len(c["actions"]), c["actions"])) if p["candidates"] else None
    if p["selected"] != selected or p["actions"] != ([] if selected is None else selected["actions"]):
        raise ValueError("reasoning_selected_path")
    applied = response["status"] == "moving" and selected is not None
    if evidence["applied"] != applied:
        raise ValueError("reasoning_applied_claim")
    if applied and (response["plan_source"] != "echo5_reasoner" or response["plan"] != selected["actions"]
                    or response["prediction"] != selected["positions"][1]
                    or module("nexus0.drone3.contract").intention(response["wsp"])[1] != selected["actions"][0]):
        raise ValueError("reasoning_action_binding")
    return dict(called=1, applied=int(applied))
