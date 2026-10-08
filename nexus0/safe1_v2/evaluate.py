"""Narrow correction: distinguish normal rejected arm retries from forcing."""
import json
from pathlib import Path
from pyulog import ULog
from echoai.nexus0.safe1.evaluate import audit as audit_v1


def normal_arming(commands, acks, events, start_us):
    if not 1 <= len(commands) <= 10 or len(acks) != len(commands):
        return False
    if len(events) != len(commands):
        return False
    previous_ack = -1
    for i, (command, ack, event) in enumerate(zip(commands, acks, events)):
        last = i == len(commands)-1
        if (command['param1'] != 1 or command['param2'] != 0
                or not previous_ack < command['timestamp'] < ack['timestamp'] < start_us
                or ack['timestamp']-command['timestamp'] > 3_000_000):
            return False
        if last:
            if ack['result'] != 0 or event['event'] != 'armed':
                return False
        elif not (ack['result'] in (1, 2, 3, 4, 5, 6)
                  and event['event'] == 'arm_rejected' and event.get('result') == ack['result']):
            return False
        previous_ack = ack['timestamp']
    return True


def audit(root):
    root = Path(root)
    result = audit_v1(root)
    try:
        rows = [json.loads(line) for line in (root/'out/trace.jsonl').read_text().splitlines()]
        start = next(r['now_ns'] for r in rows if r['kind'] == 'supervision_start')//1000
        ulog = ULog(str(next(root.rglob('*.ulg'))))
        data = ulog.get_dataset('vehicle_command').data
        commands = [{k: data[k][i].item() for k in ('timestamp', 'param1', 'param2')}
                    for i in range(len(data['command'])) if data['command'][i] == 400 and data['from_external'][i] == 1]
        data = ulog.get_dataset('vehicle_command_ack').data
        acks = [{k: data[k][i].item() for k in ('timestamp', 'result')}
                for i in range(len(data['command'])) if data['command'][i] == 400]
        runtime = json.loads((root/'out/result.json').read_text())
        events = [e for e in runtime['driver_events'] if e['event'] in ('armed', 'arm_rejected')]
        if normal_arming(commands, acks, events, start):
            result['findings'] = [f for f in result['findings'] if f != 'forced_arm_or_disarm']
        else:
            result['findings'].append('normal_arming_protocol')
        result['arming_attempts'] = len(commands)
    except Exception as exc:
        result['findings'].append('arming_audit_exception:'+repr(exc))
    result['findings'] = sorted(set(result['findings']))
    result['valid'] = not result['findings']
    return result


if __name__ == '__main__':
    import sys
    result = audit(sys.argv[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['valid'] else 1)
