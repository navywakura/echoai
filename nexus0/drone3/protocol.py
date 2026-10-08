"""The DRONE-3 matrix: rooms, conditions, private manipulations and seeds.

Private to the harness and the judge. The agent never imports this module.
Each room (a COMPOSE-1 geometry drawn from a seed) is flown under the four
conditions, so the manipulation is the only difference inside a block.
"""
from echoai.nexus0.compose1_v3.space import Space
from echoai.nexus0.power1.core import Model, RESERVE

CONDITIONS = ('access', 'low_reserve', 'contradiction', 'fault')
FAULTS = ('agent_hang', 'lidar_stale')
FAULT_AFTER_MOVES = 3
INSPECTIONS = 4
HANDOVER_FRACTION = (3, 5)       # hand over at 3/5 of the oracle's upper mission cost
BATTERY = dict(drain_s=500.0, min_pct=5.0, usable_floor=0.2)
ROOMS_PER_STAGE = 3
STAGE_BASE = dict(development=20266001, validation=20267001, confirmation=20268001)


def geometry(seed):
    s = Space(seed)
    return (s.rotation, s.wall_x, s.gap_y)


def rooms(stage, count=ROOMS_PER_STAGE, excluded=()):
    """First `count` seeds from the stage base whose geometry is new to the bench."""
    taken = set(excluded)
    out = []
    seed = STAGE_BASE[stage]
    while len(out) < count:
        g = geometry(seed)
        if g not in taken:
            taken.add(g)
            out.append(seed)
        seed += 1
    return out


def oracle_cost(seed, model_snapshot):
    """Upper-cost mission the judge knows and the agent never sees."""
    model = Model(model_snapshot)
    steps = Space(seed).oracle_distance()
    costs = model.data['costs']
    return (model.route([0]*(steps+INSPECTIONS))+model.route([1]*steps)
            + costs['land']['upper']+RESERVE)


def handover(seed, model_snapshot):
    num, den = HANDOVER_FRACTION
    return oracle_cost(seed, model_snapshot)*num//den


def flights(stage, model_snapshot, offset, excluded=()):
    out = []
    for index, seed in enumerate(rooms(stage, excluded=excluded)):
        for k, condition in enumerate(CONDITIONS):
            spec = dict(seed=seed, condition=condition, physics_seed=seed*10+k, battery=BATTERY,
                        power_model=model_snapshot, offset=list(offset),
                        handover_remaining=handover(seed, model_snapshot) if condition == 'low_reserve' else None,
                        fault=dict(kind=FAULTS[index % 2], after_moves=FAULT_AFTER_MOVES)
                        if condition == 'fault' else None)
            out.append((f'{seed}-{condition}', spec))
    return out
