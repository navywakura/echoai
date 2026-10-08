"""One episode: Gazebo on the private side, a probe on the public side.

The supervisor is the only place the two ever meet, and the only thing
that crosses is a clock. A tick is literally three fields:

    {"v":1,"seq":<n>,"sim_time_ns":<observed>}

``sim_time_ns`` is read out of the running backend. If Gazebo does not
start, or stops advancing, there is no tick to send: the supervisor has
no code path that manufactures one. That is the whole point of putting
the stepping behind a request/response instead of a timer.

Everything else the run produces — poses, model entities, contacts,
package identity, split, seed — stays on the private side and goes to
the evaluator, never back down the socket.
"""

from __future__ import annotations

import json
import os
import select
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from echoai.nexus0.sim3 import sandbox
from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.pkg import Package, Protocol
from echoai.nexus0.sim3.rig import CONTACT_TOPIC, RIG_MODEL, build_effective
from echoai.nexus0.sim3.runtime import RUNNER, Runtime, _podman

MAX_TICK_BYTES = 256


@dataclass
class SessionResult:
    ok: bool
    cause: Optional[Dict] = None
    frames: List[Dict] = field(default_factory=list)
    tick_transcript_sha256: str = ""
    n_ticks: int = 0
    effective_sha256: str = ""
    source_sha256: str = ""
    systems: List[str] = field(default_factory=list)
    gz_report: Dict = field(default_factory=dict)
    consumer: Dict = field(default_factory=dict)
    metrics: Dict = field(default_factory=dict)
    initial: Dict = field(default_factory=dict)
    model_poses_um: Dict = field(default_factory=dict)
    gravity_um: List[int] = field(default_factory=list)
    canaries: Dict = field(default_factory=dict)
    label: str = "bench"

    def trace(self) -> Dict:
        """The artefact the auditor recomputes from. Private-side truth."""
        return {
            "label": self.label,
            "effective_sha256": self.effective_sha256,
            "source_sha256": self.source_sha256,
            "systems": self.systems,
            "n_ticks": self.n_ticks,
            "tick_transcript_sha256": self.tick_transcript_sha256,
            "initial": self.initial,
            "frames_um": [[f["sim_time_ns"], *f["rig_um"]] for f in self.frames],
            "model_poses_um": self.model_poses_um,
            "gravity_um": self.gravity_um,
            "gz_report": self.gz_report,
            "consumer": self.consumer,
            "metrics": self.metrics,
            "cause": self.cause,
            "ok": self.ok,
        }


class _LineReader:
    def __init__(self, stream) -> None:
        self.stream = stream

    def read(self, timeout: float) -> Optional[str]:
        ready, _, _ = select.select([self.stream], [], [], timeout)
        if not ready:
            return None
        line = self.stream.readline()
        if not line:
            return ""
        return line.decode("utf-8", "replace").strip()


def _drain(stream, sink: List[str]) -> threading.Thread:
    def run() -> None:
        for line in iter(stream.readline, b""):
            sink.append(line.decode("utf-8", "replace").rstrip())
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


def run_episode(runtime: Runtime, package: Package, protocol: Protocol, *,
                canaries: Optional[Dict[str, str]] = None,
                probe_path: Optional[Path] = None,
                probe_env: Optional[Dict[str, str]] = None,
                label: str = "bench",
                steps: Optional[int] = None,
                rig_centre_mm: Optional[Sequence[int]] = None,
                runner_path: Optional[Path] = None,
                tick_mutation: Optional[Dict] = None) -> SessionResult:
    """Run one Gazebo episode in lockstep with one sandboxed consumer."""
    runtime.require()
    podman = _podman()
    if podman is None:
        raise Sim3Error("podman_missing", "preflight said available; it is not")

    canaries = dict(canaries or {})
    n_steps = int(steps if steps is not None else protocol.steps)
    step_ns = protocol.step_ns
    ack_timeout = float(protocol.timeouts["ack_s"])
    launch_timeout = float(protocol.timeouts["launch_s"])
    rig = protocol.rig
    centre = list(rig_centre_mm if rig_centre_mm is not None else package.rig_start_mm)

    source_sdf = (package.path / package.manifest["sdf"]["path"]).read_bytes()
    effective = build_effective(source_sdf, package.sdf.sha256, centre,
                                int(rig["radius_mm"]), int(rig["mass_g"]))

    result = SessionResult(ok=False, label=label,
                           effective_sha256=effective.sha256,
                           source_sha256=effective.source_sha256,
                           systems=effective.systems,
                           canaries={k: sha256_bytes(v.encode())[:16]
                                     for k, v in canaries.items()})

    workdir = Path(tempfile.mkdtemp(prefix="sim3-run-"))
    consumer: Optional[sandbox.Consumer] = None
    gz_proc: Optional[subprocess.Popen] = None
    gz_stderr: List[str] = []
    # Hoisted: a run that goes red still has to hand the evaluator what the
    # consumer saw. A refusal the probe made is evidence, not debris.
    consumer_err: List[str] = []
    try:
        (workdir / "world.sdf").write_bytes(effective.data)
        shutil.copy2(RUNNER, workdir / "gzrunner.py")
        entry = "/sim3/gzrunner.py"
        if runner_path is not None:
            # Mutant backends live in their own file next to the trusted
            # one and are named in the run label; nothing here silently
            # changes what a bench run executes.
            shutil.copy2(runner_path, workdir / Path(runner_path).name)
            entry = f"/sim3/{Path(runner_path).name}"

        runner_args = json.dumps({
            "sdf": "/sim3/world.sdf",
            "rig_model": RIG_MODEL,
            "contact_topic": CONTACT_TOPIC,
            # A private token that must never appear on the consumer's side.
            "canary": canaries.get("argv", ""),
        }, sort_keys=True)
        gz_argv = [
            podman, "run", "--rm", "-i", "--pull=never", "--network=none",
            "--read-only",
            "--security-opt", "label=disable",
            # gz-sim writes a cache under $HOME; a read-only rootfs with a
            # tmpfs home keeps the image immutable without segfaulting it.
            "--tmpfs", "/tmp", "--tmpfs", "/home", "-e", "HOME=/home",
            "-e", f"SIM3_CANARY_ENV={canaries.get('env', '')}",
            "-v", f"{workdir}:/sim3:ro",
            runtime.image, "python3", entry, runner_args,
        ]

        t_launch = time.monotonic()
        gz_proc = subprocess.Popen(gz_argv, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        _drain(gz_proc.stderr, gz_stderr)
        reader = _LineReader(gz_proc.stdout)
        line = reader.read(launch_timeout)
        if not line:
            result.cause = {"code": "backend_no_ready",
                            "detail": "\n".join(gz_stderr[-6:])}
            return result
        ready = json.loads(line)
        if ready.get("ev") != "ready" or not ready.get("subscribed"):
            result.cause = {"code": "backend_bad_ready", "detail": line[:300]}
            return result
        launch_s = time.monotonic() - t_launch

        consumer = sandbox.spawn(runtime, probe_path=probe_path,
                                 extra_env=probe_env)
        _drain(consumer.process.stderr, consumer_err)

        transcript = bytearray()
        latencies: List[float] = []
        seq = 0
        t_run = time.monotonic()

        def send_tick(sim_time_ns: int) -> Optional[Dict]:
            nonlocal seq
            payload = {"v": 1, "seq": seq, "sim_time_ns": int(sim_time_ns)}
            if tick_mutation:
                # Only the mutant group passes this. A tick that carries
                # anything beyond the three fields must be refused by the
                # consumer, and the run must go red because of it.
                payload.update(tick_mutation)
            line_ = (json.dumps(payload, separators=(",", ":"),
                                sort_keys=True) + "\n").encode("utf-8")
            if len(line_) > MAX_TICK_BYTES:
                return {"code": "tick_too_long", "detail": str(len(line_))}
            transcript.extend(line_)
            t0 = time.monotonic()
            try:
                consumer.sock.sendall(line_)
            except OSError as exc:
                return {"code": "consumer_gone", "detail": str(exc)}
            ack = _read_ack(consumer.sock, ack_timeout)
            latencies.append(time.monotonic() - t0)
            if ack is None:
                return {"code": "ack_timeout", "detail": f"seq={seq}"}
            if ack != {"v": 1, "ack": seq}:
                return {"code": "ack_mismatch", "detail": json.dumps(ack)[:200]}
            seq += 1
            return None

        last_ns = -1
        for i in range(1, n_steps + 1):
            gz_proc.stdin.write(b'{"cmd":"step"}\n')
            gz_proc.stdin.flush()
            line = reader.read(launch_timeout)
            if not line:
                result.cause = {"code": "backend_stalled", "detail": f"step {i}"}
                return result
            frame = json.loads(line)
            if frame.get("ev") != "frame":
                result.cause = {"code": "backend_error", "detail": line[:300]}
                return result
            if i == 1:
                pre = frame.get("pre") or {}
                observed = int(pre.get("sim_time_ns", -1))
                if observed != step_ns:
                    result.cause = {"code": "backend_step_mismatch",
                                    "detail": f"first pre_update {observed}"}
                    return result
                result.initial = {
                    "sim_time_ns": observed - step_ns,
                    "rig_um": pre["rig_um"],
                    "source": "ecm state at first pre_update, minus one step",
                    "first_pre_update_sim_time_ns": observed,
                }
                result.gravity_um = frame.get("gravity_um", [])
                result.model_poses_um = frame.get("models_um", {})
                bad = send_tick(result.initial["sim_time_ns"])
                if bad:
                    result.cause = bad
                    return result
            now = int(frame["sim_time_ns"])
            if now <= last_ns or (last_ns >= 0 and now - last_ns != step_ns):
                result.cause = {"code": "clock_not_monotonic",
                                "detail": f"{last_ns} -> {now}"}
                return result
            last_ns = now
            result.frames.append({"sim_time_ns": now, "rig_um": frame["rig_um"]})
            bad = send_tick(now)
            if bad:
                result.cause = bad
                return result

        run_s = time.monotonic() - t_run
        gz_proc.stdin.write(b'{"cmd":"report"}\n')
        gz_proc.stdin.flush()
        line = reader.read(30.0)
        result.gz_report = json.loads(line) if line else {}
        gz_proc.stdin.write(b'{"cmd":"quit"}\n')
        gz_proc.stdin.flush()

        consumer.close()
        try:
            consumer.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            consumer.process.kill()
        time.sleep(0.05)
        result.consumer = _consumer_report(consumer_err)
        result.n_ticks = seq
        result.tick_transcript_sha256 = sha256_bytes(bytes(transcript))
        latencies.sort()
        result.metrics = {
            "launch_s": round(launch_s, 3),
            "run_s": round(run_s, 3),
            "sim_s": (n_steps * step_ns) / 1e9,
            "rtf": round((n_steps * step_ns) / 1e9 / run_s, 3) if run_s else None,
            "ack_latency_ms": {
                "p50": round(latencies[len(latencies) // 2] * 1000, 3),
                "p95": round(latencies[int(len(latencies) * 0.95)] * 1000, 3),
                "p99": round(latencies[min(len(latencies) - 1,
                                           int(len(latencies) * 0.99))] * 1000, 3),
                "n": len(latencies),
            },
            "supervisor_max_rss_kib": _self_rss_kib(),
            "gz_max_rss_kib": result.gz_report.get("max_rss_kib"),
            "consumer_max_rss_kib": result.consumer.get("max_rss_kib"),
        }
        result.ok = True
        return result
    finally:
        if consumer is not None:
            consumer.close()
            try:
                consumer.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                consumer.process.kill()
            time.sleep(0.05)
            if not result.consumer:
                result.consumer = _consumer_report(consumer_err)
        if gz_proc is not None:
            try:
                if gz_proc.stdin and not gz_proc.stdin.closed:
                    gz_proc.stdin.close()
            except OSError:
                pass
            try:
                gz_proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                gz_proc.kill()
            for pipe in (gz_proc.stdout, gz_proc.stderr):
                if pipe is not None and not pipe.closed:
                    pipe.close()
        shutil.rmtree(workdir, ignore_errors=True)


def _read_ack(sock: socket.socket, timeout: float) -> Optional[Dict]:
    sock.settimeout(timeout)
    buf = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            chunk = sock.recv(1)
        except (socket.timeout, TimeoutError):
            return None
        except OSError:
            return None
        if not chunk:
            return None
        if chunk == b"\n":
            try:
                return json.loads(bytes(buf).decode("utf-8"))
            except Exception:  # noqa: BLE001
                return {"malformed": bytes(buf)[:80].decode("utf-8", "replace")}
        buf.extend(chunk)
        if len(buf) > MAX_TICK_BYTES:
            return {"oversized": len(buf)}
    return None


def _consumer_report(lines: Sequence[str]) -> Dict:
    for line in reversed(list(lines)):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except Exception:  # noqa: BLE001
                continue
    return {"raw": list(lines)[-5:]}


def _self_rss_kib() -> Optional[int]:
    try:
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:  # noqa: BLE001
        return None
