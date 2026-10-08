"""Explicit read-only dependency mount, with no simulator or world files."""
import json
import select
import shutil
import subprocess
import tempfile
from pathlib import Path
from echoai.nexus0.compose1.bench import MODULES as BASE, PARENT_MODULES, ECHOAI
from echoai.nexus0.sim3.sandbox import bwrap_argv

HERE = Path(__file__).resolve().parent
MODULES = BASE+('compose1_v2/controller.py', 'compose1_v3/controller.py', 'compose1_v3/perception.py')


class Caged:
    def __init__(self, model, goal, mode='echo32', energy=240):
        self.tmp = tempfile.TemporaryDirectory(prefix='compose-v2-code-')
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
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)
        self.ready = self.call(dict(model=model, goal=list(goal), mode=mode, energy=energy))

    def call(self, value):
        self.proc.stdin.write(json.dumps(value, sort_keys=True)+'\n')
        self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], 20)[0]:
            raise TimeoutError('caged consumer')
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(self.proc.stderr.read()[-1000:])
        return json.loads(line)

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
