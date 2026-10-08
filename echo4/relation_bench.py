"""RELATION-A history/provenance benchmark; never grants relational transfer."""
import argparse
import io
import json
from pathlib import Path
import random
import unittest

from echoai.echo4 import interaction_final as parent_module
from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4.interaction_cases import summary, reconstructs
from echoai.echo4.interaction_social import SocialSession
from echoai.echo4.relation_memory import replay
from echoai.echo4.relation_session import RelationSession

SCHEMA = "echo4-relation1-a-v1"
PARENT = ROOT / "lab/echo4/interaction1-bcd-v1"
PARENT_DIGEST = "d1c5b073e7ac406ddd855184cc6f4bd1176d354eed57438eb51af1383f040735"
SEEDS = (113, 127, 139)
ROUNDS = 144
sha = parent_module.a.sha


def sources():
    extras = ("echo4/relation_memory.py", "echo4/relation_session.py", "echo4/relation_bench.py",
              "tests/test_echo4_relation1a.py", "docs/ECHO4-RELATION1-A-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report = parent_module.check_header(PARENT)
    receipt = read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or report["criteria_passed"] is not True
            or receipt["reproduction_sha256"] != PARENT_DIGEST or receipt["valid"] is not True
            or receipt["interaction1_green"] is not True or receipt["findings"] != []):
        raise ValueError("INTERACTION custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def relation_replay(session):
    result = []
    for memory in session.relations:
        expected = {"history": memory.history(), "summaries": [memory.summary(p) for p in range(3)],
                    "memory_sha256": memory.digest(), "valid": memory.invariant()}
        actual = replay([e["observation"] for e in memory.history()])
        result.append({**expected, "replay_equal": canonical(actual) == canonical(expected)})
    return result


def native(seed):
    rng, pairs = random.Random(seed), []
    for _ in range(ROUNDS // 6):
        block = [(c, h) for c in range(3) for h in (1, 2)]
        rng.shuffle(block)
        pairs.extend(block)
    cues, schedule = tuple(c for c, _ in pairs), tuple(h for _, h in pairs)
    swapped = bool(rng.randrange(2))
    run = RelationSession(cues, schedule, swapped=swapped)
    reverse = RelationSession(cues, schedule, swapped=swapped)
    control = SocialSession(cues, schedule, swapped=swapped)
    frames = [run.step(greedy=t >= 96) for t in range(ROUNDS)]
    backwards = [reverse.step(greedy=t >= 96, order=(1, 0)) for t in range(ROUNDS)]
    baseline = [control.step(greedy=t >= 96) for t in range(ROUNDS)]
    memories = relation_replay(run)
    physical = summary(frames)
    checks = {"order_invariant": canonical(frames) == canonical(backwards),
              "history_order_invariant": [m.digest() for m in run.relations] == [m.digest() for m in reverse.relations],
              "passive_policy_parity": canonical([{k: v for k, v in f.items() if k != "relation_heads"} for f in frames]) == canonical(baseline),
              "invariants": run.invariant() and reverse.invariant() and control.invariant(),
              "other_public_replay": reconstructs(run, frames),
              "relation_public_replay": all(m["replay_equal"] and m["valid"] for m in memories),
              "episodes": [m.count for m in run.relations] == [144, 72, 72],
              "native_steps": sum(a.metrics.turns for s in (run, reverse, control) for a in s.all_agents) == 2304,
              "own_costs_only": all(sum(r["paid"] for r in memories[i]["summaries"]) == physical["paid"][i] for i in range(3)),
              "own_outputs_only": all(sum(r["output"] for r in memories[i]["summaries"]) == physical["output"][i] for i in range(3))}
    return {"seed": seed, "frames": frames, "memories": memories, "summary": physical,
            "checks": checks, "passed": all(checks.values())}


def partial():
    run = RelationSession((0, 1, 2) * 8, (1, 2) * 12)
    frames = [run.step(tracked=t % 4 != 0, visible=(t % 4 != 1, True), outcomes=(t % 4 != 2, t % 3 != 0))
              for t in range(24)]
    memories = relation_replay(run)
    checks = {"invariants": run.invariant(), "replay": all(m["replay_equal"] for m in memories),
              "unidentified_not_assigned": run.relations[0].summary(0)["encounters"] == 6,
              "missing_not_wait": run.relations[0].summary(0)["peer_action_unknown"] == 6}
    return {"frames": frames, "memories": memories, "checks": checks, "passed": all(checks.values())}


def tests():
    suite = unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_relation1a")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry,
                       "seeds": SEEDS, "rounds": ROUNDS, "scope": "A passive observed history; B/C/D unopened"})
    rows, hidden, unit = [native(seed) for seed in SEEDS], partial(), tests()
    save("native.json", rows)
    save("partial.json", hidden)
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "native": [{k: row[k] for k in ("seed", "summary", "checks")} for row in rows],
              "partial": hidden["checks"], "tests": unit,
              "phase_a_valid": all(r["passed"] for r in rows) and hidden["passed"] and unit["passed"],
              "relation1_green": False, "transfer_advantage_tested": False,
              "primary_episodes": 3 * 288 + 48, "native_steps_including_controls": 3 * 2304 + 528,
              "unit_test_costs": "additional development tests, not included in primary native accounting"}
    report["reproduction_sha256"] = sha(report)
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value, valid_a = [], None, False
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if sha(unsigned) != value or report["schema"] != SCHEMA:
            raise ValueError("report digest/schema mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        if set(report["artifacts"]) != {"lock.json", "native.json", "partial.json", "tests.json"}:
            raise ValueError("artifact names mismatch")
        for name, digest in report["artifacts"].items():
            if file_hash(directory / name) != digest:
                raise ValueError("artifact digest mismatch: " + name)
        valid_a = campaign(directory, checking=True)["phase_a_valid"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "phase_a_valid": bool(valid_a and not findings), "relation1_green": False,
            "scope": "native RELATION-A reconstruction and INTERACTION custody; no transfer advantage claim"}


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
        print(json.dumps({k: result[k] for k in ("phase_a_valid", "relation1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["phase_a_valid"] else 1
    result = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] and result["phase_a_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
