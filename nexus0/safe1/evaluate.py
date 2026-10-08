"""Read-only replay, source binding and independent PX4 evidence."""
import json
import math
from pathlib import Path
import numpy as np
from pyulog import ULog
from echoai.nexus0.px41.evaluate import digest
from echoai.nexus0.cause1.core import wsp
from echoai.nexus0.safe1.core import Supervisor, Lease
from echoai.nexus0.safe1.session import CONDITIONS, SOURCES, ECHOAI, world


def audit(root):
    root = Path(root)
    findings = []
    metrics = {}

    def check(ok, label):
        if not ok:
            findings.append(label)

    try:
        cfg = json.loads((root/'configuration.json').read_text())
        result = json.loads((root/'out/result.json').read_text())
        check(result['ok'] is True, 'runtime_failure')
        check(json.loads((root/'session.json').read_text())['returncode'] == 0, 'container_exit')
        check(cfg['condition'] in CONDITIONS and cfg['physics_seed'] == cfg['seed']*10+CONDITIONS.index(cfg['condition']), 'seed')
        from echoai.nexus0.compose1_v3.rig import models
        from echoai.nexus0.pattern1r_v4.contract import configuration
        source, effective = world()
        check((root/'source.sdf').read_bytes() == source and (root/'world.sdf').read_bytes() == effective, 'world')
        check(cfg['flight'] == configuration(), 'flight_configuration')
        check(cfg['runtime'] == json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container'], 'runtime_identity')
        for name, content in models().items():
            check((root/'models'/name).read_text() == content, 'model:'+name)
        for dest, source in SOURCES.items():
            check(digest(source) == digest(root/dest), 'source:'+dest)
        rows = [json.loads(line) for line in (root/'out/trace.jsonl').read_text().splitlines()]
        check(all(a['now_ns'] <= b['now_ns'] and a['wall_ns'] <= b['wall_ns'] for a, b in zip(rows, rows[1:])), 'trace_clock')
        groups = {}
        supervisor = Supervisor(json.loads((root/'model.json').read_text()))
        lease = Lease()
        for row in rows:
            kind = row['kind']
            groups.setdefault(kind, []).append(row)
            if kind == 'check':
                check(supervisor.check(row['health']) == row['ok'] and supervisor.gateway.state == row['state'], 'health_replay')
            elif kind == 'proposal':
                check(supervisor.submit(row['request'], row['health'], row['energy']) == row['decision'], 'proposal_replay')
            elif kind == 'ipc_error':
                supervisor.trip(row['reason'])
            elif kind == 'ack':
                check(supervisor.acknowledge(row['ack'], row['ack_now_ns']) == row['accepted'], 'ack_replay')
            elif kind == 'send':
                check(not supervisor.tripped and supervisor.gateway.state == 'await_ack'
                      and supervisor.gateway.pending['wsp'] == row['wsp']
                      and supervisor.gateway.pending['target_mm'] == row['target_mm'], 'send_permission')
            elif kind == 'complete':
                check(supervisor.gateway.state == 'complete' and not supervisor.tripped, 'false_completion')
            elif kind == 'veto':
                check(supervisor.tripped and supervisor.reason == row['reason'], 'false_veto')
            elif kind == 'lease_renew':
                check(lease.renew(row['lease_now_ns']) == row['allowed'], 'lease_replay')
            elif kind == 'gcs_heartbeat':
                check(lease.allowed(row['lease_now_ns']), 'heartbeat_without_permission')
            elif kind == 'heartbeat_cut':
                lease.cancel()
        check(not groups.get('failure'), 'trace_failure')
        for kind in ('origin', 'supervision_start', 'disarmed'):
            check(len(groups[kind]) == 1, 'count:'+kind)
        start = groups['supervision_start'][0]['now_ns']
        landed = groups['disarmed'][0]['now_ns']
        fault = cfg['condition'] != 'nominal'
        check(len(groups.get('send', [])) == (0 if fault else 1), 'send_count')
        check(len(groups.get('injection', [])) == int(fault), 'injection_count')
        check(len(groups.get('complete', [])) == int(not fault), 'complete_count')
        origin = groups['origin'][0]['value']
        samples = [r for r in groups['sample'] if r['estimate']]
        # Bind private live samples to ULog, then health to private samples.
        ulogs = list(root.rglob('*.ulg'))
        check(len(ulogs) == 1 and digest(ulogs[0]) == result['ulog_sha256'], 'ulog_hash')
        ulog = ULog(str(ulogs[0]))
        positions = ulog.get_dataset('vehicle_local_position').data
        for sample in samples:
            est = sample['estimate']
            index = int(np.argmin(abs(positions['timestamp'].astype(np.int64)-est['px4_boot_ms']*1000)))
            check(abs(int(positions['timestamp'][index])-est['px4_boot_ms']*1000) <= 60000, 'odometry_time')
            xyz = [positions['y'][index]-origin[0], positions['x'][index]-origin[1], -positions['z'][index]-origin[2]]
            check(max(abs(a*1000-b) for a, b in zip(xyz, est['position_mm'])) <= 60, 'odometry_value')
        injection = groups.get('injection', [None])[0]
        for row in groups.get('check', [])+groups.get('proposal', []):
            h = row['health']
            # After latching, health is explicitly ignored, never authority to recover.
            if groups.get('veto') and row['now_ns'] >= groups['veto'][0]['now_ns']:
                continue
            preceding = [s for s in samples if s['now_ns'] <= h['now_ns']]
            sample = preceding[-1]
            check(h['now_ns']-sample['now_ns'] <= 100_000_000, 'health_sample_age')
            check(max(abs(a-b) for a, b in zip(h['frame']['position_mm'], sample['estimate']['position_mm'])) <= 100, 'health_position')
            injected = injection is not None and row['wall_ns'] >= injection['wall_ns']
            if not (injected and cfg['condition'] == 'sensor_stale'):
                check(abs(h['sensor_ns']-sample['sensor_ns']) <= 100_000_000, 'health_sensor')
            if not (injected and cfg['condition'] == 'network_stale'):
                check(abs(h['frame']['received_ns']-sample['estimate']['received_ns']) <= 100_000_000, 'health_link')
            hb = sample['heartbeat']
            check(hb['system_status'] == 4 and bool(hb['base_mode'] & 128) and sample['heartbeat_wall_age_ms'] <= 2000, 'health_authority')
        commands = ulog.get_dataset('vehicle_command').data
        external = commands['from_external'] == 1
        check(set(map(int, commands['command'][external])) <= {176, 192, 400, 21}, 'forbidden_command')
        arm = external & (commands['command'] == 400)
        check(int(arm.sum()) == 1 and bool(np.all(commands['param1'][arm] == 1))
              and bool(np.all(commands['param2'][arm] == 0)), 'forced_arm_or_disarm')
        repos = external & (commands['command'] == 192)
        check(int(repos.sum()) == int(not fault), 'ulog_reposition_count')
        land_commands = external & (commands['command'] == 21)
        status = ulog.get_dataset('vehicle_status').data
        tail = (status['timestamp']*1000 >= start) & (status['timestamp']*1000 <= landed+100_000_000)
        check(bool(np.any((status['arming_state'] == 1) & tail)), 'ulog_not_disarmed')
        motors = ulog.get_dataset('actuator_motors').data
        check(bool(np.any(motors['control[0]'] > .05)), 'no_motor_execution')
        for name, wanted in [('NAV_DLL_ACT', 3), ('COM_DL_LOSS_T', 5)]:
            values = [v for _, n, v in ulog.changed_parameters if n == name]
            check((values[-1] if values else ulog.initial_parameters.get(name)) == wanted, 'parameter:'+name)
        if fault:
            check(injection['condition'] == cfg['condition'], 'fault_identity')
            check(len(groups['veto']) == 1 and len(groups['heartbeat_cut']) == 1, 'latch_count')
            veto = groups['veto'][0]
            cut = groups['heartbeat_cut'][0]
            check(all(r['wall_ns'] < cut['wall_ns'] for r in groups['gcs_heartbeat']), 'heartbeat_after_cut')
            check(not groups.get('land_request') and not bool(land_commands.any()), 'external_rescue')
            check(0 <= veto['wall_ns']-injection['wall_ns'] <= 750_000_000
                  and 0 <= veto['now_ns']-injection['now_ns'] <= 750_000_000, 'veto_deadline')
            check(0 < landed-veto['now_ns'] <= 35_000_000_000, 'landing_deadline')
            native = tail & (status['timestamp']*1000 >= veto['now_ns']) & (status['gcs_connection_lost'] == 1) & (status['failsafe'] == 1) & (status['nav_state'] == 18)
            check(bool(native.any()), 'missing_native_failsafe')
            check(len([r for r in groups['proposal'] if r['wall_ns'] > veto['wall_ns'] and not r['decision']['allowed']]) == 2, 'recovery_probes')
            expected = {'sensor_stale': 'sensor_stale', 'network_stale': 'link_or_authority',
                        'process_exit': 'ipc_eof', 'process_hang': 'ipc_timeout', 'bad_proposal': 'proposal_rejected'}
            check(veto['reason'] == expected[cfg['condition']], 'fault_reason')
            if cfg['condition'] in ('sensor_stale', 'network_stale'):
                checks = [r for r in groups['check'] if injection['wall_ns'] < r['wall_ns'] < veto['wall_ns']]
                observed = [r['health']['sensor_ns'] if cfg['condition'] == 'sensor_stale'
                            else r['health']['frame']['received_ns'] for r in checks]
                check(bool(observed) and len(set(observed)) == 1, 'frozen_delivery')
                check(checks[-1]['health']['now_ns']-observed[-1] > 250_000_000, 'fault_not_stale')
                private = [s for s in samples if injection['now_ns'] <= s['now_ns'] <= veto['now_ns']]
                live = [s['sensor_ns'] if cfg['condition'] == 'sensor_stale' else s['estimate']['received_ns'] for s in private]
                check(bool(live) and max(live) > observed[-1], 'private_stream_not_live')
            if cfg['condition'].startswith('process_'):
                check(len(groups.get('ipc_error', [])) == 1 and groups['ipc_error'][0]['elapsed_ns'] <= 450_000_000, 'ipc_deadline')
            metrics.update(veto_ms=(veto['wall_ns']-injection['wall_ns'])//1_000_000,
                           failsafe_disarm_ms=(landed-veto['now_ns'])//1_000_000)
        else:
            check(not groups.get('heartbeat_cut') and int(land_commands.sum()) == 1, 'nominal_landing')
            send = groups['send'][0]
            check(send['wsp'] == wsp(cfg['seed'] % 2), 'intention')
            fix, local = send['reference']['fix'], send['reference']['local']
            east, north, height = [v/1000 for v in send['target_mm']]
            expected = [fix['lat']/1e7+(north+origin[1]-local['x'])/111320,
                        fix['lon']/1e7+(east+origin[0]-local['y'])/(111320*math.cos(math.radians(fix['lat']/1e7))),
                        fix['alt']/1000+local['z']+origin[2]+height]
            check(all(abs(send[k]-v) < 1e-8 for k, v in zip(('lat', 'lon', 'alt'), expected)), 'conversion')
            for key, value, tolerance in [('param5', send['lat'], 2e-7), ('param6', send['lon'], 2e-7),
                                           ('param7', send['alt'], .001), ('param1', 1., .001),
                                           ('param2', 1., .001), ('param4', send['yaw'], .001)]:
                check(bool(np.all(np.abs(commands[key][repos]-value) <= tolerance)), 'ulog_goal:'+key)
            check(abs(int(commands['timestamp'][repos][0])*1000-send['now_ns']) <= 100_000_000, 'ulog_send_clock')
            acks = ulog.get_dataset('vehicle_command_ack').data
            selected = acks['command'] == 192
            check(list(map(int, acks['result'][selected])) == [0], 'ulog_ack')
            check(len(groups['ack']) == 1 and abs(int(acks['timestamp'][selected][0])*1000-groups['ack'][0]['ack_now_ns']) <= 100_000_000, 'ulog_ack_clock')
            done = groups['complete'][0]['now_ns']
            window = (status['timestamp']*1000 >= start) & (status['timestamp']*1000 <= done)
            check(bool(window.any()) and bool(np.all(status['failsafe'][window] == 0)), 'failsafe_nominal')
            before = [s for s in samples if s['now_ns'] <= send['now_ns']][-1]
            after = min(samples, key=lambda s: abs(s['now_ns']-done))
            error = math.hypot(after['body'][1]-before['body'][1], after['body'][2]-before['body'][2]-(1 if cfg['seed'] % 2 == 0 else -1))
            check(error <= .5, 'physical_arrival')
            metrics['true_goal_error_mm'] = round(error*1000)
        active = [s for s in samples if start <= s['now_ns'] <= landed]
        # True origin is simulator spawn (0,0); no feedback uses this value.
        check(bool(active) and all(math.hypot(s['body'][1], s['body'][2]) <= 2 and s['body'][3] <= 3.2 for s in active), 'physical_envelope')
        metrics.update(sent=int(repos.sum()), native_land=int(fault))
    except Exception as exc:
        findings.append('audit_exception:'+repr(exc))
    return dict(valid=not findings, findings=sorted(set(findings)), **metrics)


if __name__ == '__main__':
    import sys
    result = audit(sys.argv[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['valid'] else 1)
