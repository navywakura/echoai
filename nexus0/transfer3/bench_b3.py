"""Explicit B3 adapters over the frozen B2 harness; public only."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import shutil
import subprocess
import tempfile
from . import bench_b2, transport_b2
from .planner_b3 import Planner
from echoai.nexus0.sim3.canon import canonical_bytes,loads_strict,sha256_bytes
from echoai.nexus0.sim3.sandbox import bwrap_argv

ROOT=bench_b2.ROOT
MODULES=transport_b2.MODULES+('transfer3/planner_b3.py',)
original_manifest=bench_b2.manifest


class Caged(transport_b2.Caged):
    def __init__(self,payload,goal,*,safe=True,timeout=20):
        self.tmp=tempfile.TemporaryDirectory(prefix='transfer3-b3-code-')
        root=Path(self.tmp.name)
        try:
            for name in MODULES:
                dest=root/'echoai/nexus0'/name;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/'nexus0'/name,dest)
            for name in transport_b2.PARENT_MODULES:shutil.copyfile(ROOT.parent/name,root/name)
            self.timeout=timeout
            argv=bwrap_argv(Path(__file__).with_name('consumer_b3.py'));i=argv.index('--remount-ro')
            argv[i:i]=['--ro-bind',str(root),'/agent']
            self.proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
            self.ready=self.call(dict(payload=payload,goal=list(goal),safe=safe))
            if self.ready['spatial_cells']:raise ValueError('map transferred')
        except BaseException:
            if hasattr(self,'proc'):self.close()
            else:self.tmp.cleanup()
            raise


def manifest():
    result=original_manifest()
    entries=[Path(__file__),Path(__file__).with_name('consumer_b3.py'),
             ROOT/'tests/test_transfer3_b3.py',ROOT/'docs/TRANSFER3-PLAN-B3-DESIGN.md']
    for p in bench_b2.dependency_paths(entries):
        key=str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else '../'+str(p.relative_to(ROOT.parent))
        result[key]=sha256_bytes(p.read_bytes())
    return result


@contextmanager
def adapters():
    previous=bench_b2.Planner,bench_b2.Caged,bench_b2.manifest
    bench_b2.Planner,bench_b2.Caged,bench_b2.manifest=Planner,Caged,manifest
    try:yield
    finally:bench_b2.Planner,bench_b2.Caged,bench_b2.manifest=previous


def run(stage,*,pilot=None,excluded=None,progress=False):
    if stage=='confirm':
        if not pilot or pilot.get('variant')!='b3-observed-braking' or not pilot.get('isolated') or not pilot['verdict']['passes']:
            raise ValueError('passing isolated B3 pilot required')
        audit(pilot,progress=progress)
    with adapters():
        report=bench_b2.run(stage,True,pilot=pilot,excluded=excluded,progress=progress)
    report['variant']='b3-observed-braking'
    return report


def audit(report,progress=False):
    bench_b2.verify_manifest(report['inventory'])
    actual=run(report['stage'],pilot=report['pilot'],excluded=report['excluded'],progress=progress)
    if canonical_bytes(actual)!=canonical_bytes(report):raise ValueError('B3 replay mismatch')
    return dict(replay_valid=True,sha256=sha256_bytes(canonical_bytes(report)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['pilot','confirm','audit']);p.add_argument('path',type=Path)
    p.add_argument('--pilot',type=Path);a=p.parse_args()
    if a.command=='audit':print(audit(loads_strict(a.path.read_bytes()),progress=True));return
    if a.path.exists():raise FileExistsError('preserve attempts')
    pilot=loads_strict(a.pilot.read_bytes()) if a.pilot else None
    result=run(a.command,pilot=pilot,progress=True)
    with a.path.open('xb') as f:f.write(canonical_bytes(result))
    print(result['verdict'],flush=True)


if __name__=='__main__':main()
