"""B21-A CPU experiment: reuse the frozen evaluator with an explicit adapter."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import gzip
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import FunctionType

from seed import s6b20 as b20
from seed.game_selfimprove import canonical, sha, journal
from echo_arc import s6b21_search as search, guard_search, consumption_timeline as timeline
from echo_arc.contrastive_grammar import validate_answer

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('ECHO_B21_ROOT', str(REPO/'lab/seed/s6b21-20261006')))
INPUT = Path(os.environ.get('ECHO_B21_INPUT', str(REPO/'lab/kaggle/s6b21-20261006/input')))
A = b20.A
DEVELOPMENT = b20.DEVELOPMENT
B = [(v,s,0,2000) for v in (2,3) for s in range(64000,64040)]
SEEDS = (821101,821117,821129)
_cells = [('B20','b20',0)] + [(f'{kind}-{s}',kind,s) for s in SEEDS for kind in ('random','balanced')]
search.rng(821000,'execution-order').shuffle(_cells)
CELLS = tuple(_cells)
ROUNDS, WORKERS, MAX_GAMES = 18,4,16000
read, atomic, file_sha, now = b20.read,b20.atomic,b20.file_sha,b20.now
previous, engine = b20.previous,b20.engine


def config():
    return dict(condition='S6-B21-A',screen=A,development=DEVELOPMENT,protected_B=B,
                cells=CELLS,seeds=SEEDS,rounds=ROUNDS,workers=WORKERS,max_games=MAX_GAMES,
                search=search.config(),model_calls_cap=0,exam_allowed=False,
                agendas={str(s):search.agenda(s) for s in SEEDS},
                actor='unchanged B20/B14 accepted base',protected_feedback=False,
                selection='first pass per cell; no reselection',scope='retrospective coverage diagnosis then new retention',
                max_expected_games=14868,private=True,paid=False,
                per_game_timeout_seconds=240,observer='existing development journal only')


def integrity():
    # Same runtime/source/input checks as B20, bound to this condition only.
    return FunctionType(b20.integrity.__code__, dict(b20.integrity.__globals__, **globals()))()


def status(stage, **fields):
    value=dict(at=now(),condition='S6-B21-A',stage=stage,**fields)
    atomic(ROOT/'status.json',value);print(canonical(value),flush=True)


def reserve(count, namespace, label):
    return FunctionType(b20.reserve.__code__,dict(b20.reserve.__globals__,**globals()))(count,namespace,label)


def play_one(job):
    policy,spec,directory=job;spec=tuple(spec)
    if spec not in DEVELOPMENT+B or (directory is not None and spec not in A):
        raise ValueError('unknown case or protected observation')
    native=FunctionType(engine.play_one.__code__,dict(engine.play_one.__globals__,ROOT=ROOT,
                        A=DEVELOPMENT,B=B,EXAM_SEEDS=(),evidence=timeline))
    started=time.monotonic()
    row=json.loads(canonical(native((policy,spec,directory))))
    return row,time.monotonic()-started


def measure(namespace,label,policy,specs,replay=False):
    if list(map(tuple,specs))==B and (ROOT/'retention-opened.json').exists():
        permit=read(ROOT/'retention-opened.json')
        allowed=set(permit['policies'].values())|{sha(read(INPUT/'baseline.json')['policy'])}
        if sha(policy) not in allowed or permit['profile_sha256']!=sha(integrity()):
            raise ValueError('unregistered protected policy')
    return FunctionType(b20.measure.__code__,dict(b20.measure.__globals__,**globals()))(namespace,label,policy,specs,replay)


def reproduced(namespace,label,policy,specs):
    a=measure(namespace,label,policy,specs)
    replay=measure(namespace,label+'/replay',policy,specs,True)
    if a!=replay:raise RuntimeError('replay mismatch; instrument blocked')
    return a


def investigator(inputs, audit=False):
    """Persist the exact data boundary, then give only those bytes to search."""
    data=canonical(inputs).encode();digest=hashlib.sha256(data).hexdigest()
    path=ROOT/'investigator-inputs'/(digest+'.json.gz')
    if path.exists():
        if gzip.decompress(path.read_bytes())!=data:raise RuntimeError('investigator input bytes changed')
    elif audit:
        raise RuntimeError('investigator input bytes missing')
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp')
        with temp.open('wb') as f:
            f.write(gzip.compress(data,mtime=0));f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    return search.from_bytes(data),digest


difference = b20.difference


def evaluate(ns,label,req,policy,base,history,audit):
    answer=search.answer(req)
    event=dict(id=req['id'],type=req['type'],target_id=req.get('target_id'),base_sha256=sha(policy),
               answer=answer,usage=dict(input_tokens=0,output_tokens=0,model_calls=0))
    proposal=validate_answer(answer,req['guard_schema'])
    if not proposal['patches']:
        return dict(event,verdict='V1',reason='finite search exhausted; logical slot consumed')
    proposal=search.validate_proposal(proposal)
    candidate=engine.strategy(program=engine.patch.append(policy['program'],proposal))
    after=measure(ns,label,candidate,A) if audit else reproduced(ns,label,candidate,A)
    if audit and after!=read(ROOT/ns.replace('audit-','micro-',1)/'measurements'/(label+'.json')):
        raise RuntimeError('independent full trajectory differs')
    delta=difference(base,after)
    development=guard_search.comparison(base,after,'HOLD')
    observations=search.baseline.points_for(base['rows'],history,policy)
    behavior=[{k:row[k] for k in ('version','seed','rep','actions','frames','automatic_reset_indices')}
              for row in after['rows']]
    return dict(event,proposal=proposal,candidate=candidate,A=delta,levels=after['levels'],
                proposal_sha256=sha(proposal),policy_sha256=sha(candidate),
                development=development,consumption_sha256=sha(development['candidate_consumers']),
                guard_observations_sha256=sha(observations),
                guard_signature_sha256=search.signature(proposal['patches'][0]['when'],observations),
                behavior_sha256=sha(behavior),
                trajectory_sha256=after['trace_digest'],
                verdict='A_ONLY_PASS' if previous.a_pass(delta) else 'V3')


def micro(audit=False):
    manifest=integrity();fixture=read(INPUT/'baseline.json');policy=fixture['policy']
    result=[];winners={}
    for name,kind,seed in CELLS:
        ns=('audit-' if audit else 'micro-')+name
        base=measure(ns,'baseline',policy,A) if audit else reproduced(ns,'baseline',policy,A)
        if sha(timeline.legacy_rows(base['rows']))!=fixture['screen_trace_sha256']:
            raise RuntimeError('baseline parity mismatch')
        if audit and base!=read(ROOT/('micro-'+name)/'measurements/baseline.json'):
            raise RuntimeError('independent baseline differs')
        history=[]
        for index in range(ROUNDS):
            inputs=dict(policy=policy,base=base,own_history=history,accepted_history=fixture['history'],
                        kind=kind,index=index,seed=seed)
            started=time.monotonic()
            req,input_digest=investigator(inputs,audit)
            search_elapsed=time.monotonic()-started
            path=ROOT/'steps'/name/f'{index:03d}.json'
            saved=read(path) if path.exists() else None
            receipt=dict(profile_sha256=sha(manifest),input_sha256=input_digest,request_sha256=sha(req))
            if saved and any(saved.get(k)!=v for k,v in receipt.items()):
                raise RuntimeError('request/input reconstruction changed')
            if saved and saved['request']!=req:raise RuntimeError('request changed')
            if audit and saved is None:raise RuntimeError('missing event for audit')
            event=evaluate(ns,f'candidate/{index:03d}',req,policy,base,history,audit) if audit or not saved else saved['event']
            if audit and event!=saved['event']:raise RuntimeError('independent event differs')
            if not audit:
                atomic(path,dict(request=req,event=event,**receipt))
                journal(ROOT/'search-metrics.jsonl',dict(arm=name,slot=index+1,elapsed=search_elapsed,
                    input_sha256=input_digest,reused=bool(saved),model_calls=0))
                visible=dict(event,id=event['id']-1)
                if event.get('A'):visible['A']=dict(event['A'],before_levels=base['levels'],after_levels=event['levels'])
                journal(ROOT/'live/journal.jsonl',dict(kind='verdict',arm=name,**visible))
            history.append(event)
            cell=dict(arm=name,slot=index+1,verdict=event['verdict'],levels=event.get('levels'),diff=event.get('A'))
            result.append(cell);status('AUDIT_RESULT' if audit else 'MICRO_RESULT',**cell)
            if event['verdict']=='A_ONLY_PASS':
                winners[name]=dict(slot=index+1,policy=event['candidate']);break
    value=dict(valid=True,cells=result,winners=winners,exam_opened=False,s6_green=False,profile_sha256=sha(manifest))
    if audit:
        if value!=read(ROOT/'micro.json'):raise RuntimeError('micro audit summary mismatch')
        value=dict(value,independent_execution=True,micro_sha256=sha(value))
    atomic(ROOT/('micro-audit.json' if audit else 'micro.json'),value)
    return value


def qualify(stage,audit=False):
    if stage not in ('qualification','retention'):raise ValueError('unknown phase')
    source='micro' if stage=='qualification' else 'qualification'
    before=read(ROOT/(source+'.json'));receipt=read(ROOT/(source+'-audit.json'))
    if not receipt['valid'] or receipt[source+'_sha256']!=sha(before):raise RuntimeError('prior audit missing or mismatched')
    selected=before['winners']
    if not any(n.startswith('balanced-') for n in selected):raise RuntimeError('no B21-A candidate eligible')
    specs=DEVELOPMENT if stage=='qualification' else B
    if stage=='retention':
        permit=dict(profile_sha256=sha(integrity()),policies={k:sha(v['policy']) for k,v in selected.items()},qualification_sha256=sha(before))
        p=ROOT/'retention-opened.json'
        if p.exists() and read(p)!=permit:raise RuntimeError('protection already opened for other candidates')
        atomic(p,permit)
    fn=measure if audit else reproduced;ns=stage+('-audit' if audit else '')
    base=fn(ns,'baseline',read(INPUT/'baseline.json')['policy'],specs)
    winners={};scores={}
    for name,item in selected.items():
        after=fn(ns,name,item['policy'],specs);d=difference(base,after);scores[name]=d
        if not d['loss_indices'] and (stage=='retention' or d['gain']>=2):winners[name]=item
    value=dict(valid=True,winners=winners,scores=scores,exam_opened=False,s6_green=False)
    if audit:
        if value!=read(ROOT/(stage+'.json')):raise RuntimeError('qualification summary differs')
        for p in (ROOT/ns/'measurements').glob('*.json'):
            if read(p)!=read(ROOT/stage/'measurements'/p.name):raise RuntimeError('independent trajectory differs')
        value=dict(value,independent_execution=True,**{stage+'_sha256':sha(value)})
    atomic(ROOT/(stage+('-audit' if audit else '')+'.json'),value)
    return value


def follow():
    gate=read(INPUT/'b20-closure.json')
    if not gate['valid'] or not gate['arithmetic_valid']:raise RuntimeError('B20 closure prerequisite missing')
    integrity()
    lock=(ROOT/'pipeline.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (ROOT/'closed.json').exists():return
    if not (ROOT/'micro.json').exists():micro()
    if not (ROOT/'micro-audit.json').exists():subprocess.run([sys.executable,'-u','-m','seed.s6b21','audit'],check=True)
    eligible=read(ROOT/'micro.json')['winners']
    for stage in ('qualification','retention'):
        if not any(n.startswith('balanced-') for n in eligible):break
        if not (ROOT/(stage+'.json')).exists():qualify(stage)
        if not (ROOT/(stage+'-audit.json')).exists():subprocess.run([sys.executable,'-u','-m','seed.s6b21',stage+'-audit'],check=True)
        eligible=read(ROOT/(stage+'.json'))['winners']
    ready=(ROOT/'retention-audit.json').exists() and any(n.startswith('balanced-') for n in eligible)
    closed=dict(valid=True,at=now(),qualification_passed=ready,ready_for_neocortex_ablation=ready,
                s6_green=False,exam_opened=False,physical_games=read(ROOT/'budget.json')['scheduled_games'],
                reason='coverage diagnosis; no autonomous LLM discovery from SEMILLA claimed')
    atomic(ROOT/'closed.json',closed)
    from seed.s6b21_review import review
    review(ROOT,INPUT/'manifest.json')
    status('QUALIFIED' if ready else 'CLOSED_NO_PROMOTION',**{k:v for k,v in closed.items() if k!='at'})


def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['follow']:follow()
        elif args==['audit']:integrity();micro(True)
        elif args in (['qualification-audit'],['retention-audit']):integrity();qualify(args[0].removesuffix('-audit'),True)
        else:raise ValueError('use follow/audit/qualification-audit/retention-audit')
    except Exception as exc:
        status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));raise


if __name__=='__main__':
    from seed import s6b21
    s6b21.main(sys.argv[1:])
