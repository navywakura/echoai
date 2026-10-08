"""Recorded public-development ablations for the additive ECHO-4.5 candidate."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from echoai.seed import gym, sandbox
from echoai.seed.final_eval import learned_state, solver_input
from echoai.seed.learn import Library
from echoai.seed.refinement import RefinementLibrary
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from seed.arc_memory import ArcMemory, sha
from seed.integrated_grid import solve
from harness.localdev.common import frozen_paths

ARMS=('base','full','no_memory','no_refinement','no_views','no_consistency','no_guide','guide640','guide65536')
CONFIG={'max_trials':2000,'max_depth':4,'beam_width':12,'verification_window':96,
        'workers':4,'model_calls':0,'origin':'ARC_PUBLIC_TRAINING_DEVELOPMENT',
        'sampling_seed':'echo45-integration-20261002-v1','attempts_scored':1}
SOURCES=('seed/arc_memory.py','seed/integrated_grid.py','seed/integration_campaign.py',
         'tests/test_arc_integration.py','docs/ECHO45-INTEGRATION-DESIGN.md',
         'seed/refinement.py','seed/kenyon_capacity.py','seed/learn.py','seed/dsl.py',
         'seed/village2.py','seed/village3.py','seed/village3_factorized.py',
         'seed/village3_efficient.py','seed/village3_receipts.py')
_STATE=None


def read(path):return json.loads(Path(path).read_text())


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp-'+str(os.getpid()))
    tmp.write_text(json.dumps(value,sort_keys=True)+'\n');tmp.replace(path)


def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def status(root,stage,**fields):
    data={'stage':stage,'at':datetime.now(timezone.utc).isoformat(),**fields}
    save(root/'status.json',data);print(json.dumps(data),flush=True)


def prepare(root,per_pool=16):
    if (root/'profile.json').exists():return integrity(root)
    if root.exists():raise ValueError('new run directory required')
    if per_pool not in (16,64):raise ValueError('declared cohort sizes: 16 or 64 per pool')
    sandbox._set_level('S2v')
    state=learned_state()
    programs=sandbox.verified_programs('echo45-s2v')
    train=set(gym.split()['train'])
    if not set(programs)<=train:raise ValueError('historical fit outside training')
    tasks={}
    for pool in ('arc1','arc2'):
        available={p.stem for p in gym.POOLS[pool].glob('*.json')}&train-set(programs)
        ordered=sorted(available,key=lambda t:hashlib.sha256((CONFIG['sampling_seed']+pool+t).encode()).hexdigest())
        for tid in ordered[:per_pool]:
            key=pool+'/'+tid
            tasks[key]={'pool':pool,'id':tid,'sha256':file_sha(gym.POOLS[pool]/(tid+'.json'))}
    all_sources=set(SOURCES)|frozen_paths(REPO)
    profile={'config':CONFIG,'arms':list(ARMS),'per_pool':per_pool,'state':state,'programs':programs,
             'tasks':tasks,'python':sys.version,
             'sources':{p:file_sha(REPO/p) for p in sorted(all_sources) if (REPO/p).is_file()},
             'fit':{tid:{'sha256':file_sha(gym.catalogue()[tid]),'path':str(gym.catalogue()[tid].relative_to(REPO))}
                    for tid in sorted(programs)}}
    root.mkdir(parents=True)
    for name in SOURCES:
        target=root/'source-archive'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((REPO/name).read_bytes())
    save(root/'profile.json',profile)
    status(root,'PREPARED',tasks=len(tasks),jobs=len(tasks)*len(ARMS),S6_deferred=True)
    return profile


def integrity(root):
    p=read(root/'profile.json')
    if p['config']!=CONFIG or p['python']!=sys.version:raise ValueError('profile configuration changed')
    for name,want in p['sources'].items():
        if file_sha(REPO/name)!=want:raise ValueError('frozen source changed: '+name)
    for record in p['fit'].values():
        if file_sha(REPO/record['path'])!=record['sha256']:raise ValueError('fit source changed')
    for record in p['tasks'].values():
        if file_sha(gym.POOLS[record['pool']]/(record['id']+'.json'))!=record['sha256']:
            raise ValueError('development task changed')
    return p


def fitted(profile):
    sandbox._set_level('S2v')
    lib=RefinementLibrary(profile['state']['concepts'],profile['state']['prior'])
    memory=ArcMemory(limit=256)
    guides={n:SparsePrimitiveGuide(n) for n in (640,65536,500000)}
    fit_metrics={str(n):0.0 for n in guides};fit_metrics['memory']=0.0
    for tid in sorted(profile['programs']):
        public=solver_input(read(REPO/profile['fit'][tid]['path']))
        program=profile['programs'][tid]
        start=time.process_time();memory.remember(public,program,lib,'ARC_TRAINING:'+tid)
        fit_metrics['memory']+=time.process_time()-start
        for n,guide in guides.items():
            start=time.process_time();guide.observe(public,program,lib)
            fit_metrics[str(n)]+=time.process_time()-start
    memory.verify(lib)
    return lib,memory,guides,fit_metrics


def initialize(root,phase):
    global _STATE
    root=Path(root);p=read(root/'profile.json')
    lib,memory,guides,cost=fitted(p)
    journal=None
    if phase=='primary':
        from echo_arc.observe import Journal
        journal=Journal(REPO/'lab/observability'/root.name/(str(os.getpid())+'.jsonl'))
    _STATE=(root,p,lib,memory,guides,cost,journal)


def one(job):
    key,arm=job
    root,p,lib,memory,guides,fit_cost,journal=_STATE
    record=p['tasks'][key]
    private=read(gym.POOLS[record['pool']]/(record['id']+'.json'))
    public=solver_input(private)
    use_memory=None if arm in ('base','no_memory') else memory
    guide=None if arm in ('base','no_guide') else guides[640 if arm=='guide640' else 65536 if arm=='guide65536' else 500000]
    selected=Library(p['state']['concepts'],p['state']['prior']) if arm=='base' else lib
    start=time.monotonic();cpu=time.process_time()
    result=solve(public,selected,memory=use_memory,guide=guide,
                 max_trials=CONFIG['max_trials'],max_depth=CONFIG['max_depth'],beam_width=CONFIG['beam_width'],
                 verification_window=CONFIG['verification_window'],
                 views=arm not in ('base','no_views'),refinement=arm not in ('base','no_refinement'),
                 consistency=arm not in ('base','no_consistency'),journal=journal)
    cpu=time.process_time()-cpu;elapsed=time.monotonic()-start
    # The judge accesses private outputs only after the solver returned.
    correct=bool(result['program'] is not None and result['predictions']==[pair['output'] for pair in private['test']])
    if result['test_ok'] is not None or result['metrics']['trials']>CONFIG['max_trials']:
        raise ValueError('label or budget invariant violated')
    return {'task':key,'arm':arm,'correct':correct,'result':result,'behavior_sha256':sha(result),
            'seconds':elapsed,'cpu_seconds':cpu,'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'fit_cpu_seconds':fit_cost,'profile_sha256':sha(p),'origin':CONFIG['origin']}


def summarize(root,phase,p):
    rows=[read(root/phase/arm/(key.replace('/','-')+'.json')) for key in p['tasks'] for arm in ARMS]
    by={(r['task'],r['arm']):r for r in rows}
    totals={}
    for pool in ('arc1','arc2','all'):
        keys=[k for k in p['tasks'] if pool=='all' or k.startswith(pool+'/')]
        totals[pool]={}
        for arm in ARMS:
            group=[by[k,arm] for k in keys]
            baseline={k for k in keys if by[k,'base']['correct']}
            solved={r['task'] for r in group if r['correct']}
            totals[pool][arm]={'solved':len(solved),'tasks':len(keys),'gained_vs_base':sorted(solved-baseline),
              'lost_vs_base':sorted(baseline-solved),'trials':sum(r['result']['metrics']['trials'] for r in group),
              'primitive_calls':sum(r['result']['metrics']['primitive_calls'] for r in group),
              'memory_reads':sum(r['result']['metrics']['memory_reads'] for r in group),
              'cpu_seconds':sum(r['cpu_seconds'] for r in group),'wall_seconds_sum':sum(r['seconds'] for r in group)}
    result={'phase':phase,'totals':totals,'development_only':True,'official_score':False,'S6_green':False}
    if phase=='audit':
        for r in rows:
            prior=read(root/'primary'/r['arm']/(r['task'].replace('/','-')+'.json'))
            if r['behavior_sha256']!=prior['behavior_sha256'] or r['correct']!=prior['correct']:
                raise RuntimeError('replay mismatch: '+r['task']+'/'+r['arm'])
        result['replays_identical']=len(rows)
    save(root/(phase+'-summary.json'),result)
    return result


def run(root,phase='primary'):
    p=integrity(root);start=time.monotonic()
    jobs=[(k,a) for k in p['tasks'] for a in ARMS]
    pending=[]
    for k,a in jobs:
        path=root/phase/a/(k.replace('/','-')+'.json')
        if path.exists():
            record=read(path)
            if record['profile_sha256']!=sha(p):raise ValueError('cache belongs to another profile')
        else:pending.append((k,a))
    completed=len(jobs)-len(pending)
    status(root,'RUNNING_'+phase.upper(),completed=completed,total=len(jobs))
    with ProcessPoolExecutor(CONFIG['workers'],mp_context=multiprocessing.get_context('spawn'),
                             initializer=initialize,initargs=(str(root),phase)) as pool:
        futures={pool.submit(one,job):job for job in pending}
        for future in as_completed(futures):
            row=future.result();k,a=futures[future]
            save(root/phase/a/(k.replace('/','-')+'.json'),row)
            completed+=1
            if completed%9==0 or completed==len(jobs):
                elapsed=time.monotonic()-start
                rate=(completed-(len(jobs)-len(pending)))/max(elapsed,.001)
                status(root,'RUNNING_'+phase.upper(),completed=completed,total=len(jobs),
                       elapsed_seconds=round(elapsed,2),eta_seconds=round((len(jobs)-completed)/max(rate,.001),2))
    integrity(root)
    summary=summarize(root,phase,p)
    status(root,phase.upper()+'_DONE',completed=len(jobs),total=len(jobs),seconds=time.monotonic()-start)
    return summary


def main():
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('prepare','run','audit'))
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--per-pool',type=int,default=16)
    a=ap.parse_args();root=a.root.resolve()
    try:
        if a.command=='prepare':prepare(root,a.per_pool)
        else:run(root,'audit' if a.command=='audit' else 'primary')
    except Exception as e:
        if root.exists():status(root,'BLOCKED',error=type(e).__name__,message=str(e))
        raise


if __name__=='__main__':main()
