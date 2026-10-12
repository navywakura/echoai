"""Mandatory Linux execution boundary. Candidate output is NEVER a verdict.

The trusted supervisor stays outside both namespaces and the resource cgroup.
No user home, host sockets, parent workspace, checkers or receipt keys are mounted.
The only writable filesystems are size-bounded tmpfs. No unsandboxed fallback.
"""
from __future__ import annotations

import hashlib
import errno
import base64
import json
import math
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import time
import uuid

DEFAULTS = dict(wall_ms=5000, cpu_ms=3000, memory_bytes=256*1024*1024,
                pids=32, output_bytes=65536, disk_bytes=16*1024*1024)
_PROPERTIES = ('ActiveState','SubState','ExecMainStatus','ExecMainCode','CPUUsageNSec',
               'MemoryPeak','ControlGroup','Result','MemoryMax','TasksMax')


def _show(unit):
    p = subprocess.run(['/usr/bin/systemctl','--user','show',unit,
                        '--property='+','.join(_PROPERTIES)], capture_output=True, timeout=3)
    return dict(line.split('=',1) for line in p.stdout.decode().splitlines() if '=' in line)


def _integer(value):
    return int(value) if str(value).isdigit() else 0


def _stop(unit):
    try:
        subprocess.run(['/usr/bin/systemctl','--user','kill','--signal=KILL',unit],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
        # Read final cgroup accounting after termination, before dropping the unit.
        # A tiny bounded wait lets systemd reap the killed service and aggregate it.
        latest={}
        for _ in range(20):
            latest=_show(unit)
            if latest.get('SubState') in ('exited','failed','dead') or not latest: break
            time.sleep(.01)
        return latest
    finally:
        subprocess.run(['/usr/bin/systemctl','--user','stop',unit],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)


def environment_identity(runtime=None):
    """Versioned runtime declaration; actual dependency manifests must accompany tasks.

    /usr is a read-only HOST runtime, not a pinned image. Consequently the first
    release never authorizes persistent execution-result caching by this alone.
    """
    files = {}
    for name in ('/usr/bin/python3','/usr/bin/bwrap','/usr/bin/systemd-run'):
        p=Path(name).resolve()
        files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if runtime is not None:
        from .runtime import validate_runtime
        validate_runtime(runtime)
        return {'schema':2,'files':{k:v for k,v in files.items() if not Path(k).name.startswith('python')},
                'kernel':os.uname().release,'machine':os.uname().machine,
                'runtime':'pinned Python rootfs','runtime_snapshot':runtime.id,
                'dependencies_pinned':True,'hermetic_cacheable':False,
                'cache_scope':'pure checker only; arbitrary candidate execution never cached'}
    return {'schema':1,'files':files,'python':os.sys.version,'kernel':os.uname().release,
            'runtime':'host /usr read-only','hermetic_cacheable':False}


def execute(workspace: Path, argv: list[str], *, limits=None, stdin=b'', runtime=None) -> dict:
    """Run a structured operator-authorized argv, returning host observations.

    Copies regular files into a private, immutable candidate snapshot before
    launch. Data flows out through bounded stdout/stderr only. Generated tests
    may run here but their assertions/output confer no semantic authority.
    """
    for command in ('bwrap','systemd-run','systemctl'):
        if not shutil.which(command):
            raise RuntimeError('UNSUPPORTED_ENVIRONMENT: '+command+' required; no fallback')
    if not Path('/sys/fs/cgroup/cgroup.controllers').is_file():
        raise RuntimeError('UNSUPPORTED_ENVIRONMENT: cgroup v2 required')
    caps={**DEFAULTS,**(limits or {})}
    if set(caps)!=set(DEFAULTS) or any(type(v) is not int or v<=0 for v in caps.values()):
        raise ValueError('invalid integer limits')
    if (caps['wall_ms']>600000 or caps['cpu_ms']>600000 or
        not 32*1024*1024<=caps['memory_bytes']<=2*1024**3 or
        not 4<=caps['pids']<=128 or caps['output_bytes']>4*1024**2 or caps['disk_bytes']>64*1024**2):
        raise ValueError('limits outside PCWORLD-1 development bounds')
    if (not isinstance(argv,list) or not argv or len(argv)>128 or
        any(not isinstance(a,str) or '\0' in a or len(a)>65536 for a in argv) or
        not argv[0].startswith(('/usr/bin/','/bin/'))):
        raise ValueError('structured argv with an explicit runtime executable required')
    if not isinstance(stdin,bytes) or len(stdin)>1024**2:
        raise ValueError('stdin exceeds limit')
    # Import here avoids a separate snapshot implementation. Every execution,
    # including legacy MCP, crosses this exact backend and capability copier.
    from .snapshots import SnapshotStore, Snapshot
    with tempfile.TemporaryDirectory(prefix='echo-pcworld-job-') as temp:
        store=SnapshotStore(Path(temp)/'snapshots')
        snapshot=store.capture(workspace if isinstance(workspace,Snapshot) else Path(workspace))
        if runtime is not None:
            from .runtime import validate_runtime
            validate_runtime(runtime)
        return _execute_snapshot(snapshot,argv,caps,stdin,runtime)


def _execute_snapshot(snapshot,argv,caps,stdin,runtime=None):
    unit='echo-pcworld-'+uuid.uuid4().hex+'.service'
    mounts=(['--ro-bind',str(runtime.root),'/'] if runtime is not None else
            ['--ro-bind','/usr','/usr','--symlink','usr/bin','/bin',
             '--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64'])
    bwrap=['/usr/bin/bwrap','--unshare-all','--unshare-user','--die-with-parent','--new-session',
           '--cap-drop','ALL','--disable-userns',*mounts,
           '--proc','/proc','--dev','/dev','--size',str(caps['disk_bytes']//2),'--tmpfs','/tmp',
           '--size',str(caps['disk_bytes']//2),'--tmpfs','/out',
           '--ro-bind',str(snapshot.root),'/workspace','--chdir','/workspace',
           '--clearenv','--setenv','PATH','/usr/bin:/bin','--setenv','HOME','/tmp',
           '--setenv','TMPDIR','/tmp','--setenv','LANG','C.UTF-8','--setenv','TZ','UTC',
           '--setenv','PYTHONDONTWRITEBYTECODE','1','--setenv','PYTHONHASHSEED','0',
           '--setenv','OMP_NUM_THREADS','1','--setenv','OPENBLAS_NUM_THREADS','1',
           '--',*argv]
    # RemainAfterExit keeps the service accounting available until this supervisor
    # has copied it. RuntimeMaxSec is an independent wall watchdog if we disappear.
    args=['/usr/bin/systemd-run','--user','--quiet','--pipe','--unit='+unit,
          '-p','Type=exec','-p','RemainAfterExit=yes','-p','KillMode=control-group',
          '-p','TimeoutStopSec=1','-p',f'RuntimeMaxSec={math.ceil(caps["wall_ms"]/1000)+2}',
          '-p',f'MemoryMax={caps["memory_bytes"]}','-p','MemorySwapMax=0',
          '-p',f'TasksMax={caps["pids"]}','-p','MemoryAccounting=yes',
          '-p','LimitCORE=0','-p','LimitNOFILE=128',*bwrap]
    started=time.monotonic_ns();out=bytearray();err=bytearray();reason=None;props={};cg=None
    cpu_us=peak=0;events={};proc=None
    try:
        with tempfile.TemporaryFile() as input_file:
            input_file.write(stdin);input_file.seek(0)
            proc=subprocess.Popen(args,stdin=input_file,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            selector=selectors.DefaultSelector()
            for stream,target in ((proc.stdout,out),(proc.stderr,err)):
                os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,target)
            next_poll=0
            while True:
                elapsed=(time.monotonic_ns()-started)//1_000_000
                for key,_ in selector.select(.02):
                    chunk=os.read(key.fd,65536)
                    if not chunk:
                        selector.unregister(key.fileobj);key.fileobj.close();continue
                    available=max(0,caps['output_bytes']-len(out)-len(err))
                    key.data.extend(chunk[:available])
                    if len(chunk)>available: reason=reason or 'OUTPUT_LIMIT'
                if elapsed>=next_poll:
                    props=_show(unit);next_poll=elapsed+50
                    cpu_us=max(cpu_us,_integer(props.get('CPUUsageNSec'))//1000)
                    peak=max(peak,_integer(props.get('MemoryPeak')))
                    if props.get('ControlGroup'):
                        cg=Path('/sys/fs/cgroup'+props['ControlGroup'])
                    if cg is not None and cg.is_dir():
                        for name in ('memory.events','pids.events'):
                            try:
                                for line in (cg/name).read_text().splitlines():
                                    key,val=line.split();events[name+'.'+key]=int(val)
                            except OSError as exc:
                                # A finished/removed cgroup can disappear between
                                # is_dir and read, including ENODEV on kernfs.
                                if exc.errno not in (errno.ENOENT,errno.ENODEV): raise
                    if cpu_us>=caps['cpu_ms']*1000: reason=reason or 'CPU_LIMIT'
                    if props.get('SubState') in ('exited','failed','dead'):
                        break
                if elapsed>=caps['wall_ms']: reason=reason or 'TIMEOUT'
                if reason: break
                if proc.poll() is not None:
                    # Failure to construct the sandbox is an environment error;
                    # nothing retries the candidate outside the boundary.
                    if not props or props.get('ActiveState')=='inactive': break
            # Drain available output; never block on a descendant's open pipe.
            for _ in range(16):
                ready=selector.select(0)
                if not ready: break
                for key,_ in ready:
                    chunk=os.read(key.fd,65536)
                    if not chunk:
                        selector.unregister(key.fileobj);key.fileobj.close();continue
                    available=max(0,caps['output_bytes']-len(out)-len(err))
                    key.data.extend(chunk[:available])
                    if len(chunk)>available: reason=reason or 'OUTPUT_LIMIT'
            selector.close()
    finally:
        try:
            final=_show(unit)
        finally:
            stopped=_stop(unit)
        cpu_us=max(cpu_us,_integer(stopped.get('CPUUsageNSec'))//1000)
        peak=max(peak,_integer(stopped.get('MemoryPeak')))
        cpu_us=max(cpu_us,_integer(final.get('CPUUsageNSec'))//1000)
        peak=max(peak,_integer(final.get('MemoryPeak')))
        if final.get('ExecMainCode') not in (None,'0'): props=final
        if proc is not None:
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill();proc.wait()
            for stream in (proc.stdout,proc.stderr):
                if stream is not None: stream.close()
        subprocess.run(['/usr/bin/systemctl','--user','reset-failed',unit],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=3)
    empty=cg is None or not cg.exists() or not (cg/'cgroup.procs').read_text().strip()
    if not empty: raise RuntimeError('ISOLATION_FAILURE: surviving job processes')
    exit_code=_integer(props.get('ExecMainStatus')) if props.get('ExecMainCode')=='1' else None
    signal=_integer(props.get('ExecMainStatus')) if props.get('ExecMainCode') in ('2','3') else None
    if events.get('memory.events.oom_kill',0) or props.get('Result')=='oom-kill':
        reason=reason or 'MEMORY_LIMIT'
    if exit_code is None and not signal and not reason:
        raise RuntimeError('UNSUPPORTED_ENVIRONMENT: isolated job could not start: '+err.decode(errors='replace')[-500:])
    return {'schema':'pcworld.execution.v1','status':reason or ('EXITED' if exit_code==0 else 'FAILED'),
            'snapshot':snapshot.id,'argv':argv,'exit_code':exit_code,'signal':signal,
            'stdout':out.decode(errors='replace'),'stderr':err.decode(errors='replace'),
            'stdout_b64':base64.b64encode(out).decode('ascii'),
            'stderr_b64':base64.b64encode(err).decode('ascii'),
            'stdout_sha256':hashlib.sha256(out).hexdigest(),'stderr_sha256':hashlib.sha256(err).hexdigest(),
            'claim_status':'unknown','task_success':False,'observation_integrity':'supervisor_observed',
            'resources':{'cpu_us':cpu_us,'wall_ms':(time.monotonic_ns()-started)//1_000_000,
                         'memory_peak_bytes':peak,'output_bytes':len(out)+len(err),
                         'measurement':'systemd cgroup v2 CPUUsageNSec/MemoryPeak; 50ms CPU watchdog',
                         'events':events},'limits':caps,
            'isolation':{'backend':'bubblewrap+cgroup-v2','unit':unit,'network_disabled':True,
                         'host_usr_mounted':runtime is None,'runtime_snapshot':runtime.id if runtime else None,
                         'parent_mounted':False,'workspace_readonly':True,'job_empty':empty}}
