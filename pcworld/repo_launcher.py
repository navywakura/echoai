"""Trusted, pinned launcher, executed only INSIDE the RepoWorld cgroup/namespace.

Exported files are bounded untrusted observations, never property verdicts.
No writes made by the tested process are imported into an immutable candidate.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys


def main():
    request=json.loads(Path('/runner/request.json').read_text())
    protected=set(request.get('protected',[]))
    def ignore(directory,names):
        parent=Path(directory).relative_to('/candidate')
        return [name for name in names if (parent/name).as_posix() in protected]
    shutil.copytree('/candidate','/work',dirs_exist_ok=True,copy_function=shutil.copyfile,ignore=ignore)
    for parent,dirs,files in os.walk('/work'):
        rel=Path(parent).relative_to('/work')
        dirs[:]=[d for d in dirs if (rel/d).as_posix() not in protected]
        os.chmod(parent,0o755)
        for name in files:
            if (rel/name).as_posix() in protected: continue
            source=Path('/candidate')/Path(parent).relative_to('/work')/name
            os.chmod(Path(parent)/name,0o644 | (source.stat().st_mode & 0o111))
    for name in ('.tmp','.home','.out'):
        Path('/work',name).mkdir(exist_ok=True)
    env=dict(os.environ);env.update(request['env'])
    result=subprocess.run(request['argv'],cwd=Path('/work')/request['cwd'],env=env)
    artifacts={};remaining=65536
    # Descriptor traversal rejects symlinked parents as well as symlinked files.
    for name in request['artifacts']:
        fd=None
        try:
            fd=os.open('/work/.out',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            parts=name.split('/')
            for part in parts[:-1]:
                child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                os.close(fd);fd=child
            f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
            try:
                info=os.fstat(f)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>remaining: continue
                data=b''
                while len(data)<=remaining:
                    chunk=os.read(f,min(65536,remaining-len(data)+1))
                    if not chunk: break
                    data+=chunk
                if len(data)>remaining: continue
                remaining-=len(data);artifacts[name]=base64.b64encode(data).decode('ascii')
            finally: os.close(f)
        except OSError: pass
        finally:
            if fd is not None: os.close(fd)
    if request['artifacts']:
        print('\nREPOWORLD_ARTIFACTS_V1 '+json.dumps(artifacts),flush=True)
    return result.returncode if result.returncode>=0 else 128-result.returncode


if __name__=='__main__': sys.exit(main())
