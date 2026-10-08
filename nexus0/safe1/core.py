"""Integer supervisor; no recovery path and no direct actuator authority."""
from echoai.nexus0.px41.core import Gateway, telemetry, TTL
from echoai.nexus0.power1.core import Guard


class Lease:
    """Called under the adapter's lock when shared between threads."""
    TTL_NS = 500_000_000

    def __init__(self):
        self.deadline = None
        self.last = -1
        self.revoked = False

    def cancel(self):
        self.revoked = True

    def allowed(self, now):
        if type(now) is not int or now < self.last:
            self.cancel()
            return False
        self.last = now
        if self.deadline is None or now >= self.deadline:
            self.cancel()
        return not self.revoked

    def renew(self, now):
        if type(now) is not int or now < 0 or now < self.last:
            self.cancel()
            return False
        if self.deadline is not None and not self.allowed(now):
            return False
        if self.revoked:
            return False
        self.last = now
        self.deadline = now+self.TTL_NS
        return True


class Supervisor:
    def __init__(self, model):
        self.gateway = Gateway()
        self.power = Guard(model)
        self.tripped = False
        self.reason = None
        self.last_now = -1

    def trip(self, reason):
        if not self.tripped:
            self.reason = reason
        self.tripped = True
        self.gateway.fault(reason)
        return False

    def check(self, health):
        if self.tripped:
            return False
        if (type(health) is not dict or set(health) != {'now_ns', 'sensor_ns', 'frame', 'worker_alive'}
                or type(health['now_ns']) is not int or health['now_ns'] < 0
                or health['now_ns'] < self.last_now or type(health['worker_alive']) is not bool):
            return self.trip('health_schema_or_clock')
        now = health['now_ns']
        self.last_now = now
        if type(health['sensor_ns']) is not int or not 0 <= now-health['sensor_ns'] <= TTL:
            return self.trip('sensor_stale')
        if not health['worker_alive']:
            return self.trip('process_dead')
        frame = health['frame']
        if not telemetry(frame, now) or not frame['armed'] or not frame['authority'] or frame['failsafe']:
            return self.trip('link_or_authority')
        if self.gateway.observe(frame, now) == 'fault':
            return self.trip('execution_fault')
        return True

    def submit(self, request, health, energy):
        if not self.check(health):
            return dict(allowed=False, reason=self.reason)
        now = health['now_ns']
        # PX4's gate validates WSP/schema/envelope before any budget state changes.
        decision = self.gateway.propose(request, health['frame'], now)
        if not decision['allowed']:
            self.trip('proposal_rejected')
            return dict(allowed=False, reason=self.reason)
        budget = self.power.decide(energy)
        if (type(energy) is not dict or energy.get('now_ns') != now
                or budget.get('viable') is not True or budget['wsp'] != request['wsp']
                or budget.get('stopped', True)):
            self.trip('power_veto')
            return dict(allowed=False, reason=self.reason)
        return decision

    def acknowledge(self, ack, now):
        if self.tripped:
            return False
        accepted = self.gateway.acknowledge(ack, now)
        if self.gateway.state == 'fault':
            self.trip('ack_rejected_or_late')
        return accepted
