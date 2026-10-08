"""OTHER development, source-locked exams, observation replay and native audit."""
import argparse
import hashlib
from itertools import permutations
import json
from pathlib import Path
import random
import subprocess
import sys

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import maintain_final as parent_module
from echoai.echo4.other_model import OtherModel, MODES, context, outcome
from echoai.echo4.other_world import Encounter, PRIVATE_STEPS, ENCOUNTERS
from echoai.echo4.other_replay import digest, transcript, replay
from echoai.core.cam import Cam
from echoai.nexus0.world import World

SCHEMA = "echo4-other1-v1"
PARENT = ROOT / "lab/echo4/maintain1-final-v1"
PARENT_DIGEST = "7e1c0e821ba2ddf79834fef6a66a16bfd2773a456d29ac5bbf535c11e6024fbe"
DEVELOPMENT = (11, 29, 47)
EXAMS = (tuple(range(261001, 261009)), tuple(range(261101, 261109)))


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sources():
    extras = ("echo4/other_model.py", "echo4/other_world.py", "echo4/other_replay.py",
              "echo4/other_bench.py", "tests/test_echo4_other1.py", "docs/ECHO4-OTHER1-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT/p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT/"report.json"), read_json(PARENT/"audit-receipt.json")
    unsigned = dict(report)
    value = unsigned.pop("reproduction_sha256")
    if value != PARENT_DIGEST or sha(unsigned) != value or receipt["valid"] is not True:
        raise ValueError("unexpected parent")
    if (receipt["maintain1_green"] is not True or receipt["findings"] != []
            or receipt["reproduction_sha256"] != value or report["sources"] != parent_module.sources()
            or report["parent"] != parent_module.parent()):
        raise ValueError("MAINTAIN custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def preferences(seed, same):
    rng = random.Random(seed)
    choices = tuple(permutations(range(3)))
    own = rng.choice(choices)
    peer = own if same else rng.choice(tuple(p for p in choices if all(a != b for a, b in zip(own, p))))
    return own, peer


def scores(frames):
    pairs = [(e["predictions"][i], e["actions"][1-i]) for e in frames for i in range(2)]
    return {"targets": len(pairs), "issued": sum(p is not None for p, _ in pairs),
            "correct": sum(p == a for p, a in pairs),
            "wrong": sum(p is not None and p != a for p, a in pairs)}


def episode(seed, same, mode):
    run = Encounter(preferences(seed, same), seed=seed, mode=mode)
    frames = [run.step() for _ in range(ENCOUNTERS)]
    replays = []
    for index, model in enumerate(run.models):
        recreated = replay(transcript(frames, index), mode)
        expected = {"predictions": [e["predictions"][index] for e in frames],
                    "forecasts": [e["forecasts"][index] for e in frames], "memory_sha256": digest(model)}
        replays.append(canonical(expected) == canonical(recreated))
    behavior = [{k: e[k] for k in ("tick", "actions", "proposals", "gates", "rewards")} for e in frames]
    return {"seed": seed, "same_preferences": same, "mode": mode, "frames": frames,
            "scores": scores(frames[96:]), "first_half": scores(frames[:96]),
            "native_successes": sum(r == 16 for e in frames for r in e["rewards"]),
            "native_actions": 2*ENCOUNTERS, "private_preparation_actions": 2*PRIVATE_STEPS,
            "behavior_sha256": sha(behavior), "replay_equal": all(replays),
            "invariants": run.invariant(), "cam_used": tuple(a.cam.used for a in run.agents),
            "public_rows": tuple(sum(s.occupied and s.source.startswith("other1-") for s in a.cam.slot)
                                 for a in run.agents)}


def batch(seeds, progress=lambda _: None):
    result, checks = {}, {}
    for same in (False, True):
        kind = "same" if same else "heterogeneous"
        arms = {m: [] for m in MODES}
        for seed in seeds:
            progress(f"{kind} {seed}")
            for mode in MODES:
                arms[mode].append(episode(seed, same, mode))
        totals = {m: {k: sum(r["scores"][k] for r in rows) for k in ("targets", "issued", "correct", "wrong")}
                  for m, rows in arms.items()}
        n, right, issued = (totals["identity"][k] for k in ("targets", "correct", "issued"))
        checks[kind+"_accuracy"] = right*100 >= n*85 and n > 0
        checks[kind+"_precision"] = issued > 0 and right*100 >= issued*95
        checks[kind+"_native_learning"] = all(r["native_successes"]*100 >= r["native_actions"]*95
                                               for rows in arms.values() for r in rows)
        checks[kind+"_same_actions"] = all(len({arms[m][i]["behavior_sha256"] for m in MODES}) == 1
                                           for i in range(len(seeds)))
        checks[kind+"_invariants"] = all(r["invariants"] and r["replay_equal"] for rows in arms.values() for r in rows)
        if same:
            checks["same_copy_accuracy"] = totals["self_copy"]["correct"]*100 >= n*85
        else:
            for mode, margin in (("pooled", 20), ("self_copy", 20), ("no_history", 50)):
                checks["gain_"+mode] = (right-totals[mode]["correct"])*100 >= n*margin
        result[kind] = {"arms": arms, "totals": totals}
    return {**result, "checks": checks, "passed": all(checks.values())}


def witness_model():
    model = OtherModel(Cam(), World())
    for tick in range(4):
        model.begin(tick, (context(0, 0), context(1, 1)))
        model.finish(tick, 0, (outcome(0, 0, 0), outcome(1, 1, 1)))
    return model


def controls():
    checks = {}
    model = witness_model()
    checks["learned_peer_not_self"] = model.begin(4, (context(0, 0), context(1, 1)))[1][0] == 1
    before = digest(model)
    for packets in ((outcome(0, 0, 0), outcome(2, 1, 1)),
                    (outcome(0, 0, 0), outcome(1, 2, 1))):
        try:
            model.finish(4, 0, packets)
        except ValueError:
            checks["reject_"+packets[1].hex()] = digest(model) == before
        else:
            checks["reject_"+packets[1].hex()] = False
    model.finish(4, 0, (outcome(0, 0, 0), outcome(1, 1, 2)))
    checks["contradiction_abstains"] = model.begin(5, (context(0, 0), context(1, 1)))[1][0] is None
    model.finish(5, 0, (outcome(0, 0, 0), None))
    try:
        model.begin(5, (context(0, 0), context(1, 1)))
    except ValueError:
        checks["duplicate_rejected"] = True
    else:
        checks["duplicate_rejected"] = False
    model.stop()
    before = digest(model)
    try:
        model.begin(6, (context(0, 0), context(1, 1)))
    except RuntimeError:
        checks["stop_preserved"] = digest(model) == before
    else:
        checks["stop_preserved"] = False
    for name, packet in (("new_identity", context(2, 1)), ("hidden_cue", context(1, None)), ("untracked", None)):
        other = witness_model()
        checks[name] = other.begin(4, (context(0, 0), packet))[1] == (None, None, None)
    run = Encounter(((0, 1, 2), (1, 2, 0)), seed=11)
    reverse = Encounter(((0, 1, 2), (1, 2, 0)), seed=11)
    rows = [run.step() for _ in range(24)]
    reversed_rows = [reverse.step(order=(1, 0)) for _ in range(24)]
    checks["execution_order_invariant"] = canonical(rows) == canonical(reversed_rows)
    # An action under veto is still a real WAIT, never the unexecuted proposal.
    vetoed = run.step(veto=(False, True))
    checks["gate_applied_not_proposal"] = vetoed["gates"][1] == 2 and vetoed["actions"][1] == 2
    checks["separate_memories"] = run.invariant() and reverse.invariant()
    return {"checks": checks, "passed": all(checks.values()), "rows": rows+[vetoed],
            "public_memory": tuple(digest(model) for model in run.models)}


def fresh_replay(directory, control, checking):
    results = []
    rows = control["rows"]
    for observer in range(2):
        records = transcript(rows, observer)
        filename = f"public-observer-{observer}.json"
        persist(directory, filename, records, checking)
        child = subprocess.run([sys.executable, "-m", "echoai.echo4.other_bench", "replay",
                                str((directory/filename).resolve()), "--mode", "identity"],
                               cwd=ROOT.parent, capture_output=True, text=True, check=True, timeout=60)
        expected = {"predictions": [r["predictions"][observer] for r in rows],
                    "forecasts": [r["forecasts"][observer] for r in rows],
                    "memory_sha256": control["public_memory"][observer]}
        results.append({"equal": canonical(json.loads(child.stdout)) == canonical(expected),
                        "memory_sha256": expected["memory_sha256"], "records": len(records)})
    return results


def campaign(directory, *, checking=False, progress=lambda _: None):
    manifest, ancestry = sources(), parent()
    lock = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "development": DEVELOPMENT,
            "exams": EXAMS, "private_steps": PRIVATE_STEPS, "encounters": ENCOUNTERS,
            "accuracy_percent": 85, "precision_percent": 95, "gain_points": (20, 20, 50)}
    lock_sha = persist(directory, "lock.json", lock, checking)
    development = batch(DEVELOPMENT, lambda s: progress("development "+s))
    persist(directory, "development.json", development, checking)
    c = controls()
    c["fresh_replay"] = fresh_replay(directory, c, checking)
    c["passed"] &= all(r["equal"] for r in c["fresh_replay"])
    persist(directory, "controls.json", c, checking)
    exams = []
    if development["passed"] and c["passed"]:
        for index, seeds in enumerate(EXAMS):
            data = batch(seeds, lambda s: progress(f"exam {index+1} "+s))
            persist(directory, f"exam-{index+1}.json", data, checking)
            exams.append({"checks": data["checks"], "passed": data["passed"],
                          **{k: data[k]["totals"] for k in ("heterogeneous", "same")}})
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during exam")
    result = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "lock_sha256": lock_sha,
              "development_checks": development["checks"], "controls": c["checks"],
              "fresh_replay": c["fresh_replay"], "exams": exams,
              "criteria_passed": bool(development["passed"] and c["passed"] and len(exams) == 2
                                      and all(e["passed"] for e in exams)), "other1_green": False,
              "scope": "observational other-model in a discrete task; not social control or integrated thermal agent"}
    result["reproduction_sha256"] = sha(result)
    persist(directory, "report.json", result, checking)
    return result


def verify(directory, progress=lambda _: None):
    findings, value, green = [], None, False
    try:
        report = read_json(directory/"report.json")
        value = report["reproduction_sha256"]
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/custody mismatch")
        rebuilt = campaign(directory, checking=True, progress=progress)
        green = rebuilt["criteria_passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "other1_green": bool(green and not findings),
            "scope": "OTHER native reconstruction; MAINTAIN custody only, not rerun"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("development", "campaign", "verify", "replay"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--mode", choices=MODES, default="identity")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    progress = lambda s: print(s, file=sys.stderr, flush=True)
    if args.command == "replay":
        print(json.dumps(replay(read_json(args.directory), args.mode)))
        return 0
    if args.command in ("development", "campaign"):
        if args.write_receipt:
            parser.error("audit in a fresh process")
        args.directory.mkdir(parents=True, exist_ok=False)
        if args.command == "development":
            result = batch(DEVELOPMENT, progress)
            persist(args.directory, "development.json", result, False)
            print(json.dumps({"checks": result["checks"], "passed": result["passed"],
                              **{k: result[k]["totals"] for k in ("heterogeneous", "same")}}, indent=2))
            return 0 if result["passed"] else 1
        result = campaign(args.directory, progress=progress)
        print(json.dumps({k: result[k] for k in ("criteria_passed", "other1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["criteria_passed"] else 1
    result = verify(args.directory, progress)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
