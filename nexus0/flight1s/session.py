"""One flight episode, supervised from the host.

The host never touches Gazebo, PX4 or MAVLink. It builds the effective
world, starts exactly one container, hands the runner a config that
contains a world file, a spawn pose and the frozen script — and reads
back JSON lines. The split, the seed, the package id, the roles and the
condition ordering stay here.

``condition`` does cross the boundary, because the runner has to know
whether to publish a wrench. It is the manipulated variable of the
experiment, not an identity: it takes the same two values in every
world, and the ordering that decides which episode gets which is derived
from a seed the runner never sees.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.pkg import Package
from echoai.nexus0.flight1s.runtime import MODEL_DIR, RUNNER, Runtime, podman
from echoai.nexus0.flight1s.worldbuild import build_effective, spawn_pose

CONDITIONS = ("nominal", "perturbed")


@dataclass
class Episode:
    ok: bool
    condition: str
    label: str
    cause: Optional[Dict] = None
    samples: List[List[int]] = field(default_factory=list)
    sample_columns: List[str] = field(default_factory=list)
    stage_marks: Dict = field(default_factory=dict)
    driver_events: List[Dict] = field(default_factory=list)
    wrench_published: int = 0
    force_n: List[float] = field(default_factory=list)
    body_pose_updates: int = 0
    clock_samples: int = 0
    effective_sha256: str = ""
    source_sha256: str = ""
    systems: List[str] = field(default_factory=list)
    ulog_sha256: Optional[str] = None
    ulog_bytes: int = 0
    px4_tail: List[str] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    events: List[Dict] = field(default_factory=list)

    def trace(self) -> Dict:
        return {
            "label": self.label,
            "condition": self.condition,
            "ok": self.ok,
            "cause": self.cause,
            "effective_sha256": self.effective_sha256,
            "source_sha256": self.source_sha256,
            "systems": self.systems,
            "stage_marks": self.stage_marks,
            "sample_columns": self.sample_columns,
            "samples": self.samples,
            "driver_events": self.driver_events,
            "wrench_published": self.wrench_published,
            "force_n": self.force_n,
            "body_pose_updates": self.body_pose_updates,
            "clock_samples": self.clock_samples,
            "ulog_sha256": self.ulog_sha256,
            "ulog_bytes": self.ulog_bytes,
            "events": self.events,
            "metrics": self.metrics,
            "px4_tail": self.px4_tail,
        }


def run_episode(runtime: Runtime, package: Package, protocol: Dict, *,
                condition: str, label: str,
                force_mn: Optional[int] = None,
                ulog_dir: Optional[Path] = None,
                runner_path: Optional[Path] = None,
                extra_env: Optional[Dict[str, str]] = None) -> Episode:
    """Fly one episode. One container, one process tree, nothing reused."""
    runtime.require()
    if condition not in CONDITIONS:
        raise Sim3Error("flight_condition", condition)
    pm = podman()
    if pm is None:
        raise Sim3Error("podman_missing", "preflight said available; it is not")

    body = protocol["body"]
    stages = dict(protocol["stages"])
    # Only the three fields the runner uses. The protocol's own
    # ``swept_on_split`` records where the magnitude was calibrated; it is
    # the same word in every world, but it is still a word about splits and
    # it has no business inside the container.
    src = protocol["disturbance"]
    disturbance = {
        "link": src["link"],
        "axis": list(src["axis"]),
        "force_mn": int(force_mn if force_mn is not None else src["force_mn"]),
    }

    source = (package.path / package.manifest["sdf"]["path"]).read_bytes()
    effective = build_effective(source, package.sdf.sha256)
    pose, _ = spawn_pose(package, body)

    episode = Episode(ok=False, condition=condition, label=label,
                      effective_sha256=effective.sha256,
                      source_sha256=effective.source_sha256,
                      systems=effective.systems)

    workdir = Path(tempfile.mkdtemp(prefix="flight1s-"))
    out_dir = workdir / "out"
    out_dir.mkdir()
    try:
        (workdir / "world.sdf").write_bytes(effective.data)
        # The trusted runner always travels: the mutant backends import it
        # and patch one method, so what they change stays visible as a diff
        # against a file that is in the code inventory.
        shutil.copy2(RUNNER, workdir / RUNNER.name)
        runner = Path(runner_path or RUNNER)
        if runner != RUNNER:
            shutil.copy2(runner, workdir / runner.name)

        cfg = {
            "world_name": effective.world_name,
            "world_path": "/flight/world.sdf",
            "model": body["model"],
            "airframe": int(body["airframe"]),
            "spawn_pose": pose,
            "workdir": "/out/wd",
            "condition": condition,
            "stages": stages,
            "timeouts": protocol["timeouts"],
            "disturbance": disturbance,
            "rates": protocol["rates"],
        }
        argv = [
            pm, "run", "--rm", "--pull=never", "--network=none",
            "--security-opt", "label=disable",
            "--tmpfs", "/tmp", "-e", "HOME=/out/wd",
            "-v", f"{workdir}:/flight:ro", "-v", f"{out_dir}:/out",
        ]
        for key, value in sorted((extra_env or {}).items()):
            argv += ["-e", f"{key}={value}"]
        argv += [runtime.image, "python3", f"/flight/{runner.name}",
                 json.dumps(cfg, sort_keys=True)]

        timeout_s = int(protocol["timeouts"]["episode_s"])
        t0 = time.monotonic()
        try:
            proc = subprocess.run(argv, capture_output=True,
                                  timeout=timeout_s + 120)
        except subprocess.TimeoutExpired as exc:
            # A backend whose clock never advances hangs the stage loop.
            # That is a detection, not a crash: report it as one.
            episode.cause = {"code": "episode_timeout",
                             "detail": f"{timeout_s + 120}s"}
            episode.metrics = {"wall_s": round(time.monotonic() - t0, 2),
                               "timed_out": True}
            episode.events.append({"ev": "timeout",
                                   "stdout_tail": (exc.stdout or b"")
                                   .decode(errors="replace")[-300:]})
            return episode
        wall_s = time.monotonic() - t0

        for line in proc.stdout.decode(errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("ev") == "episode":
                episode.ok = bool(msg.get("ok"))
                episode.cause = msg.get("cause")
                episode.samples = msg.get("samples", [])
                episode.sample_columns = msg.get("sample_columns", [])
                episode.stage_marks = msg.get("stage_marks", {})
                episode.driver_events = msg.get("driver_events", [])
                episode.wrench_published = int(msg.get("wrench_published", 0))
                episode.force_n = msg.get("force_n", [])
                episode.body_pose_updates = int(msg.get("body_pose_updates", 0))
                episode.clock_samples = int(msg.get("clock_samples", 0))
                episode.px4_tail = msg.get("px4_tail", [])[-20:]
                _keep_ulog(msg.get("ulog"), out_dir, ulog_dir, label, episode)
            else:
                episode.events.append(msg)

        if not episode.sample_columns and episode.cause is None:
            episode.cause = {"code": "runner_no_episode",
                             "detail": proc.stderr.decode(errors="replace")[-300:]}
        sim_ns = 0
        if episode.samples:
            sim_ns = episode.samples[-1][0] - episode.samples[0][0]
        episode.metrics = {
            "wall_s": round(wall_s, 2),
            "sim_s": round(sim_ns / 1e9, 3),
            "rtf": round((sim_ns / 1e9) / wall_s, 3) if wall_s else None,
            "n_samples": len(episode.samples),
            "pose_updates": episode.body_pose_updates,
            "clock_samples": episode.clock_samples,
            "container_returncode": proc.returncode,
        }
        return episode
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _keep_ulog(path_in_container: Optional[str], out_dir: Path,
               ulog_dir: Optional[Path], label: str, episode: Episode) -> None:
    """Keep PX4's own flight log as independent evidence, hashed."""
    if not path_in_container:
        return
    rel = str(path_in_container).replace("/out/", "", 1)
    src = out_dir / rel
    if not src.exists():
        return
    raw = src.read_bytes()
    episode.ulog_sha256 = sha256_bytes(raw)
    episode.ulog_bytes = len(raw)
    if ulog_dir is not None:
        Path(ulog_dir).mkdir(parents=True, exist_ok=True)
        (Path(ulog_dir) / f"{label}.ulg").write_bytes(raw)
