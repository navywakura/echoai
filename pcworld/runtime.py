"""Exportable pinned Python userspace, not a reproducible kernel or arbitrary OS.

The builder reads only the trusted operator's system Python installation. It is
never exposed as a candidate tool. Reproduction uses the exported bytes, not a
second build from a possibly updated host. No package installation at run time.
"""
from pathlib import Path, PurePosixPath
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import sysconfig
import shutil
import tarfile
import tempfile

from .snapshots import SnapshotStore
from .receipts import canonical

MAX_BYTES=256*1024*1024
EXCLUDE={'site-packages','__pycache__','test','tests','idlelib','tkinter','turtledemo','ensurepip'}

def runtime_store(directory):
    return SnapshotStore(Path(directory)/'snapshots',max_bytes=MAX_BYTES)

def validate_runtime(snapshot):
    # Validate the existing content store, not an unverified mount path.
    # Explicit dependency images have a separate bounded profile. Never extend
    # the default PCWorld workspace/candidate bounds.
    dependencies=snapshot.manifest['entries'].get('etc/repoworld-dependencies.json')
    store=(SnapshotStore(snapshot.root.parent.parent,max_bytes=2*1024**3,max_files=60000,max_entries=100000,streaming=True)
           if dependencies else SnapshotStore(snapshot.root.parent.parent,max_bytes=MAX_BYTES,streaming=True))
    store.validate(snapshot)
    spec=json.loads((snapshot.root/'etc/pcworld-runtime.json').read_text())
    if spec.get('schema')!='pcworld.python-rootfs.v1': raise ValueError('unsupported runtime')
    if not (snapshot.root/'usr/bin/python3').is_file(): raise ValueError('missing Python runtime')
    return snapshot

def _publish(directory,root):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    snapshot=runtime_store(directory).capture(root,exclude=())
    (directory/'runtime.json').write_bytes(canonical({'schema':'pcworld.runtime.v1','snapshot':snapshot.id})+b'\n')
    return snapshot

def load_runtime(directory):
    record=json.loads((Path(directory)/'runtime.json').read_text())
    if record.get('schema')!='pcworld.runtime.v1': raise ValueError('unsupported runtime record')
    return validate_runtime(runtime_store(directory).get(record['snapshot']))


def repository_runtime(snapshot, directory):
    """Derive an exact-byte stdlib image with mount points; no SWE dependencies.

    Never changes the input image or its manifest. RepoWorld must not try to
    create mount points inside an already read-only root bind.
    """
    validate_runtime(snapshot)
    with tempfile.TemporaryDirectory(prefix='pcworld-repo-runtime-') as temp:
        root=Path(temp)/'root'
        shutil.copytree(snapshot.root,root)
        for path,entry in snapshot.manifest['entries'].items():
            (root if path=='.' else root/path).chmod(entry['mode'])
        for name in ('work','candidate','repo-base','runner'):
            (root/name).mkdir(mode=0o755,exist_ok=True)
        return _publish(directory,root)

def build_runtime(directory):
    """Freeze the current trusted Python plus stdlib and ELF dependency closure."""
    with tempfile.TemporaryDirectory(prefix='pcworld-runtime-build-') as temp:
        root=Path(temp);root.chmod(0o755)
        for name in ('proc','dev','tmp','out','workspace','etc'):
            (root/name).mkdir(mode=0o755)
        copied={}
        def copy(source,destination):
            source=Path(source);destination=Path(destination)
            target=root/str(destination).lstrip('/')
            data=source.read_bytes()
            target.parent.mkdir(parents=True,exist_ok=True)
            if str(destination) in copied:
                if copied[str(destination)]!=hashlib.sha256(data).hexdigest():
                    raise ValueError('runtime path collision')
                return
            target.write_bytes(data)
            target.chmod(0o755 if os.access(source,os.X_OK) else 0o644)
            copied[str(destination)]=hashlib.sha256(data).hexdigest()
        interpreter=Path(sys.executable).resolve()
        copy(interpreter,'/usr/bin/python3')
        stdlib=Path(sysconfig.get_path('stdlib'))
        shared=[interpreter]
        for path in sorted(stdlib.rglob('*')):
            relative=path.relative_to(stdlib)
            if any(part in EXCLUDE for part in relative.parts): continue
            if path.is_file() and path.suffix not in ('.pyc','.pyo'):
                # Tcl/Tk is not an admitted dependency of the repair corpus.
                if path.name.startswith('_tkinter.'): continue
                copy(path,path)
                if '.so' in path.name: shared.append(path)
        # ldd is used ONLY on trusted host interpreter/extensions, never on a
        # candidate binary. Every dependency is copied at its loader-visible path.
        visited=set()
        while shared:
            binary=shared.pop()
            if str(binary) in visited: continue
            visited.add(str(binary))
            result=subprocess.run(['/usr/bin/ldd',str(binary)],capture_output=True,text=True,timeout=10)
            if result.returncode or 'not found' in result.stdout: raise RuntimeError('unresolved trusted runtime dependency: '+str(binary))
            for line in result.stdout.splitlines():
                part=line.split('=>',1)[-1].strip().split(' ',1)[0]
                if part.startswith('/'):
                    copy(part,part);shared.append(Path(part))
        spec={'schema':'pcworld.python-rootfs.v1','python':sys.version,'machine':platform.machine(),
              'scope':'Python stdlib excluding GUI, installers and third-party packages',
              'reproduction':'exported exact bytes; build from host is not reproducible from source',
              'execution_determinism':False}
        (root/'etc/pcworld-runtime.json').write_bytes(canonical(spec)+b'\n')
        return _publish(directory,root)

def export_runtime(snapshot,archive):
    validate_runtime(snapshot)
    # Fixed order, modes, uid and timestamps make the archive itself stable.
    with tarfile.open(archive,'w',format=tarfile.USTAR_FORMAT) as tar:
        for name,entry in sorted(snapshot.manifest['entries'].items()):
            info=tarfile.TarInfo(name);info.mode=entry['mode'];info.mtime=0
            if entry['type']=='directory':
                info.type=tarfile.DIRTYPE;tar.addfile(info)
            else:
                data=(snapshot.root/name).read_bytes();info.size=len(data)
                tar.addfile(info,io.BytesIO(data))

def import_runtime(archive,directory,*,expected_id):
    """Import regular files only; never tar.extractall or trust archive paths."""
    if not isinstance(expected_id,str) or len(expected_id)!=64: raise ValueError('full runtime identity required')
    with tempfile.TemporaryDirectory(prefix='pcworld-runtime-import-') as temp:
        root=Path(temp);seen=set();size=0
        # Parse fixed USTAR headers ourselves before any tarfile metadata
        # expansion. GNU/PAX/sparse/link entries are not in our export format.
        # A declared huge PAX header must never reach tarfile's large read.
        with Path(archive).open('rb') as stream:
            if os.fstat(stream.fileno()).st_size>MAX_BYTES+20000*1024+10240:
                raise ValueError('runtime archive too large')
            while True:
                header=stream.read(512)
                if header==b'\0'*512:
                    if stream.read(512)!=b'\0'*512: raise ValueError('invalid tar terminator')
                    while chunk:=stream.read(65536):
                        if chunk.strip(b'\0'): raise ValueError('data after tar terminator')
                    break
                if len(header)!=512: raise ValueError('truncated runtime archive')
                try: member=tarfile.TarInfo.frombuf(header,'utf-8','strict')
                except (tarfile.HeaderError,UnicodeError) as exc: raise ValueError('invalid tar header') from exc
                name=member.name;parts=PurePosixPath(name).parts
                if (name in seen or len(seen)>=20000 or not name or name.startswith('/') or
                    '..' in parts or '\\' in name or (name!='.' and str(PurePosixPath(name))!=name) or
                    member.type not in (tarfile.REGTYPE,tarfile.AREGTYPE,tarfile.DIRTYPE) or
                    member.mode not in (0o644,0o755) or (member.isdir() and member.size)):
                    raise ValueError('unsafe runtime archive entry')
                seen.add(name);size+=member.size
                if size>MAX_BYTES or member.size<0: raise ValueError('runtime archive too large')
                target=root/name
                if member.isdir(): target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as f:
                        remaining=member.size
                        while remaining:
                            chunk=stream.read(min(65536,remaining))
                            if not chunk: raise ValueError('truncated file data')
                            f.write(chunk);remaining-=len(chunk)
                    padding=(-member.size)%512
                    if len(stream.read(padding))!=padding: raise ValueError('truncated tar padding')
                target.chmod(member.mode)
        # Validate identity before publishing even an invalid operator archive.
        with tempfile.TemporaryDirectory(prefix='pcworld-runtime-verify-') as check:
            snap=SnapshotStore(Path(check)/'store',max_bytes=MAX_BYTES).capture(root,exclude=())
            if snap.id!=expected_id: raise ValueError('runtime identity mismatch')
        return validate_runtime(_publish(directory,root))

def host_dependencies():
    """Hash the trusted supervisor Python/stdlib and ELF closure, uncached.

    Used for pure-check cache identity. This host process is trusted; generated
    code cannot import into it. Changes in excluded GUI/site packages are outside
    the admitted checker dependency scope.
    """
    stdlib=Path(sysconfig.get_path('stdlib'));files={Path(sys.executable).resolve()}
    for path in stdlib.rglob('*'):
        if (path.is_file() and not any(part in EXCLUDE for part in path.relative_to(stdlib).parts)
                and path.suffix not in ('.pyc','.pyo') and not path.name.startswith('_tkinter.')):
            files.add(path)
    binaries=[p for p in files if '.so' in p.name or p==Path(sys.executable).resolve()]
    visited=set()
    while binaries:
        binary=binaries.pop()
        if binary in visited: continue
        visited.add(binary)
        result=subprocess.run(['/usr/bin/ldd',str(binary)],capture_output=True,text=True,timeout=10)
        if result.returncode or 'not found' in result.stdout: raise RuntimeError('unresolved checker dependency')
        for line in result.stdout.splitlines():
            name=line.split('=>',1)[-1].strip().split(' ',1)[0]
            if name.startswith('/'):
                dep=Path(name);files.add(dep);binaries.append(dep)
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
