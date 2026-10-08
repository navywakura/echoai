"""Deterministic fault fixtures; no simulator or actuator authority."""
import copy
from echoai.nexus0.cause1.core import wsp
from echoai.nexus0.safe1.core import Supervisor

CONDITIONS = ('nominal', 'sensor_missing', 'sensor_stale', 'sensor_future',
              'network_stale', 'process_dead', 'process_timeout', 'bad_wsp',
              'expired_proposal', 'out_of_bounds', 'px4_failsafe', 'power_unknown',
              'low_energy', 'replay', 'ack_rejected', 'ack_missing')


def fixture(seed, now=1_000_000_000):
    action = seed % 2
    health = dict(now_ns=now, sensor_ns=now, worker_alive=True,
                  frame=dict(received_ns=now, position_mm=[seed % 101-50, 0, 2500],
                             speed_mm_s=0, armed=True, authority=True, failsafe=False))
    request = dict(wsp=wsp(action), seq=1, published_ns=now)
    energy = dict(now_ns=now, battery=dict(capture_ns=now, remaining=150, capacity=1000, unit='sim_u'),
                  routes=dict(out=[action], goal_home=[1-action], home=[]), at_home=True, goal_reached=False)
    return health, request, energy


def episode(model, seed, condition, factory=Supervisor):
    if condition not in CONDITIONS:
        raise ValueError(condition)
    supervisor = factory(model)
    health, request, energy = fixture(seed)
    events = []

    def submit():
        decision = supervisor.submit(request, health, energy)
        events.append(copy.deepcopy(dict(kind='submit', health=health, request=request, energy=energy, decision=decision)))
        return decision

    def check():
        ok = supervisor.check(health)
        events.append(copy.deepcopy(dict(kind='check', health=health, ok=ok)))

    if condition.startswith('sensor_'):
        health['sensor_ns'] = dict(sensor_missing=None, sensor_stale=health['now_ns']-250_000_001,
                                   sensor_future=health['now_ns']+1)[condition]
    if condition == 'network_stale':
        health['frame']['received_ns'] -= 250_000_001
    if condition == 'process_dead':
        health['worker_alive'] = False
    if condition == 'process_timeout':
        supervisor.trip('ipc_timeout')
        events.append(dict(kind='trip', reason='ipc_timeout'))
    if condition == 'bad_wsp':
        request['wsp'] = 'ff'*16
    if condition == 'expired_proposal':
        request['published_ns'] -= 250_000_001
    if condition == 'out_of_bounds':
        health['frame']['position_mm'][0] = 6000
    if condition == 'px4_failsafe':
        health['frame']['failsafe'] = True
    if condition == 'power_unknown':
        energy['battery']['remaining'] = None
    if condition == 'low_energy':
        energy['battery']['remaining'] = 30
    decision = submit()
    initially_valid = condition in ('nominal', 'replay', 'ack_rejected', 'ack_missing')
    valid = decision['allowed'] == initially_valid
    if initially_valid and decision['allowed']:
        if condition == 'replay':
            valid &= not submit()['allowed']
        elif condition == 'ack_missing':
            health['now_ns'] += 2_000_000_001
            health['sensor_ns'] = health['frame']['received_ns'] = health['now_ns']
            check()
        else:
            now = health['now_ns']+1
            ack = dict(system=1, component=1, command=192, result=1 if condition == 'ack_rejected' else 0, received_ns=now)
            accepted = supervisor.acknowledge(ack, now)
            events.append(dict(kind='ack', ack=ack, now_ns=now, accepted=accepted))
            if condition == 'nominal':
                for step in range(3):
                    health['now_ns'] = now+(step+1)*50_000_000
                    health['sensor_ns'] = health['frame']['received_ns'] = health['now_ns']
                    health['frame']['position_mm'] = list(decision['target_mm'])
                    check()
                valid &= supervisor.gateway.state == 'complete' and not supervisor.tripped
    if condition != 'nominal':
        valid &= supervisor.tripped
        health, request, energy = fixture(seed, health['now_ns']+1)
        valid &= not submit()['allowed'] and supervisor.tripped
    return dict(seed=seed, condition=condition, events=events, ok=bool(valid),
                reason=supervisor.reason, state=supervisor.gateway.state)


def bank(model, seeds):
    rows = [episode(model, seed, case) for seed in seeds for case in CONDITIONS]
    return dict(rows=rows, total=len(rows), passed=sum(r['ok'] for r in rows),
                # A pass-through adapter always forwards the first proposal, including faults.
                unguarded_fault_forwards=sum(r['condition'] not in ('nominal', 'replay', 'ack_rejected', 'ack_missing') for r in rows))
