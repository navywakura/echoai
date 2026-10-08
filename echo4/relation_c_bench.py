"""RELATION-C witnesses on development seeds. Limits are published, not hidden."""
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
from echoai.echo4.interaction_cases import fixture, ROUNDS, FORMATION
from echoai.echo4.other_model import LIMIT
from echoai.echo4.relation_help import bucket, WINDOW
from echoai.echo4.relation_c import RelationCSession
from echoai.echo4 import relation_b_bench as b
from echoai.echo4 import relation_help as help_module

SCHEMA = "echo4-relation1-c-dev-v1"
PARENT = ROOT / "lab/echo4/relation1-b-dev-v1"
PARENT_DIGEST = "ea6f55c28a58582df934e259367bc6fa88ecbe256f1fc196e49da737e780239f"
SEEDS = b.DEVELOPMENT
RELIEF = FORMATION + b.B_FORMATION  # encounter 384
ABSENCE = (336, 384)
RELIABLE = (0, 1, 2)  # joins at cue 0, the only productive joint cue it prefers


def reliable_handle(session):
    return 1 + session._preferences.index(RELIABLE)


def life(seed, arm, *, cues=None, schedule=None, relief=None, outcomes=None, veto_at=None):
    base_cues, base_schedule, swapped = fixture(seed)
    cues, schedule = cues or base_cues, schedule or base_schedule
    s = RelationCSession(cues, schedule, b_arm=arm, seed=seed, swapped=swapped)
    frames, a_frames, levels = [], [], []
    handle_relieved = None
    for t in range(len(cues)):
        if relief and t == RELIEF:
            handle_relieved = reliable_handle(s)
            s.relieve(handle_relieved, *relief, seed=seed)
        if t >= FORMATION:
            h = schedule[t]
            partner_level = s.partner_level(h)
            f = s.help_step(greedy=t >= RELIEF, veto=(veto_at is not None and t >= veto_at, False))
            frames.append(f)
            levels.append((f["level"], partner_level))
        kwargs = {"outcomes": outcomes(t)} if outcomes else {}
        a_frames.append(s.step(greedy=t >= FORMATION, **kwargs))
    return s, frames, a_frames, levels, handle_relieved


def refusals(frames, handle, start):
    return sum(f["asked"] and not f["helped"] for f in frames if f["handle"] == handle and f["tick"] >= start)


def c0_nominal_parity():
    """RelationCSession reproduces the sealed B development frames exactly."""
    sealed = read_json(PARENT / "development.json")
    ok = True
    for seed in SEEDS:
        _, frames, _, _, _ = life(seed, "history")
        ok &= b.b_summary(frames) == sealed["lives"][SEEDS.index(seed)]["arms"]["history"]["b"]
    return {"passed": bool(ok)}


def c1_relief():
    rows = []
    for seed in SEEDS:
        row = {"seed": seed}
        for arm in ("history", "other_only"):
            s, frames, _, _, h = life(seed, arm, relief=((1, 2, 0), "reciprocal"))
            row[arm] = {"refusals_after_relief": refusals(frames, h, RELIEF),
                        "asks_after_relief": sum(f["asked"] for f in frames if f["handle"] == h and f["tick"] >= RELIEF),
                        "focal_b_net": b.b_summary(frames)["net"][0], "invariant": s.invariant()}
        rows.append(row)
    passed = all(r["history"]["refusals_after_relief"] <= WINDOW and r["history"]["invariant"] for r in rows)
    return {"rows": rows, "criterion": f"history refusals after relief <= {WINDOW}", "passed": passed}


def c2_impostor():
    rows = []
    for seed in SEEDS:
        s, frames, _, _, h = life(seed, "history", relief=(RELIABLE, "never"))
        _, nominal, _, _, _ = life(seed, "history")
        rows.append({"seed": seed, "refusals_after_relief": refusals(frames, h, RELIEF),
                     "focal_b_net": b.b_summary(frames)["net"][0],
                     "nominal_focal_b_net": b.b_summary(nominal)["net"][0], "invariant": s.invariant()})
    return {"rows": rows, "limit": "history says >=1 recent success and the body never helps; reputation is not a guarantee",
            "passed": all(r["invariant"] for r in rows)}


def c3_absence():
    rows = []
    for seed in SEEDS:
        cues, schedule, swapped = fixture(seed)
        probe = RelationCSession(cues, schedule, b_arm="history", seed=seed, swapped=swapped)
        other = 3 - reliable_handle(probe)
        gap = tuple(other if ABSENCE[0] <= t < ABSENCE[1] else h for t, h in enumerate(schedule))
        s, frames, _, levels, _ = life(seed, "history", schedule=gap)
        counts = [sum(1 for h in gap if h == k) for k in (1, 2)]
        rows.append({"seed": seed, "absent_handle": 3 - other, "levels_agree": all(x == y for x, y in levels),
                     "episodes_match": [s.relations[0].summary(k)["encounters"] for k in (1, 2)] == counts,
                     "invariant": s.invariant(), "focal_b_net": b.b_summary(frames)["net"][0]})
    return {"rows": rows, "passed": all(r["levels_agree"] and r["episodes_match"] and r["invariant"] for r in rows)}


def c4_partial():
    rows = []
    for seed in SEEDS:
        s, frames, _, levels, _ = life(seed, "history", outcomes=lambda t: (t % 3 != 0, True))
        _, nominal, _, _, _ = life(seed, "history")
        rows.append({"seed": seed, "below_partner": sum(x < y for x, y in levels),
                     "above_partner": sum(x > y for x, y in levels),
                     "focal_b_net": b.b_summary(frames)["net"][0],
                     "nominal_focal_b_net": b.b_summary(nominal)["net"][0], "invariant": s.invariant()})
    ok = all(r["above_partner"] == 0 and r["invariant"] for r in rows)  # missing never becomes success
    return {"rows": rows, "limit": "unseen receipts lower the learner's bucket; cost published", "passed": ok}


def c5_new_identity():
    rows = []
    for seed in SEEDS:
        cues, schedule, swapped = fixture(seed)
        probe = RelationCSession(cues, schedule, b_arm="history", seed=seed, swapped=swapped)
        known = reliable_handle(probe)
        late = tuple(known if t < FORMATION else h for t, h in enumerate(schedule))
        row = {"seed": seed}
        for arm in ("history", "pooled"):
            s, frames, _, _, _ = life(seed, arm, schedule=late)
            first = next(f for f in frames if f["handle"] != known)
            row[arm] = {"first_level": first["level"], "invariant": s.invariant()}
        rows.append(row)
    ok = all(r["history"]["first_level"] == 0 and r["history"]["invariant"] for r in rows)
    return {"rows": rows, "note": "pooled level is published: it borrows another identity's history", "passed": ok}


def c6_corruption():
    seed = SEEDS[0]
    cues, schedule, swapped = fixture(seed)
    s = RelationCSession(cues, schedule, b_arm="history", seed=seed, swapped=swapped)
    for t in range(FORMATION):
        s.step(greedy=False)
    handle = schedule[FORMATION]
    slot = s.relations[0].peer_heads[handle]
    row = s.focal.cam.slot[slot]
    row.extract = row.extract.replace('"paid":', '"paid": ', 1)
    ledger, turns = tuple(s.ledger), tuple(s.b_turns)
    try:
        s.help_step()
        raised = False
    except (ValueError, RuntimeError):
        raised = True
    passed = raised and s.failed and s.stopped and tuple(s.ledger) == ledger and tuple(s.b_turns) == turns
    return {"raised": raised, "failed": s.failed, "stopped": s.stopped, "passed": bool(passed)}


def c7_limits():
    seed = SEEDS[0]
    cues, schedule, swapped = fixture(seed)
    cues, schedule = (cues + cues)[:LIMIT], (schedule + schedule)[:LIMIT]
    s, frames, _, _, _ = life(seed, "history", cues=cues, schedule=schedule)
    ends = []
    for call in (lambda: s.help_step(), lambda: s.step()):
        try:
            call()
            ends.append(False)
        except RuntimeError:
            ends.append(True)
    full = RelationCSession(*fixture(seed)[:2], b_arm="history", seed=seed)
    for t in range(FORMATION):
        full.step()
    with patch.object(help_module, "allocate", return_value=(-1, None)):
        try:
            full.help_step()
            capacity = False
        except RuntimeError:
            capacity = full.failed and full.stopped
    passed = (all(ends) and s.invariant() and s.relations[0].count == LIMIT
              and s.focal.cam.destroyed == 0 and capacity)
    return {"episodes": s.relations[0].count, "closed_after_limit": ends, "cam_full_stops": capacity,
            "passed": bool(passed)}


def c8_operator():
    seed = SEEDS[0]
    s, frames, _, _, _ = life(seed, "always_ask", veto_at=400)
    after = [f for f in frames if f["tick"] >= 400]
    s.stop()
    try:
        s.help_step()
        closed = False
    except RuntimeError:
        closed = True
    passed = all(not f["asked"] and f["paid"] == (0, 0) for f in after) and closed
    return {"vetoed_steps": len(after), "asks_after_veto": sum(f["asked"] for f in after),
            "closed_after_stop": closed, "passed": bool(passed)}


WITNESSES = {"c0_nominal_parity": c0_nominal_parity, "c1_relief": c1_relief, "c2_impostor": c2_impostor,
             "c3_absence": c3_absence, "c4_partial": c4_partial, "c5_new_identity": c5_new_identity,
             "c6_corruption": c6_corruption, "c7_limits": c7_limits, "c8_operator": c8_operator}


def sources():
    extras = ("echo4/relation_c.py", "echo4/relation_c_bench.py", "tests/test_echo4_relation1c.py",
              "docs/ECHO4-RELATION1-CD-DESIGN.md")
    return {**b.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["findings"] != [] or report["development_criterion"] is not True):
        raise ValueError("RELATION-B development custody mismatch")
    b.parent()  # RELATION-A custody too
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    suite = unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_relation1c")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "seeds": SEEDS,
                       "scope": "RELATION-C development witnesses; D unopened"})
    witnesses = {name: run() for name, run in WITNESSES.items()}
    unit = tests()
    save("witnesses.json", witnesses)
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "witnesses": {k: v["passed"] for k, v in witnesses.items()}, "tests": unit,
              "phase_c_valid": all(v["passed"] for v in witnesses.values()) and unit["passed"],
              "relation1_green": False, "exam_opened": False}
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
            "relation1_green": False, "scope": "RELATION-C development witnesses; not an exam"}


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
