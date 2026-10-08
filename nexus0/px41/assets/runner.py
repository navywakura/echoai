"""Private SITL adapter. Only the gateway's bounded goal reaches MAVLink."""
import hashlib
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from live_runner import LiveDriver, flight
from echoai.nexus0.cause1.core import wsp
from echoai.nexus0.px41.core import Gateway


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
    heartbeat_enabled, last_heartbeat, last_record = False, -1, -1
    origin = None
    gate = Gateway()

    def log(kind, **value):
        ledger.write(json.dumps(dict(kind=kind, now_ns=backend.now_ns(), **value), sort_keys=True)+'\n')

    def poll():
        nonlocal last_heartbeat, last_record
        driver.drain()
        now = backend.now_ns()
        if heartbeat_enabled and now-last_heartbeat >= 500_000_000:
            driver.conn.mav.heartbeat_send(flight.mavutil.mavlink.MAV_TYPE_GCS,
                flight.mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, flight.mavutil.mavlink.MAV_STATE_ACTIVE)
            last_heartbeat = now
            log('gcs_heartbeat')
        if now-last_record >= 50_000_000:
            last_record = now
            hb = driver.conn.messages.get('HEARTBEAT')
            log('sample', estimate=driver.estimate(origin) if origin else None,
                heartbeat=hb.to_dict() if hb else None,
                heartbeat_wall_age_ms=round((time.time()-hb._timestamp)*1000) if hb else None,
                body=list(backend.body) if backend.body else None)
        if px4.poll() is not None or time.monotonic()-started > 200:
            raise RuntimeError('runtime/deadline')

    def wait(seconds):
        until = backend.now_ns()+round(seconds*1e9)
        while backend.now_ns() < until:
            poll()
            time.sleep(.01)

    def frame():
        estimate = driver.estimate(origin)
        hb = driver.conn.messages.get('HEARTBEAT')
        fresh_hb = hb is not None and 0 <= time.time()-hb._timestamp <= 2
        main = (hb.custom_mode >> 16) & 255 if hb else -1
        sub = (hb.custom_mode >> 24) & 255 if hb else -1
        return dict(received_ns=estimate['received_ns'], position_mm=estimate['position_mm'],
                    speed_mm_s=estimate['speed_mm_s'], armed=bool(hb and hb.base_mode & 128),
                    authority=bool(fresh_hb and main == 4 and sub in (2, 3)),
                    failsafe=bool(not fresh_hb or hb.system_status != 4))

    def propose(request, telemetry, label):
        now = backend.now_ns()
        decision = gate.propose(request, telemetry, now)
        log('proposal', request=request, frame=telemetry, decision=decision, gate_now_ns=now, label=label)
        return decision

    try:
        if not driver.connect(30) or not driver.wait_ready(45):
            raise RuntimeError('PX4 not ready')
        gate = Gateway(driver.conn.target_system, 1)
        heartbeat_enabled = True
        poll()
        for name, value, ptype in [('MIS_TAKEOFF_ALT', 2.5, 9), ('COM_DL_LOSS_T', 5, 6), ('NAV_DLL_ACT', 3, 6)]:
            if not driver.set_param(name, value, ptype) or driver.read_param(name, ptype) != value:
                raise RuntimeError('parameter readback '+name)
            log('parameter', name=name, value=value)
            poll()
        driver.streams()
        wait(2)
        origin = (driver.local.y, driver.local.x, -driver.local.z)
        log('origin', value=list(origin))
        if not driver.takeoff(5) or not driver.arm(10):
            raise RuntimeError('takeoff')
        wait(12)
        until = backend.now_ns()+15_000_000_000
        while frame()['speed_mm_s'] > 100 and backend.now_ns() < until:
            wait(.1)
        current = frame()
        request = dict(wsp=wsp(0 if cfg['seed'] % 2 else 1), seq=1, published_ns=backend.now_ns())
        for label, req, telem in [
            ('malformed', dict(request, wsp='00'), current),
            ('expired', dict(request, published_ns=backend.now_ns()-500_000_000), current),
            ('authority', request, dict(current, authority=False)),
            ('envelope', request, dict(current, position_mm=[6000, 0, 2500]))]:
            if propose(req, telem, label)['allowed']:
                raise RuntimeError('illegal accepted: '+label)
        poll()
        request['published_ns'] = backend.now_ns()
        decision = propose(request, frame(), 'legal')
        if not decision['allowed']:
            raise RuntimeError('legal blocked '+str(decision))
        if propose(request, frame(), 'busy')['allowed']:
            raise RuntimeError('busy accepted')
        fix, local = driver.global_fix, driver.local
        east, north, height = [v/1000 for v in decision['target_mm']]
        north += origin[1]
        east += origin[0]
        lat = fix.lat/1e7+(north-local.x)/111320
        lon = fix.lon/1e7+(east-local.y)/(111320*math.cos(math.radians(fix.lat/1e7)))
        alt = fix.alt/1000+local.z+origin[2]+height
        log('send', wsp=request['wsp'], target_mm=decision['target_mm'], lat=lat, lon=lon, alt=alt,
            yaw=driver.attitude.yaw, reference=dict(fix=fix.to_dict(), local=local.to_dict()))
        driver.conn.messages.pop('COMMAND_ACK', None)
        driver.conn.mav.command_int_send(driver.conn.target_system, 1, 5, 192,
            0, 0, 1., 1., 0., driver.attitude.yaw, round(lat*1e7), round(lon*1e7), alt)
        while gate.state in ('await_ack', 'executing'):
            poll()
            msg = driver.conn.messages.pop('COMMAND_ACK', None)
            if msg and msg.command == 192:
                now = backend.now_ns()
                ack = dict(system=msg.get_srcSystem(), component=msg.get_srcComponent(),
                           command=msg.command, result=msg.result, received_ns=now)
                accepted = gate.acknowledge(ack, now)
                log('ack', ack=ack, accepted=accepted, state=gate.state, gate_now_ns=now)
            now = backend.now_ns()
            telem = frame()
            state = gate.observe(telem, now)
            log('observe', frame=telem, state=state, gate_now_ns=now)
            time.sleep(.02)
        if gate.state != 'complete':
            raise RuntimeError('execution '+gate.state)
        if propose(request, frame(), 'replay')['allowed']:
            raise RuntimeError('replay accepted')
        log('complete', target_mm=decision['target_mm'])
        if cfg['condition'] == 'link_loss':
            heartbeat_enabled = False
            log('heartbeat_cut')
        else:
            log('land_request')
            if not driver.land(5):
                raise RuntimeError('land rejected')
        until = backend.now_ns()+35_000_000_000
        while backend.now_ns() < until:
            poll()
            hb = driver.conn.messages.get('HEARTBEAT')
            if hb and not hb.base_mode & 128:
                log('disarmed')
                result['ok'] = True
                break
            time.sleep(.02)
        if not result['ok']:
            raise TimeoutError('disarm')
    except Exception as exc:
        result['error'] = repr(exc)
        log('failure', error=repr(exc))
        # Simulator teardown only: never conceal failure with force-disarm.
    finally:
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
