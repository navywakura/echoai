"""Public V2: geometry-disjoint rooms, common kinetics, frozen relative Q."""
import argparse
import json
import random
from pathlib import Path

from echoai.nexus0.compose1.controller import distance
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.compose1_v3.space import Space as Previous, DIRECTIONS, add
from echoai.nexus0.compose1_v3.transport import Caged
from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import policy
from .rehearsal import inventory

PROTOCOL = dict(version=2, scope='public-functional-development',
    school_seed=20264401, exam_seed=20264501, school_count=4, exam_count=16,
    school_repeats=3, max_generation_attempts=100, arms=['transfer', 'scratch'],
    common_kinematics=True, planner='compose1_v3.echo32',
    reward='8*(L1_before-L1_after)-1+32*observed_arrival',
    learning_in_exam=False, campaign_ready=False)


class Space(Previous):
    """One-wall extruded rooms; inherited sensor and transition interfaces.

Geometry PRNG is policy-independent. All rooms are static; no claim about
SDF material validation, dynamics, flight, or a final campaign partition.
"""
    def __init__(self, seed):
        super().__init__(seed, 'static')
        rng = random.Random(seed)
        self.rotation = rng.randrange(4)
        width, height = rng.randrange(5, 10), rng.randrange(3, 6)
        wall = rng.randrange(1, width-1)
        gap = rng.choice([y for y in range(-height+1, height) if y != 0])
        self.domain = {self.rotate((x, y, 0)) for x in range(-1, width+1)
                       for y in range(-height, height+1)}
        self.solids = {self.rotate((x, y, 0)) for x in range(-1, width+1)
                       for y in range(-height, height+1)
                       if x in (-1, width) or y in (-height, height) or (x == wall and y != gap)}
        self.goal = self.rotate((width-1, 0, 0))
        self.camera_solids = set(self.solids)


def shape(world):
    # Exclude goal/start roles as well: moving the goal cannot make an old
    # physical room count as new. geometry normalizes translation and D4.
    variants = []
    for reflection in (1, -1):
        for rotation in range(4):
            def transform(p):
                x, y, z = p
                x *= reflection
                for _ in range(rotation):
                    x, y = -y, x
                return x, y, z
            domain = [transform(p) for p in world.domain]
            origin = tuple(min(p[i] for p in domain) for i in range(3))
            def normal(points):
                return sorted([v-origin[i] for i, v in enumerate(transform(p))] for p in points)
            variants.append(canonical_bytes(dict(domain=normal(world.domain), solids=normal(world.solids))))
    return sha256_bytes(min(variants))


def suite(start, count, forbidden=()):
    seen = set(forbidden)
    accepted, ledger = [], []
    index = 0
    for case in range(count):
        for _ in range(PROTOCOL['max_generation_attempts']):
            seed = start+index
            index += 1
            world = Space(seed)
            fingerprint = shape(world)
            reason = 'duplicate' if fingerprint in seen else 'accepted'
            if len(world.domain) > 256 or world.oracle_distance() is None:
                reason = 'invalid_geometry'
            ledger.append(dict(case=case, index=index-1, seed=seed, shape=fingerprint, reason=reason))
            if reason == 'accepted':
                seen.add(fingerprint)
                accepted.append(dict(seed=seed, shape=fingerprint))
                break
        else:
            raise ValueError('geometry sampling exhausted; no policy-dependent fallback')
    return accepted, ledger


def episode(snapshot, seed, *, learn=False, isolated=False):
    if learn and isolated:
        raise ValueError('school is local; isolated exam has no learning interface')
    world = Space(seed)
    agent = Caged(snapshot, world.goal) if isolated else Composer(snapshot, world.goal)
    baseline = agent.ready['model_sha256'] if isolated else agent.model.fingerprint()
    rows = []
    reserve_violations = 0
    try:
        for _ in range(65):
            frame = world.scan()
            decision = agent.call(frame) if isolated else agent.decide(frame)
            row = dict(observation=frame, decision=decision, consequence=None)
            rows.append(row)
            if decision['status'] not in ('moving', 'returning'):
                break
            wsp = bytes.fromhex(decision['wsp'])
            if len(wsp) != 16 or wsp[1] != 11 or not 0 <= wsp[13] < 4:
                raise ValueError('planar WSP command')
            action = wsp[13]
            before_feature = agent.feature() if learn else None
            home = world.home_distance(add(world.pos, DIRECTIONS[action]))
            reserve_violations += home is None or world.energy-4 < home*4+10
            before = world.pos
            consequence = world.step(action)
            row['consequence'] = consequence
            if learn:
                after = world.scan()
                agent.update(after)
                reward = 8*(distance(before, world.goal)-distance(world.pos, world.goal))-1
                reward += 32*int(after['station_observed'] and world.pos == world.goal)
                next_feature = agent.feature()
                agent.model.learn_reward(before_feature, action, reward, next_feature)
                row['learning'] = dict(before=before_feature.hex(), after=next_feature.hex(), reward=reward)
        last = rows[-1]['decision']
        reached = last['status'] == 'reached'
        result = dict(seed=seed, rows=rows, status=last['status'], reached=reached,
            moves=world.steps, collisions=world.collisions, reserve_violations=reserve_violations,
            false_facts=int(reached and not (world.pos == world.goal and rows[-1]['observation']['station_observed'])),
            model_unchanged=all(r['decision']['model_sha256'] == baseline for r in rows),
            initial_model_sha256=baseline, initial_map_cells=0)
        return result, policy.export(agent.model) if learn else None
    finally:
        if isolated:
            agent.close()


def run(*, isolated=False):
    rooms_a, ledger_a = suite(PROTOCOL['school_seed'], PROTOCOL['school_count'])
    rooms_e, ledger_e = suite(PROTOCOL['exam_seed'], PROTOCOL['exam_count'], [r['shape'] for r in rooms_a])
    payload = policy.scratch()
    school = []
    for _ in range(PROTOCOL['school_repeats']):
        for room in rooms_a:
            row, payload = episode(policy.restore(payload).snapshot(), room['seed'], learn=True)
            school.append(row)
    episodes = []
    for room in rooms_e:
        for arm in PROTOCOL['arms']:
            initial = payload if arm == 'transfer' else policy.scratch()
            row, _ = episode(policy.restore(initial).snapshot(), room['seed'], isolated=isolated)
            episodes.append(dict(arm=arm, result=row))
    totals = {}
    for arm in PROTOCOL['arms']:
        rows = [e['result'] for e in episodes if e['arm'] == arm]
        totals[arm] = {k: sum(r[k] for r in rows) for k in
                      ('reached', 'moves', 'collisions', 'reserve_violations', 'false_facts')}
        totals[arm]['models_unchanged'] = all(r['model_unchanged'] for r in rows)
    pairs = []
    for i, room in enumerate(rooms_e):
        t, s = episodes[2*i]['result'], episodes[2*i+1]['result']
        # Failure is worse than success; moves compared only on joint success.
        win = (int(t['reached'])-int(s['reached'])) if t['reached'] != s['reached'] else (
            (s['moves'] > t['moves'])-(s['moves'] < t['moves']) if t['reached'] else 0)
        pairs.append(dict(seed=room['seed'], outcome=win))
    return dict(protocol=PROTOCOL, inventory=inventory(), isolated=isolated,
        school_rooms=rooms_a, exam_rooms=rooms_e, ledger=ledger_a+ledger_e,
        school=school, training_moves=sum(r['moves'] for r in school), payload=payload,
        episodes=episodes, totals=totals, pairs=pairs,
        wins=sum(p['outcome'] == 1 for p in pairs), ties=sum(p['outcome'] == 0 for p in pairs),
        losses=sum(p['outcome'] == -1 for p in pairs),
        transfer3_green=False, campaign_C_opened=False)


def audit(report):
    if type(report.get('isolated')) is not bool:
        raise ValueError('isolation field')
    if canonical_bytes(run(isolated=report['isolated'])) != canonical_bytes(report):
        raise ValueError('V2 rehearsal does not reconstruct')
    return dict(replay_valid=True, report_sha256=sha256_bytes(canonical_bytes(report)), transfer3_green=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'audit'])
    parser.add_argument('report', type=Path)
    parser.add_argument('--isolated', action='store_true')
    args = parser.parse_args()
    if args.command == 'audit':
        print(json.dumps(audit(loads_strict(args.report.read_bytes())), sort_keys=True))
    else:
        if args.report.exists():
            raise FileExistsError('preserve every public attempt')
        report = run(isolated=args.isolated)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('xb') as stream:
            stream.write(canonical_bytes(report))
        print(json.dumps({k: report[k] for k in ('totals', 'wins', 'ties', 'losses', 'training_moves')}, sort_keys=True))


if __name__ == '__main__':
    main()
