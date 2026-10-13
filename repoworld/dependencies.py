"""Curator-only dependency image preparation; never installs in the actor.

Wheel acquisition is a separate explicit preparation step. This module freezes
already provisioned bytes. Build provenance + exported bytes, not a claim that
different hosts produce identical dynamic linker libraries.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from ..pcworld.receipts import canonical
from ..pcworld.snapshots import SnapshotStore
from ..pcworld.runtime import validate_runtime, EXCLUDE

MAX_DEPENDENCY_BYTES=2*1024**3


def image_store(path):
    return SnapshotStore(path,max_files=60000,max_entries=100000,max_bytes=MAX_DEPENDENCY_BYTES,streaming=True)


def freeze_dependencies(path):
    root=Path(path);entries={};size=0
    for p in sorted(root.rglob('*')):
        if p.is_symlink(): raise ValueError('dependency symlinks forbidden')
        if p.is_dir(): continue
        if not p.is_file() or p.stat().st_nlink!=1: raise ValueError('regular dependency file required')
        if '__pycache__' in p.parts: continue
        size+=p.stat().st_size
        if size>MAX_DEPENDENCY_BYTES or len(entries)>=60000: raise ValueError('dependency image limit')
        with p.open('rb') as f: entries[p.relative_to(root).as_posix()]=hashlib.file_digest(f,'sha256').hexdigest()
    return entries


def publish_image(root,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    snap=image_store(directory/'snapshots').capture(root,exclude=())
    (directory/'runtime.json').write_bytes(canonical(dict(schema='repoworld.dependency-runtime.v1',snapshot=snap.id))+b'\n')
    return snap


def load_image(directory):
    directory=Path(directory);record=json.loads((directory/'runtime.json').read_bytes())
    if record['schema']!='repoworld.dependency-runtime.v1': raise ValueError('dependency image schema')
    return validate_runtime(image_store(directory/'snapshots').get(record['snapshot']))


def dependency_runtime(stdlib,deps,directory,*,expected_manifest):
    validate_runtime(stdlib)
    manifest=freeze_dependencies(deps)
    if manifest!=expected_manifest or not manifest: raise ValueError('dependency manifest mismatch')
    with tempfile.TemporaryDirectory(prefix='repoworld-deps-') as temp:
        root=Path(temp)/'root';shutil.copytree(stdlib.root,root)
        for path,entry in stdlib.manifest['entries'].items():
            (root if path=='.' else root/path).chmod(entry['mode'])
        shutil.copytree(deps,root/'deps',ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('work','candidate','repo-base','runner'): (root/name).mkdir(exist_ok=True,mode=0o755)
        (root/'etc/repoworld-dependencies.json').write_bytes(canonical(dict(schema='repoworld.dependencies.v1',
            parent_stdlib=stdlib.id,files=manifest,scope='public-dependencies',network=False)))
        for p in root.rglob('*'):
            if p.is_file(): p.chmod(0o755 if p.stat().st_mode&0o111 else 0o644)
        if freeze_dependencies(deps)!=manifest: raise ValueError('dependencies changed while freezing')
        return publish_image(root,directory)


def freeze_python(interpreter,directory):
    """Relocate an explicitly provisioned trusted CPython to /usr in a rootfs."""
    executable=Path(interpreter).resolve()
    meta=json.loads(subprocess.check_output([str(executable),'-I','-c',
        'import sys,sysconfig,json;print(json.dumps(dict(stdlib=sysconfig.get_path("stdlib"),version=sys.version,minor="%s.%s"%sys.version_info[:2])))'],timeout=10))
    with tempfile.TemporaryDirectory(prefix='repoworld-python-') as temp:
        root=Path(temp);root.chmod(0o755);copied={};queue=[]
        def copy(src,dst):
            src=Path(src);target=root/str(dst).lstrip('/')
            data=src.read_bytes();sha=hashlib.sha256(data).hexdigest()
            if str(dst) in copied:
                if copied[str(dst)]!=sha: raise ValueError('library path collision')
                return
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            target.chmod(0o755 if os.access(src,os.X_OK) else 0o644);copied[str(dst)]=sha
            if data[:4]==b'\x7fELF': queue.append(src)
        copy(executable,'/usr/bin/python3')
        stdlib=Path(meta['stdlib'])
        for p in sorted(stdlib.rglob('*')):
            rel=p.relative_to(stdlib)
            if any(k in EXCLUDE for k in rel.parts) or p.suffix in ('.pyc','.pyo') or p.name.startswith(('_tkinter','_crypt.')): continue
            if p.is_file(): copy(p,Path('/usr/lib')/('python'+meta['minor'])/rel)
        seen=set()
        while queue:
            binary=queue.pop()
            if binary in seen: continue
            seen.add(binary)
            r=subprocess.run(['/usr/bin/ldd',str(binary)],text=True,capture_output=True,timeout=10)
            if r.returncode or 'not found' in r.stdout: raise ValueError('trusted Python ELF closure incomplete: '+str(binary)+' '+r.stdout+r.stderr)
            for line in r.stdout.splitlines():
                source=line.split('=>')[-1].strip().split(' ',1)[0]
                if source.startswith('/'):
                    # CPython's relative RPATH resolves to /usr/lib after relocation.
                    dst='/usr/lib/'+Path(source).name if Path(source).name.startswith('libpython') else source
                    copy(source,dst)
        for name in ('etc','proc','dev','tmp','out','workspace','work','candidate','repo-base','runner'): (root/name).mkdir(exist_ok=True,mode=0o755)
        (root/'etc/pcworld-runtime.json').write_bytes(canonical(dict(schema='pcworld.python-rootfs.v1',python=meta['version'],
            scope='relocated trusted CPython stdlib excluding GUI/installers/crypt',reproduction='frozen byte inventory',execution_determinism=False)))
        return publish_image(root,directory)
