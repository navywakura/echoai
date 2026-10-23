"""Per-run resource wrappers; no global Podman/systemd configuration changes."""
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import re
import subprocess

THREADS = ('LP_NUM_THREADS', 'GALLIUM_NUM_THREADS', 'OMP_NUM_THREADS',
           'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS')
LIMITS = ('--cpus=1.5', '--memory=3g', '--memory-swap=3g', '--pids-limit=128')
LABEL = 'echoai.study=percibex-recovery-20261023'


def cleanup_owned_containers(reason):
    """Stop/remove only this study's full IDs after fresh exact-label checks.

    All commands have short deadlines. Receipts contain IDs and status codes,
    never inherited environment, raw tool output or foreign label contents.
    Fatal supervisor death still needs the external service watcher to call
    this same helper: Python cannot run a finally block after SIGKILL/OOM.
    """
    key, value = LABEL.split('=',1)
    receipt = dict(reason=' '.join(str(reason).split())[:160], label=LABEL,
                   wall_ns=time.time_ns(), operations=[], ownership_rejected=[],
                   invalid_ids=0, errors=[], unavailable_after_stop=[])

    def call(args, stage):
        try:
            result = subprocess.run(['/usr/bin/podman',*args], capture_output=True,
                                    text=True, timeout=5)
        except (OSError,subprocess.TimeoutExpired) as exc:
            receipt['errors'].append(dict(stage=stage,error=type(exc).__name__))
            return None
        return result

    def ownership(ident, stage):
        result = call(['inspect','--type','container','--format','{{json .Config.Labels}}',ident],stage)
        if result is None: return 'error'
        if result.returncode != 0: return 'missing'
        try: labels = json.loads(result.stdout)
        except (ValueError,TypeError): return 'invalid'
        if type(labels) is not dict: return 'invalid'
        return 'owned' if labels.get(key)==value else 'foreign'

    result = call(['ps','--all','--no-trunc','--filter','label='+LABEL,'--format','{{.ID}}'],'list')
    if result is None or result.returncode != 0:
        if result is not None: receipt['errors'].append(dict(stage='list',returncode=result.returncode))
        receipt['ok'] = False
        return receipt
    ids = []
    for token in result.stdout.splitlines():
        token = token.strip()
        if not token: continue
        if not re.fullmatch('[0-9a-f]{64}',token):
            receipt['invalid_ids'] += 1
        elif token not in ids: ids.append(token)
    verified = []
    for ident in ids:
        if ownership(ident,'discover_ownership')=='owned': verified.append(ident)
        else: receipt['ownership_rejected'].append(ident)
    for ident in verified:
        # Revalidate immediately before mutation, independently of discovery.
        if ownership(ident,'before_stop')!='owned':
            receipt['ownership_rejected'].append(ident); continue
        stopped = call(['stop','--time=2',ident],'stop')
        if stopped is not None:
            receipt['operations'].append(dict(id=ident,action='stop',returncode=stopped.returncode))
            if stopped.returncode: receipt['errors'].append(dict(stage='stop',returncode=stopped.returncode))
        state = ownership(ident,'before_remove')
        if state=='missing':
            # --rm commonly removes an already stopped container, but a failed
            # inspect alone is not proof of removal. Keep that distinction.
            receipt['unavailable_after_stop'].append(ident)
        elif state=='owned':
            removed = call(['rm','--force',ident],'remove')
            if removed is not None:
                receipt['operations'].append(dict(id=ident,action='remove',returncode=removed.returncode))
                if removed.returncode: receipt['errors'].append(dict(stage='remove',returncode=removed.returncode))
        else:
            receipt['ownership_rejected'].append(ident)
    receipt['ok'] = not receipt['errors'] and not receipt['invalid_ids'] and not receipt['ownership_rejected']
    return receipt


def bounded_podman_args(args):
    args = list(args)
    if args and args[0] == 'run':
        prefixes = ('--cpus', '--memory', '--memory-swap', '--pids-limit')
        if any(a.split('=')[0] in prefixes for a in args[1:]):
            raise ValueError('resource flags already present')
        args[1:1] = [*LIMITS, '--label', LABEL, *(x for k in THREADS for x in ('-e', k+'=1'))]
    return ['/usr/bin/podman', *args]


PODMAN_WRAPPER = '''#!/usr/bin/python3
import json,os,sys,time
args=list(sys.argv[1:])
if args and args[0]=='run':
    forbidden=('--cpus','--memory','--memory-swap','--pids-limit')
    if any(a.split('=')[0] in forbidden for a in args[1:]):
        raise SystemExit('PERCIBE-X: duplicate resource flags')
    threads=('LP_NUM_THREADS','GALLIUM_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')
    args[1:1]=['--cpus=1.5','--memory=3g','--memory-swap=3g','--pids-limit=128','--label','echoai.study=percibex-recovery-20261023']+[x for k in threads for x in ('-e',k+'=1')]
    log=os.environ.get('PERCIBEX_RESOURCE_LOG')
    if log:
        with open(log,'a') as f:
            f.write(json.dumps({'event':'bounded_podman_run','wall_ns':time.time_ns(),'argv':args})+'\\n')
os.execv('/usr/bin/podman',['/usr/bin/podman']+args)
'''

CAGE_WRAPPER = '''#!/usr/bin/python3
import json,os,resource,sys
allowed=os.sched_getaffinity(0)
os.sched_setaffinity(0,{min(allowed)})
resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,512*1024*1024))
if sys.argv[1:]==['--resource-probe']:
    print(json.dumps({'affinity':sorted(os.sched_getaffinity(0)),'rlimit_as':list(resource.getrlimit(resource.RLIMIT_AS)),
                      'cgroup':open('/proc/self/cgroup').read().strip()}))
else:
    os.execv(REAL_BWRAP,[REAL_BWRAP]+sys.argv[1:])
'''


def _script(path, body):
    raw = body.encode()
    if path.exists():
        if path.read_bytes() != raw: raise ValueError('resource wrapper changed')
    else:
        with path.open('xb') as f: f.write(raw)
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return hashlib.sha256(raw).hexdigest()


def install(directory, real_bwrap):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    cage_body = CAGE_WRAPPER.replace('REAL_BWRAP', repr(str(real_bwrap)))
    hashes = {'podman': _script(directory/'podman', PODMAN_WRAPPER),
              'cage': _script(directory/'bwrap-bounded', cage_body)}
    return dict(directory=str(directory), sha256=hashes, podman_limits=list(LIMITS), podman_label=LABEL,
                cage_affinity_cpus=1, cage_address_space_bytes=512*1024*1024,
                cage_memory_limit_kind='RLIMIT_AS inherited by exec; CPU affinity one allowed host CPU',
                thread_environment={k:'1' for k in THREADS})


def available_memory(path='/proc/meminfo'):
    for line in Path(path).read_text().splitlines():
        if line.startswith('MemAvailable:'): return int(line.split()[1])*1024
    raise RuntimeError('host MemAvailable missing')


def wait_for_memory(minimum=6*1024**3):
    while (available := available_memory()) < minimum:
        print(json.dumps(dict(event='resource_wait', available_bytes=available,
                              required_bytes=minimum, scientific_result=False)), flush=True)
        time.sleep(5)
    return dict(available_bytes=available, required_bytes=minimum)


def supervisor_limits(cgroup_file='/proc/self/cgroup', cgroup_root='/sys/fs/cgroup'):
    line = next(x for x in Path(cgroup_file).read_text().splitlines() if x.startswith('0::'))
    relative = line.split('::',1)[1].lstrip('/')
    root = Path(cgroup_root).resolve()
    current = root/relative
    limits = {'memory.max': [], 'memory.high': []}
    location = current
    while True:
        for key in limits:
            p = location/key
            if p.exists():
                value = p.read_text().strip()
                if value != 'max': limits[key].append(int(value))
        if location == root: break
        if root not in location.parents: raise ValueError('cgroup path outside mount')
        location = location.parent
    effective = {k:min(v) if v else None for k,v in limits.items()}
    bounded = (effective['memory.max'] is not None and effective['memory.max'] <= 2*1024**3
               and effective['memory.high'] is not None and effective['memory.high'] <= 1536*1024**2)
    return dict(cgroup=str(current), effective=effective, bounded=bounded,
                requested_memory_max_bytes=2*1024**3, requested_memory_high_bytes=1536*1024**2)


@contextlib.contextmanager
def active(cage_runtime, directory, log):
    details = install(directory, cage_runtime.lock['sandbox']['path'])
    runtime = copy.deepcopy(cage_runtime)
    runtime.lock['sandbox']['path'] = str(Path(directory)/'bwrap-bounded')
    keys = ['PATH', 'PERCIBEX_RESOURCE_LOG', *THREADS]
    before = {k:os.environ.get(k) for k in keys}
    os.environ['PATH'] = str(directory)+os.pathsep+os.environ.get('PATH','/usr/bin')
    os.environ['PERCIBEX_RESOURCE_LOG'] = str(log)
    for k in THREADS: os.environ[k] = '1'
    try:
        yield runtime, details
    finally:
        for k,v in before.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
