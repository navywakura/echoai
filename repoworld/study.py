"""Gated, resumable study orchestration. Preparation never starts a GPU."""
from dataclasses import asdict
import fcntl
import hashlib
import json
from pathlib import Path
import time
from ..pcworld.receipts import ReceiptStore, canonical, _atomic_write
from .calibration import source_manifest
from .dataset import read_fixed_dataset, public_task, sample_roster, validate_launch, sha256_file
from .dependencies import load_image
from .environment import environment_ref,prepare_repo
from .checks import catalog_for,collect_public_baseline,validate_plan
from .evaluator import existing_receipts,freeze_set
from .protocol import run_episode
from .provider import RepoProvider,InferencePending,provider_identity,validate_model_config
from .workspace import Workspace
from .accounting import LIMITS


def schedule_for(contract,sample):
    rows=[]
    def add(phase,item,arm,seed,**extra):
        data=dict(phase=phase,instance_id=item['instance_id'],repo=item['repo'],arm=arm,seed=seed,**extra)
        data['cell_id']=hashlib.sha256(canonical(data)).hexdigest()[:32];rows.append(data)
    for seed in contract['model']['seeds']:
        for phase in ('calibration','primary'):
            for item in sample[phase]:
                # Balanced cyclic arm order is fixed before outcomes are known.
                arms=contract['phases'][phase]['arms'];shift=int(hashlib.sha256(item['instance_id'].encode()).hexdigest(),16)%len(arms)
                for arm in arms[shift:]+arms[:shift]:add(phase,item,arm,seed)
        for item in sample['primary']:add('guard_ablation',item,'E_no_guard',seed)
        for chain in sample['memory_chains']:
            add('memory_donor',chain['donor'],'E',seed,chain_id=chain['chain_id'])
            for position,item in enumerate(chain['targets'],1):
                for condition in ('empty','shared'):add('memory',item,'E',seed,chain_id=chain['chain_id'],position=position,condition=condition)
    return rows


def write_gate(directory,report,*,source_before=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    store=ReceiptStore(directory/'receipts',directory/'authority')
    current=source_manifest()
    value={**report,'source_manifest':current}
    if source_before is not None:
        value['source_unchanged']=source_before==current
        value['valid']=value.get('valid') is True and value['source_unchanged']
    r=store.append(dict(event='repoworld.gate',report=value))
    _atomic_write(directory/'report.json',canonical(dict(report=value,receipt_id=r['sha256'])))
    return value


def require_gate(directory,kind):
    directory=Path(directory);store=existing_receipts(directory)
    row=json.loads((directory/'report.json').read_bytes());report=row['report']
    if not any(r['sha256']==row['receipt_id'] and r['body']==dict(event='repoworld.gate',report=report) for r in store.records):raise ValueError('gate report authentication failed')
    if report['kind']!=kind or report.get('valid') is not True:raise ValueError(kind+' has not passed')
    if report['source_manifest']!=source_manifest():raise ValueError('gate sources changed; repeat under frozen sources')
    return report


def load_registry(path,contract,sample_path):
    registry=json.loads(Path(path).read_bytes())
    if set(registry)!={'schema','dataset','entries'} or registry['schema'] not in ('repoworld.environment-registry.v1','repoworld.environment-registry.v2'):raise ValueError('environment registry schema')
    rows=read_fixed_dataset(Path(registry['dataset']),expected_sha256=contract['dataset']['parquet_sha256'])
    tasks={r['instance_id']:public_task(r) for r in rows}
    registered={r['instance_id']:r for r in sample_roster(json.loads(Path(sample_path).read_bytes()))}
    entries={}
    for row in registry['entries']:
        fields={'instance_id','source','runtime','check_plan'}
        if registry['schema']=='repoworld.environment-registry.v2' and 'supplement' in row:
            fields.add('supplement');validate_supplement_descriptor(row['supplement'])
        if set(row)!=fields:raise ValueError('registry entry fields')
        key=row['instance_id']
        if key not in registered or key in entries or tasks[key].base_commit!=registered[key]['base_commit']:raise ValueError('registry identity mismatch')
        if row['check_plan']['repo']!=tasks[key].repo:raise ValueError('check plan repo mismatch')
        validate_plan(row['check_plan']);entries[key]=row
    return tasks,entries,registered


def validate_supplement_descriptor(value):
    from ..pcworld.snapshots import _hash
    if not isinstance(value,dict) or set(value)!={'directory','manifest','manifest_sha256'}:
        raise ValueError('supplement descriptor fields')
    for key in ('directory','manifest'):
        if type(value[key]) is not str or not value[key] or '\0' in value[key]:
            raise ValueError('supplement descriptor path')
    _hash(value['manifest_sha256'])


def prepare_entry(task,entry,output):
    manifest=None
    if 'supplement' in entry:
        descriptor=entry['supplement'];validate_supplement_descriptor(descriptor)
        path=Path(descriptor['manifest'])
        if path.stat().st_size>4*1024*1024:raise ValueError('supplement manifest too large')
        manifest=json.loads(path.read_bytes())
        if hashlib.sha256(canonical(manifest)).hexdigest()!=descriptor['manifest_sha256']:
            raise ValueError('supplement manifest authorization hash mismatch')
    environment=environment_ref(load_image(entry['runtime']),scope='public-dependencies')
    base=prepare_repo(task,Path(entry['source']),environment,task.base_commit,store_dir=Path(output)/'base')
    if manifest is not None:
        from .supplements import apply_supplement
        base=apply_supplement(base,descriptor['directory'],manifest,descriptor['manifest_sha256'])
    return base


def preflight(registry,contract,sample_path,output):
    sources=source_manifest()
    output=Path(output);output.mkdir(parents=True,exist_ok=True,mode=0o700)
    tasks,entries,registered=load_registry(registry,contract,sample_path);results=[]
    for identifier in registered:
        row=dict(instance_id=identifier,repo=tasks[identifier].repo,valid=False)
        if identifier not in entries:row['reason']='missing pinned environment/check plan'
        else:
            try:
                target=output/'instances'/identifier;base=prepare_entry(tasks[identifier],entries[identifier],target)
                receipts=ReceiptStore(target/'receipts',target/'authority')
                report=collect_public_baseline(base,entries[identifier]['check_plan'],receipts=receipts)
                row.update(valid=report.valid,reason=report.summary,baseline=asdict(report),
                    online_rootfs_sha256=base.environment.rootfs_sha256,online_tree_sha256=base.snapshot.id,
                    public_checks_sha256=report.check_plan_sha256,base_commit=base.task.base_commit)
            except (ValueError,RuntimeError,OSError,KeyError) as exc:row['reason']=str(exc)
        results.append(row)
        _atomic_write(output/'progress.json',canonical(results))
        print(json.dumps(dict(preflight=identifier,valid=row['valid'],reason=row['reason'][-220:])),flush=True)
    repos={r['repo'] for r in results if r['valid']}
    return write_gate(output,dict(kind='offline-preflight',valid=bool(results) and all(r['valid'] for r in results),
        gpu_hours=0,llm_calls=0,results=results,passed=sum(r['valid'] for r in results),registered=len(results),
        repositories_passed=len(repos),repositories_required=len({r['repo'] for r in results}),
        registry_sha256=sha256_file(registry),sample_sha256=sha256_file(sample_path),
        official_images_verified=False),source_before=sources)


class ScriptedProvider:
    """Finite local fixture; never described as model performance."""
    is_llm=False
    def __init__(self,actions):self.actions=list(actions);self.index=0
    def prepare(self,messages,request_id,deadline):
        text=json.dumps(messages,ensure_ascii=False)
        return text,list(range(max(1,len(text.encode())//4)))
    def complete(self,prompt,*,schema,max_tokens,request_id,deadline,sample_seed=None):
        if self.index>=len(self.actions):raise ValueError('mock fixture exhausted')
        value=self.actions[self.index];self.index+=1;text=json.dumps(value)
        return dict(content=text,tokens_evaluated=max(1,len(prompt.encode())//4),tokens_predicted=min(max_tokens,max(1,len(text)//4)))


def smoke(registry,contract,sample_path,*,instance_id,actions,output):
    sources=source_manifest()
    tasks,entries,_=load_registry(registry,contract,sample_path)
    calibration={r['instance_id'] for r in json.loads(Path(sample_path).read_bytes())['calibration']}
    if instance_id not in calibration:raise ValueError('smoke restricted to reserved calibration issues')
    output=Path(output);base=prepare_entry(tasks[instance_id],entries[instance_id],output/'prepared')
    provider=ScriptedProvider(actions)
    result=run_episode(base,'E',73,provider=provider,output=output/'episode',check_plan=entries[instance_id]['check_plan'])
    replay=run_episode(base,'E',73,provider=provider,output=output/'episode',check_plan=entries[instance_id]['check_plan'])
    store=existing_receipts(output/'episode/main')
    decisions=[r['body'] for r in store.records if r['body'].get('event')=='repoworld.public-decision']
    valid=result==replay and bool(result['model_patch']) and any(r['status']=='PUBLIC_REGRESSION' and not r['retain'] for r in decisions) and any(r['status']=='PUBLIC_CHECKS_PASSED' and r['retain'] for r in decisions)
    return write_gate(output,dict(kind='mock-smoke',valid=valid,instance_id=instance_id,gpu_hours=0,is_llm=False,
        replay_identical=result==replay,rollback_observed=any(not r['retain'] for r in decisions),
        diff_sha256=result['diff_sha256'],budget=result['budget'],official_evaluation=False),source_before=sources)


def require_launch(contract,sample_path,lock,*,contract_sha256=None):
    return validate_launch(contract,sample_path,lock,contract_sha256=contract_sha256)


def bind_study(store,identity):
    rows=[r['body'] for r in store.records if r['body'].get('event')=='repoworld.study-start']
    expected=dict(event='repoworld.study-start',identity=identity)
    if rows:
        if rows!=[expected]:raise ValueError('output is bound to another study lock/configuration')
    elif store.records:raise ValueError('existing study lacks an authenticated launch identity')
    else:store.append(expected)


def study_identity(sealed_dir,registry_sha256,model_config_sha256):
    sealed_dir=Path(sealed_dir)
    return dict(lock_sha256=sha256_file(sealed_dir/'SWE-RUN-LOCK.json'),
        contract_sha256=sha256_file(sealed_dir/'SWE-CONTRACT.json'),
        schedule_sha256=sha256_file(sealed_dir/'schedule.json'),registry_sha256=registry_sha256,
        model_config_sha256=model_config_sha256)


def record_not_started(store,cell,reason):
    existing=[r['body'] for r in store.records if r['body'].get('event')=='repoworld.cell-not-started' and r['body']['cell_id']==cell['cell_id']]
    if existing:return existing[0]['result']
    if any(r['body'].get('cell_id')==cell['cell_id'] and r['body'].get('event') in ('repoworld.cell-start','repoworld.cell-completed') for r in store.records):
        raise ValueError('an attempted episode cannot be called not_started')
    result=dict(instance_id=cell['instance_id'],arm=cell['arm'],seed=cell['seed'],status='not_started',reason=reason,
        model_patch='',diff_sha256=hashlib.sha256(b'').hexdigest(),wall_seconds=0,is_llm=False,task_success=False,
        budget={'limits':dict(LIMITS),'used':dict.fromkeys(LIMITS,0),'pending':0})
    store.append(dict(event='repoworld.cell-not-started',cell_id=cell['cell_id'],result=result,
        submission_sha256=hashlib.sha256(canonical(result)).hexdigest()))
    return result


def validate_seal(directory,sample_path):
    directory=Path(directory);store=existing_receipts(directory)
    records=[r['body'] for r in store.records if r['body'].get('event')=='repoworld.study-seal']
    if len(records)!=1:raise ValueError('one authenticated study seal required')
    seal=records[0]
    names={'SWE-CONTRACT.json','SWE-RUN-LOCK.json','schedule.json','source-manifest.json'}
    if set(seal['files'])!=names:raise ValueError('seal inventory mismatch')
    for name,digest in seal['files'].items():
        if sha256_file(directory/name)!=digest:raise ValueError('sealed bytes changed: '+name)
    kinds={'offline-preflight','official-controls','mock-smoke','remote-calibration','software-verification'}
    if set(seal['gates'])!=kinds:raise ValueError('missing authenticated gates')
    for kind,ref in seal['gates'].items():
        if sha256_file(Path(ref['directory'])/'report.json')!=ref['sha256']:raise ValueError('gate changed after seal')
        require_gate(ref['directory'],kind)
    contract=json.loads((directory/'SWE-CONTRACT.json').read_bytes());lock=json.loads((directory/'SWE-RUN-LOCK.json').read_bytes())
    require_launch(contract,sample_path,lock,contract_sha256=sha256_file(directory/'SWE-CONTRACT.json'))
    schedule=json.loads((directory/'schedule.json').read_bytes())
    if schedule!=schedule_for(contract,json.loads(Path(sample_path).read_bytes())):raise ValueError('schedule differs from registered full matrix')
    if hashlib.sha256(canonical(schedule)).hexdigest()!=lock['schedule_sha256']:raise ValueError('schedule digest mismatch')
    if hashlib.sha256(canonical(source_manifest())).hexdigest()!=lock['code_manifest_sha256']:raise ValueError('sealed source bytes changed')
    return seal


def validate_curator_binding(row,control):
    for field in ('official_image_digest','official_eval_script_sha256','sealed_tests_sha256','empty_patch_resolved','gold_patch_resolved'):
        if row[field]!=control[field]:raise ValueError('lock differs from curator controls: '+field)
    if row.get('service_manifest_sha256')!=control.get('service_manifest_sha256'):
        raise ValueError('lock differs from curator service profile')
    if row.get('reporting_profile_sha256')!=control.get('reporting_profile_sha256'):
        raise ValueError('lock differs from curator reporting profile')


def seal(contract_path,sample_path,materials,*,preflight_dir,curator_dir,smoke_dir,calibration_dir,verification_dir,output):
    # Evidence is bound to the CURRENT source bytes, not a boolean edited by an actor.
    offline=require_gate(preflight_dir,'offline-preflight');require_gate(smoke_dir,'mock-smoke')
    curator=require_gate(curator_dir,'official-controls')
    require_gate(calibration_dir,'remote-calibration');require_gate(verification_dir,'software-verification')
    contract=json.loads(Path(contract_path).read_bytes());contract={**contract,'status':'sealed','launch_enabled':True}
    contract_bytes=canonical(contract)+b'\n';contract_sha=hashlib.sha256(contract_bytes).hexdigest()
    sample=json.loads(Path(sample_path).read_bytes());schedule=schedule_for(contract,sample)
    lock=dict(materials,contract_sha256=contract_sha,sample_sha256=sha256_file(sample_path),
        code_manifest_sha256=hashlib.sha256(canonical(source_manifest())).hexdigest(),
        schedule_sha256=hashlib.sha256(canonical(schedule)).hexdigest(),
        budget_manifest_sha256=hashlib.sha256(canonical(contract['budget_per_issue_all_roles'])).hexdigest())
    require_launch(contract,sample_path,lock,contract_sha256=contract_sha)
    ready={r['instance_id']:r for r in offline['results']}
    official={r['instance_id']:r for r in curator['results']}
    for row in lock['instances']:
        for field in ('online_rootfs_sha256','online_tree_sha256','public_checks_sha256','base_commit'):
            if row[field]!=ready[row['instance_id']][field]:raise ValueError('lock differs from tested environment: '+field)
        validate_curator_binding(row,official[row['instance_id']])
    output=Path(output);output.mkdir(parents=True,exist_ok=False,mode=0o700)
    _atomic_write(output/'SWE-CONTRACT.json',contract_bytes);_atomic_write(output/'SWE-RUN-LOCK.json',canonical(lock))
    _atomic_write(output/'schedule.json',canonical(schedule));_atomic_write(output/'source-manifest.json',canonical(source_manifest()))
    gates={kind:dict(directory=str(Path(path).resolve()),sha256=sha256_file(Path(path)/'report.json')) for kind,path in
        [('offline-preflight',preflight_dir),('official-controls',curator_dir),('mock-smoke',smoke_dir),('remote-calibration',calibration_dir),('software-verification',verification_dir)]}
    store=ReceiptStore(output/'receipts',output/'authority')
    store.append(dict(event='repoworld.study-seal',gates=gates,files={name:sha256_file(output/name) for name in
        ('SWE-CONTRACT.json','SWE-RUN-LOCK.json','schedule.json','source-manifest.json')}))
    validate_seal(output,sample_path)
    return lock


def calibrate_remote(registry,contract,sample_path,*,preflight_dir,curator_dir,smoke_dir,provider_config,instance_id,output):
    sources=source_manifest()
    offline=require_gate(preflight_dir,'offline-preflight');require_gate(smoke_dir,'mock-smoke')
    curator=require_gate(curator_dir,'official-controls')
    if (offline['registry_sha256']!=sha256_file(registry) or offline['sample_sha256']!=sha256_file(sample_path)
        or curator['sample_sha256']!=sha256_file(sample_path) or curator['dataset_sha256']!=contract['dataset']['parquet_sha256']):
        raise ValueError('calibration gates belong to another registry/sample/dataset')
    validate_model_config(provider_config,contract)
    sample=json.loads(Path(sample_path).read_bytes())
    if instance_id not in {r['instance_id'] for r in sample['calibration']}:raise ValueError('remote calibration must not consume a primary issue')
    tasks,entries,_=load_registry(registry,contract,sample_path)
    output=Path(output);base=prepare_entry(tasks[instance_id],entries[instance_id],output/'prepared')
    tested=next(r for r in offline['results'] if r['instance_id']==instance_id)
    if (base.snapshot.id!=tested['online_tree_sha256'] or base.environment.rootfs_sha256!=tested['online_rootfs_sha256']
        or validate_plan(entries[instance_id]['check_plan'])!=tested['public_checks_sha256']):raise ValueError('calibration environment changed after preflight')
    provider=RepoProvider(provider_config);start=time.monotonic()
    try:
        metadata=provider.verify_worker(contract)
        result=run_episode(base,'E',73,provider=provider,output=output/'episode',check_plan=entries[instance_id]['check_plan'])
    finally:_atomic_write(output/'worker-stop.json',canonical(provider.stop()))
    valid=result['is_llm'] and result['budget']['used']['llm_calls']>0 and not result['budget']['pending']
    return write_gate(output,dict(kind='remote-calibration',valid=bool(valid),instance_id=instance_id,
        elapsed_seconds=time.monotonic()-start,budget=result['budget'],diff_sha256=result['diff_sha256'],
        official_evaluation=False,worker_metadata=metadata,model_config_sha256=hashlib.sha256(canonical(provider_identity(provider_config))).hexdigest()),source_before=sources)


def curator_scope(sample,scope):
    if scope == 'all':return 'official-controls', sample_roster(sample)
    if scope == 'calibration':return 'official-calibration-controls', sample['calibration']
    raise ValueError('unsupported curator scope')


def curator_preflight(cap,contract,sample_path,output,*,allow_pull=False,scope='all'):
    """No model, no GPU: only the curator can read the reference implementation."""
    import subprocess,os
    from .evaluator import HARNESS_COMMIT,curator_command
    sources=source_manifest()
    output=Path(output);output.mkdir(parents=True,exist_ok=False,mode=0o700)
    if sha256_file(cap.dataset)!=contract['dataset']['parquet_sha256']:raise ValueError('fixed curator dataset required')
    commit=subprocess.check_output(['git','-C',str(cap.harness),'rev-parse','HEAD'],text=True,timeout=10).strip()
    dirty=subprocess.check_output(['git','-C',str(cap.harness),'status','--porcelain','--untracked-files=no'],timeout=10)
    if commit!=HARNESS_COMMIT or dirty:raise ValueError('clean pinned official harness required')
    kind,selected=curator_scope(json.loads(Path(sample_path).read_bytes()),scope)
    request=dict(harness=str(cap.harness.resolve()),dataset=str(cap.dataset.resolve()),dataset_sha256=contract['dataset']['parquet_sha256'],
        instances=[{k:r[k] for k in ('instance_id','base_commit')} for r in selected],allow_pull=allow_pull)
    _atomic_write(output/'request.json',canonical(request))
    env=dict(os.environ)
    if cap.docker_host:env['DOCKER_HOST']=cap.docker_host
    with (output/'curator-private.log').open('wb') as f:
        process=subprocess.run(curator_command(cap.python,'--controls',str((output/'request.json').resolve())),
            cwd=output,env=env,stdout=f,stderr=f,timeout=12*3600)
    if process.returncode:
        results=[dict(instance_id=r['instance_id'],valid=False,error='curator_process_failed') for r in request['instances']]
    else:results=json.loads((output/'controls.json').read_bytes())
    valid=process.returncode==0 and {r['instance_id'] for r in results}=={r['instance_id'] for r in request['instances']} and all(r['valid'] for r in results)
    return write_gate(output,dict(kind=kind,scope=scope,valid=valid,results=results,gpu_hours=0,
        harness_commit=commit,dataset_sha256=contract['dataset']['parquet_sha256'],
        private_log_sha256=sha256_file(output/'curator-private.log'),sample_sha256=sha256_file(sample_path)),source_before=sources)


def run_study(sealed_dir,registry,sample_path,provider_config,output,*,phase=None):
    holder={}
    try:return _run_study(sealed_dir,registry,sample_path,provider_config,output,phase=phase,holder=holder)
    finally:
        if holder.get('provider') is not None:
            _atomic_write(Path(output)/'worker-stop.json',canonical(holder['provider'].stop()))


def _run_study(sealed_dir,registry,sample_path,provider_config,output,*,phase=None,holder):
    sealed_dir=Path(sealed_dir);output=Path(output);output.mkdir(parents=True,exist_ok=True,mode=0o700)
    contract=json.loads((sealed_dir/'SWE-CONTRACT.json').read_bytes());lock=json.loads((sealed_dir/'SWE-RUN-LOCK.json').read_bytes())
    seal=validate_seal(sealed_dir,sample_path)
    gate=require_gate(seal['gates']['offline-preflight']['directory'],'offline-preflight')
    calibration=require_gate(seal['gates']['remote-calibration']['directory'],'remote-calibration')
    validate_model_config(provider_config,contract)
    provider_sha=hashlib.sha256(canonical(provider_identity(provider_config))).hexdigest()
    if provider_sha!=calibration['model_config_sha256']:raise ValueError('provider differs from remote calibration')
    if sha256_file(registry)!=gate['registry_sha256']:raise ValueError('registry differs from offline preflight')
    require_launch(contract,sample_path,lock,contract_sha256=sha256_file(sealed_dir/'SWE-CONTRACT.json'))
    if hashlib.sha256(canonical(source_manifest())).hexdigest()!=lock['code_manifest_sha256']:raise ValueError('sources changed after freeze')
    schedule=json.loads((sealed_dir/'schedule.json').read_bytes())
    if hashlib.sha256(canonical(schedule)).hexdigest()!=lock['schedule_sha256']:raise ValueError('schedule hash mismatch')
    tasks,entries,_=load_registry(registry,contract,sample_path)
    worker_verified=False
    from .memory import SharedConceptLibrary
    with (output/'run.lock').open('a') as ownership:
        fcntl.flock(ownership,fcntl.LOCK_EX|fcntl.LOCK_NB)
        store=ReceiptStore(output/'receipts',output/'authority')
        bind_study(store,study_identity(sealed_dir,gate['registry_sha256'],provider_sha))
        provider=RepoProvider(provider_config);holder['provider']=provider
        from .audit import audit_episode
        for r in store.records:
            if r['body'].get('event')=='repoworld.cell-completed':
                old=r['body'];completed_episode=audit_episode(output/'episodes'/old['cell_id'])
                if hashlib.sha256(canonical(completed_episode['result'])).hexdigest()!=old['submission_sha256']:raise ValueError('completed episode was altered')
        # A crash before the timing receipt cannot erase active GPU wall time.
        starts={r['body']['window_id']:r['body'] for r in store.records if r['body'].get('event')=='repoworld.gpu-window-start'}
        ends={r['body']['window_id'] for r in store.records if r['body'].get('event')=='repoworld.gpu-window-end'}
        for key,value in starts.items():
            if key not in ends:store.append(dict(event='repoworld.gpu-window-end',window_id=key,phase=value['phase'],
                seconds=max(0,time.time()-value['utc']),charge_basis='conservative elapsed across interrupted window'))
        for cell in schedule:
            if phase is not None and cell['phase']!=phase:continue
            completed=[r['body'] for r in store.records if r['body'].get('event') in ('repoworld.cell-completed','repoworld.cell-not-started') and r['body']['cell_id']==cell['cell_id']]
            if completed:continue
            windows=[r['body'] for r in store.records if r['body'].get('event')=='repoworld.gpu-window-end']
            spent=sum(r['seconds'] for r in windows)
            category='memory' if cell['phase'].startswith('memory') else cell['phase']
            phase_spent=sum(r['seconds'] for r in windows if r['phase']==category)
            if spent+1800>contract['gpu_budget']['total_cap_hours']*3600 or phase_spent+1800>contract['gpu_budget']['phase_caps_hours'][category]*3600:
                # Never label an interrupted/pending episode as unstarted.
                if any(r['body'].get('event')=='repoworld.cell-start' and r['body']['cell_id']==cell['cell_id'] for r in store.records):break
                record_not_started(store,cell,'registered GPU wall cap: insufficient room for one bounded episode')
                continue
            # Includes local preparation/waiting while a worker may be loaded.
            import uuid
            window=uuid.uuid4().hex;window_start=time.time()
            store.append(dict(event='repoworld.gpu-window-start',window_id=window,phase=category,utc=window_start))
            target=output/'episodes'/cell['cell_id'];base=prepare_entry(tasks[cell['instance_id']],entries[cell['instance_id']],target/'prepared')
            locked=next(r for r in lock['instances'] if r['instance_id']==cell['instance_id'])
            if base.snapshot.id!=locked['online_tree_sha256'] or base.environment.rootfs_sha256!=locked['online_rootfs_sha256'] or validate_plan(entries[cell['instance_id']]['check_plan'])!=locked['public_checks_sha256']:raise ValueError('prepared episode differs from lock')
            if not worker_verified:
                metadata=provider.verify_worker(contract,lock)
                store.append(dict(event='repoworld.worker-ready',metadata=metadata))
                worker_verified=True
            library=None
            if cell['phase']=='memory_donor' or cell.get('condition')=='shared':
                library=SharedConceptLibrary(output/'libraries'/cell['chain_id'])
            started=time.monotonic()
            store.append(dict(event='repoworld.cell-start',cell_id=cell['cell_id'],utc=time.time()))
            try:
                result=run_episode(base,cell['arm'],cell['seed'],provider=provider,output=target,
                    check_plan=entries[cell['instance_id']]['check_plan'],library=library)
                store.append(dict(event='repoworld.cell-completed',cell_id=cell['cell_id'],submission_sha256=hashlib.sha256(canonical(result)).hexdigest()))
                print(json.dumps(dict(cell_id=cell['cell_id'],instance_id=cell['instance_id'],arm=cell['arm'],status=result['status'])),flush=True)
            finally:
                store.append(dict(event='repoworld.cell-time',cell_id=cell['cell_id'],elapsed_seconds=time.monotonic()-started))
                store.append(dict(event='repoworld.gpu-window-end',window_id=window,phase=category,seconds=max(0,time.time()-window_start),charge_basis='local wall including preparation'))
        # All phases, including guard and memory, must be accounted for.
        completed={r['body']['cell_id'] for r in store.records if r['body'].get('event')=='repoworld.cell-completed'}
        unstarted={r['body']['cell_id']:r['body']['result'] for r in store.records if r['body'].get('event')=='repoworld.cell-not-started'}
        if completed|set(unstarted)=={r['cell_id'] for r in schedule}:
            submissions={r['cell_id']:unstarted[r['cell_id']] if r['cell_id'] in unstarted else audit_episode(output/'episodes'/r['cell_id'])['result'] for r in schedule}
            freeze_set(output/'frozen',schedule,submissions,lock_sha256=hashlib.sha256(canonical(lock)).hexdigest())
    return dict(completed=len(completed),not_started=len(unstarted),registered=len(schedule),frozen=completed|set(unstarted)=={r['cell_id'] for r in schedule})
