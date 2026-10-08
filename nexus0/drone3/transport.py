"""The DRONE-3 agent's cage: an explicit read-only module mount, nothing else.

No repository, no lab/, no simulator, world file, seed, map or network. The
consumer is pid 1 of its own namespaces (SIM-3 sandbox). Every module that
enters is listed here and hashed into the lock.
"""
import json
import os
import select
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from echoai.nexus0.sim3.sandbox import bwrap_argv

HERE = Path(__file__).resolve().parent
ECHOAI = HERE.parents[1]
MODULES = ('constants.py', 'types.py', 'qtable.py', 'world.py', 'gate.py',
           'fusion1/core.py', 'fusion1/integration.py',
           'compose1/controller.py', 'compose1/model.py', 'compose1_v2/controller.py',
           'compose1_v3/controller.py', 'compose1_v3/perception.py',
           'cause1/core.py', 'power1/core.py', 'transfer3/calib_c1.py',
           'drone3/__init__.py', 'drone3/contract.py', 'drone3/calibration.py',
           'drone3/energy.py', 'drone3/gates.py', 'drone3/agent.py')
PARENT_MODULES = ('core/cam.py', 'core/qn.py', 'core/wsp.py')


class Caged:
    def __init__(self, init, *, deadline_s=20):
        self.tmp = tempfile.TemporaryDirectory(prefix='drone3-agent-')
        root = Path(self.tmp.name)
        for name in MODULES:
            dest = root/'echoai/nexus0'/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ECHOAI/'nexus0'/name, dest)
        for name in PARENT_MODULES:
            shutil.copyfile(ECHOAI.parent/name, root/name)
        argv = bwrap_argv(HERE/'consumer.py')
        index = argv.index('--remount-ro')
        argv[index:index] = ['--ro-bind', str(root), '/agent']
        self.deadline_s = deadline_s
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)
        self.ready = self.call(init)

    def call(self, value, deadline_s=None):
        self.proc.stdin.write(json.dumps(value, sort_keys=True)+'\n')
        self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], deadline_s or self.deadline_s)[0]:
            raise TimeoutError('caged agent')
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError('caged agent closed: '+self.proc.stderr.read()[-2000:])
        return json.loads(line)

    def freeze(self):
        """Fault injection used by the `fault/agent_hang` condition only."""
        for pid in self.descendants():
            os.kill(pid, signal.SIGSTOP)

    def descendants(self):
        pids, frontier = [], [self.proc.pid]
        while frontier:
            pid = frontier.pop()
            pids.append(pid)
            try:
                children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
            except OSError:
                children = []
            frontier.extend(int(p) for p in children)
        return pids

    def peak_rss_kb(self):
        best = 0
        for pid in self.descendants():
            try:
                for line in Path(f'/proc/{pid}/status').read_text().splitlines():
                    if line.startswith('VmHWM:'):
                        best = max(best, int(line.split()[1]))
            except OSError:
                pass
        return best

    def close(self):
        for pid in self.descendants():
            try:
                os.kill(pid, signal.SIGCONT)
            except OSError:
                pass
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


def wait_monotonic(seconds):
    end = time.monotonic()+seconds
    while time.monotonic() < end:
        time.sleep(min(.05, end-time.monotonic()))
