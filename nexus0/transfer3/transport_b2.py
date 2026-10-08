"""B2 explicit read-only mount, reusing A2 transport protocol and cleanup."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from .transport_a2 import CagedPlanner, MODULES as BASE, PARENT_MODULES, ECHOAI, FORBIDDEN
from echoai.nexus0.sim3.sandbox import bwrap_argv

MODULES = BASE+('transfer3/planner_b1.py','transfer3/planner_b2.py','transfer3/calib_b2.py')


class Caged(CagedPlanner):
    def __init__(self, payload, goal, *, safe=False, timeout=20):
        self.tmp = tempfile.TemporaryDirectory(prefix='transfer3-b2-code-')
        root = Path(self.tmp.name)
        try:
            for name in MODULES:
                dest = root/'echoai/nexus0'/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ECHOAI/'nexus0'/name,dest)
            for name in PARENT_MODULES:
                shutil.copyfile(ECHOAI.parent/name,root/name)
            self.mounted = sorted(str(p.relative_to(root)) for p in root.rglob('*.py'))
            for forbidden in FORBIDDEN+('gain_b1.py','bench_b2.py','school_b2.py'):
                if any(p.endswith(forbidden) for p in self.mounted):
                    raise ValueError('evaluator reached cage')
            self.timeout = timeout
            argv = bwrap_argv(Path(__file__).with_name('consumer_b2.py'))
            index = argv.index('--remount-ro')
            argv[index:index] = ['--ro-bind',str(root),'/agent']
            self.proc = subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,text=True,bufsize=1)
            self.ready = self.call(dict(payload=payload,goal=list(goal),safe=safe))
            if self.ready['spatial_cells'] != 0:
                raise ValueError('map transferred')
        except BaseException:
            if hasattr(self,'proc'):
                self.close()
            else:
                self.tmp.cleanup()
            raise
