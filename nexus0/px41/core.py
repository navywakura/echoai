"""Integer-only transport gate. No arming, parameters, motor or mode commands.

One transaction per supervised session prevents late COMMAND_ACK ambiguity:
MAVLink ACK has no application transaction ID. A new session needs an adapter
connection with an emptied receive queue; this is not automatic recovery.
"""
from echoai.nexus0.cause1.core import decode

TTL = 250_000_000
ACK_TIMEOUT = 2_000_000_000
EXEC_TIMEOUT = 15_000_000_000


def integer(value):
    return type(value) is int


def telemetry(value, now):
    return (type(value) is dict and set(value) == {'received_ns', 'position_mm',
            'speed_mm_s', 'armed', 'authority', 'failsafe'}
            and integer(now) and integer(value['received_ns'])
            and 0 <= now-value['received_ns'] <= TTL
            and type(value['position_mm']) is list and len(value['position_mm']) == 3
            and all(integer(v) for v in value['position_mm'])
            and integer(value['speed_mm_s']) and 0 <= value['speed_mm_s'] <= 3000
            and all(type(value[k]) is bool for k in ('armed', 'authority', 'failsafe')))


class Gateway:
    def __init__(self, system=1, component=1):
        if not all(integer(v) and 1 <= v <= 255 for v in (system, component)):
            raise ValueError('PX4 identity')
        self.system, self.component = system, component
        self.state = 'ready'
        self.last_seq = -1
        self.pending = None
        self.samples = 0
        self.last_sample = -1

    def fault(self, reason):
        self.state = 'fault'
        return dict(allowed=False, state=self.state, reason=reason)

    def propose(self, request, frame, now):
        def deny(reason):
            return dict(allowed=False, state=self.state, reason=reason)
        if self.state != 'ready':
            return deny('session_not_ready')
        if (type(request) is not dict or set(request) != {'wsp', 'seq', 'published_ns'}
                or not integer(request['seq']) or not integer(request['published_ns'])
                or not integer(now) or type(request['wsp']) is not str):
            return deny('schema')
        try:
            action = decode(request['wsp'])
        except (ValueError, TypeError):
            return deny('wsp')
        if not 0 <= request['seq'] <= 2**63-1 or request['seq'] <= self.last_seq:
            return deny('sequence')
        if not 0 <= request['published_ns'] <= now or now-request['published_ns'] > TTL:
            return deny('expired')
        if not telemetry(frame, now):
            return deny('telemetry')
        if not frame['armed'] or not frame['authority'] or frame['failsafe']:
            return deny('authority')
        east, north, height = frame['position_mm']
        goal = [east, north + (1000 if action == 0 else -1000 if action == 1 else 0), 2500]
        if (abs(east) > 5000 or abs(north) > 5000 or not 1800 <= height <= 3200
                or max(abs(goal[0]), abs(goal[1])) > 5000):
            return deny('envelope')
        self.last_seq = request['seq']
        self.pending = dict(**request, target_mm=goal, sent_ns=now)
        self.state = 'await_ack'
        return dict(allowed=True, state=self.state, reason='bounded_goal',
                    **dict(self.pending, target_mm=list(goal)))

    def acknowledge(self, ack, now):
        if self.state != 'await_ack':
            return False
        if not integer(now) or not self.pending['sent_ns'] <= now <= self.pending['sent_ns']+ACK_TIMEOUT:
            self.fault('ack_timeout')
            return False
        keys = {'system', 'component', 'command', 'result', 'received_ns'}
        if (type(ack) is not dict or set(ack) != keys
                or not all(integer(v) for v in ack.values())
                or ack['system'] != self.system or ack['component'] != self.component
                or ack['command'] != 192 or not self.pending['sent_ns'] < ack['received_ns'] <= now):
            return False
        if ack['result'] != 0:
            self.fault('px4_rejected')
            return False
        self.pending['ack_ns'] = ack['received_ns']
        self.state = 'executing'
        return True

    def observe(self, frame, now):
        if self.state not in ('await_ack', 'executing'):
            return self.state
        if (not telemetry(frame, now) or not frame['armed'] or not frame['authority']
                or frame['failsafe']):
            self.fault('authority_or_telemetry_lost')
            return self.state
        east, north, height = frame['position_mm']
        if max(abs(east), abs(north)) > 5000 or not 1800 <= height <= 3200:
            self.fault('envelope_lost')
            return self.state
        deadline = ACK_TIMEOUT if self.state == 'await_ack' else EXEC_TIMEOUT
        if now-self.pending['sent_ns'] > deadline:
            self.fault('timeout')
            return self.state
        if self.state == 'executing' and frame['received_ns'] > max(self.pending['ack_ns'], self.last_sample):
            self.last_sample = frame['received_ns']
            error2 = sum((a-b)**2 for a, b in zip(frame['position_mm'], self.pending['target_mm']))
            self.samples = self.samples+1 if error2 <= 350**2 and frame['speed_mm_s'] <= 150 else 0
            if self.samples >= 3:
                self.state = 'complete'
        return self.state
