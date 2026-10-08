"""SENSOR-1S v2 development flights in A: kept, never counted.

    PYTHONPATH=.. python3 -m echoai.nexus0.sensor1s_v2.dev <label> [--world N]
        [--condition perturbed|nominal] [--faulted] [--mutant NAME] [--seed N]
"""
import argparse
import json

from echoai.nexus0.flight1s.runtime import Runtime
from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.sim3 import runtime as sim3runtime
from echoai.nexus0.sim3.canon import dump_report
from echoai.nexus0.sensor1s import contract, model
from . import session

DEV = c.ECHOAI/'lab/sensor1s-v2/dev'


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
    tmp, packages = legacy.generate_suite_unique()
    try:
        g = packages[:4][a.world]
        spec = contract.spec(contract.schedule(a.seed, a.faulted), a.mutant)
        ep, sensors = session.run_episode(flight, cage, g, contract.configuration(), spec,
                                          condition=a.condition, label=a.label, root=root)
        dump_report(root/'episode.json', ep.trace())
        dump_report(root/'sensors.json', dict(sensors, spec=spec, package_id=g.package_id))
        print(json.dumps(dict(ok=ep.ok, cause=ep.cause, rtf=ep.metrics.get('rtf'),
                              frames=sensors['forwarder']['frames']), sort_keys=True), flush=True)
    finally:
        tmp.cleanup()


if __name__ == '__main__':
    main()
