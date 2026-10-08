"""Read-only dependency mount for the Plan A2 consumer.

The mounted set is explicit and asserted: no simulator, no generator, no world,
no evaluator cost table. `space_a2` and `body_a1` are absent by construction, and
a test walks the mounted tree to prove it rather than trusting this docstring.
"""
import json
import select
import shutil
import subprocess
import tempfile
from pathlib import Path

from echoai.nexus0.compose1.bench import MODULES as BASE, PARENT_MODULES, ECHOAI
from echoai.nexus0.sim3.sandbox import bwrap_argv

HERE = Path(__file__).resolve().parent
MODULES = BASE+('compose1_v2/controller.py', 'compose1_v3/controller.py',
                'transfer3/__init__.py', 'transfer3/costs_a2.py',
                'transfer3/planner_a2.py')
FORBIDDEN = ('space_a2.py', 'body_a1.py', 'rehearsal_v2.py', 'confirm_a2.py',
             'compose1/space.py', 'compose1_v3/space.py')


class CagedPlanner:
    def __init__(self, model, goal, calibration, *, reserve, timeout=20):
        self.tmp = tempfile.TemporaryDirectory(prefix='transfer3-a2-code-')
        root = Path(self.tmp.name)
        for name in MODULES:
            dest = root/'echoai/nexus0'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ECHOAI/'nexus0'/name, dest)
        for name in PARENT_MODULES:
            shutil.copyfile(ECHOAI.parent/name, root/name)
        self.mounted = sorted(str(p.relative_to(root)) for p in root.rglob('*.py'))
        for forbidden in FORBIDDEN:
            if any(path.endswith(forbidden) for path in self.mounted):
                raise ValueError('simulator reached the cage: '+forbidden)
        self.timeout = timeout
        argv = bwrap_argv(HERE/'consumer_a2.py')
        index = argv.index('--remount-ro')
        argv[index:index] = ['--ro-bind', str(root), '/agent']
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)
        self.ready = self.call(dict(model=model, goal=list(goal),
                                    calibration=calibration, reserve=reserve))

    def call(self, value):
        self.proc.stdin.write(json.dumps(value, sort_keys=True)+'\n')
        self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], self.timeout)[0]:
            raise TimeoutError('caged consumer')
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(self.proc.stderr.read()[-1000:])
        return json.loads(line)

    def frozen_check(self):
        return self.call(dict(frozen_check=True))

    def close(self):
        if not self.proc.stdin.closed:
            self.proc.stdin.close()
        if self.proc.poll() is None:
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc.stdout.close()
        self.proc.stderr.close()
        self.tmp.cleanup()
