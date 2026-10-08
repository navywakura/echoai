"""Private Gazebo/PX4 process. Public sensor snapshots out; one WSP in.

Imports frozen backend/driver; no pose write and no navigation route table.
True pose is written only to private.jsonl, never used to generate commands.
"""
import hashlib
import json
import math
import os
import select
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import flightrunner_survey as flight
from gz.msgs10.image_pb2 import Image
from gz.msgs10.laserscan_pb2 import LaserScan
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.boolean_pb2 import Boolean
from gz.transport13 import Node

STEP_MM = 3000
VECTORS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def stamp(msg):
    return msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nsec


class Sensors:
    def __init__(self, backend):
        self.backend = backend
        self.lock = threading.Lock()
        self.data = {}
        self.node = Node()
        self.node.subscribe(LaserScan, '/sensor1s/lidar', self.lidar)
        self.node.subscribe(Image, '/sensor1s/rgb', self.rgb)
        self.node.subscribe(Image, '/sensor1s/depth', self.depth(0))
        self.callbacks = []
        for i in range(1, 4):
            callback = self.depth(i)
            self.callbacks.append(callback)
            self.node.subscribe(Image, f'/compose/depth_{i}', callback)

    def keep(self, name, msg, payload):
        with self.lock:
            self.data[name] = dict(capture_ns=stamp(msg), delivered_ns=self.backend.now_ns(), **payload)

    def lidar(self, msg):
        self.keep('lidar', msg, dict(
            angles_mrad=[round((msg.angle_min+i*msg.angle_step)*1000) for i in range(len(msg.ranges))],
            ranges_mm=[round(r*1000) if math.isfinite(r) and .3 <= r <= 30 else -1 for r in msg.ranges]))

    def depth(self, i):
        yaw = (0, math.pi/2, math.pi, -math.pi/2)[i]
        def callback(msg):
            if msg.width != 160 or msg.height != 120:
                return
            values = struct.unpack_from('<160f', msg.data, 60*160*4)
            focal = 80/math.tan(.8)
            angles = [math.atan((79.5-x)/focal) for x in range(160)]
            self.keep(f'depth{i}', msg, dict(
                angles_mrad=[round(((a+yaw+math.pi) % (2*math.pi)-math.pi)*1000) for a in angles],
                ranges_mm=[round(r/math.cos(a)*1000) if math.isfinite(r) and .1 <= r <= 20 else -1
                           for r, a in zip(values, angles)]))
        return callback

    def rgb(self, msg):
        self.keep('rgb', msg, dict(pixels_hex=bytes(msg.data).hex(), width=msg.width, height=msg.height))

    def snapshot(self):
        with self.lock:
            if not all(k in self.data for k in ('lidar', 'rgb', 'depth0', 'depth1', 'depth2', 'depth3')):
                return None
            return dict(lidar=self.data['lidar'], rgb=self.data['rgb'],
                        depth=[self.data[f'depth{i}'] for i in range(4)])


class LiveDriver(flight.ConfiguredDriver):
    def __init__(self, timeouts, backend):
        super().__init__(timeouts)
        self.backend = backend
        self.local = self.attitude = self.global_fix = None
        self.local_received = 0

    def drain(self):
        for _ in range(256):
            msg = self.conn.recv_match(blocking=False)
            if msg is None:
                break
            kind = msg.get_type()
            if kind == 'LOCAL_POSITION_NED':
                self.local, self.local_received = msg, self.backend.now_ns()
            elif kind == 'ATTITUDE':
                self.attitude = msg
            elif kind == 'GLOBAL_POSITION_INT':
                self.global_fix = msg

    def streams(self):
        for message in (32, 30, 33):
            self._cmd(flight.mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, float(message), 50000.0)
            self._ack(flight.mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 3)

    def estimate(self, origin):
        if self.local is None or self.attitude is None:
            return None
        p, a = self.local, self.attitude
        return dict(position_mm=[round((p.y-origin[0])*1000), round((p.x-origin[1])*1000),
                                 round((-p.z-origin[2])*1000)],
                    yaw_mrad=round(((math.pi/2-a.yaw+math.pi) % (2*math.pi)-math.pi)*1000),
                    received_ns=self.local_received, px4_boot_ms=p.time_boot_ms,
                    tilt_mrad=round(max(abs(a.roll), abs(a.pitch))*1000),
                    speed_mm_s=round(math.sqrt(p.vx*p.vx+p.vy*p.vy+p.vz*p.vz)*1000))


def main():
    cfg = json.loads(sys.argv[1])
    work = Path('/out/wd')
    work.mkdir(parents=True, exist_ok=True)
    world = 'sim3'
    env = dict(os.environ, GZ_SIM_RESOURCE_PATH=flight.PX4_MODELS+':/flight/models',
               GZ_FUEL_STATIC_ONLY='1')
    gz_log = open('/out/gazebo.log', 'wb')
    gz = subprocess.Popen(['gz', 'sim', '-s', '-r', '--headless-rendering', '/flight/world.sdf'],
                          stdout=gz_log, stderr=subprocess.STDOUT, env=env)
    backend = flight.Backend(world)
    backend.start()
    sensors = Sensors(backend)
    t0 = time.monotonic()
    while not backend.clock_samples:
        if time.monotonic()-t0 > 30:
            raise TimeoutError('Gazebo clock')
        time.sleep(.05)
    model = 'x500_sensor1s'
    backend.model_name = model+'_0'
    pxenv = dict(env, PX4_SYS_AUTOSTART='4001', PX4_SIM_MODEL='gz_'+model,
                 PX4_GZ_STANDALONE='1', PX4_GZ_MODEL=model, PX4_GZ_WORLD=world,
                 PX4_GZ_MODEL_POSE='0,0,0.2,0,0,0', HOME=str(work))
    hook = flight.prepare_px4_parameters(pxenv, work)
    px4 = subprocess.Popen([flight.PX4_BIN, flight.PX4_ETC, '-s', 'etc/init.d-posix/rcS',
                            '-i', '0', '-d', '-w', str(work)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=pxenv, cwd=work)
    lines = []
    threading.Thread(target=flight._drain, args=(px4.stdout, lines), daemon=True).start()
    driver = LiveDriver(cfg['timeouts'], backend)
    private = open('/out/private.jsonl', 'x', buffering=1)
    mission = open('/out/mission.jsonl', 'x', buffering=1)
    result = dict(ok=False, error=None, steps=0, body_pose_writes=0, hook=hook)
    last_truth = -1

    def poll():
        nonlocal last_truth
        driver.drain()
        body, now, _ = backend.snapshot()
        if body is not None and now-last_truth >= 20_000_000:
            last_truth = now
            private.write(json.dumps(dict(now_ns=now, body=list(body),
                                         local=(driver.local.to_dict() if driver.local else None)))+'\n')
        if px4.poll() is not None:
            raise RuntimeError('PX4 exited')
        if time.monotonic()-t0 > cfg['timeouts']['episode_s']:
            raise TimeoutError('episode wall deadline')

    def wait(seconds):
        end = backend.now_ns()+round(seconds*1e9)
        while backend.now_ns() < end:
            poll()
            time.sleep(.01)

    try:
        if not driver.connect(30) or not driver.wait_ready(45):
            raise RuntimeError('PX4 not ready')
        driver.streams()
        wait(2)
        if driver.local is None:
            raise RuntimeError('no local odometry')
        origin = (driver.local.y, driver.local.x, -driver.local.z)
        mission.write(json.dumps(dict(kind='odometry_origin', value=list(origin),
                                      now_ns=backend.now_ns()))+'\n')
        # PX4's pinned EKF requires HAGL > 1.5 m for final magnetic alignment.
        # Fly above that requirement; never force its heading-valid flag.
        if not driver.set_param('MIS_TAKEOFF_ALT', 2.5, flight.mavutil.mavlink.MAV_PARAM_TYPE_REAL32):
            raise RuntimeError('takeoff parameter')
        if not driver.takeoff(5) or not driver.arm(10):
            raise RuntimeError('takeoff/arm rejected')
        wait(10)
        fix = driver.global_fix
        local = driver.local
        if fix is None or local is None:
            raise RuntimeError('navigation reference missing')
        # Both references come from the estimator, never from backend pose.
        lat_ref = fix.lat/1e7-local.x/111320
        lon_scale = 111320*math.cos(math.radians(fix.lat/1e7))
        lon_ref = fix.lon/1e7-local.y/lon_scale
        alt_ref = fix.alt/1000+local.z
        target = (0, 0)
        yaw = driver.attitude.yaw
        epoch = 0
        changed = False
        while epoch < 65:
            # Wait for a settled, fresh snapshot; this is one observation skill.
            deadline = backend.now_ns()+15_000_000_000
            raw = None
            while backend.now_ns() < deadline:
                poll()
                estimate = driver.estimate(origin)
                snapshot = sensors.snapshot()
                if estimate and snapshot:
                    now = backend.now_ns()
                    ages = [now-r['capture_ns'] for r in snapshot['depth']+[snapshot['lidar'], snapshot['rgb']]]
                    target_error = math.hypot(estimate['position_mm'][0]-target[0]*STEP_MM,
                                              estimate['position_mm'][1]-target[1]*STEP_MM)
                    yaw_error = abs((driver.attitude.yaw-yaw+math.pi) % (2*math.pi)-math.pi)
                    if (target_error < 400 and abs(estimate['position_mm'][2]-2500) < 300
                            and estimate['speed_mm_s'] < 200 and estimate['tilt_mrad'] < 80
                            and (epoch == 0 or yaw_error < .08) and abs(driver.attitude.yawspeed) < .05
                            and max(ages) <= 200_000_000 and min(ages) >= 0):
                        raw = dict(now_ns=now, estimate=estimate, **snapshot)
                        break
                time.sleep(.02)
            if raw is None:
                result['observation_failure'] = dict(estimate=estimate, ages=locals().get('ages'),
                                                     target_error=locals().get('target_error'),
                                                     yaw_error=locals().get('yaw_error'))
                raise TimeoutError('settled sensor observation')
            intervention = cfg.get('world_intervention')
            if intervention and not changed and result['steps'] >= intervention['after_movements']:
                body, _, _ = backend.snapshot()
                target_pose = intervention['target']
                gap_clearance = math.hypot(*(max(abs(body[i+1]-target_pose[i])-1.5, 0) for i in range(2)))
                if gap_clearance > 1.0:
                    request = Pose()
                    request.name = intervention['entity']
                    request.position.x, request.position.y, request.position.z = target_pose
                    request.orientation.w = 1
                    begin = backend.now_ns()
                    backend.node.request('/world/sim3/set_pose', request, Pose, Boolean, 300)
                    limit = backend.now_ns()+2_000_000_000
                    while backend.now_ns() < limit:
                        wait(.05)
                        measured = backend.static_poses.get(intervention['entity'])
                        if measured and max(abs(a-b) for a, b in zip(measured, target_pose)) < .01:
                            break
                    else:
                        raise RuntimeError('world intervention not observed')
                    mission.write(json.dumps(dict(kind='world_change', begin_ns=begin,
                        now_ns=backend.now_ns(), entity=intervention['entity'], observed=list(measured),
                        source=intervention['source'], target=target_pose))+'\n')
                    changed = True
                    result['world_change_observed'] = True
                    wait(.15)
                    continue  # obtain new sensor evidence; no hidden change flag sent
            mission.write(json.dumps(dict(kind='observation', epoch=epoch, raw=raw), sort_keys=True)+'\n')
            flight.emit(dict(kind='observation', epoch=epoch, raw=raw))
            if not select.select([sys.stdin], [], [], 30)[0]:
                raise TimeoutError('agent response')
            command = json.loads(sys.stdin.readline())
            if set(command) != {'wsp'}:
                raise ValueError('command schema: only WSP is causal')
            w = bytes.fromhex(command['wsp'])
            if len(w) != 16 or w[11:13] != bytes((9, 8)):
                raise ValueError('command WSP')
            mission.write(json.dumps(dict(kind='command', epoch=epoch, now_ns=backend.now_ns(), **command))+'\n')
            action = w[13]
            if w[1] == 14 and action == 6:
                result['status'] = 'agent_stopped'
                break
            oldest = min(s['capture_ns'] for s in raw['depth']+[raw['lidar'], raw['rgb']])
            if backend.now_ns()-oldest > 250_000_000:
                raise TimeoutError('evidence expired before physical execution')
            if w[1] == 14 and 7 <= action <= 10:
                # Inspection yaw only; same generic skill in every room.
                yaw = (action-7)*math.pi/2
            elif w[1] == 11 and action < 4:
                p = raw['estimate']['position_mm']
                cell = (round(p[0]/STEP_MM), round(p[1]/STEP_MM))
                delta = VECTORS[action]
                target = (cell[0]+delta[0], cell[1]+delta[1])
                yaw = math.atan2(delta[0], delta[1])  # NED heading
                result['steps'] += 1
            else:
                raise ValueError('unsupported physical skill')
            north = origin[1]+target[1]*3
            east = origin[0]+target[0]*3
            accepted = driver.reposition(lat_ref+north/111320, lon_ref+east/lon_scale,
                                         alt_ref+origin[2]+2.5, yaw)
            mission.write(json.dumps(dict(kind='ack', epoch=epoch, accepted=accepted,
                                          now_ns=backend.now_ns(), target_local_mm=[round(east*1000), round(north*1000)]))+'\n')
            if not accepted:
                raise RuntimeError('reposition rejected')
            wait(1)
            epoch += 1
        if not driver.land(5):
            raise RuntimeError('land rejected')
        deadline = backend.now_ns()+25_000_000_000
        while backend.now_ns() < deadline:
            poll()
            hb = driver.conn.messages.get('HEARTBEAT')
            if hb and not hb.base_mode & flight.mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                result['disarmed'] = True
                break
            time.sleep(.02)
        result['ok'] = bool(result.get('disarmed'))
    except Exception as exc:
        result['error'] = repr(exc)
        try:
            if driver.conn:
                driver.land(3)
                wait(15)
        except Exception:
            pass
    finally:
        result['driver_events'] = driver.events
        result['px4_tail'] = lines[-30:]
        result['wall_s'] = time.monotonic()-t0
        private.close()
        mission.close()
        px4.terminate()
        try:
            px4.wait(timeout=15)
        except subprocess.TimeoutExpired:
            px4.kill()
            px4.wait()
        gz.terminate()
        try:
            gz.wait(timeout=15)
        except subprocess.TimeoutExpired:
            gz.kill()
            gz.wait()
        gz_log.close()
        ulog = flight._latest_ulog(work)
        if ulog:
            result['ulog'] = str(ulog)
            result['ulog_sha256'] = hashlib.sha256(ulog.read_bytes()).hexdigest()
        Path('/out/result.json').write_text(json.dumps(result, sort_keys=True, indent=2))
        flight.emit(dict(kind='result', **result))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
