"""Private B23 packaging, source custody, model readiness and frozen launch."""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from seed import s6b23 as r
from seed import s6b23_model as model

CONTRACT='docs/ECHO45-S6-B23-MICRO-DESIGN.md'
BEHAVIOR=('version','seed','rep','budget','actions','frames','automatic_reset_indices',
          'levels_completed','score','actions_per_level','baseline')


def closure():
    pending={'seed.s6b23','seed.s6b23_review','echo_arc.agent','echo_arc.runner',
             'echo_arc.temporal_bench','echo_arc.temporal_agent','seed.arc3gym'}
    done=set();files=set()
    while pending:
        module=pending.pop()
        if module in done or module.endswith('_exam'):continue
        path=r.REPO/(module.replace('.','/')+'.py')
        if not path.is_file():path=r.REPO/module.replace('.','/')/'__init__.py'
        if not path.is_file():continue
        done.add(module);files.add(str(path.relative_to(r.REPO)))
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import):names=[x.name for x in node.names]
            elif isinstance(node,ast.ImportFrom):
                prefix=node.module or ''
                if node.level:prefix='.'.join(module.split('.')[:-node.level]+([prefix] if prefix else []))
                names=[prefix]+[prefix+'.'+x.name for x in node.names]
            else:continue
            pending.update(n for n in names if n.startswith(('seed.','echo_arc.')))
    files.update(['seed/__init__.py','echo_arc/__init__.py','lab/temporal/h1h3-exam-20260927/evaluate.py'])
    forbidden=('probe','forensics','_build','_report','_exam')
    unwanted=[f for f in files if any(word in Path(f).stem for word in forbidden)
              or f.startswith(('tests/','docs/')) or f=='seed/s6b20_capacity.py']
    if unwanted:
        raise RuntimeError('research/control content in runtime closure: '+str(unwanted))
    return sorted(files)


def prior_receipts():
    root=r.REPO/'lab/seed/s6b22-20261006'; manifest=r.read(root/'input/manifest.json')
    for group,base in (('sources',r.REPO),('inputs',root/'input')):
        for name,h in manifest[group].items():
            if r.file_sha(base/name)!=h:raise RuntimeError('B22 frozen bytes changed: '+name)
    audit=r.read(root/'arithmetic-review.json');closed=r.read(root/'closed.json')
    if not closed['valid'] or not audit['valid'] or audit['profile_sha256']!=r.sha(manifest):
        raise RuntimeError('B22 must be closed and audited')
    first=manifest['configuration']['cells'][0][0]
    micro=r.read(root/('s-'+first)/'measurements/baseline.json')
    broad=r.read(root/'v-broad/measurements/baseline.json')
    rows=micro['rows']+[broad['rows'][144],broad['rows'][154]]
    if [tuple(row[k] for k in ('version','seed','rep','budget')) for row in rows]!=r.A:
        raise RuntimeError('baseline cohort differs')
    fixture=dict(policy=r.read(root/'input/baseline.json')['policy'],
                 behavior=[{k:row[k] for k in BEHAVIOR} for row in rows],levels=61,
                 provenance=dict(b22_profile_sha256=r.sha(manifest),b22_audit_sha256=r.sha(audit),
                                 micro_sha256=r.sha(micro),broad_sha256=r.sha(broad),
                                 note='baseline observations only; no winning or rejected policy'))
    return fixture


def exposure_review():
    targets={(v,s) for v,s,_,_ in r.V_NEW}
    if len(targets)!=80 or targets&{(v,s) for v,s,_,_ in r.DEVELOPMENT}:raise RuntimeError('overlapping partitions')
    command=['rg','--files','lab/seed','lab/kaggle','-g','*manifest*.json','-g','profile.json','-g','*freeze*.json',
             '-g','*partition*.json','-g','*opened*.json','-g','!**/runtime/**','-g','!**/source-archive/**',
             '-g','!**/cache/**','-g','!**/collected/**']
    names=subprocess.run(command,cwd=r.REPO,capture_output=True,text=True,check=True).stdout.splitlines()
    def hits(obj):
        if isinstance(obj,list):
            if len(obj)==4 and all(type(x) is int for x in obj) and tuple(obj[:2]) in targets:return [obj]
            return [h for x in obj for h in hits(x)]
        if isinstance(obj,dict):
            found=[]
            if type(obj.get('version')) is int and type(obj.get('seed')) is int and (obj['version'],obj['seed']) in targets:
                found.append([obj['version'],obj['seed']])
            return found+[h for x in obj.values() for h in hits(x)]
        return []
    inventory={};overlap=[]
    for name in sorted(names):
        if 's6b23-' in name:continue
        p=r.REPO/name;inventory[name]=r.file_sha(p);found=hits(r.read(p))
        if found:overlap.append(dict(path=name,cases=found))
    return dict(valid=not overlap,cohort_sha256=r.sha(r.V_NEW),inventory=inventory,overlap=overlap,
                identity='world version + seed, regardless of budget',
                scope='registered historical metadata only; external unregistered exposure unknown')


def stage():
    if (r.INPUT/'manifest.json').exists():raise RuntimeError('already frozen; use readiness or launch')
    fixture=prior_receipts();exposure=exposure_review()
    if not exposure['valid']:raise RuntimeError('retention cohort previously registered')
    r.INPUT.mkdir(parents=True,exist_ok=True)
    r.atomic(r.INPUT/'baseline.json',fixture);r.atomic(r.INPUT/'exposure-registry.json',exposure)
    files=closure()
    intent=dict(configuration=r.config(),sources={f:r.file_sha(r.REPO/f) for f in files},
                inputs={p.name:r.file_sha(p) for p in r.INPUT.glob('*.json')},
                contract_sha256=r.file_sha(r.REPO/CONTRACT),games_started=False,models_ready=False)
    r.atomic(r.ROOT/'intent.json',intent)
    template={}
    for arm,size in [('N7',7),('N14',14)]:
        template[arm]=dict(family='Qwen2.5-Coder-Instruct',repo=f'Qwen/Qwen2.5-Coder-{size}B-Instruct-GGUF',
            revision='REQUIRED_HF_COMMIT',model=f'/models/qwen2.5-coder-{size}b-instruct-q4_k_m.gguf',
            model_sha256='REQUIRED_SHA256',cli='/usr/local/bin/llama-cli',cli_sha256='REQUIRED_SHA256',
            tokenizer='/usr/local/bin/llama-tokenize',tokenizer_sha256='REQUIRED_SHA256',gguf={},
            backend='cuda',gpu_layers=99,tensor_split='1,1',quantization='Q4_K_M')
    r.atomic(r.ROOT/'models.template.json',template)
    r.status('STAGED_WAITING_MODELS',games_started=False,models_ready=False)
    return intent


def registry(args):
    value={}
    for arm,size,path,revision in [('N7',7,args.n7,args.revision7),('N14',14,args.n14,args.revision14)]:
        value[arm]=dict(family='Qwen2.5-Coder-Instruct',repo=f'Qwen/Qwen2.5-Coder-{size}B-Instruct-GGUF',
            revision=revision,model=str(Path(path).resolve()),model_sha256=model.digest_file(Path(path)),
            cli=str(Path(args.cli).resolve()),cli_sha256=model.digest_file(Path(args.cli)),
            tokenizer=str(Path(args.tokenizer).resolve()),tokenizer_sha256=model.digest_file(Path(args.tokenizer)),
            quantization='Q4_K_M',backend=args.backend,gpu_layers=99 if args.backend=='cuda' else 0,
            tensor_split=args.tensor_split,gguf=model.gguf_info(path))
        value[arm]['prompt_protocol']=model.prompt_protocol(value[arm])
    model.verify_pair(value);r.atomic(Path(args.output),value)


def readiness(model_path=None):
    issues=[]
    try:prior_receipts()
    except (OSError,ValueError,KeyError,RuntimeError) as exc:issues.append(str(exc))
    try:
        from importlib.metadata import version
        actual=('.'.join(map(str,sys.version_info[:3])),version('numpy'),version('arcengine'))
        if actual!=('3.12.13','2.3.2','0.9.3'):issues.append('frozen Python/numpy/arcengine required: '+str(actual))
    except Exception as exc:issues.append('runtime: '+str(exc))
    if model_path is None:issues.append('7B/14B model registry not supplied')
    else:
        try:model.verify_pair(r.read(Path(model_path)))
        except (OSError,KeyError,ValueError,RuntimeError) as exc:issues.append('models: '+str(exc))
    receipt=dict(ready=not issues,issues=issues,games_started=False,model_calls=0,at=r.now())
    r.atomic(r.ROOT/'readiness.json',receipt);return receipt


def prepare(model_path,tests_log):
    if (r.INPUT/'manifest.json').exists():raise RuntimeError('already frozen')
    ready=readiness(model_path)
    if not ready['ready']:raise RuntimeError('; '.join(ready['issues']))
    log=Path(tests_log)
    if '\nOK\n' not in log.read_text():raise RuntimeError('passing instrument tests required')
    intent=r.read(r.ROOT/'intent.json')
    for f,h in intent['sources'].items():
        if r.file_sha(r.REPO/f)!=h:raise RuntimeError('staged source changed; stage again before freeze')
    if intent['contract_sha256']!=r.file_sha(r.REPO/CONTRACT):raise RuntimeError('contract changed')
    r.immutable(r.INPUT/'models.json',r.read(Path(model_path)))
    from importlib.metadata import version
    manifest=dict(configuration=r.config(),sources=intent['sources'],
        inputs={p.name:r.file_sha(p) for p in r.INPUT.glob('*.json') if p.name!='manifest.json'},
        python='.'.join(map(str,sys.version_info[:3])),numpy=version('numpy'),arcengine=version('arcengine'),
        tests_sha256=r.file_sha(log),test_sources={'tests/test_s6b23.py':r.file_sha(r.REPO/'tests/test_s6b23.py')},
        contract_sha256=intent['contract_sha256'])
    r.immutable(r.INPUT/'manifest.json',manifest)
    for f in manifest['sources']:
        dest=r.ROOT/'runtime'/f;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r.REPO/f,dest)
    r.status('PREPARED',games_started=False,profile_sha256=r.sha(manifest));return manifest


def package(destination):
    """Private portable source/data archive, no model weights or research solutions."""
    intent=r.read(r.ROOT/'intent.json')
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f,h in intent['sources'].items():
            if r.file_sha(r.REPO/f)!=h:raise RuntimeError('source changed after stage')
            z.write(r.REPO/f,f)
        # Bootstrap is separate engineering code, never input to the researcher.
        z.write(r.REPO/'seed/s6b23_build.py','seed/s6b23_build.py')
        z.write(r.REPO/'seed/s6b23_cloud.py','seed/s6b23_cloud.py')
        z.write(r.REPO/'seed/s6b23_report.py','seed/s6b23_report.py')
        z.write(r.REPO/'tests/test_s6b23.py','tests/test_s6b23.py')
        z.writestr('tests/__init__.py','')
        z.write(r.REPO/CONTRACT,CONTRACT)
        z.write(r.REPO/'docs/ECHO45-S6-B23-IMPLEMENTATION.md','docs/ECHO45-S6-B23-IMPLEMENTATION.md')
        z.writestr('requirements-b23.txt','numpy==2.3.2\narcengine==0.9.3\n')
        for name in ('baseline.json','exposure-registry.json'):
            z.write(r.INPUT/name,'b23-input/'+name)
        z.write(r.ROOT/'intent.json','b23-input/intent.json')
        z.write(r.ROOT/'models.template.json','b23-input/models.template.json')
    return dict(path=str(destination),sha256=r.file_sha(Path(destination)),private=True,published=False)


def launch():
    m=r.integrity();runtime=r.ROOT/'runtime'
    for f,h in m['sources'].items():
        if r.file_sha(runtime/f)!=h:raise RuntimeError('staged runtime changed')
    env=dict(os.environ,ECHO_B23_ROOT=str(r.ROOT),ECHO_B23_INPUT=str(r.INPUT),PYTHONPATH=str(runtime),
             PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    subprocess.run([sys.executable,'-u','-m','seed.s6b23','follow'],cwd=runtime,env=env,check=True)


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('stage');sub.add_parser('launch')
    q=sub.add_parser('readiness');q.add_argument('--models')
    q=sub.add_parser('prepare');q.add_argument('--models',required=True);q.add_argument('--tests-log',required=True)
    q=sub.add_parser('package');q.add_argument('destination')
    q=sub.add_parser('models')
    for name in ('n7','n14','revision7','revision14','cli','tokenizer','output'):q.add_argument('--'+name,required=True)
    q.add_argument('--backend',choices=['cpu','cuda'],default='cuda');q.add_argument('--tensor-split',default='1,1')
    args=p.parse_args()
    if args.command=='stage':stage()
    elif args.command=='readiness':print(r.canonical(readiness(args.models)))
    elif args.command=='models':registry(args)
    elif args.command=='prepare':prepare(args.models,args.tests_log)
    elif args.command=='package':print(r.canonical(package(Path(args.destination))))
    elif args.command=='launch':launch()


if __name__=='__main__':main()
