"""The evaluator. It sees the truth; it never answers back.

Everything here reads private data — the manifest, the roles, the rig
poses, the canaries — and turns it into a verdict. Nothing it computes
is written to the tick channel; the only direction of travel is towards
the report.

Two things it deliberately does not do:

* it does not soften a criterion. The numbers come from the frozen
  protocol, and a run that misses one is red with its measurement
  attached;
* it does not accept the probe's word for whether an access was allowed.
  The probe reports what happened; this module decides what that meant,
  and it is the only side that knows the canaries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List

from echoai.nexus0.sim3.pkg import Package, Protocol
from echoai.nexus0.sim3.rig import RIG_COLLISION, RIG_MODEL
from echoai.nexus0.sim3.runtime import (
    SANDBOX_CONSUMER_ARGV,
    SANDBOX_ENV_EXPECTED,
    SANDBOX_HOSTNAME,
)
from echoai.nexus0.sim3.session import SessionResult

ALLOWED_ROOT = {"bin", "dev", "lib", "lib64", "probe", "proc", "sbin", "usr", "work"}
LEAKY_SUBSTRINGS = ("REALRXOS", "echoai", "/lab/", "sim3-run-", "packages/",
                    "manifest", "world.sdf", "seed", "split")


@dataclass
class Verdict:
    ok: bool
    failures: List[str] = field(default_factory=list)
    measured: Dict = field(default_factory=dict)

    def fail(self, why: str) -> None:
        self.ok = False
        self.failures.append(why)


def physics(result: SessionResult, package: Package, protocol: Protocol) -> Verdict:
    """Did a real backend advance a real clock and drop a real sphere?"""
    v = Verdict(ok=True)
    if not result.ok:
        v.fail(f"session:{(result.cause or {}).get('code', 'unknown')}")
        return v
    rig = protocol.rig
    crit = protocol.criteria
    step_ns = protocol.step_ns
    n = protocol.steps

    if len(result.frames) != n:
        v.fail(f"frames={len(result.frames)} expected {n}")
    if result.n_ticks != n + 1:
        v.fail(f"ticks={result.n_ticks} expected {n + 1}")
    if result.initial.get("sim_time_ns") != 0:
        v.fail(f"initial sim_time={result.initial.get('sim_time_ns')}")
    for i, frame in enumerate(result.frames, start=1):
        if frame["sim_time_ns"] != i * step_ns:
            v.fail(f"clock at frame {i}: {frame['sim_time_ns']}")
            break
    if result.gravity_um and result.gravity_um != [0, 0, -9810000]:
        v.fail(f"backend gravity {result.gravity_um}")

    z0_um = result.initial.get("rig_um", [0, 0, 0])[2]
    sample_ns = int(rig["fall_sample_ns"])
    sampled = next((f for f in result.frames if f["sim_time_ns"] == sample_ns), None)
    if sampled is None:
        v.fail(f"no frame at {sample_ns} ns")
        fall_mm = None
    else:
        fall_mm = (z0_um - sampled["rig_um"][2]) / 1000.0
        if not (crit["fall_min_mm"] <= fall_mm <= crit["fall_max_mm"]):
            v.fail(f"fall {fall_mm:.2f} mm outside "
                   f"[{crit['fall_min_mm']},{crit['fall_max_mm']}]")

    floor_top_mm = package.aabb_of(package.floor).hi[2]
    rest_um = result.frames[-1]["rig_um"][2] if result.frames else 0
    expected_um = (floor_top_mm + int(rig["radius_mm"])) * 1000
    rest_err_mm = abs(rest_um - expected_um) / 1000.0
    if rest_err_mm > crit["rest_error_mm"]:
        v.fail(f"rest error {rest_err_mm:.2f} mm > {crit['rest_error_mm']}")

    report = result.gz_report or {}
    n_contacts = int(report.get("n_contact_msgs", 0))
    pairs = [tuple(p) for p in report.get("pairs", [])]
    want_rig = f"{RIG_MODEL}::body::{RIG_COLLISION}"
    want_floor = f"{package.floor}::body::solid"
    if n_contacts <= 0:
        v.fail("no contact observed")
    elif not any(want_rig in p and want_floor in p for p in pairs):
        v.fail(f"contact pairs {pairs} lack {want_rig}/{want_floor}")

    v.measured = {
        "fall_mm": None if fall_mm is None else round(fall_mm, 3),
        "rest_error_mm": round(rest_err_mm, 3),
        "rest_z_um": rest_um,
        "n_contact_msgs": n_contacts,
        "first_contact_ns": (report.get("first_contact") or {}).get("stamp_ns"),
        "contact_pairs": [list(p) for p in pairs],
        "gravity_um": result.gravity_um,
        "n_frames": len(result.frames),
        "n_ticks": result.n_ticks,
    }
    return v


def isolation(result: SessionResult, canaries: Dict[str, str]) -> Verdict:
    """Every forbidden access failed, the allowed one worked, nothing leaked."""
    v = Verdict(ok=True)
    report = result.consumer or {}
    survey = report.get("survey")
    if not survey:
        v.fail("no consumer survey")
        return v

    if survey.get("argv") != SANDBOX_CONSUMER_ARGV:
        v.fail(f"argv {survey.get('argv')}")
    env = survey.get("env", {})
    if set(env) != set(SANDBOX_ENV_EXPECTED):
        v.fail(f"env keys {sorted(env)}")
    for key, want in SANDBOX_ENV_EXPECTED.items():
        if env.get(key) != want:
            v.fail(f"env {key}={env.get(key)!r}")
    hostname = survey.get("hostname", {})
    if hostname.get("value") != SANDBOX_HOSTNAME:
        v.fail(f"hostname {hostname}")
    cwd = survey.get("cwd", {})
    if cwd.get("value") != "/work":
        v.fail(f"cwd {cwd}")
    root = set(survey.get("root_tree", {}))
    if not root or not root <= ALLOWED_ROOT:
        v.fail(f"root {sorted(root)}")
    work = survey.get("work_tree", {})
    if work.get("value"):
        v.fail(f"work not empty: {work}")
    procs = survey.get("proc_entries", {}).get("value", [])
    digits = [p for p in procs if str(p).isdigit()]
    if len(digits) > 2:
        v.fail(f"sibling processes visible: {digits}")

    # The namespace the probe *is* allowed to see must itself be empty.
    self_view = survey.get("self_view") or {}
    cmdline = (self_view.get("proc1_cmdline", {}).get("value") or "")
    cmd_parts = [p for p in cmdline.split("\0") if p]
    if cmd_parts != ["/usr/bin/python3", "/probe/probe.py"]:
        v.fail(f"pid 1 is not the consumer: {cmd_parts[:4]}")
    env1 = [p.split("=", 1)[0] for p in
            (self_view.get("proc1_environ", {}).get("value") or "").split("\0") if p]
    if set(env1) != set(SANDBOX_ENV_EXPECTED):
        v.fail(f"pid 1 environ keys {sorted(env1)}")
    for name in ("proc_net_tcp", "proc_net_unix"):
        rows = (self_view.get(name, {}).get("value") or "").strip().splitlines()
        if len(rows) > 1:
            v.fail(f"{name} has {len(rows) - 1} entries")
    if self_view.get("dev_shm", {}).get("value"):
        v.fail(f"/dev/shm not empty: {self_view['dev_shm']['value']}")

    n_allowed = 0
    for section in ("reads", "writes", "net"):
        for what, outcome in (survey.get(section) or {}).items():
            if outcome.get("ok"):
                v.fail(f"{section} succeeded: {what}")
            else:
                n_allowed += 1

    blob = json.dumps(report, sort_keys=True)
    for name, token in (canaries or {}).items():
        if token and token in blob:
            v.fail(f"canary {name} visible to consumer")
    lowered = blob.lower()
    for needle in LEAKY_SUBSTRINGS:
        if needle.lower() in lowered:
            v.fail(f"private substring {needle!r} visible to consumer")

    if report.get("ticks") != result.n_ticks:
        v.fail(f"consumer saw {report.get('ticks')} of {result.n_ticks} ticks")
    if report.get("protocol_error"):
        v.fail(f"consumer protocol error {report['protocol_error']}")

    v.measured = {
        "denied_accesses": n_allowed,
        "consumer_ticks": report.get("ticks"),
        "consumer_max_rss_kib": report.get("max_rss_kib"),
        "root": sorted(root),
        "mounts_lines": len((survey.get("mounts", {}).get("value") or "").splitlines()),
    }
    return v


def pair_repetition(a: SessionResult, b: SessionResult, protocol: Protocol) -> Verdict:
    """Same lock, same world, twice: static hash exact, final pose within 2 mm."""
    v = Verdict(ok=True)
    if a.effective_sha256 != b.effective_sha256:
        v.fail("effective sdf hash differs between repeats")
    if not a.ok or not b.ok:
        v.fail("a repeat did not complete")
        return v
    tol_um = int(protocol.criteria["pair_pose_error_mm"]) * 1000
    delta = [abs(x - y) for x, y in zip(a.frames[-1]["rig_um"], b.frames[-1]["rig_um"])]
    if max(delta) > tol_um:
        v.fail(f"final pose delta {max(delta) / 1000.0:.3f} mm > "
               f"{protocol.criteria['pair_pose_error_mm']} mm")
    v.measured = {"delta_um": delta, "max_delta_mm": round(max(delta) / 1000.0, 4)}
    return v
