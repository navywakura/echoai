"""Exactly budgeted public school; no unseen tail transitions are executed."""
from . import policy
from .school_v3 import Student, VARIANTS, reward
from .rehearsal_v2 import Space
from echoai.nexus0.compose1.controller import add


def train(seeds, variant, budget=128):
    if type(budget) is not int or not 1 <= budget <= 4096 or not seeds:
        raise ValueError('school budget/seeds')
    config = VARIANTS[variant]
    payload = policy.scratch()
    counts, episodes = {}, []
    used = 0
    for attempt in range(budget+1):
        seed = seeds[attempt % len(seeds)]
        world = Space(seed)
        agent = Student(policy.restore(payload).snapshot(), world.goal,
                        coverage=config['coverage'], counts=counts)
        rows = []
        reserve_violations = 0
        status = 'unknown'
        for _ in range(65):
            if used == budget:
                status = 'training_budget_cut'
                break
            frame = world.scan()
            decision = agent.decide(frame)
            row = dict(observation=frame, decision=decision, consequence=None)
            rows.append(row)
            if decision['status'] not in ('moving', 'returning'):
                status = decision['status']
                break
            w = bytes.fromhex(decision['wsp'])
            if len(w) != 16 or w[1] != 11 or not 0 <= w[13] < 4:
                raise ValueError('school action')
            action = w[13]
            feature = agent.feature()
            home = world.home_distance(add(world.pos, agent.model.predict(action)))
            reserve_violations += home is None or world.energy-4 < home*4+10
            before = world.pos
            consequence = world.step(action)
            after = world.scan()
            agent.update(after)
            r = reward(config['reward'], before, world.pos, world.goal, after['station_observed'])
            next_feature = agent.feature()
            agent.model.learn_reward(feature, action, r, next_feature)
            counts.setdefault(feature.hex(), [0]*4)[action] += 1
            used += 1
            row.update(consequence=consequence, after=after,
                       learning=dict(before=feature.hex(), after=next_feature.hex(), reward=r))
        payload = policy.export(agent.model)
        if agent.ingestions != world.steps+1 or sum(agent.visits.values()) != agent.ingestions:
            raise ValueError('capture multiplicity')
        episodes.append(dict(seed=seed, rows=rows, status=status, moves=world.steps,
            ingestions=agent.ingestions, visits=sum(agent.visits.values()),
            collisions=world.collisions, reserve_violations=reserve_violations))
        if used == budget:
            return dict(payload=payload, episodes=episodes, moves=used, sim_u=used*4,
                        counts=counts, features=len(counts),
                        feature_action_pairs=sum(sum(n>0 for n in row) for row in counts.values()),
                        features_with_one_action=sum(sum(n>0 for n in row)==1 for row in counts.values()))
    raise ValueError('school cannot spend its budget; no synthetic observations')
