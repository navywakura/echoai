"""Frozen v3 validation, full bank and reconstructible evidence.

Historical evaluators and arithmetic are reused without modifying their files.
Each output directory is write-once; all episodes remain in the denominator.
"""
import copy
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import fields
from pathlib import Path

from echoai.nexus0.flight1s import mutants as old_mutants, worldbuild
from echoai.nexus0.flight1s.session import Episode
from echoai.nexus0.flight1s.runtime import Runtime
from echoai.nexus0.flight1s.v2.audit import _recompute
from echoai.nexus0.flight1s.v2.bench import Bench
from echoai.nexus0.sim3.canon import report_sha256, dump_report, sha256_bytes
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from . import campaign as c

REPORT = c.ECHOAI / 'lab/echo3_flight1s_v3_report.json'
GROUPS = {'episodes','stimulus','challenge','recovery','hygiene','configuration',
          'repetition','envelope','controls','mutants','regression','history'}


def fingerprint_history():
    paths = set()
    for name in ('flight1s', 'flight1s-v2'):
        paths.update(p for p in (c.ECHOAI / 'lab' / name).rglob('*') if p.is_file())
        paths.update(p for p in (c.ECHOAI / 'docs/examples' / name).rglob('*') if p.is_file())
    paths.update((c.ECHOAI/'lab').glob('echo3_flight1s*.json'))
    paths = {p for p in paths if '_v3_' not in p.name}
    entries = {str(p.relative_to(c.ECHOAI)): sha256_bytes(p.read_bytes()) for p in sorted(paths)}
    return {'files': entries, 'sha256': report_sha256(entries)}


def verdict_groups(rows, p, packages):
    gs = c.groups(rows, p)
    b = Bench(report_path=Path('/unused'), protocol_path=None, verbose=False)
    b.episodes = rows
    b._group_repetition({(m['package_id'], m['repeat'], m['condition']): m for m in rows}, p)
    b._group_envelope(packages, p)
    gs.update(b.groups)
    return gs


def regression(root):
    root.mkdir(parents=True, exist_ok=True)
    cases = []
    for mod in ['test_flight1s_v3','test_flight1s_v2','test_flight1s','test_sim3','test_nexus0']:
        cmd = [sys.executable, '-m', 'echoai.tests.'+mod, '-q']
        print('regression '+mod, flush=True)
        try:
            pr = subprocess.run(cmd, cwd=c.ECHOAI,
                                env=dict(os.environ, PYTHONPATH=str(c.ECHOAI.parent)),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=2400)
            log = pr.stdout.decode(errors='replace')
            (root / (mod+'.log')).write_text(log)
            cases.append(dict(name=mod, ok=pr.returncode==0, returncode=pr.returncode,
                              log=str((root/(mod+'.log')).relative_to(c.ECHOAI)),
                              sha256=sha256_bytes(pr.stdout), tail=log.splitlines()[-4:]))
        except subprocess.TimeoutExpired:
            cases.append(dict(name=mod, ok=False, cause='timeout'))
        print(cases[-1], flush=True)
    return {'status':'pass' if all(x['ok'] for x in cases) else 'fail','cases':cases}


def run_bench(candidate, attempt=1):
    """``attempt`` names which A validation authorises this bank.

    A campaign that had to be repeated lands in ``validation-<cand>-rN``.
    The operator says which one authorises the bank; the code still refuses
    unless that report passed and its inventory is today's inventory, so
    naming a red or stale attempt changes nothing.
    """
    if attempt < 1:
        raise ValueError('attempt must be positive')
    root = c.LAB/'bench'
    if root.exists() or REPORT.exists():
        raise FileExistsError('Existing bank must not be overwritten')
    validation_path = (c.LAB/('validation-'+candidate+(f'-r{attempt}' if attempt > 1 else ''))
                       /'report.json')
    v = json.loads(validation_path.read_text())
    if not v['passed'] or v['inventory'] != c.inventory():
        raise ValueError('A validation absent, red or code changed since validation')
    p = c.configuration(candidate)
    c.validate_configuration(p)
    root.mkdir(parents=True)
    before = fingerprint_history()
    dump_report(root/'history.json', before)
    reg = regression(c.LAB/'regression')
    if reg['status'] != 'pass':
        dump_report(root/'not-run.json', dict(cause='regression', regression=reg))
        return False
    runtime = c.preflight(write=False)
    runtime.require()
    a_runtime=json.loads((validation_path.parent/'runtime.json').read_text())
    if runtime.lock['container'] != a_runtime['container']:
        raise ValueError('PX4/container changed since A validation')
    # Pin by image ID, so replacing a tag cannot replace the executed image.
    original_image = runtime.lock['container']['image']
    image_id = runtime.lock['container'].get('image_id')
    if not image_id:
        image_id = subprocess.check_output(['podman','image','inspect',original_image,
                                            '--format','{{.Id}}'], text=True).strip()
    runtime.lock['container']['image'] = image_id
    runtime.lock['lock_sha256'] = report_sha256({k:v for k,v in runtime.lock.items() if k!='lock_sha256'})
    lock = dict(protocol_version=3, runtime=runtime.lock, inventory=c.inventory(),
                configuration=p, configuration_sha256=report_sha256(p),
                validation_path=str(validation_path.relative_to(c.ECHOAI)),
                validation_attempt=attempt,
                validation_sha256=sha256_bytes(validation_path.read_bytes()),
                history_sha256=before['sha256'], workers=2, seed=20260915)
    lock['sha256'] = report_sha256(lock)
    dump_report(root/'lock.json', lock)
    dump_report(root/'protocol.json', dict(version=3, configuration=p, seed=20260915,
                                         episodes=48, repeats=2, workers=2))
    packages = generate_suite(root/'suite', load_protocol(c.WORLD_PROTOCOL),
                              REHEARSAL_SECRET, rehearsal_assignment())
    jobs = []
    order = c.condition_order(lock['seed'],24)
    for i,g in enumerate(packages):
        for repeat in (1,2):
            slot = i*2+repeat-1
            for condition in order[slot*2:slot*2+2]:
                jobs.append((g,condition,repeat,slot))
    start = time.monotonic()
    def one(job):
        g,condition,repeat,slot = job
        m = c.fly(runtime,g,p,condition,f'{condition}-{g.package_id}-r{repeat}',root)
        m.update(repeat=repeat,order_slot=slot,lock_sha256=lock['sha256'],
                 protocol_sha256=lock['configuration_sha256'])
        return m
    with ThreadPoolExecutor(max_workers=2) as ex:
        rows = list(ex.map(one,jobs))
    gs = verdict_groups(rows,p,packages)
    controls = controls_and_mutants(runtime,packages,p,root,rows)
    gs.update(controls)
    gs['regression'] = reg
    gs['history'] = {'status':'pass' if fingerprint_history()==before else 'fail','cases':[]}
    report = dict(schema_version=1, slice='FLIGHT-1S', scope='flight_software_in_the_loop',
                  protocol_version=3, dataset_kind='rehearsal',hardware_status='not_available',
                  agent_in_gazebo=False,cortex_calls=0,wsp_writes=0,lock=lock,
                  lock_path=str((root/'lock.json').relative_to(c.ECHOAI)),
                  history_path=str((root/'history.json').relative_to(c.ECHOAI)),
                  validation_path=str(validation_path.relative_to(c.ECHOAI)),
                  assignment=[dict(package_id=g.package_id,index=g.index,split=g.split,
                                   package_sha256=g.package.package_sha256) for g in packages],
                  episodes=rows,groups=gs,workers=2,wall_s=round(time.monotonic()-start,2))
    report['group_status'] = {k:gs[k]['status'] for k in sorted(GROUPS)}
    report['flight1s_green'] = all(s=='pass' for s in report['group_status'].values())
    report['sha256'] = report_sha256(report)
    dump_report(REPORT,report)
    audit = audit_report(report)
    audit['mutation_self_test'] = mutation_test(report)
    audit['evidence_mutations'] = evidence_mutations(report)
    dump_report(c.ECHOAI/'lab/echo3_flight1s_v3_audit.json', audit)
    print(json.dumps({'green':report['flight1s_green'],'audit':audit,'report':str(REPORT)}),flush=True)
    return (report['flight1s_green'] and audit['evidence_valid']
            and audit['mutation_self_test']['ok'] and audit['evidence_mutations']['ok'])


def controls_and_mutants(runtime, packages, p, root, rows):
    configs = [old_mutants.container_config(g.package,p,cond)
               for g in packages for cond in ('nominal','perturbed')]
    varying = {k for cfg in configs for k in cfg if cfg[k]!=configs[0][k]}
    cases = [dict(name='private_config',ok=varying<={'spawn_pose','condition'}
                  and all(old_mutants.inspect_config(cfg)['ok'] for cfg in configs)),
             old_mutants._no_network_control(runtime),
             old_mutants._hash_mismatch_control(packages[0],p)]
    pairs = {(m['package_id'],m['repeat']):{} for m in rows}
    for m in rows:
        pairs[(m['package_id'],m['repeat'])][m['condition']] = m
    cases.append(dict(name='paired_separation',ok=all(
        x['perturbed']['disturb_excursion_mm']>x['nominal']['disturb_excursion_mm']
        for x in pairs.values())))
    mutants=[]
    for kind in ['noforce','accumulate','frozen_clock']:
        q=copy.deepcopy(p)
        if kind=='frozen_clock': q['timeouts']['episode_s']=30
        ep=c.session.run_episode(runtime,packages[0].package,q,condition='perturbed',
                 label='mutant-'+kind,ulog_dir=root/'ulogs',runner_path=c.RUNNER,
                 extra_env={'FLIGHT1S_PARAMETERS':json.dumps(q['px4_parameters']),
                            'FLIGHT1S_MUTANT':kind})
        m=c.evaluate.episode_metrics(ep,q,package=packages[0].package)
        path=root/('mutant-'+kind+'.json')
        dump_report(path,ep.trace())
        if kind=='frozen_clock':
            caught=not ep.ok and any(e.get('ev')=='watchdog_timeout' for e in ep.events)
        else:
            caught=not m.get('stimulus',{}).get('ok')
            if kind=='noforce': caught=caught and ep.ok
        mutants.append(dict(name=kind,ok=caught,trace=str(path.relative_to(c.ECHOAI)),
                            sha256=sha256_bytes(path.read_bytes()),cause=ep.cause))
    return {name:{'status':'pass' if all(x['ok'] for x in items) else 'fail','cases':items}
            for name,items in [('controls',cases),('mutants',mutants)]}


def audit_report(r, *, files=True):
    """Recompute per-episode arithmetic and all flight verdicts, including nominal."""
    findings=[]
    checks=0
    def check(name,ok):
        nonlocal checks
        checks+=1
        if not ok: findings.append(name)
    check('report_hash',r.get('sha256')==report_sha256({k:v for k,v in r.items() if k!='sha256'}))
    lock=r['lock']; p=lock['configuration']; rows=r['episodes']
    check('lock_hash',lock['sha256']==report_sha256({k:v for k,v in lock.items() if k!='sha256'}))
    try: c.validate_configuration(p)
    except (ValueError,KeyError): check('configuration',False)
    else: check('configuration',True)
    check('configuration_hash',lock['configuration_sha256']==report_sha256(p))
    check('version',r.get('protocol_version')==3)
    check('isolation',r.get('agent_in_gazebo') is False and r.get('wsp_writes')==0
          and r.get('cortex_calls')==0 and r.get('hardware_status')=='not_available')
    check('groups_required',set(r['groups'])==GROUPS and set(r['group_status'])==GROUPS)
    check('denominator',len(rows)==48 and len({m['label'] for m in rows})==48)
    assignments=r['assignment']; expected=[]; order=c.condition_order(20260915,24)
    for i,g in enumerate(assignments):
        for repeat in (1,2):
            slot=i*2+repeat-1
            for cond in order[slot*2:slot*2+2]:
                expected.append((g['package_id'],repeat,cond,slot))
    check('assignment_count',len(assignments)==12 and len({g['package_id'] for g in assignments})==12)
    check('order',[(m['package_id'],m['repeat'],m['condition'],m['order_slot']) for m in rows]==expected)
    check('single_lock',all(m['lock_sha256']==lock['sha256'] for m in rows))
    check('single_protocol',all(m['protocol_sha256']==lock['configuration_sha256'] for m in rows))
    for key,group in r['groups'].items():
        check('group_status/'+key,r['group_status'].get(key)==group['status'])
        if group['status']=='pass':
            check('group_cases/'+key,all(x.get('ok',x.get('completed',True)) for x in group.get('cases',[])))
    check('green',r['flight1s_green']==(set(r['group_status'])==GROUPS and all(s=='pass' for s in r['group_status'].values())))
    if files:
        check('code',lock['inventory']==c.inventory())
        check('lock_file',json.loads((c.ECHOAI/r['lock_path']).read_text())==lock)
        history=json.loads((c.ECHOAI/r['history_path']).read_text())
        check('history',history==fingerprint_history() and history['sha256']==lock['history_sha256'])
        vp=c.ECHOAI/r['validation_path']; check('validation_hash',sha256_bytes(vp.read_bytes())==lock['validation_sha256'])
        validation=json.loads(vp.read_text())
        check('validation_pass',validation['passed'] and validation['inventory']==lock['inventory'])
        packages=generate_suite_unique()
        try:
            byid={g.package_id:g for g in packages[1]}
            check('worlds',all(x['package_id'] in byid and byid[x['package_id']].package.package_sha256==x['package_sha256'] for x in assignments))
            reconstructed=[]
            for m in rows:
                label=m['label']; tp=c.ECHOAI/m['trace']; raw=tp.read_bytes()
                check('trace/'+label,sha256_bytes(raw)==m['trace_sha256'])
                trace=json.loads(raw); check('identity/'+label,trace['label']==label and trace['condition']==m['condition'])
                ulog=tp.parent.parent/'ulogs'/(label+'.ulg')
                check('ulog/'+label,ulog.exists() and sha256_bytes(ulog.read_bytes())==m['ulog_sha256']==trace['ulog_sha256'])
                check('params/'+label,c.parameters_observed(ulog,trace['driver_events'],p['px4_parameters'])==m['parameters'] and m['parameters']['ok'])
                arithmetic=_recompute(trace,p)
                for key in ['hover_horiz_rms_mm','disturb_excursion_mm']:
                    check(key+'/'+label,abs(arithmetic.get(key,1e9)-m.get(key,0))<.05)
                if m['condition']=='perturbed':
                    check('impulse/'+label,abs(arithmetic.get('impulse_ratio_ppk',-9999)-m['impulse']['ratio_ppk'])<=2)
                    check('recovery/'+label,arithmetic['recovery_status']==m['recovery']['status'])
                ep=Episode(**{k:v for k,v in trace.items() if k in {f.name for f in fields(Episode)}})
                check('force/'+label,ep.force_n==([p['disturbance']['force_mn']/1000,0,0]
                      if m['condition']=='perturbed' else [0,0,0]))
                computed=c.evaluate.episode_metrics(ep,p,package=byid[m['package_id']].package)
                for key in ('stimulus','challenge','recovery','recovery_verdict','collisions','px4_signature','timing'):
                    check(key+'/'+label,computed.get(key)==m.get(key))
                check('stage_durations/'+label,all(b-a==p['stages'][key]*1_000_000
                    for name,a,b in ep.stage_marks['plan']
                    for key in [{'climb':'takeoff_hold_ms','stabilize':'stabilize_ms','hover':'hover_ms','disturb':'disturb_ms','recover':'recover_ms'}[name]]))
                computed.update({k:m[k] for k in ('package_id','split','repeat','order_slot',
                    'lock_sha256','protocol_sha256','trace_sha256','effective_sha256','parameters')})
                check('effective_world/'+label,m['effective_sha256']==trace['effective_sha256']==worldbuild.build_effective(
                    (byid[m['package_id']].package.path/'world.sdf').read_bytes(),
                    byid[m['package_id']].package.sdf.sha256).sha256)
                reconstructed.append(computed)
            derived=verdict_groups(reconstructed,p,packages[1])
            for name,group in derived.items(): check('derived_group/'+name,r['groups'][name]==group)
        finally:
            packages[0].cleanup()
        for x in r['groups']['regression']['cases']:
            check('regression/'+x['name'],x['ok'] and sha256_bytes((c.ECHOAI/x['log']).read_bytes())==x['sha256'])
        for x in r['groups']['mutants']['cases']:
            raw=(c.ECHOAI/x['trace']).read_bytes()
            check('mutant/'+x['name'],sha256_bytes(raw)==x['sha256'])
            t=json.loads(raw)
            if x['name']=='frozen_clock':
                detected=not t['ok'] and any(e.get('ev')=='watchdog_timeout' for e in t['events'])
            else:
                detected=not _recompute(t,p).get('stimulus_ok',False)
                if x['name']=='noforce': detected=detected and t['ok']
            check('mutant_observation/'+x['name'],detected==x['ok'])
    return dict(evidence_valid=not findings,checks=checks,findings=findings,
                recomputed_episodes=len(rows) if files else 0,flight1s_green=r['flight1s_green'])


def generate_suite_unique():
    import tempfile
    tmp=tempfile.TemporaryDirectory(prefix='flight-v3-audit-')
    return tmp,generate_suite(Path(tmp.name),load_protocol(c.WORLD_PROTOCOL),REHEARSAL_SECRET,rehearsal_assignment())


def mutation_test(r):
    """Structural integrity tests use the accepted report as their control."""
    cases=[]
    operations={
        'omit_episode':lambda x:x['episodes'].pop(),
        'omit_group':lambda x:(x['groups'].pop('recovery'),x['group_status'].pop('recovery')),
        'relax_radius':lambda x:x['lock']['configuration']['recovery'].update(radius_mm=500),
        'mix_lock':lambda x:x['episodes'][0].update(lock_sha256='0'*64),
        'wrong_order':lambda x:x['episodes'].reverse(),
        'fake_green':lambda x:x.update(flight1s_green=not x['flight1s_green']),
        'activate_agent':lambda x:x.update(agent_in_gazebo=True),
        'fake_group_status':lambda x:x['group_status'].update(recovery='not_run'),
    }
    cases.append(dict(name='positive',ok=audit_report(r,files=False)['evidence_valid']))
    for name,fn in operations.items():
        clone=copy.deepcopy(r);fn(clone)
        clone['sha256']=report_sha256({k:v for k,v in clone.items() if k!='sha256'})
        got=audit_report(clone,files=False)
        cases.append(dict(name=name,ok=not got['evidence_valid'],findings=got['findings']))
    return dict(ok=all(x['ok'] for x in cases),cases=cases)


def evidence_mutations(r):
    """Changed measurements must fail even with a newly computed report hash."""
    cases=[]
    for name in ('impulse','nominal_excursion','recovery_time'):
        x=copy.deepcopy(r)
        target=next(m for m in x['episodes'] if m['condition']==(
            'nominal' if name=='nominal_excursion' else 'perturbed'))
        if name=='impulse': target['impulse']['ratio_ppk']+=100
        elif name=='nominal_excursion': target['disturb_excursion_mm']+=100
        else: target['recovery']['recovery_ms']=999999
        x['sha256']=report_sha256({k:v for k,v in x.items() if k!='sha256'})
        got=audit_report(x)
        cases.append(dict(name=name,ok=not got['evidence_valid'],findings=got['findings']))
    return dict(ok=all(x['ok'] for x in cases),cases=cases)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['bench','audit'])
    parser.add_argument('--candidate',choices=c.CANDIDATES,default='delay')
    parser.add_argument('--attempt',type=int,default=1)
    args=parser.parse_args()
    if args.command=='bench':
        raise SystemExit(0 if run_bench(args.candidate, args.attempt) else 1)
    r=json.loads(REPORT.read_text()); result=audit_report(r)
    result['mutation_self_test']=mutation_test(r)
    result['evidence_mutations']=evidence_mutations(r)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['evidence_valid'] and r['flight1s_green'] and result['mutation_self_test']['ok'] else 1)
