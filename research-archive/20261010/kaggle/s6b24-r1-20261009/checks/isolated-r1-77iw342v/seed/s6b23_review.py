"""Independent B23 arithmetic/accounting review; no simulator or researcher."""
import gzip
import hashlib
from pathlib import Path
from seed.s6b20_review import read, sha, validate, diff


def require(ok, message):
    if not ok: raise RuntimeError(message)


def review(root,manifest_path):
    m=read(manifest_path);repo=Path(__file__).resolve().parents[1]
    for group,base in (('sources',repo),('inputs',manifest_path.parent)):
        for name,digest in m[group].items():
            require(hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,'changed '+name)
    budget=read(root/'budget.json');jobs=budget['jobs'];counts={};cached=0
    require(len(jobs)==budget['scheduled_games']<=budget['cap']==8310,'game cap mismatch')
    require(len({j['task_id'] for j in jobs})==len(jobs),'duplicate task IDs')
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
            require(json.loads(raw)==dict(policy=fixture['policy'],base=base,own_history=history,kind=arm,index=index,seed=823101),'research input surface')
            require(sha(req)==saved['request_sha256']==receipt['request_sha256'],'request digest')
            require(e['base_sha256']==sha(fixture['policy']) and e['id']==index+1,'event base or ID')
            if arm in ('N7','N14'):
                call_id=f'{arm}/{index:03d}';calls.append(call_id);folder=root/'calls'/call_id
                call=read(folder/'result.json')
                require(call['request_sha256']==sha(req) and call['profile_sha256']==sha(m),'model request linkage')
                require(call['proposal']==e['proposal'] and call['usage']==e['usage'],'model result linkage')
                for name,digest in call['files'].items():require(hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,'model file digest')
                tokens=read(folder/'tokens.json')
                require(set(tokens)=={'N7','N14'} and all(len(t)<=8192 for t in tokens.values()),'input token limits')
                require(e['usage']['input_tokens']==len(tokens[arm]),'input token accounting')
                require(e['usage']['output_tokens']==len(read(folder/'output-tokens.json')),'output token accounting')
            else:require(e['proposal']==req['proposal'] and e['usage']['model_calls']==0,'non-model proposal')
            require(e['verdict']==cell['verdict'] and e.get('A')==cell['diff'],'cell linkage')
            if e['verdict'] in ('INVALID_PROPOSAL','DUPLICATE'):
                require(arm in ('N7','N14') and not e.get('development'),'unexpected skipped simulation')
                if e['verdict']=='DUPLICATE':require(any(h.get('proposal')==e['proposal'] for h in history),'false duplicate')
                else: require(e['proposal'] is None,'invalid proposal has program')
            else:
                after=read(root/('s-'+arm)/'measurements/candidate'/f'{index:03d}.json')
                change=diff(base,after)
                require(e['A']==change and e['levels']==after['levels'],'effects')
                require(e['proposal_sha256']==sha(e['proposal']) and e['policy_sha256']==sha(e['candidate']),'policy digest')
                require(e['actions_per_level']==[r['actions_per_level'] for r in after['rows']],'feedback actions')
                passed=change['gain']>=2 and not change['loss_indices']
                require((e['verdict']=='A_ONLY_PASS')==passed,'verdict')
                if passed:
                    require(index==len(cells)-1,'search after pass')
                    winners[arm]=dict(slot=index+1,policy=e['candidate'],policy_sha256=sha(e['candidate']))
            if e['schedule']['phase']=='repair':
                parent=next(h for h in history if h['id']==e['target_id'])
                require(e['proposal']['patches'][0]['set']==parent['proposal']['patches'][0]['set'],'repair changed duration')
            history.append(e);logical+=1
        require(sum(e['schedule']['phase']=='repair' for e in history)<=8,'repair cap')
    require(winners==micro['winners']==read(root/'finalists.json')['selection'],'winner identity')
    ledger=read(root/'model-budget.json') if (root/'model-budget.json').exists() else {'calls':[]}
    require(set(calls)==set(ledger['calls']) and len(calls)==len(ledger['calls'])<=36,'call ledger')
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
                permit=read(root/'permits/v-new.json')
                require(item['policy_sha256'] in permit['policies'] and transfer[arm]['broad']=='PASS','protection bypass')
    result=dict(valid=True,profile_sha256=sha(m),completed_games=cached,logical_attempts=logical,
                measurements=measurements,model_calls=len(calls),exam_opened=False,s6_green=False)
    (root/'arithmetic-review.json').write_text(__import__('json').dumps(result,sort_keys=True)+'\n')
    return result
