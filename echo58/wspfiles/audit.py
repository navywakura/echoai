"""Offline audit from archived sources and artifacts. Never runs an environment."""
import argparse
import json
from pathlib import Path

from . import codec as c
from .bench import ARMS, OPERATIONS, REPLICAS, session_archive, decode_arm, selective_packet, sha, summary, save_json
from .memory import memory_archive, restore_memory, compare_decisions
from ..memx.memory import Memory


def inside(root, relative):
    path = (root/relative).resolve()
    c.require(path.is_relative_to(root.resolve()), 'audit path escapes root')
    return path


def audit(root):
    root = Path(root)
    manifest = c.loads((root/'manifest.json').read_bytes())
    preflight = c.loads((root/'preflight.json').read_bytes())
    results = c.loads((root/'results.json').read_bytes())
    c.require(manifest['sources'] == preflight['sources'] and manifest['code'] == preflight['code'], 'preflight changed')
    c.require(manifest['replicas'] == REPLICAS and manifest['arms'] == list(ARMS)
              and manifest['operations'] == list(OPERATIONS), 'study controls changed')
    for item in manifest['sources']+manifest['code']:
        c.require(sha(inside(root,item['snapshot']).read_bytes()) == item['sha256'], 'source snapshot changed')
    expected = {}
    for source in manifest['sources']:
        raw = inside(root, source['snapshot']).read_bytes()
        if source['name'] == 'memory-training-m01':
            m = Memory.load(inside(root, source['snapshot']))
            expected[source['name']] = memory_archive(m, {'source': source['source'], 'source_sha256': source['sha256'],
                'source_kind': 'training memory; postcards generated at export'})
        else: expected[source['name']] = session_archive(raw, source['source'], source['sha256'])
    c.require(set(results['datasets']) == set(expected), 'result dataset set changed')
    c.require(len(manifest['artifacts']) == len(expected)*len(ARMS), 'artifact control count mismatch')
    for dataset in results['datasets'].values():
        c.require(set(dataset['arms']) == set(ARMS), 'result control set changed')
    checked = packets = 0
    seen = set()
    for relative, item in manifest['artifacts'].items():
        raw = inside(root, relative).read_bytes()
        c.require(sha(raw) == item['sha256'] and len(raw) == item['bytes'], 'artifact changed')
        name = item['dataset']; arm = item['arm']; seen.add((name,arm))
        a = decode_arm(raw, arm); c.require(a == expected[name], 'information mismatch')
        c.require(all(selective_packet(raw, arm, i) == r.packet for i, r in enumerate(a.records)), 'selective mismatch')
        d = results['datasets'][name]
        c.require(d['records'] == len(a.records) and d['lossless'] is True, 'record receipt mismatch')
        c.require(d['json_without_receipt_bytes'] == len(c.to_json(a).encode()), 'JSON bytes mismatch')
        entry = d['arms'][arm]; c.require(entry['bytes'] == len(raw), 'reported size mismatch')
        c.require(set(entry['samples']) == set(OPERATIONS) and set(entry['timing']) == set(OPERATIONS), 'operation receipt set')
        for op in OPERATIONS:
            samples = entry['samples'][op]
            c.require(len(samples) == REPLICAS and [s['replica'] for s in samples] == list(range(REPLICAS)), 'replica receipt mismatch')
            c.require(all(type(s[k]) is int and s[k] >= 0 for s in samples for k in ('wall_ns', 'process_ns')), 'invalid elapsed time')
            c.require(summary(samples) == entry['timing'][op], 'derived timing mismatch')
        checked += 1; packets += len(a.records)
    c.require(seen == {(name,arm) for name in expected for arm in ARMS}, 'missing/duplicate controls')
    original = Memory.load(inside(root, manifest['sources'][-1]['snapshot']))
    restored = restore_memory(c.read(root/'artifacts/memory-training-m01.wsp'))
    integration = compare_decisions(original,restored)
    # Tuple/list differences are only JSON rendering, compare canonical values.
    c.require(c.dumps(integration) == c.dumps(results['integration']), 'integration receipt mismatch')
    c.require(integration['mismatches'] == 0 and integration['source_hits'] > 0, 'integration failed')
    return {'valid': True, 'artifacts': checked, 'packets_roundtripped': packets,
            'decisions': integration['decisions'], 'mismatches': integration['mismatches'],
            'results_sha256': sha((root/'results.json').read_bytes()),
            'manifest_sha256': sha((root/'manifest.json').read_bytes())}


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path)
    args=p.parse_args(); result=audit(args.root)
    save_json(args.root/'audit.json', result); print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
