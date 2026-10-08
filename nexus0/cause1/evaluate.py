"""Reconstruct public attribution and independently judge physical effects."""
import hashlib
import json
from pathlib import Path
from echoai.nexus0.compose1_v3.evaluate import ulog_check
from .core import prepare, attribute
from .perception import project
from .session import settings, source, ECHOAI, build_effective, models, configuration


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def audit_session(root):
    root = Path(root)
    findings, failures = [], []
    config = json.loads((root/'configuration.json').read_text())
    expected = settings(config['seed'], config['condition'])
    if any(config.get(k) != v for k, v in expected.items()):
        findings.append('configuration')
    if (root/'source.sdf').read_bytes() != source(expected):
        findings.append('world_source')
    sdf = source(expected)
    effective = build_effective(sdf, hashlib.sha256(sdf).hexdigest()).data.replace(b'  </world>',
        b'<plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">'
        b'<render_engine>ogre2</render_engine></plugin>\n  </world>')
    if (root/'world.sdf').read_bytes() != effective:
        findings.append('effective_world')
    if any((root/'models'/name).read_text() != content for name, content in models().items()):
        findings.append('sensor_rig')
    runtime = json.loads((ECHOAI/'lab/flight1s-v6/lock.json').read_text())['runtime']['container']
    if config['runtime'] != runtime or config['config'] != configuration():
        findings.append('runtime_configuration')
    session = json.loads((root/'session.json').read_text())
    result = json.loads((root/'out/result.json').read_text())
    if result.get('physics_seed') != config.get('physics_seed'):
        findings.append('physics_seed_binding')
    if session['result'] != dict(kind='result', **result) or session['returncode'] != (0 if result['ok'] else 1):
        findings.append('session_result')
    rows = read_lines(root/'journal.jsonl')
    mission = read_lines(root/'out/mission.jsonl')
    truth = read_lines(root/'out/private.jsonl')
    wanted = ['odometry_origin', 'before', 'command', 'ack']
    if expected['external_mm']:
        wanted += ['world_change']
    wanted += ['after']
    if [r['kind'] for r in mission] != wanted:
        return dict(evidence_valid=False, findings=findings+['event_order'], execution_green=False,
                    failures=['incomplete_flight'], seed=config['seed'], condition=config['condition'])
    by_kind = {r['kind']: r for r in mission}
    before, after = by_kind['before']['raw'], by_kind['after']['raw']
    command, ack = by_kind['command'], by_kind['ack']
    execution = {k: v for k, v in ack.items() if k != 'kind'}
    responses = [r for r in rows if r['side'] == 'agent']
    causal = [r for r in rows if r['side'] == 'agent' or r['event'].get('kind') in ('before', 'after')]
    if [r['side'] for r in causal] != ['backend', 'agent', 'backend', 'agent'] or len(responses) != 2:
        return dict(evidence_valid=False, findings=findings+['public_order'], execution_green=False,
                    failures=['incomplete_consumer'], seed=config['seed'], condition=config['condition'])
    if causal[0]['event'] != dict(kind='before', raw=before) or causal[2]['event'] != dict(
            kind='after', raw=after, execution=execution):
        findings.append('sensor_transport')
    if responses[0]['request'] != dict(intention=config['intention'], before=before) or responses[1]['request'] != dict(
            execution=execution, after=after):
        findings.append('consumer_input')
    first, last = project(before), project(after)
    prepared = prepare(config['intention'], first)
    conclusion = attribute(config['intention'], first, prepared, execution, last)
    if responses[0]['response'] != prepared or responses[1]['response'] != conclusion:
        findings.append('consumer_reconstruction')
    if (command['wsp'] != prepared['wsp'] or command['sent_ns'] != execution['sent_ns']
            or execution['wsp'] != command['wsp']):
        findings.append('executed_wsp')
    if not (before['now_ns'] <= command['sent_ns'] <= ack['ack_ns'] < after['lidar']['capture_ns']):
        findings.append('causal_chronology')
    if not result.get('ok') or not result.get('disarmed') or result.get('body_pose_writes') != 0:
        failures.append('flight_execution')
    if not ack['accepted']:
        failures.append('command_rejected')
    ulog = root/'out'/Path(result.get('ulog', '/missing')).relative_to('/out') if result.get('ulog', '').startswith('/out/') else root/'missing'
    if not ulog.is_file() or hashlib.sha256(ulog.read_bytes()).hexdigest() != result.get('ulog_sha256'):
        findings.append('ulog_hash')
    else:
        findings += ulog_check(ulog, result, [dict(raw=before), dict(raw=after)], [by_kind['odometry_origin']])
        from pyulog import ULog
        data = {d.name: d.data for d in ULog(str(ulog)).data_list}
        confirmations = data.get('vehicle_command_ack', {})
        accepted_codes = [int(confirmations['result'][i]) for i, code in enumerate(confirmations.get('command', []))
                          if code == 192]
        if accepted_codes != [0] or ack['accepted'] is not True:
            findings.append('ulog_ack_binding')
    events = [r for r in rows if r['side'] == 'backend' and r['event'].get('event') == 'reposition']
    if len(events) != 1 or events[0]['event'].get('result') != 0:
        findings.append('mavlink_ack_binding')
    elif not rows.index(responses[0]) < rows.index(events[0]) < rows.index(responses[1]):
        findings.append('prediction_after_execution')
    origin = by_kind['odometry_origin']['value']
    expected_target = [round(origin[0]*1000)+before['estimate']['position_mm'][0],
                       round(origin[1]*1000)+first['north_mm']+(prepared['predicted_north_mm'] or 0)]
    if any(abs(a-b) > 100 for a, b in zip(command['target_local_mm'], expected_target)):
        findings.append('setpoint_intention_binding')
    nearest = [min(truth, key=lambda r: abs(r['now_ns']-raw['now_ns'])) for raw in (before, after)]
    if any(abs(row['now_ns']-raw['now_ns']) > 50_000_000 for row, raw in zip(nearest, (before, after))):
        findings.append('truth_time_binding')
    own_truth = round((nearest[1]['body'][2]-nearest[0]['body'][2])*1000)
    wall_truth = round((nearest[1]['wall'][1]-nearest[0]['wall'][1])*1000)
    if abs(wall_truth-config['external_mm']) > 20:
        failures.append('intervention_not_realized')
    if expected['external_mm']:
        change = by_kind['world_change']
        target = [0, (expected['wall_mm']+expected['external_mm'])/1000, 3]
        if (change['entity'] != 'cause_wall' or change['target'] != target
                or any(abs(a-b) > .01 for a, b in zip(change['observed'], target))
                or not ack['ack_ns'] <= change['begin_ns'] <= change['now_ns'] < after['lidar']['capture_ns']):
            findings.append('intervention_record')
    own_expected = prepared['predicted_north_mm']
    if own_expected is None or abs(own_truth-own_expected) > (200 if own_expected == 0 else 350):
        failures.append('body_effect_not_realized')
    if conclusion['north_delta_mm'] is not None and abs(conclusion['north_delta_mm']-own_truth) > 300:
        failures.append('odometry_error')
    # Geometry independently observed in the private pose stream. Entire flight.
    unsafe = sum(bool(row['wall']) and row['wall'][1]-.1-row['body'][2] < .4 for row in truth)
    if unsafe:
        failures.append('body_envelope')
    max_speed = max((sum((b['body'][i]-a['body'][i])**2 for i in (1, 2, 3))**.5 /
                     ((b['now_ns']-a['now_ns'])/1e9) for a, b in zip(truth, truth[1:])
                     if b['now_ns'] > a['now_ns']), default=0)
    if max_speed > 3:
        failures.append('body_discontinuity')
    sensor = last['distance_mm']-first['distance_mm']
    baseline = 'self' if abs(sensor) > 300 else 'none'
    residual_error = (abs(conclusion['external_delta_mm']-wall_truth)
                      if conclusion['external_delta_mm'] is not None else None)
    return dict(seed=config['seed'], condition=config['condition'], evidence_valid=not findings,
                findings=findings, execution_green=not failures, failures=failures,
                label=conclusion['label'], correct=conclusion['label'] == config['condition'],
                baseline=baseline, baseline_correct=baseline == config['condition'],
                own_truth_mm=own_truth, wall_truth_mm=wall_truth, residual_error_mm=residual_error,
                range_delta_mm=sensor, north_delta_mm=conclusion['north_delta_mm'],
                external_delta_mm=conclusion['external_delta_mm'], unsafe_samples=unsafe,
                consumer_latency_ns=[r.get('call_latency_ns') for r in responses],
                false_self=conclusion['label'] in ('self', 'both') and config['condition'] in ('none', 'external'))
