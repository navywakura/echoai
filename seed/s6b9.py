"""B9: observed contradictions, bounded transition revision, paired CPU proposals."""
import hashlib
from importlib.util import module_from_spec,spec_from_file_location
import json
import os
from pathlib import Path
import subprocess
import sys
from types import FunctionType,SimpleNamespace

from seed import s6b8 as parent,s6_transition_capacity as control,s6_precise_capacity as capacity
from echo_arc import stale_transition as patch,repair_loop_requests as prompts
from echo_arc.repair_loop_observe import Recorder,traced_agent_class
from seed.game_selfimprove import atomic,canonical,sha,journal,events

REPO=parent.REPO
ROOT=REPO/'lab/seed/s6b9-20260929'
BASE=REPO/'lab/kaggle/s6b9-20260929'
LIVE=REPO/'lab/observability/s6b9-20260929'
A,B=control.A,control.B
EXAM_SEEDS=tuple(range(24700,24760))
SEEDS=(635001,635017,635029)
CAMPAIGN_SEEDS=(645001,)
MODEL,REVISION=parent.MODEL,parent.REVISION
CACHE_REF='rogeernavarro/echo45-s6-model-cache-20260929'
CACHE_MANIFEST=REPO/'lab/kaggle/s6-model-cache-20260929/output/manifest.json'
old,now,strategy=parent.old,parent.now,control.strategy
SOURCES=list(dict.fromkeys(control.SOURCES+['echo_arc/consumer_observe.py','echo_arc/consumer_requests.py',
    'echo_arc/parameter_first_grammar.py','echo_arc/repair_loop_observe.py','echo_arc/repair_loop_requests.py',
    'echo_arc/repair_loop_grammar.py','seed/s6b9.py','seed/s6b9_exam.py','tests/test_s6b9.py',
    'lab/kaggle/s6b9-20260929/generate.py','lab/kaggle/s6b9-20260929/transport.py',
    'lab/kaggle/cpu_inference_support.py','docs/ECHO45-S6-B9-DESIGN.md']))


def config():
    return {'A':A,'B':B,'exam_seeds':EXAM_SEEDS,'pilot_seeds':SEEDS,'campaign_seeds':CAMPAIGN_SEEDS,
            'pilot_rounds':3,'pilot_calls_per_arm_round':1,'campaign_rounds':6,'campaign_calls_per_arm_round':5,
            'calls_including_calibration':82,'cpu_jobs':9,'job_seconds':3600,'paid':False,'workers':4,
            'backend':'cpu-dynamic-int8','promotion':'ECHO accepts >=1 and paired A sum > FIJO',
            'criteria':'unchanged V1-V4 and B1-B5','prior_policies_in_prompts':False}


def hashes():return {p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in SOURCES}


def profile():
    return {'sources':hashes(),'configuration':config(),'capacity_profile_sha256':sha(control.integrity()),
            'capacity_audit_sha256':sha(json.loads((control.ROOT/'audit.json').read_text())),
            'cache_manifest_sha256':hashlib.sha256(CACHE_MANIFEST.read_bytes()).hexdigest(),
            'backend':'cpu-dynamic-int8','threads':4}


def integrity():
    value=json.loads((ROOT/'profile.json').read_text())
    assert value==json.loads(canonical(profile())), 'frozen B9 source changed'
    return value


def prepare():
    assert json.loads((control.ROOT/'audit.json').read_text())['valid'], 'instrument audit required'
    p=profile()
    if (ROOT/'profile.json').exists():integrity()
    else:
        for name in SOURCES:
            dest=ROOT/'source-archive'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((REPO/name).read_bytes())
        atomic(ROOT/'profile.json',p);atomic(ROOT/'prepared.json',{'at':now(),'profile_sha256':sha(p)})


def status(stage,**fields):
    row={'at':now(),'stage':stage,'condition':'S6-B9',**fields};atomic(ROOT/'status.json',row);print(canonical(row),flush=True)


class Execution(control.Execution):
    @staticmethod
    def play(env,budget,seed,value,recorder=None):
        if recorder is None:return control.Execution.play(env,budget,seed,value)
        interface=SimpleNamespace(agent_class=lambda program:traced_agent_class(program,recorder))
        play=FunctionType(capacity.Execution.play.__code__,dict(capacity.Execution.play.__globals__,
            patch=interface,Execution=Execution),'play',capacity.Execution.play.__defaults__)
        return play(env,budget,seed,value,recorder)


def play_one(item):
    value,spec,record_dir=item
    if spec[1] in EXAM_SEEDS:
        assert record_dir is None
        worker=FunctionType(parent.play_one.__code__,dict(parent.play_one.__globals__,ROOT=ROOT,
            EXAM_SEEDS=EXAM_SEEDS,Execution=Execution))
        record=worker(item);record['origin']='RESERVED_EXAM_S6B9';return record
    def recorder(journal):return Recorder(journal,origin='DEVELOPMENT_A',program=value['program'])
    worker=FunctionType(control.play_one.__code__,dict(control.play_one.__globals__,
        Execution=Execution,TransitionRecorder=recorder))
    return worker(item)


measure=FunctionType(capacity.measure.__code__,dict(capacity.measure.__globals__,ROOT=ROOT,LIVE=LIVE,
    Execution=Execution,integrity=integrity,status=status,play_one=play_one),'measure',capacity.measure.__defaults__)


def verifier(measurement):
    return FunctionType(parent.base.verify.__code__,dict(parent.base.verify.__globals__,A=A,B=B,
        patch=patch,strategy=strategy,c=SimpleNamespace(measure=measurement,result=capacity.result)),
        'verify',parent.base.verify.__defaults__)


requests=prompts.requests
raw_step=FunctionType(parent.raw_step.__code__,dict(parent.raw_step.__globals__,patch=patch,strategy=strategy))


def phase_shape(phase):
    assert phase in ('pilot','campaign')
    return (3,1,SEEDS) if phase=='pilot' else (6,5,CAMPAIGN_SEEDS)


def generator():
    spec=spec_from_file_location('_s6b9_generator',BASE/'generate.py')
    module=module_from_spec(spec);spec.loader.exec_module(module);return module


def load_phase(phase,index):return json.loads((ROOT/phase/f'round-{index}.json').read_text())


def audit_model(stage,requests_expected=None):
    assert json.loads((BASE/stage/'terminal.json').read_text())['status']=='COMPLETE'
    audit=FunctionType(parent.audit_model.__code__,dict(parent.audit_model.__globals__,BASE=BASE,
        generator=generator,integrity=integrity))
    return audit(stage,requests_expected)


run_phase=FunctionType(parent.run_phase.__code__,dict(parent.run_phase.__globals__,ROOT=ROOT,LIVE=LIVE,
    measure=measure,verifier=verifier,integrity=integrity,status=status,requests=requests,
    generator=generator,audit_model=audit_model,raw_step=raw_step,load_phase=load_phase,phase_shape=phase_shape,
    strategy=strategy,A=A,B=B),'run_phase',parent.run_phase.__defaults__)


def publish(stage):
    pilot=json.loads((ROOT/'pilot.json').read_text()) if (ROOT/'pilot.json').exists() else None
    audit=json.loads((ROOT/'exam/audit.json').read_text()) if (ROOT/'exam/audit.json').exists() else None
    lines=['# S6-B9 · reparación guiada por contradicciones','',f'Estado: **{stage}**. S6 verde: **{bool(audit and audit["green"])}**.','',
        'Modelo Qwen fijado, backend CPU int8 declarado; ECHO y FIJO parten de SEMILLA vacía. El control humano no entra en prompts.','']
    if pilot:lines += ['Piloto: '+canonical({k:pilot[k] for k in ('paired_A','accepted_echo','promote')}),'']
    if audit:lines += ['Criterios: '+canonical(audit['checks']),'Totales: '+canonical(audit['totals']),'']
    lines += ['[Contrato](ECHO45-S6-B9-DESIGN.md) · [Estado](../lab/seed/s6b9-20260929/status.json).','']
    (REPO/'docs/ECHO45-S6-B9-RESULTS.md').write_text('\n'.join(lines))


def preflight():
    if (ROOT/'preflight.json').exists():return
    for name,specs,visible in (('A',A,True),('B',B,False)):
        measured=measure('baseline/'+name,strategy(),specs,observed=visible)
        native=json.loads((control.ROOT/f'measurements/baseline/{name}.json').read_text())
        assert all(capacity.same_behavior(a,b) for a,b in zip(native['rows'],measured['rows']))
    atomic(ROOT/'preflight.json',{'at':now(),'pass':True,'native_parity':True,'exam_opened':False,
                                 'profile_sha256':sha(integrity())})


def follow():
    prepare()
    if (ROOT/'closed.json').exists():return
    preflight()
    for phase in ('pilot','campaign'):
        path=ROOT/(phase+'.json')
        if path.exists():result=json.loads(path.read_text())
        else:
            atomic(ROOT/(phase+'-process.json'),{'at':now(),'pid':os.getpid()})
            result=run_phase(phase)
        if not (ROOT/(phase+'-audit.json')).exists():
            status('AUDIT',phase=phase)
            with (ROOT/(phase+'-audit-process.log')).open('a') as stream:
                subprocess.run([sys.executable,'-m','seed.s6b9','audit',phase],check=True,stdout=stream,stderr=subprocess.STDOUT)
        if phase=='pilot' and not result['promote']:
            atomic(ROOT/'closed.json',{'at':now(),'result':'PILOT_NO_PROMOTION','s6_green':False,'exam_opened':False})
            publish('PILOT_NO_PROMOTION');status('CLOSED',s6_green=False);return
    policies={'semilla':strategy(),'sinfiltro':result['raw'],**{r['arm']:r['strategy'] for r in result['finals']}}
    atomic(ROOT/'strategies.json',policies)
    atomic(ROOT/'completed.json',{'at':now(),'sources':hashes(),'strategies_sha256':sha(policies),'profile_sha256':sha(integrity())})
    from seed import s6b9_exam
    s6b9_exam.run()
    audit=json.loads((ROOT/'exam/audit.json').read_text())
    atomic(ROOT/'closed.json',{'at':now(),'result':'EXAM_CLOSED','s6_green':audit['green'],'checks':audit['checks']})
    publish('EXAM_CLOSED');status('CLOSED',s6_green=audit['green'])


def main(args):
    try:
        if args==['prepare']:prepare()
        elif args==['follow']:follow()
        elif len(args)==2 and args[0]=='audit':run_phase(args[1],audit=True)
        else:raise SystemExit('use prepare, follow, audit pilot/campaign')
    except Exception as exc:
        status('PENDING_ERROR',error=type(exc).__name__,message=str(exc));publish('PENDING_ERROR');raise


if __name__=='__main__':
    from seed import s6b9
    s6b9.main(sys.argv[1:])
