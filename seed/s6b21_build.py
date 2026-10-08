"""Stage a private, minimal B21-A runtime and wait for the audited B20 gate."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from seed import s6b21 as r

REPO=r.REPO
HERE=REPO/'lab/kaggle/s6b21-20261006'
RUNTIME=r.ROOT/'runtime'
CONTRACT='docs/ECHO45-S6-B21-A-DESIGN.md'


def immutable(path,value):
    if path.exists():
        if r.read(path)!=json.loads(r.canonical(value)):raise RuntimeError('frozen artifact differs: '+str(path))
    else:r.atomic(path,value)


def closure():
    pending={'seed.s6b21','seed.s6b21_review','seed.s6b21_build','echo_arc.agent',
             'echo_arc.runner','echo_arc.temporal_bench','echo_arc.temporal_agent','seed.arc3gym'}
    done=set();files=set()
    while pending:
        module=pending.pop()
        if module in done or module.endswith('_exam'):continue
        path=REPO/(module.replace('.','/')+'.py')
        if not path.is_file():path=REPO/module.replace('.','/')/'__init__.py'
        if not path.is_file():continue
        done.add(module);files.add(str(path.relative_to(REPO)))
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import):names=[x.name for x in node.names]
            elif isinstance(node,ast.ImportFrom):
                prefix=node.module or ''
                if node.level:prefix='.'.join(module.split('.')[:-node.level]+([prefix] if prefix else []))
                names=[prefix]+[prefix+'.'+x.name for x in node.names]
            else:continue
            pending.update(n for n in names if n.startswith(('seed.','echo_arc.')))
    files.update(['seed/__init__.py','echo_arc/__init__.py','lab/temporal/h1h3-exam-20260927/evaluate.py'])
    forbidden={'seed/s6b20_capacity.py','seed/s6probe1.py','seed/s6probe2.py'}
    if files&forbidden or any(x.startswith(('tests/','docs/')) for x in files):
        raise RuntimeError('research/control content reached runtime closure')
    return sorted(files)


def prior_sources():
    profiles={}
    for name in ('s6b18-20261005','s6b19-20261005','s6b20-20261006'):
        path=REPO/'lab/kaggle'/name/'input/manifest.json';m=r.read(path)
        for f,h in m['sources'].items():
            if r.file_sha(REPO/f)!=h:raise RuntimeError('earlier frozen source changed: '+f)
        for f,h in m['inputs'].items():
            if r.file_sha(path.parent/f)!=h:raise RuntimeError('earlier frozen input changed: '+f)
        profiles[name]=r.file_sha(path)
    return profiles


def partition_review():
    """Inspect historical partition metadata, never protected game outcomes."""
    command=['rg','--files','lab/seed','lab/kaggle','-g','*manifest*.json','-g','profile.json',
             '-g','*freeze*.json','-g','*partition*.json','-g','!**/runtime/**',
             '-g','!**/source-archive/**','-g','!**/cache/**','-g','!**/collected/**']
    paths=subprocess.run(command,cwd=REPO,text=True,capture_output=True,check=True).stdout.splitlines()
    target=set(r.B);inventory={};overlap=[]
    def visit(obj):
        if isinstance(obj,list):
            if len(obj)==4 and all(type(v) is int for v in obj) and tuple(obj) in target:return [obj]
            return [item for child in obj for item in visit(child)]
        if isinstance(obj,dict):return [item for child in obj.values() for item in visit(child)]
        return []
    for name in sorted(paths):
        if 's6b21-' in name:continue
        path=REPO/name;inventory[name]=r.file_sha(path)
        hits=visit(r.read(path))
        if hits:overlap.append(dict(path=name,cases=hits))
    value=dict(valid=not overlap and not(set(r.B)&set(r.DEVELOPMENT)),
               protected_B=r.B,inventory=inventory,overlap=overlap,
               scope='explicit case tuples in historical profiles; design/source range review also required',
               source_range_review='64000 references before B21 are workload caps; no declared prior 64000-64039 partition',
               exam_opened=False)
    immutable(HERE/'partition-review.json',value);return value


def b20_gate():
    status=r.read(REPO/'lab/seed/s6b20-20261006/pipeline-status.json')
    if status['stage'].startswith('BLOCKED'):raise RuntimeError('B20 supervisor is blocked')
    if status['stage'] not in ('MICRO_CLOSED_NO_PROMOTION','QUALIFIED_FOR_PILOT_CONTRACT'):return None
    root=REPO/'lab/seed/s6b20-20261006/kaggle-results'
    names=('closed.json','micro.json','micro-audit.json','arithmetic-review.json')
    if not all((root/n).exists() for n in names):return None
    closed,micro,audit,arithmetic=(r.read(root/n) for n in names)
    manifest=REPO/'lab/kaggle/s6b20-20261006/input/manifest.json'
    profile=r.sha(r.read(manifest))
    if not (closed['valid'] and micro['valid'] and audit['valid'] and arithmetic['valid']):
        raise RuntimeError('invalid B20 closure')
    if audit['micro_sha256']!=r.sha(micro) or arithmetic['profile_sha256']!=profile or micro['profile_sha256']!=profile:
        raise RuntimeError('unlinked B20 closure')
    capacity=REPO/'lab/seed/s6b20-capacity-20261006'
    c=r.read(capacity/'capacity-audit.json');ca=r.read(capacity/'arithmetic-review.json')
    if not c['valid'] or not ca['valid']:raise RuntimeError('B20 capacity not audited')
    return dict(valid=True,arithmetic_valid=True,source=str(root.relative_to(REPO)),
                receipts={n:r.file_sha(root/n) for n in names},profile_sha256=profile,
                capacity_audit_sha256=r.file_sha(capacity/'capacity-audit.json'),
                capacity_review_sha256=r.file_sha(capacity/'arithmetic-review.json'),
                physical_games=arithmetic['cache_records'],s6_green=False)


def prepare():
    HERE.mkdir(parents=True,exist_ok=True)
    log=HERE/'tests-final.log'
    if '\nOK\n' not in log.read_text():raise RuntimeError('passing final tests required')
    files=closure();intent=dict(configuration=r.config(),sources={f:r.file_sha(REPO/f) for f in files},
        contract_sha256=r.file_sha(REPO/CONTRACT),tests_sha256=r.file_sha(log),
        test_sources={f:r.file_sha(REPO/f) for f in ('tests/test_s6b21.py','tests/test_s6b20.py','tests/test_s6b18.py')},
        baseline_sha256=r.sha(r.read(REPO/'lab/kaggle/s6b20-20261006/input/baseline.json')),
        prior_profiles=prior_sources(),private=True,paid=False,
        partition_review_sha256=r.file_sha(HERE/'partition-review.json'))
    if not r.read(HERE/'partition-review.json')['valid']:raise RuntimeError('partition review missing')
    immutable(HERE/'intent.json',intent)
    r.INPUT.mkdir(parents=True,exist_ok=True)
    immutable(r.INPUT/'baseline.json',r.read(REPO/'lab/kaggle/s6b20-20261006/input/baseline.json'))
    for f in files:
        path=RUNTIME/f;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and r.file_sha(path)!=intent['sources'][f]:raise RuntimeError('staged source changed')
        if not path.exists():shutil.copyfile(REPO/f,path)
    r.status('PREPARED_WAITING_B20_AUDIT',games_started=False,intent_sha256=r.sha(intent))
    return intent


def check_intent():
    intent=r.read(HERE/'intent.json')
    for f,h in intent['sources'].items():
        if r.file_sha(REPO/f)!=h or r.file_sha(RUNTIME/f)!=h:raise RuntimeError('queued source changed: '+f)
    if r.file_sha(REPO/CONTRACT)!=intent['contract_sha256']:raise RuntimeError('queued contract changed')
    if r.file_sha(HERE/'tests-final.log')!=intent['tests_sha256']:raise RuntimeError('tests receipt changed')
    for f,h in intent['test_sources'].items():
        if r.file_sha(REPO/f)!=h:raise RuntimeError('queued test source changed')
    if r.sha(r.read(r.INPUT/'baseline.json'))!=intent['baseline_sha256']:raise RuntimeError('queued baseline changed')
    if prior_sources()!=intent['prior_profiles']:raise RuntimeError('prior profile changed')
    return intent


def launch():
    intent=check_intent();gate=b20_gate()
    if gate is None:return False
    immutable(r.INPUT/'b20-closure.json',gate)
    manifest=dict(configuration=intent['configuration'],stage='micro',sources=intent['sources'],
        inputs={n:r.file_sha(r.INPUT/n) for n in ('baseline.json','b20-closure.json')},
        python='3.12.13',numpy='2.3.2',arcengine='0.9.3',
        tests_sha256=intent['tests_sha256'],contract_sha256=intent['contract_sha256'],
        partition_review_sha256=intent['partition_review_sha256'],intent_sha256=r.sha(intent))
    immutable(r.INPUT/'manifest.json',manifest)
    env=dict(os.environ,ECHO_B21_ROOT=str(r.ROOT),ECHO_B21_INPUT=str(r.INPUT),
             PYTHONPATH=str(RUNTIME),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    r.status('LAUNCHING',profile_sha256=r.sha(manifest),runtime=str(RUNTIME),games_started=False)
    subprocess.run([sys.executable,'-u','-m','seed.s6b21','follow'],cwd=RUNTIME,env=env,check=True)
    return True


def main(args):
    if args==['partitions']:print(r.canonical(partition_review()));return
    if args==['prepare']:prepare();return
    if args!=['watch']:raise ValueError('use prepare/watch')
    while True:
        if launch():return
        r.status('WAITING_B20_AUDIT',games_started=False)
        time.sleep(45)


if __name__=='__main__':
    try:main(sys.argv[1:])
    except Exception as exc:
        r.status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));raise
