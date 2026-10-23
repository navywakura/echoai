"""Frozen, offline byte-size comparison; imports no agent, model or world."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import zlib

from ..wspfiles import codec as wsp
from . import codec

BASE = Path(__file__).resolve().parents[2]
OLD = BASE / 'lab/echo58/wspfiles/20261023-r1'
NAMES = ('honesto-none-m1', 'memory-training-m01', 'oraculo-false_remote-m3', 'prudente-false_safe-m1')
MANIFEST_SHA = '8bae0fbd8af0db432b3e5ee5159ffc116095dd3db153b0119faf18094596cc3a'
SOURCES = ('echo58/wspstrongjson/__init__.py', 'echo58/wspstrongjson/codec.py',
           'echo58/wspstrongjson/bench.py', 'echo58/wspstrongjson/audit.py',
           'echo58/wspfiles/codec.py', 'tests/test_echo58_wspstrongjson.py',
           'ECHO-5.8/docs/WSP-STRONGJSON-PLAN-20261023.md')
VARIANTS = ('payload', 'full', 'payload.zlib', 'full.zlib')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def save(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def event(root, action, **fields):
    row = dict(time=datetime.now(timezone.utc).isoformat(), action=action, **fields)
    with (root / 'events.jsonl').open('ab') as stream:
        stream.write(packed(row) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def prepare(root):
    root = Path(root)
    manifest_raw = (OLD / 'manifest.json').read_bytes()
    wsp.require(sha(manifest_raw) == MANIFEST_SHA, 'original manifest hash changed')
    manifest = json.loads(manifest_raw)
    root.mkdir(parents=True, exist_ok=False)
    event(root, 'prepare', hypothesis='post hoc descriptive strong JSON controls; no W/R2 reclassification')
    files = {}
    for rel in SOURCES:
        raw = (BASE / rel).read_bytes()
        save(root / 'frozen' / rel, raw)
        files['frozen/' + rel] = {'sha256': sha(raw), 'bytes': len(raw)}
    save(root / 'original-manifest.json', manifest_raw)
    files['original-manifest.json'] = {'sha256': sha(manifest_raw), 'bytes': len(manifest_raw)}
    for name in NAMES:
        for suffix in ('.wsp', '.wsp.zlib'):
            rel = 'artifacts/' + name + suffix
            raw = (OLD / rel).read_bytes()
            expected = manifest['artifacts'][rel]
            wsp.require(sha(raw) == expected['sha256'] and len(raw) == expected['bytes'], 'original artifact changed')
            dest = 'inputs/' + name + suffix
            save(root / dest, raw)
            files[dest] = {'sha256': sha(raw), 'bytes': len(raw)}
    freeze = dict(version=1, names=list(NAMES), layouts=list(codec.LAYOUTS), sources=list(SOURCES),
                  original_manifest_sha256=MANIFEST_SHA, files=files,
                  python=platform.python_version(), zlib=zlib.ZLIB_RUNTIME_VERSION,
                  interpretation='post hoc descriptive; no scientific gate or latency claim')
    save(root / 'freeze.json', packed(freeze))
    event(root, 'freeze_complete', freeze_sha256=sha(packed(freeze)), files=len(files))
    print(json.dumps({'phase': 'frozen', 'freeze_sha256': sha(packed(freeze))}))


def verify_freeze(root):
    root = Path(root)
    freeze = json.loads((root / 'freeze.json').read_bytes())
    wsp.require(freeze['names'] == list(NAMES) and freeze['layouts'] == list(codec.LAYOUTS), 'fixed arms/corpus changed')
    wsp.require(freeze['sources'] == list(SOURCES), 'source set changed')
    required = {'frozen/' + rel for rel in SOURCES} | {'original-manifest.json'}
    required |= {'inputs/' + name + suffix for name in NAMES for suffix in ('.wsp', '.wsp.zlib')}
    wsp.require(set(freeze['files']) == required, 'frozen inventory changed')
    wsp.require(freeze['original_manifest_sha256'] == MANIFEST_SHA, 'manifest anchor changed')
    events = [json.loads(line) for line in (root / 'events.jsonl').read_bytes().splitlines()]
    frozen_events = [row for row in events if row['action'] == 'freeze_complete']
    wsp.require(len(frozen_events) == 1 and frozen_events[0]['freeze_sha256'] == sha((root / 'freeze.json').read_bytes()),
                'freeze receipt mismatch')
    for rel, expected in freeze['files'].items():
        raw = (root / rel).read_bytes()
        wsp.require(sha(raw) == expected['sha256'] and len(raw) == expected['bytes'], 'frozen bytes changed: ' + rel)
    for rel in SOURCES:
        wsp.require((BASE / rel).read_bytes() == (root / 'frozen' / rel).read_bytes(), 'live source changed: ' + rel)
    original = (OLD / 'manifest.json').read_bytes()
    wsp.require(original == (root / 'original-manifest.json').read_bytes() and sha(original) == MANIFEST_SHA,
                'original manifest changed')
    for name in NAMES:
        for suffix in ('.wsp', '.wsp.zlib'):
            wsp.require((OLD / 'artifacts' / (name + suffix)).read_bytes() == (root / 'inputs' / (name + suffix)).read_bytes(),
                        'original control changed')
    return freeze


def calculate(root):
    """Reconstruct all arms; caller persists or compares these bytes without selection."""
    root = Path(root)
    files, datasets = {}, []
    formats = ('wsp',) + codec.LAYOUTS
    totals = {fmt: {variant: 0 for variant in VARIANTS} for fmt in formats}
    for name in NAMES:
        original = (root / 'inputs' / (name + '.wsp')).read_bytes()
        original_z = (root / 'inputs' / (name + '.wsp.zlib')).read_bytes()
        archive = wsp.decode(original)
        wsp.require(wsp.encode(archive) == original, 'source does not round-trip exactly')
        wsp.require(wsp.decompress(original_z) == original, 'original compressed source mismatch')
        fulls = {'wsp': original}
        for layout in codec.LAYOUTS:
            fulls[layout] = codec.encode(archive, layout)
        sizes = {}
        for fmt, full in fulls.items():
            payload = full[:-32]
            wsp.require(hashlib.sha256(payload).digest() == full[-32:], 'integrity envelope mismatch')
            variants = {'payload': payload, 'full': full,
                        'payload.zlib': zlib.compress(payload, 9), 'full.zlib': zlib.compress(full, 9)}
            sizes[fmt] = {key: len(raw) for key, raw in variants.items()}
            for variant, raw in variants.items():
                if fmt != 'wsp':
                    decoded = codec.decode(raw, fmt, integrity=variant.startswith('full'), compressed=variant.endswith('zlib'))
                    wsp.require(wsp.encode(decoded) == original, 'complete Archive information mismatch')
                path = 'artifacts/' + name + '.' + fmt + '.' + variant
                files[path] = raw
                totals[fmt][variant] += len(raw)
        advantages = {layout: {v: 100 * (sizes[layout][v] - sizes['wsp'][v]) / sizes[layout][v]
                               for v in VARIANTS} for layout in codec.LAYOUTS}
        datasets.append(dict(name=name, records=len(archive.records), sizes=sizes,
                             wsp_original_zlib_bytes=len(original_z),
                             wsp_recompressed_equals_original=zlib.compress(original, 9) == original_z,
                             wsp_advantage_percent=advantages))
    result = dict(version=1, interpretation='post hoc descriptive; four previously seen Archives; W/R2 unchanged',
                  datasets=datasets, totals=totals,
                  total_wsp_advantage_percent={layout: {v: 100 * (totals[layout][v]-totals['wsp'][v])/totals[layout][v]
                                                        for v in VARIANTS} for layout in codec.LAYOUTS},
                  artifacts={rel: {'sha256': sha(raw), 'bytes': len(raw)} for rel, raw in files.items()},
                  exact_wsp_roundtrip=True, all_original_zlib_equal=all(d['wsp_recompressed_equals_original'] for d in datasets))
    return result, files


def measure(root):
    root = Path(root)
    verify_freeze(root)
    wsp.require(not (root / 'results.json').exists() and not (root / 'artifacts').exists(), 'measurement already exists')
    event(root, 'measure_start', freeze_sha256=sha((root / 'freeze.json').read_bytes()))
    result, files = calculate(root)
    for rel, raw in files.items():
        save(root / rel, raw)
    save(root / 'results.json', packed(result))
    event(root, 'measure_complete', results_sha256=sha(packed(result)), artifacts=len(files))
    print(json.dumps({'phase': 'measured', 'artifacts': len(files), 'totals': result['totals']}))


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('phase', choices=('prepare', 'measure'))
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    (prepare if args.phase == 'prepare' else measure)(args.root)


if __name__ == '__main__':
    main()
