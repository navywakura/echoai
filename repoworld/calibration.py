"""Four-issue LOCAL infrastructure calibration; no LLM and no official oracle.

Uses real frozen repository trees with synthetic, explicitly labelled probes.
Passing this program does not resolve an issue or qualify a dependency image.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import resource
import time
from ..pcworld.memory import EpisodeMemory
from ..pcworld.receipts import canonical, ReceiptStore
from ..pcworld.runtime import load_runtime, repository_runtime
from ..pcworld.runner import environment_identity
from .dataset import read_fixed_dataset, select_public_tasks, sha256_file
from .environment import prepare_repo, environment_ref, execute_repo, repo_store
from .workspace import Workspace
from .tools import dispatch_tool

PROBES=('isolation','timeout','cpu','memory','pids','disk','output')


def check_probe(name,value):
    isolation=value.get('isolation',{})
    if (not isolation.get('job_empty') or isolation.get('host_usr_mounted') is not False
        or isolation.get('network_disabled') is not True or value.get('task_success') is not False
        or value.get('claim_status')!='unknown'):
        return False
    if name=='isolation': return value['exit_code']==0 and value['stdout'].strip()=='calibration-ok'
    if name=='timeout': return value['status']=='TIMEOUT'
    if name=='cpu': return value['status']=='CPU_LIMIT'
    if name=='memory': return value['status']=='MEMORY_LIMIT'
    if name=='pids': return value['status']=='TIMEOUT' and 'pids-bounded' in value['stdout']
    if name=='disk': return value['exit_code']==0 and 'disk-bounded' in value['stdout']
    if name=='output': return value['status']=='OUTPUT_LIMIT' and value['resources']['output_bytes']<=4096
    return False


def calibration_verdict(rows,expected_ids):
    actual=[r['instance_id'] for r in rows]
    if len(set(actual))!=len(actual) or set(actual)!=set(expected_ids): raise ValueError('calibration roster mismatch')
    return dict(schema='repoworld.local-calibration.v1',valid=all(r.get('valid') is True for r in rows),
                completed=len(rows),passed=sum(r.get('valid') is True for r in rows),
                llm_calls=0,gpu_hours=0,swe_resolved=None,official_evaluation=False,
                scope='infrastructure probes on real base trees; not issue solving or dependency validation',issues=rows)


def source_manifest():
    root=Path(__file__).resolve().parents[1]
    files=list((root/'repoworld').glob('*.py'))
    files += list((root/'pcworld').glob('*.py'))+list((root/'core').glob('*.py'))
    files += list((root/'tests').glob('test_repoworld_*.py'))
    files += [root/'ECHO-5.1/scripts/run_repoworld.py',root/'ECHO-5.1/scripts/inference_relay.py',root/'scripts/plot_swebench_results.py']
    files += [root/'ECHO-5.1/docs/swebench'/name for name in ('SWE-TOOLS.schema.json','SWE-RUN-LOCK.schema.json','SWE-RESULTS.schema.json')]
    return {str(path.relative_to(root)):sha256_file(path) for path in sorted(files)}


def _emit(session,memory,kind,body):
    receipt=session.receipts.append(dict(kind=kind,**body))
    event=memory.record(receipt,kind=kind)
    with (session.directory/'thought.jsonl').open('ab') as f: f.write(canonical(event)+b'\n')
    print(json.dumps(dict(instance_id=session.base.task.instance_id,kind=kind,
                         operation=body.get('operation'),valid=body.get('valid'))),flush=True)
    return receipt


def _probes(sentinel):
    return {
      'isolation': (f"""from pathlib import Path
import socket
assert Path.cwd()==Path('/work')
assert not Path({str(sentinel)!r}).exists()
assert not Path('/usr/bin/git').exists()
assert not Path('/candidate/.git').exists()
Path('transient-calibration.txt').write_text('scratch only')
for path in ('/candidate/forbidden','/repo-base/forbidden'):
 try: Path(path).write_text('bad')
 except OSError: pass
 else: raise AssertionError('mutable input')
s=socket.socket();s.settimeout(.1)
try: s.connect(('127.0.0.1',8771))
except OSError: pass
else: raise AssertionError('host network reached')
print('calibration-ok')
""",{}),
      'timeout': ('import os,time\nif os.fork()==0: time.sleep(20)\ntime.sleep(20)',{'wall_ms':1200}),
      'cpu': ('while True: pass',{'cpu_ms':500,'wall_ms':5000}),
      'memory': ('data=bytearray(384*1024*1024)',{'memory_bytes':128*1024*1024}),
      'pids': ("import os,time\nfor _ in range(64):\n try:\n  if os.fork()==0: time.sleep(20);os._exit(0)\n except OSError: print('pids-bounded',flush=True);break\ntime.sleep(20)",{'pids':12,'wall_ms':1500}),
      'disk': ("from pathlib import Path\ntry:\n with Path('.out/fill').open('wb') as f:\n  for _ in range(1025): f.write(b'x'*1024*1024)\nexcept OSError as e:\n assert e.errno==28;print('disk-bounded')\nelse: raise AssertionError('unbounded disk')",{}),
      'output': ("while True: print('x'*1024,flush=True)",{'output_bytes':4096})}


def calibrate_issue(task,source,environment,directory,sentinel):
    started=time.monotonic();base=prepare_repo(task,source,environment,task.base_commit,store_dir=directory/'base')
    entries=base.snapshot.manifest['entries'];tree_bytes=sum(e.get('size',0) for e in entries.values())
    files=sum(e['type']=='file' for e in entries.values())
    session=Workspace(directory/'session',base);memory=EpisodeMemory(task.instance_id,'LOCAL-INFRA')
    _emit(session,memory,'observation',dict(operation='prepared_commit',base_commit=task.base_commit,
               snapshot=base.snapshot.id,tree_bytes=tree_bytes,files=files,oracle_visible=False))
    scratch=max(64*1024*1024,((tree_bytes+files*4096+8*1024*1024+1048575)//1048576)*1048576)
    if scratch>1024**3: raise ValueError('scratch profile insufficient')
    results={}
    for name,(code,caps) in _probes(sentinel).items():
        r=execute_repo(base,base.snapshot,('/usr/bin/python3','-I','-c',code),
                       limits={'disk_bytes':scratch,**caps},check_artifacts=())
        valid=check_probe(name,r)
        receipt=_emit(session,memory,'observation',dict(operation=name,valid=valid,execution=r))
        results[name]=dict(valid=valid,receipt=receipt['sha256'],status=r['status'],resources=r['resources'])
    # Exercise the public tools and a neutral text edit, NOT a purported issue fix.
    targets=[p for p,e in entries.items() if e['type']=='file' and p.endswith('.py')
             and e['size']<200000 and not any(x in p.split('/') for x in ('tests','test','testing'))
             and not Path(p).name.startswith('test_') and Path(p).name!='conftest.py']
    target=sorted(targets)[0]
    view=dispatch_tool(dict(tool='file_view',snapshot_id=session.current.id,path=target,start_line=1,line_count=100,cursor=None),session=session)
    search=dispatch_tool(dict(tool='repo_search',snapshot_id=session.current.id,pattern='def ',path='.',literal=True,cursor=None),session=session)
    original=session.store.read(session.current,target).decode('utf-8')
    modified=original+('' if original.endswith('\n') else '\n')+'# RepoWorld infrastructure calibration only.\n'
    diff=''.join(difflib.unified_diff(original.splitlines(True),modified.splitlines(True),fromfile='a/'+target,tofile='b/'+target))
    old=session.current.id
    candidate=session.stage(diff,old)
    stage_kept_head=session.current.id==old
    # Known mechanical predicate, independently checked outside candidate process.
    expected=hashlib.sha256(modified.encode()).hexdigest()
    code=f"import hashlib;from pathlib import Path;print(hashlib.sha256(Path({target!r}).read_bytes()).hexdigest())"
    observation=execute_repo(base,candidate.snapshot,('/usr/bin/python3','-I','-c',code),limits={'disk_bytes':scratch},check_artifacts=())
    supported=observation['exit_code']==0 and observation['stdout'].strip()==expected and observation['isolation']['job_empty']
    rec=session.receipts.append(dict(event='repoworld.public-property',candidate=candidate.snapshot.id,
                     checker_id='exact-file-hash-calibration-v1',scope='public',
                     property_status='supported' if supported else 'contradicted',observation=observation,
                     expected_sha256=expected,task_solved=False))
    if supported: session.retain(candidate,expected_head=old,public_receipt_ids=(rec['sha256'],))
    export=session.final_diff()
    repo_store(base.snapshot.root.parent.parent).validate(base.snapshot)
    atomic=stage_kept_head and supported and session.current.id==candidate.snapshot.id and export==diff
    _emit(session,memory,'observation',dict(operation='tools_and_transaction',valid=atomic,
               view_receipt=view['receipt_id'],search_receipt=search['receipt_id'],patch_sha256=hashlib.sha256(export.encode()).hexdigest()))
    audit=session.receipts.audit()
    valid=all(r['valid'] for r in results.values()) and atomic and audit['ok']
    return dict(instance_id=task.instance_id,base_commit=task.base_commit,snapshot=base.snapshot.id,
                valid=valid,tree_bytes=tree_bytes,files=files,scratch_bytes=scratch,probes=results,
                tools_and_transaction=atomic,receipt_audit=audit,wall_seconds=time.monotonic()-started,
                destroyed=memory.cam.destroyed)


def run_local(*,dataset,sample,runtime,sources,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False,mode=0o700)
    doc=Path(__file__).resolve().parents[1]/'ECHO-5.1/docs/SWE-CONTRACT.json'
    contract=json.loads(doc.read_bytes());sample_path=Path(sample)
    if sha256_file(sample_path)!=contract['dataset']['sample_sha256']: raise ValueError('registered sample changed')
    roster=json.loads(sample_path.read_bytes())['calibration']
    if len(roster)!=4: raise ValueError('four registered calibration issues required')
    tasks=select_public_tasks(read_fixed_dataset(Path(dataset),contract['dataset']['parquet_sha256']),roster)
    (output/'public-tasks.json').write_bytes(canonical([asdict(t) for t in tasks])+b'\n')
    image=repository_runtime(load_runtime(runtime),output/'runtime')
    env=environment_ref(image,scope='stdlib-calibration')
    sentinel=output/'host-sentinel';sentinel.write_text('CALIBRATION-HOST-ONLY-NOT-A-SECRET')
    before=source_manifest();rows=[]
    for task in tasks:
        try: row=calibrate_issue(task,Path(sources)/task.instance_id,env,output/task.instance_id,sentinel)
        except Exception as error:
            row=dict(instance_id=task.instance_id,valid=False,error_type=type(error).__name__,error=str(error))
            print(json.dumps(row),flush=True)
        rows.append(row)
        (output/'progress.json').write_bytes(canonical(dict(completed=len(rows),issues=rows))+b'\n')
    report=calibration_verdict(rows,[t.instance_id for t in tasks])
    if source_manifest()!=before: raise RuntimeError('sources changed during calibration')
    report.update(created_utc=datetime.now(timezone.utc).isoformat(),source_manifest=before,
                  sample_sha256=sha256_file(sample_path),dataset_sha256=contract['dataset']['parquet_sha256'],
                  environment=environment_identity(image),runtime_snapshot=image.id,
                  supervisor_maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  dependency_environments_validated=False,kaggle_tunnel_started=False)
    (output/'result.json').write_bytes(canonical(report)+b'\n')
    return report


def audit_local(directory):
    """Replay local probe predicates against authenticated observations.

    A local infrastructure audit, not the independent SWE evaluator in task 7.
    Missing authorities fail closed; this operation never invents signing keys.
    """
    directory=Path(directory)
    report=json.loads((directory/'result.json').read_bytes())
    docs=Path(__file__).resolve().parents[1]/'ECHO-5.1/docs'
    sample=docs/'swebench/SWE-SAMPLE.json'
    refs=json.loads(sample.read_bytes())['calibration']
    if report.get('schema')!='repoworld.local-calibration.v1' or report.get('source_manifest')!=source_manifest():
        raise ValueError('calibration sources/schema differ; audit from its frozen checkout')
    if report['sample_sha256']!=sha256_file(sample): raise ValueError('sample changed')
    expected={r['instance_id']:r for r in refs}
    rows=report['issues'];calibration_verdict(rows,expected)
    image=load_runtime(directory/'runtime')
    if image.id!=report['runtime_snapshot']: raise ValueError('runtime mismatch')
    total=0;findings=[]
    for row in rows:
        identifier=row['instance_id'];path=directory/identifier/'session'
        if not (path/'authority/authority.json').is_file() or not (path/'receipts/receipts.jsonl').is_file():
            raise ValueError('missing existing receipt custody')
        receipts=ReceiptStore(path/'receipts',path/'authority');audit=receipts.audit()
        if not audit['ok']: raise ValueError('receipt custody invalid')
        total+=audit['count'];records=receipts.records
        observations={}
        for rec in records:
            body=rec['body']
            if body.get('kind')=='observation' and body.get('operation') in PROBES:
                name=body['operation']
                if name in observations: raise ValueError('duplicate probe')
                observations[name]=rec
        if set(observations)!=set(PROBES): raise ValueError('missing probes')
        for name,rec in observations.items():
            value=check_probe(name,rec['body']['execution'])
            declared=row['probes'][name]
            if not value or not declared['valid'] or declared['receipt']!=rec['sha256'] or declared['resources']!=rec['body']['execution']['resources']:
                raise ValueError('probe report disagrees with witnessed execution')
        # Opening the workspace checks its retained head against its receipt and
        # validates the immutable candidate; no candidate code is executed here.
        session=Workspace(path)
        if session.base.task.base_commit!=expected[identifier]['base_commit'] or session.base.snapshot.id!=row['snapshot']:
            raise ValueError('base identity mismatch')
        current=session.current
        changed=[e['sha256'] for p,e in current.manifest['entries'].items() if e['type']=='file'
                 and e!=session.base.snapshot.manifest['entries'].get(p)]
        properties=[r['body'] for r in records if r['body'].get('event')=='repoworld.public-property']
        if len(properties)!=1 or len(changed)!=1: raise ValueError('unexpected calibration edit/property')
        prop=properties[0];observation=prop['observation']
        if (prop['candidate']!=current.id or prop['expected_sha256']!=changed[0] or
            prop['property_status']!='supported' or observation['exit_code']!=0 or
            observation['stdout'].strip()!=changed[0] or not observation['isolation']['job_empty']):
            raise ValueError('file-hash property lacks observed support')
        exported=session.final_diff()
        transactions=[r['body'] for r in records if r['body'].get('operation')=='tools_and_transaction']
        if len(transactions)!=1 or not transactions[0]['valid'] or transactions[0]['patch_sha256']!=hashlib.sha256(exported.encode()).hexdigest():
            raise ValueError('patch roundtrip mismatch')
        memory=EpisodeMemory(identifier,'LOCAL-INFRA')
        replay=[memory.record(r,kind=r['body']['kind']) for r in records if r['body'].get('kind') in ('observation','failure','property','proposal','decision')]
        actual=[json.loads(line) for line in (path/'thought.jsonl').read_text().splitlines()]
        if actual!=replay or memory.cam.destroyed!=0 or row['destroyed']!=0: raise ValueError('thought/CAM replay mismatch')
        if not row['valid']: raise ValueError('reported incomplete episode')
        findings.append(dict(instance_id=identifier,valid=True,receipts=audit['count'],probes=len(PROBES)))
    return dict(schema='repoworld.local-audit.v1',valid=True,scope='local infrastructure only',
                receipts=total,issues=findings,source_manifest=source_manifest(),
                result_sha256=sha256_file(directory/'result.json'),official_evaluation=False)
