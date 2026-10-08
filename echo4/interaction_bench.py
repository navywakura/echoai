"""INTERACTION-A mechanics and native wiring, not an INTERACTION closure."""
import argparse
from itertools import product
import json
from pathlib import Path
import random

from echoai.echo4 import other_bench as parent_module
from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4.other_replay import digest, replay, transcript
from echoai.echo4.interaction_world import InteractionWorld
from echoai.echo4.interaction_session import InteractionSession

SCHEMA = "echo4-interaction1-a-v1"
PARENT = ROOT / "lab/echo4/other1-v1"
PARENT_DIGEST = "1263f11ab291a1ff350313a93a70d9f4b3b9259099482bb8425e9f414c2aa024"
SEEDS = (17, 31, 59)
ROUNDS = 144
sha = parent_module.sha


def sources():
    extras = ("echo4/interaction_world.py", "echo4/interaction_session.py", "echo4/interaction_bench.py",
              "tests/test_echo4_interaction1a.py", "docs/ECHO4-INTERACTION1-A-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT/p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT/"report.json"), read_json(PARENT/"audit-receipt.json")
    unsigned = dict(report)
    value = unsigned.pop("reproduction_sha256")
    if (value != PARENT_DIGEST or sha(unsigned) != value
            or receipt["valid"] is not True or receipt["other1_green"] is not True
            or receipt["findings"] != [] or receipt["reproduction_sha256"] != value
            or report["sources"] != parent_module.sources() or report["parent"] != parent_module.parent()):
        raise ValueError("OTHER custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def census():
    rows, passed = [], True
    for cue, a, b, ea, eb in product(range(3), range(3), range(3), (0, 2, 8), (0, 2, 8)):
        row = InteractionWorld((cue,), (ea, eb)).advance((a, b))
        reverse = InteractionWorld((cue,), (eb, ea)).advance((b, a))
        # Independent reference calculation, not the runtime helper/constants.
        required = tuple((3 if cue != 1 else 5) if x == 0 else int(x == 1) for x in (a, b))
        capable = (ea >= required[0], eb >= required[1])
        paid = tuple(required[i] if capable[i] else 0 for i in range(2))
        joint = a == b == 0 and all(capable)
        output = tuple((10, 6, 0)[cue] if joint else 5 if x == 1 and capable[i] else 0
                       for i, x in enumerate((a, b)))
        good = (row["paid"] == paid and row["output"] == output
                and row["joint_executed"] == joint
                and row["after"] == (ea-paid[0], eb-paid[1])
                and row["net"] == tuple(output[i]-paid[i] for i in range(2))
                and row["incapable"] == tuple(not v for v in capable)
                and all(row[k] == reverse[k][::-1] for k in ("paid", "output", "after", "net", "incapable")))
        passed &= good
        rows.append({**row, "reference_and_symmetry": good})
    return {"rows": rows, "passed": passed}


def summary(rows):
    return {"rounds": len(rows),
            **{key: tuple(sum(r[key][i] for r in rows) for i in range(2)) for key in ("paid", "output", "net")},
            "joint_rounds": sum(r["joint_executed"] for r in rows),
            "incapable_attempts": sum(sum(r["incapable"]) for r in rows)}


def witnesses():
    rows = []
    for cue, action in product(range(3), range(3)):
        world = InteractionWorld((cue,)*12)
        frames = [world.advance((action, action)) for _ in range(12)]
        rows.append({"cue": cue, "scripted_action": action, "frames": frames, "summary": summary(frames)})
    checks = {"opportunity": rows[0]["summary"]["net"] == (84, 84),
              "friction": rows[3]["summary"]["net"] == (12, 12),
              "blocked": rows[6]["summary"]["net"] == (-36, -36),
              "solo": all(rows[i]["summary"]["net"] == (48, 48) for i in (1, 4, 7)),
              "wait": all(rows[i]["summary"]["net"] == (0, 0) for i in (2, 5, 8))}
    return {"rows": rows, "checks": checks, "passed": all(checks.values())}


def native(seed):
    rng = random.Random(seed)
    cues = tuple(rng.randrange(3) for _ in range(ROUNDS))
    run, reverse = InteractionSession(cues), InteractionSession(cues)
    frames = [run.step(greedy=t >= 72) for t in range(ROUNDS)]
    backwards = [reverse.step(greedy=t >= 72, order=(1, 0)) for t in range(ROUNDS)]
    reproduced = []
    for i, model in enumerate(run.models):
        expected = {"forecasts": [r["forecasts"][i] for r in frames],
                    "predictions": [r["predictions"][i] for r in frames], "memory_sha256": digest(model)}
        reproduced.append(canonical(expected) == canonical(replay(transcript(frames, i), "identity")))
    checks = {"order_invariant": canonical(frames) == canonical(backwards),
              "public_replay": all(reproduced), "invariants": run.invariant() and reverse.invariant(),
              "q_learned": all(a.metrics.deltas > 0 and any(any(row) for row in a.q.q) for a in run.agents),
              "two_native_steps_per_round": sum(a.metrics.turns for a in run.agents) == 2*ROUNDS}
    scripted = {}
    for action, name in enumerate(("always_join", "solo", "wait")):
        world = InteractionWorld(cues)
        scripted[name] = summary([world.advance((action, action)) for _ in cues])
    return {"seed": seed, "frames": frames, "summary": summary(frames),
            "first_half": summary(frames[:72]), "last_half": summary(frames[72:]),
            "scripted_controls": scripted,
            "remaining_resources": run.world.resources, "checks": checks, "passed": all(checks.values())}


def campaign(directory, *, checking=False):
    manifest, ancestry = sources(), parent()
    lock = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "seeds": SEEDS, "rounds": ROUNDS,
            "scope": "A mechanics and wiring; B/C/D unopened"}
    lock_sha = persist(directory, "lock.json", lock, checking)
    mechanical, scripts = census(), witnesses()
    persist(directory, "census.json", mechanical, checking)
    persist(directory, "witnesses.json", scripts, checking)
    agents = [native(seed) for seed in SEEDS]
    persist(directory, "native.json", agents, checking)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    result = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "lock_sha256": lock_sha,
              "census_transitions": len(mechanical["rows"]), "census_passed": mechanical["passed"],
              "witness_checks": scripts["checks"],
              "native": [{k: r[k] for k in ("seed", "summary", "first_half", "last_half", "remaining_resources", "scripted_controls", "checks")}
                         for r in agents],
              "phase_a_valid": mechanical["passed"] and scripts["passed"] and all(r["passed"] for r in agents),
              "interaction1_green": False, "autonomous_interaction_gain_tested": False}
    result["reproduction_sha256"] = sha(result)
    persist(directory, "report.json", result, checking)
    return result


def verify(directory):
    findings, value, valid_a = [], None, False
    try:
        report = read_json(directory/"report.json")
        value = report["reproduction_sha256"]
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        rebuilt = campaign(directory, checking=True)
        valid_a = rebuilt["phase_a_valid"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "phase_a_valid": bool(valid_a and not findings), "interaction1_green": False,
            "scope": "native INTERACTION-A reconstruction; OTHER custody only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "campaign":
        if args.write_receipt:
            parser.error("audit in a fresh process")
        args.directory.mkdir(parents=True, exist_ok=False)
        result = campaign(args.directory)
        print(json.dumps({k: result[k] for k in ("phase_a_valid", "interaction1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["phase_a_valid"] else 1
    result = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] and result["phase_a_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
