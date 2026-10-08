"""Frozen functional fusion certificate, with isolated sensor replay."""
import argparse
import copy
import json
import subprocess
import sys
import time
from pathlib import Path
from . import core, judge, scenarios, replay
from .integration import admit
from echoai.nexus0.sim3 import sandbox
from echoai.nexus0.sim3.runtime import Runtime

HERE=Path(__file__).resolve().parent
ROOT=replay.ECHOAI/'lab/fusion1'
REPORT=replay.ECHOAI/'lab/echo3_fusion1_report.json'
PROTOCOL=dict(version=1,ttl_ns=250_000_000,skew_ns=100_000_000,capacity=512,
              development=dict(seed=20261701,repetitions=4),
              validation=dict(seed=20261702,repetitions=16),
              confirmation=dict(seed=20261703,repetitions=32),
              physical_replay_windows=240,physical_replay_flights=12,
              scope='functional_fusion_and_reduced_sitl_sensor_replay',
              hardware=False,integrated_navigation=False)
TARGETS=dict(last_writer='conflict',no_expiry='expired',duplicate_votes='duplicates',
             ignore_predicate='different_predicate',ignore_region='different_region',
             erase_conflict='conflict',constant_confidence='no_return',unsafe_gate='blocked')


def seal(d):
    d={k:v for k,v in d.items() if k!='sha256'}
    return dict(d,sha256=core.digest(d))


def save(path,d):
    path.parent.mkdir(parents=True,exist_ok=True)
    with open(path,'x') as f:json.dump(d,f,sort_keys=True,indent=2,allow_nan=False)


def inventory():
    paths=list(HERE.glob('*.py'))+[replay.ECHOAI/'tests/test_fusion1.py',replay.ECHOAI/'docs/FUSION1-DESIGN.md',
          replay.ECHOAI/'nexus0/gate.py',replay.ECHOAI/'nexus0/constants.py',
          replay.ECHOAI/'nexus0/sim3/sandbox.py',replay.ECHOAI/'nexus0/sim3/runtime.py',
          replay.ECHOAI/'nexus0/ground1/evaluate.py',replay.ECHOAI/'nexus0/loop.py',
          replay.ECHOAI.parent/'core/cam.py',replay.ECHOAI.parent/'core/qn.py',
          replay.ECHOAI.parent/'core/spoke.py',replay.ECHOAI.parent/'core/wsp.py']
    return {str(p.relative_to(replay.ECHOAI) if p.is_relative_to(replay.ECHOAI) else Path('..')/p.name):replay.file_hash(p) for p in sorted(paths)}


def cage_run(cases,mutant=''):
    request=''.join(json.dumps(dict(commands=c['commands'],mutant=mutant),sort_keys=True)+'\n' for c in cases)
    pr=subprocess.run(sandbox.bwrap_argv(HERE/'core.py'),input=request.encode(),capture_output=True,timeout=120)
    if pr.returncode or pr.stderr:
        raise RuntimeError('caged consumer: '+pr.stderr.decode()[-800:])
    outputs=[json.loads(line) for line in pr.stdout.splitlines()]
    if len(outputs)!=len(cases):raise RuntimeError('consumer denominator')
    return outputs


def assess(cases,outputs):
    groups={};unsafe=useful=baseline_unsafe=baseline_useful=gate_mismatches=0
    for case,result in zip(cases,outputs):
        kind=case['condition'];g=groups.setdefault(kind,dict(episodes=0,passed=0,queries=0,findings=[]))
        fs=judge.findings(case['commands'],result)
        g['episodes']+=1;g['passed']+=not fs;g['queries']+=len(result['decisions'])
        if fs:g['findings'].append(dict(repetition=case['repetition'],errors=fs))
        expected=judge.expected(case['commands']);control=judge.last_writer(case['commands'])
        for actual,want,last in zip(result['decisions'],expected,control):
            gate_decision=admit(bytes.fromhex(actual['wsp']))
            gate_mismatches += (gate_decision[0]==0) != actual['allow_advance']
            unsafe+=actual['allow_advance'] and not want['allow_advance']
            useful+=actual['allow_advance'] and want['allow_advance']
            baseline_unsafe+=last and not want['allow_advance']
            baseline_useful+=last and want['allow_advance']
    for g in groups.values():
        g['interval_95']=judge.wilson(g['passed'],g['episodes'])
    return dict(groups=groups,unsafe_permissions=unsafe,useful_permissions=useful,gate_mismatches=gate_mismatches,
                last_writer=dict(unsafe_permissions=baseline_unsafe,useful_permissions=baseline_useful),
                always_unknown=dict(unsafe_permissions=0,useful_permissions=0),
                passed=all(g['episodes']==g['passed'] for g in groups.values()) and len(cases)==len(outputs) and gate_mismatches==0)


def measure_core(cases):
    durations=[]
    for case in cases:
        m=core.EvidenceMemory()
        for c in case['commands']:
            if c['op']=='observe':
                m.ingest(bytes.fromhex(c['wsp']),**{k:v for k,v in c.items() if k not in ('op','wsp')})
            else:
                t=time.perf_counter_ns();m.resolve(**{k:v for k,v in c.items() if k!='op'})
                durations.append(time.perf_counter_ns()-t)
    ordered=sorted(durations)
    return dict(scope='host_resolve_only_not_flight',samples=len(durations),
                p99_ns=ordered[min(len(ordered)-1,len(ordered)*99//100)],max_ns=max(ordered),
                ledger_capacity_records=512,neurons_added=0)


def stage(name,cases):
    outputs=cage_run(cases)
    result=seal(dict(name=name,cases=cases,outputs=outputs,assessment=assess(cases,outputs),performance=measure_core(cases)))
    save(ROOT/name/'report.json',result)
    print(json.dumps(dict(stage=name,passed=result['assessment']['passed'],episodes=len(cases))),flush=True)
    return result


def audit_stage(r,cases):
    findings=[]
    if r!=seal(r):findings.append('report_hash')
    if r.get('cases')!=cases:findings.append('inputs')
    if len(r.get('outputs',[]))!=len(cases):findings.append('outputs_denominator')
    recalculated=[core.run_commands(c['commands']) for c in cases]
    if r.get('outputs')!=recalculated:findings.append('outputs_recomputed')
    expected=assess(cases,recalculated)
    if r.get('assessment')!=expected:findings.append('assessment')
    return dict(evidence_valid=not findings,findings=findings,passed=expected['passed'],episodes=len(cases))


def mutations(r,cases):
    changes={
        'omit_episode':lambda d:d['cases'].pop(),
        'fake_green':lambda d:d['assessment'].update(passed=not d['assessment']['passed']),
        'alter_wsp':lambda d:d['outputs'][0]['decisions'][0].update(wsp='00'*16),
        'alter_source':lambda d:d['cases'][0]['commands'][0].update(source='host'),
        'alter_time':lambda d:d['cases'][0]['commands'][0].update(capture_ns=0),
        'alter_control':lambda d:d['assessment']['last_writer'].update(unsafe_permissions=-1),
        'alter_hash':lambda d:d.update(sha256='0'*64)}
    results=[]
    for name,change in changes.items():
        d=copy.deepcopy(r);change(d)
        if name!='alter_hash':d=seal(d)
        a=audit_stage(d,cases)
        results.append(dict(name=name,caught=not a['evidence_valid'],findings=a['findings']))
    return results


def control_mutants(cases):
    results=[]
    for mutant,condition in TARGETS.items():
        chosen=[c for c in cases if c['condition']==condition]
        out=cage_run(chosen,mutant)
        caught=[bool(judge.findings(c['commands'],r)) for c,r in zip(chosen,out)]
        twin=[not judge.findings(c['commands'],core.run_commands(c['commands'])) for c in chosen]
        results.append(dict(mutant=mutant,condition=condition,episodes=len(chosen),
                            caught=sum(caught),honest_passed=sum(twin),
                            passed=all(caught) and all(twin) and bool(chosen)))
    return results


def develop():
    cases=scenarios.generate(**PROTOCOL['development'])
    out=cage_run(cases)
    r=seal(dict(protocol=PROTOCOL,inventory=inventory(),assessment=assess(cases,out),
                mutants=control_mutants(cases)))
    save(ROOT/'development.json',r)
    print(json.dumps(r['assessment'],indent=2))
    return r['assessment']['passed'] and all(m['passed'] for m in r['mutants'])


def accept():
    if REPORT.exists() or (ROOT/'lock.json').exists():raise FileExistsError('immutable campaign already started')
    dev=json.loads((ROOT/'development.json').read_text())
    if dev['inventory']!=inventory() or not dev['assessment']['passed'] or not all(m['passed'] for m in dev['mutants']):
        raise ValueError('development not green/current')
    physical,pins=replay.build()
    prior=json.loads((replay.ECHOAI/'lab/pattern1r-v4/lock.json').read_text())
    runtime=Runtime(available=True,lock=prior['cage'])
    isolation=sandbox.self_test(runtime)
    if not isolation['ok']:raise RuntimeError('SIM-3 cage self-test failed '+str(isolation))
    regression=subprocess.run([sys.executable,'-m','echoai.tests.test_fusion1','-q'],capture_output=True)
    save(ROOT/'regression.json',dict(returncode=regression.returncode,output=(regression.stdout+regression.stderr).decode()))
    if regression.returncode:raise RuntimeError('regression')
    lock=seal(dict(protocol=PROTOCOL,inventory=inventory(),parent_files=pins,
                   development_sha256=dev['sha256'],isolation=isolation,
                   regression_sha256=replay.file_hash(ROOT/'regression.json')))
    save(ROOT/'lock.json',lock)
    stages={};errors=[];confirmed=None
    try:
        for name,cases in [('validation',scenarios.generate(**PROTOCOL['validation'])),
                           ('confirmation',scenarios.generate(**PROTOCOL['confirmation'])),
                           ('physical_replay',physical)]:
            r=stage(name,cases);a=audit_stage(r,cases);stages[name]=a
            if not a['evidence_valid'] or not a['passed']:break
        confirmed=json.loads((ROOT/'confirmation/report.json').read_text()) if (ROOT/'confirmation/report.json').exists() else None
        mut=control_mutants(confirmed['cases']) if confirmed else []
        tamper=mutations(confirmed,scenarios.generate(**PROTOCOL['confirmation'])) if confirmed else []
    except Exception as exc:
        errors.append(type(exc).__name__+': '+str(exc));mut=[];tamper=[]
    valid=not errors and inventory()==lock['inventory'] and all(a['evidence_valid'] for a in stages.values())
    green=valid and len(stages)==3 and all(a['passed'] for a in stages.values()) and len(mut)==8 and all(m['passed'] for m in mut) and len(tamper)==7 and all(m['caught'] for m in tamper)
    if confirmed:
        a=confirmed['assessment'];green &= a['unsafe_permissions']==0 and a['useful_permissions']>0 and a['last_writer']['unsafe_permissions']>a['unsafe_permissions']
    result=seal(dict(fusion1_green=bool(green),evidence_valid=valid,lock_sha256=lock['sha256'],stages=stages,
                     mutants=mut,tamper_tests=tamper,errors=errors,scope=PROTOCOL['scope']))
    save(REPORT,result)
    print(json.dumps(result,indent=2),flush=True)
    return green


def audit():
    lock=json.loads((ROOT/'lock.json').read_text());final=json.loads(REPORT.read_text())
    issues=[]
    if lock!=seal(lock) or final!=seal(final) or final['lock_sha256']!=lock['sha256']:issues.append('hash')
    if lock['protocol']!=PROTOCOL or lock['inventory']!=inventory():issues.append('code/protocol')
    if replay.file_hash(ROOT/'regression.json')!=lock['regression_sha256']:issues.append('regression')
    dev=json.loads((ROOT/'development.json').read_text())
    if dev!=seal(dev) or dev['sha256']!=lock['development_sha256']:issues.append('development')
    physical,pins=replay.build()
    if pins!=lock['parent_files']:issues.append('parent_files')
    stages={}
    for name,cases in [('validation',scenarios.generate(**PROTOCOL['validation'])),('confirmation',scenarios.generate(**PROTOCOL['confirmation'])),('physical_replay',physical)]:
        stages[name]=audit_stage(json.loads((ROOT/name/'report.json').read_text()),cases)
    if stages!=final['stages']:issues.append('stage_summary')
    # Mutants have a fresh independent execution here, not trusted green flags.
    cases=scenarios.generate(**PROTOCOL['confirmation'])
    mutants=[]
    for m,k in TARGETS.items():
        rows=[r for r in cases if r['condition']==k]
        mutants.append(dict(mutant=m,condition=k,episodes=len(rows),
            caught=sum(bool(judge.findings(r['commands'],core.run_commands(r['commands'],m))) for r in rows),
            honest_passed=sum(not judge.findings(r['commands'],core.run_commands(r['commands'])) for r in rows),passed=True))
    if mutants!=final['mutants'] or any(m['caught']!=m['episodes'] or m['honest_passed']!=m['episodes'] for m in mutants):issues.append('mutants')
    tamper=mutations(json.loads((ROOT/'confirmation/report.json').read_text()),cases)
    if tamper!=final['tamper_tests']:issues.append('tamper_tests')
    valid=not issues and all(a['evidence_valid'] for a in stages.values())
    green=valid and all(a['passed'] for a in stages.values()) and all(m['caught'] for m in tamper)
    if final['evidence_valid']!=valid or final['fusion1_green']!=green or final['errors']:issues.append('final_summary')
    result=dict(evidence_valid=not issues and valid,fusion1_green=not issues and green,findings=issues,stages=stages)
    print(json.dumps(result,indent=2));return result['fusion1_green']


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('develop','accept','audit'))
    args=ap.parse_args();raise SystemExit(0 if globals()[args.command]() else 1)
