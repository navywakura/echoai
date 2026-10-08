"""POWER-1 over PX4 SITL's simulated battery.

The pinned PX4 publishes no current (-1 A) and no capacity, so no physical
energy can be measured here. Its battery simulator lowers the pack voltage
linearly with armed time. The adapter maps that voltage, with the pack limits
read from PX4 once, to per-mille of the simulated pack: unit `sim_u`, capacity
1000. It is simulated charge, never joules or instrumented consumption.

POWER-1's Model and Guard are used unchanged. Phases keep POWER-1's names:
'0' = one mission step (a cell move or a yaw inspection) away from home,
'1' = one return step over cells already occupied, 'land' = the landing.
"""
from echoai.nexus0.power1.core import Guard, Model, RESERVE
from . import contract as c

CAPACITY = 1000


def battery_sample(raw):
    """Raw PX4 SYS_STATUS reading -> POWER-1 battery frame, or None."""
    keys = {'capture_ns', 'delivered_ns', 'voltage_mv', 'empty_mv', 'full_mv'}
    if type(raw) is not dict or set(raw) != keys or any(type(raw[k]) is not int for k in keys):
        return None
    if not 0 <= raw['capture_ns'] <= raw['delivered_ns'] or not 0 < raw['empty_mv'] < raw['full_mv']:
        return None
    if not 0 < raw['voltage_mv'] < 65535:
        return None
    span = raw['full_mv']-raw['empty_mv']
    remaining = (raw['voltage_mv']-raw['empty_mv'])*CAPACITY//span
    return dict(capture_ns=raw['capture_ns'], remaining=max(0, min(CAPACITY, remaining)),
                capacity=CAPACITY, unit='sim_u')


def manhattan(a, b):
    return abs(a[0]-b[0])+abs(a[1]-b[1])


def guard_frame(now, battery, pos, goal, home, home_route_len, reached):
    """POWER-1 input. Outbound routes are Manhattan lower bounds, declared as such:
    the planner has no map, so a longer detour is caught by the return check."""
    out = [] if reached else [0]*max(1, manhattan(pos, goal))
    return dict(now_ns=now, battery=battery,
                routes=dict(out=out, goal_home=[1]*manhattan(goal, home),
                            home=None if home_route_len is None else [1]*home_route_len),
                at_home=tuple(pos) == tuple(home), goal_reached=reached)


def receipts(rows):
    """Consumption receipts from confirmed A skills, in POWER-1's schema."""
    out = []
    for row in rows:
        out.append(dict(seq=len(out), phase=row['phase'], before=row['before'], after=row['after'],
                        elapsed_ms=row['elapsed_ms'], confirmed=True, unit='sim_u'))
    return out


def fit(rows):
    return Model.fit(receipts(rows), unit='sim_u').snapshot()


__all__ = ['Guard', 'Model', 'RESERVE', 'CAPACITY', 'battery_sample', 'guard_frame', 'fit', 'c']
