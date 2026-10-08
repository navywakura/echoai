"""The v2 auditor: rebuild the three verdicts, do not read the green.

It regenerates the twelve worlds from the published seeds, re-hashes
every trace and every ULog, recomputes the hover statistics, the impulse
ratio, the band exit and the recovery from the raw pose samples,
reconstructs the condition permutation from the seed, checks the
denominator is 48 with 24 per condition, and verifies that one lock and
one v2 protocol cover every episode.

It also audits the thing v2 is most likely to be accused of: it checks
that the v1 artefacts are still on disk with their original hashes, and
that the v2 bands were derived by the frozen rules rather than picked.
"""

from __future__ import annotations

import copy
import math
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

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
from echoai.nexus0.flight1s.bench import WORLD_PROTOCOL, condition_order
from echoai.nexus0.flight1s.evaluate import COL, MASS_G
from echoai.nexus0.flight1s.v2 import (
    V1_CODE_SHA256,
    V1_PROTOCOL_SHA256,
    V1_REPORT_SHA256,
)
from echoai.nexus0.flight1s.v2 import protocol as protomod
from echoai.nexus0.flight1s.v2.runtime import ECHOAI, code_inventory


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

    a.check("protocol_version", report.get("protocol_version") == 2,
            str(report.get("protocol_version")))
    a.check("scope", report.get("scope") == "flight_software_in_the_loop", "")
    a.check("dataset_kind", report.get("dataset_kind") == "rehearsal", "")
    a.check("hardware_status", report.get("hardware_status") == "not_available", "")
    a.check("agent_in_gazebo", report.get("agent_in_gazebo") is False, "")
    a.check("cortex_calls", report.get("cortex_calls") == 0, "")
    a.check("wsp_writes", report.get("wsp_writes") == 0, "")

    # v2 must point back at the v1 red it repairs, and must not have moved it.
    sup = report.get("supersedes", {})
    a.check("supersedes_v1", sup.get("version") == 1
            and sup.get("protocol_sha256") == V1_PROTOCOL_SHA256
            and sup.get("report_sha256") == V1_REPORT_SHA256
            and sup.get("verdict") == "red", str(sup)[:160])
    v1_report = ECHOAI / "lab" / "echo3_flight1s_report.json"
    if v1_report.exists():
        v1_data = loads_strict(v1_report.read_bytes(), code="v1_report")
        a.check("v1_report_still_red", v1_data.get("flight1s_green") is False,
                str(v1_data.get("flight1s_green")))
        a.check("v1_report_hash_unchanged",
                v1_data.get("report_sha256") == V1_REPORT_SHA256,
                str(v1_data.get("report_sha256")))
        a.check("v1_report_still_48",
                len(v1_data.get("episodes", [])) == 48,
                str(len(v1_data.get("episodes", []))))
    else:
        a.check("v1_report_present", False, str(v1_report))
    v1_proto = ECHOAI / "docs" / "examples" / "flight1s" / "protocol.json"
    if v1_proto.exists():
        a.check("v1_protocol_unchanged",
                sha256_bytes(v1_proto.read_bytes()) == V1_PROTOCOL_SHA256,
                "v1 protocol bytes moved")
    else:
        a.check("v1_protocol_present", False, str(v1_proto))
    a.check("v1_code_unchanged",
            report.get("runtime_lock", {}).get("v1", {}).get("code_sha256")
            == V1_CODE_SHA256, "the v1 code inventory moved")

    # The v2 protocol bytes are the freeze; bands come from the file.
    proto_rel = report.get("protocol", {}).get("path", "")
    proto_path = ECHOAI / proto_rel if proto_rel else None
    proto = None
    if proto_path and proto_path.exists():
        proto = protomod.load(proto_path)
        a.check("protocol_sha256", proto.sha256 == report["protocol"]["sha256"],
                f"file {proto.sha256}")
        for key in ("stimulus", "challenge", "recovery", "hover_bands",
                    "tolerances"):
            a.check(f"protocol_{key}", proto[key] == report["protocol"][key],
                    "report does not match the frozen protocol")
        # The margin and the arithmetic must be the declared rules, not choices.
        expected = protomod.exit_margin_mm()
        a.check("margin_derived",
                proto["challenge"]["exit_margin_mm"] == expected["exit_margin_mm"]
                and proto["challenge"]["margin_derivation"]
                == expected["derivation"],
                f"expected {expected}")
        a.check("radius_not_below_v1",
                proto["recovery"]["radius_mm"] >= protomod.V1_RECOVERY_RADIUS_MM,
                str(proto["recovery"]["radius_mm"]))
        a.check("impulse_floor_not_lowered",
                proto["stimulus"]["min_impulse_ratio_ppk"]
                >= protomod.IMPULSE_FLOOR_PPK,
                str(proto["stimulus"]["min_impulse_ratio_ppk"]))
        a.check("impulse_arithmetic",
                proto["stimulus"]["commanded_impulse_mn_s"]
                == protomod.commanded_impulse_mn_s(
                    proto["disturbance"]["force_mn"],
                    proto["stages"]["disturb_ms"]), "F*dt does not check out")
    else:
        a.check("protocol_present", False, f"missing {proto_path}")

    entries, code_sha = code_inventory()
    a.check("code_sha256",
            code_sha == report.get("runtime_lock", {}).get("code_sha256"),
            f"recomputed {code_sha}")

    stated_lock = report.get("runtime_lock", {}).get("lock_sha256")
    ep_locks = {e.get("lock_sha256") for e in report.get("episodes", [])}
    ep_protos = {e.get("protocol_sha256") for e in report.get("episodes", [])}
    a.check("single_runtime_lock", ep_locks <= {stated_lock},
            f"episodes report {sorted(x for x in ep_locks if x != stated_lock)}")
    a.check("single_protocol",
            proto is None or ep_protos <= {proto.sha256},
            f"episodes report {sorted(x for x in ep_protos)}")

    episodes = report.get("episodes", [])
    a.check("episode_count", len(episodes) == 48, str(len(episodes)))
    by_condition: Dict[str, int] = {}
    by_package: Dict[str, int] = {}
    for e in episodes:
        by_condition[e["condition"]] = by_condition.get(e["condition"], 0) + 1
        by_package[e.get("package_id", "?")] = by_package.get(
            e.get("package_id", "?"), 0) + 1
    a.check("episodes_per_condition",
            by_condition.get("nominal") == 24
            and by_condition.get("perturbed") == 24, str(by_condition))
    a.check("episodes_per_world",
            len(by_package) == 12 and set(by_package.values()) == {4},
            str(sorted(by_package.values())))

    if proto is not None:
        order = condition_order(int(proto["order_seed"]), 24)
        slots: Dict[int, List[str]] = {}
        for e in episodes:
            slots.setdefault(e.get("order_slot"), []).append(e["condition"])
        mismatch = [s for s, conds in sorted(slots.items())
                    if conds != order[s * 2:s * 2 + 2]]
        a.check("condition_order_from_seed", not mismatch,
                f"slots {mismatch[:4]} do not follow the seed")

    packages = {}
    tmp: Optional[Path] = None
    if rebuild:
        try:
            tmp = Path(tempfile.mkdtemp(prefix="flight1s-v2-audit-"))
            regenerated = generate_suite(tmp, load_world_protocol(WORLD_PROTOCOL),
                                         REHEARSAL_SECRET, rehearsal_assignment())
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
            if e.get("ulog_sha256"):
                ulog = ulog_dir / f"{label}.ulg"
                if ulog.exists():
                    a.check(f"ulog_sha/{label}",
                            sha256_bytes(ulog.read_bytes()) == e["ulog_sha256"],
                            "PX4 log does not match its recorded hash")
                else:
                    a.check(f"ulog_file/{label}", False, f"missing {ulog}")
            if proto is None:
                continue
            trace = loads_strict(path.read_bytes(), code="trace")
            mine = _recompute(trace, proto)
            recomputed[label] = mine
            for key, tol in (("hover_horiz_rms_mm", 0.05),
                             ("disturb_excursion_mm", 0.05)):
                if key in mine and key in e:
                    a.check(f"recompute/{label}/{key}",
                            _close(mine[key], e[key], tol),
                            f"auditor {mine.get(key)} vs report {e.get(key)}")
            if e["condition"] != "perturbed":
                continue
            a.check(f"recompute/{label}/impulse",
                    _close(mine.get("impulse_ratio_ppk"),
                           (e.get("impulse") or {}).get("ratio_ppk"), 2),
                    f"auditor {mine.get('impulse_ratio_ppk')}")
            a.check(f"recompute/{label}/stimulus",
                    mine.get("stimulus_ok") == (e.get("stimulus") or {}).get("ok"),
                    f"auditor {mine.get('stimulus_ok')}")
            a.check(f"recompute/{label}/challenge",
                    mine.get("left_band") == (e.get("challenge") or {}).get("ok"),
                    f"auditor {mine.get('left_band')}")
            a.check(f"recompute/{label}/recovery",
                    mine.get("recovery_status")
                    == (e.get("recovery") or {}).get("status"),
                    f"auditor {mine.get('recovery_status')}")
            a.check(f"recompute/{label}/wrench_once",
                    mine.get("wrench_publications") == 1,
                    f"auditor saw {mine.get('wrench_publications')} publications")
            a.check(f"recompute/{label}/wrench_cleared",
                    mine.get("wrench_cleared") is True,
                    "no withdrawal recorded at the end of the window")
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
        "protocol_version": 2,
        "note": "evidence_valid means the evidence reconstructs, not that the "
                "bench passed; v1 is checked to be intact, not reinterpreted",
    }


def _recompute(trace: Dict, proto) -> Dict:
    """The auditor's own arithmetic for all three verdicts."""
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
    horiz = [math.hypot(s[COL["x"]] - rx, s[COL["y"]] - ry) for s in hover]
    out = {"hover_horiz_rms_mm": round(
        math.sqrt(sum(v * v for v in horiz) / len(horiz)) / 1000.0, 3)}

    db, de = plan["disturb"]
    rb, re = plan["recover"]
    after = [s for s in samples if db <= s[COL["t"]] < re]
    if after:
        out["disturb_excursion_mm"] = round(
            max(math.hypot(s[COL["x"]] - rx, s[COL["y"]] - ry)
                for s in after) / 1000.0, 3)

    applied = [int(e["sim_time_ns"]) for e in trace.get("events", [])
               if e.get("ev") == "wrench_applied"]
    cleared = [int(e["sim_time_ns"]) for e in trace.get("events", [])
               if e.get("ev") == "wrench_cleared"]
    out["wrench_publications"] = int(trace.get("wrench_published", 0))
    out["wrench_cleared"] = bool(
        [t for t in cleared if de <= t <= de + 200_000_000])
    applied_inside = len([t for t in applied if db <= t <= de]) == 1

    force = trace.get("force_n") or [0.0]
    expected = float(force[0]) * (de - db) / 1e9
    pre = [s for s in samples if db - 300_000_000 <= s[COL["t"]] < db]
    post = [s for s in samples if db <= s[COL["t"]] <= de + 300_000_000]
    ratio = None
    if len(pre) >= 3 and len(post) >= 3 and expected:
        def vx(x, y):
            dt = y[COL["t"]] - x[COL["t"]]
            return ((y[COL["x"]] - x[COL["x"]]) / 1000.0 / (dt / 1e9)
                    if dt > 0 else None)
        v0 = vx(pre[0], pre[-1])
        peaks = [v for v in (vx(post[i], post[i + 1])
                             for i in range(len(post) - 1)) if v is not None]
        if v0 is not None and peaks:
            delta_p = (max(peaks) - v0) / 1000.0 * (MASS_G / 1000.0)
            ratio = int(round(1000 * delta_p / expected))
    out["impulse_ratio_ppk"] = ratio

    spec = proto["stimulus"]
    out["stimulus_ok"] = bool(
        trace.get("ok") and out["wrench_publications"] == 1
        and applied_inside and out["wrench_cleared"] and ratio is not None
        and spec["min_impulse_ratio_ppk"] <= ratio <= spec["max_impulse_ratio_ppk"])

    threshold = (int(proto["challenge"]["recovery_radius_mm"])
                 + int(proto["challenge"]["exit_margin_mm"]))
    out["left_band"] = bool(trace.get("ok")
                            and out.get("disturb_excursion_mm", 0) > threshold)

    radius_um = int(proto["recovery"]["radius_mm"]) * 1000
    hold_ns = int(proto["recovery"]["hold_ms"]) * 1_000_000
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

def _mut_impulse(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    for e in out["episodes"]:
        if e["condition"] == "perturbed":
            e["impulse"]["ratio_ppk"] = 990
            e["stimulus"]["impulse_ratio_ppk"] = 990
            break
    return out


def _mut_relax_margin(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["protocol"]["challenge"] = dict(out["protocol"]["challenge"])
    out["protocol"]["challenge"]["exit_margin_mm"] = 1
    return out


def _mut_relax_floor(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["protocol"]["stimulus"] = dict(out["protocol"]["stimulus"])
    out["protocol"]["stimulus"]["min_impulse_ratio_ppk"] = 10
    return out


def _mut_drop_red(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["episodes"] = out["episodes"][:-1]
    return out


def _mut_two_locks(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["episodes"][5]["lock_sha256"] = "e" * 64
    return out


def _mut_mixed_protocol(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["episodes"][7]["protocol_sha256"] = V1_PROTOCOL_SHA256
    return out


def _mut_v1_touched(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["runtime_lock"]["v1"] = dict(out["runtime_lock"]["v1"])
    out["runtime_lock"]["v1"]["code_sha256"] = "d" * 64
    return out


def _mut_supersedes(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["supersedes"] = dict(out["supersedes"])
    out["supersedes"]["verdict"] = "green"
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


def _mut_green(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["flight1s_green"] = True
    out["group_status"] = dict(out["group_status"])
    out["group_status"]["stimulus"] = "fail"
    return out


def _mut_code_hash(report: Dict) -> Dict:
    out = copy.deepcopy(report)
    out["runtime_lock"]["code_sha256"] = "b" * 64
    return out


REPORT_MUTANTS = (
    ("impulse_altered_in_report", _mut_impulse),
    ("exit_margin_relaxed_in_report", _mut_relax_margin),
    ("impulse_floor_relaxed_in_report", _mut_relax_floor),
    ("omitted_red_episode", _mut_drop_red),
    ("two_locks_across_episodes", _mut_two_locks),
    ("v1_and_v2_protocols_mixed", _mut_mixed_protocol),
    ("v1_code_reported_as_touched", _mut_v1_touched),
    ("v1_red_reported_as_green", _mut_supersedes),
    ("rewritten_trace_hash", _mut_trace_hash),
    ("rewritten_ulog_hash", _mut_ulog_hash),
    ("green_without_groups", _mut_green),
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
