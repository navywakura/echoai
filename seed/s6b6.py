"""B6 pilot: explain parameter consumption and retrieve real decision sites.

No old experiment is modified; model choices still need unmodified V1--V4.
"""
from collections import Counter
from datetime import datetime, timezone
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import signal
from types import FunctionType, SimpleNamespace

from seed import game_selfimprove_b5 as old, s6_precise_capacity as capacity
from seed.game_selfimprove import atomic, canonical, sha, journal, events

REPO = old.REPO
ROOT = REPO / "lab/seed/s6b6-20260928"
BASE = REPO / "lab/kaggle/s6b6-20260928"
LIVE = REPO / "lab/observability/s6b6-20260928"
A = old.A
B = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(24320, 24340)]
SEEDS = (613001, 613017, 613029)
MODEL, REVISION = old.MODEL, old.REVISION
Execution, patch, strategy = old.Execution, old.patch, old.strategy
SOURCES = list(dict.fromkeys(old.SOURCES + ["seed/s6b6.py", "tests/test_s6b6.py",
    "lab/kaggle/s6b6-20260928/generate.py", "lab/kaggle/s6b6-20260928/transport.py",
    "docs/ECHO45-S6-B6-DESIGN.md"]))


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def config():
    return {"A": A, "B": B, "sampling_seeds": SEEDS, "calls_per_arm_per_seed": 2,
            "model_calls_with_calibration": 14, "gpu_seconds_cap": 900,
            "paid": False, "pilot_only": True, "exam_opened": False,
            "promotion": "ECHO accepts >=1; paired A sum strictly exceeds FIJO"}


def integrity():
    old.integrity()
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == hashes()
    assert profile["configuration"] == json.loads(canonical(config()))
    return profile


def status(stage, **kwargs):
    row = dict(at=datetime.now(timezone.utc).isoformat(), stage=stage, **kwargs)
    atomic(ROOT / "status.json", row)
    print(canonical(row), flush=True)


def prepare():
    old.integrity()
    p = {"sources": hashes(), "configuration": config()}
    if (ROOT / "profile.json").exists():
        integrity()
        return
    for name in SOURCES:
        target = ROOT / "source-archive" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((REPO / name).read_bytes())
    atomic(ROOT / "profile.json", p)
    integrity()


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    from echo_arc.precise_observe import PreciseRecorder
    value, spec, record_dir = item
    version, seed, rep, budget = spec
    assert version in (2, 3) and rep == 0 and budget == 2000
    assert seed in range(20) or seed in range(24320, 24340)
    assert record_dir is None or seed < 20
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    recorder = None
    try:
        env = _gym_env(version, seed)
        counted = old.old.accounting().ResetCounter(env)
        if record_dir:
            recorder = PreciseRecorder(Journal(Path(record_dir) / "arc-decisions.jsonl"))
            recorder.write(kind="start", origin="DEVELOPMENT", agent="s6b6", budget=budget)
            recorder.write(kind="game", game=env.game_id)
        rec = Execution.play(counted, budget, runner.seed_for(env.game_id, rep), value, recorder)
        rec.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                   family=env.game.fam, baseline=env.baseline_actions,
                   policy_sha256=Execution.digest(value), automatic_reset_indices=counted.automatic,
                   origin="DEVELOPMENT_A" if seed < 20 else "PROTECTED_B")
        rec["score"] = runner.official_game_score(rec["actions_per_level"], env.baseline_actions)
        if recorder:
            rec["episodes"] = recorder.episodes()
        assert counted.emitted == len(rec["actions"])
        old.old.accounting().check_record(rec)
        return rec
    finally:
        if recorder:
            recorder.write(kind="end", status="closed")
            recorder.close()
        signal.alarm(0)


measure = FunctionType(capacity.measure.__code__, dict(capacity.measure.__globals__, ROOT=ROOT,
    LIVE=LIVE, integrity=integrity, play_one=play_one, status=status), "measure", capacity.measure.__defaults__)
verify = FunctionType(old.verify.__code__, dict(old.verify.__globals__, A=A, B=B,
    c=SimpleNamespace(measure=measure, result=capacity.result)), "verify", old.verify.__defaults__)


def decision_sites():
    """Only the native A journals; never read manual repairs or protected games."""
    measured = json.loads((capacity.ROOT / "measurements/baseline/A.json").read_text())
    digest = Execution.digest(strategy())
    profile = capacity.integrity()
    root = capacity.LIVE / "main" / digest
    result, provenance = [], {}
    for i, rec in enumerate(measured["rows"]):
        spec = [rec[k] for k in ("version", "seed", "rep", "budget")]
        assert spec in [list(x) for x in A]
        key = sha({"profile": sha(profile), "candidate": strategy(), "spec": spec, "observed": True})
        path = root / key / "arc-decisions.jsonl"
        provenance[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
        sites, count, holds = {}, Counter(), Counter()
        for line in path.open():
            e = json.loads(line)
            if e.get("kind") != "decision":
                continue
            f = e["repair_features"]
            site = "set_future_wait" if f["reset_pending"] else "remaining_wait" if f["hold_remaining"] else "other"
            count[site] += 1
            if f["hold_remaining"]:
                holds[f["hold_remaining"]] += 1
            if site != "other" and site not in sites:
                sites[site] = {"features": f, "action": e["action"][:2], "step": e["step"]}
        result.append({"index": i, "levels": rec["levels_completed"], "sites": sites,
                       "site_counts": dict(count), "remaining_wait_histogram": dict(holds)})
    return result, provenance


def requests(arm, seed, sites):
    failing = sorted((r for r in sites if r["levels"] < 5), key=lambda r: (r["levels"], r["index"]))
    common = ("Repair ECHO using one legal JSON patch, with 1-3 AND guards and one integer parameter. "
              "Must gain >=2 training levels with no individual score or level regression. "
              "Bounds: " + canonical(patch.LIMITS) + ". Native defaults: " + canonical(patch.DEFAULTS) + ". "
              "Guard bounds: " + canonical(patch.FEATURES) + ". Operators eq/ge/le. "
              "HOLD is consumed only when a known reset is deliberately tried after the remaining wait reaches 0 "
              "(or 1 before decrement). It does NOT change an already active wait. "
              "COOLDOWN_CAP sets remaining_wait=min(remaining_wait,value); it only changes state if the value "
              "is STRICTLY BELOW the current remaining wait. reset_pending=1 implies remaining_wait=0. "
              "A matching guard alone is insufficient. Changing a parameter to its native value is ineffective. "
              "Other controls: MIN_EVIDENCE body confidence, BABBLE key trials, WALL_MIN wall support, "
              "ENTRY_PROBE_LIMIT temporal trials, ORDER/COUNT support and enable flags, "
              "AFTER_EFFECT_POLICY 0 explore/1 evidence/2 shortest route, PROBE_STRATEGY 0 balanced/1 reentry/2 order. "
              "No IDs, seeds, family, private state or reserved data. Return JSON only. ")
    out = []
    for n in range(2):
        if arm == "fijo":
            chosen, typ = failing[:3], "P4"
            ask = "Here are three incomplete tasks. Propose a general repair. "
        else:
            # Prefer a near success with a real site at which a control is consumed.
            near = sorted(failing, key=lambda r: (-r["levels"], -r["site_counts"].get("set_future_wait", 0), r["index"]))
            chosen, typ = near[:1] if n == 0 else near[:3], "P1" if n == 0 else "P2"
            ask = "Repair this near success at an observed decision site. Preserve earlier skills. " if n == 0 else \
                  "Compare these near successes and repair their shared decision-site failure. "
        out.append({"id": n, "type": typ, "prompt": common + ask + canonical(chosen)})
    return out


def generator():
    spec = spec_from_file_location("_s6b6_generator", BASE / "generate.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run():
    prepare()
    assert not (ROOT / "pilot.json").exists(), "B6 pilot already closed"
    sites, provenance = decision_sites()
    batches = {f"local-{arm}-{seed}": requests(arm, seed, sites) for seed in SEEDS for arm in ("fijo", "echo")}
    atomic(ROOT / "prompt-evidence.json", {"sites": sites, "provenance": provenance})
    atomic(ROOT / "requests.json", batches)
    answers = generator().propose("pilot", batches, {key: int(key.rsplit('-', 1)[-1]) for key in batches})
    a0 = measure("baseline/A", strategy(), A)
    b0 = measure("baseline/B", strategy(), B, observed=False)
    verdicts, finals = [], []
    for seed in SEEDS:
        for arm in ("fijo", "echo"):
            key = f"local-{arm}-{seed}"
            current, a, b = strategy(), a0, b0
            for req, answer in zip(batches[key], answers["arms"][key]):
                current, a, b, verdict = verify(f"pilot/{key}/{req['id']}", answer["answer"], current, a, b)
                row = dict(verdict, arm=arm, seed=seed, id=req["id"], type=req["type"],
                           answer=answer["answer"], prompt_sha256=sha(req["prompt"]), usage=answer["usage"])
                verdicts.append(row)
                journal(ROOT / key / "journal.jsonl", dict(kind="verdict", **row))
                status("PILOT_VERDICT", arm=arm, seed=seed, verdict=row["verdict"])
            finals.append({"arm": arm, "seed": seed, "A": a["levels"], "B": b["levels"], "strategy": current})
    accepted = sum(r["arm"] == "echo" and r["verdict"] == "accepted" for r in verdicts)
    totals = {arm: sum(r["A"] for r in finals if r["arm"] == arm) for arm in ("fijo", "echo")}
    result = {"promote": bool(accepted and totals["echo"] > totals["fijo"]), "accepted_echo": accepted,
              "paired_A": totals, "verdicts": verdicts, "finals": finals, "llm_calls": 14,
              "profile_sha256": sha(integrity()), "exam_opened": False}
    atomic(ROOT / "pilot.json", result)
    status("PILOT_PROMOTED" if result["promote"] else "PILOT_NO_PROMOTION", accepted_echo=accepted, paired_A=totals)


def audit():
    """Replay all verifier decisions in fresh workers/cache and rebuild prompts."""
    profile = integrity()
    saved = json.loads((ROOT / "pilot.json").read_text())
    sites, provenance = decision_sites()
    assert json.loads((ROOT / "prompt-evidence.json").read_text()) == json.loads(canonical(
        {"sites": sites, "provenance": provenance}))
    expected = {f"local-{arm}-{seed}": requests(arm, seed, sites) for seed in SEEDS for arm in ("fijo", "echo")}
    assert expected == json.loads((ROOT / "requests.json").read_text())
    generator().check(json.loads((BASE / "pilot/answers.json").read_text()),
                      json.loads((BASE / "pilot/payload.json").read_text()))
    fresh = FunctionType(capacity.measure.__code__, dict(measure.__globals__, ROOT=ROOT / "audit-cache",
                         LIVE=LIVE / "audit"), "measure", capacity.measure.__defaults__)
    verifier = FunctionType(old.verify.__code__, dict(old.verify.__globals__, A=A, B=B,
        c=SimpleNamespace(measure=fresh, result=capacity.result)), "verify", old.verify.__defaults__)
    a0 = fresh("baseline/A", strategy(), A)
    b0 = fresh("baseline/B", strategy(), B, observed=False)
    for seed in SEEDS:
        for arm in ("fijo", "echo"):
            current, a, b = strategy(), a0, b0
            for row in (r for r in saved["verdicts"] if r["seed"] == seed and r["arm"] == arm):
                current, a, b, replayed = verifier(f"{arm}-{seed}-{row['id']}", row["answer"], current, a, b)
                assert all(canonical(row[k]) == canonical(value) for k, value in replayed.items())
    integrity()
    atomic(ROOT / "audit.json", {"valid": True, "verdicts_rebuilt": len(saved["verdicts"]),
                                 "profile_sha256": sha(profile), "exam_opened": False})


if __name__ == "__main__":
    import sys
    audit() if sys.argv[1:] == ["audit"] else run()
