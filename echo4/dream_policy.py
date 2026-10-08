"""DREAM bounded strategy interpreter. No model, physics executor or file access."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json

from echoai.echo4.continuity import _no_float, _unique_pairs, canonical
from echoai.echo4.dream_history import integer, keys, sha
from echoai.echo4.self_attribution import CATALOG, ProbePlan, SelfAttributor

MAX_STEPS = 12
MAX_CANDIDATES = 4


@dataclass(frozen=True)
class Policy:
    order: tuple[int, ...] = tuple(range(6))
    enabled: tuple[int, ...] = (1,) * 6
    step_budget: int = MAX_STEPS

    def __post_init__(self):
        if type(self.order) is not tuple or len(self.order) != 6:
            raise ValueError("order must be a permutation")
        for index in self.order:
            integer(index, 0, 5)
        if set(self.order) != set(range(6)):
            raise ValueError("duplicate experiment")
        if type(self.enabled) is not tuple or len(self.enabled) != 6:
            raise ValueError("six quotas required")
        for quota in self.enabled:
            integer(quota, 0, 1)
        integer(self.step_budget, 4, MAX_STEPS)

    def data(self):
        return {"version": 1, "order": list(self.order), "enabled": list(self.enabled),
                "step_budget": self.step_budget}

    @property
    def identity(self):
        return sha(canonical(self.data()))

    @classmethod
    def from_data(cls, data):
        keys(data, {"version", "order", "enabled", "step_budget"})
        integer(data["version"], 1, 1)
        if type(data["order"]) is not list or type(data["enabled"]) is not list:
            raise ValueError("JSON arrays required")
        return cls(tuple(data["order"]), tuple(data["enabled"]), data["step_budget"])


def parse_candidates(raw):
    if type(raw) is not str or len(raw.encode()) > 8192:
        raise ValueError("oversized proposal")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_float=_no_float, parse_constant=_no_float)
        keys(value, {"candidates"})
        rows = value["candidates"]
        if type(rows) is not list or not 1 <= len(rows) <= MAX_CANDIDATES:
            raise ValueError("candidate limit")
        return tuple(Policy.from_data(row) for row in rows)
    except (RecursionError, TypeError) as exc:
        raise ValueError("invalid proposal") from exc


def request_plan(model, index, token):
    """Same prior, pending forecasts and consume contract as SELF-B.choose.

    Only experiment priority differs. Private hypothetical candidates belong to
    SELF inference, never to the physical executor or the language model.
    """
    if type(model) is not SelfAttributor:
        raise ValueError("requires native SELF diagnosis")
    integer(index, 0, 5)
    integer(token, model.last_token + 1, (1 << 31) - 1)
    if model.pending is not None:
        raise RuntimeError("pending experiment")
    if model.invalid_reason or model.diagnosis()["label"] != "unknown" or index in model.used:
        return None
    prediction = model._prediction(index)
    if prediction is None:
        return None
    score, hs, ts = prediction
    plan = ProbePlan(token, index, CATALOG[index], score[0], score[1])
    model.pending = (plan, hs, ts)
    model.used.add(index)
    model.last_token = token
    return plan


def run_policy(model, policy, request, *, stopped=lambda: False, active=False):
    """Callback returns observed receipt or None for an unrecorded branch.

    Intent budgets are charged before requests, including unavailable branches;
    physical/replayed steps are counted separately. No repeated experiment.
    """
    if type(policy) is not Policy:
        raise ValueError("validated policy required")
    reserved = steps = terminals = 0
    events = []
    reason = "budget_or_catalog"
    while len(events) < 6:
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
        before = copy.deepcopy(model.diagnosis())
        plan = request_plan(model, index, model.last_token + 1)
        reserved += len(plan.actions)
        receipt = request(plan)
        if receipt is None:
            model.pending = None
            status = "unknown"
        else:
            steps += len(receipt.applied)
            terminals += sum(receipt.terminal)
            model.consume(receipt)
            status = "observed"
        events.append({"experiment": index, "status": status, "before": before,
                       "after": copy.deepcopy(model.diagnosis())})
    return {"diagnosis": model.diagnosis(), "events": events, "steps": steps,
            "reserved_steps": reserved, "queries": len(events), "terminalities": terminals,
            "reason": reason}


def ranking(rows):
    """Public inference result, not the private cause labels."""
    return (sum(r["diagnosis"]["label"] != "unknown" for r in rows),
            -sum(r["steps"] for r in rows))


def select(incumbent, candidates, evaluate):
    best, best_score = incumbent, ranking(evaluate(incumbent))
    scores = [{"policy": incumbent.data(), "score": list(best_score)}]
    seen = {incumbent.identity}
    for candidate in candidates:
        if candidate.identity in seen:
            continue
        seen.add(candidate.identity)
        score = ranking(evaluate(candidate))
        scores.append({"policy": candidate.data(), "score": list(score)})
        if score > best_score:
            best, best_score = candidate, score
    return best, scores


def promotion(incumbent, candidate, incumbent_rows, candidate_rows, *, stopped=False):
    if stopped:
        return incumbent, "operator_stop"
    if not candidate_rows or len(candidate_rows) != len(incumbent_rows):
        return incumbent, "insufficient_evidence"
    if any(r["wrong"] or r["terminalities"] for r in candidate_rows):
        return incumbent, "safety_rejection"
    if ranking(candidate_rows) < ranking(incumbent_rows):
        return incumbent, "rollback_regression"
    return candidate, "accepted" if candidate != incumbent else "incumbent_retained"
