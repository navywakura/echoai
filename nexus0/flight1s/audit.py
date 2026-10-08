"""An auditor that does not read ``flight1s_green``.

It rebuilds instead: it regenerates the twelve rehearsal worlds from the
published seeds, re-hashes every episode trace and every ulog, recomputes
the hover statistics, the impulse ratio and the recovery time from the
raw pose samples, recomputes the condition permutation from the seed, and
checks the denominator is the 48 the protocol demands. Only then does it
compare with what the report claims.

``evidence_valid`` means the evidence reconstructs. A red bench with
reconstructible traces is what an honest failure looks like.

``--self-test`` mutates copies of the report — a dropped red episode, a
relaxed band, two locks, a rewritten trace hash — and requires each to be
rejected, starting from a control it accepted.
"""

from __future__ import annotations

import copy
import math
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    loads_strict,
    read_bounded,
    report_sha256,
    sha256_bytes,
)
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.flight1s import protocol as protomod
from echoai.nexus0.flight1s.bench import WORLD_PROTOCOL, condition_order
from echoai.nexus0.flight1s.evaluate import COL, MASS_G
from echoai.nexus0.flight1s.runtime import ECHOAI, code_inventory


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


def _close(a, b, tol: float = 0.05) -> bool:
    if a is None or b is None:
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= tol
    return a == b


def audit_report(report: Dict, *, rebuild: bool = True) -> Dict:
    a = Audit()
    recomputed: Dict[str, Dict] = {}

    stated = report.get("report_sha256")
    fresh = report_sha256({k: v for k, v in report.items()
                           if k != "report_sha256"})
    a.check("report_sha256", stated == fresh, f"recomputed {fresh}")

    a.check("scope", report.get("scope") == "flight_software_in_the_loop",
            str(report.get("scope")))
    a.check("dataset_kind", report.get("dataset_kind") == "rehearsal",
            str(report.get("dataset_kind")))
    a.check("hardware_status", report.get("hardware_status") == "not_available",
            str(report.get("hardware_status")))
    a.check("agent_in_gazebo", report.get("agent_in_gazebo") is False,
            str(report.get("agent_in_gazebo")))
    a.check("cortex_calls", report.get("cortex_calls") == 0,
            str(report.get("cortex_calls")))

    # The protocol bytes are the freeze. Bands come from the file, never
    # from the report that is being audited.
    proto_rel = report.get("protocol", {}).get("path", "")
    proto_path = ECHOAI / proto_rel if proto_rel else None
    proto = None
    if proto_path and proto_path.exists():
        proto = protomod.load(proto_path)
        a.check("protocol_sha256", proto.sha256 == report["protocol"]["sha256"],
                f"file {proto.sha256}")
        for key in ("bands", "tolerances"):
            a.check(f"protocol_{key}", proto[key] == report["protocol"][key],
                    "report does not match the frozen protocol")
        a.check("protocol_force",
                proto["disturbance"]["force_mn"]
                == report["protocol"]["force_mn"], "force differs")
        a.check("protocol_episodes", int(proto["episodes"]) == 48,
                str(proto["episodes"]))
    else:
        a.check("protocol_present", False, f"missing {proto_path}")

    entries, code_sha = code_inventory()
    a.check("code_sha256",
            code_sha == report.get("runtime_lock", {}).get("code_sha256"),
            f"recomputed {code_sha}")

    # One runtime, one PX4 commit, for every episode.
    stated_lock = report.get("runtime_lock", {}).get("lock_sha256")
    ep_locks = {e.get("lock_sha256") for e in report.get("episodes", [])}
    a.check("single_runtime_lock", ep_locks <= {stated_lock},
            f"episodes report {sorted(x for x in ep_locks if x != stated_lock)}")
    lock_rel = report.get("runtime_lock", {}).get("path", "")
    lock_path = ECHOAI / lock_rel if lock_rel else None
    if lock_path and lock_path.exists():
        lock = loads_strict(read_bounded(lock_path, code="lock"), code="lock")
        a.check("lock_matches_report",
                lock.get("lock_sha256") == stated_lock,
                f"lock file {lock.get('lock_sha256')}")
        px4 = lock.get("px4", {})
        container = lock.get("container", {})
        a.check("px4_commit_single",
                px4.get("commit") == container.get("px4_commit"),
                f"pinned {px4.get('commit')} built {container.get('px4_commit')}")
    else:
        a.check("lock_present", False, f"missing {lock_path}")

    # The denominator: 48 episodes, 24 per condition, 4 per world.
    episodes = report.get("episodes", [])
    a.check("episode_count", len(episodes) == 48, str(len(episodes)))
    by_condition: Dict[str, int] = {}
    by_package: Dict[str, int] = {}
    for e in episodes:
        by_condition[e["condition"]] = by_condition.get(e["condition"], 0) + 1
        by_package[e.get("package_id", "?")] = by_package.get(
            e.get("package_id", "?"), 0) + 1
    a.check("episodes_per_condition",
            by_condition.get("nominal") == 24 and by_condition.get("perturbed") == 24,
            str(by_condition))
    a.check("episodes_per_world",
            len(by_package) == 12 and set(by_package.values()) == {4},
            str(sorted(by_package.values())))

    # The condition order is derived from the seed, not chosen per world.
    if proto is not None:
        order = condition_order(int(proto["order_seed"]), 24)
        seen_order = [(e.get("order_slot"), e["condition"]) for e in episodes]
        slots: Dict[int, List[str]] = {}
        for slot, cond in seen_order:
            slots.setdefault(slot, []).append(cond)
        mismatch = [s for s, conds in sorted(slots.items())
                    if conds != order[s * 2:s * 2 + 2]]
        a.check("condition_order_from_seed", not mismatch,
                f"slots {mismatch[:4]} do not follow the seed")

    packages = {}
    tmp: Optional[Path] = None
    if rebuild:
        try:
            world_proto = load_world_protocol(WORLD_PROTOCOL)
            tmp = Path(tempfile.mkdtemp(prefix="flight1s-audit-"))
            regenerated = generate_suite(tmp, world_proto, REHEARSAL_SECRET,
                                         rehearsal_assignment())
            packages = {g.package_id: g for g in regenerated}
        except Sim3Error as exc:
            a.check("suite_rebuild", False, f"{exc.code}: {exc.detail}")

    try:
        for row in report.get("assignment", []):
            gen = packages.get(row["package_id"])
            if gen is None:
                if packages:
                    a.check(f"assignment/{row['package_id']}", False,
                            "not reproduced from the published seeds")
                continue
            a.check(f"package_sha/{row['package_id']}",
                    gen.package.package_sha256 == row["package_sha256"],
                    f"recomputed {gen.package.package_sha256}")

        traces = {t["label"]: t for t in report.get("traces", {}).get("files", [])}
        for entry in traces.values():
            path = ECHOAI / entry["path"]
            if not path.exists():
                a.check(f"trace_file/{entry['label']}", False, f"missing {path}")
                continue
            digest = sha256_bytes(path.read_bytes())
            a.check(f"trace_sha/{entry['label']}", digest == entry["sha256"],
                    f"recomputed {digest}")

        ulog_dir = ECHOAI / report.get("traces", {}).get("ulogs", "")
        for e in episodes:
            label = e["label"]
            entry = traces.get(label)
            if entry is None:
                a.check(f"trace/{label}", False, "no trace recorded")
                continue
            a.check(f"trace_hash_in_episode/{label}",
                    e.get("trace_sha256") == entry["sha256"],
                    "episode and trace index disagree")
            path = ECHOAI / entry["path"]
            if not path.exists():
                continue
            trace = loads_strict(path.read_bytes(), code="trace")
            if e.get("ulog_sha256"):
                ulog = ulog_dir / f"{label}.ulg"
                if ulog.exists():
                    a.check(f"ulog_sha/{label}",
                            sha256_bytes(ulog.read_bytes()) == e["ulog_sha256"],
                            "PX4 log does not match its recorded hash")
                else:
                    a.check(f"ulog_file/{label}", False, f"missing {ulog}")
            if proto is not None:
                mine = _recompute(trace, proto)
                recomputed[label] = mine
                for key, tol in (("hover_horiz_rms_mm", 0.05),
                                 ("hover_alt_offset_mm", 0.05),
                                 ("disturb_excursion_mm", 0.05)):
                    if key in mine and key in e:
                        a.check(f"recompute/{label}/{key}",
                                _close(mine[key], e[key], tol),
                                f"auditor {mine.get(key)} vs report {e.get(key)}")
                if e["condition"] == "perturbed":
                    a.check(f"recompute/{label}/impulse",
                            _close(mine.get("impulse_ratio_ppk"),
                                   (e.get("impulse") or {}).get("ratio_ppk"), 2),
                            f"auditor {mine.get('impulse_ratio_ppk')}")
                    a.check(f"recompute/{label}/recovery",
                            mine.get("recovery_status")
                            == (e.get("recovery") or {}).get("status"),
                            f"auditor {mine.get('recovery_status')}")
    finally:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)

    for name, group in report.get("groups", {}).items():
        flags = [c["ok"] for c in group.get("cases", [])
                 if isinstance(c, dict) and "ok" in c]
        if flags and group.get("status") == "pass":
            a.check(f"group_consistency/{name}", all(flags),
                    f"{flags.count(False)} failing cases inside a pass")
        if group.get("status") not in ("pass", "fail", "not_run"):
            a.check(f"group_status/{name}", False, str(group.get("status")))

    stated_green = report.get("flight1s_green")
    derived = bool(report.get("group_status")) and all(
        v == "pass" for v in report.get("group_status", {}).values())
    a.check("flight1s_green_consistent", stated_green == derived,
            f"stated {stated_green}, derived {derived}")

    return {
        "evidence_valid": a.ok,
        "checks": a.checks,
        "findings": a.findings,
        "recomputed_episodes": len(recomputed),
        "flight1s_green_as_reported": stated_green,
        "note": "evidence_valid means the evidence reconstructs, not that the "
                "bench passed",
    }


def _recompute(trace: Dict, proto) -> Dict:
    """The auditor's own arithmetic over the raw pose samples."""
    samples = trace.get("samples", [])
    marks = trace.get("stage_marks", {})
    plan = {n: (a, b) for n, a, b in marks.get("plan", [])}
    if not samples or "hover" not in plan:
        return {}
    hb, he = plan["hover"]
    hover = [s for s in samples if hb <= s[COL["t"]] < he]
    if not hover:
        return {}
    rx = int(round(sum(s[COL["x"]] for s in hover) / len(hover)))
    ry = int(round(sum(s[COL["y"]] for s in hover) / len(hover)))
    rz = int(round(sum(s[COL["z"]] for s in hover) / len(hover)))
    horiz = [math.hypot(s[COL["x"]] - rx, s[COL["y"]] - ry) for s in hover]
    commanded = int(marks.get("rest_z_um", 0)) + proto["stages"]["takeoff_alt_mm"] * 1000
    out = {
        "hover_horiz_rms_mm": round(
            math.sqrt(sum(v * v for v in horiz) / len(horiz)) / 1000.0, 3),
        "hover_alt_offset_mm": round((rz - commanded) / 1000.0, 3),
    }
    db, de = plan["disturb"]
    rb, re = plan["recover"]
    after = [s for s in samples if db <= s[COL["t"]] < re]
    if after:
        out["disturb_excursion_mm"] = round(
            max(math.hypot(s[COL["x"]] - rx, s[COL["y"]] - ry)
                for s in after) / 1000.0, 3)
    force = trace.get("force_n") or [0.0]
    expected = float(force[0]) * (de - db) / 1e9
    pre = [s for s in samples if db - 300_000_000 <= s[COL["t"]] < db]
    post = [s for s in samples if db <= s[COL["t"]] <= de + 300_000_000]
    if len(pre) >= 3 and len(post) >= 3 and expected:
        def vx(a, b):
            dt = b[COL["t"]] - a[COL["t"]]
            return ((b[COL["x"]] - a[COL["x"]]) / 1000.0 / (dt / 1e9)
                    if dt > 0 else None)
        v0 = vx(pre[0], pre[-1])
        peaks = [v for v in (vx(post[i], post[i + 1])
                             for i in range(len(post) - 1)) if v is not None]
        if v0 is not None and peaks:
            delta_p = (max(peaks) - v0) / 1000.0 * (MASS_G / 1000.0)
            out["impulse_ratio_ppk"] = int(round(1000 * delta_p / expected))
    bands = proto["bands"]
    radius_um = int(bands["recovery_radius_mm"]) * 1000
    hold_ns = int(bands["recovery_hold_ms"]) * 1_000_000
    tail = [s for s in samples if de <= s[COL["t"]] <= re]
    out["recovery_status"] = "not_recovered"
    for i, sample in enumerate(tail):
        if math.hypot(sample[COL["x"]] - rx, sample[COL["y"]] - ry) > radius_um:
            continue
        if all(math.hypot(l[COL["x"]] - rx, l[COL["y"]] - ry) <= radius_um
               for l in tail[i:]
               if l[COL["t"]] - sample[COL["t"]] <= hold_ns) and (
                   tail[-1][COL["t"]] - sample[COL["t"]] >= hold_ns):
            out["recovery_status"] = "recovered"
            break
    return out


# --- evidence mutation -----------------------------------------------------

def _mut_drop_red(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["episodes"] = out["episodes"][:-1]
    return out


def _mut_relax_band(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["protocol"]["bands"] = dict(out["protocol"]["bands"])
    out["protocol"]["bands"]["recovery_radius_mm"] *= 4
    return out


def _mut_two_locks(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["episodes"][5]["lock_sha256"] = "e" * 64
    return out


def _mut_trace_hash(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["traces"]["files"][0]["sha256"] = "0" * 64
    return out


def _mut_ulog_hash(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    for e in out["episodes"]:
        if e.get("ulog_sha256"):
            e["ulog_sha256"] = "1" * 64
            break
    return out


def _mut_altered_measurement(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["episodes"][0]["hover_horiz_rms_mm"] = 1.0
    return out


def _mut_green(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["flight1s_green"] = True
    out["group_status"] = dict(out["group_status"])
    out["group_status"]["disturbance"] = "fail"
    return out


def _mut_order(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    for e in out["episodes"]:
        e["condition"] = "nominal"
    return out


def _mut_code_hash(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["runtime_lock"]["code_sha256"] = "b" * 64
    return out


REPORT_MUTANTS = (
    ("omitted_red_episode", _mut_drop_red),
    ("relaxed_band_in_report", _mut_relax_band),
    ("two_locks_across_episodes", _mut_two_locks),
    ("rewritten_trace_hash", _mut_trace_hash),
    ("rewritten_ulog_hash", _mut_ulog_hash),
    ("altered_measurement", _mut_altered_measurement),
    ("green_without_groups", _mut_green),
    ("condition_order_rewritten", _mut_order),
    ("wrong_code_hash", _mut_code_hash),
)


def self_test(report: Dict) -> Dict:
    control = audit_report(report)
    cases = [{"mutant": "positive_control", "expected": "evidence_valid",
              "observed": control["evidence_valid"],
              "findings": [f["check"] for f in control["findings"]][:4],
              "ok": control["evidence_valid"]}]
    for name, mutate in REPORT_MUTANTS:
        mutated = mutate(report)
        mutated["report_sha256"] = report_sha256(
            {k: v for k, v in mutated.items() if k != "report_sha256"})
        result = audit_report(mutated)
        cases.append({
            "mutant": name, "expected": "rejected",
            "observed": "rejected" if not result["evidence_valid"] else "accepted",
            "findings": [f["check"] for f in result["findings"]][:4],
            "ok": (not result["evidence_valid"]) and control["evidence_valid"],
        })
    return {"cases": cases, "ok": all(c["ok"] for c in cases)}


def run(report_path: Path, *, do_self_test: bool = True) -> Dict:
    report = loads_strict(Path(report_path).read_bytes(), code="report")
    result = audit_report(report)
    if do_self_test:
        result["mutation_self_test"] = self_test(report)
        result["evidence_valid"] = bool(
            result["evidence_valid"] and result["mutation_self_test"]["ok"])
    result["report"] = str(report_path)
    result["flight1s_green_as_reported"] = report.get("flight1s_green")
    return result
