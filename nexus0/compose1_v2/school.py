"""Learn/refine T from actual A flight consequences, not target commands."""
import json
from pathlib import Path
from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1.bench import save
from echoai.nexus0.fusion1.bench import seal
from .perception import grid
from .development import ROOT


def learn(root):
    root = Path(root)
    model = Effects.restore(json.loads((root/'training.json').read_text()))
    rows = [json.loads(line) for line in (root/'journal.jsonl').read_text().splitlines()]
    observations = [r['event'] for r in rows if r['side'] == 'backend' and r['event'].get('kind') == 'observation']
    decisions = [r for r in rows if r['side'] == 'agent']
    effects = []
    for i, (before, after) in enumerate(zip(observations, observations[1:])):
        w = bytes.fromhex(decisions[i]['response']['wsp'])
        if w[1] != 11 or w[13] >= 4:
            continue
        p = grid(before['raw']['estimate']['position_mm'])
        q = grid(after['raw']['estimate']['position_mm'])
        delta = tuple(b-a for a, b in zip(p, q))
        model.observe_effect(True, w[13], delta)
        effects.append(dict(epoch=i, action=w[13], before=list(p), after=list(q),
                            delta=list(delta), before_ns=before['raw']['now_ns'], after_ns=after['raw']['now_ns']))
    counts = [sum(r['action'] == a for r in effects) for a in range(4)]
    if min(counts) < 2:
        raise ValueError('need at least two observed flights of each horizontal action')
    return seal(dict(model=model.snapshot(), physical_effects=effects, counts=counts,
                     source=str(root.relative_to(ROOT)),
                     description='kinematic prior refined by measured A PX4 odometry; no map inherited'))


if __name__ == '__main__':
    result = learn(ROOT/'sitl-development/live-1')
    save(ROOT/'physical-school.json', result)
    print(json.dumps(dict(counts=result['counts'], sha256=result['sha256']), sort_keys=True))
