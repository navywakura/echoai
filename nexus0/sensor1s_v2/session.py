"""SENSOR-1S v2 episode: v1's session, copied with three references changed
(runner, consumer, model); the runner now starts the sensor channel in its
own process.

One SENSOR-1S episode: the v6 flight with a sensor tap on the private
side, and the caged consumer at the far end of a FIFO the host forwards.

The frozen FLIGHT-1S session collects the container's stdout at the end,
which cannot carry a live sensor stream; this one streams. The flight
itself — config, runner, parameters, parsing of the episode — is the
frozen one. What is new: the effective world gains the rendering system
(both hashes are kept), the rig model is mounted, a FIFO leaves the
container, and the host forwards frames byte for byte to the consumer
while scanning them for canaries. The host never alters a frame.
"""
import hashlib
import json
import os
import select
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from echoai.nexus0.flight1s.session import Episode, _keep_ulog
from echoai.nexus0.flight1s.worldbuild import build_effective, spawn_pose
from echoai.nexus0.flight1s.runtime import RUNNER as FROZEN_RUNNER, podman
from echoai.nexus0.flight1s_v6.campaign import RUNNER as V6_RUNNER
from echoai.nexus0.sim3 import sandbox
from echoai.nexus0.sim3.canon import sha256_bytes
from echoai.nexus0.sensor1s import model

HERE = Path(__file__).resolve().parent
TAP = HERE/'assets/sensor_runner.py'
CONSUMER = model.HERE/'assets/consumer.py'
SENSORS_PLUGIN = (b'    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">\n'
                  b'      <render_engine>ogre2</render_engine>\n    </plugin>\n')


def effective_world(package):
    """The frozen flight world plus one rendering system, inserted at a fixed place."""
    source = (package.path/package.manifest['sdf']['path']).read_bytes()
    base = build_effective(source, package.sdf.sha256)
    i = base.data.find(b'    <magnetic_field>')
    data = base.data[:i] + SENSORS_PLUGIN + base.data[i:]
    return dict(data=data, sha256=sha256_bytes(data), base_sha256=base.sha256,
                source_sha256=base.source_sha256, world_name=base.world_name,
                systems=list(base.systems) + ['gz::sim::systems::Sensors'])


def canaries(gen):
    """Strings that would only appear if private identity leaked."""
    p = gen.package
    out = {gen.package_id, p.sdf.sha256[:16], str(p.manifest.get('name', ''))}
    out |= {m.name for m in p.sdf.models}
    return sorted(x for x in out if len(x) >= 4)


class Forwarder(threading.Thread):
    def __init__(self, fifo, sock, marks):
        super().__init__(daemon=True)
        self.fifo, self.sock, self.marks = fifo, sock, [m.encode() for m in marks]
        self.done = threading.Event()
        self.headers, self.hits, self.frames, self.bytes = [], set(), 0, 0
        self.digest = hashlib.sha256()
        self.wire_sha, self.wire_len = [], []
        self.error = None

    def run(self):
        fd = os.open(self.fifo, os.O_RDONLY | os.O_NONBLOCK)
        buf, opened = bytearray(), False
        try:
            while True:
                ready, _, _ = select.select([fd], [], [], 0.2)
                chunk = os.read(fd, 1 << 20) if ready else b''
                if chunk:
                    opened = True
                    buf += chunk
                    self.consume(buf)
                elif opened and ready:
                    break                                   # writer closed
                elif self.done.is_set():
                    break
                else:
                    time.sleep(0.05)
        except OSError as exc:
            self.error = repr(exc)[:200]
        finally:
            os.close(fd)
            if buf:
                self.error = self.error or f'trailing_bytes:{len(buf)}'

    def consume(self, buf):
        while len(buf) >= 4:
            hlen = int.from_bytes(buf[:4], 'big')
            if len(buf) < 8 + hlen:
                return
            plen = int.from_bytes(buf[4+hlen:8+hlen], 'big')
            end = 8 + hlen + plen
            if len(buf) < end:
                return
            frame = bytes(buf[:end])
            del buf[:end]
            header = frame[4:4+hlen]
            payload = frame[8+hlen:]
            self.digest.update(frame[:4] + header)
            self.headers.append(header.decode())
            self.wire_sha.append(sha256_bytes(payload))
            self.wire_len.append(len(payload))
            for m in self.marks:
                if m in header or m in payload:
                    self.hits.add(m.decode())
            self.frames += 1
            self.bytes += len(frame)
            try:
                self.sock.sendall(frame)
            except OSError as exc:
                self.error = self.error or 'consumer:'+repr(exc)[:100]


def run_episode(flight_runtime, sim3_runtime, gen, cfg, spec, *, condition, label, root):
    """Fly one episode; return the flight Episode plus the sensor evidence."""
    pm = podman()
    world = effective_world(gen.package)
    pose, _ = spawn_pose(gen.package, cfg['body'])
    ep = Episode(ok=False, condition=condition, label=label, effective_sha256=world['sha256'],
                 source_sha256=world['source_sha256'], systems=world['systems'])
    work = Path(tempfile.mkdtemp(prefix='sensor1s-'))
    out = work/'out'
    out.mkdir()
    sensors = dict(label=label, world=dict((k, world[k]) for k in ('sha256', 'base_sha256', 'source_sha256')))
    try:
        (work/'world.sdf').write_bytes(world['data'])
        for f in (FROZEN_RUNNER, V6_RUNNER, TAP):
            shutil.copy2(f, work/f.name)
        (work/'sensor1s.json').write_text(json.dumps(spec, sort_keys=True))
        shutil.copytree(model.OUT, work/'models')
        os.mkfifo(out/'sensors.fifo', 0o600)
        consumer = sandbox.spawn(sim3_runtime, probe_path=CONSUMER)
        fwd = Forwarder(str(out/'sensors.fifo'), consumer.sock, canaries(gen))
        fwd.start()
        run_cfg = dict(world_name=world['world_name'], world_path='/flight/world.sdf',
                       model=cfg['body']['model'], airframe=int(cfg['body']['airframe']),
                       spawn_pose=pose, workdir='/out/wd', condition=condition,
                       stages=dict(cfg['stages']), timeouts=cfg['timeouts'], rates=cfg['rates'],
                       disturbance=dict(link=cfg['disturbance']['link'],
                                        axis=list(cfg['disturbance']['axis']),
                                        force_mn=int(cfg['disturbance']['force_mn'])))
        env = {'FLIGHT1S_PARAMETERS': json.dumps(cfg['px4_parameters'], sort_keys=True),
               'FLIGHT1S_HEARTBEAT_S': '30'}
        argv = [pm, 'run', '--rm', '--pull=never', '--network=none', '--security-opt',
                'label=disable', '--tmpfs', '/tmp', '-e', 'HOME=/out/wd',
                '-v', f'{work}:/flight:ro', '-v', f'{out}:/out']
        for k, v in sorted(env.items()):
            argv += ['-e', f'{k}={v}']
        argv += [flight_runtime.image, 'python3', '/flight/'+TAP.name, json.dumps(run_cfg, sort_keys=True)]
        t0 = time.monotonic()
        timeout = int(cfg['timeouts']['episode_s']) + 120
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=timeout)
            stdout, rc = proc.stdout, proc.returncode
            stderr = proc.stderr
        except subprocess.TimeoutExpired as exc:
            stdout, rc, stderr = exc.stdout or b'', None, exc.stderr or b''
            ep.cause = {'code': 'episode_timeout', 'detail': f'{timeout}s'}
        wall = time.monotonic() - t0
        fwd.done.set()
        fwd.join(timeout=60)
        try:
            consumer.sock.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        try:
            _, report = consumer.process.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            consumer.process.kill()
            _, report = consumer.process.communicate()
        consumer.close()
        for line in stdout.decode(errors='replace').splitlines():
            line = line.strip()
            if not line.startswith('{'):
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get('ev') == 'episode':
                ep.ok = bool(msg.get('ok'))
                ep.cause = msg.get('cause')
                ep.samples = msg.get('samples', [])
                ep.sample_columns = msg.get('sample_columns', [])
                ep.stage_marks = msg.get('stage_marks', {})
                ep.driver_events = msg.get('driver_events', [])
                ep.wrench_published = int(msg.get('wrench_published', 0))
                ep.force_n = msg.get('force_n', [])
                ep.body_pose_updates = int(msg.get('body_pose_updates', 0))
                ep.clock_samples = int(msg.get('clock_samples', 0))
                ep.px4_tail = msg.get('px4_tail', [])[-20:]
                _keep_ulog(msg.get('ulog'), out, root/'ulogs', label, ep)
            else:
                ep.events.append(msg)
        if not ep.sample_columns and ep.cause is None:
            ep.cause = {'code': 'runner_no_episode', 'detail': stderr.decode(errors='replace')[-300:]}
        sim_ns = ep.samples[-1][0] - ep.samples[0][0] if ep.samples else 0
        ep.metrics = dict(wall_s=round(wall, 2), sim_s=round(sim_ns/1e9, 3),
                          rtf=round(sim_ns/1e9/wall, 3) if wall else None, n_samples=len(ep.samples),
                          pose_updates=ep.body_pose_updates, clock_samples=ep.clock_samples,
                          container_returncode=rc)
        private = out/'private.jsonl'
        (root/'private').mkdir(parents=True, exist_ok=True)
        (root/'transcript').mkdir(parents=True, exist_ok=True)
        kept = root/'private'/(label+'.jsonl')
        if private.exists():
            shutil.copyfile(private, kept)
        transcript = root/'transcript'/(label+'.jsonl')
        transcript.write_text(''.join(json.dumps(dict(h=h, wire=w, len=n)) + '\n'
                                      for h, w, n in zip(fwd.headers, fwd.wire_sha, fwd.wire_len)))
        try:
            tally = json.loads(report.decode().strip().splitlines()[-1])
        except (ValueError, IndexError):
            tally = dict(error='no_consumer_report', stderr=report.decode(errors='replace')[-300:])
        sensors.update(
            private=str(kept.relative_to(model.HERE.parents[1])) if kept.exists() else None,
            private_sha256=sha256_bytes(kept.read_bytes()) if kept.exists() else None,
            transcript=str(transcript.relative_to(model.HERE.parents[1])),
            transcript_sha256=sha256_bytes(transcript.read_bytes()),
            forwarder=dict(frames=fwd.frames, bytes=fwd.bytes, header_digest=fwd.digest.hexdigest(),
                           canary_hits=sorted(fwd.hits), error=fwd.error),
            consumer=tally, consumer_returncode=consumer.process.returncode)
        return ep, sensors
    finally:
        shutil.rmtree(work, ignore_errors=True)
