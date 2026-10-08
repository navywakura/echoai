"""E4-INTEGRATE-1 development bench: one life, seven arms, adversarial cases, profile.

Development only. Numeric thresholds for the ablation margins are fixed later in a
separate D contract; here the campaign reports them and checks the invariants the
design already fixes (zero false facts when firewalled, harm without the firewall,
bit-identical resume in a fresh process, SITUATE correct, cortex off, CAM intact).
"""
import argparse
import hashlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import integrate as I
from echoai.echo4 import tribe as T
from echoai.echo4 import situate2 as Z
from echoai.echo4 import situate2_bench as parent_module

SCHEMA_DEV = "e4-integrate1-dev-v1"
DEVELOPMENT = (811, 823, 839)
PARENT = ROOT / "lab/echo4/situate2-d-v1"
PARENT_DIGEST = "09f90a77d0e8cf3c85ed12b16d5f8014f8ba3367012057bc9238818dac156dfd"
RESUMED_ARMS = ("integrated", "no_continuity", "no_firewall")
PROFILE_ROUNDS = 192          # the liar acts from tick 192: the reference worlds agree before it


# ------------------------------------------------------------ adversarial cases (C)

def _decisions(life):
    return [[f["tick"], f["seeker"], f["topic"], f["attempts"], f["solved"]] for f in life["frames"]]


def c1_fault_and_liar(seed):
    life, _ = I.run(seed, "integrated", faults=((48, "clogged"), (200, "clogged")))
    s = I.summary(life)
    tribe = life["tribe"]
    lied = [f for f in life["frames"] if f.get("seeker") == T.ECHO and f["topic"] in tribe.lies]
    return {"seed": seed, "survived": s["survived"], "repairs": s["repairs"], "false_facts": s["false_facts"],
            "lied_rounds": len(lied), "lied_solved": sum(f["solved"] for f in lied),
            "passed": bool(s["survived"] == I.HORIZON and s["repairs"] >= 2 and s["false_facts"] == 0
                           and s["tribe_invariant"] and lied and s["cam_destroyed"] == 0)}


def c2_pause_after_fault(seed):
    pause = I.FAULTS_AT[0][0] + 1
    control, _ = I.run(seed, "integrated")
    paused, digest = I.run(seed, "integrated", until=pause, pause_digest=True, pause=pause)
    if digest is None:
        digest = I.fingerprint(paused)
    resumed = I.resume_fresh_process(seed, "integrated", digest, pause)
    want = I.summary(control)["trace_sha256"]
    return {"seed": seed, "pause": pause, "fault_before_pause": paused["body"].env._fault != "healthy",
            "resumed": resumed, "control": want,
            "passed": bool(resumed == want and paused["body"].env._fault != "healthy")}


def c3_no_energy_at_hierarchy_change(seed):
    at, level, seen = 188, 25, {}
    def drain(life):
        I.credit(life["body"], level - life["body"].env.body.h)
        seen["h"] = life["body"].env.body.h
    control, _ = I.run(seed, "integrated")
    drained, _ = I.run(seed, "integrated", hooks={at: (drain,)})
    s = I.summary(drained)
    low = seen["h"]
    rows_c, rows_d = control["tribe"].memories[T.ECHO].rows, drained["tribe"].memories[T.ECHO].rows
    return {"seed": seed, "drained_to": low, "survived": s["survived"], "false_facts": s["false_facts"],
            "same_social_decisions": _decisions(control) == _decisions(drained),
            "same_derived_order": T.derived_order(rows_c, I.HORIZON - 1) == T.derived_order(rows_d, I.HORIZON - 1),
            "passed": bool(s["survived"] == I.HORIZON and s["false_facts"] == 0 and low <= level
                           and _decisions(control) == _decisions(drained))}


def c4_corrupt_fact(seed):
    at = 100
    def corrupt(life):
        cam = life["body"].cam
        cam.slot[cam.get(T.event_key(3))].extract += " "
    life, _ = I.run(seed, "integrated", hooks={at: (corrupt,)})
    rows = life["tribe"].memories[T.ECHO]
    stopped_at = life["tick"]
    return {"seed": seed, "ended": life["ended"], "stopped_at": stopped_at, "cam_destroyed": life["body"].cam.destroyed,
            "passed": bool(life["ended"] == "tribe:ValueError" and at <= stopped_at <= at + 2
                           and life["body"].cam.destroyed == 0 and rows.stopped)}


def c4b_testimony_forged_as_fact(seed):
    """A testimony slot rewritten to look like a fact must be detected by the invariant."""
    life, _ = I.run(seed, "integrated", until=100)
    cam = life["body"].cam
    slot = next(i for i, x in enumerate(cam.slot) if x.occupied and x.source == T.TESTIMONY_SOURCE)
    before = life["tribe"].memories[T.ECHO].invariant()
    cam.slot[slot].has_fact, cam.slot[slot].extract = 1, "C does not know"
    after = life["tribe"].memories[T.ECHO].invariant()
    return {"seed": seed, "invariant_before": before, "invariant_after": after,
            "passed": bool(before and not after)}


def c5_cam_full(seed):
    at, box = 100, {}
    def fill(life):
        box["patch"] = patch.object(T, "allocate", return_value=(-1, None))
        box["patch"].start()
    try:
        life, _ = I.run(seed, "integrated", hooks={at: (fill,)})
    finally:
        if "patch" in box:
            box["patch"].stop()
    return {"seed": seed, "ended": life["ended"], "stopped_at": life["tick"],
            "cam_destroyed": life["body"].cam.destroyed,
            "passed": bool(life["ended"] == "tribe:RuntimeError" and life["tick"] <= at + 2
                           and life["body"].cam.destroyed == 0)}


def c6_veto_and_operator_stop(seed):
    veto_from, stop_at = 200, 230
    def stop(life):
        life["body"].env.stop()
    life, _ = I.run(seed, "integrated", veto_from=veto_from, hooks={stop_at: (stop,)})
    vetoed = [f for f in life["frames"] if f["tick"] >= veto_from and f.get("seeker") == T.ECHO]
    last = life["frames"][-1]
    body = life["body"].env.body
    return {"seed": seed, "vetoed_rounds": len(vetoed), "asked_after_veto": sum(len(f["attempts"]) for f in vetoed),
            "energy_after_veto": sum(f.get("energy", 0) for f in vetoed), "ended": life["ended"],
            "frames": len(life["frames"]),
            "passed": bool(vetoed and not any(f["attempts"] for f in vetoed)
                           and all(f.get("energy", 0) == 0 for f in vetoed)
                           and life["ended"] == "operator" and len(life["frames"]) == stop_at
                           and (body.h, body.temperature) == (last["h"], last["temp"]))}


WITNESSES = (c1_fault_and_liar, c2_pause_after_fault, c3_no_energy_at_hierarchy_change, c4_corrupt_fact,
             c4b_testimony_forged_as_fact, c5_cam_full, c6_veto_and_operator_stop)


# ------------------------------------------------------------ indicator profile (Butlin et al. 2023)

def integrated_trace(life, rounds=PROFILE_ROUNDS):
    frames = [{"tick": f["tick"], "seeker": f["seeker"], "knower": f["knower"], "solved": f["solved"],
               "attempts": f["attempts"], "suggestion": f["suggestion"]}
              for f in life["frames"][:rounds]]
    rows = [r for r in life["tribe"].memories[T.ECHO].rows if r["tick"] < rounds]
    return {"frames": frames, "rows": rows, "tick": rounds - 1}


def integrated_profile(seed, lives):
    """Same fixed catalog and trivial controls as SITUATE-2; ECHO is the integrated life."""
    traces = Z.reference_traces(seed, PROFILE_ROUNDS)
    traces["echo_full"] = integrated_trace(lives["integrated"])
    prof = Z.profile(traces)
    prof["echo_full_is"] = "integrated life (body + tribe, one CAM/T/Q), first 192 ticks"
    return prof


# ------------------------------------------------------------ campaign

def seed_block(seed):
    lives, summaries, resumes = {}, {}, {}
    for arm in I.ARMS:
        life, digest = I.run(seed, arm, pause_digest=True)
        lives[arm], summaries[arm] = life, I.summary(life)
        if arm in RESUMED_ARMS:
            resumed = I.resume_fresh_process(seed, arm, digest)
            try:
                I.resume_fresh_process(seed, arm, "0" * 64)
                wrong_rejected = False
            except RuntimeError:
                wrong_rejected = True
            resumes[arm] = {"pause_fingerprint": digest, "resumed": resumed,
                            "identical": resumed == summaries[arm]["trace_sha256"],
                            "wrong_digest_rejected": wrong_rejected}
    witnesses = {w.__name__: w(seed) for w in WITNESSES}
    return {"seed": seed, "arms": summaries, "resume": resumes, "witnesses": witnesses,
            "profile": integrated_profile(seed, lives)}


def ablation_table(blocks):
    """Target metric per ablation (reported; margins are fixed in the D contract)."""
    def total(arm, key, idx=None):
        return sum(b["arms"][arm][key] if idx is None else b["arms"][arm][key][idx] for b in blocks)
    return {
        "no_maintain": {"metric": "work", "integrated": total("integrated", "work"), "ablation": total("no_maintain", "work")},
        "no_self": {"metric": "repairs", "integrated": total("integrated", "repairs"), "ablation": total("no_self", "repairs")},
        "no_tribe_reasoning": {"metric": "questions (lower is better)", "integrated": total("integrated", "questions"),
                               "ablation": total("no_tribe_reasoning", "questions")},
        "no_relation": {"metric": "known_topic_first_ok", "integrated": total("integrated", "known_topic_first_ok", 0),
                        "ablation": total("no_relation", "known_topic_first_ok", 0)},
        "no_firewall": {"metric": "false_facts (lower is better)", "integrated": total("integrated", "false_facts"),
                        "ablation": total("no_firewall", "false_facts")},
        "no_continuity": {"metric": "post_pause_first_ok", "integrated": total("integrated", "post_pause_first_ok", 0),
                          "ablation": total("no_continuity", "post_pause_first_ok", 0)},
    }


def judge(blocks):
    """Development checks fixed by the design. Ablation margins are reported, not judged."""
    arms = [s for b in blocks for s in b["arms"].values()]
    integ = [b["arms"]["integrated"] for b in blocks]
    checks = {
        "integrated_survives": all(s["survived"] == I.HORIZON for s in integ),
        "integrated_zero_false_facts": all(s["false_facts"] == 0 for s in integ),
        "no_firewall_produces_false_facts": all(b["arms"]["no_firewall"]["false_facts"] > 0 for b in blocks),
        "resume_identical": all(r["identical"] and r["wrong_digest_rejected"]
                                for b in blocks for r in b["resume"].values()),
        "situate_ok": all(s["situate_ok"] for s in arms),
        "cortex_off": all(s["cortex_calls"] == 0 for s in arms),
        "cam_intact": all(s["cam_destroyed"] == 0 and s["tribe_invariant"] for s in arms),
        "witnesses": all(w["passed"] for b in blocks for w in b["witnesses"].values()),
        "profile_is_not_a_verdict": all(b["profile"]["verdict"] is None for b in blocks),
    }
    return {"checks": checks, "ablations": ablation_table(blocks), "passed": all(checks.values())}


def sources():
    extras = ("echo4/integrate.py", "echo4/integrate_bench.py", "tests/test_echo4_integrate1.py",
              "docs/ECHO4-INTEGRATE1-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["situate2_green"] is not True):
        raise ValueError("SITUATE-2 custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_integrate1"))
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, schema, seeds, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": schema, "sources": manifest, "parent": ancestry, "seeds": list(seeds),
                       "contract": "docs/ECHO4-INTEGRATE1-DESIGN.md"})
    blocks = [seed_block(seed) for seed in seeds]
    for b in blocks:
        save(f"seed-{b['seed']}.json", b)
    verdict = judge(blocks)
    unit = tests()
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": schema, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "verdict": verdict, "tests": unit, "passed": verdict["passed"] and unit["passed"],
              "integrate1_green": False}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value, passed = [], None, False
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if hashlib.sha256(canonical(unsigned)).hexdigest() != value:
            raise ValueError("report digest mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        for name, d in report["artifacts"].items():
            if file_hash(directory / name) != d:
                raise ValueError("artifact digest mismatch: " + name)
        seeds = tuple(read_json(directory / "lock.json")["seeds"])
        passed = campaign(directory, report["schema"], seeds, checking=True)["passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings), "integrate1_green": False,
            "scope": "INTEGRATE-1 development reconstruction in a fresh process (not an exam)"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dev", "verify-dev", "explore"))
    parser.add_argument("arg", nargs="?")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        blocks = [seed_block(s) for s in DEVELOPMENT]
        print(json.dumps(judge(blocks), indent=1, ensure_ascii=False))
        return 0
    directory = Path(args.arg)
    if args.command == "dev":
        directory.mkdir(parents=True, exist_ok=False)
        r = campaign(directory, SCHEMA_DEV, DEVELOPMENT)
        print(json.dumps({"verdict": r["verdict"], "passed": r["passed"], "sha": r["reproduction_sha256"]},
                         indent=1, ensure_ascii=False))
        return 0 if r["passed"] else 1
    r = verify(directory)
    if args.write_receipt:
        persist(directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
