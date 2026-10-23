"""Local CLI; inspection emits JSON suitable for a web viewer."""
import argparse
import hashlib
import json
from pathlib import Path

from ..memx.memory import Memory
from . import codec
from .codec import read_bytes
from .memory import compare_decisions, export_memory, load_memory


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('inspect', 'verify', 'import-json', 'export-json', 'export-memory', 'use-memory'))
    p.add_argument('source', type=Path)
    p.add_argument('destination', type=Path, nargs='?')
    args = p.parse_args()
    if args.command in ('import-json', 'export-json', 'export-memory') and args.destination is None:
        p.error('destination required')
    try:
        if args.command == 'import-json':
            codec.write(args.destination, codec.from_json(read_bytes(args.source)))
            result = {'written': str(args.destination)}
        elif args.command == 'export-json':
            raw = codec.to_json(codec.read(args.source)).encode()
            with args.destination.open('xb') as f: f.write(raw)
            result = {'written': str(args.destination)}
        elif args.command == 'export-memory':
            export_memory(Memory.load(args.source), args.destination,
                provenance={'source': str(args.source), 'source_sha256': hashlib.sha256(read_bytes(args.source)).hexdigest(),
                            'source_kind': 'training memory; postcards generated at export'})
            result = {'written': str(args.destination)}
        elif args.command == 'use-memory':
            memory = load_memory(args.source)
            result = compare_decisions(memory, load_memory(args.source))
        else:
            a = codec.read(args.source)
            if args.command == 'verify' and a.profile == 'memx-replay-v1': load_memory(args.source)
            result = {'valid': True, 'profile': a.profile, 'records': len(a.records),
                      'provenance': a.provenance,
                      'sha256': hashlib.sha256(read_bytes(args.source)).hexdigest()}
            if args.command == 'inspect':
                result['packets'] = [{'index': i, 'hex': r.packet.hex(), 'metadata': r.metadata}
                                     for i, r in enumerate(a.records)]
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        p.exit(2, f'{type(exc).__name__}: {exc}\n')


if __name__ == '__main__': main()
