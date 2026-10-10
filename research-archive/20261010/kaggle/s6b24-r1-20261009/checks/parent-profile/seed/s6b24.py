"""B24 repaired and cooperative researcher diagnostic. Never opens the S6 exam."""
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from types import FunctionType

from seed import s6b22 as old
from seed import s6b24_preflight as preflight
from seed import s6b24_model as model
from echo_arc import s6b24_search as search, guard_search

REPO=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('ECHO_B24_ROOT',str(REPO/'lab/seed/s6b24-20261009')))
INPUT=Path(os.environ.get('ECHO_B24_INPUT',str(ROOT/'input')))
A=old.A+[(3,62004,0,2000),(3,62014,0,2000)]
DEVELOPMENT=old.DEVELOPMENT
V_NEW=[(v,s,0,2000) for v in (2,3) for s in range(67000,67040)]
S_NEW=[]
SEED=824101
CELLS=tuple(random.Random(824000).sample(('R4-REF','B24-G','B24-S','B24-I','B24-C'),5))
WORKERS=4
CAPS={**{'S-'+k:798 for k in search.KINDS},'BROAD':2880,'NEW':1440}
MAX_GAMES=sum(CAPS.values())
read,atomic,file_sha,now=old.read,old.atomic,old.file_sha,old.now
sha,canonical,journal=old.sha,old.canonical,old.journal
immutable,engine,difference,timeline=old.immutable,old.engine,old.difference,old.timeline
passes=old.passes
previous=old.previous


def config():
    return dict(condition='S6-B24',screen=A,development=DEVELOPMENT,retention=V_NEW,
                cells=CELLS,seed=SEED,order_seed=824000,workers=WORKERS,rounds=18,
                allocations=CAPS,max_games=MAX_GAMES,search=search.config(),model=model.config(),
                epsilon=1e-10,per_game_timeout_seconds=240,first_pass=True,
                protected_feedback=False,exam_allowed=False,paid=False,private=True,
                acceptance='>=2 levels and no individual level/score loss; retention no loss',
                calibration='first arm baseline triple, included in budget',
                scope='one paired search seed, diagnostic only; no statistical superiority claim')


def integrity():
    if sys.flags.optimize:raise RuntimeError('optimized Python disables inherited audit checks')
    m=read(INPUT/'manifest.json')
    if m.get('execution_root')!=str(ROOT.resolve()):raise RuntimeError('runtime path changed')
    from importlib.metadata import version
    if ('.'.join(map(str,sys.version_info[:3])),version('numpy'),version('arcengine')) != (m['python'],m['numpy'],m['arcengine']):
        raise RuntimeError('frozen runtime changed')
    if m['configuration']!=json.loads(canonical(config())): raise RuntimeError('configuration changed')
    for name,h in m['sources'].items():
        if file_sha(REPO/name)!=h: raise RuntimeError('frozen source changed: '+name)
    for name,h in m['inputs'].items():
        if file_sha(INPUT/name)!=h: raise RuntimeError('input changed: '+name)
    return m


def status(stage,**fields):
    record=dict(at=now(),condition='S6-B24',stage=stage,**fields)
    atomic(ROOT/'status.json',record);print(canonical(record),flush=True)


def allocation(namespace):
    stem=namespace.removesuffix('-audit')
    if stem.startswith('s-') and stem[2:] in search.KINDS: return 'S-'+stem[2:]
    if stem=='v-broad': return 'BROAD'
    if stem=='v-new': return 'NEW'
    raise ValueError('undeclared budget namespace')


def partition_name(specs):
    for name,expected in (('micro',A),('broad',DEVELOPMENT),('v-new',V_NEW)):
        if list(map(tuple,specs))==expected:return name
    raise ValueError('complete declared partition required')


def check_permit(policy,specs):
    name=partition_name(specs)
    if name!='v-new': return
    path=ROOT/'permits/v-new.json'
    if not path.exists(): raise ValueError('protection closed')
    receipt=read(path)
    if receipt['profile_sha256']!=sha(integrity()) or receipt['cohort_sha256']!=sha(V_NEW) or sha(policy) not in receipt['policies']:
        raise ValueError('unregistered protected policy')
    if receipt['finalists_sha256']!=sha(read(ROOT/'finalists.json')): raise ValueError('finalists changed')


def reuse(function,*args,**kwargs):
    # Reuse the audited game/cache implementation with private B23 globals.
    scope=dict(function.__globals__,**globals())
    return FunctionType(function.__code__,scope,function.__name__,function.__defaults__)(*args,**kwargs)


def reserve_tasks(tasks,namespace,label):
    preflight.verify(ROOT,read(INPUT/'models.json'),sha(integrity()))
    scoped=[dict(t,execution_root=str(ROOT.resolve()),input_root=str(INPUT.resolve())) for t in tasks]
    return reuse(old.reserve_tasks,scoped,namespace,label)


def play_one(job):
    global ROOT,INPUT
    policy,spec,directory,dest,task=job
    if tuple(spec) not in DEVELOPMENT+V_NEW or (directory is not None and tuple(spec) not in A):
        raise ValueError('undeclared case or protected observation')
    # spawn imports a fresh module: parent globals alone do not propagate.
    ROOT=Path(task['execution_root']);INPUT=Path(task['input_root'])
    if not Path(dest).resolve().is_relative_to(ROOT.resolve()):raise ValueError('cache outside execution root')
    if directory and not Path(directory).resolve().is_relative_to(ROOT.resolve()):raise ValueError('journal outside execution root')
    return reuse(old.play_one,job)
def measure(namespace,label,policy,specs,replay=False):
    if not (ROOT/namespace/'measurements'/(label+'.json')).exists():checkpoint('before measurement '+namespace+'/'+label)
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
        key=sha(dict(profile=sha(manifest),namespace=namespace,policy=policy,spec=spec,observed=observed,
                      evaluation=label.removesuffix('/replay')))
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


def persist_input(inputs): return reuse(old.persist_input,inputs)


def verify_request(relative):
    receipt=read(ROOT/relative)
    data=gzip.decompress((ROOT/'investigator-inputs'/(receipt['input_sha256']+'.json.gz')).read_bytes())
    if hashlib.sha256(data).hexdigest()!=receipt['input_sha256']: raise RuntimeError('investigator input changed')
    req=search.from_bytes(data)
    if req!=receipt['request'] or sha(req)!=receipt['request_sha256']: raise RuntimeError('request reconstruction differs')
    return req,json.loads(data)


def proposal_for(req,inputs):
    if req['model_call_required']:
        folder=ROOT/'calls'/inputs['kind']/f"{inputs['index']:03d}"
        result=model.load(folder,req,inputs['kind'],SEED+inputs['index'],sha(integrity()))
        expected=model.command(read(INPUT/'models.json')['N7'],folder/'prompt.txt',SEED+inputs['index'],req)
        if read(folder/'command.json')!=expected: raise RuntimeError('model command differs')
        return result['proposal'],result['usage'],result['error']
    return (search.validate_proposal(req['proposal']) if req.get('proposal') else None),dict(model_calls=0,input_tokens=0,output_tokens=0),None


def audit_measure(task_path):
    task=read(task_path); integrity()
    if task.get('request_receipt'):
        req,inputs=verify_request(task['request_receipt'])
        proposal,_,_=proposal_for(req,inputs)
        if proposal is None: raise RuntimeError('invalid proposal cannot execute')
        policy=engine.strategy(program=engine.patch.append(inputs['policy']['program'],proposal))
        if policy!=task['policy']: raise RuntimeError('policy differs from submitted proposal')
    ns,label=task['namespace'],task['label']
    result=measure(ns+'-audit',label,task['policy'],task['specs'])
    original=read(ROOT/ns/'measurements'/(label+'.json'))
    if result!=original: raise RuntimeError('independent trajectory differs')
    immutable(ROOT/ns/'audits'/(label+'.json'),dict(valid=True,measurement_sha256=sha(original),
              task_sha256=sha(task),independent_execution=True,profile_sha256=sha(integrity())))


def triple(namespace,label,policy,specs,request_receipt=None):
    result=measure(namespace,label,policy,specs)
    replay=measure(namespace,label+'/replay',policy,specs,True)
    if replay!=result: raise RuntimeError('replay differs')
    task=dict(namespace=namespace,label=label,policy=policy,specs=specs,request_receipt=request_receipt)
    path=ROOT/'audit-tasks'/(sha(task)+'.json');immutable(path,task)
    receipt=ROOT/namespace/'audits'/(label+'.json')
    if not receipt.exists():
        checkpoint('before independent audit '+namespace+'/'+label)
        env=dict(os.environ,ECHO_B24_ROOT=str(ROOT),ECHO_B24_INPUT=str(INPUT),ECHO_B24_DEADLINE_EPOCH='')
        subprocess.run([sys.executable,'-u','-m','seed.s6b24','audit-measure',str(path)],env=env,check=True)
    saved=read(receipt)
    if not saved['valid'] or saved['measurement_sha256']!=sha(result) or saved['task_sha256']!=sha(task):
        raise RuntimeError('audit receipt mismatch')
    if read(ROOT/(namespace+'-audit')/'measurements'/(label+'.json'))!=result: raise RuntimeError('audit measurement changed')
    return result


def parity(base):
    expected=read(INPUT/'baseline.json')['behavior']
    actual=[{k:r[k] for k in expected[0]} for r in base['rows']]
    if actual!=expected or base['levels']!=61: raise RuntimeError('B23 baseline parity mismatch')


def event_for(arm,index,req,receipt,inputs,base):
    policy=inputs['policy'];proposal,usage,error=proposal_for(req,inputs)
    event=dict(id=index+1,type=req['type'],target_id=req['target_id'],schedule=req['schedule'],
               base_sha256=sha(policy),proposal=proposal,usage=usage,
               author=req['schedule'].get('author',0),round=req['schedule'].get('round',index//6),slot=index)
    if proposal is None:
        return dict(event,verdict='NO_ELIGIBLE_CANDIDATE',error=req.get('abstention',error),audited=True)
    if any(e.get('proposal')==proposal for e in search.visible_history(arm,index,SEED,inputs['own_history'])):
        return dict(event,verdict='DUPLICATE',error='exact prior proposal; slot consumed',audited=True)
    if not (ROOT/'steps'/arm/f'{index:03d}.json').exists():
        status('RESEARCH_PROPOSAL',arm=arm,slot=index+1,author=event['author'],
               mode=req['schedule']['phase'],parent_id=req['target_id'],proposal=proposal)
    candidate=engine.strategy(program=engine.patch.append(policy['program'],proposal))
    after=triple('s-'+arm,f'candidate/{index:03d}',candidate,A,receipt)
    change=difference(base,after)
    return dict(event,candidate=candidate,proposal_sha256=sha(proposal),policy_sha256=sha(candidate),
                A=change,levels=after['levels'],trajectory_sha256=after['trace_digest'],
                development=guard_search.comparison(base,after,'HOLD'),
                actions_per_level=[r['actions_per_level'] for r in after['rows']],
                verdict='A_ONLY_PASS' if passes(change) else 'V3',audited=True)


@contextmanager
def slot_timing(arm,index):
    """Durable cumulative wall/parent CPU, including reconstruction and safe cuts."""
    wall=time.monotonic();cpu=time.process_time()
    try:
        yield
    finally:
        path=ROOT/'timings'/arm/f'{index:03d}.json'
        elapsed=time.monotonic()-wall;used=time.process_time()-cpu
        value=read(path) if path.exists() else dict(arm=arm,slot=index,segments=[])
        if value['arm']!=arm or value['slot']!=index:raise RuntimeError('timing scope differs')
        exc=sys.exc_info()[0]
        value['segments'].append(dict(seconds=elapsed,cpu_seconds=used,
                exit='complete' if exc is None else 'checkpoint' if issubclass(exc,SliceComplete) else 'failure'))
        atomic(path,value)


def timing_totals(arm,index):
    rows=read(ROOT/'timings'/arm/f'{index:03d}.json')['segments']
    return dict(seconds=sum(x['seconds'] for x in rows),cpu_seconds=sum(x['cpu_seconds'] for x in rows),segments=len(rows))


def micro(registry):
    policy=read(INPUT/'baseline.json')['policy'];winners={};cells=[]
    for arm in CELLS:
        checkpoint('before baseline '+arm)
        started=time.monotonic()
        base=triple('s-'+arm,'baseline',policy,A);parity(base)
        if arm==CELLS[0] and not (ROOT/'estimate.json').exists():
            elapsed=time.monotonic()-started
            immutable(ROOT/'estimate.json',dict(at=now(),baseline_triple_seconds=elapsed,
                       physical_games=42,remaining_micro_game_upper_estimate_seconds=elapsed*94,
                       warning='upper micro only, baseline projection; candidates and inference differ; excludes conditional broad/retention',model_seconds=None))
        history=[]
        for index in range(search.ROUNDS):
            if not (ROOT/'steps'/arm/f'{index:03d}.json').exists():checkpoint('before '+arm+' '+str(index))
            inputs=dict(policy=policy,base=base,own_history=search.visible_history(arm,index,SEED,history),kind=arm,index=index,seed=SEED)
            with slot_timing(arm,index):
                req,digest=persist_input(inputs)
                relative=f'requests/{arm}/{index:03d}.json'
                immutable(ROOT/relative,dict(request=req,input_sha256=digest,request_sha256=sha(req),profile_sha256=sha(integrity())))
                step=ROOT/'steps'/arm/f'{index:03d}.json'
                if not step.exists():
                    journal(ROOT/'live/journal.jsonl',dict(kind='request',arm=arm,id=index,request=req))
                if req['model_call_required']:
                    status('NEOCORTEX',arm=arm,slot=index+1,total_slots=18)
                    model.propose(ROOT,registry,arm,index,req,SEED+index,sha(integrity()))
                event=event_for(arm,index,req,relative,inputs,base)
            if step.exists():
                saved=read(step)
                if saved['event']!=event or saved['input_sha256']!=digest or saved['request_sha256']!=sha(req):
                    raise RuntimeError('resumed event differs')
            else:
                immutable(step,dict(event=event,input_sha256=digest,request_sha256=sha(req),
                          seconds=timing_totals(arm,index)['seconds'],cpu_seconds=timing_totals(arm,index)['cpu_seconds'],
                          timing_receipt=f'timings/{arm}/{index:03d}.json'))
                journal(ROOT/'live/journal.jsonl',dict(kind='verdict',arm=arm,**event))
            history.append(event)
            cell=dict(arm=arm,slot=index+1,verdict=event['verdict'],diff=event.get('A'))
            cells.append(cell);status('MICRO_RESULT',**cell)
            if event['verdict']=='A_ONLY_PASS':
                winners[arm]=dict(slot=index+1,policy=event['candidate'],policy_sha256=event['policy_sha256'])
                break
    result=dict(valid=True,cells=cells,winners=winners,profile_sha256=sha(integrity()),s6_green=False,exam_opened=False)
    immutable(ROOT/'micro.json',result);return result


def validate_finalist(arm,policy,specs,retention=False):
    namespace='v-new' if retention else 'v-broad'
    base=triple(namespace,'baseline',read(INPUT/'baseline.json')['policy'],specs)
    after=triple(namespace,'candidate/'+arm,policy,specs)
    change=difference(base,after)
    result=dict(valid=True,passed=passes(change,retention),diff=change,policy_sha256=sha(policy),
                cohort_sha256=sha(specs),audited=True,base_levels=base['levels'],levels=after['levels'])
    immutable(ROOT/'validation'/namespace/(arm+'.json'),result);return result


def permit(qualified):
    frozen=read(ROOT/'finalists.json');allowed=[];proof={}
    for arm,item in frozen['selection'].items():
        result=read(ROOT/'validation/v-broad'/(arm+'.json'))
        if result['passed'] and result['audited'] and result['policy_sha256']==sha(item['policy']):
            allowed.append(arm);proof[arm]=sha(result)
    if not allowed or set(allowed)!=set(qualified): raise RuntimeError('exact broad qualification required')
    exposure=read(INPUT/'exposure-registry.json')
    if not exposure['valid'] or exposure['cohort_sha256']!=sha(V_NEW): raise RuntimeError('unverified retention exposure')
    immutable(ROOT/'permits/v-new.json',dict(profile_sha256=sha(integrity()),cohort_sha256=sha(V_NEW),
              finalists_sha256=sha(frozen),qualification=proof,
              policies=sorted({sha(read(INPUT/'baseline.json')['policy'])}|{sha(frozen['selection'][k]['policy']) for k in allowed})))


def follow():
    integrity()
    with (ROOT/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/'closed.json').exists(): return read(ROOT/'closed.json')
        registry=read(INPUT/'models.json');model.verify_registry(registry)
        preflight.run(ROOT,registry,sha(integrity()),status)
        results=micro(registry)
        immutable(ROOT/'finalists.json',dict(selection=results['winners'],micro_sha256=sha(results)))
        transfer={};qualified=[]
        for arm,item in results['winners'].items():
            checkpoint('before broad '+arm)
            result=validate_finalist(arm,item['policy'],DEVELOPMENT)
            transfer[arm]=dict(broad='PASS' if result['passed'] else 'FAIL',retention='NOT_RUN')
            if result['passed']:qualified.append(arm)
        if qualified:
            permit(qualified)
            for arm in qualified:
                checkpoint('before retention '+arm)
                result=validate_finalist(arm,results['winners'][arm]['policy'],V_NEW,True)
                transfer[arm]['retention']='PASS' if result['passed'] else 'FAIL'
        immutable(ROOT/'transfer.json',transfer)
        from seed.s6b24_review import review
        audit=review(ROOT,INPUT/'manifest.json')
        closed=dict(valid=True,at=now(),s6_green=False,exam_opened=False,transfer=transfer,
                    physical_games=audit['completed_games'],model_calls=audit['model_calls'],format_calls=8,total_model_calls=audit['model_calls']+8,
                    result='DIAGNOSTIC_COMPLETE',confirmation='NOT_RUN',campaign='NOT_RUN',
                    promotion='a later SEMILLA contract is required')
        immutable(ROOT/'closed.json',closed);status('CLOSED',**{k:v for k,v in closed.items() if k!='at'})
        return closed


class SliceComplete(Exception):
    pass


def checkpoint(label):
    # Wall-time transport cut only. No stop/arm change based on scientific outcome.
    deadline=os.environ.get('ECHO_B24_DEADLINE_EPOCH')
    if deadline and time.time()>=float(deadline):
        raise SliceComplete(label)


def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['follow']:follow()
        elif len(args)==2 and args[0]=='audit-measure':audit_measure(Path(args[1]))
        else:raise ValueError('use follow or audit-measure TASK')
    except SliceComplete as exc:
        status('CHECKPOINT_READY',reason=str(exc),s6_green=False,exam_opened=False)
        return
    except BaseException as exc:
        status('INSTRUMENT_BLOCKED',reason=type(exc).__name__+': '+str(exc),s6_green=False)
        raise


if __name__=='__main__':
    from seed import s6b24
    s6b24.main(sys.argv[1:])
