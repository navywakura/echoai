"""B24 arithmetic, physical custody and deterministic feedback review; no simulation."""
import gzip
import hashlib
import json
from echo_arc import s6b24_search as search
from seed import s6b24_model as model
from pathlib import Path
from seed.s6b20_review import read, sha, validate, diff


def require(ok, message):
    if not ok: raise RuntimeError(message)


def bind_measurement(root,manifest,namespace,label,result,jobs):
    """An equal replay alone is insufficient: every row needs its paid execution."""
    config=manifest['configuration'];stem=namespace.removesuffix('-audit')
    if stem.startswith('s-'):
        require(stem[2:] in config['cells'],'unknown arm namespace')
        specs=config['screen']
    elif stem=='v-broad':specs=config['development']
    elif stem=='v-new':specs=config['retention']
    else:raise RuntimeError('unknown measurement namespace')
    evaluation=label.removesuffix('/replay')
    if evaluation=='baseline':
        policy=read(root/'input/baseline.json')['policy']
    elif evaluation.startswith('candidate/'):
        ident=evaluation.split('/',1)[1]
        if stem.startswith('s-'):
            require(ident.isdigit() and 0<=int(ident)<18,'unknown candidate label')
            policy=read(root/'steps'/stem[2:]/(ident+'.json'))['event']['candidate']
        else:
            policy=read(root/'finalists.json')['selection'][ident]['policy']
    else:raise RuntimeError('unknown evaluation label')
    expected=[list(spec) for spec in specs]
    require([[row[k] for k in ('version','seed','rep','budget')] for row in result['rows']]==expected,
            'measurement does not contain complete declared cohort')
    partition='replay' if label.endswith('/replay') else 'main'
    for spec,row in zip(expected,result['rows']):
        require(row.get('policy_sha256')==sha(policy),'measurement row uses wrong policy')
        key=sha(dict(profile=sha(manifest),namespace=namespace,policy=policy,spec=spec,
                     observed=expected==config['screen'],evaluation=evaluation))
        relative=f'{namespace}/cache/{partition}/{key}.json';path=root/relative
        require(path.is_file(),'measurement lacks physical execution cache')
        cache=read(path)
        require(cache['key']==key and cache['record']==row and cache['digest']==sha(row),'measurement row differs from execution cache')
        job=jobs.get(cache['job_id'])
        require(job is not None,'measurement has no reserved execution')
        require(job['key']==key and job['cache']==relative and job['spec']==spec and job['policy_sha256']==sha(policy)
                and job['namespace']==namespace and job['label']==label,'measurement execution identity mismatch')
        require(job['task_id']==sha([namespace,partition,key]),'execution task hash mismatch')


def review(root,manifest_path):
    m=read(manifest_path)
    from seed.s6b24_preflight import verify
    runtime_root=Path(m.get('execution_root',str(root)))
    verify(root,read(manifest_path.parent/'models.json'),sha(m),runtime_root=runtime_root)
    repo=Path(__file__).resolve().parents[1]
    for group,base in (('sources',repo),('inputs',manifest_path.parent)):
        for name,digest in m[group].items():
            require(hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,'changed '+name)
    budget=read(root/'budget.json');jobs=budget['jobs'];counts={};cached=0
    require(len(jobs)==budget['scheduled_games']<=budget['cap']==8310,'game cap mismatch')
    require(len({j['task_id'] for j in jobs})==len(jobs),'duplicate task IDs')
    require([j['job_id'] for j in jobs]==list(range(len(jobs))),'job ID sequence')
    by_job={j['job_id']:j for j in jobs}
    for group,cap in m['configuration']['allocations'].items():
        require(sum(j['allocation']==group for j in jobs)<=cap,'allocation exceeded')
    for job in jobs:
        started=read(root/'executions/started'/f"{job['job_id']:06d}.json")
        done=read(root/'executions/completed'/f"{job['job_id']:06d}.json")
        record=read(root/job['cache'])
        require(started['task_id']==done['task_id']==job['task_id'],'task identity')
        require(record['job_id']==job['job_id'] and record['key']==job['key'],'cache identity')
        require(record['digest']==sha(record['record'])==done['record_sha256'],'cache digest')
        require([record['record'][k] for k in ('version','seed','rep','budget')]==job['spec'],'case identity')
        cached+=1
    for state in ('started','completed'):
        require(len(list((root/'executions'/state).glob('*.json')))==cached,'orphan execution')
    require(not list((root/'executions/failed').glob('*.json')),'failed physical game')
    require(sum(len(list((ns/'cache').glob('*/*.json'))) for ns in root.iterdir() if ns.is_dir())==cached,'orphan cache')
    measurements=0
    for ns in root.iterdir():
        if not ns.is_dir():continue
        for path in (ns/'measurements').rglob('*.json'):
            result=read(path);validate(result);measurements+=1
            label=path.relative_to(ns/'measurements').with_suffix('').as_posix()
            bind_measurement(root,m,ns.name,label,result,by_job)
            if ns.name.endswith('-audit') or path.name=='replay.json':continue
            relative=path.relative_to(ns/'measurements')
            require(result==read(path.with_suffix('')/'replay.json'),'replay mismatch')
            require(result==read(root/(ns.name+'-audit')/'measurements'/relative),'independent mismatch')
            receipt=read(ns/'audits'/relative)
            require(receipt['valid'] and receipt['measurement_sha256']==sha(result),'audit receipt')
    fixture=read(manifest_path.parent/'baseline.json');micro=read(root/'micro.json');winners={};logical=0;calls=[]
    for arm in m['configuration']['cells']:
        base=read(root/('s-'+arm)/'measurements/baseline.json');history=[]
        cells=[c for c in micro['cells'] if c['arm']==arm]
        require([c['slot'] for c in cells]==list(range(1,len(cells)+1)),'slot order')
        require(len(cells)==18 or bool(cells) and cells[-1]['verdict']=='A_ONLY_PASS','early stop without pass')
        for index,cell in enumerate(cells):
            saved=read(root/'steps'/arm/f'{index:03d}.json');e=saved['event']
            receipt=read(root/'requests'/arm/f'{index:03d}.json');req=receipt['request']
            raw=gzip.decompress((root/'investigator-inputs'/(saved['input_sha256']+'.json.gz')).read_bytes())
            import json
            require(hashlib.sha256(raw).hexdigest()==saved['input_sha256']==receipt['input_sha256'],'research input digest')
            require(json.loads(raw)==dict(policy=fixture['policy'],base=base,own_history=search.visible_history(arm,index,824101,history),kind=arm,index=index,seed=824101),'research input surface')
            require(search.from_bytes(raw)==req,'deterministic request reconstruction')
            require(sha(req)==saved['request_sha256']==receipt['request_sha256'],'request digest')
            require(e['base_sha256']==sha(fixture['policy']) and e['id']==index+1,'event base or ID')
            require(e['schedule']==req['schedule'] and e['target_id']==req['target_id'] and e['type']==req['type'],'feedback request binding')
            if req['model_call_required']:
                call_id=f'{arm}/{index:03d}';calls.append(call_id);folder=root/'calls'/call_id
                call=model.load(folder,req,arm,824101+index,sha(m))
                expected_command=model.command(read(manifest_path.parent/'models.json')['N7'],runtime_root/'calls'/arm/f'{index:03d}'/'prompt.txt',824101+index,req)
                require(read(folder/'command.json')==expected_command,'inference command')
                require(call['request_sha256']==sha(req) and call['profile_sha256']==sha(m),'model request linkage')
                require(call['proposal']==e['proposal'] and call['usage']==e['usage'],'model result linkage')
                for name,digest in call['files'].items():require(hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,'model file digest')
                tokens=read(folder/'tokens.json')
                require(set(tokens)=={'N7'} and all(len(t)<=8192 for t in tokens.values()),'input token limits')
                require(e['usage']['input_tokens']==len(tokens['N7']),'input token accounting')
                require(e['usage']['output_tokens']==len(read(folder/'output-tokens.json')),'output token accounting')
            else:require(e['proposal']==req.get('proposal') and e['usage']['model_calls']==0,'non-model proposal')
            require(e['verdict']==cell['verdict'] and e.get('A')==cell['diff'],'cell linkage')
            if e['verdict'] in ('NO_ELIGIBLE_CANDIDATE','DUPLICATE'):
                require(not e.get('development'),'unexpected skipped simulation')
                if e['verdict']=='DUPLICATE':require(any(h.get('proposal')==e['proposal'] for h in search.visible_history(arm,index,824101,history)),'false duplicate')
                else: require(e['proposal'] is None and not req['model_call_required'] and req.get('abstention')=='NO_ELIGIBLE_CANDIDATE','false exhausted menu')
            else:
                from seed import s6b22
                actual_policy=s6b22.engine.strategy(program=s6b22.engine.patch.append(fixture['policy']['program'],e['proposal']))
                require(actual_policy==e['candidate'],'candidate differs from submitted patch')
                after=read(root/('s-'+arm)/'measurements/candidate'/f'{index:03d}.json')
                change=diff(base,after)
                require(e['A']==change and e['levels']==after['levels'],'effects')
                require(e['proposal_sha256']==sha(e['proposal']) and e['policy_sha256']==sha(e['candidate']),'policy digest')
                require(e['actions_per_level']==[r['actions_per_level'] for r in after['rows']],'feedback actions')
                from echo_arc import guard_search
                require(e['development']==guard_search.comparison(base,after,'HOLD'),'research feedback differs from measured trajectories')
                require(e['trajectory_sha256']==after['trace_digest'],'trajectory feedback hash')
                passed=change['gain']>=2 and not change['loss_indices']
                require((e['verdict']=='A_ONLY_PASS')==passed,'verdict')
                if passed:
                    require(index==len(cells)-1,'search after pass')
                    winners[arm]=dict(slot=index+1,policy=e['candidate'],policy_sha256=sha(e['candidate']))
            if e['schedule']['phase']=='repair':
                parent=next(h for h in history if h['id']==e['target_id'])
                require(e['proposal']['patches'][0]['set']==parent['proposal']['patches'][0]['set'],'repair changed duration')
            require(e['author']==req['schedule'].get('author',0) and e['round']==req['schedule'].get('round',index//6),'researcher attribution')
            history.append(e);logical+=1
        require(sum(e['schedule']['phase']=='repair' for e in history)<=8,'repair cap')
    require(winners==micro['winners']==read(root/'finalists.json')['selection'],'winner identity')
    ledger=read(root/'model-budget.json') if (root/'model-budget.json').exists() else {'calls':[]}
    require(set(calls)==set(ledger['calls']) and len(calls)==len(ledger['calls'])<=72,'call ledger')
    transfer=read(root/'transfer.json'); require(set(transfer)==set(winners),'transfer entries')
    for arm,item in winners.items():
        for ns,phase in (('v-broad','broad'),('v-new','retention')):
            if phase=='retention' and transfer[arm][phase]=='NOT_RUN':continue
            result=read(root/'validation'/ns/(arm+'.json'))
            change=diff(read(root/ns/'measurements/baseline.json'),read(root/ns/'measurements/candidate'/(arm+'.json')))
            passed=not change['loss_indices'] and (phase=='retention' or change['gain']>=2)
            require(result['diff']==change and result['passed']==passed,'validation arithmetic')
            require(transfer[arm][phase]==('PASS' if passed else 'FAIL'),'transfer status')
            if phase=='retention':
                require(result['policy_sha256']==item['policy_sha256'],'retention policy binding')
                permit=read(root/'permits/v-new.json')
                require(item['policy_sha256'] in permit['policies'] and transfer[arm]['broad']=='PASS','protection bypass')
    timing=[]
    for arm in m['configuration']['cells']:
        for cell in [c for c in micro['cells'] if c['arm']==arm]:
            index=cell['slot']-1;t=read(root/'timings'/arm/f'{index:03d}.json')
            require(t['arm']==arm and t['slot']==index and bool(t['segments']),'timing scope')
            require(all(x['seconds']>=0 and x['cpu_seconds']>=0 and x['exit'] in ('complete','checkpoint') for x in t['segments']),'incomplete/invalid slot timing')
            saved=read(root/'steps'/arm/f'{index:03d}.json')
            require(saved['seconds']<=sum(x['seconds'] for x in t['segments'])+1e-9,'lost wall timing')
            timing.extend(t['segments'])
    result=dict(valid=True,profile_sha256=sha(m),completed_games=cached,logical_attempts=logical,
                measurements=measurements,model_calls=len(calls),exam_opened=False,s6_green=False,
                slot_wall_seconds=sum(x['seconds'] for x in timing),parent_cpu_seconds=sum(x['cpu_seconds'] for x in timing),
                checkpoint_segments=sum(x['exit']=='checkpoint' for x in timing))
    (root/'arithmetic-review.json').write_text(__import__('json').dumps(result,sort_keys=True)+'\n')
    return result
