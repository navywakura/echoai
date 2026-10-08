"""Small paired-seed LLM pilot, gated by a completed human capacity control."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from types import FunctionType

from seed import s6_capacity as capacity
from seed import game_selfimprove_b4 as b4
from seed.game_selfimprove import atomic, canonical, sha

REPO = b4.REPO
ROOT = REPO / "lab/seed/s6-prompt-pilot-20260928"
BASE = REPO / "lab/kaggle/s6-prompt-pilot-20260928"
SEEDS = (602001, 602017, 602029)
ARMS = ("fijo", "echo")
SOURCES = list(dict.fromkeys(capacity.SOURCES + ["seed/s6_prompt_pilot.py",
    "tests/test_s6_prompt_pilot.py", "docs/ECHO45-S6-PROMPT-PILOT.md",
    "lab/kaggle/s6-prompt-pilot-20260928/generate.py",
    "lab/kaggle/s6-prompt-pilot-20260928/transport.py"]))
INPUTS = ["lab/seed/s6-capacity-20260928/profile.json",
          "lab/seed/s6-capacity-20260928/historical-diagnostic.json",
          "lab/seed/s6b4-20260928/baseline-local.json",
          "lab/seed/s6b4-20260928/local-fijo/journal.jsonl",
          "lab/seed/s6b4-20260928/local-echo/journal.jsonl"]


def configuration():
    return {"purpose": "DEVELOPMENT_PROMPT_AND_DIVERSITY_PILOT", "A": b4.A, "B": b4.B,
            "seeds": SEEDS, "calls_per_arm_per_seed": 2, "calibration_calls": 2,
            "max_llm_calls": 14, "max_games": 2720, "workers": capacity.WORKERS,
            "model": b4.MODEL, "revision": b4.REVISION, "temperature": .7,
            "top_p": .95, "max_new_tokens": 900, "max_gpu_job_seconds": 900,
            "paid": False, "exam_access": False,
            "gate": "completed positive human control with intact profile",
            "requests": "precomputed from B4 A diary plus measured activation feedback; no human candidate",
            "adaptation": "verification composes accepted patches; no prompt adaptation within this pilot",
            "promote": "ECHO accepts >=1; sum of paired final A levels ECHO > FIJO; all accepted pass V1-V4"}


def digests(paths):
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in paths}


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == digests(SOURCES), "pilot sources changed"
    assert profile["inputs"] == digests(INPUTS), "pilot development inputs changed"
    assert profile["configuration"] == json.loads(canonical(configuration()))
    assert profile["runtime"] == capacity.runtime()
    capacity.integrity()
    return profile


def prepare():
    capacity.integrity()
    profile = {"sources": digests(SOURCES), "inputs": digests(INPUTS),
               "configuration": configuration(), "runtime": capacity.runtime()}
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / "profile.json"
    if path.exists():
        assert json.loads(path.read_text()) == json.loads(canonical(profile))
    else:
        for source in SOURCES + INPUTS:
            target = ROOT / "source-archive" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as f:
                f.write((REPO / source).read_bytes())
        atomic(path, profile)
        atomic(ROOT / "prepared.json", {"at": capacity.now(), "profile_sha256": sha(profile)})
    integrity()


def positive_gate(summary, profile_digest):
    if summary.get("status") != "POSITIVE_CONTROL" or summary.get("profile_sha256") != profile_digest:
        raise ValueError("no completed positive human control")
    winner = summary.get("winner")
    verdict = next((v for v in summary.get("verdicts", []) if v.get("name") == winner), None)
    if (not verdict or verdict.get("verdict") != "POSITIVE_CONTROL" or
            verdict["A"]["gain"] < 2 or verdict["A"]["loss_indices"] or
            "B" not in verdict or verdict["B"]["loss_indices"]):
        raise ValueError("positive-control evidence does not pass original filters")


def requests():
    measured = json.loads((b4.ROOT / "baseline-local.json").read_text())
    diagnostic = json.loads((capacity.ROOT / "historical-diagnostic.json").read_text())
    out = {}
    for repetition, seed in enumerate(SEEDS):
        for arm in ARMS:
            native = "local-" + arm
            _, stats, accepted, feedback = b4.reconstruct(native)
            assert not accepted, "historical B4 promoted unexpectedly"
            last = dict(feedback[-1], activation_feedback={k: diagnostic[native][k] for k in
                        ("activated_games", "activation_count", "changed_action_games", "gain", "unique_proposals")})
            batch = b4.requests(native, repetition, repetition * 2, 2, b4.strategy("local"),
                                stats, measured, [], [last])
            for item in batch:
                item["prompt"] += (" Activation feedback counts actual matches, not useful action changes. "
                                   "Repeated rejected proposals need new evidence. Choose a condition that applies "
                                   "when the changed parameter is consumed; matching alone is insufficient.")
            out[f"local-{arm}-{seed}"] = batch
    return out


# Reuse immutable native execution and this control's independent cache/replay engine.
measure = FunctionType(capacity.measure.__code__, dict(capacity.measure.__globals__,
    ROOT=ROOT, LIVE=REPO / "lab/observability/s6-prompt-pilot-20260928", integrity=integrity,
    status=lambda stage, **data: status(stage, **data)), capacity.measure.__name__, capacity.measure.__defaults__)


def status(stage, **data):
    row = dict(at=datetime.now(timezone.utc).isoformat(), stage=stage, **data)
    atomic(ROOT / "status.json", row)
    print(json.dumps(row), flush=True)


def verify(label, proposal, current, before_a, before_b):
    try:
        program = b4.patch.parse(proposal)
        candidate = b4.strategy("local", b4.patch.append(current["program"], program))
    except ValueError as exc:
        return current, before_a, before_b, {"verdict": "V1", "reason": str(exc)}
    a = measure(label + "/A", candidate, b4.A)
    replay = measure("replay/" + label + "/A", candidate, b4.A)
    verdict = {"proposal": program, "candidate": candidate, "A": capacity.result(before_a, a)}
    if a["trace_digest"] != replay["trace_digest"]:
        verdict.update(verdict="V2", reason="A replay differs")
    elif a["levels"] < before_a["levels"] + 2 or not b4.no_regressions(before_a, a):
        verdict.update(verdict="V3", reason="under two A levels gain or individual A regression")
    else:
        b = measure(label + "/B", candidate, b4.B)
        replay_b = measure("replay/" + label + "/B", candidate, b4.B)
        verdict["B"] = capacity.result(before_b, b)
        if b["trace_digest"] != replay_b["trace_digest"]:
            verdict.update(verdict="V2", reason="B replay differs")
        elif not b4.no_regressions(before_b, b):
            verdict.update(verdict="V4", reason="protected B regression")
        else:
            verdict.update(verdict="accepted", reason="original V1-V4 pass")
            return candidate, a, b, verdict
    return current, before_a, before_b, verdict


def run():
    profile = integrity()
    summary_path = capacity.ROOT / "summary.json"
    assert summary_path.exists(), "capacity control has not closed"
    positive_gate(json.loads(summary_path.read_text()), sha(capacity.integrity()))
    batches = requests()
    if (ROOT / "requests.json").exists():
        assert json.loads((ROOT / "requests.json").read_text()) == batches
    else:
        atomic(ROOT / "requests.json", batches)
    status("GENERATING", llm_calls=14)
    spec = __import__("importlib.util", fromlist=["spec_from_file_location"])
    definition = spec.spec_from_file_location("_prompt_pilot_generate", BASE / "generate.py")
    generator = spec.module_from_spec(definition)
    definition.loader.exec_module(generator)
    answers = generator.propose(batches, sha(profile))
    empty = b4.strategy("local")
    baseline_a = measure("baseline/A", empty, b4.A)
    baseline_b = measure("baseline/B", empty, b4.B)
    historical = json.loads((b4.ROOT / "baseline-local.json").read_text())
    assert all(capacity.same_behavior(b, a) for b, a in zip(historical["rows"], baseline_a["rows"]))
    replay_a = measure("baseline/replay-A", empty, b4.A)
    replay_b = measure("baseline/replay-B", empty, b4.B)
    assert baseline_a["trace_digest"] == replay_a["trace_digest"]
    assert baseline_b["trace_digest"] == replay_b["trace_digest"]
    verdicts, final = [], []
    for seed in SEEDS:
        for arm in ARMS:
            key = f"local-{arm}-{seed}"
            current, a, b = empty, baseline_a, baseline_b
            for request, answer in zip(batches[key], answers["arms"][key]):
                label = key + "/" + str(request["id"])
                current, a, b, verdict = verify(label, answer["answer"], current, a, b)
                verdict.update(arm=arm, seed=seed, id=request["id"], type=request["type"],
                               prompt_sha256=sha(request["prompt"]), answer=answer["answer"], usage=answer["usage"])
                verdicts.append(verdict)
                atomic(ROOT / "verdicts.json", verdicts)
                status("VERDICT", arm=arm, seed=seed, id=request["id"], verdict=verdict["verdict"])
            final.append({"arm": arm, "seed": seed, "strategy": current, "A": a["levels"], "B": b["levels"]})
    accepted = sum(v["verdict"] == "accepted" and v["arm"] == "echo" for v in verdicts)
    echo_levels = sum(r["A"] for r in final if r["arm"] == "echo")
    fijo_levels = sum(r["A"] for r in final if r["arm"] == "fijo")
    result = {"at": capacity.now(), "profile_sha256": sha(integrity()), "S6_green": False,
              "status": "PROMOTE_NEW_CAMPAIGN" if accepted and echo_levels > fijo_levels else "NO_PROMOTION",
              "accepted_echo": accepted, "paired_A_echo": echo_levels, "paired_A_fijo": fijo_levels,
              "unique_proposals": {arm: len({sha(v["proposal"]) for v in verdicts
                                      if v["arm"] == arm and "proposal" in v}) for arm in ARMS},
              "final": final, "verdicts": verdicts, "llm_calls": 14, "paid": False}
    atomic(ROOT / "summary.json", result)
    status("CLOSED", result=result["status"], accepted_echo=accepted)


def follow():
    integrity()
    status("WAIT_CAPACITY", llm_calls=0)
    while not (capacity.ROOT / "summary.json").exists():
        state_path = capacity.ROOT / "status.json"
        if state_path.exists() and json.loads(state_path.read_text()).get("stage") == "FAILED":
            status("SKIPPED", reason="capacity execution failed; no model call", llm_calls=0)
            return
        time.sleep(15)
    summary = json.loads((capacity.ROOT / "summary.json").read_text())
    if summary.get("status") != "POSITIVE_CONTROL":
        status("SKIPPED", reason="no positive control in frozen bounded search", llm_calls=0)
        return
    run()


if __name__ == "__main__":
    if sys.argv[1] == "prepare":
        prepare()
    elif sys.argv[1] in ("run", "follow"):
        try:
            run() if sys.argv[1] == "run" else follow()
        except BaseException as exc:
            status("FAILED", error=type(exc).__name__, message=str(exc))
            raise
    else:
        raise SystemExit("use prepare or run")
