"""One prospective chain, raw evidence, and an audit that rebuilds its verdict.

v6 keeps the v5 configuration and the v4 acceptance. It repairs the chain:
aggregation fails a case instead of raising, a job that raises is counted
instead of stopping the pool, and a PX4 whose MAVLink never answers is
relaunched once in a fresh container, before anything reaches the vehicle.
"""
import copy
import json
import os
import shutil
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
from echoai.nexus0.flight1s_v5.campaign import patched_runtime
from echoai.nexus0.sim3.canon import dump_report, report_sha256, sha256_bytes
from . import contract

HERE = Path(__file__).resolve().parent
RUNNER = HERE/'assets/flightrunner_configured.py'
ROOT = c.ECHOAI/'lab/flight1s-v6'
REPORT = c.ECHOAI/'lab/echo3_flight1s_v6_report.json'
LOG = c.ECHOAI/'lab/flight1s-v6-run.log'
MODULES = ('test_flight1s_v6','test_flight1s_v5','test_flight1s_v4','test_flight1s_v3',
           'test_flight1s_v2','test_flight1s','test_flight1s_backend','test_sim3','test_nexus0')


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
    for name in ('flight1s','flight1s-v2','flight1s-v3','flight1s-v4','flight1s-v5'):
        paths += [p for p in (c.ECHOAI/'lab'/name).rglob('*') if p.is_file()]
        paths += [p for p in (c.ECHOAI/'docs/examples'/name).rglob('*') if p.is_file()]
    paths += list((c.ECHOAI/'lab').glob('flight1s-v5-run.log'))
    for p in (c.ECHOAI/'lab').glob('echo3_flight1s*.json'):
        if '_v6_' not in p.name:
            paths.append(p)
    paths += [p for p in (c.ECHOAI/'docs').glob('FLIGHT1S*.md') if '-V6-' not in p.name]
    paths += [c.ECHOAI/'docs/flight1s-v5/DESIGN.md']
    return fingerprint(paths)


def inventory():
    paths = [c.ECHOAI/p for p in c.inventory()['files']]
    for name in ('flight1s_v6', 'flight1s_v5', 'flight1s_v4', 'sim3'):
        paths += list((c.ECHOAI/'nexus0'/name).rglob('*.py'))
    paths += [c.ECHOAI/'docs/flight1s-v6/DESIGN.md']
    paths += [c.ECHOAI/'tests'/(m+'.py') for m in MODULES]
    paths += [c.ECHOAI/'nexus0/flight1s/container/Containerfile',
              c.ECHOAI/'nexus0/flight1s_v5/container/Containerfile']
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
        raise FileExistsError('v6 already started; audit or resume the frozen chain')
    ROOT.mkdir(parents=True)
    p = contract.protocol()
    inv = inventory()
    reg = regression()
    save(ROOT/'regression.json', reg)
    if reg['status'] != 'pass' or inv != inventory():
        raise RuntimeError('Regression failed or code changed; no flights authorised')
    runtime = c.preflight(write=False)
    runtime.require()
    runtime.lock = patched_runtime(runtime.lock)
    image_id = runtime.lock['container'].get('image_id') or subprocess.check_output(
        ['podman','image','inspect',runtime.image,'--format','{{.Id}}'],text=True).strip()
    runtime.lock['container']['image'] = image_id
    runtime.lock['lock_sha256'] = report_sha256({k:v for k,v in runtime.lock.items() if k!='lock_sha256'})
    hist = history()
    save(ROOT/'history.json', hist)
    lock = seal(dict(version=6, created_utc=datetime.now(timezone.utc).isoformat(),
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
                split=g.split, repeat=repeat, order_slot=slot, protocol_version=6,
                lock_sha256=lock['sha256'], protocol_sha256=lock['protocol_sha256'],
                trace=relative(root/'episodes'/(label+'.json')))


def negative_group(negatives):
    return contract.group([dict(label=m['label'], ok=bool(m['ok']
                        and m['parameters']['ok'] and not m['stimulus']['ok']
                        and abs(m.get('impulse',{}).get('ratio_ppk',9999))<500))
                           for m in negatives])


def attempt(runtime, gen, cfg, condition, label, root, boot, mutant=None):
    env = {'FLIGHT1S_PARAMETERS': json.dumps(cfg['px4_parameters'], sort_keys=True),
           'FLIGHT1S_HEARTBEAT_S': str(boot['heartbeat_s'])}
    if mutant:
        env['FLIGHT1S_MUTANT'] = mutant
    return c.session.run_episode(runtime, gen.package, cfg, condition=condition,
                                 label=label, ulog_dir=root/'ulogs',
                                 runner_path=RUNNER, extra_env=env)


def set_aside(ep, label, n, root):
    """Keep a hung boot as evidence under its own name before the relaunch
    reuses the label (and would overwrite its ULog)."""
    name = f'{label}-boot{n}'
    trace = root/'boots'/(name+'.json')
    dump_report(trace, ep.trace())
    ulog, kept = root/'ulogs'/(label+'.ulg'), None
    if ulog.exists():
        kept = root/'boots'/(name+'.ulg')
        shutil.move(ulog, kept)
    return dict(attempt=n, trace=relative(trace), trace_sha256=sha256_bytes(trace.read_bytes()),
                ulog=relative(kept) if kept else None, ulog_sha256=ep.ulog_sha256, cause=ep.cause)


def launch(runtime, gen, cfg, condition, label, root, boot, mutant=None):
    """Fly once; relaunch only a boot that never answered, at most boot['restarts'] times."""
    restarts = []
    for n in range(1, boot['restarts']+2):
        ep = attempt(runtime, gen, cfg, condition, label, root, boot, mutant)
        if n > boot['restarts'] or not contract.boot_hung(ep.trace()):
            return ep, restarts
        print(f'boot_restart {label}: attempt {n} {ep.cause}', flush=True)
        restarts.append(set_aside(ep, label, n, root))


def fly(runtime, gen, cfg, condition, label, root, boot, *, negative=False):
    print('start '+label, flush=True)
    ep, restarts = launch(runtime, gen, cfg, condition, label, root, boot,
                          'noforce' if negative else None)
    m = c.evaluate.episode_metrics(ep, cfg, package=gen.package)
    m.update(package_id=gen.package_id, split=gen.split, runtime=ep.metrics,
             effective_sha256=ep.effective_sha256, protocol_version=3, boot_restarts=restarts)
    m['parameters'] = c.parameters_observed(root/'ulogs'/(label+'.ulg'),
                                            ep.driver_events, cfg['px4_parameters'])
    m['trace'] = relative(root/'episodes'/(label+'.json'))
    dump_report(c.ECHOAI/m['trace'], ep.trace())
    m['trace_sha256'] = sha256_bytes((c.ECHOAI/m['trace']).read_bytes())
    dump_report(root/'metrics'/(label+'.json'), m)
    failures = [k for k in ('stimulus','challenge','recovery_verdict','parameters')
                if not m.get(k, {}).get('ok')]
    print(f"done {label}: excursion={m.get('disturb_excursion_mm')} "
          f"recovery={m.get('recovery')} restarts={len(restarts)} fail={failures}", flush=True)
    return m


def controls_and_mutants(runtime, packages, p, root, rows, boot):
    """v3 controls and physical mutants, flown through the v6 runner."""
    old = legacy.old_mutants
    configs = [old.container_config(g.package,p,cond)
               for g in packages for cond in ('nominal','perturbed')]
    varying = {k for cfg in configs for k in cfg if cfg[k]!=configs[0][k]}
    cases = [dict(name='private_config',ok=varying<={'spawn_pose','condition'}
                  and all(old.inspect_config(cfg)['ok'] for cfg in configs)),
             old._no_network_control(runtime),
             old._hash_mismatch_control(packages[0],p)]
    pairs = {}
    for m in rows:
        pairs.setdefault((m['package_id'],m['repeat']),{})[m['condition']] = m
    cases.append(dict(name='paired_separation',ok=all(
        contract.finite(x.get('perturbed',{}).get('disturb_excursion_mm'))
        and contract.finite(x.get('nominal',{}).get('disturb_excursion_mm'))
        and x['perturbed']['disturb_excursion_mm']>x['nominal']['disturb_excursion_mm']
        for x in pairs.values())))
    mutants = []
    for kind in ('noforce','accumulate','frozen_clock'):
        q = copy.deepcopy(p)
        if kind=='frozen_clock': q['timeouts']['episode_s'] = 30
        ep, restarts = launch(runtime, packages[0], q, 'perturbed', 'mutant-'+kind, root, boot, kind)
        m = c.evaluate.episode_metrics(ep,q,package=packages[0].package)
        path = root/('mutant-'+kind+'.json')
        dump_report(path,ep.trace())
        if kind=='frozen_clock':
            caught = not ep.ok and any(e.get('ev')=='watchdog_timeout' for e in ep.events)
        else:
            caught = not m.get('stimulus',{}).get('ok')
            if kind=='noforce': caught = caught and ep.ok
        mutants.append(dict(name=kind,ok=caught,trace=relative(path),
                            sha256=sha256_bytes(path.read_bytes()),cause=ep.cause,
                            boot_restarts=restarts))
    return {name:contract.group(items) for name,items in (('controls',cases),('mutants',mutants))}


def restart_tally(rows, negatives, gs):
    out = [dict(label=m['label'], **r) for m in rows+negatives for r in m.get('boot_restarts', [])]
    out += [dict(label='mutant-'+x['name'], **r) for x in gs.get('mutants',{}).get('cases',[])
            for r in x.get('boot_restarts', [])]
    return out


def run_stage(lock, stage):
    root = ROOT/stage
    if root.exists():
        raise FileExistsError('Stage is immutable: '+stage)
    p = lock['protocol']; boot = p['boot']
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
        try:
            m = fly(runtime,g,p['configuration'],cond,meta['label'],root,boot)
            m.update(meta)
            m['v4_displacement'] = contract.displacement(read(c.ECHOAI/m['trace']))
        except Exception as exc:
            print('exception '+meta['label']+': '+repr(exc)[:300], flush=True)
            m = contract.failed_row(meta, exc)
        save(root/'completed'/(m['label']+'.json'),m)
        return m
    with ThreadPoolExecutor(max_workers=p['workers']) as ex:
        rows = list(ex.map(one,schedule))
    gs = contract.verdict(rows,stage,p,packages)
    negatives = []
    if stage=='validation':
        for g in packages:
            label = 'negative-'+g.package_id
            try:
                m = fly(runtime,g,p['configuration'],'perturbed',label,root,boot,negative=True)
            except Exception as exc:
                print('exception '+label+': '+repr(exc)[:300], flush=True)
                m = contract.failed_row(dict(label=label, condition='perturbed',
                                             trace=relative(root/'episodes'/(label+'.json'))), exc)
            negatives.append(m)
        gs['negative_controls'] = negative_group(negatives)
    else:
        try:
            gs.update(controls_and_mutants(runtime,packages,p['configuration'],root,rows,boot))
        except Exception as exc:
            gs['controls'] = contract.error_group('controls_and_mutants', exc)
            gs['mutants'] = contract.error_group('controls_and_mutants', exc)
    gs['frozen'] = contract.group([dict(name='code',ok=inventory()==lock['inventory']),
                                    dict(name='history',ok=history()['sha256']==lock['history_sha256'])])
    result = seal(dict(version=6, stage=stage, lock_sha256=lock['sha256'],
                       agent_in_gazebo=False, cortex_calls=0, wsp_writes=0,
                       hardware_status='not_available', dataset_kind='rehearsal',
                       episodes=rows, negatives=negatives, groups=gs,
                       boot_restarts=restart_tally(rows, negatives, gs),
                       passed=all(g['status']=='pass' for g in gs.values()),
                       wall_s=round(time.monotonic()-start,2)))
    save(root/'report.json',result)
    print(json.dumps(dict(stage=stage,passed=result['passed'],restarts=len(result['boot_restarts']),
                          groups={k:g['status'] for k,g in gs.items()})),flush=True)
    return result


def check_restarts(records, label, root, boot, check):
    """Each relaunch is a set-aside boot that provably never reached the vehicle."""
    check('boot_restart_count/'+label, isinstance(records, list) and len(records) <= boot['restarts'])
    for n, r in enumerate(records, 1):
        name = f'{label}-boot{n}'
        tpath = root/'boots'/(name+'.json')
        t = read(tpath)
        ok = (r['attempt'] == n and r['trace'] == relative(tpath)
              and sha256_bytes(tpath.read_bytes()) == r['trace_sha256']
              and t['label'] == label and contract.boot_hung(t)
              and r['cause'] == t['cause'] and r['ulog_sha256'] == t['ulog_sha256'])
        if r['ulog']:
            upath = root/'boots'/(name+'.ulg')
            ok = ok and r['ulog'] == relative(upath) and sha256_bytes(upath.read_bytes()) == t['ulog_sha256']
        else:
            ok = ok and t['ulog_sha256'] is None
        check('boot_restart/'+name, ok)
    return {relative(root/'boots'/f'{label}-boot{n}.{ext}') for n in range(1, len(records)+1)
            for ext in ('json','ulg')}


def reconstruct(m, g, meta, lock, check):
    p = lock['protocol']; cfg = p['configuration']
    path = c.ECHOAI/meta['trace']
    label = meta['label']
    if (m.get('cause') or {}).get('code') == 'coordinator_exception':
        want = {k:v for k,v in contract.failed_row(meta, Exception()).items() if k!='cause'}
        check('exception_row/'+label, {k:v for k,v in m.items() if k!='cause'}==want
              and not path.exists())
        return m
    t = read(path)
    check('trace/'+label, sha256_bytes(path.read_bytes())==m['trace_sha256'])
    check('identity/'+label,t['label']==label and t['condition']==meta['condition'])
    ep = Episode(**{k:v for k,v in t.items() if k in {f.name for f in fields(Episode)}})
    expected = c.evaluate.episode_metrics(ep,cfg,package=g.package)
    ulog = path.parent.parent/'ulogs'/(label+'.ulg')
    check('ulog/'+label,(ulog.exists() and sha256_bytes(ulog.read_bytes())==ep.ulog_sha256
          and ulog.stat().st_size==ep.ulog_bytes) or (not ulog.exists() and ep.ulog_sha256 is None))
    params = c.parameters_observed(ulog,ep.driver_events,cfg['px4_parameters'])
    records = m.get('boot_restarts', [])
    check_restarts(records, label, path.parent.parent, p['boot'], check)
    expected.update(package_id=g.package_id,split=g.split,runtime=ep.metrics,
                    effective_sha256=ep.effective_sha256,protocol_version=3,boot_restarts=records,
                    parameters=params,trace=relative(path),trace_sha256=sha256_bytes(path.read_bytes()))
    expected.update(meta)
    if 'v4_displacement' in m:
        expected['v4_displacement'] = contract.displacement(t)
    check('measurements/'+label,expected==m)
    effective = worldbuild.build_effective((g.package.path/'world.sdf').read_bytes(),g.package.sdf.sha256)
    check('world/'+label,ep.effective_sha256==effective.sha256 and ep.source_sha256==g.package.sdf.sha256)
    force = [cfg['disturbance']['force_mn']/1000,0,0] if meta['condition']=='perturbed' else [0,0,0]
    check('force/'+label,ep.force_n==force)
    check('stage_durations/'+label, contract.plan_ok(ep, cfg))
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
        check('isolation',r['version']==6 and r['agent_in_gazebo'] is False
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
            referenced=set()
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
                observed.append(dict(name='paired_separation',ok=sep.get('status')=='pass'
                                     and all(x['difference_mm']>0 for x in sep.get('pairs',[]))))
                check('controls_rebuilt',[x['ok'] for x in ctrl['cases']]==[x['ok'] for x in observed])
                check('controls_status',ctrl['status']==contract.group(observed)['status'])
                gs['controls']=ctrl
                check('mutants_required',[x['name'] for x in mut['cases']]==['noforce','accumulate','frozen_clock'])
                observed_mut=[]
                for case in mut['cases']:
                    path=root/('mutant-'+case['name']+'.json'); t=read(path)
                    check('mutant_hash/'+case['name'],case['trace']==relative(path)
                          and sha256_bytes(path.read_bytes())==case['sha256'])
                    referenced|=check_restarts(case.get('boot_restarts',[]),'mutant-'+case['name'],
                                               root,p['boot'],check)
                    if case['name']=='frozen_clock':
                        detected=not t['ok'] and any(e.get('ev')=='watchdog_timeout' for e in t['events'])
                    else:
                        detected=not _recompute(t,p['configuration']).get('stimulus_ok',False)
                        if case['name']=='noforce': detected=detected and t['ok']
                    check('mutant_observation/'+case['name'],detected==case['ok'])
                    observed_mut.append(dict(ok=detected))
                check('mutants_status',mut['status']==contract.group(observed_mut)['status'])
                gs['mutants']=mut
            for m in r['episodes']+r['negatives']:
                referenced|={x for x in (relative(root/'boots'/f"{m['label']}-boot{n}.{ext}")
                             for n in range(1,len(m.get('boot_restarts',[]))+1) for ext in ('json','ulg'))}
            present={relative(x) for x in (root/'boots').glob('*')} if (root/'boots').exists() else set()
            check('boot_files_accounted',present<=referenced)
            check('restart_tally',r['boot_restarts']==restart_tally(r['episodes'],r['negatives'],r['groups']))
            gs['frozen']=contract.group([dict(name='code',ok=inventory()==lock['inventory']),
                dict(name='history',ok=history()['sha256']==lock['history_sha256'])])
            check('all_groups_reconstructed',r['groups']==gs)
            check('passed_reconstructed',r['passed']==all(g['status']=='pass' for g in gs.values()))
        finally:
            tmp.cleanup()
    except Exception as exc:
        check('malformed_evidence/'+type(exc).__name__+': '+str(exc),False)
    return dict(evidence_valid=not findings,checks=checks,findings=findings,
                recomputed_episodes=len(r.get('episodes',[])),passed=r.get('passed',False),
                boot_restarts=len(r.get('boot_restarts',[])))


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
    forged=dict(attempt=1,trace='lab/flight1s-v6/validation/boots/forged.json',trace_sha256='0'*64,
                ulog=None,ulog_sha256=None,cause={'code':'mavlink_no_heartbeat'})
    changes={
        'omit_episode':lambda x:x['episodes'].pop(),
        'changed_measurement':lambda x:x['episodes'][0].update(disturb_excursion_mm=9999),
        'fake_green':lambda x:x.update(passed=not x['passed']),
        'omit_recovery':lambda x:x['groups'].pop('recovery'),
        'activate_agent':lambda x:x.update(agent_in_gazebo=True),
        'forged_boot_restart':lambda x:x['episodes'][0].update(boot_restarts=[forged]),
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
    result.update(version=6,lock_sha256=lock['sha256'],scope='flight_software_in_the_loop',
                  legacy_precision_guarantee=False)
    save(REPORT,seal(result))
    print(json.dumps(result,indent=2),flush=True)
    return result['flight1s_green']


def start():
    """Launch `run` in its own session: v4 died with the shell that started it."""
    if ROOT.exists() or REPORT.exists() or LOG.exists():
        raise FileExistsError('v6 already started')
    with open(LOG, 'xb') as out:
        proc = subprocess.Popen([sys.executable,'-u','-m','echoai.nexus0.flight1s_v6.campaign','run'],
                                cwd=c.ECHOAI, env=dict(os.environ, PYTHONPATH=str(c.ECHOAI.parent)),
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True)
    print(json.dumps(dict(pid=proc.pid, log=relative(LOG))), flush=True)
    return proc.pid


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['start','run','audit'])
    args=parser.parse_args()
    if args.command=='start':
        start(); raise SystemExit(0)
    if args.command=='run':
        raise SystemExit(0 if run() else 1)
    result=audit()
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['evidence_valid'] and result['flight1s_green'] else 1)
