"""V2 search-order hypothesis on the same public development cohort."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from seed import integration_campaign as c
from seed.arc_memory import sha
from seed.integrated_grid import solve as v1
from seed.integrated_grid_v2 import solve as v2
from echoai.seed.refinement import solver_input
from echoai.seed import gym

ARMS=('v1_no_views','v2','v2_views','v2_no_memory','v2_no_guide','v2_640','v2_65536','v2_no_refinement','v2_no_consistency')
SOURCES=('seed/integration_revision.py','seed/integrated_grid_v2.py','docs/ECHO45-INTEGRATION-V2-DESIGN.md')
STATE=None


def prepare(root,reference):
    p=c.integrity(reference)
    if root.exists():raise ValueError('new output required')
    data={'reference':str(reference.resolve()),'reference_sha256':sha(p),
          'sources':{f:c.file_sha(REPO/f) for f in SOURCES},'arms':ARMS,'config':c.CONFIG,
          'tasks':p['tasks'],'python':sys.version,'development_revision':2,'S6_deferred':True}
    root.mkdir(parents=True);c.save(root/'profile.json',data)
    for f in SOURCES:
        t=root/'source-archive'/f;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((REPO/f).read_bytes())


def integrity(root):
    p=c.read(root/'profile.json')
    reference=c.integrity(Path(p['reference']))
    if sha(reference)!=p['reference_sha256'] or p['python']!=sys.version:raise ValueError('reference changed')
    for f,h in p['sources'].items():
        if c.file_sha(REPO/f)!=h:raise ValueError('source changed: '+f)
    return p,reference


def initialize(root,phase):
    global STATE
    root=Path(root);p,reference=integrity(root)
    lib,memory,guides,fit_cost=c.fitted(reference)
    journal=None
    if phase=='primary':
        from echo_arc.observe import Journal
        journal=Journal(REPO/'lab/observability'/root.name/(str(os.getpid())+'.jsonl'))
    STATE=(p,lib,memory,guides,journal)


def one(job):
    key,arm=job;p,lib,memory,guides,journal=STATE;r=p['tasks'][key]
    private=c.read(gym.POOLS[r['pool']]/(r['id']+'.json'))
    guide=None if arm=='v2_no_guide' else guides[640 if arm=='v2_640' else 65536 if arm=='v2_65536' else 500000]
    start=time.process_time()
    result=(v1 if arm=='v1_no_views' else v2)(solver_input(private),lib,
        memory=None if arm=='v2_no_memory' else memory,guide=guide,views=arm=='v2_views',
        refinement=arm!='v2_no_refinement',consistency=arm!='v2_no_consistency',journal=journal,
        **{k:c.CONFIG[k] for k in ('max_trials','max_depth','beam_width','verification_window')})
    cpu=time.process_time()-start
    correct=result['program'] is not None and result['predictions']==[p['output'] for p in private['test']]
    return {'task':key,'arm':arm,'result':result,'correct':correct,'cpu_seconds':cpu,
            'behavior_sha256':sha(result),'profile_sha256':sha(p),
            'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def run(root,phase):
    p,_=integrity(root);start=time.monotonic()
    jobs=[(key,a) for key in p['tasks'] for a in ARMS]
    paths=lambda key,arm:root/phase/arm/(key.replace('/','-')+'.json')
    pending=[]
    for key,a in jobs:
        if paths(key,a).exists():
            if c.read(paths(key,a))['profile_sha256']!=sha(p):raise ValueError('foreign cache')
        else:pending.append((key,a))
    done=len(jobs)-len(pending)
    with ProcessPoolExecutor(4,mp_context=multiprocessing.get_context('spawn'),
                             initializer=initialize,initargs=(str(root),phase)) as pool:
        futures={pool.submit(one,j):j for j in pending}
        for f in as_completed(futures):
            key,a=futures[f];c.save(paths(key,a),f.result());done+=1
            if done%18==0:c.status(root,'RUNNING_'+phase.upper(),completed=done,total=len(jobs))
    rows=[c.read(paths(k,a)) for k,a in jobs]
    totals={};index={(r['task'],r['arm']):r for r in rows}
    for population in ('arc1','arc2','all'):
        keys=[k for k in p['tasks'] if population=='all' or k.startswith(population+'/')]
        totals[population]={}
        base={k for k in keys if index[k,'v1_no_views']['correct']}
        for a in ARMS:
            group=[index[k,a] for k in keys];solved={r['task'] for r in group if r['correct']}
            totals[population][a]={'solved':len(solved),'tasks':len(keys),
              'gains_vs_v1_no_views':sorted(solved-base),'losses_vs_v1_no_views':sorted(base-solved),
              'primitive_calls':sum(r['result']['metrics']['primitive_calls'] for r in group),
              'cpu_seconds':sum(r['cpu_seconds'] for r in group)}
    result={'totals':totals,'development_only':True,'official_score':False}
    # v1 is rerun to check the comparator before interpreting a new hypothesis.
    for k in p['tasks']:
        prior=c.read(Path(p['reference'])/'primary/no_views'/(k.replace('/','-')+'.json'))
        if index[k,'v1_no_views']['behavior_sha256']!=prior['behavior_sha256']:
            raise RuntimeError('v1 comparator failed parity')
    result['v1_parity']=len(p['tasks'])
    if phase=='audit':
        for r in rows:
            prior=c.read(root/'primary'/r['arm']/(r['task'].replace('/','-')+'.json'))
            if r['behavior_sha256']!=prior['behavior_sha256'] or r['correct']!=prior['correct']:
                raise RuntimeError('v2 replay mismatch')
        result['replays_identical']=len(rows)
    integrity(root);c.save(root/(phase+'-summary.json'),result)
    c.status(root,phase.upper()+'_DONE',completed=len(rows),total=len(rows),seconds=time.monotonic()-start)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('prepare','run','audit'))
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--reference',type=Path)
    a=ap.parse_args()
    if a.command=='prepare':prepare(a.root,a.reference)
    else:run(a.root,'audit' if a.command=='audit' else 'primary')
