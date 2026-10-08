"""SITL-only safety adapter. Private pose is audit-only, never an action input."""
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from live_runner import LiveDriver, Sensors, flight
from echoai.nexus0.cause1.core import wsp
from echoai.nexus0.safe1.core import Supervisor, Lease
from echoai.nexus0.safe1.ipc import Channel, ChannelError
from echoai.nexus0.safe1.service import serviced_call


def main():
    cfg = json.loads(sys.argv[1])
    work = Path('/out/wd')
    work.mkdir()
    env = dict(os.environ, GZ_SIM_RESOURCE_PATH=flight.PX4_MODELS+':/flight/models', GZ_FUEL_STATIC_ONLY='1')
    gzlog = open('/out/gazebo.log', 'wb')
    gz = subprocess.Popen(['gz', 'sim', '-s', '-r', '--headless-rendering', '--seed', str(cfg['physics_seed']),
                           '/flight/world.sdf'], stdout=gzlog, stderr=subprocess.STDOUT, env=env)
    backend = flight.Backend('sim3')
    backend.start()
    started = time.monotonic()
    while not backend.clock_samples:
        if time.monotonic()-started > 30:
            gz.terminate()
            raise TimeoutError('clock')
        time.sleep(.05)
    backend.model_name = 'x500_sensor1s_0'
    sensors = Sensors(backend)
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
    ledger = open('/out/trace.jsonl', 'x', buffering=1)
    result = dict(ok=False, hook=hook)
    lock = threading.RLock()
    lease = Lease()
    stop = threading.Event()
    origin = None
    last_record = -1
    supervisor = Supervisor(json.loads(Path('/flight/model.json').read_text()))
    channel = None
    frozen_sensor = frozen_link = None
    pump = None

    def log(kind, **value):
        with lock:
            ledger.write(json.dumps(dict(kind=kind, now_ns=backend.now_ns(), wall_ns=time.monotonic_ns(), **value), sort_keys=True)+'\n')

    def renew():
        with lock:
            now = time.monotonic_ns()
            ok = lease.renew(now)
            log('lease_renew', lease_now_ns=now, allowed=ok)
            if not ok:
                raise RuntimeError('heartbeat lease expired')

    def cancel():
        with lock:
            lease.cancel()
            log('heartbeat_cut')

    def heartbeat():
        while not stop.wait(.1):
            with lock:
                now = time.monotonic_ns()
                if lease.allowed(now):
                    driver.conn.mav.heartbeat_send(flight.mavutil.mavlink.MAV_TYPE_GCS,
                        flight.mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, flight.mavutil.mavlink.MAV_STATE_ACTIVE)
                    log('gcs_heartbeat', lease_now_ns=now)

    def sensor_stamp():
        with sensors.lock:
            return sensors.data.get('lidar', {}).get('capture_ns')

    def poll():
        nonlocal last_record
        driver.drain()
        now = backend.now_ns()
        if now-last_record >= 50_000_000:
            last_record = now
            hb = driver.conn.messages.get('HEARTBEAT')
            log('sample', estimate=driver.estimate(origin) if origin else None,
                heartbeat=hb.to_dict() if hb else None,
                heartbeat_wall_age_ms=round((time.time()-hb._timestamp)*1000) if hb else None,
                sensor_ns=sensor_stamp(), body=list(backend.body) if backend.body else None)
        if px4.poll() is not None or time.monotonic()-started > 220:
            raise RuntimeError('runtime/deadline')

    def wait(seconds):
        until = backend.now_ns()+round(seconds*1e9)
        while backend.now_ns() < until:
            poll()
            renew()  # Operator bootstrap/normal termination only, never fault containment.
            time.sleep(.02)

    def health():
        estimate = driver.estimate(origin)
        hb = driver.conn.messages.get('HEARTBEAT')
        fresh = hb is not None and 0 <= time.time()-hb._timestamp <= 2
        main = (hb.custom_mode >> 16) & 255 if hb else -1
        sub = (hb.custom_mode >> 24) & 255 if hb else -1
        frame = dict(received_ns=estimate['received_ns'] if frozen_link is None else frozen_link,
                     position_mm=estimate['position_mm'], speed_mm_s=estimate['speed_mm_s'],
                     armed=bool(hb and hb.base_mode & 128),
                     authority=bool(fresh and main == 4 and sub in (2, 3)),
                     failsafe=bool(not fresh or hb.system_status != 4))
        return dict(now_ns=backend.now_ns(), sensor_ns=sensor_stamp() if frozen_sensor is None else frozen_sensor,
                    frame=frame, worker_alive=channel is not None and channel.process.poll() is None)

    def check():
        h = health()
        ok = supervisor.check(h)
        log('check', health=h, ok=ok, state=supervisor.gateway.state)
        if ok:
            renew()
        return ok

    def energy(now, action):
        return dict(now_ns=now, battery=dict(capture_ns=now, remaining=150, capacity=1000, unit='sim_u'),
                    routes=dict(out=[action], goal_home=[1-action], home=[]), at_home=True, goal_reached=False)

    def submit(request):
        h = health()
        e = energy(h['now_ns'], cfg['seed'] % 2)
        decision = supervisor.submit(request, h, e)
        log('proposal', request=request, health=h, energy=e, decision=decision)
        return decision

    try:
        if not driver.connect(30) or not driver.wait_ready(45):
            raise RuntimeError('PX4 not ready')
        # Configure before heartbeat lease begins. No aircraft is armed yet.
        for name, value, ptype in [('MIS_TAKEOFF_ALT', 2.5, 9), ('COM_DL_LOSS_T', 5, 6), ('NAV_DLL_ACT', 3, 6)]:
            if not driver.set_param(name, value, ptype) or driver.read_param(name, ptype) != value:
                raise RuntimeError('parameter readback '+name)
            log('parameter', name=name, value=value)
        driver.streams()
        renew()
        pump = threading.Thread(target=heartbeat, daemon=True)
        pump.start()
        wait(2)
        origin = (driver.local.y, driver.local.x, -driver.local.z)
        log('origin', value=list(origin))
        if not serviced_call(lambda: driver.takeoff(5), renew, 6):
            raise RuntimeError('takeoff')
        renew()
        if not serviced_call(lambda: driver.arm(10), renew, 11):
            raise RuntimeError('arm')
        renew()
        wait(12)
        until = backend.now_ns()+15_000_000_000
        while (driver.estimate(origin)['speed_mm_s'] > 100 or sensor_stamp() is None) and backend.now_ns() < until:
            wait(.1)
        mode = {'process_exit': 'exit', 'process_hang': 'hang', 'bad_proposal': 'bad'}.get(cfg['condition'], 'healthy')
        channel = Channel([sys.executable, '/flight/worker.py', mode])
        poll()
        log('supervision_start', health=health())
        if not check():
            raise RuntimeError('initial health '+str(supervisor.reason))
        fault = cfg['condition'] != 'nominal'
        if fault:
            log('injection', condition=cfg['condition'])
        if cfg['condition'] == 'sensor_stale':
            frozen_sensor = sensor_stamp()
        if cfg['condition'] == 'network_stale':
            frozen_link = driver.estimate(origin)['received_ns']
        if frozen_sensor is not None or frozen_link is not None:
            while check():
                time.sleep(.02)
                poll()
        else:
            before = time.monotonic_ns()
            try:
                reply = channel.call(wsp(cfg['seed'] % 2))
                log('ipc', reply=reply, elapsed_ns=time.monotonic_ns()-before)
                request = dict(wsp=reply['wsp'], seq=reply['seq'], published_ns=backend.now_ns())
                decision = submit(request)
            except ChannelError as exc:
                supervisor.trip('ipc_'+str(exc))
                log('ipc_error', reason=supervisor.reason, elapsed_ns=time.monotonic_ns()-before)
                decision = dict(allowed=False)
            if decision['allowed']:
                if fault:
                    raise RuntimeError('fault forwarded')
                fix, local = driver.global_fix, driver.local
                east, north, height = [v/1000 for v in decision['target_mm']]
                north += origin[1]
                east += origin[0]
                lat = fix.lat/1e7+(north-local.x)/111320
                lon = fix.lon/1e7+(east-local.y)/(111320*math.cos(math.radians(fix.lat/1e7)))
                alt = fix.alt/1000+local.z+origin[2]+height
                driver.conn.messages.pop('COMMAND_ACK', None)
                with lock:
                    if not lease.allowed(time.monotonic_ns()):
                        raise RuntimeError('expired send permission')
                    log('send', wsp=request['wsp'], target_mm=decision['target_mm'], lat=lat, lon=lon, alt=alt,
                        yaw=driver.attitude.yaw, reference=dict(fix=fix.to_dict(), local=local.to_dict()))
                    driver.conn.mav.command_int_send(driver.conn.target_system, 1, 5, 192,
                        0, 0, 1., 1., 0., driver.attitude.yaw, round(lat*1e7), round(lon*1e7), alt)
                while supervisor.gateway.state in ('await_ack', 'executing'):
                    poll()
                    msg = driver.conn.messages.pop('COMMAND_ACK', None)
                    if msg and msg.command == 192:
                        now = backend.now_ns()
                        ack = dict(system=msg.get_srcSystem(), component=msg.get_srcComponent(),
                                   command=msg.command, result=msg.result, received_ns=now)
                        accepted = supervisor.acknowledge(ack, now)
                        log('ack', ack=ack, accepted=accepted, ack_now_ns=now)
                    if not check():
                        break
                    time.sleep(.02)
        if fault:
            if not supervisor.tripped:
                raise RuntimeError('missing latch')
            cancel()
            log('veto', reason=supervisor.reason)
            # Restoring good observations cannot resume this session.
            frozen_link = frozen_sensor = None
            for _ in range(2):
                poll()
                if submit(dict(wsp=wsp(cfg['seed'] % 2), seq=2, published_ns=backend.now_ns()))['allowed']:
                    raise RuntimeError('automatic recovery')
        else:
            if supervisor.gateway.state != 'complete' or supervisor.tripped:
                raise RuntimeError('nominal incomplete')
            log('complete')
            log('land_request')
            if not serviced_call(lambda: driver.land(5), renew, 6):
                raise RuntimeError('land rejected')
        until = backend.now_ns()+35_000_000_000
        while backend.now_ns() < until:
            poll()
            if not fault:
                renew()  # Mission is terminal; operator's normal landing, never more goals.
            hb = driver.conn.messages.get('HEARTBEAT')
            if hb and not hb.base_mode & 128:
                log('disarmed')
                result['ok'] = True
                break
            time.sleep(.02)
        if not result['ok']:
            raise TimeoutError('disarm')
    except Exception as exc:
        cancel()
        result['error'] = repr(exc)
        log('failure', error=repr(exc))
    finally:
        stop.set()
        if pump:
            pump.join(2)
        if channel:
            channel.close()
        result.update(driver_events=driver.events, px4_tail=lines[-40:], wall_s=time.monotonic()-started)
        ledger.close()
        for process in (px4, gz):
            process.terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        gzlog.close()
        ulog = flight._latest_ulog(work)
        if ulog:
            result['ulog_sha256'] = hashlib.sha256(ulog.read_bytes()).hexdigest()
        Path('/out/result.json').write_text(json.dumps(result, sort_keys=True, indent=2))
        print(json.dumps(result), flush=True)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
