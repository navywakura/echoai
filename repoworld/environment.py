"""Curator preparation and explicit RepoWorld profile of the existing backend.

No checkout hooks, filters or candidate imports execute in the supervisor.
The stdlib calibration scope is NOT a dependency environment for SWE-bench.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from ..pcworld.receipts import canonical
from ..pcworld.runtime import validate_runtime
from ..pcworld.snapshots import SnapshotStore
from ..pcworld.runner import execute
from .types import EnvironmentRef, RepoBase
from .dataset import public_task
from dataclasses import asdict

REPO_LIMITS = dict(max_files=50000, max_bytes=512*1024*1024, max_entries=100000, max_depth=64, streaming=True)
POLICY = dict(schema='repoworld.environment-policy.v1', network=False, host_usr=False,
              scratch='single-tmpfs', scope='stdlib-calibration', dependencies='Python stdlib only',
              max_bytes=REPO_LIMITS['max_bytes'])
DEPENDENCY_POLICY={**POLICY,'scope':'public-dependencies','dependencies':'frozen read-only /deps inventory'}


def repo_store(path):
    return SnapshotStore(path, **REPO_LIMITS)


def environment_ref(runtime, *, scope):
    if scope not in ('stdlib-calibration','public-dependencies'):
        raise ValueError('dependency environments require a separately validated profile')
    validate_runtime(runtime)
    if any(runtime.manifest['entries'].get(name,{}).get('type')!='directory'
           for name in ('work','candidate','repo-base','runner')):
        raise ValueError('derive repository_runtime with required mount points first')
    # Exact inventory is the snapshot manifest. A scope claim cannot add dependencies.
    policy=POLICY
    if scope=='public-dependencies':
        spec=json.loads((runtime.root/'etc/repoworld-dependencies.json').read_bytes())
        if spec.get('schema')!='repoworld.dependencies.v1' or spec.get('scope')!=scope or not spec.get('files'):
            raise ValueError('dependency image provenance missing')
        policy=DEPENDENCY_POLICY
    return EnvironmentRef(runtime.id, hashlib.sha256(canonical(policy)).hexdigest(), runtime.root)


def runtime_for(ref):
    policies={hashlib.sha256(canonical(p)).hexdigest():p for p in (POLICY,DEPENDENCY_POLICY)}
    if ref.policy_sha256 not in policies:
        raise ValueError('unrecognized environment policy')
    from .dependencies import image_store
    store=(image_store(ref.root.parent.parent) if policies[ref.policy_sha256]==DEPENDENCY_POLICY else
           SnapshotStore(ref.root.parent.parent, max_bytes=256*1024*1024, streaming=True))
    snapshot=store.get(ref.rootfs_sha256)
    if snapshot.root != ref.root:
        raise ValueError('runtime capability mismatch')
    validate_runtime(snapshot)
    if environment_ref(snapshot,scope=policies[ref.policy_sha256]['scope'])!=ref:
        raise ValueError('environment provenance mismatch')
    return snapshot


def git_env():
    return dict(PATH='/usr/bin:/bin', HOME='/nonexistent', LC_ALL='C',
                GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')


def git_argv(source):
    return ['/usr/bin/git','--no-pager','-c','core.hooksPath=/dev/null',
            '-c','core.fsmonitor=false','-c','core.attributesFile=/dev/null',
            '-c','protocol.file.allow=never','-C',str(source)]


def prepare_repo(task, source: Path, environment: EnvironmentRef, expected_commit: str,
                 *, store_dir=None) -> RepoBase:
    public_task(asdict(task)); runtime_for(environment)
    if expected_commit != task.base_commit or not re.fullmatch('[0-9a-f]{40}', expected_commit):
        raise ValueError('base commit mismatch')
    source=Path(source)
    argv=git_argv(source)
    actual=subprocess.run([*argv,'rev-parse','--verify',expected_commit+'^{commit}'],
        check=True,capture_output=True,env=git_env(),timeout=10).stdout.decode().strip()
    if actual != expected_commit:
        raise ValueError('commit object mismatch')
    tree=subprocess.run([*argv,'ls-tree','-r','-l','-z','--full-tree',expected_commit],
        check=True,capture_output=True,env=git_env(),timeout=20).stdout
    entries=[]; total=0
    from ..pcworld.snapshots import _parts
    for record in tree.split(b'\0'):
        if not record: continue
        metadata, raw_path=record.split(b'\t',1)
        mode,kind,oid,size=metadata.decode('ascii').split()
        name=raw_path.decode('utf-8'); parts=_parts(name)
        if any(p in ('.git','.echoai') for p in parts) or mode not in ('100644','100755') or kind!='blob':
            raise ValueError('unsupported Git entry: links/submodules/special modes forbidden')
        total+=int(size)
        if total>REPO_LIMITS['max_bytes'] or len(entries)>=REPO_LIMITS['max_files']:
            raise ValueError('repository exceeds profile')
        entries.append((name,oid,int(size),int(mode,8)&0o777))
    if not entries: raise ValueError('empty base tree')
    store=repo_store(store_dir or (source.parent/(task.instance_id+'-snapshots')))
    with tempfile.TemporaryDirectory(prefix='repoworld-export-') as tmp, tempfile.TemporaryFile() as objects:
        # Git writes blobs to a disk spool, never loads the entire tree into RAM.
        subprocess.run([*argv,'cat-file','--batch'], input=('\n'.join(e[1] for e in entries)+'\n').encode(),
                       stdout=objects,stderr=subprocess.PIPE,check=True,env=git_env(),timeout=120)
        objects.seek(0); root=Path(tmp);root.chmod(0o755)
        for name,oid,size,mode in entries:
            if objects.readline().decode().strip()!=f'{oid} blob {size}':
                raise ValueError('Git object mismatch')
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
            left=size
            with path.open('xb') as out:
                while left:
                    data=objects.read(min(65536,left))
                    if not data: raise ValueError('truncated object')
                    out.write(data);left-=len(data)
            path.chmod(mode)
            if objects.read(1)!=b'\n': raise ValueError('invalid object boundary')
        if objects.read(1): raise ValueError('extra object bytes')
        snapshot=store.capture(root,exclude=('.git',))
    return RepoBase(task,snapshot,environment)


def execute_repo(base: RepoBase, candidate, check_argv: tuple[str,...], *, limits: dict,
                 check_artifacts: tuple[str,...], cwd='.', env=None,probe_source=None):
    runtime=runtime_for(base.environment)
    repo_store(base.snapshot.root.parent.parent).validate(base.snapshot)
    return execute(candidate,list(check_argv),limits=limits,runtime=runtime,profile='repoworld',
                   snapshot_limits=REPO_LIMITS,repo_base=base.snapshot,cwd=cwd,
                   env=env,check_artifacts=check_artifacts,probe_source=probe_source)
