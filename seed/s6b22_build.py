"""Recover exact B21 receipts, review exposure, and freeze the private B22 runtime."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from seed import s6b22 as r
from seed import s6b21_build as prior

REPO=r.REPO
RUNTIME=r.ROOT/'runtime'
CONTRACT='docs/ECHO45-S6-B22-DESIGN.md'
PDF=Path('/home/user/Descargas/B22-investigacion-20261006.pdf')


def closure():
    pending={'seed.s6b22','seed.s6b22_review','echo_arc.agent','echo_arc.runner',
             'echo_arc.temporal_bench','echo_arc.temporal_agent','seed.arc3gym'}
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
    if any(p.startswith(('docs/','tests/')) or p in ('seed/s6b20_capacity.py','seed/s6probe1.py','seed/s6probe2.py') for p in files):
        raise RuntimeError('research artifacts entered runtime closure')
    return sorted(files)


def b21_receipts():
    old=REPO/'lab/seed/s6b21-20261006'
    profile=REPO/'lab/kaggle/s6b21-20261006/input/manifest.json'
    m=r.read(profile)
    for f,h in m['sources'].items():
        if r.file_sha(REPO/f)!=h:raise RuntimeError('B21 frozen source changed: '+f)
    for f,h in m['inputs'].items():
        if r.file_sha(profile.parent/f)!=h:raise RuntimeError('B21 input changed: '+f)
    micro=r.read(old/'micro.json');audit=r.read(old/'micro-audit.json');arithmetic=r.read(old/'arithmetic-review.json')
    if not (r.read(old/'closed.json')['valid'] and audit['valid'] and arithmetic['valid']):
        raise RuntimeError('B21 not validly closed')
    if audit['micro_sha256']!=r.sha(micro) or arithmetic['profile_sha256']!=r.sha(m):raise RuntimeError('B21 audit linkage differs')
    step=r.read(old/'steps/random-821117/001.json');event=step['event']
    selected=micro['winners']['random-821117']
    if selected['slot']!=2 or event['candidate']!=selected['policy'] or r.sha(event['candidate'])!=event['policy_sha256']:
        raise RuntimeError('exact winner identity mismatch')
    fixture=r.read(profile.parent/'baseline.json')
    if r.sha(fixture['policy'])!=event['base_sha256']:raise RuntimeError('winner base mismatch')
    rebuilt=r.engine.strategy(program=r.engine.patch.append(fixture['policy']['program'],event['proposal']))
    if rebuilt!=event['candidate']:raise RuntimeError('winner composition mismatch')
    reference={}
    for label,name in (('baseline','baseline.json'),('candidate','candidate/001.json')):
        primary=r.read(old/'micro-random-821117/measurements'/name)
        other=r.read(old/'audit-random-821117/measurements'/name)
        replay=r.read((old/'micro-random-821117/measurements'/name).with_suffix('')/'replay.json')
        if primary!=other or primary!=replay:raise RuntimeError('B21 winning trajectories differ')
        reference[label]=primary
    if r.difference(reference['baseline'],reference['candidate'])!=event['A'] or not r.passes(event['A']):
        raise RuntimeError('B21 winning verdict differs')
    receipt=dict(valid=True,profile_sha256=r.sha(m),step_sha256=r.file_sha(old/'steps/random-821117/001.json'),
                 micro_sha256=r.sha(micro),audit_sha256=r.file_sha(old/'micro-audit.json'),
                 arithmetic_sha256=r.file_sha(old/'arithmetic-review.json'),frozen_sources=len(m['sources']))
    return fixture,dict(policy=event['candidate'],policy_sha256=event['policy_sha256'],origin=receipt),reference,receipt


def partition_review():
    """Review identities from historical metadata, never protected outcomes."""
    targets={(x[0],x[1]) for x in r.V_NEW+r.S_NEW}
    if len(targets)!=160 or targets&{(x[0],x[1]) for x in r.DEVELOPMENT}:raise RuntimeError('partitions overlap')
    command=['rg','--files','lab/seed','lab/kaggle','-g','*manifest*.json','-g','profile.json','-g','*freeze*.json',
             '-g','*partition*.json','-g','*opened*.json','-g','!**/runtime/**','-g','!**/source-archive/**',
             '-g','!**/cache/**','-g','!**/collected/**']
    paths=subprocess.run(command,cwd=REPO,text=True,capture_output=True,check=True).stdout.splitlines()
    def visit(obj):
        if isinstance(obj,list):
            if len(obj)==4 and all(type(v) is int for v in obj) and tuple(obj[:2]) in targets:return [obj]
            return [x for child in obj for x in visit(child)]
        if isinstance(obj,dict):
            if obj.get('version') in (2,3) and type(obj.get('seed')) is int and (obj['version'],obj['seed']) in targets:
                return [[obj['version'],obj['seed']]]
            return [x for child in obj.values() for x in visit(child)]
        return []
    inventory={};overlap=[]
    for name in sorted(paths):
        if 's6b22-' in name:continue
        path=REPO/name;inventory[name]=r.file_sha(path)
        hits=visit(r.read(path))
        if hits:overlap.append(dict(path=name,cases=hits))
    return dict(valid=not overlap,validation=r.V_NEW,selector=r.S_NEW,inventory=inventory,overlap=overlap,
                identity='world version + seed, independent of replicate or action budget',
                scope='registered historical metadata; not a proof about unregistered external executions',
                source_range_review='65000-65039 and 66000-66039 have no earlier declared S6 partition',exam_opened=False)


def prepare():
    log=r.ROOT/'tests-final.log'
    if '\nOK\n' not in log.read_text():raise RuntimeError('passing tests required')
    prior_profiles=prior.prior_sources()
    fixture,winner,reference,gate=b21_receipts()
    exposure=partition_review()
    if not exposure['valid']:raise RuntimeError('protected cohort previously registered')
    r.INPUT.mkdir(parents=True,exist_ok=True)
    for name,value in (('baseline.json',fixture),('winner.json',winner),('b21-reference.json',reference),
                       ('b21-closure.json',gate),('exposure-registry.json',exposure)):
        r.immutable(r.INPUT/name,value)
    files=closure()
    from importlib.metadata import version
    manifest=dict(configuration=r.config(),stage='B22-VS-pilot',sources={f:r.file_sha(REPO/f) for f in files},
                  inputs={p.name:r.file_sha(p) for p in r.INPUT.glob('*.json') if p.name!='manifest.json'},
                  python='.'.join(map(str,sys.version_info[:3])),numpy=version('numpy'),arcengine=version('arcengine'),
                  contract_sha256=r.file_sha(REPO/CONTRACT),research_pdf_sha256=r.file_sha(PDF),
                  tests_sha256=r.file_sha(log),prior_profiles=prior_profiles,
                  test_sources={f:r.file_sha(REPO/f) for f in ('tests/test_s6b22.py','tests/test_s6b21.py','tests/test_s6b20.py','tests/test_s6b18.py')},
                  engineering_sources={f:r.file_sha(REPO/f) for f in ('seed/s6b22_build.py','seed/s6b22_report.py')})
    if (manifest['python'],manifest['numpy'],manifest['arcengine'])!=('3.12.13','2.3.2','0.9.3'):
        raise RuntimeError('use the frozen B21 Python environment')
    r.immutable(r.INPUT/'manifest.json',manifest)
    for f,h in manifest['sources'].items():
        dest=RUNTIME/f;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists() and r.file_sha(dest)!=h:raise RuntimeError('staged source changed')
        if not dest.exists():shutil.copyfile(REPO/f,dest)
    r.status('PREPARED',games_started=False,profile_sha256=r.sha(manifest))
    return manifest


def launch():
    manifest=r.integrity()
    for f,h in manifest['sources'].items():
        if r.file_sha(RUNTIME/f)!=h:raise RuntimeError('staged source changed: '+f)
    for f,h in {**manifest['test_sources'],**manifest['engineering_sources']}.items():
        if r.file_sha(REPO/f)!=h:raise RuntimeError('frozen engineering source changed: '+f)
    if r.file_sha(REPO/CONTRACT)!=manifest['contract_sha256']:raise RuntimeError('contract changed')
    if r.file_sha(r.ROOT/'tests-final.log')!=manifest['tests_sha256']:raise RuntimeError('test receipt changed')
    if prior.prior_sources()!=manifest['prior_profiles']:raise RuntimeError('prior source profile changed')
    b21_receipts()
    env=dict(os.environ,ECHO_B22_ROOT=str(r.ROOT),ECHO_B22_INPUT=str(r.INPUT),
             PYTHONPATH=str(RUNTIME),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    subprocess.run([sys.executable,'-u','-m','seed.s6b22','follow'],cwd=RUNTIME,env=env,check=True)


if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['launch']:launch()
    else:raise SystemExit('use prepare or launch')
