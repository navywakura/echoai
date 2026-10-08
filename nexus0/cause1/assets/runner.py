"""Private paired intervention. Frozen PX4 driver; never writes body pose."""
import hashlib
import json
import math
import os
import select
import subprocess
import sys
import threading
import time
from pathlib import Path

from live_runner import LiveDriver, Sensors, flight, Pose, Boolean
from cause_core import decode


def main():
    cfg = json.loads(sys.argv[1])
    work = Path('/out/wd')
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GZ_SIM_RESOURCE_PATH=flight.PX4_MODELS+':/flight/models',
               GZ_FUEL_STATIC_ONLY='1')
    gz_log = open('/out/gazebo.log', 'wb')
    seed_args = ['--seed', str(cfg['physics_seed'])] if cfg.get('physics_seed') is not None else []
    gz = subprocess.Popen(['gz', 'sim', '-s', '-r', '--headless-rendering', *seed_args, '/flight/world.sdf'],
                          stdout=gz_log, stderr=subprocess.STDOUT, env=env)
    backend = flight.Backend('sim3')
    backend.start()
    sensors = Sensors(backend)
    started = time.monotonic()
    while not backend.clock_samples:
        if time.monotonic()-started > 30:
            raise TimeoutError('Gazebo clock')
        time.sleep(.05)
    backend.model_name = 'x500_sensor1s_0'
    pxenv = dict(env, PX4_SYS_AUTOSTART='4001', PX4_SIM_MODEL='gz_x500_sensor1s',
                 PX4_GZ_STANDALONE='1', PX4_GZ_MODEL='x500_sensor1s', PX4_GZ_WORLD='sim3',
                 PX4_GZ_MODEL_POSE='0,0,0.2,0,0,0', HOME=str(work))
    hook = flight.prepare_px4_parameters(pxenv, work)
    px4 = subprocess.Popen([flight.PX4_BIN, flight.PX4_ETC, '-s', 'etc/init.d-posix/rcS',
                            '-i', '0', '-d', '-w', str(work)], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, env=pxenv, cwd=work)
    lines = []
    threading.Thread(target=flight._drain, args=(px4.stdout, lines), daemon=True).start()
    driver = LiveDriver(cfg['timeouts'], backend)
    private = open('/out/private.jsonl', 'x', buffering=1)
    mission = open('/out/mission.jsonl', 'x', buffering=1)
    result = dict(ok=False, body_pose_writes=0, hook=hook, physics_seed=cfg.get('physics_seed'))
    last = -1

    def record(value):
        mission.write(json.dumps(value, sort_keys=True)+'\n')

    def poll():
        nonlocal last
        driver.drain()
        body, now, _ = backend.snapshot()
        if body is not None and now-last >= 20_000_000:
            last = now
            private.write(json.dumps(dict(now_ns=now, body=list(body),
                wall=list(backend.static_poses.get('cause_wall', ())),
                local=driver.local.to_dict() if driver.local else None))+'\n')
        if px4.poll() is not None:
            raise RuntimeError('PX4 exited')
        if time.monotonic()-started > 180:
            raise TimeoutError('episode wall deadline')

    def wait(seconds):
        until = backend.now_ns()+round(seconds*1e9)
        while backend.now_ns() < until:
            poll()
            time.sleep(.01)

    def observation(origin):
        until = backend.now_ns()+20_000_000_000
        while backend.now_ns() < until:
            poll()
            estimate = driver.estimate(origin)
            with sensors.lock:
                scan = sensors.data.get('lidar')
            now = backend.now_ns()
            if (estimate and scan and estimate['tilt_mrad'] < 80
                    and estimate['speed_mm_s'] < 100
                    and abs(estimate['position_mm'][2]-2500) < 300
                    and 0 <= now-scan['capture_ns'] <= 200_000_000
                    and 0 <= now-estimate['received_ns'] <= 100_000_000
                    and abs(scan['capture_ns']-estimate['received_ns']) <= 100_000_000):
                return dict(now_ns=now, estimate=estimate, lidar=scan)
            time.sleep(.02)
        raise TimeoutError('settled fresh observation')

    try:
        if not driver.connect(30) or not driver.wait_ready(45):
            raise RuntimeError('PX4 not ready')
        driver.streams()
        wait(2)
        if driver.local is None:
            raise RuntimeError('no local position')
        origin = (driver.local.y, driver.local.x, -driver.local.z)
        record(dict(kind='odometry_origin', value=list(origin), now_ns=backend.now_ns()))
        if not driver.set_param('MIS_TAKEOFF_ALT', 2.5, flight.mavutil.mavlink.MAV_PARAM_TYPE_REAL32):
            raise RuntimeError('takeoff parameter')
        if not driver.takeoff(5) or not driver.arm(10):
            raise RuntimeError('takeoff rejected')
        wait(12)
        before = observation(origin)
        record(dict(kind='before', raw=before))
        flight.emit(dict(kind='before', raw=before))
        if not select.select([sys.stdin], [], [], 20)[0]:
            raise TimeoutError('consumer command')
        command = json.loads(sys.stdin.readline())
        if set(command) != {'wsp'}:
            raise ValueError('only WSP commands')
        action = decode(command['wsp'])
        if backend.now_ns()-before['lidar']['capture_ns'] > 250_000_000:
            raise TimeoutError('expired pre-action evidence')
        poll()
        fix, local = driver.global_fix, driver.local
        if fix is None or local is None:
            raise RuntimeError('navigation reference')
        amount = 1 if action == 0 else -1 if action == 1 else 0
        target_north = local.x+amount
        lat_ref = fix.lat/1e7-local.x/111320
        lon_scale = 111320*math.cos(math.radians(fix.lat/1e7))
        lon_ref = fix.lon/1e7-local.y/lon_scale
        alt_ref = fix.alt/1000+local.z
        sent = backend.now_ns()
        record(dict(kind='command', wsp=command['wsp'], sent_ns=sent,
                    target_local_mm=[round(local.y*1000), round(target_north*1000)]))
        accepted = driver.reposition(lat_ref+target_north/111320,
            lon_ref+local.y/lon_scale, alt_ref+origin[2]+2.5, driver.attitude.yaw)
        execution = dict(wsp=command['wsp'], sent_ns=sent, ack_ns=backend.now_ns(), accepted=accepted)
        record(dict(kind='ack', **execution))
        if not accepted:
            raise RuntimeError('reposition rejected')
        # Only the wall is intervened on, privately; treatment absent from wire.
        if cfg['external_mm']:
            target = [0, (cfg['wall_mm']+cfg['external_mm'])/1000, 3]
            request = Pose()
            request.name = 'cause_wall'
            request.position.x, request.position.y, request.position.z = target
            request.orientation.w = 1
            begin = backend.now_ns()
            backend.node.request('/world/sim3/set_pose', request, Pose, Boolean, 300)
            until = backend.now_ns()+2_000_000_000
            while backend.now_ns() < until:
                wait(.05)
                measured = backend.static_poses.get('cause_wall')
                if measured and max(abs(a-b) for a, b in zip(measured, target)) < .01:
                    break
            else:
                raise RuntimeError('wall intervention not observed')
            record(dict(kind='world_change', begin_ns=begin, now_ns=backend.now_ns(),
                        entity='cause_wall', target=target, observed=list(measured)))
        wait(10)
        after = observation(origin)
        record(dict(kind='after', raw=after))
        flight.emit(dict(kind='after', execution=execution, raw=after))
        if not driver.land(5):
            raise RuntimeError('land rejected')
        until = backend.now_ns()+25_000_000_000
        while backend.now_ns() < until:
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
        result.update(driver_events=driver.events, px4_tail=lines[-30:], wall_s=time.monotonic()-started)
        private.close()
        mission.close()
        for process in (px4, gz):
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        gz_log.close()
        ulog = flight._latest_ulog(work)
        if ulog:
            result.update(ulog=str(ulog), ulog_sha256=hashlib.sha256(ulog.read_bytes()).hexdigest())
        Path('/out/result.json').write_text(json.dumps(result, sort_keys=True, indent=2))
        flight.emit(dict(kind='result', **result))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
