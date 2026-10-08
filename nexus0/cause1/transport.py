"""Reuse SIM-3 namespaces and COMPOSE's synchronous public transport."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from echoai.nexus0.compose1_v3.transport import Caged as Parent
from echoai.nexus0.sim3.sandbox import bwrap_argv

HERE = Path(__file__).resolve().parent


class Caged(Parent):
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cause1-public-')
        root = Path(self.tmp.name)
        dest = root/'echoai/nexus0/cause1'
        dest.mkdir(parents=True)
        for name in ('core.py', 'perception.py'):
            shutil.copyfile(HERE/name, dest/name)
        argv = bwrap_argv(HERE/'consumer.py')
        index = argv.index('--remount-ro')
        argv[index:index] = ['--ro-bind', str(root), '/agent']
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)
