"""DYNAMIC-1: the channel of PATTERN-1R, copied; it starts the mover runner.

PATTERN-1R: GROUND-1 v2's channel, copied. It starts the survey runner
(the frozen stage script plus bounded goals) instead of the frozen one, and
nothing else changes.

GROUND-1 v2: SENSOR-1S v2's channel, copied; the sender reads its clock
under the queue lock. GROUND-1 v1 went red on a message queued between the
clock read and the lock, stamped 1 ms before its arrival.

SENSOR-1S v2 private side: the v6 flight in one process, the sensor
channel in another.

v1 ran tap, injector and adapter as threads inside the flight runner.
Its one red record was an adapter stall at PX4 startup. Instrumented
development flights (lab/sensor1s-v2/dev/diag1, diag2) found two causes:
FIFO writes of 230 KB camera frames blocking on a 64 KiB pipe, and the
sender thread not being scheduled while the flight process was busy.
v2 moves the whole channel into its own process, with its own interpreter,
its own subscriptions to Gazebo's clock and true pose, and a pipe large
enough for whole frames. Tap, injector and adapter logic are v1's.

    python3 sensor_runner.py <flight config json>        flight + channel
    python3 sensor_runner.py --channel <channel json>    channel only

Runs inside the flight container. Nothing reaches the consumer but the
frames; truth (body pose) goes to the private log only.
"""
import fcntl
import hashlib
import heapq
import json
import math
import os
import signal
import struct
import subprocess
import sys
import threading
import time

sys.path.insert(0, '/flight')
import gz.math7                                   # noqa: E402,F401
from gz.msgs10.clock_pb2 import Clock             # noqa: E402
from gz.msgs10.image_pb2 import Image             # noqa: E402
from gz.msgs10.imu_pb2 import IMU                 # noqa: E402
from gz.msgs10.laserscan_pb2 import LaserScan     # noqa: E402
from gz.msgs10.pose_v_pb2 import Pose_V           # noqa: E402
from gz.transport13 import Node                   # noqa: E402

SPEC = json.loads(open('/flight/sensor1s.json').read())
MUTANT = SPEC.get('mutant')
TYPES = {'imu': IMU, 'rgb': Image, 'depth': Image, 'lidar': LaserScan}
SWAP = {'depth': 'lidar', 'lidar': 'depth'}
F_SETPIPE_SZ, F_GETPIPE_SZ = 1031, 1032
PIPE_BYTES = 1 << 20                              # holds four 230 KB camera frames


def stamp_ns(msg):
    return int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nsec)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(source, msg):
    """Payload bytes, shape, format, and the sample the evaluator keeps."""
    if source == 'imu':
        a, w = msg.linear_acceleration, msg.angular_velocity
        v = [a.x, a.y, a.z, w.x, w.y, w.z]
        return struct.pack('<6d', *v), [6], 'f64', v
    if source == 'lidar':
        r = list(msg.ranges)
        return (struct.pack('<%df' % len(r), *r), [len(r)], 'f32',
                dict(angle_min=msg.angle_min, angle_step=msg.angle_step, ranges=r))
    if source == 'depth':
        w, h = msg.width, msg.height
        row = h // 2
        return (bytes(msg.data), [h, w], 'f32',
                dict(row=row, values=list(struct.unpack_from('<%df' % w, msg.data, row*w*4))))
    return bytes(msg.data), [msg.height, msg.width, 3], 'rgb8', None


def quat_to_rpy(w, x, y, z):
    """The frozen runner's conversion, so the private truth means the same."""
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    pitch = math.asin(max(-1.0, min(1.0, 2.0 * (w * y - z * x))))
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return roll, pitch, yaw


class Truth:
    """The channel's own clock and true body pose. Private side only."""

    def __init__(self, world, instance):
        self.world, self.instance = world, instance
        self.node = Node()
        self.lock = threading.Lock()
        self.sim_ns, self.body, self.seen = 0, None, 0
        self.node.subscribe(Clock, f'/world/{world}/clock', self._clock)
        self.node.subscribe(Pose_V, f'/world/{world}/dynamic_pose/info', self._pose)

    def _clock(self, msg):
        with self.lock:
            self.sim_ns = int(msg.sim.sec) * 1_000_000_000 + int(msg.sim.nsec)

    def _pose(self, msg):
        stamp = stamp_ns(msg)
        for p in msg.pose:
            if p.name == self.instance:
                q = p.orientation
                body = (stamp, p.position.x, p.position.y, p.position.z) + quat_to_rpy(q.w, q.x, q.y, q.z)
                with self.lock:
                    self.body, self.seen = body, self.seen + 1
                return

    def now_ns(self):
        with self.lock:
            return self.sim_ns

    def snapshot(self):
        with self.lock:
            return self.body, self.sim_ns, self.seen


class Tap:
    def __init__(self, backend, instance):
        self.backend = backend
        self.lock = threading.Lock()
        self.log = open(SPEC['private_log'], 'w', buffering=1 << 20)
        self.raw = {s: 0 for s in SPEC['sources']}
        self.genuine = {s: None for s in SPEC['sources']}
        self.last_release = {s: 0 for s in SPEC['sources']}
        self.adapter = {s: dict(seq=0, last_stamp=None) for s in SPEC['sources']}
        self.pending, self.order = [], 0
        self.faults = {}
        for source, items in SPEC['faults'].items():
            for f in items:
                for i in range(f['count']):
                    self.faults[(source, f['start']+i)] = f
        self.stop = threading.Event()
        topics = {s: v['topic'].format(world=backend.world, instance=instance)
                  for s, v in SPEC['sources'].items()}
        self.write(dict(k='start', topics=topics, mutant=MUTANT, process='channel'))
        for source, topic in topics.items():
            ok = backend.node.subscribe(TYPES[source], topic, self.callback(source))
            self.write(dict(k='subscribe', src=source, ok=bool(ok)))
        self.sender = threading.Thread(target=self.send_loop, daemon=True)
        self.sender.start()

    def write(self, entry):
        self.log.write(json.dumps(entry, sort_keys=True) + '\n')

    def callback(self, source):
        def cb(msg):
            try:
                self.ingest(source, msg)
            except Exception as exc:  # noqa: BLE001  - logged, never silent
                with self.lock:
                    self.write(dict(k='error', src=source, error=repr(exc)[:200]))
        return cb

    def ingest(self, source, msg):
        arrive = self.backend.now_ns()          # sim time the message reached the tap
        stamp = stamp_ns(msg)
        payload, shape, fmt, sample = encode(source, msg)
        body = self.backend.snapshot()[0] if source in ('lidar', 'depth') else None
        with self.lock:
            n = self.raw[source]
            self.raw[source] += 1
            self.write(dict(k='raw', src=source, n=n, stamp=stamp, arrive=arrive,
                            sha=sha(payload), sample=sample, body=body))
            fault = self.faults.get((source, n))
            kind = fault['kind'] if fault else None
            if kind == 'drop':
                self.write(dict(k='inject', src=source, n=n, kind='drop'))
                return
            if kind == 'freeze':
                if self.genuine[source] is None:
                    self.write(dict(k='inject', src=source, n=n, kind='freeze_skipped'))
                    return
                stamp, payload, shape, fmt, _ = self.genuine[source]
                self.write(dict(k='inject', src=source, n=n, kind='freeze', stamp=stamp))
            else:
                self.genuine[source] = (stamp, payload, shape, fmt, n)
            delay = fault['delay_ns'] if kind == 'delay' else 0
            if delay:
                self.write(dict(k='inject', src=source, n=n, kind='delay', delay_ns=delay))
            if kind == 'corrupt':
                self.write(dict(k='inject', src=source, n=n, kind='corrupt'))
            # A delayed message holds the ones behind it: order per source is kept.
            release = max(stamp + delay, self.last_release[source])
            self.last_release[source] = release
            heapq.heappush(self.pending, (release, self.order, source, n, stamp, payload,
                                          shape, fmt, kind == 'corrupt', kind == 'freeze'))
            self.order += 1

    def adapt(self, item, now):
        _, _, source, n, stamp, payload, shape, fmt, corrupt, frozen = item
        spec, st = SPEC['sources'][source], self.adapter[source]
        last = st['last_stamp']
        if last is not None and stamp <= last:
            status, gap = 'stale', 0
        else:
            gap = 0 if last is None else max(0, round((stamp - last) / spec['period_ns']) - 1)
            status = 'ok'
            st['last_stamp'] = stamp
        capture = stamp
        if MUTANT == 'delivery_stamp':
            capture = now
        elif MUTANT == 'wall_clock':
            capture = time.time_ns()
        if MUTANT == 'hide_loss':
            gap = 0
        if MUTANT == 'fresh_stale':
            status = 'ok'
        noise_ref = spec['noise_ref']
        if MUTANT == 'noise_lie' and source in SWAP:
            noise_ref = source + ':gauss-5mm'
        label = SWAP.get(source, source) if MUTANT == 'source_swap' else source
        header = dict(v=2, source=label, seq=st['seq'], capture_ns=capture, delivered_ns=now,
                      gap=gap, status=status, noise_ref=noise_ref, shape=shape, format=fmt,
                      payload_len=len(payload), payload_sha256=sha(payload))
        if MUTANT == 'leak_pose':
            body = self.backend.snapshot()[0]
            header['pose'] = [round(x, 3) for x in body[1:4]] if body else None
        st['seq'] += 1
        wire = bytes([payload[0] ^ 0xFF]) + payload[1:] if corrupt and payload else payload
        hb = json.dumps(header, sort_keys=True, separators=(',', ':')).encode()
        with self.lock:
            self.write(dict(k='send', src=source, n=n, frozen=frozen, corrupt=corrupt,
                            header=header))
        return len(hb).to_bytes(4, 'big') + hb + len(wire).to_bytes(4, 'big') + wire

    def send_loop(self):
        fd = os.open(SPEC['fifo'], os.O_WRONLY)        # waits for the host's reader
        try:
            fcntl.fcntl(fd, F_SETPIPE_SZ, PIPE_BYTES)
        except OSError as exc:
            with self.lock:
                self.write(dict(k='diag', what='pipe_resize_failed', error=repr(exc)[:100]))
        with self.lock:
            self.write(dict(k='diag', what='pipe', bytes=fcntl.fcntl(fd, F_GETPIPE_SZ)))
        out = os.fdopen(fd, 'wb', buffering=0)
        last = time.monotonic()
        try:
            while not self.stop.is_set():
                t0 = time.monotonic()
                batch = []
                with self.lock:
                    # GROUND-1 v2: the clock is read under the queue lock, so every
                    # message popped here was queued before `now`: delivered >= arrive.
                    now = self.backend.now_ns()
                    while self.pending and self.pending[0][0] <= now:
                        batch.append(heapq.heappop(self.pending))
                wt = 0.0
                for item in batch:
                    frame = self.adapt(item, now)
                    ws = time.monotonic()
                    out.write(frame)
                    wt += time.monotonic() - ws
                if t0 - last > 0.004 or wt > 0.004:     # kept as evidence, never judged
                    with self.lock:
                        self.write(dict(k='diag', what='sender', wall=t0, gap_ms=(t0-last)*1e3,
                                        write_ms=wt*1e3, frames=len(batch), clock=now))
                last = time.monotonic()
                if not batch:
                    time.sleep(0.0005)
        except BrokenPipeError:
            with self.lock:
                self.write(dict(k='error', src=None, error='fifo_broken'))
        finally:
            out.close()

    def close(self):
        self.stop.set()
        self.sender.join(timeout=20)
        with self.lock:
            for item in sorted(self.pending):
                self.write(dict(k='undelivered', src=item[2], n=item[3], release=item[0]))
            self.write(dict(k='end', raw=self.raw, sender_alive=self.sender.is_alive()))
            self.log.close()


def channel(cfg):
    done = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: done.set())
    tap = Tap(Truth(cfg['world'], cfg['instance']), cfg['instance'])
    while not done.wait(0.2):
        pass
    tap.close()
    return 0


def flight(config):
    import flightrunner_mover as original            # FLIGHT-1S script + the mover
    def deadline():
        original.emit({'ev': 'watchdog_timeout', 'clock': 'wall'})
        os._exit(124)
    watchdog = threading.Timer(config['timeouts']['episode_s'], deadline)
    watchdog.daemon = True
    watchdog.start()
    instance = config['model'] + '_0'
    err = open('/out/channel.err', 'wb')
    ch = subprocess.Popen([sys.executable, os.path.abspath(__file__), '--channel',
                           json.dumps(dict(world=config['world_name'], instance=instance))],
                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=err)
    original.PX4_MODELS = original.PX4_MODELS + ':/flight/models'
    original.Driver = original.ConfiguredDriver
    # PX4 v1.15 spawns the model named by PX4_SIM_MODEL, which the frozen
    # runner fixes to gz_x500. Only PX4's environment is changed, only here.
    _popen = original.subprocess.Popen
    def _px4_popen(argv, *a, **kw):
        if argv and argv[0] == original.PX4_BIN and kw.get('env') is not None:
            kw['env'] = dict(kw['env'], PX4_SIM_MODEL='gz_' + config['model'])
        return _popen(argv, *a, **kw)
    original.subprocess.Popen = _px4_popen
    rc = 1
    try:
        rc = original.main()
    finally:
        watchdog.cancel()
        ch.send_signal(signal.SIGTERM)
        try:
            ch.wait(timeout=30)
        except subprocess.TimeoutExpired:
            ch.kill()
        err.close()
    return rc


if __name__ == '__main__':
    if sys.argv[1] == '--channel':
        sys.exit(channel(json.loads(sys.argv[2])))
    sys.exit(flight(json.loads(sys.argv[1])))
