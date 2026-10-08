"""DREAM-v3 evaluation and history-only policy development, fixed weights."""
from __future__ import annotations

from dataclasses import asdict
import json
import random
import time

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_bench import CONDITIONS, TRAIN, persist, summary
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import ranking
from echoai.echo4.dream_qwen import LocalQwen
from echoai.echo4.dream_v2 import ReplayEvaluator as PreviousEvaluator, binding as v1_binding
from echoai.echo4.dream_v2 import exam_bodies as v2_bodies
from echoai.echo4.dream_v3_profile import (
    Archive, CATALOG, CATALOG_SHA, N, PROFILE, Policy, collect, model_for, native,
    parse_candidates, prepare, run_policy,
)
from echoai.echo4.self_audit import cam_hash, private_cause
from echoai.echo4.world import Body

V2 = ROOT / "lab/echo4/dream1-d-v2"
V2_DIGEST = "f5d36371c330c8d3ee439f3710391c744789a9026927b995aa1ae450fd4585ee"
DEVELOPMENT = (TRAIN,) + v2_bodies()


def binding():
    parent = v1_binding()
    report, receipt = read_json(V2 / "report.json"), read_json(V2 / "audit-receipt.json")
    unsigned = dict(report)
    claimed = unsigned.pop("reproduction_sha256")
    if (report["parent"] != parent or claimed != V2_DIGEST or sha(canonical(unsigned)) != claimed
            or receipt["valid"] is not True or receipt["dream1_green"] is not False
            or receipt["reproduction_sha256"] != claimed):
        raise ValueError("v2 identity/custody mismatch")
    for name, digest in report["sources"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("sealed v2 source changed: " + name)
    return {p.name: file_hash(p) for p in sorted(V2.iterdir()) if p.is_file()}


def exam_bodies():
    """New recipes only; no outcomes, models or forecasts in this sampler."""
    from itertools import product
    from echoai.echo4.dream_bench import EXAMS
    from echoai.echo4.self_final_audit import GRIDS
    excluded = {b for group in DEVELOPMENT + EXAMS for b in group}
    excluded.update(product(*GRIDS["B"]))
    excluded.update(product(*GRIDS["C"]))
    excluded.update(((77, 50), (76, 51), (78, 52), (79, 53), (80, 54)))
    result, rng = [], random.Random(260924)
    for _ in range(3):
        bodies = []
        for start in (65, 73, 81, 89):
            pool = [(h, t) for h in range(start, start + 8) for t in range(40, 61)
                    if (h, t) not in excluded]
            selected = rng.sample(pool, 4)
            bodies.extend(selected)
            excluded.update(selected)
        result.append(tuple(bodies))
    return tuple(result)


def cases(bodies):
    rows = []
    for values in bodies:
        body = Body(*values)
        prepared = prepare(body)
        rows.extend((body, condition, prepared) for condition in CONDITIONS)
    return rows


def histories(directory, name, rows, *, checking):
    result, stored = [], []
    for body, condition, prepared in rows:
        archive = collect(body, condition, prepared)
        stored.append({"private_context": {"body": asdict(body), "condition": list(condition)},
                       "archive": json.loads(archive.dumps()), "sha256": sha(archive.dumps())})
        result.append((body, condition, prepared, archive))
    digest = persist(directory, name, stored, checking)
    return result, {"sha256": digest, "contexts": len(rows),
                    "collection_steps": sum(b["native_steps"] for r in stored for b in r["archive"]["branches"]),
                    "branches": sum(len(r["archive"]["branches"]) for r in stored),
                    "calibration_steps": 72 * len({b for b, _, _ in rows})}


def evaluate(policy, rows, *, replay=False, active=False, random_seed=None):
    outcomes = []
    for i, row in enumerate(rows):
        body, condition, prepared = row[:3]
        reference = prepared[0]
        frozen = reference.model_hash(), cam_hash(reference.boundary.cam)
        chosen = policy
        if random_seed is not None:
            order = list(range(N))
            random.Random(random_seed + i).shuffle(order)
            chosen = Policy(tuple(order))
        model = model_for(body, prepared)
        if replay:
            archive = row[3]
            if (archive._data["reference_sha256"] != reference.model_hash()
                    or archive._data["initial"] != model.initial.hex()):
                raise ValueError("archive/reference binding mismatch")
            request = archive.replay().request
        else:
            request = lambda plan: native(body, condition, plan)
        result = run_policy(model, chosen, request, active=active)
        truth = private_cause(*condition)
        result.update(correct=result["diagnosis"]["label"] == truth,
                      wrong=result["diagnosis"]["label"] not in (truth, "unknown"),
                      truth_retained=(body.h, condition[0]) in model.h_candidates
                          and (body.temperature, condition[1], condition[2]) in model.t_candidates,
                      reference_preserved=frozen == (reference.model_hash(), cam_hash(reference.boundary.cam)),
                      cam_facts=sum(s.has_fact for s in reference.boundary.cam.slot if s.occupied),
                      destroyed=reference.boundary.cam.destroyed)
        outcomes.append(result)
    return outcomes


def starters():
    """Eight systematic historical queries, not hand-injected model proposals."""
    policies = []
    for i in range(N):
        prefix = (2, i) if i != 2 else (2,)
        order = prefix + tuple(j for j in range(N) if j not in prefix)
        policy = Policy(order)
        if policy not in policies:
            policies.append(policy)
    policies.append(Policy())
    assert len(set(policies)) == 8
    return tuple(policies)


class ReplayEvaluator(PreviousEvaluator):
    # Reuse selection, public aggregate interface, cache and cost accounting.
    def outcomes(self, policy):
        if policy.identity not in self.cache:
            self.cache[policy.identity] = [evaluate(policy, g, replay=True) for g in self.groups]
        return self.cache[policy.identity]

    def score(self, policy):
        groups, fixed = self.outcomes(policy), self.outcomes(Policy())
        gains = [(ranking(g)[0] - ranking(f)[0]) * 1000000 // len(g)
                 for g, f in zip(groups, fixed)]
        return min(gains), *ranking([r for group in groups for r in group])


def context(evaluator, incumbent, feedback=(), *, empty=False):
    guidance = (
        "Optimize worst historical batch gain, then resolved count, then fewer steps. "
        "Costs are 4 or 8; 12 allows probe2 plus another. Unsafe probes are skipped "
        "and reconsidered after observations: a conditional branch can become safe. "
        "Summaries are measured schedules, not predictions. Use feedback to revise. "
        "All comparisons share eight probes and at most12 native steps."
    )
    if empty:
        return {"instructions": guidance, "observed_schedules": [], "feedback": []}
    return {"instructions": guidance, "incumbent": evaluator.public(incumbent),
            "observed_schedules": [evaluator.public(p) for p in starters()],
            "feedback": [evaluator.public(p) for p in feedback]}


SYSTEM = """Propose bounded experiment schedules for echoAI DREAM-v3.
Return only JSON with candidates: an array of 1 to 4 policies.
Each policy has version:3, order:a permutation of [0,1,2,3,4,5,6,7],
enabled:eight integer 0/1 quotas indexed by experiment, step_budget:integer4..12.
Maximize resolved diagnoses using supplied historical scores, then reduce steps.
The unchanged SELF inference intersects hypotheses from real observations.
An unknown is not success. A safe probe restores the initial body, not the
knowledge state. Safety considers every remaining hypothesis before executing.
Propose diverse policies. No code, prose, private causes or invented outcomes.
"""
GRAMMAR = r'''root ::= "{" ws "\"candidates\"" ws ":" ws "[" ws policy (ws "," ws policy)? (ws "," ws policy)? (ws "," ws policy)? ws "]" ws "}"
policy ::= "{" ws "\"version\"" ws ":" ws "3" ws "," ws "\"order\"" ws ":" ws array ws "," ws "\"enabled\"" ws ":" ws array ws "," ws "\"step_budget\"" ws ":" ws number ws "}"
array ::= "[" ws number ws "," ws number ws "," ws number ws "," ws number ws "," ws number ws "," ws number ws "," ws number ws "," ws number ws "]"
number ::= "0" | [1-9] [0-9]?
ws ::= [ \t\n]*
'''


def payload(history, turn):
    data = {"profile": PROFILE, "catalog_sha256": CATALOG_SHA,
            "catalog": [{"index": i, "actions": a, "cost": len(a)} for i, a in enumerate(CATALOG)],
            "observed_history": history}
    prompt = ("<|im_start|>system\n" + SYSTEM + "<|im_end|>\n<|im_start|>user\n"
              + canonical(data).decode() + "<|im_end|>\n<|im_start|>assistant\n")
    return {"prompt": prompt, "n_predict": 640, "temperature": 0,
            "seed": 260924 + turn, "grammar": GRAMMAR,
            "cache_prompt": False, "stop": ["<|im_end|>"]}


class Qwen(LocalQwen):
    def propose(self, history, turn):
        if self.calls >= 15:
            raise RuntimeError("v3 model-call budget exhausted")
        self.calls += 1
        request, start = payload(history, turn), time.monotonic_ns()
        raw, error = "", ""
        try:
            raw = self._request("/completion", canonical(request), timeout=300).decode()
        except (OSError, ValueError) as exc:
            error = type(exc).__name__
        receipt = {"request": request, "raw_response": raw, "transport_error": error,
                   "elapsed_ms": (time.monotonic_ns() - start) // 1000000,
                   "model_sha256": self.metadata["model_sha256"]}
        receipt["sha256"] = sha(canonical(receipt))
        return receipt


def read_proposal(receipt, history, turn, model_sha):
    unsigned = dict(receipt)
    claimed = unsigned.pop("sha256")
    if sha(canonical(unsigned)) != claimed or receipt["request"] != payload(history, turn):
        raise ValueError("proposal receipt/request mismatch")
    if (receipt["model_sha256"] != model_sha or type(receipt["elapsed_ms"]) is not int
            or receipt["elapsed_ms"] < 0):
        raise ValueError("model/time mismatch")
    cost = {"calls": 1, "prompt_tokens": 0, "generated_tokens": 0,
            "elapsed_ms": receipt["elapsed_ms"]}
    if receipt["transport_error"]:
        return (), cost, receipt["transport_error"]
    try:
        response = json.loads(receipt["raw_response"])
        for field, target in (("tokens_evaluated", "prompt_tokens"), ("tokens_predicted", "generated_tokens")):
            value = response[field]
            if type(value) is not int or value < 0:
                raise ValueError("invalid token accounting")
            cost[target] = value
        if not 0 < cost["generated_tokens"] <= 640 or cost["prompt_tokens"] + cost["generated_tokens"] > 8192:
            raise ValueError("token budget")
        if response.get("truncated") or response.get("stopped_limit"):
            return (), cost, "truncated_generation"
        return parse_candidates(response["content"]), cost, ""
    except (ValueError, TypeError, KeyError) as exc:
        return (), cost, "rejected:" + str(exc)
