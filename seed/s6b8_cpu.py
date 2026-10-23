"""Separate paired CPU continuation of B8; all original scientific gates kept."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import FunctionType, SimpleNamespace
from importlib.util import module_from_spec, spec_from_file_location

from seed import s6b8 as parent, s6_precise_capacity as capacity
from seed.game_selfimprove import atomic, canonical, sha, journal, events

REPO = parent.REPO
ROOT = REPO / "lab/seed/s6b8-cpu-20260929"
BASE = REPO / "lab/kaggle/s6b8-cpu-20260929"
LIVE = REPO / "lab/observability/s6b8-cpu-20260929"
CACHE_MANIFEST = REPO / "lab/kaggle/s6-model-cache-20260929/output/manifest.json"
CACHE_REF = "navywakura/echo45-s6-model-cache-20260929"
MODEL, REVISION = parent.MODEL, parent.REVISION
A, B, EXAM_SEEDS = parent.A, parent.B, parent.EXAM_SEEDS
strategy, patch, Execution, old = parent.strategy, parent.patch, parent.Execution, parent.old
GPU_JOB_CAP = 3600  # Interface name reused by generator; this transport is CPU-only.
SOURCES = ("seed/s6b8_cpu.py", "lab/kaggle/s6b8-cpu-20260929/generate.py",
           "lab/kaggle/s6b8-cpu-20260929/transport.py", "docs/ECHO45-S6-B8-CPU-DESIGN.md",
           "tests/test_s6b8_cpu.py")
now = parent.now


def profile():
    return {"parent_profile_sha256": sha(parent.integrity()), "sources": {
        name: parent.hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in SOURCES},
        "history": {str(r): sha(parent.load_phase('pilot', r)) for r in (0, 1)},
        "cache_manifest_sha256": parent.hashlib.sha256(CACHE_MANIFEST.read_bytes()).hexdigest(),
        "backend": "cpu-float16", "threads": 4, "cpu_seconds_cap": 3600, "paid": False}


def integrity():
    assert json.loads((ROOT / 'cpu-profile.json').read_text()) == profile()
    return parent.integrity()  # Unchanged actor/grammar provenance; CPU provenance is additional.


def hashes():
    return dict(parent.hashes(), **profile()['sources'])


def prepare():
    manifest = json.loads(CACHE_MANIFEST.read_text())
    assert manifest['complete'] and manifest['model'] == MODEL and manifest['revision'] == REVISION
    assert manifest['weight_shards'] == 4
    assert all(r['lfs_sha256_checked'] for name, r in manifest['files'].items() if name.endswith('.safetensors'))
    p = profile()
    if (ROOT / 'cpu-profile.json').exists():
        integrity()
        if (ROOT / 'prepared.json').exists():
            return
    else:
        atomic(ROOT / 'cpu-profile.json', p)
    for name in SOURCES:
        target=ROOT/'source-archive'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((REPO/name).read_bytes())
    for r in (0, 1):
        atomic(ROOT/'pilot'/f'round-{r}.json', parent.load_phase('pilot', r))
    # Copy only deterministic records, never the original experiment's directories
    # by writable link. Reuse is declared and independently checked by the auditor.
    for name in ('cache', 'pilot-audit/cache'):
        shutil.copytree(parent.ROOT/name, ROOT/name, dirs_exist_ok=True)
    atomic(ROOT/'prepared.json', {'at':now(),'cpu_profile_sha256':sha(p),'inherited_rounds':[0,1]})


def status(stage, **fields):
    value = dict(at=now(),stage=stage,condition='S6-B8-CPU',**fields)
    atomic(ROOT/'status.json',value);print(canonical(value),flush=True)


def play_one(item):
    worker=FunctionType(parent.play_one.__code__,dict(parent.play_one.__globals__,ROOT=ROOT))
    return worker(item)


measure=FunctionType(capacity.measure.__code__,dict(parent.measure.__globals__,
    ROOT=ROOT,LIVE=LIVE,integrity=integrity,status=status,play_one=play_one),
    'measure',capacity.measure.__defaults__)


def generator():
    spec=spec_from_file_location('_s6b8_cpu_generator',BASE/'generate.py')
    module=module_from_spec(spec);spec.loader.exec_module(module);return module


def load_phase(phase, round_id):
    return json.loads((ROOT / phase / f'round-{round_id}.json').read_text())


def audit_model(stage, requests_expected=None):
    integrity()
    if stage in ('p0','p1'):
        return parent.audit_model(stage,requests_expected)
    assert json.loads((BASE/stage/'terminal.json').read_text())['status']=='COMPLETE'
    audit=FunctionType(parent.audit_model.__code__,dict(parent.audit_model.__globals__,
        BASE=BASE,generator=generator,integrity=integrity))
    result=audit(stage,requests_expected)
    assert result['profile']['backend']=='cpu-float16'
    assert all(value=='cpu' for value in result['profile']['devices'].values())
    return result


run_phase=FunctionType(parent.run_phase.__code__,dict(parent.run_phase.__globals__,
    ROOT=ROOT,LIVE=LIVE,measure=measure,generator=generator,audit_model=audit_model,
    integrity=integrity,status=status,load_phase=load_phase),'run_phase',parent.run_phase.__defaults__)


def publish(state):
    pilot_path=ROOT/'pilot.json';pilot=json.loads(pilot_path.read_text()) if pilot_path.exists() else None
    audit_path=ROOT/'exam/audit.json';audit=json.loads(audit_path.read_text()) if audit_path.exists() else None
    lines=['# S6-B8-CPU · continuación declarada','',f'Estado: **{state}**. S6 VERDE: **{bool(audit and audit["green"])}**.','',
           'Dos rondas B8 heredadas de GPU; tercera ronda y campaña condicional en CPU float16. Mismos pesos y prompts; muestreo no bit-equivalente a CUDA.','']
    if pilot:lines += [f"Piloto: ECHO {pilot['paired_A']['echo']}, FIJO {pilot['paired_A']['fijo']}; aceptaciones ECHO {pilot['accepted_echo']}; promoción {pilot['promote']}.",'']
    if audit:lines += ['Criterios: '+canonical(audit['checks']),'Totales: '+canonical(audit['totals']),'']
    lines += ['[Contrato](ECHO45-S6-B8-CPU-DESIGN.md) · [Datos](../lab/seed/s6b8-cpu-20260929/) · [B8 original](ECHO45-S6-B8-RESULTS.md).','']
    (REPO/'docs/ECHO45-S6-B8-CPU-RESULTS.md').write_text('\n'.join(lines))


def follow():
    prepare()
    if (ROOT/'closed.json').exists():return
    for phase in ('pilot','campaign'):
        path=ROOT/(phase+'.json')
        if path.exists():result=json.loads(path.read_text())
        else:
            atomic(ROOT/(phase+'-process.json'),{'pid':os.getpid(),'at':now()})
            result=run_phase(phase)
        if not (ROOT/(phase+'-audit.json')).exists():
            status('AUDIT',phase=phase)
            with (ROOT/(phase+'-audit-process.log')).open('a') as stream:
                subprocess.run([sys.executable,'-m','seed.s6b8_cpu','audit',phase],check=True,stdout=stream,stderr=subprocess.STDOUT)
        if phase=='pilot' and not result['promote']:
            atomic(ROOT/'closed.json',{'at':now(),'stage':'CLOSED','result':'PILOT_NO_PROMOTION','s6_green':False,
                                       'exam_opened':False,'cpu_profile_sha256':sha(profile())})
            publish('PILOT_NO_PROMOTION');status('CLOSED',s6_green=False,result='PILOT_NO_PROMOTION');return
    policies={'semilla':strategy(),'sinfiltro':result['raw']}
    policies.update({r['arm']:r['strategy'] for r in result['finals']})
    atomic(ROOT/'strategies.json',policies)
    atomic(ROOT/'completed.json',{'strategies_sha256':sha(policies),'profile_sha256':sha(integrity()),'sources':hashes(),'at':now()})
    assert not (parent.ROOT/'exam/opened.json').exists(), 'reserve already used by original condition'
    from seed import s6b8_exam
    proxy=SimpleNamespace(**dict(vars(parent),ROOT=ROOT,BASE=BASE,integrity=integrity,hashes=hashes,audit_model=audit_model,status=status))
    exam_measure=FunctionType(capacity.measure.__code__,dict(measure.__globals__,ROOT=ROOT/'exam/measurements'),
                              'measure',capacity.measure.__defaults__)
    exam=FunctionType(s6b8_exam.run.__code__,dict(s6b8_exam.run.__globals__,s=proxy,measure=exam_measure))
    exam()
    audit=json.loads((ROOT/'exam/audit.json').read_text())
    atomic(ROOT/'closed.json',{'at':now(),'stage':'CLOSED','result':'EXAM_CLOSED','s6_green':audit['green'],
                              'checks':audit['checks'],'cpu_profile_sha256':sha(profile())})
    publish('EXAM_CLOSED');status('CLOSED',s6_green=audit['green'],checks=audit['checks'])


def main(args):
    try:
        if args==['prepare']:prepare()
        elif args==['follow']:follow()
        elif len(args)==2 and args[0]=='audit':
            run_phase(args[1],audit=True)
            atomic(ROOT/(args[1]+'-cpu-audit.json'),{'valid':True,'cpu_profile_sha256':sha(profile())})
        else:raise SystemExit('use prepare, follow or audit pilot/campaign')
    except Exception as exc:
        status('PENDING_ERROR',error=type(exc).__name__,message=str(exc));publish('PENDING_ERROR');raise


if __name__=='__main__':
    from seed import s6b8_cpu
    s6b8_cpu.main(sys.argv[1:])
