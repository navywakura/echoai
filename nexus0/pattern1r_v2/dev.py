"""PATTERN-1R development flights: kept, never counted.

    PYTHONPATH=.. python3 -m echoai.nexus0.pattern1r_v2.dev <label> [--world N]
        [--condition perturbed|nominal] [--faulted] [--mutant NAME] [--seed N]

Each flight is judged at once by the GROUND-1 evaluator, and the verdict is
kept next to the evidence.
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
from . import contract as p1r, session

DEV = c.ECHOAI/'lab/pattern1r-v2/dev'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('label')
    ap.add_argument('--world', type=int, default=0)
    ap.add_argument('--condition', default='perturbed')
    ap.add_argument('--faulted', action='store_true')
    ap.add_argument('--mutant')
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
                              [(p1r.WORLD_SPLIT, i, s) for i, s in zip(p1r.WORLD_INDEX, p1r.WORLD_SEEDS)],
                              family_path=c.ECHOAI/p1r.FAMILY_PATH)
    try:
        g = packages[a.world]
        spec = p1r.spec(contract.schedule(a.seed, a.faulted), a.mutant)
        ep, sensors = session.run_episode(flight, cage, g, p1r.configuration(), spec,
                                          condition=a.condition, label=a.label, root=root)
        dump_report(root/'episode.json', ep.trace())
        dump_report(root/'sensors.json', dict(sensors, spec=spec, package_id=g.package_id, world_index=a.world,
                                              condition=a.condition, faulted=a.faulted, seed=a.seed))
        legs = ep.trace().get('stage_marks', {}).get('survey', [])
        tally = sensors['consumer']
        print(json.dumps(dict(ok=ep.ok, cause=ep.cause, rtf=ep.metrics.get('rtf'),
                              frames=sensors['forwarder']['frames'],
                              legs=len(legs), commanded=sum(1 for x in legs if x['commanded']),
                              settled=sum(1 for x in legs if x['settled_ns']),
                              sightings=len(tally.get('sightings', []))),
                         sort_keys=True), flush=True)
    finally:
        tmp.cleanup()


if __name__ == '__main__':
    main()
