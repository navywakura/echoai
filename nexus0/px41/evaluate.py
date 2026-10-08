"""Reconstruct the gate and check independent PX4 ULog/physical evidence."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from pyulog import ULog

from .core import Gateway
from .session import HERE, ECHOAI, CONDITIONS


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(root):
    root = Path(root)
    findings = []
    metrics = {}

    def check(condition, label):
        if not condition:
            findings.append(label)

    try:
        cfg = json.loads((root/'configuration.json').read_text())
        result = json.loads((root/'out/result.json').read_text())
        check(result['ok'] is True, 'runtime_failure')
        check(json.loads((root/'session.json').read_text())['returncode'] == 0, 'container_exit')
        check(cfg['condition'] in CONDITIONS and cfg['physics_seed'] == cfg['seed']*10+CONDITIONS.index(cfg['condition']), 'seed')
        from echoai.nexus0.compose1_v3.space import source_sdf, Space
        from echoai.nexus0.compose1_v3.rig import models
        from echoai.nexus0.flight1s.worldbuild import build_effective
        from echoai.nexus0.pattern1r_v4.contract import configuration
        source = source_sdf(Space(0), empty=True)
        check((root/'source.sdf').read_bytes() == source, 'world_source')
        check((root/'world.sdf').read_bytes() == build_effective(source, hashlib.sha256(source).hexdigest()).data, 'world_effective')
        check(cfg['flight'] == configuration(), 'flight_configuration')
        check(cfg['runtime'] == json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container'], 'runtime_identity')
        for name, content in models().items():
            check((root/'models'/name).read_text() == content, 'model:'+name)
        for source_path, dest in [(HERE/'assets/runner.py', 'runner.py'), (HERE/'core.py', 'echoai/nexus0/px41/core.py'),
                         (HERE.parent/'cause1/core.py', 'echoai/nexus0/cause1/core.py'),
                         (HERE.parent/'compose1_v3/assets/live_runner.py', 'live_runner.py'),
                         (HERE.parent/'pattern1r_v4/assets/flightrunner_survey.py', 'flightrunner_survey.py')]:
            check(digest(source_path) == digest(root/dest), 'source:'+dest)
        rows = [json.loads(x) for x in (root/'out/trace.jsonl').read_text().splitlines()]
        check(all(a['now_ns'] <= b['now_ns'] for a, b in zip(rows, rows[1:])), 'trace_clock')
        groups = {}
        for row in rows:
            groups.setdefault(row['kind'], []).append(row)
        check(not groups.get('failure'), 'trace_failure')
        gate = Gateway()
        for row in rows:
            kind = row['kind']
            if kind == 'proposal':
                check(gate.propose(row['request'], row['frame'], row['gate_now_ns']) == row['decision'], 'gate_replay')
            elif kind == 'ack':
                check(gate.acknowledge(row['ack'], row['gate_now_ns']) == row['accepted'] and gate.state == row['state'], 'ack_replay')
            elif kind == 'observe':
                check(gate.observe(row['frame'], row['gate_now_ns']) == row['state'], 'arrival_replay')
            elif kind == 'send':
                check(gate.state == 'await_ack' and gate.pending['wsp'] == row['wsp']
                      and gate.pending['target_mm'] == row['target_mm'], 'send_binding')
            elif kind == 'complete':
                check(gate.state == 'complete', 'false_completion')
        proposals = groups['proposal']
        check([r['label'] for r in proposals] == ['malformed', 'expired', 'authority', 'envelope', 'legal', 'busy', 'replay'], 'probe_inventory')
        check([r['decision']['allowed'] for r in proposals] == [False]*4+[True, False, False], 'illegal_accepted')
        for kind in ('send', 'ack', 'complete', 'disarmed', 'origin'):
            check(len(groups[kind]) == 1, 'count:'+kind)
        send, ack, done = groups['send'][0], groups['ack'][0], groups['complete'][0]
        check(send['now_ns'] < ack['ack']['received_ns'] < done['now_ns'], 'chronology')
        from echoai.nexus0.cause1.core import wsp
        check(send['wsp'] == wsp(0 if cfg['seed'] % 2 else 1), 'intention')
        origin = groups['origin'][0]['value']
        fix, local = send['reference']['fix'], send['reference']['local']
        east, north, height = [v/1000 for v in send['target_mm']]
        expected = [fix['lat']/1e7+(north+origin[1]-local['x'])/111320,
                    fix['lon']/1e7+(east+origin[0]-local['y'])/(111320*math.cos(math.radians(fix['lat']/1e7))),
                    fix['alt']/1000+local['z']+origin[2]+height]
        check(all(abs(send[k]-v) < 1e-8 for k, v in zip(('lat', 'lon', 'alt'), expected)), 'coordinate_conversion')
        ulogs = list(root.rglob('*.ulg'))
        check(len(ulogs) == 1, 'ulog_count')
        check(digest(ulogs[0]) == result['ulog_sha256'], 'ulog_hash')
        ulog = ULog(str(ulogs[0]))
        commands = ulog.get_dataset('vehicle_command').data
        external = commands['from_external'] == 1
        check(set(map(int, commands['command'][external])) <= {176, 192, 400, 21}, 'forbidden_command')
        arm = external & (commands['command'] == 400)
        check(int(arm.sum()) == 1 and bool(np.all(commands['param1'][arm] == 1))
              and bool(np.all(commands['param2'][arm] == 0)), 'forced_arm_or_disarm')
        repos = external & (commands['command'] == 192)
        check(int(repos.sum()) == 1, 'ulog_reposition_count')
        for key, value, tolerance in [('param5', send['lat'], 2e-7), ('param6', send['lon'], 2e-7),
                                       ('param7', send['alt'], .001), ('param1', 1., .001),
                                       ('param2', 1., .001), ('param4', send['yaw'], .001)]:
            check(bool(np.all(np.abs(commands[key][repos]-value) <= tolerance)), 'ulog_goal:'+key)
        check(abs(int(commands['timestamp'][repos][0])*1000-send['now_ns']) <= 100_000_000, 'ulog_send_clock')
        acks = ulog.get_dataset('vehicle_command_ack').data
        selected = acks['command'] == 192
        check(list(map(int, acks['result'][selected])) == [0], 'ulog_ack')
        check(abs(int(acks['timestamp'][selected][0])*1000-ack['ack']['received_ns']) <= 100_000_000, 'ulog_ack_clock')
        # Bind every observed estimate to the flight controller's own estimator.
        positions = ulog.get_dataset('vehicle_local_position').data
        samples = [r for r in groups['sample'] if r['estimate']]
        for sample in samples:
            est = sample['estimate']
            index = int(np.argmin(abs(positions['timestamp'].astype(np.int64)-est['px4_boot_ms']*1000)))
            check(abs(int(positions['timestamp'][index])-est['px4_boot_ms']*1000) <= 60000, 'odometry_time')
            xyz = [positions['y'][index]-origin[0], positions['x'][index]-origin[1], -positions['z'][index]-origin[2]]
            check(max(abs(a*1000-b) for a, b in zip(xyz, est['position_mm'])) <= 60, 'odometry_value')
        # The gate's frames must be live samples, not fabricated acceptance flags.
        for row in groups['observe']+[r for r in proposals if r['label'] == 'legal']:
            preceding = [s for s in samples if s['now_ns'] <= row['gate_now_ns']]
            sample = preceding[-1]
            check(row['gate_now_ns']-sample['now_ns'] <= 100_000_000, 'frame_sample_age')
            check(max(abs(a-b) for a, b in zip(row['frame']['position_mm'], sample['estimate']['position_mm'])) <= 100, 'frame_position')
            hb = sample['heartbeat']
            check(hb['system_status'] == 4 and bool(hb['base_mode'] & 128) and sample['heartbeat_wall_age_ms'] <= 2000, 'frame_authority')
        status = ulog.get_dataset('vehicle_status').data
        window = (status['timestamp']*1000 >= send['now_ns']) & (status['timestamp']*1000 <= done['now_ns'])
        check(bool(window.any()) and bool(np.all(status['failsafe'][window] == 0)), 'failsafe_during_goal')
        motors = ulog.get_dataset('actuator_motors').data
        check(bool(np.any(motors['control[0]'] > .05)), 'no_motor_execution')
        landed = groups['disarmed'][0]['now_ns']
        tail = (status['timestamp']*1000 >= done['now_ns']) & (status['timestamp']*1000 <= landed+100_000_000)
        check(bool(np.any(status['arming_state'][tail] == 1)), 'ulog_not_disarmed')
        land_commands = external & (commands['command'] == 21)
        if cfg['condition'] == 'link_loss':
            check(len(groups.get('heartbeat_cut', [])) == 1 and not groups.get('land_request'), 'cut_protocol')
            cut = groups['heartbeat_cut'][0]['now_ns']
            check(not any(r['now_ns'] > cut for r in groups['gcs_heartbeat']), 'heartbeat_after_cut')
            check(not bool(land_commands.any()), 'failsafe_bypass_land_command')
            lost = tail & (status['gcs_connection_lost'] == 1) & (status['failsafe'] == 1) & (status['nav_state'] == 18)
            check(bool(lost.any()), 'missing_PX4_failsafe_land')
            check(0 < landed-cut <= 35_000_000_000, 'failsafe_deadline')
            metrics['failsafe_disarm_ms'] = (landed-cut)//1_000_000
        else:
            check(not groups.get('heartbeat_cut') and int(land_commands.sum()) == 1, 'nominal_land')
        for name, wanted in [('NAV_DLL_ACT', 3), ('COM_DL_LOSS_T', 5)]:
            values = [v for _, n, v in ulog.changed_parameters if n == name]
            actual = values[-1] if values else ulog.initial_parameters.get(name)
            check(actual == wanted, 'ulog_parameter:'+name)
        active = [s for s in samples if send['now_ns'] <= s['now_ns'] <= done['now_ns']]
        before = [s for s in samples if s['now_ns'] <= send['now_ns']][-1]
        after = min(samples, key=lambda s: abs(s['now_ns']-done['now_ns']))
        shift = 1 if cfg['seed'] % 2 else -1
        error = math.hypot(after['body'][1]-before['body'][1], after['body'][2]-before['body'][2]-shift)
        metrics['true_goal_error_mm'] = round(error*1000)
        check(error <= .5, 'physical_arrival')
        check(all(1.8 <= s['body'][3] <= 3.2 and s['estimate']['speed_mm_s'] <= 3000 for s in active), 'physical_envelope')
        metrics.update(blocked=6, sent=1, completed=1)
    except Exception as exc:
        findings.append('audit_exception:'+repr(exc))
    return dict(valid=not findings, findings=sorted(set(findings)), **metrics)
