"""One bounded adaptive follow-up to B6, preserving every earlier result."""
import hashlib
import json
import time
from importlib.util import module_from_spec, spec_from_file_location
from types import FunctionType, SimpleNamespace

from seed import s6b6 as previous, s6_precise_capacity as capacity
from seed.game_selfimprove import atomic, canonical, sha, journal

REPO, A, B, SEEDS = previous.REPO, previous.A, previous.B, previous.SEEDS
MODEL, REVISION, Execution, strategy = previous.MODEL, previous.REVISION, previous.Execution, previous.strategy
ROOT = REPO / "lab/seed/s6b7-20260929"
BASE = REPO / "lab/kaggle/s6b7-20260929"
LIVE = REPO / "lab/observability/s6b7-20260929"
SOURCES = previous.SOURCES + ["seed/s6b7.py", "tests/test_s6b7.py", "docs/ECHO45-S6-B7-DESIGN.md",
                            "lab/kaggle/s6b7-20260929/generate.py", "lab/kaggle/s6b7-20260929/transport.py"]


def config():
    return {"A": A, "B": B, "parent_seeds": SEEDS, "sampling_seeds": [x + 1000 for x in SEEDS],
            "new_proposals_per_arm_per_seed": 1, "new_calls_with_calibration": 8,
            "total_history_proposals": 18, "total_history_calls_with_calibration": 22,
            "gpu_seconds_cap": 900, "paid": False, "exam_opened": False}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def history():
    return json.loads((previous.ROOT / "pilot.json").read_text())


def integrity():
    previous.integrity()
    p = json.loads((ROOT / "profile.json").read_text())
    assert p["sources"] == hashes() and p["history_sha256"] == sha(history())
    assert p["configuration"] == json.loads(canonical(config()))
    return p


status = FunctionType(previous.status.__code__, dict(previous.status.__globals__, ROOT=ROOT))


def prepare():
    previous.integrity()
    profile = {"sources": hashes(), "configuration": config(), "history_sha256": sha(history())}
    if (ROOT / "profile.json").exists():
        return integrity()
    for name in SOURCES:
        target = ROOT / "source-archive" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((REPO / name).read_bytes())
    atomic(ROOT / "profile.json", profile)
    return integrity()


measure = FunctionType(capacity.measure.__code__, dict(previous.measure.__globals__, ROOT=ROOT,
    LIVE=LIVE, integrity=integrity, status=status), "measure", capacity.measure.__defaults__)
verify = FunctionType(previous.verify.__code__, dict(previous.verify.__globals__,
    c=SimpleNamespace(measure=measure, result=capacity.result)), "verify", previous.verify.__defaults__)


def public_feedback(events):
    """No protected indices, scores, frames, source IDs or free-form errors."""
    out = []
    for event in events:
        a = event.get("A", {})
        out.append({"proposal": previous.patch.validate(event["proposal"]) if "proposal" in event else None,
                    "verdict": event["verdict"],
                    "training": {key: a[key] for key in ("gain", "changed_action_games", "activated_games") if key in a},
                    "protected_rejection": event["verdict"] == "V4"})
    return out


def requests(arm, seed, sites, parent):
    final = next(r for r in parent["finals"] if r["arm"] == arm and r["seed"] == seed)
    feedback = public_feedback([r for r in parent["verdicts"] if r["arm"] == arm and r["seed"] == seed])
    req = dict(previous.requests(arm, seed, sites)[0], id=2)
    req["prompt"] += " Current accepted program: " + canonical(final["strategy"]["program"])
    req["prompt"] += ". Results of your two actual prior proposals: " + canonical(feedback)
    req["prompt"] += (". Propose one NEW repair relative to the current program. A proposal with zero changed "
                      "training actions did not repair behavior. A protected rejection permits no protected details. "
                      "Do not simply repeat a rejected or already accepted patch.")
    if arm == "echo":
        req["prompt"] += (" Diagnose the strongest training improvement that failed conservation, if present. "
                          "Refine its scope or magnitude to retain useful behavior. Otherwise use the observed "
                          "decision site and measured no-effect feedback. Choose your own guard and value.")
    return req


def generator():
    spec = spec_from_file_location("_s6b7_generator", BASE / "generate.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    while not (previous.ROOT / "pilot.json").exists():
        status("WAIT_B6_CLOSURE")
        time.sleep(15)
    prepare()
    assert not (ROOT / "pilot.json").exists(), "follow-up already closed"
    parent = history()
    sites, provenance = previous.decision_sites()
    batches = {f"local-{arm}-{seed}": [requests(arm, seed, sites, parent)] for seed in SEEDS for arm in ("fijo", "echo")}
    atomic(ROOT / "requests.json", batches)
    atomic(ROOT / "prompt-evidence.json", {"provenance": provenance, "parent_sha256": sha(parent)})
    answers = generator().propose("pilot", batches, {key: int(key.rsplit('-', 1)[-1]) + 1000 for key in batches})
    verdicts, finals = [], []
    for seed in SEEDS:
        for arm in ("fijo", "echo"):
            key = f"local-{arm}-{seed}"
            before = next(r for r in parent["finals"] if r["arm"] == arm and r["seed"] == seed)
            current = before["strategy"]
            a = measure(f"initial/{key}/A", current, A)
            b = measure(f"initial/{key}/B", current, B, observed=False)
            assert a["levels"] == before["A"] and b["levels"] == before["B"]
            req, answer = batches[key][0], answers["arms"][key][0]
            current, a, b, verdict = verify(f"followup/{key}", answer["answer"], current, a, b)
            row = dict(verdict, arm=arm, seed=seed, id=2, type=req["type"], answer=answer["answer"],
                       prompt_sha256=sha(req["prompt"]), usage=answer["usage"])
            verdicts.append(row)
            journal(ROOT / key / "journal.jsonl", dict(kind="verdict", **row))
            finals.append({"arm": arm, "seed": seed, "A": a["levels"], "B": b["levels"], "strategy": current})
            status("FOLLOWUP_VERDICT", arm=arm, seed=seed, verdict=row["verdict"])
    accepted = parent["accepted_echo"] + sum(r["arm"] == "echo" and r["verdict"] == "accepted" for r in verdicts)
    totals = {arm: sum(r["A"] for r in finals if r["arm"] == arm) for arm in ("fijo", "echo")}
    result = {"promote": bool(accepted and totals["echo"] > totals["fijo"]), "accepted_echo": accepted,
              "paired_A": totals, "verdicts": verdicts, "finals": finals, "new_llm_calls": 8,
              "total_history_calls": 22, "profile_sha256": sha(integrity()), "exam_opened": False}
    atomic(ROOT / "pilot.json", result)
    status("PILOT_PROMOTED" if result["promote"] else "PILOT_NO_PROMOTION", accepted_echo=accepted, paired_A=totals)


def audit():
    integrity()
    assert json.loads((previous.ROOT / "audit.json").read_text())["valid"], "parent audit required"
    saved, parent = json.loads((ROOT / "pilot.json").read_text()), history()
    sites, _ = previous.decision_sites()
    batches = {f"local-{arm}-{seed}": [requests(arm, seed, sites, parent)] for seed in SEEDS for arm in ("fijo", "echo")}
    assert batches == json.loads((ROOT / "requests.json").read_text())
    payload = json.loads((BASE / "pilot/payload.json").read_text())
    answers = generator().check(json.loads((BASE / "pilot/answers.json").read_text()), payload)
    assert payload["requests"] == batches and payload["source_digest"] == sha(integrity())
    fresh = FunctionType(capacity.measure.__code__, dict(measure.__globals__, ROOT=ROOT / "audit-cache",
                         LIVE=LIVE / "audit"), "measure", capacity.measure.__defaults__)
    verifier = FunctionType(verify.__code__, dict(verify.__globals__,
        c=SimpleNamespace(measure=fresh, result=capacity.result)), "verify", verify.__defaults__)
    rebuilt_finals = []
    for row in saved["verdicts"]:
        arm, seed = row["arm"], row["seed"]
        key = f"local-{arm}-{seed}"
        assert row["answer"] == answers["arms"][key][0]["answer"]
        assert row["prompt_sha256"] == sha(batches[key][0]["prompt"])
        before = next(r for r in parent["finals"] if r["arm"] == arm and r["seed"] == seed)
        current = before["strategy"]
        a = fresh(f"initial/{key}/A", current, A)
        b = fresh(f"initial/{key}/B", current, B, observed=False)
        current, a, b, checked = verifier(key, row["answer"], current, a, b)
        assert all(canonical(row[k]) == canonical(value) for k, value in checked.items())
        rebuilt_finals.append({"arm": arm, "seed": seed, "A": a["levels"], "B": b["levels"], "strategy": current})
    assert rebuilt_finals == saved["finals"]
    totals = {arm: sum(r["A"] for r in rebuilt_finals if r["arm"] == arm) for arm in ("fijo", "echo")}
    assert totals == saved["paired_A"]
    integrity()
    atomic(ROOT / "audit.json", {"valid": True, "parent_verdicts_rebuilt": 12, "new_verdicts_rebuilt": 6,
                                 "profile_sha256": sha(integrity()), "exam_opened": False})


if __name__ == "__main__":
    import sys
    audit() if sys.argv[1:] == ["audit"] else run()
