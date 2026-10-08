"""Versioned DREAM-v3 probes and conditional replay; original SELF is sealed.

The additional probes use only native actions. A probe unsafe at the root can
be admitted after genuine evidence removes the dangerous hypotheses. Forecasts
are never receipts; missing conditional branches remain unknown.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, replace
import json

from echoai.echo4.boundary_world import packet
from echoai.echo4.continuity import _no_float, _unique_pairs, canonical
from echoai.echo4.dream_history import digest, integer, keys, sha
from echoai.echo4.dream_probe import decode_trace, native, prepare
from echoai.echo4.self_attribution import (
    CATALOG as LEGACY_CATALOG, ProbePlan, ProbeTrace, SelfAttributor, forecast,
    possible_labels, validate_trace,
)
from echoai.echo4.self_probe_audit import public
from echoai.echo4.self_audit import cam_hash

PROFILE = "echo4-dream-conditional-probes-v3"
CATALOG = LEGACY_CATALOG + ((0, 1, 0, 1, 0, 0, 0, 0),
                            (0, 0, 1, 0, 0, 1, 2, 2))
CATALOG_SHA = sha(canonical(CATALOG))
N = len(CATALOG)
MAX_STEPS = 12
MAX_BRANCHES = 22  # eight singles + 2 * seven ordered pairs involving probe2


@dataclass(frozen=True)
class Policy:
    order: tuple[int, ...] = tuple(range(N))
    enabled: tuple[int, ...] = (1,) * N
    step_budget: int = MAX_STEPS

    def __post_init__(self):
        if type(self.order) is not tuple or len(self.order) != N:
            raise ValueError("eight priorities required")
        for value in self.order:
            integer(value, 0, N - 1)
        if set(self.order) != set(range(N)):
            raise ValueError("priorities must be a permutation")
        if type(self.enabled) is not tuple or len(self.enabled) != N:
            raise ValueError("eight quotas required")
        for value in self.enabled:
            integer(value, 0, 1)
        integer(self.step_budget, 4, MAX_STEPS)

    def data(self):
        return {"version": 3, "order": list(self.order), "enabled": list(self.enabled),
                "step_budget": self.step_budget}

    @property
    def identity(self):
        return sha(canonical({"profile": PROFILE, "catalog": CATALOG_SHA, "policy": self.data()}))

    @classmethod
    def from_data(cls, data):
        keys(data, {"version", "order", "enabled", "step_budget"})
        integer(data["version"], 3, 3)
        if type(data["order"]) is not list or type(data["enabled"]) is not list:
            raise ValueError("JSON arrays required")
        return cls(tuple(data["order"]), tuple(data["enabled"]), data["step_budget"])


def parse_candidates(raw):
    if type(raw) is not str or len(raw.encode()) > 8192:
        raise ValueError("proposal size")
    try:
        data = json.loads(raw, object_pairs_hook=_unique_pairs,
                          parse_float=_no_float, parse_constant=_no_float)
        keys(data, {"candidates"})
        rows = data["candidates"]
        if type(rows) is not list or not 1 <= len(rows) <= 4:
            raise ValueError("candidate limit")
        return tuple(Policy.from_data(row) for row in rows)
    except (TypeError, RecursionError) as exc:
        raise ValueError("invalid proposal") from exc


class Attributor(SelfAttributor):
    """Reuse calibration, finite prior, consume/diagnosis and receipt validation.

    Only the catalog dispatch is new. It has no executor or exact-body input.
    """
    def _prediction(self, index):
        integer(index, 0, N - 1)
        actions = CATALOG[index]
        hs = tuple((c, forecast(c, actions, thermal=False)) for c in self.h_candidates)
        ts = tuple((c, forecast(c, actions, thermal=True)) for c in self.t_candidates)
        if any(seq is None for _, seq in hs + ts):
            return None
        groups = []
        for factors in (hs, ts):
            grouped = {}
            for candidate, seq in factors:
                grouped.setdefault(seq, []).append(candidate)
            groups.append(tuple(grouped.values()))
        score = (max(len(possible_labels(h, t)) for h in groups[0] for t in groups[1]),
                 max(len(h) * len(t) for h in groups[0] for t in groups[1]), len(actions), index)
        return score, hs, ts

    def choose(self, token, *, mode="active"):
        raise RuntimeError("v3 requires its bounded policy interpreter")

    def resources(self):
        return {**super().resources(), "probe_capacity": N}


def model_for(body, prepared):
    reference, nominal = prepared
    return Attributor(reference, packet(body), nominal)


def request_plan(model, index, token):
    if type(model) is not Attributor:
        raise ValueError("requires v3 attributor")
    integer(index, 0, N - 1)
    integer(token, model.last_token + 1, (1 << 31) - 1)
    if model.pending is not None:
        raise RuntimeError("pending probe")
    if model.invalid_reason or model.diagnosis()["label"] != "unknown" or index in model.used:
        return None
    prediction = model._prediction(index)
    if prediction is None:
        return None
    score, hs, ts = prediction
    plan = ProbePlan(token, index, CATALOG[index], score[0], score[1])
    model.pending, model.last_token = (plan, hs, ts), token
    model.used.add(index)
    return plan


def run_policy(model, policy, request, *, active=False, stopped=lambda: False):
    if type(policy) is not Policy or type(model) is not Attributor:
        raise ValueError("profile mismatch")
    reserved = steps = terminals = 0
    events = []
    reason = "budget_or_catalog"
    while len(events) < N:
        if stopped():
            reason = "operator_stop"
            break
        if model.invalid_reason or model.diagnosis()["label"] != "unknown":
            reason = model.diagnosis()["reason"]
            break
        eligible = [i for i in policy.order if policy.enabled[i] and i not in model.used
                    and reserved + len(CATALOG[i]) <= policy.step_budget
                    and model._prediction(i) is not None]
        if not eligible:
            break
        index = min(eligible, key=lambda i: model._prediction(i)[0]) if active else eligible[0]
        before = model.diagnosis()
        plan = request_plan(model, index, model.last_token + 1)
        reserved += len(plan.actions)
        receipt = request(plan)
        if receipt is None:
            model.pending = None
            status = "unknown"
        else:
            # Validation still belongs to original SELF.consume, never to Qwen.
            model.consume(receipt)
            if type(receipt) is ProbeTrace:
                steps += len(receipt.applied) if type(receipt.applied) is tuple else 0
                terminals += sum(t is True for t in receipt.terminal) if type(receipt.terminal) is tuple else 0
            status = "observed"
        events.append({"experiment": index, "status": status,
                       "before": before, "after": model.diagnosis()})
    return {"diagnosis": model.diagnosis(), "events": events, "steps": steps,
            "reserved_steps": reserved, "queries": len(events),
            "terminalities": terminals, "reason": reason}


class Archive:
    MAX_BYTES = 262144

    def __init__(self, data):
        keys(data, {"profile", "catalog_sha256", "initial", "reference_sha256", "branches"})
        if data["profile"] != PROFILE or data["catalog_sha256"] != CATALOG_SHA:
            raise ValueError("archive profile/catalog mismatch")
        digest(data["reference_sha256"])
        if type(data["initial"]) is not str or len(data["initial"]) != 32:
            raise ValueError("initial WSP16 required")
        initial = bytes.fromhex(data["initial"])
        if type(data["branches"]) is not list or len(data["branches"]) > MAX_BRANCHES:
            raise ValueError("branch budget")
        paths = set()
        for row in data["branches"]:
            keys(row, {"path", "receipt", "native_steps"})
            path = row["path"]
            if type(path) is not list or not 1 <= len(path) <= 2:
                raise ValueError("invalid branch path")
            for i in path:
                integer(i, 0, N - 1)
            if len(set(path)) != len(path) or sum(len(CATALOG[i]) for i in path) > MAX_STEPS:
                raise ValueError("invalid path budget")
            key = tuple(path)
            if key in paths:
                raise ValueError("duplicate branch")
            paths.add(key)
            validate_trace(decode_trace(row["receipt"]), initial, CATALOG[path[-1]], 17 + len(path))
            integer(row["native_steps"], len(CATALOG[path[-1]]), len(CATALOG[path[-1]]))
        if any(len(p) > 1 and p[:-1] not in paths for p in paths):
            raise ValueError("orphan conditional branch")
        self._data = copy.deepcopy(data)
        if len(self.dumps()) > self.MAX_BYTES:
            raise ValueError("oversized archive")

    def dumps(self):
        return canonical(self._data)

    @classmethod
    def loads(cls, raw, expected_sha256):
        digest(expected_sha256)
        if type(raw) is not bytes or len(raw) > cls.MAX_BYTES or sha(raw) != expected_sha256:
            raise ValueError("archive custody mismatch")
        try:
            return cls(json.loads(raw, object_pairs_hook=_unique_pairs,
                                  parse_float=_no_float, parse_constant=_no_float))
        except (UnicodeDecodeError, RecursionError) as exc:
            raise ValueError("invalid archive encoding") from exc

    def replay(self):
        return Replay(self)


class Replay:
    def __init__(self, archive):
        self._data = copy.deepcopy(archive._data)
        self._path = ()
        self._revealed = []
        self.queries = self.steps = self.reserved = 0

    def view(self):
        return {"initial": self._data["initial"], "observed": copy.deepcopy(self._revealed),
                "queries": self.queries, "represented_steps": self.steps,
                "replay_native_steps": 0, "replay_llm_calls": 0}

    def request(self, plan):
        if type(plan) is not ProbePlan:
            raise ValueError("requires ProbePlan")
        integer(plan.index, 0, N - 1)
        integer(plan.token, 18 + self.queries, 18 + self.queries)
        if plan.actions != CATALOG[plan.index] or plan.index in self._path:
            raise ValueError("invalid or repeated branch")
        if self.reserved + len(plan.actions) > MAX_STEPS:
            raise RuntimeError("replay step budget")
        self.queries += 1
        self.reserved += len(plan.actions)
        self._path += (plan.index,)
        row = next((r for r in self._data["branches"] if tuple(r["path"]) == self._path), None)
        if row is None:
            return None
        self.steps += row["native_steps"]
        self._revealed.append(copy.deepcopy(row))
        return replace(decode_trace(row["receipt"]), token=plan.token)


def collect(body, condition, prepared):
    """Execute only admissible paths; children inherit real parent observations."""
    reference = prepared[0]
    frozen = reference.model_hash(), cam_hash(reference.boundary.cam)
    branches = []

    def visit(model, prefix, budget):
        for index, actions in enumerate(CATALOG):
            if len(actions) > budget or index in model.used:
                continue
            child = copy.copy(model)
            child.used = set(model.used)
            plan = request_plan(child, index, child.last_token + 1)
            if plan is None:
                continue
            trace = native(body, condition, plan)
            validate_trace(trace, child.initial, plan.actions, plan.token)
            child.consume(trace)
            if child.invalid_reason:
                raise ValueError("collection contradicts declared prior")
            path = prefix + (index,)
            branches.append({"path": list(path), "receipt": json.loads(canonical(public(trace))),
                             "native_steps": len(trace.applied)})
            visit(child, path, budget - len(actions))

    visit(model_for(body, prepared), (), MAX_STEPS)
    if frozen != (reference.model_hash(), cam_hash(reference.boundary.cam)):
        raise ValueError("nominal reference modified")
    return Archive({"profile": PROFILE, "catalog_sha256": CATALOG_SHA,
                    "initial": packet(body).hex(), "reference_sha256": reference.model_hash(),
                    "branches": branches})
