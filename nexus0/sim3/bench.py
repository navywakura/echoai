"""The preregistered SIM-3 bench.

Nine groups, each with the green criterion SIM3-DESIGN.md §6 fixed
before any of this ran. A group is ``pass``, ``fail`` or ``not_run``;
a missing dependency is never ``pass``, and ``sim3_green`` requires
every mandatory group in ``pass`` plus the existing NEXUS-0 regression.

The bench writes one trace file per Gazebo run and records its hash, so
the auditor can recompute every number here from the traces instead of
believing the summary. It also writes red results: a failing case keeps
its measurement and its cause.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from echoai.nexus0.sim3 import evaluate, metamorph, mutants, sandbox
from echoai.nexus0.sim3.canon import (
    Sim3Error,
    dump_report,
    report_sha256,
    sha256_bytes,
)
from echoai.nexus0.sim3.generate import (
    ARCHETYPES,
    SplitMix64,
    build_layout,
    generate_suite,
    load_family,
    rehearsal_assignment,
)
from echoai.nexus0.sim3.geom import Aabb, planar_equivalent
from echoai.nexus0.sim3.pkg import Protocol, load_protocol
from echoai.nexus0.sim3.runtime import (
    DEFAULT_LOCK,
    ECHOAI,
    Runtime,
    check_sdf,
    code_inventory,
    load_lock,
    preflight,
)
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET, protocol_commitment
from echoai.nexus0.sim3.session import SessionResult, run_episode

LAB = ECHOAI / "lab" / "sim3"
DEFAULT_REPORT = ECHOAI / "lab" / "echo3_sim3_report.json"
EXAMPLE_PROTOCOL = ECHOAI / "docs" / "examples" / "sim3" / "protocol.json"

MANDATORY_GROUPS = (
    "packages", "distinction", "physics", "repetition", "isolation",
    "rename", "moved_wall", "sealing", "mutants", "regression",
)

LIMITATIONS = [
    "Infrastructure only: no flight, no sensors, no WSP, no learning, no cortex.",
    "The consumer is an instrumental probe, not an agent; agent_in_gazebo=false.",
    "Isolation covers accidental leaks and direct access by the probe. It is not "
    "a claim about kernel escapes or timing side channels.",
    "Contact and fall prove gravity and collision. They prove nothing about "
    "aerodynamics or about an X500 airframe.",
    "The initial tick's sim_time is the backend's first pre-update time minus one "
    "verified step; every other tick carries a time read from the backend.",
    "Connectivity is a discrete 100 mm flood fill over inflated AABBs, not a "
    "guarantee of safe continuous navigation.",
    "24 runs on one host describe latency and RTF; they do not promise a stable "
    "P99 or an edge power figure.",
    "rehearsal-C is a dress rehearsal with a published secret. It is not reserved "
    "evidence and it consumes no campaign exam.",
    "Physics is not claimed to be bit-identical across hosts; a new platform "
    "requires a new lock and a rerun of the bench.",
]


def _rel(path: Path) -> str:
    """Repo-relative when it can be, absolute when it cannot."""
    p = Path(path).resolve()
    return str(p.relative_to(ECHOAI)) if p.is_relative_to(ECHOAI) else str(p)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Bench:
    def __init__(self, *, report_path: Path, protocol_path: Path,
                 lock_path: Optional[Path] = None, keep_traces: bool = True,
                 verbose: bool = True) -> None:
        self.report_path = Path(report_path).resolve()
        self.protocol_path = Path(protocol_path).resolve()
        self.lock_path = lock_path
        self.keep_traces = keep_traces
        self.verbose = verbose
        self.groups: Dict[str, Dict] = {}
        self.traces: List[Dict] = []
        self.runs: List[Dict] = []
        self.commands: List[str] = []
        self.run_root = LAB / "runs"
        self.suite_root = LAB / "suite"
        self.work_root = Path(tempfile.mkdtemp(prefix="sim3-bench-"))
        self.lock_sha256 = ""
        self.t0 = time.monotonic()

    # -- plumbing ---------------------------------------------------------

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[sim3 {time.monotonic() - self.t0:7.1f}s] {msg}", flush=True)

    def group(self, name: str, status: str, detail: str = "",
              cases: Optional[Sequence[Dict]] = None, **extra) -> None:
        payload = {"status": status, "detail": detail, "cases": list(cases or [])}
        payload.update(extra)
        self.groups[name] = payload
        self.log(f"group {name}: {status} ({detail})" if detail
                 else f"group {name}: {status}")

    def save_trace(self, run_id: str, result: SessionResult) -> Dict:
        self.run_root.mkdir(parents=True, exist_ok=True)
        path = self.run_root / f"{run_id}.json"
        raw = dump_report(path, result.trace())
        entry = {"run_id": run_id, "path": str(path.relative_to(ECHOAI)),
                 "sha256": sha256_bytes(raw), "bytes": len(raw)}
        self.traces.append(entry)
        return entry

    def record_run(self, run_id: str, group: str, package_id: str,
                   split: str, result: SessionResult, verdicts: Dict[str, Dict]
                   ) -> None:
        self.runs.append({
            "run_id": run_id,
            "group": group,
            # Per run, not once per report: "the same runtime for every
            # world" is only checkable if each world says which one it used.
            "lock_sha256": self.lock_sha256,
            "package_id": package_id,
            "split": split,
            "ok": result.ok,
            "cause": result.cause,
            "effective_sha256": result.effective_sha256,
            "source_sha256": result.source_sha256,
            "tick_transcript_sha256": result.tick_transcript_sha256,
            "n_ticks": result.n_ticks,
            "metrics": result.metrics,
            "verdicts": verdicts,
        })

    # -- the run ----------------------------------------------------------

    def execute(self) -> Dict:
        protocol = load_protocol(self.protocol_path)
        commitment = protocol_commitment(protocol.sha256, REHEARSAL_SECRET)
        self.commands = [
            f"PYTHONPATH=.. python3 -m echoai.nexus0.sim3 preflight "
            f"--output lab/sim3/runtime-lock.json",
            f"PYTHONPATH=.. python3 -m echoai.nexus0.sim3 bench --rehearsal "
            f"--output {_rel(self.report_path)}",
            f"PYTHONPATH=.. python3 -m echoai.nexus0.sim3 audit "
            f"{_rel(self.report_path)}",
        ]

        runtime = self._lock()
        self.lock_sha256 = str(runtime.lock.get("lock_sha256", ""))
        self.log(f"runtime available={runtime.available} {runtime.reason}")

        packages = self._group_packages(protocol, runtime)
        if packages is None:
            for name in MANDATORY_GROUPS:
                self.groups.setdefault(
                    name, {"status": "not_run", "detail": "package group failed",
                           "cases": []})
        else:
            self._group_distinction(protocol, packages)
            if runtime.available:
                self._group_physics(runtime, protocol, packages)
                self._group_rename(runtime, protocol, packages)
                self._group_moved_wall(runtime, protocol, packages)
            else:
                for name in ("physics", "repetition", "isolation", "rename",
                             "moved_wall"):
                    self.group(name, "not_run", runtime.reason
                               or "backend or sandbox unavailable")
            self._group_sealing(protocol, packages)
            self._group_mutants(runtime, protocol, packages)
        self._group_regression()

        return self._finish(protocol, runtime, commitment, packages)

    def _lock(self) -> Runtime:
        existing = load_lock(self.lock_path)
        if existing.lock:
            # A lock that predates the code it is supposed to pin is not a
            # lock. Refuse rather than measure under one and report another.
            _, code_sha = code_inventory()
            frozen = existing.lock.get("code", {}).get("code_sha256")
            if code_sha != frozen:
                raise Sim3Error(
                    "lock_stale",
                    f"code is {code_sha}, lock pins {frozen}; re-run "
                    f"`python3 -m echoai.nexus0.sim3 preflight`")
            self.log("using frozen runtime-lock.json")
            return existing
        self.log("no lock: running preflight and freezing it")
        return preflight(lock_path=self.lock_path, write=True)

    # -- groups -----------------------------------------------------------

    def _group_packages(self, protocol: Protocol,
                        runtime: Runtime) -> Optional[List]:
        if self.suite_root.exists():
            shutil.rmtree(self.suite_root)
        assignment = rehearsal_assignment()
        try:
            results = generate_suite(self.suite_root, protocol, REHEARSAL_SECRET,
                                     assignment)
        except Sim3Error as exc:
            self.group("packages", "fail", f"{exc.code}: {exc.detail}")
            return None

        cases = []
        ok = True
        for gen in results:
            case = {
                "package_id": gen.package_id, "split": gen.split,
                "index": gen.index, "seed": gen.seed, "attempts": gen.attempts,
                "rejections": gen.rejections,
                **gen.package.public_view(),
                "own_validator": "pass",
            }
            if runtime.available:
                source = (gen.path / "world.sdf").read_bytes()
                check = check_sdf(runtime, source)
                case["libsdformat"] = check
                if not check["valid"]:
                    ok = False
            else:
                case["libsdformat"] = {"status": "not_run",
                                       "reason": runtime.reason}
            cases.append(case)
        if not runtime.available:
            # Our own validator passed, but the group asks for libsdformat
            # too. A missing dependency is not_run, never pass and never a
            # failure we did not observe.
            self.group("packages", "not_run", runtime.reason, cases)
            return results
        detail = f"{len(cases)} packages; libsdformat checked"
        self.group("packages", "pass" if ok and len(cases) == 12 else "fail",
                   detail, cases)
        return results

    def _group_distinction(self, protocol: Protocol, results: Sequence) -> None:
        cases = []
        ok = True
        bases = {}
        family = load_family()
        for split in ARCHETYPES:
            layout = build_layout(SplitMix64(0), split, family)
            bases[split] = [Aabb.from_pose_size(b.pose, b.size) for b in layout.boxes]
        for a, b in (("A", "B"), ("A", "C"), ("B", "C")):
            equivalent = planar_equivalent(bases[a], bases[b])
            cases.append({"pair": f"{a}/{b}", "planar_equivalent": equivalent,
                          "n_boxes": [len(bases[a]), len(bases[b])]})
            if equivalent:
                ok = False

        fingerprints = {}
        for gen in results:
            fp = gen.package.fingerprint_sha256
            if fp in fingerprints:
                cases.append({"duplicate_fingerprint": [fingerprints[fp],
                                                        gen.package_id]})
                ok = False
            fingerprints[fp] = gen.package_id

        # Regenerate from the same seeds into a different directory: the
        # package hash must come back identical, and it must not depend on
        # the order the suite was written in.
        replay_root = self.work_root / "replay"
        replay = generate_suite(replay_root, protocol, REHEARSAL_SECRET,
                                list(reversed(rehearsal_assignment())))
        replayed = {r.package_id: r.package.package_sha256 for r in replay}
        for gen in results:
            same = replayed.get(gen.package_id) == gen.package.package_sha256
            cases.append({"package_id": gen.package_id, "reproducible": same,
                          "package_sha256": gen.package.package_sha256})
            if not same:
                ok = False
        shutil.rmtree(replay_root, ignore_errors=True)
        self.group("distinction", "pass" if ok else "fail",
                   f"{len(fingerprints)} distinct fingerprints", cases)

    def _group_physics(self, runtime: Runtime, protocol: Protocol,
                       results: Sequence) -> None:
        phys_cases: List[Dict] = []
        iso_cases: List[Dict] = []
        rep_cases: List[Dict] = []
        phys_ok = iso_ok = rep_ok = True
        for gen in results:
            repeats: List[SessionResult] = []
            for repeat in (1, 2):
                run_id = f"physics-{gen.package_id}-r{repeat}"
                canaries = mutants.canaries(run_id)
                self.log(f"run {run_id}")
                result = run_episode(runtime, gen.package, protocol,
                                     canaries=canaries, label=run_id)
                trace = self.save_trace(run_id, result)
                pv = evaluate.physics(result, gen.package, protocol)
                iv = evaluate.isolation(result, canaries)
                verdicts = {
                    "physics": {"ok": pv.ok, "failures": pv.failures,
                                "measured": pv.measured},
                    "isolation": {"ok": iv.ok, "failures": iv.failures,
                                  "measured": iv.measured},
                }
                self.record_run(run_id, "physics", gen.package_id, gen.split,
                                result, verdicts)
                phys_cases.append({"run_id": run_id, "trace_sha256": trace["sha256"],
                                   **verdicts["physics"]})
                iso_cases.append({"run_id": run_id, **verdicts["isolation"]})
                phys_ok &= pv.ok
                iso_ok &= iv.ok
                repeats.append(result)
            rv = evaluate.pair_repetition(repeats[0], repeats[1], protocol)
            rep_cases.append({"package_id": gen.package_id, "ok": rv.ok,
                              "failures": rv.failures, "measured": rv.measured})
            rep_ok &= rv.ok

        self.group("physics", "pass" if phys_ok else "fail",
                   f"{len(phys_cases)} runs", phys_cases)
        self.group("repetition", "pass" if rep_ok else "fail",
                   f"{len(rep_cases)} pairs", rep_cases)
        selftest = sandbox.self_test(runtime)
        if not selftest.get("ok"):
            iso_ok = False
        self.group("isolation", "pass" if iso_ok else "fail",
                   f"{len(iso_cases)} runs", iso_cases, sandbox_self_test=selftest)

    def _group_rename(self, runtime: Runtime, protocol: Protocol,
                      results: Sequence) -> None:
        cases = []
        ok = True
        for gen in results:
            out = self.work_root / "renamed" / gen.package_id
            renamed = metamorph.renamed(gen.package, out, protocol)
            run_id = f"rename-{gen.package_id}"
            self.log(f"run {run_id}")
            result = run_episode(runtime, renamed, protocol,
                                 canaries=mutants.canaries(run_id), label=run_id)
            trace = self.save_trace(run_id, result)
            base = next(r for r in self.runs
                        if r["run_id"] == f"physics-{gen.package_id}-r1")
            same_fp = renamed.fingerprint_sha256 == gen.package.fingerprint_sha256
            same_transcript = (result.tick_transcript_sha256
                               == base["tick_transcript_sha256"])
            pose_delta = None
            if result.ok:
                origin = next(t for t in self.traces
                              if t["run_id"] == f"physics-{gen.package_id}-r1")
                origin_trace = json.loads(
                    (ECHOAI / origin["path"]).read_text())
                pose_delta = max(
                    abs(a - b) for a, b in
                    zip(result.frames[-1]["rig_um"],
                        origin_trace["frames_um"][-1][1:]))
            case = {
                "package_id": gen.package_id, "run_id": run_id,
                "trace_sha256": trace["sha256"],
                "names_differ": [m.name for m in renamed.sdf.models]
                                != [m.name for m in gen.package.sdf.models]
                                or [m.pose_mm for m in renamed.sdf.models]
                                != [m.pose_mm for m in gen.package.sdf.models],
                "source_sha_differs": renamed.sdf.sha256 != gen.package.sdf.sha256,
                "fingerprint_identical": same_fp,
                "transcript_identical": same_transcript,
                "final_pose_delta_um": pose_delta,
            }
            case["ok"] = bool(result.ok and same_fp and same_transcript
                              and case["names_differ"]
                              and pose_delta is not None
                              and pose_delta <= protocol.criteria[
                                  "pair_pose_error_mm"] * 1000)
            self.record_run(run_id, "rename", gen.package_id, gen.split, result,
                            {"rename": case})
            cases.append(case)
            ok &= case["ok"]
        self.group("rename", "pass" if ok else "fail", f"{len(cases)} pairs", cases)

    def _group_moved_wall(self, runtime: Runtime, protocol: Protocol,
                          results: Sequence) -> None:
        cases = []
        ok = True
        rig_r = int(protocol.rig["radius_mm"])
        for gen in results:
            out = self.work_root / "moved" / gen.package_id
            try:
                moved = metamorph.moved_wall(gen.package, out, protocol,
                                             rig_radius_mm=rig_r)
            except Sim3Error as exc:
                cases.append({"package_id": gen.package_id, "ok": False,
                              "cause": exc.as_dict()})
                ok = False
                continue
            run_id = f"moved-{gen.package_id}"
            self.log(f"run {run_id}")
            result = run_episode(runtime, moved.package, protocol,
                                 canaries=mutants.canaries(run_id), label=run_id)
            trace = self.save_trace(run_id, result)
            base = next(r for r in self.runs
                        if r["run_id"] == f"physics-{gen.package_id}-r1")

            # Backend entity truth, not the parser: the moved barrier's
            # link pose as the running simulator reports it.
            moved_name = moved.package.sdf.models[moved.barrier_index].name
            entity_um = result.model_poses_um.get(moved_name)
            origin_trace = json.loads(
                (ECHOAI / next(t["path"] for t in self.traces
                               if t["run_id"] == f"physics-{gen.package_id}-r1")
                 ).read_text())
            origin_um = origin_trace["model_poses_um"].get(moved_name)
            entity_delta_um = (
                [abs(a - b) for a, b in zip(entity_um, origin_um)]
                if entity_um and origin_um else None
            )

            drop = self._collision_probe(runtime, protocol, gen.package,
                                         moved, run_id)
            case = {
                "package_id": gen.package_id, "run_id": run_id,
                "trace_sha256": trace["sha256"],
                "axis": moved.axis, "shift_mm": moved.shift_mm,
                "old_aabb_mm": moved.old_aabb, "new_aabb_mm": moved.new_aabb,
                "fingerprint_differs":
                    moved.package.fingerprint_sha256 != gen.package.fingerprint_sha256,
                "source_sha_differs":
                    moved.package.sdf.sha256 != gen.package.sdf.sha256,
                "entity_delta_um": entity_delta_um,
                "entity_moved_500mm": bool(entity_delta_um
                                           and max(entity_delta_um) == 500_000),
                "transcript_identical":
                    result.tick_transcript_sha256 == base["tick_transcript_sha256"],
                "collision_probe": drop,
            }
            case["ok"] = bool(
                result.ok and case["fingerprint_differs"]
                and case["source_sha_differs"] and case["entity_moved_500mm"]
                and case["transcript_identical"] and drop.get("ok")
            )
            self.record_run(run_id, "moved_wall", gen.package_id, gen.split,
                            result, {"moved_wall": case})
            cases.append(case)
            ok &= case["ok"]
        self.group("moved_wall", "pass" if ok else "fail", f"{len(cases)} pairs",
                   cases)

    def _collision_probe(self, runtime: Runtime, protocol: Protocol,
                         original: Package, moved: metamorph.MovedWall,
                         run_id: str) -> Dict:
        """Drop the rig over the moved wall in both worlds and compare."""
        rig_r = int(protocol.rig["radius_mm"])
        cx, cy = moved.drop_column_mm
        start_z = moved.barrier_top_mm + 300
        steps = 1500
        out: Dict = {"column_mm": [cx, cy], "start_z_mm": start_z, "steps": steps}
        try:
            after = run_episode(runtime, moved.package, protocol,
                                label=f"{run_id}-drop-moved", steps=steps,
                                rig_centre_mm=(cx, cy, start_z))
            before = run_episode(runtime, original, protocol,
                                 label=f"{run_id}-drop-origin", steps=steps,
                                 rig_centre_mm=(cx, cy, start_z))
        except Sim3Error as exc:
            out.update({"ok": False, "cause": exc.as_dict()})
            return out
        self.save_trace(f"{run_id}-drop-moved", after)
        self.save_trace(f"{run_id}-drop-origin", before)
        if not (after.ok and before.ok):
            out.update({"ok": False, "cause": (after.cause or before.cause)})
            return out
        floor_top = original.aabb_of(original.floor).hi[2]
        rest_after_um = after.frames[-1]["rig_um"][2]
        rest_before_um = before.frames[-1]["rig_um"][2]
        want_after = (moved.barrier_top_mm + rig_r) * 1000
        want_before = (floor_top + rig_r) * 1000
        tol = int(protocol.criteria["rest_error_mm"]) * 1000
        out.update({
            "rest_on_moved_wall_um": rest_after_um,
            "expected_on_wall_um": want_after,
            "rest_in_original_um": rest_before_um,
            "expected_on_floor_um": want_before,
            "contacts_moved": (after.gz_report or {}).get("pairs"),
            "contacts_origin": (before.gz_report or {}).get("pairs"),
            "ok": (abs(rest_after_um - want_after) <= tol
                   and abs(rest_before_um - want_before) <= tol
                   and rest_after_um - rest_before_um > 1000),
        })
        return out

    def _group_sealing(self, protocol: Protocol, results: Sequence) -> None:
        cases, ok = mutants.sealing_cases(self.work_root / "seal", protocol, results)
        self.group("sealing", "pass" if ok else "fail", f"{len(cases)} checks", cases)

    def _group_mutants(self, runtime: Runtime, protocol: Protocol,
                       results: Sequence) -> None:
        cases, ok = mutants.run_all(self.work_root / "mutants", protocol, results,
                                    runtime, self.report_path, log=self.log)
        if not runtime.available:
            status = "not_run"
        else:
            status = "pass" if ok else "fail"
        self.group("mutants", status,
                   f"{len(cases)} cases; runtime mutants " +
                   ("run" if runtime.available else "not run"), cases)

    def _group_regression(self) -> None:
        cmd = [sys.executable, "-m", "echoai.tests.test_nexus0"]
        env = dict(os.environ, PYTHONPATH=str(ECHOAI.parent))
        self.log("regression: echoai.tests.test_nexus0")
        try:
            proc = subprocess.run(cmd, cwd=str(ECHOAI.parent), env=env,
                                  capture_output=True, timeout=1800)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.group("regression", "not_run", str(exc))
            return
        tail = proc.stdout.decode(errors="replace").strip().splitlines()[-12:]
        self.group("regression", "pass" if proc.returncode == 0 else "fail",
                   f"returncode={proc.returncode}",
                   [{"command": "PYTHONPATH=.. python3 -m echoai.tests.test_nexus0",
                     "returncode": proc.returncode, "tail": tail}])

    # -- report -----------------------------------------------------------

    def _finish(self, protocol: Protocol, runtime: Runtime, commitment: str,
                packages) -> Dict:
        mandatory = {k: self.groups.get(k, {"status": "not_run"})["status"]
                     for k in MANDATORY_GROUPS}
        green = all(v == "pass" for v in mandatory.values())
        assignment = []
        if packages:
            for gen in packages:
                assignment.append({
                    "package_id": gen.package_id, "split": gen.split,
                    "index": gen.index, "seed": gen.seed,
                    "package_sha256": gen.package.package_sha256,
                    "fingerprint_sha256": gen.package.fingerprint_sha256,
                })
        report = {
            "schema_version": 1,
            "scope": "simulation_infrastructure",
            "dataset_kind": "rehearsal",
            "slice": "SIM-3",
            "generated_at_utc": _utc(),
            "sim3_green": green,
            "hardware_status": "not_available",
            "agent_in_gazebo": False,
            "cortex_calls": 0,
            "group_status": mandatory,
            "groups": self.groups,
            "runs": self.runs,
            "assignment": assignment,
            "protocol": {
                "path": _rel(self.protocol_path),
                "sha256": protocol.sha256,
                "rehearsal_commitment": commitment,
                "rehearsal_secret_hex": REHEARSAL_SECRET.hex(),
            },
            "runtime_lock": {
                "path": _rel(Path(self.lock_path or DEFAULT_LOCK)),
                "available": runtime.available,
                "reason": runtime.reason,
                "lock_sha256": runtime.lock.get("lock_sha256"),
                "code_sha256": runtime.lock.get("code", {}).get("code_sha256"),
                "container": runtime.lock.get("container", {}),
                "sandbox": runtime.lock.get("sandbox", {}),
            },
            "host": {"platform": platform.platform(),
                     "python": platform.python_version()},
            "commands": self.commands,
            "traces": {"dir": str(self.run_root.relative_to(ECHOAI)),
                       "files": self.traces},
            "metrics": self._metrics(),
            "limitations": LIMITATIONS,
            "wall_clock_s": round(time.monotonic() - self.t0, 1),
        }
        report["report_sha256"] = report_sha256(
            {k: v for k, v in report.items() if k != "report_sha256"})
        dump_report(self.report_path, report)
        shutil.rmtree(self.work_root, ignore_errors=True)
        return report

    def _metrics(self) -> Dict:
        # The 24 principal runs only. SIM3-DESIGN.md §6 keeps the
        # metamorphic pairs out of that count, so they stay out of the
        # numbers that describe it too.
        bench_runs = [r for r in self.runs
                      if r["metrics"] and r["group"] == "physics"]
        if not bench_runs:
            return {"n_runs": 0}
        def pick(key, sub=None):
            out = []
            for r in bench_runs:
                v = r["metrics"].get(key)
                if sub and isinstance(v, dict):
                    v = v.get(sub)
                if isinstance(v, (int, float)):
                    out.append(v)
            return sorted(out)
        def summary(vals, unit):
            if not vals:
                return None
            return {"unit": unit, "n": len(vals), "min": vals[0], "max": vals[-1],
                    "p50": vals[len(vals) // 2]}
        return {
            "n_runs": len(bench_runs),
            "n_episodes_total": len(self.traces),
            "scope": "the 24 principal physics runs; metamorphic pairs and "
                     "collision probes are counted but not aggregated here",
            "launch": summary(pick("launch_s"), "s"),
            "rtf": summary(pick("rtf"), "sim_s/wall_s"),
            "ack_latency_p50": summary(pick("ack_latency_ms", "p50"), "ms"),
            "ack_latency_p99": summary(pick("ack_latency_ms", "p99"), "ms"),
            "gz_max_rss": summary(pick("gz_max_rss_kib"), "KiB"),
            "supervisor_max_rss": summary(pick("supervisor_max_rss_kib"), "KiB"),
            "consumer_max_rss": summary(pick("consumer_max_rss_kib"), "KiB"),
            "note": "descriptive on one host; not an edge or energy claim",
        }


def run(report_path: Optional[Path] = None, protocol_path: Optional[Path] = None,
        lock_path: Optional[Path] = None, verbose: bool = True) -> Dict:
    bench = Bench(report_path=Path(report_path or DEFAULT_REPORT),
                  protocol_path=Path(protocol_path or EXAMPLE_PROTOCOL),
                  lock_path=lock_path, verbose=verbose)
    return bench.execute()
