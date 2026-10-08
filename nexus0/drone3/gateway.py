"""Bounded cell goals over PX4-1's transport gate.

PX4-1 certified one 1 m north/south transaction per session inside +-5 m. A
mission needs sequential 3 m cell goals in four directions and yaw-only
inspections. This adapter reuses PX4-1's telemetry validator, ACK identity and
fault latch unchanged, and replaces only the goal arithmetic, the declared
geofence and the return to `ready` after a confirmed arrival.

MAVLink COMMAND_ACK carries no transaction id. Identity is (system, component,
command 192, received after this send, inside 2 s) with exactly one goal in
flight: the next goal can only be proposed after the previous one is confirmed
by three distinct settled samples after its ACK. An ACK is never arrival.
"""
import math

from echoai.nexus0.px41.core import Gateway, telemetry
from . import contract as c


class CellGateway(Gateway):
    def __init__(self, system=1, component=1, *, mutant=''):
        super().__init__(system, component)
        if mutant not in ('', 'no_ttl', 'no_geofence', 'ack_is_arrival', 'no_sequence'):
            raise ValueError('mutant')
        self.mutant = mutant
        self.completed = 0

    def propose(self, request, frame, now):
        def deny(reason):
            return dict(allowed=False, state=self.state, reason=reason)
        if self.state != 'ready':
            return deny('session_not_ready')
        if (type(request) is not dict or set(request) != {'wsp', 'seq', 'published_ns', 'prediction'}
                or type(request['seq']) is not int or type(request['published_ns']) is not int
                or type(now) is not int or type(request['wsp']) is not str
                or type(request['prediction']) is not list or len(request['prediction']) != 3
                or any(type(v) is not int for v in request['prediction'])):
            return deny('schema')
        try:
            kind, style = c.intention(request['wsp'])
        except ValueError:
            return deny('wsp')
        if kind == 'stop':
            return deny('not_a_goal')
        if self.mutant != 'no_sequence' and (not 0 <= request['seq'] <= 2**63-1 or request['seq'] <= self.last_seq):
            return deny('sequence')
        age = now-request['published_ns']
        if request['published_ns'] < 0 or age < 0 or (age > c.TTL_NS and self.mutant != 'no_ttl'):
            return deny('expired')
        if not telemetry(frame, now):
            return deny('telemetry')
        if not frame['armed'] or not frame['authority'] or frame['failsafe']:
            return deny('authority')
        east, north, height = frame['position_mm']
        if self.mutant != 'no_geofence' and (max(abs(east), abs(north)) > c.GEOFENCE_BODY_MM
                                             or not c.HEIGHT_MIN_MM <= height <= c.HEIGHT_MAX_MM):
            return deny('envelope')
        cell = c.grid((east, north))
        if kind == 'move':
            dx, dy = c.VECTORS[style]
            target = (cell[0]+dx, cell[1]+dy)
            yaw = round(math.atan2(dx, dy)*1000)          # NED heading: 0 north, pi/2 east
        else:
            target = cell
            yaw = round((style-c.INSPECT[0])*math.pi/2*1000)
        if request['prediction'] != [target[0], target[1], 0]:
            return deny('prediction_mismatch')
        goal = c.cell_target(target)
        if self.mutant != 'no_geofence' and max(abs(goal[0]), abs(goal[1])) > c.GEOFENCE_TARGET_MM:
            return deny('envelope')
        self.last_seq = request['seq']
        self.samples = 0
        self.pending = dict(request, kind=kind, target_mm=goal, yaw_mrad=yaw, sent_ns=now)
        self.state = 'await_ack'
        return dict(allowed=True, state=self.state, reason='bounded_goal', kind=kind,
                    target_mm=list(goal), yaw_mrad=yaw, target_cell=list(target))

    def acknowledge(self, ack, now):
        accepted = super().acknowledge(ack, now)
        if accepted and self.mutant == 'ack_is_arrival':
            self.state = 'complete'
        return accepted

    def observe(self, frame, now):
        if self.state not in ('await_ack', 'executing'):
            return self.state
        if (not telemetry(frame, now) or not frame['armed'] or not frame['authority']
                or frame['failsafe']):
            self.fault('authority_or_telemetry_lost')
            return self.state
        east, north, height = frame['position_mm']
        if self.mutant != 'no_geofence' and (max(abs(east), abs(north)) > c.GEOFENCE_BODY_MM
                                             or not c.HEIGHT_MIN_MM <= height <= c.HEIGHT_MAX_MM):
            self.fault('envelope_lost')
            return self.state
        deadline = c.ACK_TIMEOUT_NS if self.state == 'await_ack' else c.EXEC_TIMEOUT_NS
        if now-self.pending['sent_ns'] > deadline:
            self.fault('timeout')
            return self.state
        if self.state == 'executing' and frame['received_ns'] > max(self.pending['ack_ns'], self.last_sample):
            self.last_sample = frame['received_ns']
            error2 = sum((a-b)**2 for a, b in zip(frame['position_mm'], self.pending['target_mm']))
            settled = error2 <= c.ARRIVAL_MM**2 and frame['speed_mm_s'] <= c.ARRIVAL_SPEED_MM_S
            self.samples = self.samples+1 if settled else 0
            if self.samples >= c.ARRIVAL_SAMPLES:
                self.state = 'complete'
        return self.state

    def release(self):
        """A confirmed arrival returns the link to `ready`; a fault never does."""
        if self.state != 'complete':
            return False
        self.completed += 1
        self.pending = None
        self.samples = 0
        self.state = 'ready'
        return True
