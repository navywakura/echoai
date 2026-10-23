"""Append-only code, memory and ordered champion snapshots; no API dependency at load."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from ..acumula3 import bench as B3
from .equiv import digest
from .language import Program
from .pieces_b3 import PLUGS
from .pilot import memory_snapshot, restore_memory, save_new
from .runtime import Plug
from .artifacts import publish


def runtime_hashes():
    directory = Path(__file__).parent
    return {'files': {name: hashlib.sha256((directory/name).read_bytes()).hexdigest()
                      for name in ('runtime.py', 'language.py', 'pieces_b3.py')},
            'base': B3.frozen_state()}


def store_piece(root, source):
    Program(source)
    sha = hashlib.sha256(source.encode()).hexdigest()
    path = Path(root)/'objects'/f'{sha}.py'
    publish(path, source.encode(), identical=True)
    return {'kind': 'model', 'sha256': sha, 'name': sha}


def reference_specs():
    return [{'kind':'b3', 'name': p.name, 'sha256': p.digest()} for p in PLUGS]


def plugs_from_specs(root, specs):
    if len(specs) > 16 or len({(s['kind'],s['name']) for s in specs}) != len(specs):
        raise ValueError('piece count or duplicate')
    plugs = []
    for spec in specs:
        if not re.fullmatch('[0-9a-f]{64}', spec['sha256']):
            raise ValueError('invalid piece hash')
        if spec['kind'] == 'b3':
            plug = next(p for p in PLUGS if p.name == spec['name'])
            if plug.digest() != spec['sha256']:
                raise ValueError('reference piece hash mismatch')
        elif spec['kind'] == 'model':
            source = (Path(root)/'objects'/f"{spec['sha256']}.py").read_text()
            if hashlib.sha256(source.encode()).hexdigest() != spec['sha256']:
                raise ValueError('piece hash mismatch')
            plug = Plug(spec['name'], Program(source))
        else:
            raise ValueError('unknown piece kind')
        plugs.append(plug)
    return tuple(plugs)


def save_snapshot(root, path, memory, specs, metadata):
    memory_doc = memory_snapshot(memory)
    memory_sha = digest(memory_doc)
    memory_path = Path(root)/'objects'/f'{memory_sha}.json'
    save_new(memory_path, memory_doc, identical=True)
    doc = {'schema':1, 'memory_sha256':memory_sha, 'pieces':specs,
           'runtime':runtime_hashes(), 'metadata':metadata}
    doc['snapshot_sha256'] = digest(doc)
    save_new(path, doc)
    return doc


def load_snapshot(root, path):
    doc = json.loads(Path(path).read_text())
    if digest({k:v for k,v in doc.items() if k != 'snapshot_sha256'}) != doc['snapshot_sha256']:
        raise ValueError('snapshot hash mismatch')
    if doc['schema'] != 1 or doc['runtime'] != runtime_hashes():
        raise ValueError('runtime/base mismatch')
    sha = doc['memory_sha256']
    if not re.fullmatch('[0-9a-f]{64}', sha):
        raise ValueError('memory hash format')
    memory_doc = json.loads((Path(root)/'objects'/f'{sha}.json').read_text())
    if digest(memory_doc) != sha:
        raise ValueError('memory object hash mismatch')
    return restore_memory(memory_doc), plugs_from_specs(root, doc['pieces']), doc


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args()
    memory, plugs, doc = load_snapshot(args.root, args.snapshot)
    print(json.dumps({'snapshot_sha256':doc['snapshot_sha256'], 'pieces':[p.name for p in plugs],
                      'memory_records':len(memory.raw), 'cortex_calls':0}))
