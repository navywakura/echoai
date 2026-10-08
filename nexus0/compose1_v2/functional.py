"""Kinematic bench with an independent consequence/geometry adjudicator."""
import json
import time

from .controller import Composer
from .space import Space, DIRECTIONS, add
from .transport import Caged


def mission(snapshot, seed, condition, mode, *, isolated=False, trace_path=None):
    world = Space(seed, condition)
    oracle = world.oracle_distance()
    agent = Caged(snapshot, world.goal, mode, world.energy) if isolated else Composer(snapshot, world.goal, mode)
    baseline = agent.ready['model_sha256'] if isolated else agent.model.fingerprint()
    records, durations = [], []
    reserve_violations = false_facts = 0
    fh = open(trace_path, 'x') if trace_path else None
    try:
        for _ in range(65):
            frame = world.scan()
            start = time.perf_counter_ns()
            response = agent.call(frame) if isolated else agent.decide(frame)
            durations.append(time.perf_counter_ns()-start)
            event = dict(observation=frame, prediction=response)
            if fh:
                fh.write(json.dumps(dict(kind='before_action', **event), sort_keys=True)+'\n')
                fh.flush()
            status = response['status']
            if status not in ('moving', 'returning'):
                false_facts += status == 'reached' and not (frame['station_observed'] and world.pos == world.goal)
                event['consequence'] = None
                records.append(event)
                break
            w = bytes.fromhex(response['wsp'])
            action = w[13]
            if len(w) != 16 or w[1] != 11 or not 0 <= action < 6:
                raise ValueError('action WSP')
            target = add(world.pos, DIRECTIONS[action])
            home = world.home_distance(target)
            reserve_violations += home is None or world.energy-4 < home*4+10
            consequence = world.step(action)
            event['consequence'] = consequence
            records.append(event)
            if fh:
                fh.write(json.dumps(dict(kind='after_action', consequence=consequence), sort_keys=True)+'\n')
                fh.flush()
        else:
            status = 'budget_exhausted'
    finally:
        if fh:
            fh.close()
        if isolated:
            agent.close()
    last = records[-1]['prediction']
    times = sorted(durations)
    return dict(seed=seed, condition=condition, mode=mode, records=records, status=status,
                reached=status == 'reached' and not false_facts, collisions=world.collisions,
                false_facts=false_facts, reserve_violations=reserve_violations,
                imagined_writes=last['imagined_writes'],
                model_unchanged=all(r['prediction']['model_sha256'] == baseline for r in records),
                expansions_max=max(r['prediction']['candidates'] for r in records),
                depth_max=max(r['prediction']['depth'] for r in records),
                steps=world.steps, energy_remaining=world.energy, revisions=last['revisions'],
                ended_home=world.pos == world.start, oracle_static_steps=oracle,
                oracle_static_feasible=oracle is not None and 2*oracle*4+10 <= (30 if condition == 'low_energy' else 240),
                isolated=isolated, initial_map_cells=0, model_initial_sha256=baseline,
                performance=dict(p99_ns=times[min(len(times)-1, len(times)*99//100)],
                                 spatial_cells=last['spatial_cells'], cam_used=last['cam_used']))
