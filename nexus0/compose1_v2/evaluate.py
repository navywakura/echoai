"""Private adjudication; geometry never enters the decision process."""
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from .controller import Composer
from .perception import project, grid
from .space import Space, source_sdf
from .space import DIRECTIONS
from echoai.core.wsp import pack


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def body_clearance(source, records, changes=()):
    root = ET.fromstring(source)
    boxes = []
    for model in root.findall('.//world/model'):
        if model.attrib['name'] == 'floor':
            continue
        centre = [float(v) for v in model.findtext('pose').split()[:3]]
        size = [float(v) for v in model.findtext('./link/collision/geometry/box/size').split()]
        boxes.append((model.attrib['name'], centre, size))
    minimum = math.inf
    unsafe = 0
    max_speed = 0
    last = None
    for row in records:
        p = row['body'][1:4]
        t = row['body'][0]
        if last and t > last[0]:
            max_speed = max(max_speed, math.hypot(p[0]-last[1], p[1]-last[2])*1e12/(t-last[0]))
        last = (t, p[0], p[1])
        active = {c['entity']: c['observed'] for c in changes if row['now_ns'] >= c['now_ns']}
        nearest = min(math.sqrt(sum(max(abs(p[i]-c[i])-s[i]/2, 0)**2 for i in range(3)))
                      for name, original, s in boxes for c in [active.get(name, original)])
        minimum = min(minimum, nearest)
        unsafe += nearest < .4
    return dict(min_clearance_mm=round(minimum*1000) if records else None,
                unsafe_samples=unsafe, samples=len(records), max_horizontal_speed_mm_s=round(max_speed))


def audit_session(root):
    root = Path(root)
    config = json.loads((root/'configuration.json').read_text())
    source = (root/'source.sdf').read_bytes()
    snapshot = json.loads((root/'training.json').read_text())
    world = Space(config['seed'], config['condition'])
    agent = Composer(snapshot, world.goal, config['mode'])
    baseline = agent.model.fingerprint()
    journal = read_lines(root/'journal.jsonl')
    backend = read_lines(root/'out/mission.jsonl')
    truth = read_lines(root/'out/private.jsonl')
    result = json.loads((root/'out/result.json').read_text())
    findings = []
    failures = []
    if hashlib.sha256(source).hexdigest() != config['source_sha256']:
        findings.append('source_hash')
    if source_sdf(world) != source:
        findings.append('declared_world_geometry')
    observations = [r['event'] for r in journal if r['side'] == 'backend' and r['event'].get('kind') == 'observation']
    responses = [r for r in journal if r['side'] == 'agent']
    sensor_records = [r for r in backend if r['kind'] == 'observation']
    commands = [r for r in backend if r['kind'] == 'command']
    acks = [r for r in backend if r['kind'] == 'ack']
    origins = [r for r in backend if r['kind'] == 'odometry_origin']
    causal_order = [r['kind'] for r in backend if r['kind'] in ('observation', 'command', 'ack')]
    wanted_order = [kind for _ in acks for kind in ('observation', 'command', 'ack')]
    wanted_order += ['observation', 'command']
    if causal_order != wanted_order or len(commands) != len(responses) or len(origins) != 1:
        findings.append('causal_event_order')
    public_order = [('observation', r['event']['epoch']) if r['side'] == 'backend' else
                    ('response', r['epoch']) for r in journal
                    if r['side'] == 'agent' or r['event'].get('kind') == 'observation']
    if public_order != [(kind, i) for i in range(len(observations)) for kind in ('observation', 'response')]:
        findings.append('journal_event_order')
    if len(observations) != len(responses) or observations != sensor_records:
        findings.append('observation_transport')
    energy = world.energy
    previous = None
    inspection = 0
    movements = 0
    status = None
    reserve_violations = 0
    target = (0, 0, 0)
    for i, (obs, response) in enumerate(zip(observations, responses)):
        if previous:
            energy -= 4 if previous[1] == 11 else 1
        frame = project(obs['raw'], energy)
        if grid(obs['raw']['estimate']['position_mm']) == world.goal and not frame['station_observed']:
            agent.update(frame)
            if inspection < 4:
                w = pack(src=2, rel=14, dst=5, time=8, E={}, domain=9, generator=8, style=7+inspection)
                inspection += 1
                expected = dict(wsp=w.hex(), status='inspect_target', plan=[], depth=0,
                                candidates=0, model_sha256=agent.model.fingerprint())
            else:
                expected = agent.output(6, [], 'target_unverified', 0)
        else:
            expected = agent.decide(frame)
        expected['frame'] = frame
        if response['epoch'] != i or obs['epoch'] != i or response['response'] != expected:
            findings.append(f'decision_{i}')
        previous = bytes.fromhex(expected['wsp'])
        status = expected['status']
        if i >= len(commands) or commands[i]['wsp'] != expected['wsp']:
            findings.append(f'causal_wsp_{i}')
        elif commands[i]['now_ns'] < obs['raw']['now_ns']:
            findings.append(f'publication_order_{i}')
        if expected['model_sha256'] != baseline or expected.get('imagined_writes', 0):
            findings.append(f'learning_during_exam_{i}')
        movements += previous[1] == 11
        if i < len(acks):
            ack = acks[i]
            if previous[1] == 11:
                current = grid(obs['raw']['estimate']['position_mm'])
                delta = DIRECTIONS[previous[13]]
                target = tuple(a+b for a, b in zip(current, delta))
                moved = any(r['kind'] == 'world_change' and r['now_ns'] <= obs['raw']['now_ns'] for r in backend)
                world.solids = world.make_solids(-world.gap_y if moved else
                                                None if world.condition == 'closed' else world.gap_y)
                home = world.home_distance(target)
                reserve_violations += home is None or energy-4 < home*4+10
            if origins:
                expected_target = [round(origins[0]['value'][axis]*1000+target[axis]*3000) for axis in (0, 1)]
                if ack['target_local_mm'] != expected_target:
                    findings.append(f'ack_target_{i}')
            if ack['epoch'] != i or ack['now_ns'] < commands[i]['now_ns']:
                findings.append(f'ack_order_{i}')
    changes = [r for r in backend if r['kind'] == 'world_change']
    if world.condition == 'dynamic':
        intervention = config['world_intervention']
        if len(changes) != 1 or not result.get('world_change_observed'):
            failures.append('missing_world_intervention')
        elif changes[0]['entity'] != intervention['entity'] or changes[0]['target'] != intervention['target'] or any(
                abs(a-b) > .01 for a, b in zip(changes[0]['observed'], intervention['target'])):
            findings.append('world_intervention_mismatch')
    elif changes:
        findings.append('unexpected_world_intervention')
    clearance = body_clearance(source, truth, changes)
    if clearance['unsafe_samples']:
        failures.append('body_envelope')
    if clearance['max_horizontal_speed_mm_s'] > 3000:
        failures.append('discontinuous_or_excessive_body_motion')
    if any(not a['accepted'] for a in acks):
        failures.append('rejected_command')
    if len(acks) != max(0, len(commands)-1) or movements != result['steps']:
        findings.append('execution_denominator')
    if not result['ok'] or not result.get('disarmed') or result.get('body_pose_writes') != 0:
        failures.append('flight_execution')
    ulog_path = Path(result.get('ulog', '').replace('/out/', str(root/'out')+'/'))
    if not ulog_path.is_file() or hashlib.sha256(ulog_path.read_bytes()).hexdigest() != result.get('ulog_sha256'):
        findings.append('ulog_hash')
    else:
        findings.extend(ulog_check(ulog_path, result, observations, origins))
    # Independent observed-pose judge, never used for commanding the body.
    goal_mm = [c*3000 for c in world.goal[:2]]
    arrived = False
    ended_home = False
    if observations:
        end = observations[-1]['raw']['now_ns']
        near = min(truth, key=lambda r: abs(r['now_ns']-end))
        error = math.hypot(near['body'][1]*1000-goal_mm[0], near['body'][2]*1000-goal_mm[1])
        arrived = status == 'reached' and error <= 1000
        ended_home = math.hypot(near['body'][1], near['body'][2]) <= 1
        if status == 'reached' and not arrived:
            failures.append('false_arrival')
    if reserve_violations:
        failures.append('reserve')
    if world.condition == 'low_energy' and (not ended_home or movements or status != 'abandoned_at_home'):
        failures.append('low_energy_abort')
    return dict(evidence_valid=not findings, findings=findings, status=status,
                execution_green=not failures, failures=failures, ended_home=ended_home,
                reserve_violations=reserve_violations,
                reached=arrived, movements=movements, energy_remaining=energy,
                clearance=clearance, px4_acknowledgements=len(acks))


def ulog_check(path, result, observations, origins):
    """Independent PX4 source binds commands and public estimator samples."""
    from pyulog import ULog
    log = ULog(str(path))
    data = {d.name: d.data for d in log.data_list}
    required = ('vehicle_status', 'actuator_motors', 'vehicle_command', 'vehicle_local_position')
    if any(name not in data for name in required):
        return ['ulog_missing_topics']
    issues = []
    if 2 not in data['vehicle_status']['arming_state'] or not any(
            math.isfinite(float(v)) and v > .05 for v in data['actuator_motors']['control[0]']):
        issues.append('ulog_no_motor_flight')
    commands = data['vehicle_command']
    actual = [i for i, command in enumerate(commands['command']) if command == 192 and commands['from_external'][i]]
    expected = [e for e in result['driver_events'] if e['event'] == 'reposition']
    if len(actual) != len(expected):
        issues.append('ulog_command_count')
    for i, event in zip(actual, expected):
        if any(abs(float(commands[field][i])-value) > tolerance for field, value, tolerance in (
            ('param5', event['lat'], 2e-7), ('param6', event['lon'], 2e-7),
            ('param7', event['alt_msl_m'], .001), ('param4', event['yaw'], .0001))):
            issues.append('ulog_command_value')
            break
    local = data['vehicle_local_position']
    if origins:
        import numpy as np
        for obs in observations:
            e = obs['raw']['estimate']
            index = int(np.argmin(abs(local['timestamp'].astype('int64')-e['px4_boot_ms']*1000)))
            sample = (local['y'][index], local['x'][index], -local['z'][index])
            expected_mm = [(float(v)-offset)*1000 for v, offset in zip(sample, origins[0]['value'])]
            if abs(int(local['timestamp'][index])-e['px4_boot_ms']*1000) > 50_000 or any(
                    abs(a-b) > 50 for a, b in zip(e['position_mm'], expected_mm)):
                issues.append('ulog_estimate_binding')
                break
    return issues
