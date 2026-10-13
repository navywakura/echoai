"""Trusted, pinned launcher, executed only INSIDE the RepoWorld cgroup/namespace.

Exported files are bounded untrusted observations, never property verdicts.
No writes made by the tested process are imported into an immutable candidate.
"""
import base64
import ctypes
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys


def protect_directory_ancestors():
    """Keep read-only bind mounts in place; permit cleanup only in scratch.

    A read-only file mount alone is insufficient: its writable parent could be
    renamed and replaced. Landlock's REMOVE_DIR right also mediates directory
    renames, including renameat2 exchanges. Enforce before any candidate code;
    the restriction is inherited and cannot be relaxed by children.
    Linux x86_64/aarch64 syscall numbers, ABI >= 2; unsupported hosts fail closed.
    """
    if os.uname().machine not in ('x86_64', 'aarch64'):
        raise RuntimeError('RepoWorld requires Landlock on x86_64 or aarch64')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    def checked(value):
        if value < 0:
            error = ctypes.get_errno()
            raise OSError(error, 'RepoWorld Landlock: ' + os.strerror(error))
        return value
    if checked(libc.syscall(444, 0, 0, 1)) < 2:
        raise RuntimeError('RepoWorld requires Landlock ABI >= 2')
    remove_dir, refer = 1 << 4, 1 << 13
    class Ruleset(ctypes.Structure):
        _fields_ = [('handled_access_fs', ctypes.c_uint64)]
    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]
    attrs = Ruleset(remove_dir | refer)
    fd = checked(libc.syscall(444, ctypes.byref(attrs), ctypes.sizeof(attrs), 0))
    try:
        # Ordinary production-file renames remain possible. Directory removals
        # and renames are only permitted strictly BELOW the four scratch roots.
        for path, access in [('/work', refer), ('/tmp', refer | remove_dir)] + [
                ('/work/' + name, remove_dir) for name in ('.tmp', '.home', '.out', '.shm')]:
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                rule = Beneath(access, parent)
                checked(libc.syscall(445, fd, 1, ctypes.byref(rule), 0))
            finally:
                os.close(parent)
        checked(libc.prctl(38, 1, 0, 0, 0))  # PR_SET_NO_NEW_PRIVS
        checked(libc.syscall(446, fd, 0))
    finally:
        os.close(fd)


def main():
    request=json.loads(Path('/runner/request.json').read_text())
    protected=set(request.get('protected',[]))
    def ignore(directory,names):
        parent=Path(directory).relative_to('/candidate')
        return [name for name in names if (parent/name).as_posix() in protected]
    shutil.copytree('/candidate','/work',dirs_exist_ok=True,copy_function=shutil.copyfile,ignore=ignore,symlinks=True)
    for parent,dirs,files in os.walk('/work'):
        rel=Path(parent).relative_to('/work')
        dirs[:]=[d for d in dirs if (rel/d).as_posix() not in protected]
        os.chmod(parent,0o755)
        for name in files:
            if (rel/name).as_posix() in protected: continue
            if (Path(parent)/name).is_symlink(): continue
            source=Path('/candidate')/Path(parent).relative_to('/work')/name
            os.chmod(Path(parent)/name,0o644 | (source.stat().st_mode & 0o111))
    for name in ('.tmp','.home','.out','.shm'):
        Path('/work',name).mkdir(exist_ok=True)
    env=dict(os.environ);env.update(request['env'])
    protect_directory_ancestors()
    result=subprocess.run(request['argv'],cwd=Path('/work')/request['cwd'],env=env)
    artifacts={};remaining=512*1024
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
