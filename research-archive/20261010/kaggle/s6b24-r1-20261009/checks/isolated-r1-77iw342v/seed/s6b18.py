"""Portable private B18 micro, independent audit and conditional retention judge.

Reuse the frozen game execution and grammar; never import a PROBE winner.
The bundle contains the accepted baseline only. No reserved exam is exposed.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
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

from seed import s6b11 as engine, s6b17_prompt as old_prompt, s6b18_model
from seed.game_selfimprove import canonical,sha,journal
from echo_arc import guard_search as controller, consumption_timeline as timeline
from echo_arc import guard_synthesis as old_controller, repair_memory as memory

REPO = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get('ECHO_B18_ROOT',str(REPO/'lab/seed/s6b18-20261005')))
INPUT = Path(os.environ.get('ECHO_B18_INPUT',str(REPO/'lab/kaggle/s6b18-20261005/input')))
A = [(v,s,0,2000) for v in (2,3) for s in range(40)]
B = [(v,s,0,2000) for v in (2,3) for s in range(28020,28040)]
ARMS = ('llm_selector','synth','hybrid')
ROUNDS,SEED,WORKERS,MAX_GAMES = 8,770101,4,6500
atomic = engine.atomic
_play = FunctionType(engine.play_one.__code__,dict(engine.play_one.__globals__,
    ROOT=ROOT,A=A,B=B,EXAM_SEEDS=(),evidence=timeline))


def read(path): return json.loads(Path(path).read_text())
def now(): return datetime.now(timezone.utc).isoformat()
def file_sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def config():
    return dict(condition='S6-B18-GPU',arms=list(ARMS),A=A,protected_B=B,exam=[],
        rounds=ROUNDS,seed=SEED,workers=WORKERS,max_games=MAX_GAMES,model_calls_cap=8,
        per_arm_candidate_slots=8,per_arm_A_game_cap=1280,context=3072,max_output=160,
        initial_policy='accepted B14 378-level baseline; no micro/PROBE winners',
        common_first_llm_response=True,stop_each_arm_at_first_A_pass=True,
        hybrid='LLM first mechanism; core deterministic own-evidence guard refinement',
        control='B17 LLM selector on same GPU; separate model-free B18 search',
        A_gate='gain >=2; zero per-case level/score loss; full replay; fresh audit',
        B_gate='first passing hybrid/synth only; 40 fresh protected games; zero loss; no feedback',
        scope='micro and retention qualification; cannot authorize a reserved exam',
        paid=False,private=True)


def integrity():
    manifest = read(INPUT/'manifest.json')
    if manifest['configuration'] != json.loads(canonical(config())):
        raise RuntimeError('frozen configuration changed')
    for path,digest in manifest['sources'].items():
        if file_sha(REPO/path)!=digest: raise RuntimeError('source changed: '+path)
    for name,digest in manifest['inputs'].items():
        if file_sha(INPUT/name)!=digest: raise RuntimeError('baseline input changed')
    return manifest


def status(stage,**kw):
    record=dict(at=now(),stage=stage,condition='S6-B18-GPU',**kw)
    atomic(ROOT/'status.json',record);print(canonical(record),flush=True)


def reserve(n):
    path=ROOT/'budget.json';b=read(path) if path.exists() else dict(scheduled_games=0)
    if b['scheduled_games']+n>MAX_GAMES: raise RuntimeError('B18 game cap reached')
    atomic(path,dict(scheduled_games=b['scheduled_games']+n,cap=MAX_GAMES))


def worker_init(): engine.old.worker_init()


def play_one(item):
    policy,spec,path=item
    spec=tuple(spec)
    if spec not in A+B or (path is not None and spec not in A):
        raise ValueError('unregistered partition or protected observation')
    row=_play((policy,spec,path))
    return json.loads(canonical(row))


def measure(namespace,label,policy,specs,replay=False):
    specs=list(map(tuple,specs))
    if specs not in (A,B): raise ValueError('must measure the complete declared partition')
    observed=specs==A
    if not observed and not (ROOT/'retention-opened.json').exists():
        raise ValueError('protected retention requires the audited micro')
    if namespace not in ('primary','independent','retention','retention-independent'):
        raise ValueError('invalid measurement namespace')
    frozen=integrity(); partition='replay' if replay else 'main'
    records={};jobs=[]
    for spec in specs:
        key=sha(dict(profile=sha(frozen),policy=policy,spec=spec,observed=observed))
        dest=ROOT/namespace/'cache'/partition/(key+'.json')
        if dest.exists():
            cached=read(dest)
            if cached['key']!=key or sha(cached['record'])!=cached['digest']:
                raise RuntimeError('corrupt cache')
            records[spec]=cached['record'];continue
        directory=ROOT/namespace/'journals'/partition/key if observed else None
        if directory is not None and directory.exists():
            raise RuntimeError('interrupted game; explicit recovery required')
        jobs.append((spec,key,dest,directory))
    reserve(len(jobs))
    if jobs:
        with ProcessPoolExecutor(max_workers=WORKERS,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init) as pool:
            futures={pool.submit(play_one,(policy,spec,str(path) if path else None)):(spec,key,dest,path)
                     for spec,key,dest,path in jobs}
            for n,future in enumerate(as_completed(futures),1):
                spec,key,dest,path=futures[future];row=future.result()
                atomic(dest,dict(key=key,digest=sha(row),record=row));records[spec]=row
                # Persist the record with its full temporal observations first.
                if path: shutil.rmtree(path)
                if n%10==0 or n==len(jobs):
                    status('MEASURING',namespace=namespace,label=label,completed=n,total=len(jobs))
    rows=[records[s] for s in specs]
    result=dict(rows=rows,levels=sum(r['levels_completed'] for r in rows),
                score=sum(r['score'] for r in rows),trace_digest=sha(rows))
    atomic(ROOT/namespace/'measurements'/(label+'.json'),result)
    return result


def reproduced(namespace,label,policy,specs):
    main=measure(namespace,label,policy,specs)
    replay=measure(namespace,label+'/replay',policy,specs,True)
    if main!=replay: raise RuntimeError('replay discrepancy; instrument blocked')
    return main


def difference(before,after):
    if len(before['rows'])!=len(after['rows']): raise ValueError('unpaired measurement')
    losses=[i for i,(b,a) in enumerate(zip(before['rows'],after['rows'],strict=True))
            if a['levels_completed']<b['levels_completed'] or a['score']+1e-10<b['score']]
    return dict(gain=after['levels']-before['levels'],loss_indices=losses,
                score_delta=after['score']-before['score'])


def a_pass(diff): return diff['gain']>=2 and not diff['loss_indices']


def evaluate(namespace,label,arm,index,request,response,policy,base,history,audit):
    event=dict(id=index+1,type=request['type'],target_id=request.get('target_id'),
        base_sha256=sha(policy),answer=response['answer'],usage=response['usage'],equivalent_calls=[])
    try:
        proposal=old_prompt.check_answer(response['answer'],request)
        if not proposal['patches']: return dict(event,verdict='V1',reason='exhausted grammar')
        candidate=engine.strategy(program=engine.patch.append(policy['program'],proposal))
    except ValueError as exc: return dict(event,verdict='V1',reason=str(exc))
    after=(measure(namespace,label,candidate,A) if audit else reproduced(namespace,label,candidate,A))
    if audit and after!=read(ROOT/'primary/measurements'/(label+'.json')):
        raise RuntimeError('independent full trajectory differs: '+label)
    diff=difference(base,after);param=next(iter(proposal['patches'][0]['set']))
    compare=old_controller.comparison if arm=='llm_selector' else controller.comparison
    dev=compare(base,after,param)
    event.update(proposal=proposal,candidate=candidate,A=diff,development=dev,
        levels=after['levels'],verdict='A_ONLY_PASS' if a_pass(diff) else 'V3')
    if event['verdict']=='V3': event['decision_certificate']=memory.certificate(after['rows'],policy,candidate)
    return event


def run(audit=False):
    manifest=integrity();namespace='independent' if audit else 'primary'
    fixture=read(INPUT/'baseline.json');policy=fixture['policy'];initial=fixture['history']
    model=s6b18_model.environment_model()
    if audit and not (ROOT/'micro.json').exists(): raise RuntimeError('micro missing')
    base=(measure(namespace,'baseline/A',policy,A) if audit else reproduced(namespace,'baseline/A',policy,A))
    if base['levels']!=378 or sha(timeline.legacy_rows(base['rows']))!=fixture['legacy_trace_sha256']:
        raise RuntimeError('GPU host changed baseline environment/behavior')
    histories={arm:list(initial) for arm in ARMS};done={};cells=[]
    for index in range(ROUNDS):
        for arm in ARMS:
            if arm in done: continue
            label=f'micro/{arm}/{index:03d}'
            req=controller.request(arm,index,policy,base,histories[arm])
            saved_path=ROOT/'steps'/(label+'.json')
            saved=read(saved_path) if saved_path.exists() else None
            if saved and (saved['request']!=req or saved['profile_sha256']!=sha(manifest)):
                raise RuntimeError('request reconstruction mismatch')
            use_model=arm=='llm_selector' or (arm=='hybrid' and index==0)
            call=f'micro/llm_selector/{index:03d}' if use_model else None
            if use_model:
                if audit or (ROOT/'calls'/call/'result.json').exists():
                    response=model['load'](call,req,SEED+index*1000,ROOT,sha(manifest),audit_tokens=audit)
                else:
                    status('PROPOSING',arm=arm,slot=index+1)
                    response=model['propose'](call,req,SEED+index*1000,ROOT,sha(manifest),8)
                log=(ROOT/'calls'/call/'stderr.txt').read_text()
                if 'offloaded' not in log or 'offloaded 0/' in log: raise RuntimeError('CUDA execution not confirmed')
            else:
                response=dict(answer=controller.deterministic_answer(req),usage=dict(input_tokens=0,max_output_tokens=0))
            if audit and saved is None: raise RuntimeError('missing original verdict')
            if saved and not audit: event=saved['event']
            else:
                event=evaluate(namespace,label+'/A',arm,index,req,response,policy,base,histories[arm],audit)
                if audit:
                    if event!=saved['event']: raise RuntimeError('independent verdict mismatch')
                else:
                    atomic(saved_path,dict(request=req,event=event,profile_sha256=sha(manifest)))
                    journal(ROOT/'live/journal.jsonl',dict(kind='verdict',arm=arm,**event))
            histories[arm].append(event)
            cell=dict(arm=arm,slot=index+1,verdict=event['verdict'],levels=event.get('levels'),
                      gain=event.get('A',{}).get('gain'),losses=event.get('A',{}).get('loss_indices'),call=call)
            cells.append(cell);status('AUDIT_RESULT' if audit else 'MICRO_RESULT',**cell)
            if event['verdict']=='A_ONLY_PASS': done[arm]=dict(slot=index+1,policy=event['candidate'],event=event)
    result=dict(valid=True,at=now(),cells=cells,passed={k:dict(slot=v['slot'],policy=v['policy']) for k,v in done.items()},
                profile_sha256=sha(manifest),exam_opened=False,s6_green=False)
    if audit:
        original=read(ROOT/'micro.json')
        if cells!=original['cells'] or result['passed']!=original['passed']: raise RuntimeError('audit totals differ')
        result.update(independent_execution=True,micro_sha256=sha(original))
    atomic(ROOT/('micro-audit.json' if audit else 'micro.json'),result)
    return result


def retention(audit=False):
    micro=read(ROOT/'micro.json');check=read(ROOT/'micro-audit.json')
    if not check['valid'] or check['micro_sha256']!=sha(micro) or 'hybrid' not in micro['passed']:
        raise RuntimeError('retention requires audited hybrid A success')
    selected={k:v['policy'] for k,v in micro['passed'].items() if k in ('hybrid','synth')}
    selected=dict(base=read(INPUT/'baseline.json')['policy'],**selected)
    opened=dict(profile_sha256=sha(integrity()),micro_sha256=sha(micro),policies=selected,B=B)
    if (ROOT/'retention-opened.json').exists():
        if read(ROOT/'retention-opened.json')!=json.loads(canonical(opened)): raise RuntimeError('retention selection changed')
    elif audit: raise RuntimeError('primary retention missing')
    else: atomic(ROOT/'retention-opened.json',opened)
    namespace='retention-independent' if audit else 'retention'
    results={name:(measure(namespace,name,policy,B) if audit else reproduced(namespace,name,policy,B))
             for name,policy in selected.items()}
    if audit:
        for name,value in results.items():
            if value!=read(ROOT/'retention/measurements'/(name+'.json')): raise RuntimeError('protected independent mismatch')
    verdicts={name:difference(results['base'],value) for name,value in results.items() if name!='base'}
    result=dict(valid=True,at=now(),verdicts=verdicts,independent_execution=audit,
        hybrid_conserved=not verdicts['hybrid']['loss_indices'],exam_opened=False,
        results_sha256={k:v['trace_digest'] for k,v in results.items()})
    atomic(ROOT/('retention-audit.json' if audit else 'retention.json'),result)
    return result


def main(args):
    ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['audit']: run(True); return
        if args==['retention-audit']: retention(True); return
        if args!=['follow']: raise ValueError('use follow/audit/retention-audit')
        lock=(ROOT/'pipeline.lock').open('a')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (ROOT/'closed.json').exists():
            integrity();return
        manifest=integrity()
        preflight=read(os.environ['ECHO_B18_PREFLIGHT'])
        if preflight!=manifest['cuda_preflight'] or preflight.get('valid') is not True:
            raise RuntimeError('CUDA qualification receipt changed')
        for variable in ('ECHO_B18_CLI','ECHO_B18_TOKENIZER'):
            executable=Path(os.environ[variable])
            if file_sha(executable)!=preflight['binaries'][executable.name]:
                raise RuntimeError('CUDA executable checksum differs')
        atomic(ROOT/'runtime.json',dict(python=sys.version,platform=sys.platform,
            preflight=preflight,profile_sha256=sha(manifest)))
        if not (ROOT/'micro.json').exists(): run()
        if not (ROOT/'micro-audit.json').exists():
            subprocess.run([sys.executable,'-u','-m','seed.s6b18','audit'],check=True)
        micro=read(ROOT/'micro.json'); audit=read(ROOT/'micro-audit.json')
        if not audit['valid'] or audit['micro_sha256']!=sha(micro): raise RuntimeError('audit mismatch')
        qualified=False
        if 'hybrid' in micro['passed']:
            if not (ROOT/'retention.json').exists(): retention()
            if not (ROOT/'retention-audit.json').exists():
                subprocess.run([sys.executable,'-u','-m','seed.s6b18','retention-audit'],check=True)
            final=read(ROOT/'retention-audit.json');qualified=final['valid'] and final['hybrid_conserved']
        closed=dict(at=now(),valid=True,micro_passes=list(micro['passed']),judge_passed=qualified,
            ready_for_pilot_design=qualified,exam_allowed=False,s6_green=False,exam_opened=False,
            reason='qualification only; paired pilot, campaign and reserved B1-B5 remain required',
            measured_candidates=sum(c['levels'] is not None for c in micro['cells']),
            proposals=len(micro['cells']),physical_games=read(ROOT/'budget.json')['scheduled_games'],
            physical_model_calls=len(read(ROOT/'model-budget.json')['calls']))
        atomic(ROOT/'closed.json',closed);status('CLOSED',**{k:v for k,v in closed.items() if k!='at'})
    except Exception as exc:
        status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));raise


if __name__=='__main__':
    # Stable module names for spawn workers.
    from seed import s6b18
    s6b18.main(sys.argv[1:])
