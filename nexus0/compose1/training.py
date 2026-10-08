"""Training only in A, with measured kinematic consequences, never B/C."""
import random
from .model import Effects
from .space import Space,DIRECTIONS,add,distance


def feature(model,space):
    frame=space.scan()
    seen={tuple(c['position']):bytes.fromhex(c['lidar'])[2]==5 for c in frame['cells']}
    blocked=[seen.get(add(space.pos,v),True) for v in DIRECTIONS[:6]]
    return model.feature(space.pos,space.goal,blocked)


def train():
    model=Effects();contacts=transitions=0
    for seed in range(20261801,20261817):
        rng=random.Random(seed);space=Space(seed)
        for _ in range(128):
            prior=feature(model,space);action=rng.randrange(7)
            before=distance(space.pos,space.goal)
            measurement=space.step(action)
            model.observe_effect(not measurement['blocked'],action,measurement['delta'])
            reward=(before-distance(space.pos,space.goal))*4-1+(32 if space.pos==space.goal else 0)
            model.learn_reward(prior,action,reward,feature(model,space))
            transitions+=1;contacts+=measurement['blocked']
            if space.energy<20 or space.pos==space.goal:space=Space(seed)
    if any(model.predict(a)!=DIRECTIONS[a] for a in range(7)):
        raise RuntimeError('A did not establish all displacement effects')
    return model.snapshot(),dict(transitions=transitions,blocked_attempts=contacts,
                                seeds=list(range(20261801,20261817)),maps_in_model=False)
