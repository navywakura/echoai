"""DREAM-D v2: replay feedback, robust selection and anchored promotion.

Version one and its interpreter are imported unchanged. No new thought bus.
"""
from __future__ import annotations

import random
import time

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_bench import evaluate, rotations, summary
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import Policy, ranking
from echoai.echo4.dream_probe import ProbeArchive, collect, prepare
from echoai.echo4.dream_qwen import LocalQwen, payload
from echoai.echo4.world import Body

V1 = ROOT / "lab/echo4/dream1-bcd-v1"
V1_DIGEST = "5feb033f72d84a673eca26af2ec9145d267d7781073dfed80817fbdfbecdba27"
HISTORY_FILES = ("history-initial.json", "history-online-0.json",
                 "history-online-1.json", "history-online-2.json")
GUIDANCE = (
    "These are measured complete schedules, not individual experiment scores. "
    "Optimize the worst batch margin over fixed, then total resolved, then fewer steps. "
    "Retain enough budget for complementary experiments; all arms allow up to 12. "
    "Earlier termination is automatic once resolved. Costs are 4 or 8 steps, so "
    "a budget of 8 or 10 can discard a useful second experiment. Use feedback "
    "to revise orders, not invent outcomes. Return only the required policy JSON."
)


def binding():
    report = read_json(V1 / "report.json")
    receipt = read_json(V1 / "audit-receipt.json")
    if (report["reproduction_sha256"] != V1_DIGEST or receipt["valid"] is not True
            or receipt["reproduction_sha256"] != V1_DIGEST or receipt["dream1_green"] is not False):
        raise ValueError("v1 evidence identity mismatch")
    unsigned = dict(report)
    unsigned.pop("reproduction_sha256")
    if sha(canonical(unsigned)) != V1_DIGEST:
        raise ValueError("v1 report custody mismatch")
    for name, digest in report["sources"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("v1 source changed: " + name)
    return {p.name: file_hash(p) for p in sorted(V1.iterdir()) if p.is_file()}


def load_history():
    """Validate v1 custody and physically reconstruct every development branch."""
    binding()
    report = read_json(V1 / "report.json")
    expected = [report["initial_history"]["sha256"]]
    expected.extend(c["extension"]["sha256"] for c in report["cycles"])
    prepared, groups = {}, []
    for name, digest in zip(HISTORY_FILES, expected):
        if file_hash(V1 / name) != digest:
            raise ValueError("v1 history custody mismatch")
        rows = []
        for row in read_json(V1 / name):
            body = Body(**row["private_context"]["body"])
            condition = tuple(row["private_context"]["condition"])
            if body not in prepared:
                prepared[body] = prepare(body)
            archive = ProbeArchive.loads(canonical(row["archive"]), row["sha256"])
            if collect(body, condition, prepared[body]).dumps() != archive.dumps():
                raise ValueError("v1 physics reconstruction mismatch")
            rows.append((body, condition, prepared[body], archive))
        groups.append(rows)
    return groups, Policy.from_data(report["active_policy"])


def exam_bodies():
    """Outcome-blind stratification; only the campaign opens these recipes."""
    from itertools import product
    from echoai.echo4.dream_bench import TRAIN, EXAMS
    from echoai.echo4.self_final_audit import GRIDS
    excluded = set(TRAIN)
    excluded.update(b for cycle in EXAMS for b in cycle)
    excluded.update(product(*GRIDS["B"]))
    excluded.update(product(*GRIDS["C"]))
    excluded.update(((77, 50), (76, 51), (78, 52), (79, 53), (80, 54)))
    rng, result = random.Random(260923), []
    for _ in range(3):
        bodies = []
        for start in (65, 73, 81, 89):
            pool = [(h, t) for h in range(start, start + 8) for t in range(40, 61)
                    if (h, t) not in excluded]
            chosen = rng.sample(pool, 4)
            excluded.update(chosen)
            bodies.extend(chosen)
        result.append(tuple(bodies))
    return tuple(result)


def control_candidates(cycle):
    rng = random.Random(260923 + cycle)
    policies = list(rotations())
    while len(policies) < 8:
        order = list(range(6))
        rng.shuffle(order)
        policy = Policy(tuple(order))
        if policy not in policies:
            policies.append(policy)
    return tuple(policies)


class ReplayEvaluator:
    """Private history owner exports only scores of explicitly queried policies."""
    def __init__(self, groups):
        if not groups or any(not g for g in groups):
            raise ValueError("nonempty historical batches required")
        self.groups = groups
        self.cache = {}

    def outcomes(self, policy):
        if policy.identity not in self.cache:
            self.cache[policy.identity] = [evaluate(policy, g, replay=True) for g in self.groups]
        return self.cache[policy.identity]

    def score(self, policy):
        groups = self.outcomes(policy)
        fixed = self.outcomes(Policy())
        gains = [(ranking(g)[0] - ranking(f)[0]) * 1000000 // len(g)
                 for g, f in zip(groups, fixed)]
        flat = [r for group in groups for r in group]
        return (min(gains), *ranking(flat))

    def public(self, policy):
        groups = self.outcomes(policy)
        return {"policy": policy.data(), "score": list(self.score(policy)),
                "batches": [{"cases": len(g), "resolved": ranking(g)[0],
                             "steps": -ranking(g)[1]} for g in groups]}

    def select(self, incumbent, candidates):
        chosen, score = incumbent, self.score(incumbent)
        seen, rows = {incumbent.identity}, [self.public(incumbent)]
        for candidate in candidates:
            if candidate.identity in seen:
                continue
            seen.add(candidate.identity)
            rows.append(self.public(candidate))
            next_score = self.score(candidate)
            if next_score > score:
                chosen, score = candidate, next_score
        return chosen, rows

    def cost(self):
        rows = [r for batches in self.cache.values() for g in batches for r in g]
        return {"policies": len(self.cache), "queries": sum(r["queries"] for r in rows),
                "represented_steps": sum(r["steps"] for r in rows),
                "native_steps": 0, "llm_calls": 0}


def context(evaluator, incumbent, feedback=(), *, empty=False):
    if empty:
        return {"instructions": GUIDANCE, "observed_schedules": [], "feedback": []}
    return {"instructions": GUIDANCE,
            "incumbent": evaluator.public(incumbent),
            "observed_schedules": [evaluator.public(p) for p in rotations()],
            "feedback": [evaluator.public(p) for p in feedback]}


def promote(incumbent, candidate, incumbent_rows, candidate_rows, fixed_rows, *, stopped=False):
    if stopped:
        return incumbent, "operator_stop"
    if not candidate_rows or not len(candidate_rows) == len(incumbent_rows) == len(fixed_rows):
        return incumbent, "insufficient_evidence"
    for rows in (candidate_rows, incumbent_rows, fixed_rows):
        metrics = summary(rows)
        if metrics["wrong"] or metrics["terminalities"] or not metrics["invariants"]:
            return incumbent, "safety_rejection"
    if ranking(candidate_rows) < ranking(incumbent_rows):
        return incumbent, "rollback_incumbent"
    if ranking(candidate_rows) < ranking(fixed_rows):
        return incumbent, "rollback_fixed"
    return candidate, "incumbent_retained" if candidate == incumbent else "accepted"


class FeedbackQwen(LocalQwen):
    """Same owned local backend/DSL, bounded to nine calls for this profile."""
    def propose(self, history, turn):
        if self.calls >= 9:
            raise RuntimeError("v2 model-call budget exhausted")
        self.calls += 1
        request = payload(history, turn)
        start = time.monotonic_ns()
        raw, error = "", ""
        try:
            raw = self._request("/completion", canonical(request), timeout=240).decode()
        except (OSError, ValueError) as exc:
            error = type(exc).__name__
        row = {"request": request, "raw_response": raw, "transport_error": error,
               "elapsed_ms": (time.monotonic_ns() - start) // 1000000,
               "model_sha256": self.metadata["model_sha256"]}
        row["sha256"] = sha(canonical(row))
        return row
