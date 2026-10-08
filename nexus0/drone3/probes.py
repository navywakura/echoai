"""In-flight refusal probes: illegal inputs built on live telemetry, never sent.

Each probe uses its own gateway instance, so one refusal cannot mask another,
and none of them touches the mission supervisor or MAVLink. The auditor
recomputes every probe; a code mutant that accepts one is detected.
"""
from echoai.core.wsp import pack

from echoai.nexus0.power1.core import Model, RESERVE
from . import contract as c
from . import gates
from .gateway import CellGateway

NAMES = ('malformed', 'expired', 'stale_telemetry', 'no_authority', 'failsafe', 'geofence',
         'prediction_mismatch', 'stop_is_not_a_goal', 'busy', 'ack_wrong_system', 'ack_wrong_command',
         'ack_before_send', 'ack_rejected', 'ack_counts_as_arrival', 'repeated_sequence',
         'epistemic_unseen', 'energy_insufficient', 'supervisor_epistemic', 'supervisor_energy')


def move_wsp(action):
    return pack(src=2, rel=11, dst=5, time=8, E=dict(C=80), domain=9, generator=8, style=action).hex()


def run(frame, now, system, *, model, offset, gateway=CellGateway, epistemic=gates.epistemic,
        energy=gates.energy, supervisor=None):
    cell = c.grid(frame['position_mm'])
    legal = dict(wsp=move_wsp(0), seq=1, published_ns=now, prediction=[cell[0]+1, cell[1], 0])
    out = []

    def propose(name, request, telemetry):
        g = gateway(system, 1)
        out.append(dict(name=name, allowed=g.propose(request, telemetry, now)['allowed']))

    propose('malformed', dict(legal, wsp='00'*16), frame)
    propose('expired', dict(legal, published_ns=now-500_000_000), frame)
    propose('stale_telemetry', legal, dict(frame, received_ns=now-500_000_000))
    propose('no_authority', legal, dict(frame, authority=False))
    propose('failsafe', legal, dict(frame, failsafe=True))
    far = [c.GEOFENCE_TARGET_MM, frame['position_mm'][1], frame['position_mm'][2]]
    propose('geofence', dict(legal, prediction=[c.grid(far)[0]+1, c.grid(far)[1], 0]),
            dict(frame, position_mm=far))
    propose('prediction_mismatch', dict(legal, prediction=[cell[0], cell[1]+1, 0]), frame)
    stop = pack(src=2, rel=14, dst=5, time=8, E=dict(C=0), domain=9, generator=8, style=6).hex()
    propose('stop_is_not_a_goal', dict(legal, wsp=stop), frame)
    g = gateway(system, 1)
    first = g.propose(legal, frame, now)['allowed']
    out.append(dict(name='busy', allowed=first and g.propose(dict(legal, seq=2), frame, now)['allowed']))
    for name, ack in [('ack_wrong_system', dict(system=system+1, component=1, command=192, result=0)),
                      ('ack_wrong_command', dict(system=system, component=1, command=176, result=0)),
                      ('ack_before_send', dict(system=system, component=1, command=192, result=0)),
                      ('ack_rejected', dict(system=system, component=1, command=192, result=4))]:
        g = gateway(system, 1)
        g.propose(legal, frame, now)
        received = now if name == 'ack_before_send' else now+1
        accepted = g.acknowledge(dict(ack, received_ns=received), now+1)
        out.append(dict(name=name, allowed=bool(accepted) and g.state != 'fault'))
    valid_ack = dict(system=system, component=1, command=192, result=0, received_ns=now+1)
    g = gateway(system, 1)
    g.propose(legal, frame, now)
    g.acknowledge(valid_ack, now+1)
    out.append(dict(name='ack_counts_as_arrival', allowed=g.state == 'complete'))
    g = gateway(system, 1)
    decision = g.propose(legal, frame, now)
    g.acknowledge(valid_ack, now+1)
    for i in range(c.ARRIVAL_SAMPLES):
        g.observe(dict(frame, position_mm=list(decision['target_mm']), speed_mm_s=0, received_ns=now+2+i), now+2+i)
    g.release()
    out.append(dict(name='repeated_sequence',
                    allowed=g.propose(dict(legal, published_ns=now+5), frame, now+5)['allowed']))
    empty = dict(physical=True, now_ns=now, odometry=[cell[0], cell[1], 0], energy=240,
                 station_observed=False, cells=[])
    out.append(dict(name='epistemic_unseen',
                    allowed=epistemic(empty, 'move', (cell[0]+1, cell[1]), now, offset)['allowed']))
    # One unit short of step + return + landing + reserve: only the reserve refuses it.
    costs = Model(model).data['costs']
    short = costs['0']['upper']+costs['1']['upper']+costs['land']['upper']+RESERVE-1
    battery = dict(capture_ns=now, remaining=short, capacity=1000, unit='sim_u')
    out.append(dict(name='energy_insufficient',
                    allowed=energy(model, battery, now, [cell], (cell[0]+1, cell[1]), cell)['allowed']))
    # The supervisor's own wiring: a throwaway instance, never the mission's.
    if supervisor is None:
        from .supervisor import MissionSupervisor as supervisor
    health = dict(now_ns=now, sensor_ns=now, frame=frame, worker_alive=True)
    fresh = dict(capture_ns=now, remaining=1000, capacity=1000, unit='sim_u')
    s = supervisor(model, offset, cell, system, 1)
    out.append(dict(name='supervisor_epistemic',
                    allowed=s.submit(legal, health, dict(frame=empty, battery=fresh))['allowed']))
    free = dict(empty, cells=[dict(position=[cell[0]+1, cell[1], 0], sources=[
        dict(source=name, wsp=gates.packet(0, 40).hex(), capture_ns=now, delivered_ns=now, raw_sha256='0'*64)
        for name in ('lidar', 'depth')])])
    s = supervisor(model, offset, cell, system, 1)
    out.append(dict(name='supervisor_energy',
                    allowed=s.submit(legal, health, dict(frame=free, battery=battery))['allowed']))
    return out
