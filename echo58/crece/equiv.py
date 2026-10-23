"""Development-only equivalence gate; never consumes an examination split."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from types import FunctionType

from ..acumula import bench as B1
from ..acumula.agent import XAgent
from ..acumula.config import Config
from ..acumula3 import bench as B3
from ..b3.policy import PAgent, PIECES
from ..b3.trace import CORRECTED
from .pieces_b3 import PLUGS
from .runtime import HAgent

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / 'lab/echo58/crece'
FAMILIES = tuple(dict.fromkeys(B3.MIX + B3.PROBE['dev']))
CASES = ((),) + tuple((p,) for p in PIECES) + (('commit', 'no_repick'), PIECES)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def log(event, **fields):
    LAB.mkdir(parents=True, exist_ok=True)
    with (LAB / 'development.log').open('a') as stream:
        stream.write(json.dumps({'event': event, **fields}, sort_keys=True) + '\n')


class TraceWorld:
    def __init__(self, world, agent, label):
        self.world, self.agent, self.label = world, agent, label

    def __getattr__(self, key):
        return getattr(self.world, key)

    def step(self, prim):
        new = self.world.step(prim)
        self.agent.trace.append([prim, self.agent.trace_intent, None, asdict(new)])
        self.agent.trace_intent = None
        if len(self.agent.trace) % 50 == 1:
            log('action', label=self.label, step=len(self.agent.trace), primitive=prim,
                intent=self.agent.trace[-1][1], pos=new.pos, hand=new.hand, reward=new.reward,
                terminated=new.terminated, truncated=new.truncated)
        return new


def observed(base):
    class Observed(base):
        def run(self, world, max_steps=100000, frames=None):
            self.trace, self.trace_intent = [], None
            return super().run(TraceWorld(world, self, type(self).__mro__[1].__name__), max_steps, frames)

        def _decide(self, obs, world):
            prim, intent = super()._decide(obs, world)
            self.trace_intent = intent
            return prim, intent

        def _outcome(self, old, new, intent):
            out = super()._outcome(old, new, intent)
            self.trace[-1][2] = out
            return out
    return Observed


def development_memory():
    log('memory_training_start', macro=1, source='B1.start_memory training plan')
    # Same frozen function bytecode, private globals with a passive observer.
    build = FunctionType(B1.start_memory.__code__, {**B1.start_memory.__globals__, 'XAgent': observed(XAgent)})
    cfg = Config()
    for edit in CORRECTED:
        cfg = cfg.apply(edit)
    mem = build(1).reconfigure(cfg).probe_copy()
    log('memory_training_done', records=len(mem.raw), records_sha256=digest(mem.raw), destroyed=mem.destroyed)
    return mem


def state(agent):
    # clear_walk is represented by the external piece's HAND-scoped NOTE.
    return {key: getattr(agent, key) for key in
            ('E', 'auto', 'opened', 'picked', 'visits', 'progress', 'dropped', 'idle',
             'max_idle', 'blockdrops', 'steps_n', 'ban')}


def play_pair(names, family, seed, memories, max_steps=100000):
    if family not in FAMILIES or not 7_000_000 <= seed <= 7_000_199:
        raise ValueError('F0 only permits the declared development worlds and seeds')
    selected = tuple(p for name in names for p in PLUGS if p.name == name)
    native = observed(PAgent)(source=memories[0], learn=memories[0], pieces=frozenset(names))
    external = observed(HAgent)(source=memories[1], learn=memories[1], plugs=selected)
    results = []
    for agent in (native, external):
        world = B3.W.make_world(family, seed, 'A2')
        try:
            results.append(agent.run(world, max_steps))
        finally:
            world.close()
    clean = {k: v for k, v in results[1].items() if not k.startswith('plug_')}
    difference = None
    for i in range(max(len(native.trace), len(external.trace))):
        a = native.trace[i] if i < len(native.trace) else None
        b = external.trace[i] if i < len(external.trace) else None
        if a != b:
            difference = {'step': i + 1, 'native': a, 'external': b}
            break
    if difference is None and results[0] != clean:
        difference = {'episode_result': [results[0], clean]}
    if difference is None and state(native) != state(external):
        difference = {'state_keys': [k for k in state(native) if state(native)[k] != state(external)[k]]}
    if difference is None and memories[0] is not None and memories[0].raw != memories[1].raw:
        difference = {'learned_memory_differs': True}
    row = {'pieces': names, 'family': family, 'seed': seed, 'memory': memories[0] is not None,
           'steps': len(native.trace), 'native_sha256': digest(native.trace),
           'external_sha256': digest(external.trace), 'identical': difference is None,
           'first_difference': difference, 'plug_errors': results[1]['plug_errors'],
           'actions': results[1]['plug_actions']}
    log('equivalence_pair', **{k: v for k, v in row.items() if k != 'first_difference'})
    return row


def run_suite(seeds=(7_000_000,), families=FAMILIES, max_steps=100000, minimum_actions=0):
    seeds, families = tuple(seeds), tuple(families)
    if not seeds or not families or any(not 7_000_000 <= s <= 7_000_199 for s in seeds) or not set(families) <= set(FAMILIES):
        raise ValueError('invalid development suite')
    frozen = B3.frozen_state()
    source_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(Path(__file__).parent.glob('*.py'))}
    pf = json.loads((B3.LAB / 'preflight.json').read_text())
    if frozen != pf['frozen']:
        raise RuntimeError('frozen source mismatch before F0')
    initial = development_memory()
    arms = {(names, family): (initial.probe_copy(), initial.probe_copy())
            for names in CASES for family in families}
    rows, actions = [], Counter()
    for seed in seeds:
        for memory in (False, True):
            for names in CASES:
                for family in families:
                    pair = arms[(names, family)] if memory else (None, None)
                    row = play_pair(names, family, seed, pair, max_steps)
                    rows.append(row)
                    actions.update(row['actions'])
                    if not row['identical'] or row['plug_errors']:
                        break
                else:
                    continue
                break
            else:
                continue
            break
        if not rows[-1]['identical'] or rows[-1]['plug_errors']:
            break
        if minimum_actions and all(actions[p] >= minimum_actions for p in PIECES):
            break
    identical = all(row['identical'] for row in rows)
    errors = sum(len(row['plug_errors']) for row in rows)
    coverage = all(actions[p] >= minimum_actions for p in PIECES)
    unchanged = B3.frozen_state() == frozen
    source_unchanged = all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == sha
                           for p, sha in source_hashes.items())
    sample_ok = identical and errors == 0 and unchanged and source_unchanged
    official = minimum_actions >= 20 and set(families) == set(FAMILIES) and max_steps == 100000
    return {'phase': 'F0', 'identical': identical, 'plug_errors': errors, 'coverage': coverage,
            'sample_ok': sample_ok, 'official_gate': official,
            'green': sample_ok and coverage and official,
            'pairs': len(rows), 'steps_per_arm': sum(r['steps'] for r in rows),
            'seeds_used': sorted({row['seed'] for row in rows}), 'families': families,
            'minimum_actions': minimum_actions, 'actions': dict(actions),
            'first_difference': next((r for r in rows if not r['identical']), None),
            'frozen_unchanged': unchanged, 'source_unchanged': source_unchanged, 'rows': rows,
            'piece_hashes': {p.name: p.digest() for p in PLUGS}, 'source_hashes': source_hashes}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed-count', type=int, default=200)
    parser.add_argument('--minimum-actions', type=int, default=20)
    parser.add_argument('--output', type=Path, default=LAB / 'f0-equiv.json')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('output already exists; preserve the prior run and choose a new output')
    result = run_suite(range(7_000_000, 7_000_000 + args.seed_count), minimum_actions=args.minimum_actions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'first_difference', 'source_hashes')}))
    raise SystemExit(0 if result['green'] else 1)


if __name__ == '__main__':
    main()
