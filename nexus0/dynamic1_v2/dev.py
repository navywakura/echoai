"""DYNAMIC-1 v2 development flights: kept, never counted.

    PYTHONPATH=.. python3 -m echoai.nexus0.dynamic1_v2.dev <label> [--world N]
        [--condition perturbed|nominal] [--faulted] [--mutant NAME] [--seed N]

Each flight prints what the harness moved and what the consumer said; the
verdict comes from the evaluator, run separately.
"""
import argparse
import json
import tempfile
from pathlib import Path

from echoai.nexus0.flight1s.runtime import Runtime
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.sim3 import runtime as sim3runtime
from echoai.nexus0.sim3.canon import dump_report
from echoai.nexus0.sensor1s import contract, model
from echoai.nexus0.sim3.generate import generate_suite
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.dynamic1 import contract as d1
from . import campaign, session

DEV = c.ECHOAI/'lab/dynamic1-v2/dev'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('label')
    ap.add_argument('--world', type=int, default=0)
    ap.add_argument('--condition', default='perturbed')
    ap.add_argument('--faulted', action='store_true')
    ap.add_argument('--mutant')
    ap.add_argument('--still', action='store_true')
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    root = DEV/a.label
    if root.exists():
        raise FileExistsError(root)
    root.mkdir(parents=True)
    if not model.check()['ok']:
        raise RuntimeError('rig model does not derive from the pinned stock SDFs')
    lock = json.loads((c.ECHOAI/'lab/flight1s-v6/lock.json').read_text())
    flight = Runtime(available=True, lock=lock['runtime'])
    cage = sim3runtime.preflight(write=False)
    tmp = tempfile.TemporaryDirectory(prefix='pattern1r-')
    packages = generate_suite(Path(tmp.name), load_protocol(c.WORLD_PROTOCOL), REHEARSAL_SECRET,
                              [(d1.WORLD_SPLIT, i, s) for i, s in zip(d1.WORLD_INDEX, d1.WORLD_SEEDS)],
                              family_path=c.ECHOAI/d1.FAMILY_PATH)
    try:
        g = packages[a.world]
        spec = campaign.spec_for(contract.schedule(a.seed, a.faulted), a.mutant)
        ep, sensors = session.run_episode(flight, cage, g, d1.configuration(moving=not a.still), spec,
                                          condition=a.condition, label=a.label, root=root)
        dump_report(root/'episode.json', ep.trace())
        dump_report(root/'sensors.json', dict(sensors, spec=spec, package_id=g.package_id, world_index=a.world,
                                              condition=a.condition, faulted=a.faulted, seed=a.seed))
        mover = ep.trace().get('stage_marks', {}).get('mover') or {}
        tally = sensors['consumer']
        print(json.dumps(dict(ok=ep.ok, cause=ep.cause, rtf=ep.metrics.get('rtf'),
                              frames=sensors['forwarder']['frames'],
                              steps=len(mover.get('steps', [])),
                              moved_mm=(mover.get('steps') or [{}])[-1].get('seen_mm'),
                              motion=len(tally.get('motion', [])),
                              moving=sum(1 for r in tally.get('motion', []) if r[3])),
                         sort_keys=True), flush=True)
    finally:
        tmp.cleanup()


if __name__ == '__main__':
    main()
