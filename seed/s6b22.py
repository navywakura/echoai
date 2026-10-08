"""Private B22 V/S experiment, using the frozen actor and individual-loss judge."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from types import FunctionType

from seed import s6b20 as previous
from seed.game_selfimprove import canonical, sha, journal
from echo_arc import s6b22_search as search, guard_search, consumption_timeline as timeline
from echo_arc.contrastive_grammar import validate_answer

REPO=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('ECHO_B22_ROOT',str(REPO/'lab/seed/s6b22-20261006')))
INPUT=Path(os.environ.get('ECHO_B22_INPUT',str(REPO/'lab/seed/s6b22-20261006/input')))
A,DEVELOPMENT=previous.A,previous.DEVELOPMENT
V_NEW=[(v,s,0,2000) for v in (2,3) for s in range(65000,65040)]
S_NEW=[(v,s,0,2000) for v in (2,3) for s in range(66000,66040)]
SEEDS=(822101,822117,822129,822143,822157,822173,822191,822211)
_cells=[(f'{kind}-{s}',kind,s) for s in SEEDS for kind in search.KINDS]
search.rng(822000,'execution-order').shuffle(_cells)
CELLS=tuple(_cells)
WORKERS=4
CAPS={'V':1512,'S':10944,'FINAL-R22':1440,'FINAL-M22':1440}
MAX_GAMES=sum(CAPS.values())
read,atomic,file_sha,now=previous.read,previous.atomic,previous.file_sha,previous.now
engine=previous.engine
difference=previous.difference


def config():
    return dict(condition='S6-B22-VS',screen=A,development=DEVELOPMENT,
                validation_new=V_NEW,selector_new=S_NEW,seeds=SEEDS,cells=CELLS,
                rounds=18,workers=WORKERS,max_games=MAX_GAMES,allocations=CAPS,
                unallocated_margin=664,search=search.config(),epsilon=1e-10,
                first_pass=True,model_calls_cap=0,exam_allowed=False,private=True,paid=False,
                per_game_timeout_seconds=240,
                finalists='first successful seed in declared order per arm, then first audited pass',
                confirmation='eight-pair pilot only; later independent panels need a new contract',
                sequence='V micro/broad; S micro; freeze finalists; V new; S broad/new',
                N='NOT_RUN; model and budget need a later contract',
                E='NOT_RUN; SEMILLA pilot/campaign/exam need a later contract')


def immutable(path,value):
    value=json.loads(canonical(value))
    if path.exists():
        if read(path)!=value:raise RuntimeError('immutable receipt differs: '+str(path))
    else:atomic(path,value)


def integrity():
    return FunctionType(previous.integrity.__code__,dict(previous.integrity.__globals__,**globals()))()


def status(stage,**fields):
    value=dict(at=now(),condition='S6-B22-VS',stage=stage,**fields)
    atomic(ROOT/'status.json',value)
    print(canonical(value),flush=True)


def allocation(namespace):
    if namespace.startswith('v-'):return 'V'
    if namespace.startswith('s-'):return 'S'
    for arm in search.KINDS:
        if namespace.startswith('final-'+arm+'-'):return 'FINAL-'+arm
    raise ValueError('undeclared budget namespace')


def reserve_tasks(tasks,namespace,label):
    """Reserve before work; reuse only jobs that never started or have a valid cache."""
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'budget.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=ROOT/'budget.json'
        ledger=read(path) if path.exists() else dict(cap=MAX_GAMES,scheduled_games=0,jobs=[])
        group=allocation(namespace)
        existing={x['task_id']:x for x in ledger['jobs']}
        additions=[t for t in tasks if t['task_id'] not in existing]
        used=sum(x['allocation']==group for x in ledger['jobs'])
        if ledger['scheduled_games']+len(additions)>MAX_GAMES or used+len(additions)>CAPS[group]:
            raise RuntimeError('preregistered allocation exhausted')
        for task in additions:
            item=dict(task,job_id=len(ledger['jobs']),allocation=group,namespace=namespace,label=label,reserved_at=now())
            ledger['jobs'].append(item);existing[task['task_id']]=item
        ledger['scheduled_games']=len(ledger['jobs'])
        atomic(path,ledger)
        return [existing[t['task_id']] for t in tasks]


def play_one(job):
    policy,spec,directory,dest,task=job;spec=tuple(spec)
    if spec not in DEVELOPMENT+V_NEW+S_NEW or (directory is not None and spec not in A):
        raise ValueError('undeclared case or protected observation')
    started=ROOT/'executions/started'/f"{task['job_id']:06d}.json"
    if started.exists():raise RuntimeError('started job cannot silently retry')
    atomic(started,dict(job_id=task['job_id'],task_id=task['task_id'],at=now(),pid=os.getpid()))
    native=FunctionType(engine.play_one.__code__,dict(engine.play_one.__globals__,ROOT=ROOT,
                        A=DEVELOPMENT,B=V_NEW+S_NEW,EXAM_SEEDS=(),evidence=timeline))
    wall=time.monotonic();cpu=time.process_time()
    try:
        row=json.loads(canonical(native((policy,spec,directory))))
        saved=dict(key=task['key'],digest=sha(row),record=row,job_id=task['job_id'])
        atomic(Path(dest),saved)
        metric=dict(job_id=task['job_id'],task_id=task['task_id'],namespace=task['namespace'],
                    case=spec,elapsed=time.monotonic()-wall,cpu_seconds=time.process_time()-cpu,
                    max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,record_sha256=sha(row),at=now())
        atomic(ROOT/'executions/completed'/f"{task['job_id']:06d}.json",metric)
        if directory:shutil.rmtree(directory)
        return row,metric
    except BaseException as exc:
        atomic(ROOT/'executions/failed'/f"{task['job_id']:06d}.json",
               dict(job_id=task['job_id'],task_id=task['task_id'],at=now(),reason=type(exc).__name__+': '+str(exc)))
        raise


def partition_name(specs):
    for name,expected in (('micro',A),('broad',DEVELOPMENT),('v-new',V_NEW),('s-new',S_NEW)):
        if specs==expected:return name
    raise ValueError('complete declared partition required')


def check_permit(policy,specs):
    name=partition_name(specs)
    if name not in ('v-new','s-new'):return
    path=ROOT/'permits'/(name+'.json')
    if not path.exists():raise ValueError('protection closed')
    permit=read(path)
    if permit['profile_sha256']!=sha(integrity()) or sha(policy) not in permit['policies'] or permit['cohort_sha256']!=sha(specs):
        raise ValueError('unregistered protected policy')


def measure(namespace,label,policy,specs,replay=False):
    specs=list(map(tuple,specs));partition_name(specs);check_permit(policy,specs)
    if not namespace or any(x in namespace for x in ('/','..')) or '..' in label:
        raise ValueError('invalid measurement path')
    allocation(namespace)
    stem=namespace.removesuffix('-audit')
    expected=(A if stem=='v-micro' or stem.startswith('s-') else
              V_NEW if stem=='v-new' else S_NEW if stem.startswith('final-') and stem.endswith('-new') else
              DEVELOPMENT if stem=='v-broad' or stem.startswith('final-') and stem.endswith('-broad') else None)
    if specs!=expected:raise ValueError('cohort does not belong to phase namespace')
    manifest=integrity();records={};pending=[]
    partition='replay' if replay else 'main';observed=specs==A
    for spec in specs:
        key=sha(dict(profile=sha(manifest),namespace=namespace,policy=policy,spec=spec,observed=observed))
        dest=ROOT/namespace/'cache'/partition/(key+'.json')
        if dest.exists():
            cached=read(dest)
            if cached['key']!=key or cached['digest']!=sha(cached['record']):raise RuntimeError('cache checksum mismatch')
            if not (ROOT/'executions/completed'/f"{cached['job_id']:06d}.json").exists():
                raise RuntimeError('cache without completed execution receipt')
            records[spec]=cached['record'];continue
        directory=ROOT/namespace/'journals'/partition/key if observed else None
        pending.append(dict(task_id=sha([namespace,partition,key]),key=key,spec=spec,
                            policy_sha256=sha(policy),cache=str(dest.relative_to(ROOT)),
                            journal=str(directory.relative_to(ROOT)) if directory else None))
    if pending:
        tasks=reserve_tasks(pending,namespace,label)
        for task in tasks:
            if (ROOT/'executions/started'/f"{task['job_id']:06d}.json").exists():
                raise RuntimeError('interrupted game; explicit recovery required')
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn'),
                                 initializer=previous.previous.worker_init) as pool:
            futures={pool.submit(play_one,(policy,task['spec'],str(ROOT/task['journal']) if task['journal'] else None,
                                          str(ROOT/task['cache']),task)):task for task in tasks}
            for n,future in enumerate(as_completed(futures),1):
                task=futures[future];row,metric=future.result();records[tuple(task['spec'])]=row
                if n%4==0 or n==len(tasks):
                    status('MEASURING',namespace=namespace,label=label,completed=n,total=len(tasks),
                           replay=replay,audit=namespace.endswith('-audit'))
    rows=[records[s] for s in specs]
    result=dict(rows=rows,levels=sum(r['levels_completed'] for r in rows),
                score=sum(r['score'] for r in rows),trace_digest=sha(rows))
    atomic(ROOT/namespace/'measurements'/(label+'.json'),result)
    return result


def persist_input(inputs):
    data=canonical(inputs).encode();digest=hashlib.sha256(data).hexdigest()
    path=ROOT/'investigator-inputs'/(digest+'.json.gz')
    if path.exists():
        if gzip.decompress(path.read_bytes())!=data:raise RuntimeError('input bytes changed')
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix('.tmp');tmp.write_bytes(gzip.compress(data,mtime=0));os.replace(tmp,path)
    return search.from_bytes(data),digest


def audit_measure(task_path):
    task=read(task_path);integrity()
    if task.get('request_receipt'):
        receipt=read(ROOT/task['request_receipt'])
        data=gzip.decompress((ROOT/'investigator-inputs'/(receipt['input_sha256']+'.json.gz')).read_bytes())
        if hashlib.sha256(data).hexdigest()!=receipt['input_sha256']:raise RuntimeError('input hash changed')
        request=search.from_bytes(data)
        if request!=receipt['request'] or sha(request)!=receipt['request_sha256']:raise RuntimeError('independent request differs')
        inputs=json.loads(data)
        policy=engine.strategy(program=engine.patch.append(inputs['policy']['program'],request['proposal']))
        if policy!=task['policy']:raise RuntimeError('policy differs from audited proposal')
    ns=task['namespace'];label=task['label']
    result=measure(ns+'-audit',label,task['policy'],task['specs'])
    original=read(ROOT/ns/'measurements'/(label+'.json'))
    if result!=original:raise RuntimeError('independent trajectory differs')
    immutable(ROOT/ns/'audits'/(label+'.json'),dict(valid=True,measurement_sha256=sha(original),
              task_sha256=sha(task),independent_execution=True,profile_sha256=sha(integrity())))


def triple(namespace,label,policy,specs,request_receipt=None):
    result=measure(namespace,label,policy,specs)
    replay=measure(namespace,label+'/replay',policy,specs,True)
    if replay!=result:raise RuntimeError('replay differs')
    task=dict(namespace=namespace,label=label,policy=policy,specs=specs,request_receipt=request_receipt)
    path=ROOT/'audit-tasks'/(sha(task)+'.json');immutable(path,task)
    receipt=ROOT/namespace/'audits'/(label+'.json')
    if not receipt.exists():
        subprocess.run([sys.executable,'-u','-m','seed.s6b22','audit-measure',str(path)],check=True)
    audited=read(receipt)
    if not audited['valid'] or audited['measurement_sha256']!=sha(result) or audited['task_sha256']!=sha(task):
        raise RuntimeError('audit receipt mismatch')
    if read(ROOT/(namespace+'-audit')/'measurements'/(label+'.json'))!=result:
        raise RuntimeError('audit measurement changed')
    return result


def passes(delta,retention=False):
    return not delta['loss_indices'] and (retention or delta['gain']>=2)


def evaluate(name,index,req,receipt,policy,base):
    proposal=search.validate_proposal(validate_answer(search.answer(req),req['guard_schema']))
    candidate=engine.strategy(program=engine.patch.append(policy['program'],proposal))
    after=triple('s-'+name,f'candidate/{index:03d}',candidate,A,receipt)
    delta=difference(base,after)
    behavior=sha([{k:r[k] for k in ('version','seed','rep','actions','frames','automatic_reset_indices')} for r in after['rows']])
    return dict(id=index+1,type=req['type'],target_id=req['target_id'],schedule=req['schedule'],
                base_sha256=sha(policy),proposal=proposal,candidate=candidate,proposal_sha256=sha(proposal),
                policy_sha256=sha(candidate),A=delta,levels=after['levels'],behavior_sha256=behavior,
                trajectory_sha256=after['trace_digest'],development=guard_search.comparison(base,after,'HOLD'),
                verdict='A_ONLY_PASS' if passes(delta) else 'V3',audited=True,
                usage=dict(model_calls=0,input_tokens=0,output_tokens=0))


def micro():
    fixture=read(INPUT/'baseline.json');policy=fixture['policy'];winners={};cells=[];runs={}
    for name,kind,seed in CELLS:
        base=triple('s-'+name,'baseline',policy,A)
        if sha(timeline.legacy_rows(base['rows']))!=fixture['screen_trace_sha256']:
            raise RuntimeError('baseline parity mismatch')
        history=[]
        for index in range(18):
            inputs=dict(policy=policy,base=base,own_history=history,kind=kind,index=index,seed=seed)
            started=time.monotonic();cpu=time.process_time()
            req,digest=persist_input(inputs)
            relative=f'requests/{name}/{index:03d}.json'
            immutable(ROOT/relative,dict(request=req,input_sha256=digest,request_sha256=sha(req),profile_sha256=sha(integrity())))
            path=ROOT/'steps'/name/f'{index:03d}.json'
            if path.exists():
                saved=read(path)
                if saved['input_sha256']!=digest or saved['request_sha256']!=sha(req):raise RuntimeError('resumed request changed')
                event=evaluate(name,index,req,relative,policy,base)
                if event!=saved['event']:raise RuntimeError('resumed event differs')
            else:
                elapsed=time.monotonic()-started;cpu_elapsed=time.process_time()-cpu
                event=evaluate(name,index,req,relative,policy,base)
                immutable(path,dict(event=event,input_sha256=digest,request_sha256=sha(req),profile_sha256=sha(integrity()),
                          search_seconds=elapsed,search_cpu_seconds=cpu_elapsed))
                visible=dict(event,id=index)
                visible['A']=dict(event['A'],before_levels=base['levels'],after_levels=event['levels'])
                journal(ROOT/'live/journal.jsonl',dict(kind='verdict',arm=name,**visible))
            history.append(event)
            cell=dict(arm=name,slot=index+1,verdict=event['verdict'],diff=event['A'],levels=event['levels'])
            cells.append(cell);status('S_MICRO_RESULT',**cell)
            if event['verdict']=='A_ONLY_PASS':
                winners[name]=dict(slot=index+1,policy=event['candidate'],policy_sha256=event['policy_sha256'])
                break
        repaired={e['target_id'] for e in history if e['schedule']['phase']=='repair'}
        runs[name]=dict(attempts=len(history),repairs=sum(e['schedule']['phase']=='repair' for e in history),
                        unserved_at_close=[dict(parent_id=e['id'],reason='first-pass stop' if name in winners else 'run budget exhausted')
                                           for e in search.eligible(history) if e['id'] not in repaired],
                        distinct_proposals=len({e['proposal_sha256'] for e in history}),
                        distinct_behaviors=len({e['behavior_sha256'] for e in history}))
    result=dict(valid=True,cells=cells,runs=runs,winners=winners,profile_sha256=sha(integrity()),s6_green=False,exam_opened=False)
    immutable(ROOT/'micro.json',result)
    return result


def select_finalists(winners):
    return {kind:dict(winners[name],arm=name) for kind in search.KINDS
            if (name:=next((f'{kind}-{seed}' for seed in SEEDS if f'{kind}-{seed}' in winners),None)) is not None}


def validate_pair(namespace,policy,specs,retention=False):
    base=triple(namespace,'baseline',read(INPUT/'baseline.json')['policy'],specs)
    after=triple(namespace,'candidate',policy,specs)
    delta=difference(base,after)
    result=dict(valid=True,passed=passes(delta,retention),diff=delta,
                base_levels=base['levels'],levels=after['levels'],base_sha256=sha(read(INPUT/'baseline.json')['policy']),
                policy_sha256=sha(policy),cohort_sha256=sha(specs),audited=True,
                changed_action_cases=sum(b['actions']!=a['actions'] for b,a in zip(base['rows'],after['rows'])),
                activation_count=None,activation_note='protected/broad instrumentation disabled; action changes only')
    immutable(ROOT/(namespace+'.json'),result)
    return result


def permit(name,policies,qualification):
    if name not in ('v-new','s-new'):raise ValueError('unknown protected partition')
    specs=V_NEW if name=='v-new' else S_NEW
    base=read(INPUT/'baseline.json')['policy']
    if not (ROOT/'finalists.json').exists():raise RuntimeError('freeze selector finalists before protected outcomes')
    if name=='v-new':
        result=read(ROOT/'v-broad.json')
        expected={'v-broad':sha(result)}
        allowed={result['policy_sha256']} if result['passed'] and result['audited'] else set()
    else:
        expected={};allowed=set()
        for kind,item in read(ROOT/'finalists.json')['selection'].items():
            result=read(ROOT/('final-'+kind+'-broad.json'))
            if result['passed'] and result['audited']:
                if result['policy_sha256']!=sha(item['policy']):raise RuntimeError('finalist changed')
                expected[kind]=sha(result);allowed.add(result['policy_sha256'])
    if qualification!=expected or {sha(p) for p in policies}!=allowed or not allowed:
        raise RuntimeError('protected permit requires exact audited qualification')
    value=dict(profile_sha256=sha(integrity()),cohort_sha256=sha(specs),
               policies=sorted({sha(base)}|{sha(p) for p in policies}),qualification=qualification,
               finalists_sha256=sha(read(ROOT/'finalists.json')))
    immutable(ROOT/'permits'/(name+'.json'),value)


def follow():
    integrity()
    lock=(ROOT/'pipeline.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (ROOT/'closed.json').exists():return
    winner=read(INPUT/'winner.json')['policy']
    reproduction=validate_pair('v-micro',winner,A)
    expected=read(INPUT/'b21-reference.json')
    for label in ('baseline','candidate'):
        if read(ROOT/'v-micro/measurements'/(label+'.json'))!=expected[label]:
            raise RuntimeError('B21 exact reproduction differs')
    if not reproduction['passed']:raise RuntimeError('B21 known pass not reproduced')
    broad=validate_pair('v-broad',winner,DEVELOPMENT)
    immutable(ROOT/'validation-provisional.json',dict(status='RUNNING' if broad['passed'] else 'FAIL',
              broad_passed=broad['passed'],new_cases='NOT_RUN',s6_green=False))
    results=micro()
    finalists=select_finalists(results['winners'])
    immutable(ROOT/'finalists.json',dict(selection=finalists,seed_priority=SEEDS,micro_sha256=sha(results)))
    vpass=False
    if broad['passed']:
        permit('v-new',[winner],{'v-broad':sha(read(ROOT/'v-broad.json'))})
        vpass=validate_pair('v-new',winner,V_NEW,True)['passed']
    immutable(ROOT/'validation.json',dict(valid=True,status='PASS' if vpass else 'FAIL',
              broad_passed=broad['passed'],new_cases='PASS' if vpass else 'FAIL' if broad['passed'] else 'NOT_RUN',s6_green=False))
    qualified={};transfer={}
    for kind,item in finalists.items():
        result=validate_pair('final-'+kind+'-broad',item['policy'],DEVELOPMENT)
        transfer[kind]=dict(broad='PASS' if result['passed'] else 'FAIL',new_cases='NOT_RUN')
        if result['passed']:qualified[kind]=item
    if qualified:
        permit('s-new',[i['policy'] for i in qualified.values()],
               {k:sha(read(ROOT/('final-'+k+'-broad.json'))) for k in qualified})
        for kind,item in qualified.items():
            ok=validate_pair('final-'+kind+'-new',item['policy'],S_NEW,True)['passed']
            transfer[kind]['new_cases']='PASS' if ok else 'FAIL'
    from seed.s6b22_review import review,paired_summary
    summary=paired_summary(results['winners'],SEEDS)
    immutable(ROOT/'selector.json',dict(valid=True,status='INCONCLUSIVE',pilot=summary,transfer=transfer,
              confirmation='NOT_RUN',s6_green=False))
    receipt=review(ROOT,INPUT/'manifest.json')
    closed=dict(valid=receipt['valid'],V=read(ROOT/'validation.json')['status'],S='INCONCLUSIVE',N='NOT_RUN',E='NOT_RUN',
                s6_green=False,exam_opened=False,physical_games=receipt['completed_games'],
                reason='V/S pilot finished; selector confirmation and N/E need separate contracts',at=now())
    immutable(ROOT/'closed.json',closed);status('CLOSED',**{k:v for k,v in closed.items() if k!='at'})


def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['follow']:follow()
        elif len(args)==2 and args[0]=='audit-measure':audit_measure(Path(args[1]))
        else:raise ValueError('use follow or audit-measure TASK')
    except BaseException as exc:
        status('INVALID',reason=type(exc).__name__+': '+str(exc),s6_green=False)
        raise


if __name__=='__main__':
    from seed import s6b22
    s6b22.main(sys.argv[1:])
