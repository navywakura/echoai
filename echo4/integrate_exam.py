"""E4-INTEGRATE-1 exam: the approved D contract on 16 new seeds.

Contract: docs/ECHO4-INTEGRATE1-D-DESIGN.md (approved by Roger, 2026-09-24).
Parent: the sealed and audited development campaign integrate1-dev-v1.
Thresholds are the contract's, verbatim; nothing here is tuned after the exam.
"""
import argparse
import hashlib
import json
from pathlib import Path

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import integrate as I
from echoai.echo4 import integrate_bench as parent_module

SCHEMA_EXAM = "e4-integrate1-d-v1"
EXAM = tuple(range(271001, 271017))
PARENT = ROOT / "lab/echo4/integrate1-dev-v1"
PARENT_DIGEST = "873a9461f4ace8448b13814028717b838e6e57bb89e4e50fa59a0365fcac0f84"
MOST = 14                      # "in >= 14 of 16 seeds"


def _v(block, arm, key, idx=None):
    x = block["arms"][arm][key]
    return x if idx is None else x[idx]


def _tot(blocks, arm, key, idx=None):
    return sum(_v(b, arm, key, idx) for b in blocks)


def _count(blocks, pred):
    return sum(1 for b in blocks if pred(b))


def judge(blocks):
    """The D contract, criterion by criterion. Integer arithmetic only (ratios as a*100 >= k*b)."""
    n = len(blocks)
    most = n - (16 - MOST) * n // 16      # 14 of 16; all of a smaller dry-run cohort
    c = {}
    w_i, w_a = _tot(blocks, "integrated", "work"), _tot(blocks, "no_maintain", "work")
    c["1_no_maintain"] = {"work": [w_i, w_a],
                          "seeds_better": _count(blocks, lambda b: _v(b, "integrated", "work") > _v(b, "no_maintain", "work")),
                          "passed": w_i * 100 >= 115 * w_a}
    c["1_no_maintain"]["passed"] &= c["1_no_maintain"]["seeds_better"] >= most
    s_i, s_a = _tot(blocks, "integrated", "work"), _tot(blocks, "no_self", "work")
    rep = _count(blocks, lambda b: _v(b, "integrated", "repairs") > _v(b, "no_self", "repairs"))
    c["2_no_self"] = {"work": [s_i, s_a], "seeds_more_repairs": rep,
                      "passed": rep >= most and s_i * 100 >= 140 * s_a}
    q_i, q_a = _tot(blocks, "integrated", "questions"), _tot(blocks, "no_tribe_reasoning", "questions")
    k_i, k_a = (_tot(blocks, "integrated", "known_topic_first_ok", 0),
                _tot(blocks, "no_tribe_reasoning", "known_topic_first_ok", 0))
    c["3_no_tribe_reasoning"] = {"questions": [q_i, q_a], "known_first_ok": [k_i, k_a],
                                 "passed": q_i * 100 <= 80 * q_a and k_i >= 3 * k_a}
    r_i, r_a = (_tot(blocks, "integrated", "known_topic_first_ok", 0),
                _tot(blocks, "no_relation", "known_topic_first_ok", 0))
    rb = _count(blocks, lambda b: _v(b, "integrated", "known_topic_first_ok", 0) > _v(b, "no_relation", "known_topic_first_ok", 0))
    c["4_no_relation"] = {"known_first_ok": [r_i, r_a], "seeds_better": rb,
                          "passed": r_i * 100 >= 120 * r_a and rb >= most}
    f_zero = _count(blocks, lambda b: _v(b, "integrated", "false_facts") == 0)
    f_harm = _count(blocks, lambda b: _v(b, "no_firewall", "false_facts") > 0)
    c["5_no_firewall"] = {"integrated_zero": f_zero, "ablation_harm": f_harm,
                          "false_facts": [_tot(blocks, "integrated", "false_facts"), _tot(blocks, "no_firewall", "false_facts")],
                          "passed": f_zero == n and f_harm >= most}
    p_i, p_a = (_tot(blocks, "integrated", "post_pause_first_ok", 0),
                _tot(blocks, "no_continuity", "post_pause_first_ok", 0))
    pb = _count(blocks, lambda b: _v(b, "integrated", "post_pause_first_ok", 0) >= _v(b, "no_continuity", "post_pause_first_ok", 0))
    c["6_no_continuity"] = {"post_pause_first_ok": [p_i, p_a], "seeds_better_or_equal": pb,
                            "passed": p_i * 100 >= 150 * p_a and pb >= most}
    resumes = [r for b in blocks for r in b["resume"].values()]
    c["7_resume"] = {"identical": sum(r["identical"] for r in resumes),
                     "wrong_rejected": sum(r["wrong_digest_rejected"] for r in resumes), "of": len(resumes),
                     "passed": len(resumes) == 3 * n and all(r["identical"] and r["wrong_digest_rejected"] for r in resumes)}
    arms = [s for b in blocks for s in b["arms"].values()]
    c["8_invariants"] = {"passed": all(_v(b, "integrated", "survived") == I.HORIZON for b in blocks)
                         and all(s["situate_ok"] and s["cortex_calls"] == 0 and s["cam_destroyed"] == 0
                                 and s["tribe_invariant"] for s in arms)}
    wit = [w for b in blocks for w in b["witnesses"].values()]
    c["9_adversarial"] = {"passed_cases": sum(w["passed"] for w in wit), "of": len(wit),
                          "passed": len(wit) == len(parent_module.WITNESSES) * n and all(w["passed"] for w in wit)}
    c["10_profile"] = {"published": True, "gates_green": False,
                       "passed": all(b["profile"]["verdict"] is None for b in blocks)}
    return {"criteria": c, "passed": all(x["passed"] for x in c.values())}


def sources():
    extras = ("echo4/integrate_exam.py", "docs/ECHO4-INTEGRATE1-D-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["criteria_passed"] is not True):
        raise ValueError("INTEGRATE-1 development custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def campaign(directory, seeds, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA_EXAM, "sources": manifest, "parent": ancestry, "seeds": list(seeds),
                       "contract": "docs/ECHO4-INTEGRATE1-D-DESIGN.md"})
    blocks = [parent_module.seed_block(seed) for seed in seeds]
    for b in blocks:
        save(f"seed-{b['seed']}.json", b)
    verdict = judge(blocks)
    verdict["ablations"] = parent_module.ablation_table(blocks)
    unit = parent_module.tests()
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA_EXAM, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "verdict": verdict, "tests": unit, "passed": verdict["passed"] and unit["passed"]}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value, passed, official = [], None, False, False
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
        official = seeds == EXAM
        passed = campaign(directory, seeds, checking=True)["passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "integrate1_green": bool(official and passed and not findings),
            "scope": "INTEGRATE-1 exam reconstruction in a fresh process"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("exam", "verify-exam"))
    parser.add_argument("directory")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    directory = Path(args.directory)
    if args.command == "exam":
        directory.mkdir(parents=True, exist_ok=False)
        r = campaign(directory, EXAM)
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
