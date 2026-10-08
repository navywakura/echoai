"""SIM-3 namespaces and existing synchronous transport, explicit dependencies."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from echoai.nexus0.compose1_v3.transport import Caged as Parent
from echoai.nexus0.sim3.sandbox import bwrap_argv

HERE = Path(__file__).resolve().parent


class Caged(Parent):
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='power1-public-')
        root = Path(self.tmp.name)
        for source, relative in [(HERE/'core.py', 'power1/core.py'),
                                 (HERE.parent/'cause1/core.py', 'cause1/core.py')]:
            target = root/'echoai/nexus0'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        argv = bwrap_argv(HERE/'consumer.py')
        index = argv.index('--remount-ro')
        argv[index:index] = ['--ro-bind', str(root), '/agent']
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)
