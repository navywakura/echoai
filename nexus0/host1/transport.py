"""Reuse the SIM-3 cage/transport; no world, seed or future outcome mounted."""
import shutil
import subprocess
import tempfile
from pathlib import Path
from echoai.nexus0.compose1_v3.transport import Caged as Parent
from echoai.nexus0.compose1.bench import ECHOAI
from echoai.nexus0.sim3.sandbox import bwrap_argv

HERE = Path(__file__).resolve().parent


class Caged(Parent):
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='host1-public-')
        root = Path(self.tmp.name)
        sources = {HERE/'core.py': 'echoai/nexus0/host1/core.py',
                   HERE.parent/'cause1/core.py': 'echoai/nexus0/cause1/core.py',
                   ECHOAI.parent/'core/wsp.py': 'core/wsp.py',
                   ECHOAI.parent/'core/qn.py': 'core/qn.py'}
        for source, relative in sources.items():
            target = root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        argv = bwrap_argv(HERE/'consumer.py')
        index = argv.index('--remount-ro')
        argv[index:index] = ['--ro-bind', str(root), '/agent']
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, bufsize=1)
