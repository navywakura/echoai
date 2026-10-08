"""Private B17 micro: B16 / synthesis / hybrid, then independent A audit."""
import fcntl
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from types import FunctionType,SimpleNamespace

from seed import s6b16 as previous, s6b15_micro as reference_module, s6b17_prompt as prompts
from echo_arc import consumption_timeline as timeline, guard_synthesis as synthesis
from echo_arc import repair_outcomes, repair_memory as memory

core,engine,model=previous.b.parent,previous.b,previous.model
REPO,OLD=previous.REPO,previous.OLD
ROOT=REPO/'lab/seed/s6b17-20261004'
PREVIOUS=previous.ROOT
A=list(core.A)
ARMS=('b16','synth','hybrid')
ROUNDS,SEED,WORKERS,MAX_GAMES,MAX_CALLS=8,770101,4,6000,16
atomic,canonical,sha,now=core.atomic,core.canonical,core.sha,core.now
SOURCES=list(json.loads((PREVIOUS/'profile.json').read_text())['sources'])+[
    'echo_arc/consumption_timeline.py','echo_arc/guard_synthesis.py',
    'seed/s6b17_prompt.py','seed/s6b17.py','seed/s6b17_qualification.py',
    'tests/test_s6b17_timeline.py','tests/test_s6b17_synthesis.py','tests/test_s6b17_runner.py',
    'docs/ECHO45-S6-B17-DESIGN.md']


@lru_cache(maxsize=512)
def _digest(path,size,mtime):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def file_sha(path):
    path=Path(path); st=path.stat()
    return _digest(str(path),st.st_size,st.st_mtime_ns)


def read(path): return json.loads(Path(path).read_text())


def config():
    return dict(condition='S6-B17',arms=list(ARMS),rounds=ROUNDS,seed=SEED,workers=WORKERS,
        A=A,B=[],exam_seeds=[],max_games=MAX_GAMES,max_model_calls=MAX_CALLS,
        per_arm_candidate_slots=8,per_arm_model_call_cap=8,per_arm_candidate_game_cap=1280,
        shared_base_games=160,primary_game_cap=4000,independent_audit_game_cap=2000,
        paid=False,private=True,controller_max_descendants=synthesis.MAX_DESCENDANTS,
        shortlist=synthesis.SHORTLIST,model_free_arm_cannot_trade_tokens_for_games=True,
        criterion='>=2 A levels; zero individual loss; complete deterministic replay; independent audit',
        scope='development calibration only; no B, no exam, no S6 green claim',
        initial_policy='B14 378 levels and original accepted receipt only',
        rank='positive case read coverage, union-of-lineage loss read burden, literals, canonical',
        cache='shared physical cache; every candidate slot costs 160 logical games regardless of cache',
        audit='fresh process/cache; reconstruct all requests/verdicts; no generated answers',
        downstream='micro/audit only; a main-arm protocol must be frozen before pilot')


def previous_closure():
    old=read(PREVIOUS/'profile.json'); micro=read(PREVIOUS/'micro.json'); closed=read(PREVIOUS/'closed.json')
    if closed.get('result')!='MICRO_NO_PROMOTION' or closed.get('exam_opened') is not False \
            or micro.get('valid') is not True or micro['promote'] is not False \
            or micro['profile_sha256']!=sha(old) or len(micro['cells'])!=24:
        raise RuntimeError('valid negative B16 micro closure required')
    for path,digest in micro['artifacts'].items():
        if file_sha(PREVIOUS/path)!=digest:
            raise RuntimeError('B16 result changed: '+path)
    for path,digest in old['sources'].items():
        if file_sha(REPO/path)!=digest:
            raise RuntimeError('frozen B16 source changed: '+path)
    return dict(profile_sha256=sha(old),micro_sha256=sha(micro),closed_sha256=sha(closed))


def hashes(): return {n:file_sha(REPO/n) for n in SOURCES}


def profile():
    old=read(PREVIOUS/'profile.json')
    for path,digest in old['native_runtime']['artifacts'].items():
        if file_sha(REPO/path)!=digest: raise RuntimeError('native runtime changed')
    identity=model.identity()
    if identity!=old['model']: raise RuntimeError('inference model/budget changed')
    validation=read(ROOT/'validation.json')
    if validation.get('valid') is not True or validation['new_games'] or validation['new_model_calls'] \
            or validation['sources']!=hashes() or validation['tests_log_sha256']!=file_sha(ROOT/'qualification/tests.log'):
        raise RuntimeError('current instrument qualification required')
    return dict(sources=hashes(),configuration=config(),model=identity,native_runtime=old['native_runtime'],
        runtime=core.capacity.previous.runtime(),previous_closure=previous_closure(),
        validation_sha256=sha(validation))


def integrity():
    saved=read(ROOT/'profile.json')
    if saved!=json.loads(canonical(profile())): raise RuntimeError('frozen B17 profile changed')
    return saved


def prepare():
    if (ROOT/'profile.json').exists(): return integrity()
    frozen=profile()
    for name in SOURCES:
        path=ROOT/'source-archive'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream: stream.write((REPO/name).read_bytes())
    atomic(ROOT/'profile.json',frozen)
    atomic(ROOT/'prepared.json',dict(at=now(),profile_sha256=sha(frozen),exam_opened=False))
    publish('PREPARED')
    return frozen


def status(stage,**fields):
    value=dict(at=now(),condition='S6-B17',stage=stage,**fields)
    atomic(ROOT/'status.json',value)
    print(canonical(value),flush=True)


reserve_games=FunctionType(core.reserve_games.__code__,dict(core.reserve_games.__globals__,ROOT=ROOT,MAX_GAMES=MAX_GAMES))
_native_play=FunctionType(core.play_one.__code__,dict(core.play_one.__globals__,ROOT=ROOT,A=A,B=[],EXAM_SEEDS=(),
    evidence=SimpleNamespace(Recorder=timeline.Recorder,align_steps=timeline.align_steps)))


def worker_init(): OLD.worker_init()


def play_one(item):
    value,spec,directory=item
    if tuple(spec) not in A or directory is None:
        raise ValueError('B17 runs only observed development A')
    relative=Path(directory).resolve().relative_to(ROOT.resolve())
    if len(relative.parts)!=5 or relative.parts[0] not in ('primary','micro-independent') \
            or relative.parts[1]!='ephemeral-journals' or relative.parts[2] not in ('main','replay') \
            or relative.parts[3]!=core.Execution.digest(value):
        raise ValueError('invalid B17 journal destination')
    key=sha(dict(profile=sha(read(ROOT/'profile.json')),candidate=value,spec=tuple(spec),observed=True))
    if relative.parts[4]!=key: raise ValueError('invalid B17 cache key')
    started=time.monotonic()
    row=_native_play(item)
    cache=ROOT/relative.parts[0]/'cache'/relative.parts[2]/(key+'.json')
    atomic(cache,dict(key=key,digest=sha(row),record=row))
    shutil.rmtree(directory)
    atomic(ROOT/'worker-metrics'/(sha([value,spec,directory,os.getpid()])+'.json'),
        dict(seconds=time.monotonic()-started,rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             policy_sha256=core.Execution.digest(value),spec=spec,namespace=relative.parts[0]))
    return row


def measurement(namespace='primary'):
    if namespace not in ('primary','micro-independent'): raise ValueError('unknown namespace')
    out=ROOT/namespace;out.mkdir(parents=True,exist_ok=True)
    native=FunctionType(core.measure.__code__,dict(core.measure.__globals__,ROOT=out,LIVE=out/'ephemeral-journals',
        integrity=integrity,A=A,B=[],play_one=play_one,status=status,WORKERS=WORKERS,reserve_games=reserve_games,
        old=SimpleNamespace(worker_init=worker_init)),'measure',core.measure.__defaults__)
    def measure(label,value,specs,observed=True,replay=False):
        if list(map(tuple,specs))!=A or observed is not True:
            raise ValueError('B17 evaluation must cover exactly all observed A')
        return json.loads(canonical(native(label,value,specs,observed=observed,replay=replay)))
    return measure


def visible(kind,**fields):
    core.journal(ROOT/'live/journal.jsonl',dict(kind=kind,**fields))


def measured(measure,label,policy,audit):
    if audit: return measure(label,policy,A)
    return engine.reproduced(measure,label,policy,A)


def evaluate(measure,call,arm,index,req,response,policy,base,history,audit):
    event=dict(id=index+1,type=req['type'],target_id=req.get('target_id'),base_sha256=sha(policy),
               answer=response['answer'],usage=response['usage'],equivalent_calls=[])
    summary=dict(cell=call,arm=arm,round=index,passes_A=False,reproduced=False,levels=None,gain=0,
                 loss_indices=[],requested_operator=req['requested_operator'],actual_operator=None,
                 model_calls=int(arm!='synth'),logical_games=0)
    try:
        proposal=prompts.check_answer(response['answer'],req)
        candidate=core.strategy(program=core.patch.append(policy['program'],proposal))
    except ValueError as exc:
        return dict(event,verdict='V1',reason=str(exc)),dict(summary,verdict='V1')
    if not proposal['patches']:
        return dict(event,verdict='V1',reason='no remaining candidate'),dict(summary,verdict='V1')
    after=measured(measure,call+'/A',candidate,audit)
    if audit:
        old=read(ROOT/'primary/measurements'/call/'A.json')
        if after!=old: raise RuntimeError('independent candidate differs: '+call)
    diff=engine.difference(base,after)
    parameter=next(iter(proposal['patches'][0]['set']))
    development=(repair_outcomes.comparison(base,after) if arm=='b16'
                 else synthesis.comparison(base,after,parameter))
    passed=diff['gain']>=2 and not diff['loss_indices']
    event.update(proposal=proposal,candidate=candidate,A=diff,development=development,
        verdict='A_ONLY_PASS' if passed else 'V3',
        equivalent_calls=[e['id'] for e in history if e.get('development',{}).get('behavior_sha256')==development['behavior_sha256']])
    if not passed: event['decision_certificate']=memory.certificate(after['rows'],policy,candidate)
    summary.update(passes_A=passed,reproduced=True,levels=after['levels'],gain=diff['gain'],
        loss_indices=diff['loss_indices'],actual_operator=parameter,verdict=event['verdict'],logical_games=160,
        trace_digest=after['trace_digest'],proposal=proposal,changed_games=development['changed_games'],
        gross_level_gain=development['gross_level_gain'],gross_level_loss=development['gross_level_loss'])
    return event,summary


def run(audit=False):
    frozen=integrity(); profile_sha=sha(frozen)
    start=time.monotonic()
    policy,old,initial=reference_module.reference()
    measure=measurement('micro-independent' if audit else 'primary')
    base=measured(measure,'micro/baseline/A',policy,audit)
    clean=timeline.legacy_rows(base['rows'])
    if clean!=old['rows'] or sha(clean)!=old['trace_digest'] or base['levels']!=378 or base['score']!=old['score']:
        raise RuntimeError('B17 instrument changed full B14 baseline')
    if audit and base!=read(ROOT/'primary/measurements/micro/baseline/A.json'):
        raise RuntimeError('independent baseline differs')
    if not audit:
        atomic(ROOT/'parity.json',dict(valid=True,at=now(),levels=378,legacy_trace_sha256=sha(clean),
            new_trace_sha256=base['trace_digest'],consumption_timeline_reads=sum(len(r['diagnostics']['control_timeline']['reads']) for r in base['rows']),
            baseline_and_replay_identical=True))
    history={arm:list(initial) for arm in ARMS}
    cells=[]
    for index in range(ROUNDS):
        for arm in ARMS:
            call=f'micro/{arm}/{index:03d}'
            req=prompts.request(arm,index,policy,base,history[arm])
            path=ROOT/'steps'/(call+'.json')
            sampling_seed=SEED+index*1000
            if audit and not path.exists(): raise RuntimeError('missing primary verdict')
            saved=read(path) if path.exists() else None
            if saved and (saved['request_sha256']!=sha(req) or saved['request']!=req
                          or saved['profile_sha256']!=profile_sha):
                raise RuntimeError('request reconstruction mismatch: '+call)
            status('AUDIT_RECONSTRUCTING' if audit else 'MICRO_PROPOSING',cell=call,completed=len(cells),total=ROUNDS*len(ARMS))
            if arm=='synth':
                response=dict(answer=prompts.deterministic_answer(req),usage=dict(input_tokens=0,max_output_tokens=0))
                if saved and saved['event']['answer']!=response['answer']:
                    raise RuntimeError('deterministic synthesizer reconstruction mismatch')
            elif audit or (ROOT/'calls'/call/'result.json').exists():
                response=model.load(call,req,sampling_seed,ROOT,profile_sha,audit_tokens=audit)
            else:
                if saved: raise RuntimeError('verdict exists without model response')
                response=model.propose(call,req,sampling_seed,ROOT,profile_sha,MAX_CALLS)
            if saved and not audit:
                event,summary=saved['event'],saved['summary']
            else:
                event,summary=evaluate(measure,call,arm,index,req,response,policy,base,history[arm],audit)
                if audit:
                    if event!=saved['event'] or summary!=saved['summary']:
                        raise RuntimeError('independent verdict differs: '+call)
                else:
                    atomic(path,dict(event=event,summary=summary,request=req,request_sha256=sha(req),profile_sha256=profile_sha))
                    visible('answers',answers={'arms':{call:[dict(id=index+1,answer=response['answer'])]}})
                    visible('verdict',**event)
            history[arm].append(event);cells.append(summary)
            status('AUDIT_RESULT' if audit else 'MICRO_RESULT',cell=call,completed=len(cells),total=ROUNDS*len(ARMS),
                   levels=summary['levels'],gain=summary['gain'],losses=len(summary['loss_indices']))
    summary={arm:dict(proposals=sum(c['arm']==arm for c in cells),passes_A=sum(c['arm']==arm and c['passes_A'] for c in cells),
        best_levels=max((c['levels'] for c in cells if c['arm']==arm and c['levels'] is not None),default=None),
        first_pass_slot=next((c['round']+1 for c in cells if c['arm']==arm and c['passes_A']),None),
        model_calls=sum(c['model_calls'] for c in cells if c['arm']==arm),
        logical_candidate_games=sum(c['logical_games'] for c in cells if c['arm']==arm)) for arm in ARMS}
    result=dict(valid=True,at=now(),profile_sha256=profile_sha,cells=cells,summary=summary,
        promote=any(c['arm']=='hybrid' and c['passes_A'] for c in cells),s6_green=False,
        protected_games=0,exam_opened=False,seconds_this_invocation=time.monotonic()-start)
    if audit:
        primary=read(ROOT/'micro.json')
        if summary!=primary['summary'] or cells!=primary['cells'] or result['promote']!=primary['promote']:
            raise RuntimeError('audit totals differ')
        atomic(ROOT/'micro-audit.json',dict(valid=True,at=now(),independent_execution=True,
            cache='micro-independent/cache',verdicts_rebuilt=len(cells),profile_sha256=profile_sha,
            micro_sha256=sha(primary),summary=summary,protected_games=0,exam_opened=False,
            seconds_this_invocation=time.monotonic()-start))
    else:
        atomic(ROOT/'micro.json',result)
    return result


def publish(stage):
    result=read(ROOT/'micro.json') if (ROOT/'micro.json').exists() else None
    audit=read(ROOT/'micro-audit.json') if (ROOT/'micro-audit.json').exists() else None
    text=['# S6-B17 — síntesis acotada y control temporal','',f'Estado: **{stage}**. S6 sigue abierto.','',
        'Tres brazos: B16, síntesis sin LLM e híbrido. Ocho propuestas por brazo; mismo techo de partidas.',
        'Solo desarrollo A. Una mejora sin pérdidas requiere replay e independiente antes de proponer piloto.','']
    if result: text+=['| Brazo | Propuestas | Mejor total A | Pasan V3 A | Primera mejora |','| --- | ---: | ---: | ---: | ---: |']+[
        f"| {arm} | {s['proposals']} | {s['best_levels']} | {s['passes_A']} | {s['first_pass_slot']} |" for arm,s in result['summary'].items()]+['']
    if audit: text+=['Auditoría independiente: '+canonical({k:audit[k] for k in ('valid','verdicts_rebuilt','independent_execution')}),'']
    text+=['[Contrato](ECHO45-S6-B17-DESIGN.md) · [Estado](../lab/seed/s6b17-20261004/status.json).','']
    (REPO/'docs/ECHO45-S6-B17-RESULTS.md').write_text('\n'.join(text))
    begin,end='<!-- S6B17-BEGIN -->','<!-- S6B17-END -->'
    block=begin+f'\n**S6-B17: {stage}; S6 abierto.** Micro de tres brazos → auditoría independiente. '
    block+='[Contrato](ECHO45-S6-B17-DESIGN.md) · [Resultado](ECHO45-S6-B17-RESULTS.md).\n'+end
    for name in ('NOW.md','ECHO45-ECHO5-ROADMAP.md','RXLABS_STATUS.md'):
        path=REPO/'docs'/name;content=path.read_text()
        if begin in content:
            first,rest=content.split(begin,1);content=first+block+rest.split(end,1)[1]
        else:
            first,rest=content.split('\n',1);content=first+'\n\n'+block+'\n'+rest
        row=next((line for line in content.splitlines() if '| S6 B1–B5 |' in line),None)
        if row: content=content.replace(row,f'| ❌ | S6 B1–B5 | B17: {stage}; examen pendiente |',1)
        path.write_text(content)


def main(args):
    try:
        if args==['prepare']:
            prepare();return
        if args==['audit']:
            if not (ROOT/'micro.json').exists(): raise RuntimeError('micro missing')
            run(audit=True);return
        if args!=['follow']: raise ValueError('use prepare, follow or audit')
        prepare()
        with (ROOT/'pipeline.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if (ROOT/'closed.json').exists(): return
            journal=ROOT/'live/journal.jsonl';journal.parent.mkdir(parents=True,exist_ok=True);journal.touch(exist_ok=True)
            with (ROOT/'observer-process.log').open('a') as log:
                subprocess.Popen([sys.executable,str(REPO/'observe.py'),'--launch',str(journal)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            publish('MICRO_RUNNING')
            if not (ROOT/'micro.json').exists(): run()
            publish('MICRO_AUDITING')
            if not (ROOT/'micro-audit.json').exists():
                with (ROOT/'micro-audit-process.log').open('a') as log:
                    subprocess.run([sys.executable,'-u','-m','seed.s6b17','audit'],stdout=log,stderr=subprocess.STDOUT,check=True)
            audit=read(ROOT/'micro-audit.json');micro=read(ROOT/'micro.json')
            if not audit['valid'] or audit['micro_sha256']!=sha(micro) or audit['profile_sha256']!=sha(integrity()):
                raise RuntimeError('audit custody mismatch')
            budget=read(ROOT/'budget.json');model_budget=read(ROOT/'model-budget.json')
            physical={ns:sum(1 for _ in (ROOT/ns/'cache').glob('*/*.json'))
                      for ns in ('primary','micro-independent')}
            expected_calls={f'micro/{arm}/{index:03d}' for arm in ARMS if arm!='synth' for index in range(ROUNDS)}
            if set(model_budget['calls'])!=expected_calls or len(model_budget['calls'])!=MAX_CALLS \
                    or model_budget['spend_eur']!=0 or not sum(physical.values())<=budget['scheduled_games']<=MAX_GAMES \
                    or physical['primary']>4000 or physical['micro-independent']>2000:
                raise RuntimeError('closing resource ledger mismatch')
            stage='MICRO_AUDITED_READY_FOR_PILOT_DESIGN' if micro['promote'] else 'MICRO_AUDITED_NO_PROMOTION'
            atomic(ROOT/'closed.json',dict(at=now(),result=stage,s6_green=False,exam_opened=False,
                hybrid_passes=micro['summary']['hybrid']['passes_A'],pilot_started=False,
                budget=budget,model_budget=model_budget,physical_cache_records=physical))
            status('CLOSED',result=stage,s6_green=False);publish(stage)
    except Exception as exc:
        status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));publish('BLOCKED_INSTRUMENT')
        raise


if __name__=='__main__':
    from seed import s6b17
    s6b17.main(sys.argv[1:])
