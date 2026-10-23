"""New export/reload wrapper around the unchanged MEMORIA-X implementation."""
import json
from types import SimpleNamespace

from ..memx.memory import Memory, OUTCOMES
from ..memx.agent import Agent
from .codec import Archive, Record, read, require, write


def memory_archive(memory, provenance=None):
    return Archive('memx-replay-v1', dict(provenance or {}),
        tuple(Record(raw, {'rule_index': i, 'packet_source': 'Memory.postcards at export'})
              for i, raw in enumerate(memory.postcards())),
        {'n_min': memory.n_min, 'pct': memory.pct, 'head': memory.head,
         'history': memory.records})


def export_memory(memory, path, *, provenance=None):
    return write(path, memory_archive(memory, provenance))


def restore_memory(a):
    require(a.profile == 'memx-replay-v1', 'memory interpretation profile required')
    meta = a.metadata
    require(set(meta) == {'n_min', 'pct', 'head', 'history'}, 'memory schema')
    require(type(meta['n_min']) is int and 1 <= meta['n_min'] <= 1000000, 'memory bound')
    require(type(meta['pct']) is int and 1 <= meta['pct'] <= 100, 'memory percentage')
    require(type(meta['history']) is list, 'memory history list required')
    m = Memory(meta['n_min'], meta['pct'])
    for row in meta['history']:
        require(type(row) is dict and set(row) == {'i', 's', 'a', 'h', 'o', 'prev', 'sha'}, 'memory record schema')
        require(all(type(row[k]) is int and 0 <= row[k] <= 255 for k in ('i', 's', 'h')), 'memory key bounds')
        require(row['a'] in ('ENTER', 'PICK', 'TOGGLE') and row['o'] in OUTCOMES, 'memory enums')
        m.observe(row['i'], row['s'], row['a'], row['h'], row['o'])
        require(m.records[-1] == row, 'memory chain or observation mismatch')
    require(m.head == meta['head'], 'memory head mismatch')
    require(memory_archive(m, a.provenance) == a, 'memory postals or metadata mismatch')
    return m


def load_memory(path):
    return restore_memory(read(path))


def compare_decisions(original, restored):
    """Use the real Agent policy on declared probes, never a sealed world."""
    keys = sorted({(r['i'], r['s'], r['h']) for r in original.records})
    agents = (Agent(source=original), Agent(source=restored))
    mismatches = 0
    empty_differences = 0
    transcripts = []
    before_queries = restored.queries
    before_hits = restored.hits
    world = SimpleNamespace(absolute=True, acts=('ENTER', 'PICK', 'TOGGLE'))
    for ident, sig, hand in keys:
        # Explicit policy probes, not historical world observations or new scores.
        grid = ((ident, ident, ident), (ident, ident, ident), (ident, ident, ident))
        obs = SimpleNamespace(grid=grid, pos=(1, 1), hand=hand, dir=0)
        decisions = []
        for agent in agents:
            agent.E = {}; agent.auto = {ident} if sig & 16 else set()
            agent._scan(grid)
            agent.sig_cache[ident] = sig  # Probe the actual recorded observable key.
            decisions.append(agent._decide(obs, world))
        mismatches += decisions[0] != decisions[1]
        empty = Agent()
        empty.E = {}; empty.auto = {ident} if sig & 16 else set()
        empty._scan(grid); empty.sig_cache[ident] = sig
        empty_decision = empty._decide(obs, world)
        empty_differences += empty_decision != decisions[1]
        transcripts.append({'key': [ident, sig, hand],
                            'original': json.loads(json.dumps(decisions[0])),
                            'reloaded': json.loads(json.dumps(decisions[1])),
                            'empty_control': json.loads(json.dumps(empty_decision))})
    return {'decisions': len(keys), 'mismatches': mismatches,
            'source_queries': restored.queries-before_queries, 'source_hits': restored.hits-before_hits,
            'different_from_empty': empty_differences,
            'probes': transcripts}
