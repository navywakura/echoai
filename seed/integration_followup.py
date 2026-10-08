"""Fixed V2 follow-up on disjoint public training tasks, without further tuning."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import multiprocessing
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from seed import integration_campaign as c, integration_revision as r
from seed.arc_memory import sha
from echoai.seed import gym

SEED='echo45-integration-confirmation-20261002-v1'
SOURCES=('seed/integration_followup.py','docs/ECHO45-INTEGRATION-FOLLOWUP-DESIGN.md')


def prepare(root,reference):
    p=c.integrity(reference)
    if root.exists():raise ValueError('fresh follow-up directory required')
    excluded=set(p['programs'])|{t['id'] for t in p['tasks'].values()}
    fit=set(p['programs']); tasks={}; train=set(gym.split()['train'])
    for pool in ('arc1','arc2'):
        available={f.stem for f in gym.POOLS[pool].glob('*.json')}&train-excluded
        chosen=sorted(available,key=lambda tid:hashlib.sha256((SEED+pool+tid).encode()).hexdigest())[:64]
        if len(chosen)!=64:raise ValueError('insufficient disjoint tasks')
        for tid in chosen:tasks[pool+'/'+tid]={'pool':pool,'id':tid,'sha256':c.file_sha(gym.POOLS[pool]/(tid+'.json'))}
        excluded.update(chosen)
    p=deepcopy(p);p['tasks']=tasks;p['followup_sampling_seed']=SEED
    p['development_source_sha256']=sha(c.read(reference/'profile.json'))
    p['followup_scope']='disjoint from current development and fit; public training may have been seen in earlier studies'
    p['sources'].update({f:c.file_sha(REPO/f) for f in SOURCES})
    root.mkdir(parents=True);c.save(root/'cohort/profile.json',p)
    for f in SOURCES:
        dst=root/'source-archive'/f;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((REPO/f).read_bytes())
    r.prepare(root/'run',root/'cohort')
    c.save(root/'selection.json',{'ids':sorted(t['id'] for t in tasks.values()),
       'unique':len({t['id'] for t in tasks.values()}),'fit_overlap':sorted(fit&{t['id'] for t in tasks.values()}),
       'development_overlap':sorted({t['id'] for t in c.read(reference/'profile.json')['tasks'].values()}&{t['id'] for t in tasks.values()}),
       'sampling_seed':SEED,'sources':{f:c.file_sha(REPO/f) for f in SOURCES}})


def run(root):
    reference=root/'cohort';p=c.integrity(reference)
    # Actual independent V1 runs provide the parity reference required by V2.
    with ProcessPoolExecutor(4,mp_context=multiprocessing.get_context('spawn'),
        initializer=c.initialize,initargs=(str(reference),'primary')) as pool:
        futures={pool.submit(c.one,(key,'no_views')):key for key in p['tasks']}
        for f in as_completed(futures):
            key=futures[f];c.save(reference/'primary/no_views'/(key.replace('/','-')+'.json'),f.result())
    c.integrity(reference)
    r.run(root/'run','primary')
    r.run(root/'run','audit')


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('prepare','run'));ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--reference',type=Path)
    a=ap.parse_args()
    if a.command=='prepare':prepare(a.root,a.reference)
    else:run(a.root)
