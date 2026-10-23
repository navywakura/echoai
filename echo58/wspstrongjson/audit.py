"""Fresh offline reconstruction of frozen byte controls, without model inference."""
import argparse
import json
from pathlib import Path

from ..wspfiles import codec as wsp
from . import bench


def audit(root):
    root = Path(root)
    bench.verify_freeze(root)
    expected, files = bench.calculate(root)
    stored_raw = (root / 'results.json').read_bytes()
    wsp.require(stored_raw == bench.packed(expected), 'result reconstruction mismatch')
    actual = {str(p.relative_to(root)) for p in (root / 'artifacts').iterdir() if p.is_file()}
    wsp.require(actual == set(files), 'artifact inventory mismatch')
    for rel, raw in files.items():
        wsp.require((root / rel).read_bytes() == raw, 'artifact reconstruction mismatch: ' + rel)
    receipt = dict(passed=True, differences=0, datasets=len(expected['datasets']), artifacts=len(files),
                   result_sha256=bench.sha(stored_raw), freeze_sha256=bench.sha((root / 'freeze.json').read_bytes()),
                   exact_wsp_roundtrip=expected['exact_wsp_roundtrip'], all_original_zlib_equal=expected['all_original_zlib_equal'])
    bench.save(root / 'audit.json', bench.packed(receipt))
    bench.event(root, 'audit_complete', **receipt)
    print(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('root', type=Path)
    audit(parser.parse_args().root)
