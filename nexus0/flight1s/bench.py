"""The preregistered FLIGHT-1S bench: 48 episodes and the groups around them.

Twelve rehearsal worlds, two fresh repeats each, two paired conditions.
The condition order is a permutation derived from ``order_seed``, which
lives here and nowhere else — not in the container, not in the driver,
not in PX4 — so a thermal or temporal drift cannot line up with the
manipulated variable.

A group is ``pass``, ``fail`` or ``not_run``. A missing dependency is
never ``pass``. ``flight1s_green`` needs every mandatory group in pass,
and the hard criteria are counted per episode: a median cannot cover a
failed one.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    dump_report,
    report_sha256,
    sha256_bytes,
)
from echoai.nexus0.sim3.generate import SplitMix64, generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.flight1s import evaluate, mutants, protocol as protomod, worldbuild
from echoai.nexus0.flight1s.runtime import (
    DEFAULT_LOCK,
    ECHOAI,
    Runtime,
    code_inventory,
    load_lock,
    preflight,
)
from echoai.nexus0.flight1s.session import run_episode
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET

LAB = ECHOAI / "lab" / "flight1s"
DEFAULT_REPORT = ECHOAI / "lab" / "echo3_flight1s_report.json"
WORLD_PROTOCOL = ECHOAI / "docs" / "examples" / "sim3" / "protocol.json"
FAMILY = ECHOAI / "docs" / "examples" / "sim3-families" / "rehearsal-v1.json"

MANDATORY_GROUPS = (
    "envelope", "episodes", "disturbance", "recovery", "repetition",
    "hygiene", "controls", "mutants", "regression",
)

LIMITATIONS = [
    "Software in the loop only: this measures a simulated body under this PX4 "
    "configuration, not aerodynamic realism, real wind, autonomy, universal "
    "safety or sim-to-real.",
    "echoAI is disconnected: agent_in_gazebo=false, cortex_calls=0, and no "
    "simulated sensor is published as evidence or translated into WSP.",
    "PX4 owns stabilisation and mixing. The driver only sets the reference; "
    "the intent interface and the failsafes belong to PX4-1 and SAFE-1.",
    "Velocity, and therefore the impulse check, is a finite difference of the "
    "backend's pose stream, not an independent velocity sensor.",
    "The disturbance is a single constant link wrench. It is not wind and "
    "carries no atmospheric claim.",
    "The worlds are the SIM-3 rehearsal packages, revalidated for the X500 "
    "envelope. They are public rehearsal data and consume no reserved exam.",
    "Timing and RTF describe one host. They are not an energy or endurance "
    "figure and promise no P99 elsewhere.",
    "hardware_status=not_available: there is no aircraft and no Akida.",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    return str(p.relative_to(ECHOAI)) if p.is_relative_to(ECHOAI) else str(p)


def condition_order(order_seed: int, n_slots: int) -> List[str]:
    """A fixed permutation of paired conditions. Derived, never adaptive.

    The same SplitMix64 the world generator uses, so an auditor can
    reproduce the order without running this code. It depends on the seed
    and on nothing about the world.
    """
    rng = SplitMix64(order_seed)
    order: List[str] = []
    for _ in range(n_slots):
        pair = ["nominal", "perturbed"]
        if rng.below(2):
            pair.reverse()
        order.extend(pair)
    return order


class Bench:
    def __init__(self, *, report_path: Path, protocol_path: Optional[Path],
                 lock_path: Optional[Path] = None, verbose: bool = True) -> None:
        self.report_path = Path(report_path).resolve()
        self.protocol_path = protocol_path
        self.lock_path = lock_path
        self.verbose = verbose
        self.groups: Dict[str, Dict] = {}
        self.episodes: List[Dict] = []
        self.traces: List[Dict] = []
        self.episode_dir = LAB / "episodes"
        self.ulog_dir = LAB / "ulogs"
        self.suite_root = LAB / "suite"
        self.lock_sha256 = ""
        self.t0 = time.monotonic()

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[flight1s {time.monotonic() - self.t0:7.1f}s] {msg}", flush=True)

    def group(self, name: str, status: str, detail: str = "",
              cases: Optional[Sequence[Dict]] = None, **extra) -> None:
        payload = {"status": status, "detail": detail, "cases": list(cases or [])}
        payload.update(extra)
        self.groups[name] = payload
        self.log(f"group {name}: {status}" + (f" ({detail})" if detail else ""))

    # -- run --------------------------------------------------------------

    def execute(self) -> Dict:
        proto = protomod.load(self.protocol_path)
        runtime = self._lock()
        self.lock_sha256 = str(runtime.lock.get("lock_sha256", ""))
        self.log(f"runtime available={runtime.available} {runtime.reason}")

        world_proto = load_world_protocol(WORLD_PROTOCOL)
        if world_proto.sha256 != proto["worlds"]["protocol_sha256"]:
            raise Sim3Error("world_protocol_mismatch", world_proto.sha256)
        if sha256_bytes(FAMILY.read_bytes()) != proto["worlds"]["family_sha256"]:
            raise Sim3Error("world_family_mismatch",
                            sha256_bytes(FAMILY.read_bytes()))

        if self.suite_root.exists():
            shutil.rmtree(self.suite_root)
        packages = generate_suite(self.suite_root, world_proto, REHEARSAL_SECRET,
                                  rehearsal_assignment())
        by_split = {"A": [], "B": [], "C": []}
        for gen in packages:
            by_split[gen.split].append(gen)

        if not self._group_envelope(packages, proto):
            for name in MANDATORY_GROUPS:
                self.groups.setdefault(name, {
                    "status": "not_run", "detail": "envelope group failed",
                    "cases": []})
            self._group_regression()
            return self._finish(proto, runtime, packages)

        if runtime.available:
            self._fly(runtime, packages, proto)
            self._group_controls(runtime, packages, proto)
            self._group_mutants(runtime, packages, proto)
        else:
            for name in ("episodes", "disturbance", "recovery", "repetition",
                         "hygiene", "controls", "mutants"):
                self.group(name, "not_run", runtime.reason or "backend unavailable")
        self._group_regression()
        return self._finish(proto, runtime, packages)

    def _lock(self) -> Runtime:
        existing = load_lock(self.lock_path)
        if existing.lock:
            _, code_sha = code_inventory()
            frozen = existing.lock.get("code", {}).get("code_sha256")
            if code_sha != frozen:
                raise Sim3Error(
                    "lock_stale",
                    f"code is {code_sha}, lock pins {frozen}; re-run "
                    f"`python3 -m echoai.nexus0.flight1s preflight`")
            self.log("using frozen runtime-lock.json")
            return existing
        self.log("no lock: running preflight and freezing it")
        return preflight(lock_path=self.lock_path, write=True)

    # -- groups -----------------------------------------------------------

    def _group_envelope(self, packages: Sequence, proto) -> bool:
        body = proto["body"]
        cases = []
        ok = True
        for gen in packages:
            env = worldbuild.check_envelope(gen.package, gen.package_id, body)
            cases.append({**env.as_dict(), "split": gen.split})
            ok &= env.ok
        self.group("envelope", "pass" if ok else "fail",
                   f"{len(cases)} worlds revalidated for the X500 envelope", cases)
        return ok

    def _fly(self, runtime: Runtime, packages: Sequence, proto) -> None:
        order = condition_order(int(proto["order_seed"]), len(packages) * 2)
        slot = 0
        results: Dict[Tuple[str, int, str], Dict] = {}
        ep_cases: List[Dict] = []
        for gen in packages:
            for repeat in (1, 2):
                for condition in order[slot * 2:slot * 2 + 2]:
                    label = f"{condition}-{gen.package_id}-r{repeat}"
                    self.log(f"episode {slot * 2}: {label}")
                    ep = run_episode(runtime, gen.package, proto.data,
                                     condition=condition, label=label,
                                     ulog_dir=self.ulog_dir)
                    metrics = evaluate.episode_metrics(ep, proto.data,
                                                       package=gen.package)
                    metrics["package_id"] = gen.package_id
                    metrics["split"] = gen.split
                    metrics["repeat"] = repeat
                    metrics["order_slot"] = slot
                    metrics["effective_sha256"] = ep.effective_sha256
                    metrics["lock_sha256"] = self.lock_sha256
                    metrics["runtime"] = ep.metrics
                    trace = self._save_trace(label, ep)
                    metrics["trace_sha256"] = trace["sha256"]
                    results[(gen.package_id, repeat, condition)] = metrics
                    self.episodes.append(metrics)
                    ep_cases.append(_episode_case(metrics))
                slot += 1

        n = len(self.episodes)
        completed = [c for c in ep_cases if c["completed"]]
        self.group("episodes",
                   "pass" if len(completed) == n == int(proto["episodes"]) else "fail",
                   f"{len(completed)}/{n} completed, {proto['episodes']} required",
                   ep_cases)

        self._group_disturbance(proto)
        self._group_recovery(proto)
        self._group_repetition(results, proto)
        self._group_hygiene(proto)

    def _save_trace(self, label: str, ep) -> Dict:
        self.episode_dir.mkdir(parents=True, exist_ok=True)
        path = self.episode_dir / f"{label}.json"
        raw = dump_report(path, ep.trace())
        entry = {"label": label, "path": _rel(path), "sha256": sha256_bytes(raw),
                 "bytes": len(raw), "ulog_sha256": ep.ulog_sha256}
        self.traces.append(entry)
        return entry

    def _group_disturbance(self, proto) -> None:
        bands = proto["bands"]
        cases = []
        ok = True
        for m in self.episodes:
            if m["condition"] != "perturbed":
                continue
            imp = m.get("impulse", {})
            excursion = m.get("disturb_excursion_mm")
            case = {
                "label": m["label"],
                "wrench_published": m.get("wrench_published"),
                "force_n": m.get("force_n"),
                "impulse_ratio_ppk": imp.get("ratio_ppk"),
                "impulse_measured_n_s": imp.get("measured_n_s"),
                "impulse_expected_n_s": imp.get("expected_n_s"),
                "excursion_mm": excursion,
                "min_excursion_mm": bands["min_disturb_excursion_mm"],
            }
            case["ok"] = bool(
                m["ok"] and case["wrench_published"] == 1
                and imp.get("status") == "measured"
                and (imp.get("ratio_ppk") or 0) >= 500
                and excursion is not None
                and excursion >= bands["min_disturb_excursion_mm"])
            cases.append(case)
            ok &= case["ok"]
        self.group("disturbance", "pass" if ok and cases else "fail",
                   f"{len(cases)} perturbed episodes with observed force", cases)

    def _group_recovery(self, proto) -> None:
        cases = []
        ok = True
        for m in self.episodes:
            if m["condition"] != "perturbed":
                continue
            rec = m.get("recovery", {})
            case = {"label": m["label"], **rec}
            case["ok"] = rec.get("status") == "recovered"
            cases.append(case)
            ok &= case["ok"]
        self.group("recovery", "pass" if ok and cases else "fail",
                   f"{len(cases)} perturbed episodes back inside the band", cases)

    def _group_repetition(self, results: Dict, proto) -> None:
        tol = proto["tolerances"]
        cases = []
        ok = True
        seen = {(pid, cond) for (pid, _, cond) in results}
        for pid, cond in sorted(seen):
            a = results.get((pid, 1, cond))
            b = results.get((pid, 2, cond))
            if a is None or b is None:
                cases.append({"package_id": pid, "condition": cond, "ok": False,
                              "why": "missing repeat"})
                ok = False
                continue
            d_rms = abs(a["hover_horiz_rms_mm"] - b["hover_horiz_rms_mm"])
            case = {"package_id": pid, "condition": cond,
                    "hover_rms_delta_mm": round(d_rms, 3),
                    "tolerance_mm": tol["paired_hover_rms_mm"],
                    "same_effective_sha": a["effective_sha256"] == b["effective_sha256"]}
            if cond == "perturbed":
                ra = a.get("recovery", {}).get("recovery_ms")
                rb = b.get("recovery", {}).get("recovery_ms")
                case["recovery_delta_ms"] = (abs(ra - rb) if ra is not None
                                             and rb is not None else None)
                case["recovery_tolerance_ms"] = tol["paired_recovery_ms"]
            case["ok"] = bool(
                case["same_effective_sha"] and d_rms <= tol["paired_hover_rms_mm"]
                and (cond != "perturbed" or (case.get("recovery_delta_ms") is not None
                     and case["recovery_delta_ms"] <= tol["paired_recovery_ms"])))
            cases.append(case)
            ok &= case["ok"]
        self.group("repetition", "pass" if ok and cases else "fail",
                   f"{len(cases)} paired repeats", cases)

    def _group_hygiene(self, proto) -> None:
        """Clocks, contacts, finite numbers, one lock, no branch by room."""
        bands = proto["bands"]
        cases = []
        ok = True
        locks = set()
        for m in self.episodes:
            timing = m.get("timing", {})
            att = max(m.get("hover_attitude_max_mdeg", 0),
                      m.get("disturb_attitude_max_mdeg", 0))
            landed = timing.get("landed_z_um")
            rest = m.get("rest_z_um")
            case = {
                "label": m["label"],
                "clock_regressions": timing.get("clock_regressions"),
                "effective_sample_hz": timing.get("effective_sample_hz"),
                "sample_gap_ms_p99": timing.get("sample_gap_ms_p99"),
                "attitude_max_mdeg": att,
                "attitude_ceiling_mdeg": bands["attitude_max_mdeg"],
                "landed_within_10mm_of_rest": (
                    landed is not None and rest is not None
                    and abs(landed - rest) <= 10_000),
                "finite": _all_finite(m),
            }
            sig = m.get("px4_signature", {})
            col = m.get("collisions", {})
            case["px4_signature_ok"] = bool(sig.get("ok"))
            case["unauthorised_contacts"] = col.get("unauthorised")
            case["ok"] = bool(
                m["ok"] and case["clock_regressions"] == 0
                and att <= bands["attitude_max_mdeg"]
                and case["landed_within_10mm_of_rest"] and case["finite"]
                and case["px4_signature_ok"]
                and col.get("unauthorised") == 0)
            cases.append(case)
            ok &= case["ok"]
            locks.add(m.get("lock_sha256"))
        single_lock = len(locks) == 1
        if not single_lock:
            ok = False
        self.group("hygiene", "pass" if ok and cases else "fail",
                   f"{len(cases)} episodes; single lock={single_lock}", cases,
                   locks=sorted(x for x in locks if x))

    def _group_controls(self, runtime: Runtime, packages: Sequence, proto) -> None:
        cases, ok = mutants.controls(runtime, packages, proto, log=self.log)
        self.group("controls", "pass" if ok else "fail",
                   f"{len(cases)} controls", cases)

    def _group_mutants(self, runtime: Runtime, packages: Sequence, proto) -> None:
        cases, ok = mutants.run_all(runtime, packages, proto, self.episodes,
                                    log=self.log)
        status = "pass" if ok else "fail"
        if not runtime.available:
            status = "not_run"
        self.group("mutants", status, f"{len(cases)} cases", cases)

    def _group_regression(self) -> None:
        env = dict(os.environ, PYTHONPATH=str(ECHOAI.parent))
        cases = []
        ok = True
        for name, cmd in (
            ("nexus0", [sys.executable, "-m", "echoai.tests.test_nexus0"]),
            ("sim3", [sys.executable, str(ECHOAI / "tests" / "test_sim3.py")]),
        ):
            self.log(f"regression: {name}")
            try:
                proc = subprocess.run(cmd, cwd=str(ECHOAI.parent), env=env,
                                      capture_output=True, timeout=2400)
            except (OSError, subprocess.TimeoutExpired) as exc:
                cases.append({"bank": name, "status": "not_run", "why": str(exc),
                              "ok": False})
                ok = False
                continue
            tail = (proc.stdout + proc.stderr).decode(
                errors="replace").strip().splitlines()[-6:]
            cases.append({"bank": name, "returncode": proc.returncode,
                          "tail": tail, "ok": proc.returncode == 0})
            ok &= proc.returncode == 0
        self.group("regression", "pass" if ok else "fail",
                   "nexus0 and sim3 banks", cases)

    # -- report -----------------------------------------------------------

    def _finish(self, proto, runtime: Runtime, packages: Sequence) -> Dict:
        mandatory = {k: self.groups.get(k, {"status": "not_run"})["status"]
                     for k in MANDATORY_GROUPS}
        green = all(v == "pass" for v in mandatory.values())
        report = {
            "schema_version": 1,
            "scope": "flight_software_in_the_loop",
            "dataset_kind": "rehearsal",
            "slice": "FLIGHT-1S",
            "generated_at_utc": _utc(),
            "flight1s_green": green,
            "hardware_status": "not_available",
            "agent_in_gazebo": False,
            "cortex_calls": 0,
            "wsp_writes": 0,
            "group_status": mandatory,
            "groups": self.groups,
            "episodes": self.episodes,
            "assignment": [
                {"package_id": g.package_id, "split": g.split, "index": g.index,
                 "seed": g.seed, "package_sha256": g.package.package_sha256}
                for g in packages
            ],
            "protocol": {
                "path": _rel(Path(proto.path)) if proto.path else "",
                "sha256": proto.sha256,
                "order_seed": proto["order_seed"],
                "force_mn": proto["disturbance"]["force_mn"],
                "bands": proto["bands"],
                "tolerances": proto["tolerances"],
                "calibration": _rel(LAB / "sweep.json"),
            },
            "runtime_lock": {
                "path": _rel(Path(self.lock_path or DEFAULT_LOCK)),
                "available": runtime.available,
                "reason": runtime.reason,
                "lock_sha256": runtime.lock.get("lock_sha256"),
                "code_sha256": runtime.lock.get("code", {}).get("code_sha256"),
                "px4": runtime.lock.get("px4", {}),
                "container": runtime.lock.get("container", {}),
            },
            "world_systems": list(worldbuild.WORLD_SYSTEMS
                                  + worldbuild.FLIGHT_SYSTEMS),
            "host": {"platform": platform.platform(),
                     "python": platform.python_version()},
            "commands": [
                "PYTHONPATH=.. python3 -m echoai.nexus0.flight1s preflight "
                "--output lab/flight1s/runtime-lock.json",
                "PYTHONPATH=.. python3 -m echoai.nexus0.flight1s bench --rehearsal "
                f"--output {_rel(self.report_path)}",
                "PYTHONPATH=.. python3 -m echoai.nexus0.flight1s audit "
                f"{_rel(self.report_path)}",
            ],
            "traces": {"dir": _rel(self.episode_dir), "ulogs": _rel(self.ulog_dir),
                       "files": self.traces},
            "metrics": self._metrics(),
            "limitations": LIMITATIONS,
            "wall_clock_s": round(time.monotonic() - self.t0, 1),
        }
        report["report_sha256"] = report_sha256(
            {k: v for k, v in report.items() if k != "report_sha256"})
        dump_report(self.report_path, report)
        return report

    def _metrics(self) -> Dict:
        measured = [m for m in self.episodes if m.get("status") == "measured"]
        if not measured:
            return {"n_episodes": 0}

        def stat(key, cond=None, path=None):
            vals = []
            for m in measured:
                if cond and m["condition"] != cond:
                    continue
                v = m
                for part in (path or [key]):
                    v = (v or {}).get(part) if isinstance(v, dict) else None
                if isinstance(v, (int, float)):
                    vals.append(v)
            vals.sort()
            if not vals:
                return None
            return {"n": len(vals), "min": vals[0], "p50": vals[len(vals) // 2],
                    "max": vals[-1]}

        return {
            "n_episodes": len(measured),
            "hover_horiz_rms_mm": stat("hover_horiz_rms_mm"),
            "hover_horiz_max_mm": stat("hover_horiz_max_mm"),
            "hover_alt_offset_mm": stat("hover_alt_offset_mm"),
            "disturb_excursion_mm": stat("disturb_excursion_mm", cond="perturbed"),
            "impulse_ratio_ppk": stat("x", cond="perturbed",
                                      path=["impulse", "ratio_ppk"]),
            "recovery_ms": stat("x", cond="perturbed",
                                path=["recovery", "recovery_ms"]),
            "effective_sample_hz": stat("x", path=["timing", "effective_sample_hz"]),
            "sample_gap_ms_p99": stat("x", path=["timing", "sample_gap_ms_p99"]),
            "episode_wall_s": stat("x", path=["runtime", "wall_s"]),
            "rtf": stat("x", path=["runtime", "rtf"]),
            "note": "descriptive on one host; not an energy or endurance claim",
        }


def _episode_case(m: Dict) -> Dict:
    timing = m.get("timing", {})
    return {
        "label": m["label"], "package_id": m.get("package_id"),
        "split": m.get("split"), "repeat": m.get("repeat"),
        "condition": m["condition"], "order_slot": m.get("order_slot"),
        "completed": bool(m["ok"] and m.get("status") == "measured"),
        "cause": m.get("cause"),
        "hover_horiz_rms_mm": m.get("hover_horiz_rms_mm"),
        "hover_alt_offset_mm": m.get("hover_alt_offset_mm"),
        "armed_to_disarmed_ms": timing.get("armed_to_disarmed_ms"),
        "trace_sha256": m.get("trace_sha256"),
        "ulog_sha256": m.get("ulog_sha256"),
    }


def _all_finite(value) -> bool:
    if isinstance(value, float):
        return value == value and value not in (float("inf"), float("-inf"))
    if isinstance(value, dict):
        return all(_all_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_all_finite(v) for v in value)
    return True


def run(report_path: Optional[Path] = None, protocol_path: Optional[Path] = None,
        lock_path: Optional[Path] = None, verbose: bool = True) -> Dict:
    bench = Bench(report_path=Path(report_path or DEFAULT_REPORT),
                  protocol_path=protocol_path, lock_path=lock_path,
                  verbose=verbose)
    return bench.execute()
