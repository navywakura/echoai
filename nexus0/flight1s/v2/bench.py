"""The v2 bench: the same 48 episodes, three separated verdicts.

Everything about the flight is v1's — same worlds, same body, same PX4,
same script, same 5 N for 600 ms, same host supervisor and runner. What
changed is how the perturbed episodes are judged: ``stimulus``,
``challenge`` and ``recovery`` are three groups with three denominators,
and none can pay for another.

Nothing in ``nexus0/flight1s/*.py`` is touched, so v1's report keeps
reconstructing. The v2 lock records that fact and the bench refuses to
run if it stops being true.
"""

from __future__ import annotations

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
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.flight1s import worldbuild
from echoai.nexus0.flight1s.bench import FAMILY, WORLD_PROTOCOL, condition_order
from echoai.nexus0.flight1s.session import run_episode
from echoai.nexus0.flight1s.v2 import evaluate as v2eval
from echoai.nexus0.flight1s.v2 import mutants as v2mut
from echoai.nexus0.flight1s.v2 import protocol as protomod
from echoai.nexus0.flight1s.v2.runtime import (
    DEFAULT_LOCK,
    ECHOAI,
    Runtime,
    check_v1_undisturbed,
    code_inventory,
    load_lock,
    preflight,
)

LAB = ECHOAI / "lab" / "flight1s-v2"
DEFAULT_REPORT = ECHOAI / "lab" / "echo3_flight1s_v2_report.json"

MANDATORY_GROUPS = (
    "envelope", "episodes", "stimulus", "challenge", "recovery",
    "repetition", "hygiene", "controls", "mutants", "regression",
    "v1_preserved",
)

LIMITATIONS = [
    "Software in the loop only: a simulated body under this PX4 "
    "configuration. Not aerodynamic realism, real wind, autonomy, universal "
    "safety or sim-to-real.",
    "A repaired rehearsal, not a blind generalisation exam: the twelve worlds "
    "were already flown under v1 and are public rehearsal data.",
    "echoAI is disconnected: agent_in_gazebo=false, cortex_calls=0, "
    "wsp_writes=0, and no simulated sensor is published as evidence.",
    "PX4 owns stabilisation and mixing; no PID was touched between v1 and v2.",
    "The impulse ratio is a finite difference of the backend pose stream, not "
    "an independent velocity sensor, and the net momentum change also "
    "reflects PX4's reaction.",
    "The disturbance is one constant link wrench. It is not wind.",
    "Timing and RTF describe one host; they are not energy or endurance.",
    "The v1 red result is untouched and still audits; v2 does not reinterpret "
    "it.",
    "hardware_status=not_available: there is no aircraft and no Akida.",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    return str(p.relative_to(ECHOAI)) if p.is_relative_to(ECHOAI) else str(p)


class Bench:
    def __init__(self, *, report_path: Path, protocol_path: Optional[Path],
                 lock_path: Optional[Path] = None, verbose: bool = True) -> None:
        self.report_path = Path(report_path).resolve()
        self.protocol_path = protocol_path
        self.lock_path = lock_path or DEFAULT_LOCK
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
            print(f"[flight1s-v2 {time.monotonic() - self.t0:7.1f}s] {msg}",
                  flush=True)

    def group(self, name: str, status: str, detail: str = "",
              cases: Optional[Sequence[Dict]] = None, **extra) -> None:
        payload = {"status": status, "detail": detail, "cases": list(cases or [])}
        payload.update(extra)
        self.groups[name] = payload
        self.log(f"group {name}: {status}" + (f" ({detail})" if detail else ""))

    def execute(self) -> Dict:
        proto = protomod.load(self.protocol_path)
        runtime = self._lock(proto)
        self.lock_sha256 = str(runtime.lock.get("lock_sha256", ""))
        self.log(f"runtime available={runtime.available} {runtime.reason}")

        self._group_v1_preserved()

        world_proto = load_world_protocol(WORLD_PROTOCOL)
        if world_proto.sha256 != proto["worlds"]["protocol_sha256"]:
            raise Sim3Error("world_protocol_mismatch", world_proto.sha256)
        if sha256_bytes(FAMILY.read_bytes()) != proto["worlds"]["family_sha256"]:
            raise Sim3Error("world_family_mismatch", "family bytes changed")

        if self.suite_root.exists():
            shutil.rmtree(self.suite_root)
        packages = generate_suite(self.suite_root, world_proto, REHEARSAL_SECRET,
                                  rehearsal_assignment())

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
            for name in ("episodes", "stimulus", "challenge", "recovery",
                         "repetition", "hygiene", "controls", "mutants"):
                self.group(name, "not_run", runtime.reason or "backend unavailable")
        self._group_regression()
        return self._finish(proto, runtime, packages)

    def _lock(self, proto) -> Runtime:
        existing = load_lock(self.lock_path) if Path(self.lock_path).exists() \
            else Runtime(False)
        if existing.lock:
            _, code_sha = code_inventory()
            frozen = existing.lock.get("code", {}).get("code_sha256")
            if code_sha != frozen:
                raise Sim3Error(
                    "lock_stale",
                    f"code is {code_sha}, lock pins {frozen}; re-run the v2 "
                    f"preflight")
            if existing.lock.get("protocol_sha256") not in ("", proto.sha256):
                raise Sim3Error("lock_protocol_mismatch",
                                str(existing.lock.get("protocol_sha256")))
            self.log("using the frozen v2 runtime lock")
            return existing
        self.log("no v2 lock: running preflight and freezing it")
        return preflight(lock_path=self.lock_path, write=True,
                         protocol_sha256=proto.sha256)

    def _group_v1_preserved(self) -> None:
        """v2 must not have disturbed v1. Checked, not asserted."""
        state = check_v1_undisturbed()
        cases = [{"check": "v1_code_inventory", **state}]
        for rel, expected in (
            ("docs/examples/flight1s/protocol.json",
             protomod.V1_PROTOCOL_SHA256),
        ):
            path = ECHOAI / rel
            observed = sha256_bytes(path.read_bytes()) if path.exists() else None
            cases.append({"check": rel, "expected": expected,
                          "observed": observed, "ok": observed == expected})
        report_path = ECHOAI / "lab" / "echo3_flight1s_report.json"
        observed = (sha256_bytes(report_path.read_bytes())
                    if report_path.exists() else None)
        cases.append({"check": "lab/echo3_flight1s_report.json exists",
                      "file_sha256": observed, "ok": observed is not None})
        ok = all(c["ok"] for c in cases)
        self.group("v1_preserved", "pass" if ok else "fail",
                   "v1 code, protocol and report untouched", cases)

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
                    m = v2eval.episode_metrics(ep, proto.data,
                                               package=gen.package)
                    m["package_id"] = gen.package_id
                    m["split"] = gen.split
                    m["repeat"] = repeat
                    m["order_slot"] = slot
                    m["effective_sha256"] = ep.effective_sha256
                    m["lock_sha256"] = self.lock_sha256
                    m["protocol_sha256"] = proto.sha256
                    m["runtime"] = ep.metrics
                    m["hover"] = v2eval.hover_within_bands(m, proto.data)
                    trace = self._save_trace(label, ep)
                    m["trace_sha256"] = trace["sha256"]
                    results[(gen.package_id, repeat, condition)] = m
                    self.episodes.append(m)
                    ep_cases.append(_episode_case(m))
                slot += 1

        n = len(self.episodes)
        completed = [c for c in ep_cases if c["completed"]]
        self.group("episodes",
                   "pass" if len(completed) == n == int(proto["episodes"]) else "fail",
                   f"{len(completed)}/{n} completed, {proto['episodes']} required",
                   ep_cases)
        self._group_three(proto)
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

    def _group_three(self, proto) -> None:
        """The repair: one group per question, each with its own denominator."""
        for name, key in (("stimulus", "stimulus"),
                          ("challenge", "challenge"),
                          ("recovery", "recovery_verdict")):
            cases = []
            ok = True
            for m in self.episodes:
                verdict = m.get(key) or {}
                if name == "challenge":
                    keep = True                      # controls are informative
                else:
                    keep = m["condition"] == "perturbed"
                if not keep:
                    continue
                cases.append(verdict)
                ok &= bool(verdict.get("ok"))
            perturbed = sum(1 for c in cases if c.get("condition") == "perturbed")
            self.group(name, "pass" if ok and cases else "fail",
                       f"{perturbed} perturbed episodes judged", cases)

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
                    "same_effective_sha": a["effective_sha256"]
                                          == b["effective_sha256"]}
            if cond == "perturbed":
                ra = (a.get("recovery") or {}).get("recovery_ms")
                rb = (b.get("recovery") or {}).get("recovery_ms")
                case["recovery_delta_ms"] = (abs(ra - rb) if ra is not None
                                             and rb is not None else None)
                case["recovery_tolerance_ms"] = tol["paired_recovery_ms"]
            case["ok"] = bool(
                case["same_effective_sha"] and d_rms <= tol["paired_hover_rms_mm"]
                and (cond != "perturbed"
                     or (case.get("recovery_delta_ms") is not None
                         and case["recovery_delta_ms"] <= tol["paired_recovery_ms"])))
            cases.append(case)
            ok &= case["ok"]
        self.group("repetition", "pass" if ok and cases else "fail",
                   f"{len(cases)} paired repeats", cases)

    def _group_hygiene(self, proto) -> None:
        ceiling = proto["hover_bands"]["attitude_max_mdeg"]
        cases = []
        ok = True
        locks = set()
        protocols = set()
        for m in self.episodes:
            timing = m.get("timing", {})
            att = max(m.get("hover_attitude_max_mdeg", 0),
                      m.get("disturb_attitude_max_mdeg", 0))
            landed = timing.get("landed_z_um")
            rest = m.get("rest_z_um")
            sig = m.get("px4_signature", {})
            col = m.get("collisions", {})
            case = {
                "label": m["label"],
                "clock_regressions": timing.get("clock_regressions"),
                "effective_sample_hz": timing.get("effective_sample_hz"),
                "attitude_max_mdeg": att, "attitude_ceiling_mdeg": ceiling,
                "px4_signature_ok": bool(sig.get("ok")),
                "unauthorised_contacts": col.get("unauthorised"),
                "landed_within_10mm_of_rest": (
                    landed is not None and rest is not None
                    and abs(landed - rest) <= 10_000),
                "finite": _all_finite(m),
            }
            case["ok"] = bool(
                m["ok"] and case["clock_regressions"] == 0
                and att <= ceiling and case["landed_within_10mm_of_rest"]
                and case["finite"] and case["px4_signature_ok"]
                and col.get("unauthorised") == 0)
            cases.append(case)
            ok &= case["ok"]
            locks.add(m.get("lock_sha256"))
            protocols.add(m.get("protocol_sha256"))
        single = len(locks) == 1 and len(protocols) == 1
        if not single:
            ok = False
        self.group("hygiene", "pass" if ok and cases else "fail",
                   f"{len(cases)} episodes; one lock and one protocol={single}",
                   cases, locks=sorted(x for x in locks if x),
                   protocols=sorted(x for x in protocols if x))

    def _group_controls(self, runtime: Runtime, packages: Sequence, proto) -> None:
        cases, ok = v2mut.controls(runtime, packages, proto, log=self.log)
        self.group("controls", "pass" if ok else "fail",
                   f"{len(cases)} controls", cases)

    def _group_mutants(self, runtime: Runtime, packages: Sequence, proto) -> None:
        cases, ok = v2mut.run_all(runtime, packages, proto, log=self.log)
        status = "pass" if ok else "fail"
        if not runtime.available:
            status = "not_run"
        self.group("mutants", status, f"{len(cases)} cases", cases)

    def _group_regression(self) -> None:
        env = dict(os.environ, PYTHONPATH=str(ECHOAI.parent))
        cases = []
        ok = True
        banks = (
            ("nexus0", [sys.executable, "-m", "echoai.tests.test_nexus0"]),
            ("sim3", [sys.executable, str(ECHOAI / "tests" / "test_sim3.py")]),
            ("flight1s_v1_unit", [sys.executable,
                                  str(ECHOAI / "tests" / "test_flight1s.py")]),
        )
        for name, cmd in banks:
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
                   "nexus0, sim3 and the v1 unit bank", cases)

    def _finish(self, proto, runtime: Runtime, packages: Sequence) -> Dict:
        mandatory = {k: self.groups.get(k, {"status": "not_run"})["status"]
                     for k in MANDATORY_GROUPS}
        green = all(v == "pass" for v in mandatory.values())
        report = {
            "schema_version": 1,
            "scope": "flight_software_in_the_loop",
            "dataset_kind": "rehearsal",
            "slice": "FLIGHT-1S",
            "protocol_version": 2,
            "generated_at_utc": _utc(),
            "flight1s_green": green,
            "hardware_status": "not_available",
            "agent_in_gazebo": False,
            "cortex_calls": 0,
            "wsp_writes": 0,
            "supersedes": proto["supersedes"],
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
                "stimulus": proto["stimulus"],
                "challenge": proto["challenge"],
                "recovery": proto["recovery"],
                "hover_bands": proto["hover_bands"],
                "tolerances": proto["tolerances"],
                "calibration": _rel(LAB / "calibration.json"),
            },
            "runtime_lock": {
                "path": _rel(Path(self.lock_path)),
                "available": runtime.available,
                "reason": runtime.reason,
                "lock_sha256": runtime.lock.get("lock_sha256"),
                "code_sha256": runtime.lock.get("code", {}).get("code_sha256"),
                "v1": runtime.lock.get("v1", {}),
                "px4": runtime.lock.get("px4", {}),
                "container": runtime.lock.get("container", {}),
            },
            "world_systems": list(worldbuild.WORLD_SYSTEMS
                                  + worldbuild.FLIGHT_SYSTEMS),
            "host": {"platform": platform.platform(),
                     "python": platform.python_version()},
            "commands": [
                "PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 preflight "
                "--output lab/flight1s-v2/runtime-lock.json",
                "PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 bench "
                f"--rehearsal --output {_rel(self.report_path)}",
                "PYTHONPATH=.. python3 -m echoai.nexus0.flight1s.v2 audit "
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

        def stat(cond=None, path=None):
            vals = []
            for m in measured:
                if cond and m["condition"] != cond:
                    continue
                v = m
                for part in path:
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
            "hover_horiz_rms_mm": stat(path=["hover_horiz_rms_mm"]),
            "hover_horiz_max_mm": stat(path=["hover_horiz_max_mm"]),
            "hover_alt_offset_mm": stat(path=["hover_alt_offset_mm"]),
            "impulse_ratio_ppk": stat("perturbed", ["impulse", "ratio_ppk"]),
            "excursion_mm_perturbed": stat("perturbed",
                                           ["disturb_excursion_mm"]),
            "excursion_mm_nominal": stat("nominal", ["disturb_excursion_mm"]),
            "max_speed_x_mm_s": stat("perturbed", ["max_speed_x_mm_s"]),
            "attitude_mdeg_perturbed": stat("perturbed",
                                            ["disturb_attitude_max_mdeg"]),
            "recovery_ms": stat("perturbed", ["recovery", "recovery_ms"]),
            "effective_sample_hz": stat(path=["timing", "effective_sample_hz"]),
            "episode_wall_s": stat(path=["runtime", "wall_s"]),
            "rtf": stat(path=["runtime", "rtf"]),
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
