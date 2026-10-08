"""An auditor that does not read ``sim3_green``.

It rebuilds the evidence instead: it regenerates the twelve rehearsal
packages from the published seeds, re-hashes every trace file, recomputes
the fall, the resting height, the contact and the tick count from the raw
frames, and recomputes the protocol commitment and the code inventory.
Only then does it compare its own numbers with what the report claims.

``evidence_valid`` means the evidence reconstructs. It does not mean the
bench passed: a red report with perfectly reconstructible traces is
exactly what an honest failure looks like.

``--self-test`` mutates copies of the report — a flipped result, a bumped
counter, a rewritten trace hash, two different runtime locks — and
requires each to be rejected. Detection is claimed only from a positive
control that the auditor accepted first.
"""

from __future__ import annotations

import copy
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    canonical_sha256,
    loads_strict,
    read_bounded,
    report_sha256,
    sha256_bytes,
)
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import Package, load_protocol
from echoai.nexus0.sim3.rig import RIG_COLLISION, RIG_MODEL
from echoai.nexus0.sim3.runtime import ECHOAI, code_inventory
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET, protocol_commitment

MAX_REPORT_BYTES = 64 << 20


@dataclass
class Audit:
    findings: List[Dict] = field(default_factory=list)
    checks: int = 0

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks += 1
        if not ok:
            self.findings.append({"check": name, "detail": detail})
        return ok

    @property
    def ok(self) -> bool:
        return not self.findings


def _load_report(path: Path) -> Dict:
    raw = Path(path).read_bytes()
    if len(raw) > MAX_REPORT_BYTES:
        raise Sim3Error("report_too_large", str(len(raw)))
    return loads_strict(raw, code="report")


def _rebuild_packages(protocol_path: Path) -> Tuple[Dict[str, Package], Path]:
    """Regenerate the rehearsal suite from published seeds, independently."""
    protocol = load_protocol(protocol_path)
    tmp = Path(tempfile.mkdtemp(prefix="sim3-audit-"))
    results = generate_suite(tmp, protocol, REHEARSAL_SECRET, rehearsal_assignment())
    return {r.package_id: r.package for r in results}, tmp


def audit_report(report: Dict, *, rebuild: bool = True) -> Dict:
    a = Audit()
    recomputed: Dict[str, Dict] = {}

    stated = report.get("report_sha256")
    fresh = report_sha256({k: v for k, v in report.items()
                           if k != "report_sha256"})
    a.check("report_sha256", stated == fresh,
            f"stated {stated}, recomputed {fresh}")

    a.check("scope", report.get("scope") == "simulation_infrastructure",
            str(report.get("scope")))
    a.check("dataset_kind", report.get("dataset_kind") == "rehearsal",
            str(report.get("dataset_kind")))
    a.check("hardware_status", report.get("hardware_status") == "not_available",
            str(report.get("hardware_status")))
    a.check("agent_in_gazebo", report.get("agent_in_gazebo") is False,
            str(report.get("agent_in_gazebo")))

    # Protocol: bytes on disk, then the published rehearsal commitment.
    proto_rel = report.get("protocol", {}).get("path", "")
    proto_path = ECHOAI / proto_rel
    proto_sha = None
    if proto_path.exists():
        proto_sha = sha256_bytes(read_bounded(proto_path, code="protocol"))
        a.check("protocol_sha256", proto_sha == report["protocol"]["sha256"],
                f"file {proto_sha}")
        a.check("protocol_commitment",
                protocol_commitment(proto_sha, REHEARSAL_SECRET)
                == report["protocol"].get("rehearsal_commitment"),
                "recomputed commitment differs")
    else:
        a.check("protocol_present", False, f"missing {proto_path}")

    entries, code_sha = code_inventory()
    a.check("code_sha256",
            code_sha == report.get("runtime_lock", {}).get("code_sha256"),
            f"recomputed {code_sha}")

    # One runtime for every world, or the comparison is not a comparison.
    # Two separate questions: does every run name the same lock, and does
    # that lock still hash to what the frozen file on disk contains?
    stated_lock = report.get("runtime_lock", {}).get("lock_sha256")
    run_locks = {r.get("lock_sha256") for r in report.get("runs", [])}
    a.check("single_runtime_lock", run_locks <= {stated_lock},
            f"runs report {sorted(x for x in run_locks if x != stated_lock)}")
    lock_rel = report.get("runtime_lock", {}).get("path", "")
    lock_path = ECHOAI / lock_rel if lock_rel else None
    if lock_path is not None and lock_path.exists():
        lock = loads_strict(read_bounded(lock_path, code="lock"), code="lock")
        rebuilt = canonical_sha256({k: v for k, v in lock.items()
                                    if k != "lock_sha256"})
        a.check("lock_self_consistent", rebuilt == lock.get("lock_sha256"),
                f"recomputed {rebuilt}")
        a.check("lock_matches_report", lock.get("lock_sha256") == stated_lock,
                f"lock file {lock.get('lock_sha256')}, report {stated_lock}")
    else:
        a.check("lock_present", False, f"missing {lock_path}")

    # Traces: hash on disk, then recompute the physics from the frames.
    trace_index = {t["run_id"]: t for t in report.get("traces", {}).get("files", [])}
    packages: Dict[str, Package] = {}
    tmp: Optional[Path] = None
    if rebuild and proto_path.exists():
        try:
            packages, tmp = _rebuild_packages(proto_path)
        except Sim3Error as exc:
            a.check("suite_rebuild", False, f"{exc.code}: {exc.detail}")

    try:
        if packages:
            for row in report.get("assignment", []):
                pkg = packages.get(row["package_id"])
                a.check(f"assignment/{row['package_id']}", pkg is not None,
                        "package id not reproduced from published seeds")
                if pkg is not None:
                    a.check(f"package_sha/{row['package_id']}",
                            pkg.package_sha256 == row["package_sha256"],
                            f"recomputed {pkg.package_sha256}")
                    a.check(f"fingerprint/{row['package_id']}",
                            pkg.fingerprint_sha256 == row["fingerprint_sha256"],
                            f"recomputed {pkg.fingerprint_sha256}")
            fps = [r["fingerprint_sha256"] for r in report.get("assignment", [])]
            a.check("fingerprints_distinct", len(set(fps)) == len(fps),
                    "two rehearsal worlds share a geometry footprint")

        # Every trace file, including the collision probes no run row
        # points at: a hash nobody checks is not evidence.
        for entry in report.get("traces", {}).get("files", []):
            path = ECHOAI / entry["path"]
            if not path.exists():
                a.check(f"trace_file/{entry['run_id']}", False, f"missing {path}")
                continue
            digest = sha256_bytes(path.read_bytes())
            a.check(f"trace_sha/{entry['run_id']}", digest == entry["sha256"],
                    f"recomputed {digest}")

        protocol = load_protocol(proto_path) if proto_path.exists() else None
        for run in report.get("runs", []):
            entry = trace_index.get(run["run_id"])
            if entry is None:
                a.check(f"trace/{run['run_id']}", False, "no trace recorded")
                continue
            path = ECHOAI / entry["path"]
            if not path.exists():
                a.check(f"trace_file/{run['run_id']}", False, f"missing {path}")
                continue
            trace = loads_strict(path.read_bytes(), code="trace")
            a.check(f"trace_ticks/{run['run_id']}",
                    trace.get("n_ticks") == run.get("n_ticks"),
                    f"trace {trace.get('n_ticks')} vs report {run.get('n_ticks')}")
            a.check(f"trace_transcript/{run['run_id']}",
                    trace.get("tick_transcript_sha256")
                    == run.get("tick_transcript_sha256"), "transcript hash differs")
            a.check(f"trace_effective/{run['run_id']}",
                    trace.get("effective_sha256") == run.get("effective_sha256"),
                    "effective sdf hash differs")
            if run["group"] == "physics" and protocol is not None:
                pkg = packages.get(run["package_id"])
                if pkg is not None:
                    recomputed[run["run_id"]] = _recompute_physics(trace, pkg,
                                                                   protocol)

        for case in report.get("groups", {}).get("physics", {}).get("cases", []):
            mine = recomputed.get(case["run_id"])
            if mine is None:
                continue
            claimed = case.get("measured", {})
            for key in ("fall_mm", "rest_error_mm", "n_frames", "n_ticks",
                        "n_contact_msgs"):
                a.check(f"recompute/{case['run_id']}/{key}",
                        _close(mine.get(key), claimed.get(key)),
                        f"auditor {mine.get(key)} vs report {claimed.get(key)}")
            a.check(f"recompute/{case['run_id']}/verdict",
                    mine["ok"] == case.get("ok"),
                    f"auditor {mine['ok']} vs report {case.get('ok')}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)

    # Group bookkeeping: a status must follow from its own cases.
    for name, group in report.get("groups", {}).items():
        cases = group.get("cases", [])
        flags = [c["ok"] for c in cases if isinstance(c, dict) and "ok" in c]
        if flags and group.get("status") == "pass":
            a.check(f"group_consistency/{name}", all(flags),
                    f"{flags.count(False)} failing cases inside a pass")
        if group.get("status") not in ("pass", "fail", "not_run"):
            a.check(f"group_status/{name}", False, str(group.get("status")))

    stated_green = report.get("sim3_green")
    derived = all(v == "pass" for v in report.get("group_status", {}).values()) \
        and bool(report.get("group_status"))
    a.check("sim3_green_consistent", stated_green == derived,
            f"stated {stated_green}, derived {derived}")

    return {
        "evidence_valid": a.ok,
        "checks": a.checks,
        "findings": a.findings,
        "recomputed_runs": len(recomputed),
        "sim3_green_as_reported": stated_green,
        "note": "evidence_valid means the evidence reconstructs, not that the "
                "bench passed",
    }


def _close(a, b, tol: float = 1e-6) -> bool:
    if a is None or b is None:
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def _recompute_physics(trace: Dict, package: Package, protocol) -> Dict:
    """The auditor's own arithmetic over the raw frames."""
    rig = protocol.rig
    crit = protocol.criteria
    step_ns = protocol.step_ns
    frames = trace.get("frames_um", [])
    initial = trace.get("initial", {})
    z0 = initial.get("rig_um", [0, 0, 0])[2]
    sample_ns = int(rig["fall_sample_ns"])
    sampled = next((f for f in frames if f[0] == sample_ns), None)
    fall_mm = None if sampled is None else round((z0 - sampled[3]) / 1000.0, 3)
    floor_top = package.aabb_of(package.floor).hi[2]
    rest = frames[-1][3] if frames else 0
    rest_err = round(abs(rest - (floor_top + int(rig["radius_mm"])) * 1000)
                     / 1000.0, 3)
    report = trace.get("gz_report", {}) or {}
    pairs = [tuple(p) for p in report.get("pairs", [])]
    want_rig = f"{RIG_MODEL}::body::{RIG_COLLISION}"
    want_floor = f"{package.floor}::body::solid"
    clock_ok = all(f[0] == (i + 1) * step_ns for i, f in enumerate(frames))
    ok = bool(
        trace.get("ok")
        and len(frames) == protocol.steps
        and trace.get("n_ticks") == protocol.steps + 1
        and initial.get("sim_time_ns") == 0
        and clock_ok
        and fall_mm is not None
        and crit["fall_min_mm"] <= fall_mm <= crit["fall_max_mm"]
        and rest_err <= crit["rest_error_mm"]
        and int(report.get("n_contact_msgs", 0)) > 0
        and any(want_rig in p and want_floor in p for p in pairs)
        and trace.get("gravity_um") == [0, 0, -9810000]
    )
    return {"fall_mm": fall_mm, "rest_error_mm": rest_err,
            "n_frames": len(frames), "n_ticks": trace.get("n_ticks"),
            "n_contact_msgs": int(report.get("n_contact_msgs", 0)),
            "clock_monotonic": clock_ok, "ok": ok}


# --- mutation of evidence --------------------------------------------------

def _mut_flip_result(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    cases = out["groups"]["physics"]["cases"]
    cases[0]["ok"] = not cases[0]["ok"]
    return out


def _mut_bump_counter(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["groups"]["physics"]["cases"][0]["measured"]["n_contact_msgs"] += 100
    return out


def _mut_trace_hash(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["traces"]["files"][0]["sha256"] = "0" * 64
    return out


def _mut_two_locks(report: Dict) -> Dict:
    """A report that claims a runtime the frozen lock does not describe."""
    out = copy.deepcopy(report)
    out["runtime_lock"]["lock_sha256"] = "f" * 64
    for run in out["runs"]:
        run["lock_sha256"] = "f" * 64
    return out


def _mut_run_lock(report: Dict) -> Dict:
    """One world quietly measured under a different runtime."""
    out = copy.deepcopy(report)
    out["runs"][3]["lock_sha256"] = "e" * 64
    return out


def _mut_green(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["sim3_green"] = True
    out["group_status"] = dict(out["group_status"])
    out["group_status"]["physics"] = "fail"
    return out


def _mut_measured(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["groups"]["physics"]["cases"][0]["measured"]["fall_mm"] = 200.0
    return out


def _mut_protocol(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["protocol"]["sha256"] = "a" * 64
    return out


def _mut_code(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["runtime_lock"]["code_sha256"] = "b" * 64
    return out


REPORT_MUTANTS = (
    ("flipped_case_result", _mut_flip_result),
    ("bumped_contact_counter", _mut_bump_counter),
    ("rewritten_trace_hash", _mut_trace_hash),
    ("different_runtime_lock", _mut_two_locks),
    ("one_world_on_another_runtime", _mut_run_lock),
    ("green_without_groups", _mut_green),
    ("altered_measurement", _mut_measured),
    ("wrong_protocol_hash", _mut_protocol),
    ("wrong_code_hash", _mut_code),
)


def self_test(report: Dict) -> Dict:
    """Detection is only claimed from a control the auditor accepted."""
    control = audit_report(report)
    cases = [{"mutant": "positive_control",
              "expected": "evidence_valid", "observed": control["evidence_valid"],
              "findings": control["findings"][:3],
              "ok": control["evidence_valid"]}]
    if not control["evidence_valid"]:
        cases[0]["note"] = ("control is already red; mutant detection below is "
                            "not evidence of detection")
    for name, mutate in REPORT_MUTANTS:
        mutated = mutate(report)
        # A tamperer would of course re-stamp the digest, so do it for them.
        mutated["report_sha256"] = report_sha256(
            {k: v for k, v in mutated.items() if k != "report_sha256"})
        result = audit_report(mutated, rebuild=True)
        cases.append({
            "mutant": name, "expected": "rejected",
            "observed": "rejected" if not result["evidence_valid"] else "accepted",
            "findings": [f["check"] for f in result["findings"]][:4],
            "ok": (not result["evidence_valid"]) and control["evidence_valid"],
        })
    return {"cases": cases, "ok": all(c["ok"] for c in cases)}


def run(report_path: Path, *, do_self_test: bool = True) -> Dict:
    report = _load_report(Path(report_path))
    result = audit_report(report)
    if do_self_test:
        result["mutation_self_test"] = self_test(report)
        result["evidence_valid"] = bool(
            result["evidence_valid"] and result["mutation_self_test"]["ok"])
    result["report"] = str(report_path)
    result["sim3_green_as_reported"] = report.get("sim3_green")
    return result
