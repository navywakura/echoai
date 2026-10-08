"""Independent stdlib arithmetic review. Does not import researcher or simulator."""
import gzip
import hashlib
import json
import math
from pathlib import Path

from seed.s6b20_review import read, sha, validate, diff


def paired_summary(winners,seeds):
    counts=dict(both=0,M_only=0,R_only=0,neither=0)
    ranks={'R22':[],'M22':[]}
    for seed in seeds:
        r=winners.get(f'R22-{seed}');m=winners.get(f'M22-{seed}')
        counts['both' if r and m else 'M_only' if m else 'R_only' if r else 'neither']+=1
        for name,value in (('R22',r),('M22',m)):
            ranks[name].append(value['slot'] if value else 19)
    n=len(seeds);d=counts['M_only']+counts['R_only']
    p=min(1.0,2*sum(math.comb(d,k) for k in range(min(counts['M_only'],counts['R_only'])+1))/2**d) if d else 1.0
    delta=(counts['M_only']-counts['R_only'])/n
    radius=math.sqrt(2*math.log(40)/n)
    return dict(pairs=n,outcomes=counts,success_rate_difference_M_minus_R=delta,
                mcnemar_exact_two_sided=p,directional_pilot_evidence=p<=0.05 and delta>0,
                conditional_95pct_hoeffding_interval=[max(-1,delta-radius),min(1,delta+radius)],
                interval_assumption='independent seed streams, fixed development panel; conservative bound',
                capped_rank_to_first_pass=ranks,no_pass_rank=19,failures_censored_at=18,
                generalization_confirmed=False,unit='paired complete search run, not candidate or replay')


def review(root,manifest_path):
    manifest=read(manifest_path);repo=Path(__file__).resolve().parents[1]
    for name,h in manifest['sources'].items():
        assert hashlib.sha256((repo/name).read_bytes()).hexdigest()==h,name
    for name,h in manifest['inputs'].items():
        assert hashlib.sha256((manifest_path.parent/name).read_bytes()).hexdigest()==h,name
    ledger=read(root/'budget.json');jobs=ledger['jobs'];cached=0;measurements=0
    assert len(jobs)==ledger['scheduled_games']<=ledger['cap']==15336
    assert len({j['task_id'] for j in jobs})==len(jobs)
    for group,limit in manifest['configuration']['allocations'].items():
        assert sum(j['allocation']==group for j in jobs)<=limit
    for job in jobs:
        started=read(root/'executions/started'/f"{job['job_id']:06d}.json")
        finished=read(root/'executions/completed'/f"{job['job_id']:06d}.json")
        record=read(root/job['cache'])
        assert started['task_id']==finished['task_id']==job['task_id']
        assert record['job_id']==job['job_id'] and record['key']==job['key']
        assert record['digest']==sha(record['record'])==finished['record_sha256']
        assert [record['record'][k] for k in ('version','seed','rep','budget')]==job['spec']
        cached+=1
    assert not list((root/'executions/failed').glob('*.json'))
    assert len(list((root/'executions/started').glob('*.json')))==cached
    assert len(list((root/'executions/completed').glob('*.json')))==cached
    assert sum(len(list((ns/'cache').glob('*/*.json'))) for ns in root.iterdir() if ns.is_dir())==cached
    for ns in root.iterdir():
        if not ns.is_dir() or not (ns/'measurements').exists():continue
        for path in (ns/'measurements').rglob('*.json'):
            result=read(path);validate(result);measurements+=1
            if ns.name.endswith('-audit') or path.name=='replay.json':continue
            assert result==read(path.with_suffix('')/'replay.json')
            assert result==read(root/(ns.name+'-audit')/'measurements'/path.relative_to(ns/'measurements'))
            receipt=read(ns/'audits'/path.relative_to(ns/'measurements'))
            assert receipt['valid'] and receipt['measurement_sha256']==sha(result)
    micro=read(root/'micro.json');winners={};logical=0
    fixture=read(manifest_path.parent/'baseline.json')
    for name,kind,seed in manifest['configuration']['cells']:
        base=read(root/('s-'+name)/'measurements/baseline.json');history=[]
        cells=[c for c in micro['cells'] if c['arm']==name]
        assert [c['slot'] for c in cells]==list(range(1,len(cells)+1))
        assert len(cells)==18 or cells[-1]['verdict']=='A_ONLY_PASS'
        for index,cell in enumerate(cells):
            step=read(root/'steps'/name/f'{index:03d}.json');event=step['event']
            request=read(root/'requests'/name/f'{index:03d}.json')
            data=gzip.decompress((root/'investigator-inputs'/(step['input_sha256']+'.json.gz')).read_bytes())
            assert hashlib.sha256(data).hexdigest()==step['input_sha256']==request['input_sha256']
            assert json.loads(data)==dict(policy=fixture['policy'],base=base,own_history=history,kind=kind,index=index,seed=seed)
            assert sha(request['request'])==step['request_sha256']==request['request_sha256']
            assert event['proposal']==request['request']['proposal']
            assert event['proposal_sha256']==sha(event['proposal']) and event['policy_sha256']==sha(event['candidate'])
            after=read(root/('s-'+name)/'measurements/candidate'/f'{index:03d}.json')
            delta=diff(base,after)
            assert event['A']==cell['diff']==delta
            assert event['levels']==cell['levels']==after['levels']
            passed=delta['gain']>=2 and not delta['loss_indices']
            assert (cell['verdict']=='A_ONLY_PASS')==passed
            assert event['audited'] and event['usage']==dict(model_calls=0,input_tokens=0,output_tokens=0)
            if event['schedule']['phase']=='repair':
                parent=next(e for e in history if e['id']==event['target_id'])
                assert event['proposal']['patches'][0]['set']==parent['proposal']['patches'][0]['set']
            if passed:
                assert index==len(cells)-1
                winners[name]=dict(slot=index+1,policy=event['candidate'],policy_sha256=sha(event['candidate']))
            history.append(event);logical+=1
        repairs=sum(e['schedule']['phase']=='repair' for e in history)
        assert repairs<=8
        if len(history)==18:assert len(history)-repairs>=10
    assert winners==micro['winners']
    expected={}
    for kind in ('R22','M22'):
        for seed in manifest['configuration']['seeds']:
            name=f'{kind}-{seed}'
            if name in winners:
                expected[kind]=dict(winners[name],arm=name);break
    assert read(root/'finalists.json')['selection']==expected
    for name in ['v-micro','v-broad','v-new']+[f'final-{arm}-{phase}' for arm in ('R22','M22') for phase in ('broad','new')]:
        path=root/(name+'.json')
        if not path.exists():continue
        record=read(path);folder=root/name/'measurements'
        delta=diff(read(folder/'baseline.json'),read(folder/'candidate.json'))
        assert record['diff']==delta and record['passed']==(not delta['loss_indices'] and (name.endswith('-new') or delta['gain']>=2))
        if name.endswith('-new'):
            permit=read(root/'permits'/('v-new.json' if name=='v-new' else 's-new.json'))
            assert record['policy_sha256'] in permit['policies']
    summary=paired_summary(winners,manifest['configuration']['seeds'])
    assert summary==read(root/'selector.json')['pilot']
    result=dict(valid=True,profile_sha256=sha(manifest),logical_attempts=logical,
                reserved_games=len(jobs),started_games=cached,completed_games=cached,
                measurements=measurements,model_calls=0,exam_opened=False,s6_green=False)
    (root/'arithmetic-review.json').write_text(json.dumps(result,sort_keys=True)+'\n')
    return result
