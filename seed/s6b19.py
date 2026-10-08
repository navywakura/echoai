"""B19 private qualification: targeted screen, broad development, fresh conservation.
Reuse frozen B18 execution/audit machinery; never relax the S6 score gate.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import FunctionType

from seed import s6b18 as old
from seed import s6b11 as engine
from seed.game_selfimprove import canonical,sha,journal
from echo_arc import cost_guard_search as controller, consumption_timeline as timeline

REPO=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('ECHO_B19_ROOT',str(REPO/'lab/seed/s6b19-20261005')))
INPUT=Path(os.environ.get('ECHO_B19_INPUT',str(REPO/'lab/kaggle/s6b19-20261005/input')))
A=[(2,18,0,2000)]+[(3,i-40,0,2000) for i in (42,51,53,59,68,76,77)]+[(3,i,0,2000) for i in (28026,28027,28031,28039)]
DEVELOPMENT=old.A+old.B+[(v,s,0,2000) for v in (2,3) for s in range(31000,31020)]
B=[(v,s,0,2000) for v in (2,3) for s in range(31100,31140)]
ARMS=('guard_only','synth','hybrid')
ROUNDS,SEED,WORKERS,MAX_GAMES=12,790101,4,6000
read,now,file_sha,atomic=old.read,old.now,old.file_sha,old.atomic
_play=FunctionType(engine.play_one.__code__,dict(engine.play_one.__globals__,ROOT=ROOT,
    A=DEVELOPMENT,B=B,EXAM_SEEDS=(),evidence=timeline))

def config():
    return dict(condition='S6-B19-GPU',arms=ARMS,screen=A,development=DEVELOPMENT,protected_B=B,
        rounds=ROUNDS,seed=SEED,workers=WORKERS,max_games=MAX_GAMES,model_calls_cap=1,
        screen_gate='>=2 levels, zero individual level/score loss; exact replay, independent audit',
        full_gate='same criteria on full 160 development games, exact replay and independent audit',
        retention_gate='zero individual level/score loss, 80 fresh games, exact replay and independent audit',
        selection='first screen passer per arm; no reselection after full development or B',
        provenance='screen deliberately includes consumed B18; historical 80 + consumed 40 + 40 new development',
        control='B18 guard-only algorithm; same evidence and shared first model response',
        hybrid='model proposes initial mechanism; core cost-aware finite value/scope refinement',
        synth='same B19 core without model',observed='screen only, existing journal',
        exam=[],exam_allowed=False,paid=False,private=True)

def integrity():
    m=read(INPUT/'manifest.json')
    if m['configuration']!=__import__('json').loads(canonical(config())):raise RuntimeError('configuration changed')
    for f,h in m['sources'].items():
        if file_sha(REPO/f)!=h:raise RuntimeError('frozen source changed: '+f)
    for f,h in m['inputs'].items():
        if file_sha(INPUT/f)!=h:raise RuntimeError('input changed: '+f)
    return m

def status(stage,**kw):
    rec=dict(at=now(),stage=stage,condition='S6-B19-GPU',**kw)
    atomic(ROOT/'status.json',rec);print(canonical(rec),flush=True)

reserve=FunctionType(old.reserve.__code__,globals())
worker_init=old.worker_init

def play_one(item):
    policy,spec,path=item;spec=tuple(spec)
    if spec not in DEVELOPMENT+B or (path is not None and spec not in A):
        raise ValueError('unknown partition or protected observation')
    return __import__('json').loads(canonical(_play((policy,spec,path))))

def measure(namespace,label,policy,specs,replay=False):
    specs=list(map(tuple,specs))
    if specs not in (A,DEVELOPMENT,B):raise ValueError('complete declared partition required')
    observed=specs==A
    if specs==B and not (ROOT/'retention-opened.json').exists():raise ValueError('protected partition closed')
    if namespace not in ('primary','independent','qualification','qualification-independent','retention','retention-independent'):
        raise ValueError('unknown cache namespace')
    frozen=integrity();partition='replay' if replay else 'main';records={};jobs=[]
    for spec in specs:
        key=sha(dict(profile=sha(frozen),policy=policy,spec=spec,observed=observed))
        dest=ROOT/namespace/'cache'/partition/(key+'.json')
        if dest.exists():
            cached=read(dest)
            if cached['key']!=key or sha(cached['record'])!=cached['digest']:raise RuntimeError('corrupt cache')
            records[spec]=cached['record'];continue
        directory=ROOT/namespace/'journals'/partition/key if observed else None
        if directory is not None and directory.exists():raise RuntimeError('interrupted game; explicit recovery required')
        jobs.append((spec,key,dest,directory))
    reserve(len(jobs))
    if jobs:
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init) as pool:
            fs={pool.submit(play_one,(policy,spec,str(path) if path else None)):(spec,key,dest,path) for spec,key,dest,path in jobs}
            for n,f in enumerate(as_completed(fs),1):
                spec,key,dest,path=fs[f];row=f.result()
                atomic(dest,dict(key=key,digest=sha(row),record=row));records[spec]=row
                if path:shutil.rmtree(path)
                if n%10==0 or n==len(jobs):status('MEASURING',namespace=namespace,label=label,completed=n,total=len(jobs))
    rows=[records[s] for s in specs]
    out=dict(rows=rows,levels=sum(r['levels_completed'] for r in rows),score=sum(r['score'] for r in rows),trace_digest=sha(rows))
    atomic(ROOT/namespace/'measurements'/(label+'.json'),out);return out

reproduced=FunctionType(old.reproduced.__code__,globals())
difference,a_pass=old.difference,old.a_pass
old_prompt,old_controller,memory=old.old_prompt,old.old_controller,old.memory
evaluate=FunctionType(old.evaluate.__code__,globals())

def run(audit=False):
    manifest=integrity();ns='independent' if audit else 'primary'
    fixture=read(INPUT/'baseline.json');policy=fixture['policy'];initial=fixture['history']
    model=old.s6b18_model.environment_model()
    base=measure(ns,'baseline/A',policy,A) if audit else reproduced(ns,'baseline/A',policy,A)
    if sha(timeline.legacy_rows(base['rows']))!=fixture['screen_trace_sha256']:raise RuntimeError('screen baseline parity failed')
    if audit and base!=read(ROOT/'primary/measurements/baseline/A.json'):raise RuntimeError('independent baseline differs')
    histories={arm:list(initial) for arm in ARMS};done={};cells=[]
    for index in range(ROUNDS):
        for arm in ARMS:
            if arm in done:continue
            label=f'micro/{arm}/{index:03d}';req=controller.request(arm,index,policy,base,histories[arm])
            path=ROOT/'steps'/(label+'.json');saved=read(path) if path.exists() else None
            if saved and (saved['request']!=req or saved['profile_sha256']!=sha(manifest)):raise RuntimeError('request reconstruction mismatch')
            use_model=index==0 and arm in ('guard_only','hybrid');call='micro/shared/000' if use_model else None
            if use_model:
                if audit or (ROOT/'calls'/call/'result.json').exists():response=model['load'](call,req,SEED,ROOT,sha(manifest),audit_tokens=audit)
                else:
                    status('PROPOSING',arm=arm,slot=index+1)
                    response=model['propose'](call,req,SEED,ROOT,sha(manifest),1)
                log=(ROOT/'calls'/call/'stderr.txt').read_text()
                if 'offloaded' not in log or 'offloaded 0/' in log:raise RuntimeError('CUDA offload not confirmed')
            else:response=dict(answer=controller.deterministic_answer(req),usage=dict(input_tokens=0,max_output_tokens=0))
            if audit and saved is None:raise RuntimeError('missing original event')
            if saved and not audit:event=saved['event']
            else:
                event=evaluate(ns,label+'/A',arm,index,req,response,policy,base,histories[arm],audit)
                if audit:
                    if event!=saved['event']:raise RuntimeError('independent verdict mismatch')
                else:
                    atomic(path,dict(request=req,event=event,profile_sha256=sha(manifest)))
                    journal(ROOT/'live/journal.jsonl',dict(kind='verdict',arm=arm,**event))
            histories[arm].append(event)
            cell=dict(arm=arm,slot=index+1,verdict=event['verdict'],levels=event.get('levels'),gain=event.get('A',{}).get('gain'),losses=event.get('A',{}).get('loss_indices'),call=call)
            cells.append(cell);status('AUDIT_RESULT' if audit else 'MICRO_RESULT',**cell)
            if event['verdict']=='A_ONLY_PASS':done[arm]=dict(slot=index+1,policy=event['candidate'])
    result=dict(valid=True,at=now(),cells=cells,passed=done,profile_sha256=sha(manifest),exam_opened=False,s6_green=False)
    if audit:
        original=read(ROOT/'micro.json')
        if cells!=original['cells'] or done!=original['passed']:raise RuntimeError('micro audit totals differ')
        result.update(independent_execution=True,micro_sha256=sha(original))
    atomic(ROOT/('micro-audit.json' if audit else 'micro.json'),result);return result

def qualified_policies():
    micro=read(ROOT/'micro.json');audit=read(ROOT/'micro-audit.json')
    if not audit['valid'] or audit['micro_sha256']!=sha(micro):raise RuntimeError('micro audit required')
    return dict(base=read(INPUT/'baseline.json')['policy'],**{k:v['policy'] for k,v in micro['passed'].items()})

def qualification(audit=False):
    policies=qualified_policies();ns='qualification-independent' if audit else 'qualification'
    results={name:(measure(ns,name,p,DEVELOPMENT) if audit else reproduced(ns,name,p,DEVELOPMENT)) for name,p in policies.items()}
    if audit:
        for name,value in results.items():
            if value!=read(ROOT/'qualification/measurements'/(name+'.json')):raise RuntimeError('broad development audit differs')
    verdicts={name:difference(results['base'],v) for name,v in results.items() if name!='base'}
    out=dict(valid=True,at=now(),independent_execution=audit,verdicts=verdicts,passed=[n for n,d in verdicts.items() if a_pass(d)],
        micro_sha256=sha(read(ROOT/'micro.json')),results_sha256={n:v['trace_digest'] for n,v in results.items()},exam_opened=False)
    if audit:
        first=read(ROOT/'qualification.json')
        if out['verdicts']!=first['verdicts'] or out['passed']!=first['passed']:raise RuntimeError('qualification verdict differs')
        out['qualification_sha256']=sha(first)
    atomic(ROOT/('qualification-audit.json' if audit else 'qualification.json'),out);return out

def retention(audit=False):
    q=read(ROOT/'qualification.json');check=read(ROOT/'qualification-audit.json')
    if not check['valid'] or check['qualification_sha256']!=sha(q) or 'hybrid' not in q['passed']:
        raise RuntimeError('retention requires independently qualified hybrid')
    policies={k:v for k,v in qualified_policies().items() if k=='base' or k in q['passed']}
    opened=dict(profile_sha256=sha(integrity()),qualification_sha256=sha(q),policies=policies,B=B)
    path=ROOT/'retention-opened.json'
    if path.exists():
        if read(path)!=__import__('json').loads(canonical(opened)):raise RuntimeError('protected policy selection changed')
    elif audit:raise RuntimeError('primary retention missing')
    else:atomic(path,opened)
    ns='retention-independent' if audit else 'retention'
    results={name:(measure(ns,name,p,B) if audit else reproduced(ns,name,p,B)) for name,p in policies.items()}
    if audit:
        for name,value in results.items():
            if value!=read(ROOT/'retention/measurements'/(name+'.json')):raise RuntimeError('protected audit differs')
    verdicts={n:difference(results['base'],v) for n,v in results.items() if n!='base'}
    out=dict(valid=True,at=now(),independent_execution=audit,verdicts=verdicts,hybrid_conserved=not verdicts['hybrid']['loss_indices'],
        results_sha256={n:v['trace_digest'] for n,v in results.items()},qualification_sha256=sha(q),exam_opened=False)
    if audit:
        first=read(ROOT/'retention.json')
        if out['verdicts']!=first['verdicts']:raise RuntimeError('protected verdict differs')
        out['retention_sha256']=sha(first)
    atomic(ROOT/('retention-audit.json' if audit else 'retention.json'),out);return out

def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['audit']:run(True);return
        if args==['qualification-audit']:qualification(True);return
        if args==['retention-audit']:retention(True);return
        if args!=['follow']:raise ValueError('use follow/audit/qualification-audit/retention-audit')
        lock=(ROOT/'pipeline.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        m=integrity()
        if (ROOT/'closed.json').exists():return
        preflight=read(os.environ['ECHO_B18_PREFLIGHT'])
        if preflight!=m['cuda_preflight'] or not preflight['valid']:raise RuntimeError('CUDA qualification changed')
        for key in ('ECHO_B18_CLI','ECHO_B18_TOKENIZER'):
            exe=Path(os.environ[key])
            if file_sha(exe)!=preflight['binaries'][exe.name]:raise RuntimeError('CUDA executable changed')
        atomic(ROOT/'runtime.json',dict(python=sys.version,profile_sha256=sha(m),preflight=preflight))
        if not (ROOT/'micro.json').exists():run()
        if not (ROOT/'micro-audit.json').exists():subprocess.run([sys.executable,'-u','-m','seed.s6b19','audit'],check=True)
        selected=qualified_policies();qualified=False
        if 'hybrid' in selected:
            if not (ROOT/'qualification.json').exists():qualification()
            if not (ROOT/'qualification-audit.json').exists():subprocess.run([sys.executable,'-u','-m','seed.s6b19','qualification-audit'],check=True)
            if 'hybrid' in read(ROOT/'qualification-audit.json')['passed']:
                if not (ROOT/'retention.json').exists():retention()
                if not (ROOT/'retention-audit.json').exists():subprocess.run([sys.executable,'-u','-m','seed.s6b19','retention-audit'],check=True)
                q=read(ROOT/'retention.json');a=read(ROOT/'retention-audit.json')
                if not a['valid'] or a['retention_sha256']!=sha(q):raise RuntimeError('retention audit binding failed')
                qualified=a['hybrid_conserved']
        micro=read(ROOT/'micro.json')
        closed=dict(at=now(),valid=True,judge_passed=qualified,ready_for_pilot_design=qualified,
            exam_allowed=False,exam_opened=False,s6_green=False,proposals=len(micro['cells']),
            physical_games=read(ROOT/'budget.json')['scheduled_games'],physical_model_calls=len(read(ROOT/'model-budget.json')['calls']),
            reason='qualification only; paired pilot, campaign, B1-B5 remain required')
        atomic(ROOT/'closed.json',closed);status('CLOSED',**{k:v for k,v in closed.items() if k!='at'})
    except Exception as exc:
        status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));raise

if __name__=='__main__':
    from seed import s6b19
    s6b19.main(sys.argv[1:])
