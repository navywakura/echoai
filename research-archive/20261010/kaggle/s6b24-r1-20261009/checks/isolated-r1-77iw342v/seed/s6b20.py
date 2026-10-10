"""Private B20 runner. Isolated caches, unchanged judge, explicit phase gates."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import FunctionType

from seed import s6b18 as previous, s6b11 as engine, s6b18_model
from seed.game_selfimprove import canonical, sha, journal
from echo_arc import s6b20_search as search, consumption_timeline as timeline
from echo_arc.contrastive_grammar import validate_answer

REPO=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('ECHO_B20_ROOT',str(REPO/'lab/seed/s6b20-20261006')))
INPUT=Path(os.environ.get('ECHO_B20_INPUT',str(REPO/'lab/kaggle/s6b20-20261006/input')))
A=[(2,18,0,2000)]+[(3,i-40,0,2000) for i in (42,51,53,59,68,76,77)]+[(3,i,0,2000) for i in (28026,28027,28031,28039)]
DEVELOPMENT=previous.A+previous.B+[(v,s,0,2000) for v in (2,3) for s in range(62000,62020)]
B=[(v,s,0,2000) for v in (2,3) for s in range(63000,63040)]
SEEDS=(820101,820117,820129)
CELLS=(('C0','old',None),('C1','new',None))+tuple((f'{name}-{seed}',kind,seed) for seed in SEEDS for name,kind in (('H0','old'),('H1','new')))
ROUNDS,WORKERS,MAX_GAMES=18,4,16000
read,atomic,file_sha,now=previous.read,previous.atomic,previous.file_sha,previous.now
_play=FunctionType(engine.play_one.__code__,dict(engine.play_one.__globals__,ROOT=ROOT,A=DEVELOPMENT,B=B,EXAM_SEEDS=(),evidence=timeline))


def config():
    return dict(condition='S6-B20',screen=A,development=DEVELOPMENT,protected_B=B,
        cells=CELLS,seeds=SEEDS,rounds=ROUNDS,workers=WORKERS,max_games=MAX_GAMES,capacity_max_games=2928,
        model_calls_cap=3,language_sha256=search.language_sha(),pool_limit=search.POOL_LIMIT,
        max_children=search.MAX_CHILDREN,mechanism='HOLD only; post-B14 repair qualification',
        scope='capacity control and factorial micro; pilot/campaign need their own frozen contract',
        gates='gain >=2 AND zero individual level/score loss; tolerance 1e-10',
        protected_feedback=False,exam_allowed=False,paid=False,private=True,
        selection='first pass per cell; no reselection after broad development or protection',
        initial_policy='B14 accepted policy and accepted history only; no capacity/PROBE/B19 rejected proposals',
        observation='existing observer on screen; no protected observer',
        independent_cache=True,per_game_timeout_seconds=240)


def integrity():
    m=read(INPUT/'manifest.json')
    from importlib.metadata import version
    if '.'.join(map(str,sys.version_info[:3]))!=m['python'] or version('numpy')!=m['numpy'] or version('arcengine')!=m['arcengine']:
        raise RuntimeError('frozen runtime changed')
    if m['configuration']!=json.loads(canonical(config())):raise RuntimeError('configuration changed')
    for name,h in m['sources'].items():
        if file_sha(REPO/name)!=h:raise RuntimeError('frozen source changed: '+name)
    for name,h in m['inputs'].items():
        if file_sha(INPUT/name)!=h:raise RuntimeError('input changed: '+name)
    return m


def status(stage,**fields):
    value=dict(at=now(),condition='S6-B20',stage=stage,**fields)
    atomic(ROOT/'status.json',value);print(canonical(value),flush=True)


def reserve(count,namespace,label):
    ROOT.mkdir(parents=True,exist_ok=True)
    with (ROOT/'budget.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path=ROOT/'budget.json';old=read(path) if path.exists() else dict(scheduled_games=0,reservations=[])
        limit=MAX_GAMES
        if (INPUT/'manifest.json').exists() and read(INPUT/'manifest.json').get('stage')=='capacity':limit=2928
        if old['scheduled_games']+count>limit:raise RuntimeError('preregistered game cap reached')
        old['scheduled_games']+=count;old['cap']=limit
        old['reservations'].append(dict(namespace=namespace,label=label,count=count,at=now()))
        atomic(path,old)


def play_one(job):
    policy,spec,directory=job;spec=tuple(spec)
    if spec not in DEVELOPMENT+B or (directory is not None and spec not in A):
        raise ValueError('unknown case or protected observation')
    started=time.monotonic()
    row=json.loads(canonical(_play((policy,spec,directory))))
    return row,time.monotonic()-started


def measure(namespace,label,policy,specs,replay=False):
    specs=list(map(tuple,specs))
    if specs not in (A,DEVELOPMENT,B):raise ValueError('complete declared partition required')
    if specs==B and not (ROOT/'retention-opened.json').exists():raise ValueError('protection closed')
    if not namespace or any(x in namespace for x in ('/','..')):raise ValueError('invalid namespace')
    manifest=integrity();records={};jobs=[];partition='replay' if replay else 'main';observed=specs==A
    for spec in specs:
        key=sha(dict(profile=sha(manifest),namespace=namespace,policy=policy,spec=spec,observed=observed))
        dest=ROOT/namespace/'cache'/partition/(key+'.json')
        if dest.exists():
            saved=read(dest)
            if saved['key']!=key or sha(saved['record'])!=saved['digest']:raise RuntimeError('cache checksum mismatch')
            records[spec]=saved['record'];continue
        path=ROOT/namespace/'journals'/partition/key if observed else None
        if path and path.exists():raise RuntimeError('interrupted game; explicit recovery required')
        jobs.append((spec,key,dest,path))
    if jobs:
        reserve(len(jobs),namespace,label)
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn'),initializer=previous.worker_init) as pool:
            futures={pool.submit(play_one,(policy,spec,str(path) if path else None)):(spec,key,dest,path) for spec,key,dest,path in jobs}
            for n,future in enumerate(as_completed(futures),1):
                spec,key,dest,path=futures[future];row,elapsed=future.result()
                atomic(dest,dict(key=key,digest=sha(row),record=row));records[spec]=row
                journal(ROOT/'metrics.jsonl',dict(namespace=namespace,label=label,case=spec,elapsed=elapsed,replay=replay))
                if path:shutil.rmtree(path)
                status('MEASURING',namespace=namespace,label=label,completed=n,total=len(jobs))
    rows=[records[s] for s in specs]
    result=dict(rows=rows,levels=sum(r['levels_completed'] for r in rows),score=sum(r['score'] for r in rows),trace_digest=sha(rows))
    atomic(ROOT/namespace/'measurements'/(label+'.json'),result)
    return result


def reproduced(namespace,label,policy,specs):
    a=measure(namespace,label,policy,specs)
    b=measure(namespace,label+'/replay',policy,specs,True)
    if a!=b:raise RuntimeError('replay mismatch; instrument blocked')
    return a


def difference(base,after):
    if len(base['rows'])!=len(after['rows']):raise ValueError('unpaired results')
    for b,a in zip(base['rows'],after['rows'],strict=True):
        if [b[k] for k in ('version','seed','rep','budget')]!=[a[k] for k in ('version','seed','rep','budget')]:
            raise ValueError('case ordering mismatch')
    return previous.difference(base,after)


def initial_request(policy,base,history):
    req=search.request('new',0,policy,base,history)
    # Same outcome-independent language for the two paired model arms. The
    # summary comes from all own baseline cases; it contains no winning guard.
    features=[]
    for row in base['rows']:
        reads=[x for x in row['diagnostics']['consumers'] if x['parameter']=='HOLD']
        features.append(dict(levels=row['levels_completed'],reads=len(reads),
            examples=[{k:x['features'][k] for k in ('level','world_events','pending_effect','reset_useful','path_pending','pred_error')} for x in reads[:2]]))
    req['prompt_variants']=[
        'Propose one bounded HOLD repair as JSON, with 1 to 3 AND guards from the grammar. '
        'Gain at least two development levels without ANY per-case level or score loss. '
        'HOLD inhibits repeating a known reset key; the body can still move. A reset may '
        'destroy useful remote activity. pending_effect=0 does not prove such activity is finished. '
        'Use observable conditions, no task IDs, hidden state or coordinates. '
        'Feature bounds: '+canonical(search.precise_patch.FEATURES)+'. '
        'Accepted policy: '+canonical(policy['program'])+'. Own baseline observations: '+canonical(features)]
    req['model_call_required']=True
    return req


def evaluate(ns,label,req,response,policy,base,history,audit=False):
    event=dict(id=req['id'],type=req['type'],target_id=req['target_id'],base_sha256=sha(policy),
        answer=response['answer'],usage=response.get('usage',{}),equivalent_calls=[])
    try:
        proposal=validate_answer(response['answer'],req['guard_schema'])
        if not proposal['patches']:return dict(event,verdict='V1',reason='finite search exhausted')
        candidate=engine.strategy(program=engine.patch.append(policy['program'],proposal))
    except ValueError as exc:return dict(event,verdict='V1',reason=str(exc))
    after=measure(ns,label,candidate,A) if audit else reproduced(ns,label,candidate,A)
    if audit and after!=read(ROOT/ns.replace('audit-','micro-',1)/'measurements'/(label+'.json')):
        raise RuntimeError('independent full trajectory differs')
    delta=difference(base,after)
    event.update(proposal=proposal,candidate=candidate,A=delta,levels=after['levels'],
        development=search.guard_search.comparison(base,after,'HOLD'),
        verdict='A_ONLY_PASS' if previous.a_pass(delta) else 'V3')
    return event


def micro(audit=False):
    m=integrity();fixture=read(INPUT/'baseline.json');policy=fixture['policy'];accepted=fixture['history']
    model=s6b18_model.environment_model()
    results=[];winners={}
    for name,kind,seed in CELLS:
        ns=('audit-' if audit else 'micro-')+name
        base=measure(ns,'baseline',policy,A) if audit else reproduced(ns,'baseline',policy,A)
        if sha(timeline.legacy_rows(base['rows']))!=fixture['screen_trace_sha256']:raise RuntimeError('baseline parity mismatch')
        if audit and base!=read(ROOT/('micro-'+name)/'measurements/baseline.json'):raise RuntimeError('independent baseline differs')
        history=list(accepted)
        for index in range(ROUNDS):
            req=initial_request(policy,base,accepted) if seed is not None and index==0 else search.request(kind,index,policy,base,history)
            path=ROOT/'steps'/name/f'{index:03d}.json'
            saved=read(path) if path.exists() else None
            if saved and (saved['request']!=req or saved['profile_sha256']!=sha(m)):raise RuntimeError('request reconstruction changed')
            if seed is not None and index==0:
                call=f'micro/shared/{seed}'
                response=model['load'](call,req,seed,ROOT,sha(m),audit_tokens=audit) if audit or (ROOT/'calls'/call/'result.json').exists() else model['propose'](call,req,seed,ROOT,sha(m),3)
            else:response=dict(answer=search.answer(req),usage=dict(input_tokens=0,max_output_tokens=0))
            if audit and saved is None:raise RuntimeError('missing event for audit')
            event=evaluate(ns,f'candidate/{index:03d}',req,response,policy,base,history,audit) if audit or not saved else saved['event']
            if audit and event!=saved['event']:raise RuntimeError('independent event differs')
            if not audit:
                atomic(path,dict(request=req,event=event,profile_sha256=sha(m)))
                visible=dict(event,id=event['id']-1)
                if event.get('A'):visible['A']=dict(event['A'],before_levels=base['levels'],after_levels=event['levels'])
                journal(ROOT/'live/journal.jsonl',dict(kind='verdict',arm=name,**visible))
            history.append(event)
            cell=dict(arm=name,slot=index+1,verdict=event['verdict'],levels=event.get('levels'),diff=event.get('A'))
            results.append(cell);status('AUDIT_RESULT' if audit else 'MICRO_RESULT',**cell)
            if event['verdict']=='A_ONLY_PASS':winners[name]=dict(slot=index+1,policy=event['candidate']);break
            if event['verdict']=='V1' and seed is None and not req['shortlist']:break
    result=dict(valid=True,cells=results,winners=winners,exam_opened=False,s6_green=False,profile_sha256=sha(m))
    if audit:
        if result!=read(ROOT/'micro.json'):raise RuntimeError('micro audit summary mismatch')
        result=dict(result,independent_execution=True,micro_sha256=sha(result))
    atomic(ROOT/('micro-audit.json' if audit else 'micro.json'),result)
    return result


def qualify(stage,audit=False):
    if stage not in ('qualification','retention'):raise ValueError('unknown gate')
    source='micro' if stage=='qualification' else 'qualification'
    before=read(ROOT/(source+'.json'));receipt=read(ROOT/(source+'-audit.json'))
    if not receipt['valid'] or receipt[source+'_sha256']!=sha(before):raise RuntimeError('prior audit missing or mismatched')
    selected=before['winners'];fixture=read(INPUT/'baseline.json');basepolicy=fixture['policy']
    if not any(n.startswith('H1-') for n in selected):raise RuntimeError('no hybrid eligible')
    specs=DEVELOPMENT if stage=='qualification' else B
    if stage=='retention':
        permit=dict(profile_sha256=sha(integrity()),policies={k:sha(v['policy']) for k,v in selected.items()},qualification_sha256=sha(before))
        if (ROOT/'retention-opened.json').exists() and read(ROOT/'retention-opened.json')!=permit:raise RuntimeError('protection already opened for other candidates')
        atomic(ROOT/'retention-opened.json',permit)
    ns=stage+('-audit' if audit else '')
    measure_fn=measure if audit else reproduced
    base=measure_fn(ns,'baseline',basepolicy,specs);winners={};scores={}
    for name,item in selected.items():
        after=measure_fn(ns,name,item['policy'],specs);diff=difference(base,after)
        scores[name]=diff
        if not diff['loss_indices'] and (stage=='retention' or diff['gain']>=2):winners[name]=item
    result=dict(valid=True,winners=winners,scores=scores,exam_opened=False,s6_green=False)
    if audit:
        if result!=read(ROOT/(stage+'.json')):raise RuntimeError('qualification summary differs')
        # Compare full rows as well as the scalar summary.
        for path in (ROOT/ns/'measurements').glob('*.json'):
            if read(path)!=read(ROOT/stage/'measurements'/path.name):raise RuntimeError('independent trajectory differs')
        result=dict(result,independent_execution=True,**{stage+'_sha256':sha(result)})
    atomic(ROOT/(stage+('-audit' if audit else '')+'.json'),result);return result


def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        integrity()
        if args==['audit']:micro(True);return
        if args in (['qualification-audit'],['retention-audit']):qualify(args[0].removesuffix('-audit'),True);return
        if args!=['follow']:raise ValueError('use follow/audit/qualification-audit/retention-audit')
        lock=(ROOT/'pipeline.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/'closed.json').exists():return
        gate=read(INPUT/'capacity-gate.json')
        if not gate['valid'] or not gate['capacity_passed']:raise RuntimeError('capacity prerequisite not met')
        preflight=read(os.environ['ECHO_B18_PREFLIGHT'])
        if preflight!=integrity()['cuda_preflight']:raise RuntimeError('GPU runtime changed')
        for key in ('ECHO_B18_CLI','ECHO_B18_TOKENIZER'):
            exe=Path(os.environ[key])
            if file_sha(exe)!=preflight['binaries'][exe.name]:raise RuntimeError('GPU binary changed')
        atomic(ROOT/'runtime.json',dict(python=sys.version,preflight=preflight,profile_sha256=sha(integrity())))
        if not (ROOT/'micro.json').exists():micro()
        if not (ROOT/'micro-audit.json').exists():subprocess.run([sys.executable,'-u','-m','seed.s6b20','audit'],check=True)
        eligible=read(ROOT/'micro.json')['winners']
        for stage in ('qualification','retention'):
            if not any(n.startswith('H1-') for n in eligible):break
            if not (ROOT/(stage+'.json')).exists():qualify(stage)
            if not (ROOT/(stage+'-audit.json')).exists():subprocess.run([sys.executable,'-u','-m','seed.s6b20',stage+'-audit'],check=True)
            eligible=read(ROOT/(stage+'.json'))['winners']
        ready=(ROOT/'retention-audit.json').exists() and any(n.startswith('H1-') for n in eligible)
        closed=dict(valid=True,at=now(),qualification_passed=ready,ready_for_pilot_contract=ready,
                    s6_green=False,exam_opened=False,physical_games=read(ROOT/'budget.json')['scheduled_games'],
                    reason='pilot/campaign/exam need a separately frozen four-arm contract')
        atomic(ROOT/'closed.json',closed);status('QUALIFIED' if ready else 'CLOSED_NO_PROMOTION',**{k:v for k,v in closed.items() if k!='at'})
    except Exception as exc:
        status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));raise


if __name__=='__main__':
    from seed import s6b20
    s6b20.main(sys.argv[1:])
