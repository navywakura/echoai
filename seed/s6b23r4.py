"""B23-R4 two-model interface recovery, broad validation and sealed retention. Never opens S6."""
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
from seed import s6b23r4_preflight as preflight
from seed import s6b23r4_model as model
from echo_arc import s6b23r4_search as search, guard_search

REPO=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('ECHO_B23R4_ROOT',str(REPO/'lab/seed/s6b23r4-20261008')))
INPUT=Path(os.environ.get('ECHO_B23R4_INPUT',str(ROOT/'input')))
A=old.A+[(3,62004,0,2000),(3,62014,0,2000)]
DEVELOPMENT=old.DEVELOPMENT
V_NEW=[(v,s,0,2000) for v in (2,3) for s in range(67000,67040)]
S_NEW=[]
SEED=823101
CELLS=('N14','N7')
WORKERS=4
CAPS={**{'S-'+k:798 for k in search.KINDS},'BROAD':1440,'NEW':720}
MAX_GAMES=sum(CAPS.values())
read,atomic,file_sha,now=old.read,old.atomic,old.file_sha,old.now
sha,canonical,journal=old.sha,old.canonical,old.journal
immutable,engine,difference,timeline=old.immutable,old.engine,old.difference,old.timeline
passes=old.passes


def config():
    return dict(condition='S6-B23-R4',screen=A,development=DEVELOPMENT,retention=V_NEW,
                cells=CELLS,seed=SEED,order_seed=823000,workers=WORKERS,rounds=18,
                allocations=CAPS,max_games=MAX_GAMES,search=search.config(),model=model.config(),
                epsilon=1e-10,per_game_timeout_seconds=240,first_pass=True,
                protected_feedback=False,exam_allowed=False,paid=False,private=True,
                acceptance='>=2 levels and no individual level/score loss; retention no loss',
                calibration='first arm baseline triple, included in budget',
                scope='one paired search seed, diagnostic only; no statistical superiority claim')


def integrity():
    if sys.flags.optimize:raise RuntimeError('optimized Python disables inherited audit checks')
    m=read(INPUT/'manifest.json')
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
    record=dict(at=now(),condition='S6-B23-R4',stage=stage,**fields)
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
def measure(namespace,label,policy,specs,replay=False): return reuse(old.measure,namespace,label,policy,specs,replay)


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
        expected=model.command(read(INPUT/'models.json')[inputs['kind']],folder/'prompt.txt',SEED+inputs['index'])
        if read(folder/'command.json')!=expected: raise RuntimeError('model command differs')
        return result['proposal'],result['usage'],result['error']
    return search.validate_proposal(req['proposal']),dict(model_calls=0,input_tokens=0,output_tokens=0),None


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
        env=dict(os.environ,ECHO_B23R4_ROOT=str(ROOT),ECHO_B23R4_INPUT=str(INPUT))
        subprocess.run([sys.executable,'-u','-m','seed.s6b23r4','audit-measure',str(path)],env=env,check=True)
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
               base_sha256=sha(policy),proposal=proposal,usage=usage)
    if proposal is None:
        return dict(event,verdict='INVALID_PROPOSAL',error=error,audited=True)
    if arm in ('N7','N14') and any(e.get('proposal')==proposal for e in inputs['own_history']):
        return dict(event,verdict='DUPLICATE',error='exact prior proposal; slot consumed',audited=True)
    candidate=engine.strategy(program=engine.patch.append(policy['program'],proposal))
    after=triple('s-'+arm,f'candidate/{index:03d}',candidate,A,receipt)
    change=difference(base,after)
    return dict(event,candidate=candidate,proposal_sha256=sha(proposal),policy_sha256=sha(candidate),
                A=change,levels=after['levels'],trajectory_sha256=after['trace_digest'],
                development=guard_search.comparison(base,after,'HOLD'),
                actions_per_level=[r['actions_per_level'] for r in after['rows']],
                verdict='A_ONLY_PASS' if passes(change) else 'V3',audited=True)


def micro(registry):
    policy=read(INPUT/'baseline.json')['policy'];winners={};cells=[]
    for arm in CELLS:
        started=time.monotonic()
        base=triple('s-'+arm,'baseline',policy,A);parity(base)
        if arm==CELLS[0] and not (ROOT/'estimate.json').exists():
            elapsed=time.monotonic()-started
            immutable(ROOT/'estimate.json',dict(at=now(),baseline_triple_seconds=elapsed,
                       physical_games=42,remaining_micro_game_upper_estimate_seconds=elapsed*37,
                       warning='baseline only; candidates and model loading can differ; no inference ETA',model_seconds=None))
        history=[]
        for index in range(search.ROUNDS):
            inputs=dict(policy=policy,base=base,own_history=history,kind=arm,index=index,seed=SEED)
            start=time.monotonic();cpu=time.process_time();req,digest=persist_input(inputs)
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
                          seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu))
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
        registry=read(INPUT/'models.json');model.verify_pair(registry)
        preflight.run(ROOT,registry,sha(integrity()),status)
        results=micro(registry)
        immutable(ROOT/'finalists.json',dict(selection=results['winners'],micro_sha256=sha(results)))
        transfer={};qualified=[]
        for arm,item in results['winners'].items():
            result=validate_finalist(arm,item['policy'],DEVELOPMENT)
            transfer[arm]=dict(broad='PASS' if result['passed'] else 'FAIL',retention='NOT_RUN')
            if result['passed']:qualified.append(arm)
        if qualified:
            permit(qualified)
            for arm in qualified:
                result=validate_finalist(arm,results['winners'][arm]['policy'],V_NEW,True)
                transfer[arm]['retention']='PASS' if result['passed'] else 'FAIL'
        immutable(ROOT/'transfer.json',transfer)
        from seed.s6b23r4_review import review
        audit=review(ROOT,INPUT/'manifest.json')
        closed=dict(valid=True,at=now(),s6_green=False,exam_opened=False,transfer=transfer,
                    physical_games=audit['completed_games'],model_calls=audit['model_calls'],format_calls=8,total_model_calls=audit['model_calls']+8,
                    result='DIAGNOSTIC_COMPLETE',confirmation='NOT_RUN',campaign='NOT_RUN',
                    promotion='a later SEMILLA contract is required')
        immutable(ROOT/'closed.json',closed);status('CLOSED',**{k:v for k,v in closed.items() if k!='at'})
        return closed


def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['follow']:follow()
        elif len(args)==2 and args[0]=='audit-measure':audit_measure(Path(args[1]))
        else:raise ValueError('use follow or audit-measure TASK')
    except BaseException as exc:
        status('INSTRUMENT_BLOCKED',reason=type(exc).__name__+': '+str(exc),s6_green=False)
        raise


if __name__=='__main__':
    from seed import s6b23r4
    s6b23r4.main(sys.argv[1:])
