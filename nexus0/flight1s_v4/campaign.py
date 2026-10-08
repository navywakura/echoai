"""One prospective chain, raw evidence, and an audit that rebuilds its verdict."""
import copy
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

from echoai.nexus0.flight1s.v3 import campaign as c, certificate as legacy
from echoai.nexus0.flight1s.session import Episode
from echoai.nexus0.flight1s import worldbuild
from echoai.nexus0.flight1s.runtime import Runtime
from echoai.nexus0.flight1s.v2.audit import _recompute
from echoai.nexus0.sim3.canon import dump_report, report_sha256, sha256_bytes
from . import contract

ROOT = c.ECHOAI/'lab/flight1s-v4'
REPORT = c.ECHOAI/'lab/echo3_flight1s_v4_report.json'
MODULES = ('test_flight1s_v4','test_flight1s_v3','test_flight1s_v2',
           'test_flight1s','test_flight1s_backend','test_sim3','test_nexus0')


def read(path):
    return json.loads(path.read_text())


def relative(path):
    return str(path.relative_to(c.ECHOAI))


def seal(d):
    d = {k:v for k,v in d.items() if k!='sha256'}
    return dict(d, sha256=report_sha256(d))


def save(path, d):
    if path.exists():
        raise FileExistsError('Immutable evidence already exists: '+str(path))
    dump_report(path, d)


def fingerprint(paths):
    files = {relative(p):sha256_bytes(p.read_bytes()) for p in sorted(set(paths))}
    return seal(dict(files=files))


def history():
    paths = []
    for name in ('flight1s','flight1s-v2','flight1s-v3'):
        paths += [p for p in (c.ECHOAI/'lab'/name).rglob('*') if p.is_file()]
        paths += [p for p in (c.ECHOAI/'docs/examples'/name).rglob('*') if p.is_file()]
    for p in (c.ECHOAI/'lab').glob('echo3_flight1s*.json'):
        if '_v4_' not in p.name:
            paths.append(p)
    paths += [p for p in (c.ECHOAI/'docs').glob('FLIGHT1S*.md') if '-V4-' not in p.name]
    return fingerprint(paths)


def inventory():
    paths = [c.ECHOAI/p for p in c.inventory()['files']]
    for name in ('flight1s_v4', 'sim3'):
        paths += list((c.ECHOAI/'nexus0'/name).rglob('*.py'))
    paths += [c.ECHOAI/'docs/FLIGHT1S-V4-DESIGN.md']
    paths += [c.ECHOAI/'tests'/(m+'.py') for m in MODULES]
    paths += [c.ECHOAI/'nexus0/flight1s/container/Containerfile']
    return fingerprint(paths)


def regression():
    cases = []
    for mod in MODULES:
        print('regression '+mod, flush=True)
        pr = subprocess.run([sys.executable,'-m','echoai.tests.'+mod,'-q'],
                            env=dict(os.environ, PYTHONPATH=str(c.ECHOAI.parent)),
                            cwd=c.ECHOAI, capture_output=True, timeout=2400)
        log = ROOT/'regression'/(mod+'.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_bytes(pr.stdout+pr.stderr)
        cases.append(dict(name=mod, ok=pr.returncode==0, returncode=pr.returncode,
                          path=relative(log), sha256=sha256_bytes(log.read_bytes())))
    return contract.group(cases)


def freeze():
    if ROOT.exists() or REPORT.exists():
        raise FileExistsError('v4 already started; audit or resume the frozen chain')
    ROOT.mkdir(parents=True)
    p = contract.protocol()
    inv = inventory()
    reg = regression()
    save(ROOT/'regression.json', reg)
    if reg['status'] != 'pass' or inv != inventory():
        raise RuntimeError('Regression failed or code changed; no flights authorised')
    runtime = c.preflight(write=False)
    runtime.require()
    image_id = runtime.lock['container'].get('image_id') or subprocess.check_output(
        ['podman','image','inspect',runtime.image,'--format','{{.Id}}'],text=True).strip()
    runtime.lock['container']['image'] = image_id
    runtime.lock['lock_sha256'] = report_sha256({k:v for k,v in runtime.lock.items() if k!='lock_sha256'})
    hist = history()
    save(ROOT/'history.json', hist)
    lock = seal(dict(version=4, created_utc=datetime.now(timezone.utc).isoformat(),
                     protocol=p, protocol_sha256=report_sha256(p), inventory=inv,
                     runtime=runtime.lock, history_sha256=hist['sha256'], regression=reg))
    save(ROOT/'lock.json', lock)
    save(ROOT/'protocol.json', p)
    print('FROZEN '+lock['sha256'], flush=True)
    return lock


def suite(root, stage, p):
    return c.generate_suite(root, c.load_protocol(c.WORLD_PROTOCOL), c.REHEARSAL_SECRET,
                            c.rehearsal_assignment())[:p['stages'][stage]['worlds']]


def jobs(packages, stage, p):
    spec = p['stages'][stage]
    order = c.condition_order(spec['seed'], len(packages)*spec['repeats'])
    result = []
    for i,g in enumerate(packages):
        for repeat in range(1,spec['repeats']+1):
            slot = i*spec['repeats']+repeat-1
            for condition in order[2*slot:2*slot+2]:
                result.append((g,condition,repeat,slot))
    return result


def metadata(g, condition, repeat, slot, lock, root):
    label = f'{condition}-{g.package_id}-r{repeat}'
    return dict(label=label, condition=condition, package_id=g.package_id,
                split=g.split, repeat=repeat, order_slot=slot, protocol_version=4,
                lock_sha256=lock['sha256'], protocol_sha256=lock['protocol_sha256'],
                trace=relative(root/'episodes'/(label+'.json')))


def negative_group(negatives):
    return contract.group([dict(label=m['label'], ok=bool(m['ok']
                        and m['parameters']['ok'] and not m['stimulus']['ok']
                        and abs(m.get('impulse',{}).get('ratio_ppk',9999))<500))
                           for m in negatives])


def run_stage(lock, stage):
    root = ROOT/stage
    if root.exists():
        raise FileExistsError('Stage is immutable: '+stage)
    p = lock['protocol']
    if stage == 'bench':
        a = read(ROOT/'validation/report.json')
        audited = audit_stage(a, lock)
        save(ROOT/'validation/audit.json', audited)
        if not a['passed'] or not audited['evidence_valid']:
            raise RuntimeError('Validation A failed; bank not authorised')
    root.mkdir()
    if inventory()!=lock['inventory'] or history()['sha256']!=lock['history_sha256']:
        raise RuntimeError('Frozen code/history changed')
    runtime = Runtime(available=True,lock=lock['runtime'])
    packages = suite(root/'suite', stage, p)
    schedule = jobs(packages,stage,p)
    start = time.monotonic()
    def one(job):
        g,cond,repeat,slot = job
        meta = metadata(g,cond,repeat,slot,lock,root)
        m = c.fly(runtime,g,p['configuration'],cond,meta['label'],root)
        m.update(meta)
        m['v4_displacement'] = contract.displacement(read(c.ECHOAI/m['trace']))
        save(root/'completed'/(m['label']+'.json'),m)
        return m
    with ThreadPoolExecutor(max_workers=p['workers']) as ex:
        rows = list(ex.map(one,schedule))
    gs = contract.verdict(rows,stage,p,packages)
    negatives = []
    if stage=='validation':
        for g in packages:
            negatives.append(c.fly(runtime,g,p['configuration'],'perturbed',
                                   'negative-'+g.package_id,root,negative=True))
        gs['negative_controls'] = negative_group(negatives)
    else:
        gs.update(legacy.controls_and_mutants(runtime,packages,p['configuration'],root,rows))
    gs['frozen'] = contract.group([dict(name='code',ok=inventory()==lock['inventory']),
                                    dict(name='history',ok=history()['sha256']==lock['history_sha256'])])
    result = seal(dict(version=4, stage=stage, lock_sha256=lock['sha256'],
                       agent_in_gazebo=False, cortex_calls=0, wsp_writes=0,
                       hardware_status='not_available', dataset_kind='rehearsal',
                       episodes=rows, negatives=negatives, groups=gs,
                       passed=all(g['status']=='pass' for g in gs.values()),
                       wall_s=round(time.monotonic()-start,2)))
    save(root/'report.json',result)
    print(json.dumps(dict(stage=stage,passed=result['passed'],groups={k:g['status'] for k,g in gs.items()})),flush=True)
    return result


def reconstruct(m, g, meta, lock, check):
    cfg = lock['protocol']['configuration']
    path = c.ECHOAI/meta['trace']
    t = read(path)
    label = meta['label']
    check('trace/'+label, sha256_bytes(path.read_bytes())==m['trace_sha256'])
    check('identity/'+label,t['label']==label and t['condition']==meta['condition'])
    ep = Episode(**{k:v for k,v in t.items() if k in {f.name for f in fields(Episode)}})
    expected = c.evaluate.episode_metrics(ep,cfg,package=g.package)
    ulog = path.parent.parent/'ulogs'/(label+'.ulg')
    check('ulog/'+label,ulog.exists() and sha256_bytes(ulog.read_bytes())==ep.ulog_sha256
          and ulog.stat().st_size==ep.ulog_bytes)
    params = c.parameters_observed(ulog,ep.driver_events,cfg['px4_parameters'])
    expected.update(package_id=g.package_id,split=g.split,runtime=ep.metrics,
                    effective_sha256=ep.effective_sha256,protocol_version=3,
                    parameters=params,trace=relative(path),trace_sha256=sha256_bytes(path.read_bytes()))
    expected.update(meta)
    if 'v4_displacement' in m:
        expected['v4_displacement'] = contract.displacement(t)
    check('measurements/'+label,expected==m)
    effective = worldbuild.build_effective((g.package.path/'world.sdf').read_bytes(),g.package.sdf.sha256)
    check('world/'+label,ep.effective_sha256==effective.sha256 and ep.source_sha256==g.package.sdf.sha256)
    force = [cfg['disturbance']['force_mn']/1000,0,0] if meta['condition']=='perturbed' else [0,0,0]
    check('force/'+label,ep.force_n==force)
    duration_keys = {'climb':'takeoff_hold_ms','stabilize':'stabilize_ms','hover':'hover_ms',
                     'disturb':'disturb_ms','recover':'recover_ms'}
    plan = ep.stage_marks.get('plan',[])
    check('stage_durations/'+label,len(plan)==5 and [x[0] for x in plan]==list(duration_keys)
          and all(b-a==cfg['stages'][duration_keys[n]]*1_000_000 for n,a,b in plan))
    arithmetic = _recompute(t,cfg)
    for key in ('hover_horiz_rms_mm','disturb_excursion_mm'):
        av, bv = arithmetic.get(key), m.get(key)
        check('independent_'+key+'/'+label, av==bv if av is None or bv is None else abs(av-bv)<.05)
    if ep.condition=='perturbed' and ep.ok:
        check('independent_impulse/'+label, abs(arithmetic['impulse_ratio_ppk']-m['impulse']['ratio_ppk'])<=2)
        check('independent_recovery/'+label,arithmetic['recovery_status']==m['recovery']['status'])
    return expected


def audit_stage(r, lock):
    findings=[]; checks=0
    def check(name,ok):
        nonlocal checks
        checks+=1
        if not ok: findings.append(name)
    try:
        contract.validate(lock['protocol'])
        check('report_hash',r==seal(r))
        check('lock_hash',lock==seal(lock) and r['lock_sha256']==lock['sha256'])
        check('protocol_hash',report_sha256(lock['protocol'])==lock['protocol_sha256'])
        check('code',inventory()==lock['inventory'])
        check('isolation',r['version']==4 and r['agent_in_gazebo'] is False
              and r['cortex_calls']==0 and r['wsp_writes']==0
              and r['hardware_status']=='not_available' and r['dataset_kind']=='rehearsal')
        stage=r['stage']; root=ROOT/stage; p=lock['protocol']
        tmp,all_packages=legacy.generate_suite_unique()
        try:
            packages=all_packages[:p['stages'][stage]['worlds']]
            schedule=jobs(packages,stage,p)
            check('denominator',len(r['episodes'])==len(schedule))
            rebuilt=[]
            for m,(g,cond,repeat,slot) in zip(r['episodes'],schedule):
                meta=metadata(g,cond,repeat,slot,lock,root)
                check('assignment/'+meta['label'],all(m.get(k)==v for k,v in meta.items()))
                rebuilt.append(reconstruct(m,g,meta,lock,check))
            gs=contract.verdict(rebuilt,stage,p,packages)
            if stage=='validation':
                negatives=r['negatives']; rebuilt_neg=[]
                check('negative_count',len(negatives)==4)
                for m,g in zip(negatives,packages):
                    label='negative-'+g.package_id
                    meta=dict(label=label,condition='perturbed',trace=relative(root/'episodes'/(label+'.json')))
                    rebuilt_neg.append(reconstruct(m,g,meta,lock,check))
                gs['negative_controls']=negative_group(rebuilt_neg)
            else:
                check('no_unexpected_negatives',r['negatives']==[])
                ctrl=r['groups']['controls']; mut=r['groups']['mutants']
                check('controls_required',[x.get('name',x.get('control')) for x in ctrl['cases']]==
                      ['private_config','no_network_during_bench','world_hash_mismatch_refused','paired_separation'])
                # The static/config controls are re-executed. No new flight.
                configs=[legacy.old_mutants.container_config(g.package,p['configuration'],cond)
                         for g in packages for cond in ('nominal','perturbed')]
                varying={k for cfg in configs for k in cfg if cfg[k]!=configs[0][k]}
                observed=[dict(name='private_config',ok=varying<={'spawn_pose','condition'}
                    and all(legacy.old_mutants.inspect_config(cfg)['ok'] for cfg in configs)),
                    legacy.old_mutants._no_network_control(Runtime(available=True,lock=lock['runtime'])),
                    legacy.old_mutants._hash_mismatch_control(packages[0],p['configuration'])]
                sep=gs['separation']
                observed.append(dict(name='paired_separation',ok=all(x['difference_mm']>0 for x in sep.get('pairs',[]))))
                check('controls_rebuilt',[x['ok'] for x in ctrl['cases']]==[x['ok'] for x in observed])
                check('controls_status',ctrl['status']==contract.group(observed)['status'])
                gs['controls']=ctrl
                check('mutants_required',[x['name'] for x in mut['cases']]==['noforce','accumulate','frozen_clock'])
                observed_mut=[]
                for case in mut['cases']:
                    path=root/('mutant-'+case['name']+'.json'); t=read(path)
                    check('mutant_hash/'+case['name'],case['trace']==relative(path)
                          and sha256_bytes(path.read_bytes())==case['sha256'])
                    if case['name']=='frozen_clock':
                        detected=not t['ok'] and any(e.get('ev')=='watchdog_timeout' for e in t['events'])
                    else:
                        detected=not _recompute(t,p['configuration']).get('stimulus_ok',False)
                        if case['name']=='noforce': detected=detected and t['ok']
                    check('mutant_observation/'+case['name'],detected==case['ok'])
                    observed_mut.append(dict(ok=detected))
                check('mutants_status',mut['status']==contract.group(observed_mut)['status'])
                gs['mutants']=mut
            gs['frozen']=contract.group([dict(name='code',ok=inventory()==lock['inventory']),
                dict(name='history',ok=history()['sha256']==lock['history_sha256'])])
            check('all_groups_reconstructed',r['groups']==gs)
            check('passed_reconstructed',r['passed']==all(g['status']=='pass' for g in gs.values()))
        finally:
            tmp.cleanup()
    except Exception as exc:
        check('malformed_evidence/'+type(exc).__name__+': '+str(exc),False)
    return dict(evidence_valid=not findings,checks=checks,findings=findings,
                recomputed_episodes=len(r.get('episodes',[])),passed=r.get('passed',False))


def audit():
    lock=read(ROOT/'lock.json')
    findings=[]
    if lock!=seal(lock) or read(ROOT/'protocol.json')!=lock['protocol']:
        findings.append('lock_or_protocol_file')
    if history()!=read(ROOT/'history.json') or history()['sha256']!=lock['history_sha256']:
        findings.append('history_changed')
    if lock['regression']!=read(ROOT/'regression.json') or lock['regression']['status']!='pass':
        findings.append('regression')
    if [x['name'] for x in lock['regression']['cases']]!=list(MODULES):
        findings.append('regression_denominator')
    for x in lock['regression']['cases']:
        if not x['ok'] or sha256_bytes((c.ECHOAI/x['path']).read_bytes())!=x['sha256']:
            findings.append('regression/'+x['name'])
    stages={}
    for stage in ('validation','bench'):
        path=ROOT/stage/'report.json'
        if path.exists():
            stages[stage]=audit_stage(read(path),lock)
    valid=not findings and bool(stages) and all(x['evidence_valid'] for x in stages.values())
    green=valid and set(stages)=={'validation','bench'} and all(x['passed'] for x in stages.values())
    return dict(evidence_valid=valid,findings=findings,stages=stages,flight1s_green=green)


def mutations(r,lock):
    cases=[]
    changes={
        'omit_episode':lambda x:x['episodes'].pop(),
        'changed_measurement':lambda x:x['episodes'][0].update(disturb_excursion_mm=9999),
        'fake_green':lambda x:x.update(passed=not x['passed']),
        'omit_recovery':lambda x:x['groups'].pop('recovery'),
        'activate_agent':lambda x:x.update(agent_in_gazebo=True),
    }
    for name,fn in changes.items():
        mutant=copy.deepcopy(r);fn(mutant)
        result=audit_stage(seal(mutant),lock)
        cases.append(dict(name=name,ok=not result['evidence_valid'],findings=result['findings']))
    altered=copy.deepcopy(lock);altered['protocol']['configuration']['recovery']['radius_mm']=500
    altered['protocol_sha256']=report_sha256(altered['protocol']);altered=seal(altered)
    mutant=copy.deepcopy(r);mutant['lock_sha256']=altered['sha256']
    result=audit_stage(seal(mutant),altered)
    cases.append(dict(name='relax_recovery',ok=not result['evidence_valid'],findings=result['findings']))
    return contract.group(cases)


def run():
    lock=freeze() if not (ROOT/'lock.json').exists() else read(ROOT/'lock.json')
    contract.validate(lock['protocol'])
    a_path=ROOT/'validation/report.json'
    a=read(a_path) if a_path.exists() else run_stage(lock,'validation')
    if a['passed']:
        run_stage(lock,'bench')
    result=audit()
    target=read(ROOT/'bench/report.json') if (ROOT/'bench/report.json').exists() else a
    result['mutation_tests']=mutations(target,lock)
    result['flight1s_green'] &= result['mutation_tests']['status']=='pass'
    result.update(version=4,lock_sha256=lock['sha256'],scope='flight_software_in_the_loop',
                  legacy_precision_guarantee=False)
    save(REPORT,seal(result))
    print(json.dumps(result,indent=2),flush=True)
    return result['flight1s_green']


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['run','audit'])
    args=parser.parse_args()
    if args.command=='run':
        raise SystemExit(0 if run() else 1)
    result=audit()
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['evidence_valid'] and result['flight1s_green'] else 1)
