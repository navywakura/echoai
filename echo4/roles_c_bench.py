"""ROLES-C witnesses on development seeds. Limits are published, not hidden."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import roles as R
from echoai.echo4 import roles_bench as ab
from echoai.echo4.roles_c import RolesCSession, RELAY_SOURCE

SCHEMA = "echo4-roles1-c-dev-v1"
PARENT = ROOT / "lab/echo4/roles1-ab-dev-v2"
PARENT_DIGEST = "36b9cab337eb10dfab37557f2a4a42d12a08e08dbdf65d2642652b9523c257a6"
SEEDS = ab.DEVELOPMENT
ROUNDS = ab.ROUNDS


def run(seed, arm="competence", rounds=ROUNDS, **kwargs):
    s = RolesCSession(seed, rounds, arm=arm, **kwargs)
    return s, [s.step() for _ in range(rounds)]


def nominal_digest(frames):
    return hashlib.sha256(canonical([{k: v for k, v in f.items() if k != "absent"} for f in frames])).hexdigest()


def run_length(frames, start, limit):
    window = frames[start:start + limit]
    for i in range(len(window) - ab.RUN + 1):
        if all(f["output"][0] > 0 for f in window[i:i + ab.RUN]):
            return i
    return limit


def c0_nominal_parity():
    sealed = read_json(PARENT / "development.json")
    ok = True
    for life in sealed["lives"]:
        for arm in R.ARMS:
            _, frames = run(life["seed"], arm)
            ok &= nominal_digest(frames) == life["arms"][arm]["digest"]
    return {"passed": bool(ok)}


def c1_refusal():
    rows = []
    for seed in SEEDS:
        s, frames = run(seed, declines=(0, 96, 144))
        _, nominal = run(seed)
        rows.append({"seed": seed, "refused_assignments": s.declined_rounds,
                     "net": sum(f["net"][0] for f in frames), "nominal_net": sum(f["net"][0] for f in nominal),
                     "invariant": s.invariant()})
    return {"rows": rows, "limit": "refusals are not executed attempts: the row does not change",
            "passed": all(r["invariant"] for r in rows)}


def c2_relay():
    rows = []
    for seed in SEEDS:
        s, frames = run(seed, relay=True)
        _, nominal = run(seed)
        receipts = s.memory.receipts()
        rows_ok = all(f["evidence"] == R.last_attempt([r for r in receipts if r["tick"] < f["tick"]], f["type"])
                      for f in frames)
        relayed = [x for x in s.focal.cam.slot if x.occupied and x.source == RELAY_SOURCE]
        rows.append({"seed": seed, "relayed": s.relayed, "never_facts": all(not x.has_fact for x in relayed),
                     "rows_from_facts_only": rows_ok, "net": sum(f["net"][0] for f in frames),
                     "nominal_net": sum(f["net"][0] for f in nominal), "invariant": s.invariant()})
    return {"rows": rows, "passed": all(r["never_facts"] and r["rows_from_facts_only"] and r["invariant"]
                                        and r["relayed"] > 0 for r in rows)}


def c3_new_member():
    rows = []
    for seed in SEEDS:
        s, frames = run(seed, member=(240, 0, 2))
        rows.append({"seed": seed, "recovery": run_length(frames, 240, 48), "invariant": s.invariant()})
    return {"rows": rows, "criterion": "6 consecutive successes within 48 rounds of the new member",
            "passed": all(r["recovery"] < 48 and r["invariant"] for r in rows)}


def c4_absence():
    rows = []
    for seed in SEEDS:
        s, frames = run(seed, absent=(1, 72, 120))
        in_window = [f for f in frames if 72 <= f["tick"] < 120 and f["assignee"] == 1]
        receipts = s.memory.receipts()
        invented = [r for r in receipts if 72 <= r["tick"] < 120 and r["assignee"] == 1]
        rows.append({"seed": seed, "skipped": s.skipped, "assigned_to_absent": len(in_window),
                     "invented_receipts": len(invented), "recovery_after_return": run_length(frames, 120, 96),
                     "invariant": s.invariant()})
    return {"rows": rows, "passed": all(r["skipped"] == r["assigned_to_absent"] and r["invented_receipts"] == 0
                                        and r["invariant"] for r in rows)}


def c5_claimant():
    rows = []
    for seed in SEEDS:
        digests = [nominal_digest(run(seed, claimant=c)[1]) for c in (1, 2)]
        lucky = {c: [sum(f["output"][0] > 0 for f in run(seed, "rank_follow", claimant=c)[1][k:k + R.PERIOD])
                     for k in range(0, ROUNDS, R.PERIOD)] for c in (1, 2)}
        rows.append({"seed": seed, "identical": digests[0] == digests[1], "rank_follow_per_regime": lucky})
    return {"rows": rows, "passed": all(r["identical"] for r in rows)}


def c6_limits():
    s, frames = run(SEEDS[0], rounds=510)
    try:
        s.step()
        closed = False
    except RuntimeError:
        closed = True
    full = RolesCSession(SEEDS[0], 48)
    for _ in range(6):
        full.step()
    with patch.object(R, "allocate", return_value=(-1, None)):
        try:
            full.step()
            stopped = False
        except RuntimeError:
            stopped = full.failed and full.stopped
    passed = closed and stopped and s.invariant() and s.memory.count == 510 and s.focal.cam.destroyed == 0
    return {"rounds": 510, "note": "510 = largest balanced length within 512", "closed": closed,
            "cam_full_stops": stopped, "passed": bool(passed)}


def c7_operator():
    s = RolesCSession(SEEDS[0], 240)
    frames = [s.step(veto=(t >= 200, False, False)) for t in range(240)]
    after = frames[200:]
    s.stop()
    try:
        s.step()
        closed = False
    except RuntimeError:
        closed = True
    passed = all(f["paid"] == (0, 0, 0) and not f["executed"] for f in after) and closed and s.invariant()
    return {"vetoed": len(after), "cost_after_veto": sum(sum(f["paid"]) for f in after),
            "closed_after_stop": closed, "passed": bool(passed)}


def c8_corruption():
    s = RolesCSession(SEEDS[0], 48)
    for _ in range(12):
        s.step()
    slot = s.focal.cam.get(R.receipt_key(5))
    s.focal.cam.slot[slot].extract += " "
    ledger = tuple(s.ledger)
    try:
        s.step()
        raised = False
    except ValueError:
        raised = True
    passed = raised and s.failed and s.stopped and tuple(s.ledger) == ledger
    return {"raised": raised, "limit": "a canonical, physically possible forged receipt is not detectable",
            "passed": bool(passed)}


WITNESSES = {"c0_nominal_parity": c0_nominal_parity, "c1_refusal": c1_refusal, "c2_relay": c2_relay,
             "c3_new_member": c3_new_member, "c4_absence": c4_absence, "c5_claimant": c5_claimant,
             "c6_limits": c6_limits, "c7_operator": c7_operator, "c8_corruption": c8_corruption}


def sources():
    extras = ("echo4/roles_c.py", "echo4/roles_c_bench.py", "tests/test_echo4_roles1c.py",
              "docs/ECHO4-ROLES1-CD-DESIGN.md")
    return {**ab.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["findings"] != [] or report["development_criterion"] is not True):
        raise ValueError("ROLES A/B custody mismatch")
    ab.parent()
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    suite = unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_roles1c")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "seeds": SEEDS,
                       "scope": "ROLES-C development witnesses; D unopened"})
    witnesses = {name: w() for name, w in WITNESSES.items()}
    unit = tests()
    save("witnesses.json", witnesses)
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "witnesses": {k: v["passed"] for k, v in witnesses.items()}, "tests": unit,
              "phase_c_valid": all(v["passed"] for v in witnesses.values()) and unit["passed"],
              "roles1_green": False, "exam_opened": False}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value = [], None
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if hashlib.sha256(canonical(unsigned)).hexdigest() != value or report["schema"] != SCHEMA:
            raise ValueError("report digest/schema mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        for name, digest in report["artifacts"].items():
            if file_hash(directory / name) != digest:
                raise ValueError("artifact digest mismatch: " + name)
        campaign(directory, checking=True)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "roles1_green": False, "scope": "ROLES-C development witnesses; not an exam"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify", "explore"))
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        for name in args.only or WITNESSES:
            print(name, json.dumps(WITNESSES[name]()), flush=True)
        return 0
    if args.command == "campaign":
        args.directory.mkdir(parents=True, exist_ok=False)
        r = campaign(args.directory)
        print(json.dumps({k: r[k] for k in ("witnesses", "phase_c_valid", "reproduction_sha256")}, indent=2))
        return 0 if r["phase_c_valid"] else 1
    r = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
