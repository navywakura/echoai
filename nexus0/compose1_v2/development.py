"""Kept A-only diagnostics; these results never constitute acceptance."""
import argparse
import json
from pathlib import Path

from echoai.nexus0.compose1 import bench as prior
from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1.space import Space, DIRECTIONS, distance
from echoai.nexus0.compose1.training import feature
from echoai.nexus0.fusion1.bench import seal
from .controller import Composer
import random
import shutil

ROOT = Path(__file__).resolve().parents[2] / 'lab/compose1-v2'


def train():
    model = Effects()
    for seed in range(20261901, 20261933):
        rng = random.Random(seed)
        world = Space(seed)
        for _ in range(128):
            state = feature(model, world)
            action = rng.randrange(7)
            old_distance = distance(world.pos, world.goal)
            outcome = world.step(action)
            model.observe_effect(not outcome['blocked'], action, outcome['delta'])
            reward = (old_distance-distance(world.pos, world.goal))*4-1
            model.learn_reward(state, action, reward, feature(model, world))
            if world.energy < 20 or world.pos == world.goal:
                world = Space(seed)
    if any(model.predict(a) != DIRECTIONS[a] for a in range(7)):
        raise ValueError('training did not establish motion effects')
    return model.snapshot()


def mission(*args, **kwargs):
    from .functional import mission as execute
    return execute(*args, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    args = parser.parse_args()
    root = ROOT / 'development' / args.label
    root.mkdir(parents=True, exist_ok=False)
    (root/'source').mkdir()
    for path in Path(__file__).parent.glob('*.py'):
        shutil.copyfile(path, root/'source'/path.name)
    snapshot = train()
    prior.save(root/'training.json', seal(snapshot))
    rows = []
    for i, seed in enumerate(range(20261901, 20261933)):
        condition = prior.CONDITIONS[i % 4]
        for mode in prior.MODES:
            result = mission(snapshot, seed, condition, mode,
                             trace_path=root/f'{seed}-{mode}.jsonl')
            prior.save(root/f'{seed}-{mode}.json', seal(result))
            rows.append(result)
        print(seed, condition, [(x['mode'], x['reached'], x['steps'])
                               for x in rows[-len(prior.MODES):]], flush=True)
    prior.save(root/'summary.json', seal(prior.metrics(rows)))


if __name__ == '__main__':
    main()
