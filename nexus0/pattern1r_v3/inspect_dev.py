"""Rejudge one development flight, preserving the verdict with its code hash."""
import argparse
import json
import re
import tempfile
from pathlib import Path

from echoai.nexus0.sim3.canon import dump_report
from echoai.nexus0.sim3.generate import generate_suite
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from . import campaign as cp, contract as ct, evaluate as ev


def inspect(label, output='evaluation.json'):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', label) or Path(output).name != output:
        raise ValueError('local development label and output basename required')
    root = cp.ROOT/'dev'/label
    target = root/output
    if target.exists():
        raise FileExistsError(target)
    s = json.loads((root/'sensors.json').read_text())
    trace = json.loads((root/'episode.json').read_text())
    index = s['world_index']
    with tempfile.TemporaryDirectory() as tmp:
        world = generate_suite(Path(tmp), load_protocol(cp.c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                               [(ct.WORLD_SPLIT, ct.WORLD_INDEX[index], ct.WORLD_SEEDS[index])],
                               family_path=cp.c.ECHOAI/ct.FAMILY_PATH)[0]
        if world.package_id != s['package_id']:
            raise ValueError('record/package mismatch')
        p = cp.protocol()
        groups = ev.episode(trace, ev.load_private(cp.c.ECHOAI/s['private']),
                            ev.load_transcript(cp.c.ECHOAI/s['transcript']), s['consumer'],
                            s['forwarder'], world.package, s['spec'], condition=s['condition'],
                            bounds=p['latency_p99_bound_ns'], cable=s['cable'])
    result = cp.seal(dict(kind='development', label=label, world_index=index,
                          inventory_sha256=cp.inventory()['sha256'], groups=ev.summarize(groups),
                          passed=all(v and all(x['ok'] for x in v) for v in groups.values())))
    dump_report(target, result)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('label')
    ap.add_argument('--output', default='evaluation.json')
    args = ap.parse_args()
    print(json.dumps(inspect(args.label, args.output), indent=2), flush=True)
