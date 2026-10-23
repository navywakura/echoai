"""Hooks around imported PX4/Gazebo runner; no pose writes or new physics."""
import json
import math
import os
from pathlib import Path
import sys
import time
from .protocol import packet, unpack, SCHOOL, FREEZE, TICK, RECEIPT, ACTION, ACK

REQUEST = Path('/out/percibex-request.wsp')
REPLY = Path('/out/percibex-reply.wsp')


def yaw_delta(angle, baseline):
    return math.atan2(math.sin(angle-baseline), math.cos(angle-baseline))


def yaw_target(baseline):
    return yaw_delta(baseline+.4, 0.)


def inspection_angle_ok(delta):
    return .28 <= abs(delta) <= .52


def main():
    import frozen_tap as tap
    if sys.argv[1] == '--channel': return tap.channel(json.loads(sys.argv[2]))
    import flightrunner_survey as runner
    original_emit, original_popen = runner.emit, tap.subprocess.Popen
    state = dict(seq=0, driver=None, backend=None, goal=None)

    def exchange(op, value=0):
        state['seq'] += 1
        raw = packet(op, state['seq'], value)
        temp = REQUEST.with_suffix('.tmp')
        temp.write_bytes(raw); os.replace(temp, REQUEST)
        deadline = time.monotonic()+10
        while time.monotonic() < deadline:
            if REPLY.exists():
                answer = REPLY.read_bytes()
                kind, seq, val = unpack(answer)
                if seq == state['seq']:
                    if kind != (ACTION if op == TICK else ACK): raise RuntimeError('reply opcode')
                    return val
            time.sleep(.005)
        raise RuntimeError('PERCIBE-X bridge timeout')

    class Backend(runner.Backend):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw); state['backend'] = self

    class Driver(runner.ConfiguredDriver):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw); state['driver'] = self

        def reposition(self, lat, lon, alt, yaw):
            state['goal'] = (lat, lon, alt, yaw)
            return super().reposition(lat, lon, alt, yaw)

    def inspect(view):
        driver, backend, goal = state['driver'], state['backend'], state['goal']
        if driver is None or backend is None or goal is None: raise RuntimeError('inspection context')
        samples = []
        begin = backend.now_ns()
        def wait_for(condition):
            end, wall = backend.now_ns()+6_000_000_000, time.monotonic()+12
            reached = None
            while backend.now_ns() < end and time.monotonic() < wall:
                body, sim, _ = backend.snapshot()
                if body:
                    samples.append([sim]+[int(round(x*1_000_000)) for x in body[1:]])
                    if condition(body, sim):
                        reached = reached or sim
                        if sim-reached >= 200_000_000: return True
                    else: reached = None
                driver.drain(); time.sleep(.01)
            return False
        if not getattr(driver, 'percibex_attitude_requested', False):
            # Private actor telemetry, never a learner input. Request the
            # standard ATTITUDE stream explicitly rather than assume defaults.
            command = runner.mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL
            driver._cmd(command, 30., 50000.)
            driver._ack(command, 3)
            driver.percibex_attitude_requested = True
        attitude = driver.conn.recv_match(type='ATTITUDE', blocking=True, timeout=3)
        if attitude is None or not math.isfinite(attitude.yaw):
            original_emit(dict(ev='percibex_inspection', view=view, begin_ns=begin, out_begin_ns=begin,
                turn_ns=backend.now_ns(), end_ns=backend.now_ns(), ack_baseline=False,
                baseline_stable=False, ack_out=False, ack_back=False, outward=False, returned=False,
                success=False, samples=samples, baseline_yaw_urad=None, baseline_ned_urad=None,
                cause='no_fresh_attitude'))
            return False
        baseline_ned = float(attitude.yaw)
        ack_baseline = driver.reposition(*goal[:3], baseline_ned)
        recent = []
        def stable(body, sim):
            recent.append((sim, body[6]))
            while recent and sim-recent[0][0] > 400_000_000: recent.pop(0)
            return bool(recent and sim-recent[0][0] >= 300_000_000 and
                        max(abs(yaw_delta(y,body[6])) for t,y in recent) <= .03)
        baseline_stable = wait_for(stable)
        body, _, _ = backend.snapshot()
        baseline_yaw = body[6] if body else 0.
        out_begin = backend.now_ns()
        target_ned = yaw_target(baseline_ned)
        ack_out = driver.reposition(*goal[:3], target_ned)
        out = wait_for(lambda body,sim: inspection_angle_ok(yaw_delta(body[6],baseline_yaw)))
        turn_ns = backend.now_ns()
        ack_back = driver.reposition(*goal[:3], baseline_ned)
        back = wait_for(lambda body,sim: abs(yaw_delta(body[6],baseline_yaw)) <= .12)
        end = backend.now_ns()
        bounded_out = bool(out and all(abs(yaw_delta(s[6]/1000000,baseline_yaw)) <= .52
                                      for s in samples if out_begin <= s[0] <= turn_ns))
        success = bool(ack_baseline and baseline_stable and ack_out and ack_back and bounded_out and back)
        original_emit(dict(ev='percibex_inspection', view=view, begin_ns=begin, turn_ns=turn_ns,
                           end_ns=end, out_begin_ns=out_begin, ack_baseline=ack_baseline,
                           baseline_stable=baseline_stable, baseline_yaw_urad=round(baseline_yaw*1000000),
                           baseline_ned_urad=round(baseline_ned*1000000), target_ned_urad=round(target_ned*1000000),
                           ack_out=ack_out, ack_back=ack_back, outward=bounded_out, returned=back,
                           success=success, samples=samples))
        return success

    def emit(event):
        original_emit(event)
        if event.get('ev') == 'stage' and event.get('stage') == 'survey':
            exchange(SCHOOL)
        elif event.get('ev') == 'survey_leg':
            action = exchange(TICK)
            original_emit(dict(ev='percibex_action', view=event['view'], action=action,
                               seq=state['seq'], sim_time_ns=state['backend'].now_ns()))
            if action:
                success = inspect(event['view'])
                exchange(RECEIPT, int(success))
            if event['view'] == 31: exchange(FREEZE)

    def popen(argv, *a, **kw):
        # Frozen TAP restarts its own source file for the channel. In a zipapp
        # that file is an import path, so restart the archive entry point.
        if len(argv) > 2 and str(argv[1]).endswith('/frozen_tap.py'):
            argv = list(argv); argv[1] = sys.argv[0]
        return original_popen(argv, *a, **kw)

    runner.Backend, runner.ConfiguredDriver, runner.emit = Backend, Driver, emit
    tap.subprocess.Popen = popen
    return tap.flight(json.loads(sys.argv[1]))
