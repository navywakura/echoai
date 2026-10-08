"""Causal, synthetic transfer of verified ARC programs through the 3E diary.

Fresh instances of known generator families, not an official ARC examination.
Training programs must be discovered by the solver; the generator supplies no
program to the agent. Test outputs are judged only after each solve returns.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from seed import arc_capabilities as gen
from seed.arc_memory import ArcMemory, sha
from seed.integrated_grid import solve
from seed.integration_campaign import read, save, file_sha
from echoai.seed import sandbox
from echoai.seed.refinement import RefinementLibrary, solver_input

FAMILIES=tuple(gen.FAMILIES)
ARMS=('memory','reset','remove_formative','remove_control','no_refinement')
CONFIG={'max_trials':2000,'max_depth':4,'beam_width':12,'views':False,
        'consistency':True,'verification_window':96}
SOURCES=('seed/integration_transfer.py','seed/arc_memory.py','seed/integrated_grid.py',
         'seed/arc_capabilities.py','seed/refinement.py','seed/learn.py','seed/dsl.py',
         'seed/village2.py','seed/village3.py','seed/village3_factorized.py',
         'seed/village3_efficient.py','seed/village3_receipts.py',
         'docs/ECHO45-INTEGRATION-TRANSFER-DESIGN.md')


def task(family,seed):
    rng=random.Random(str(seed)+'/'+family)
    pairs=[gen.example(family,rng,i) for i in range(5)]
    return {'train':pairs[:3],'test':pairs[3:]}


def prepare(root):
    if root.exists():raise ValueError('fresh output required')
    p={'config':CONFIG,'families':FAMILIES,'arms':ARMS,
       'fit_seeds':[452001,452002], 'test_seeds':list(range(452101,452117)),
       'sources':{f:file_sha(REPO/f) for f in SOURCES},'python':sys.version,
       'origin':'NEW_SYNTHETIC_INSTANCES_OF_KNOWN_FAMILIES',
       'thresholds':{'memory_work_reduction':0.20,'zero_accuracy_regressions':True,
                     'withdraw_formative_worse_than_control':True,'refinement_accuracy_gain':True}}
    p['tasks_sha256']=sha({f:{str(s):task(f,s) for s in p['fit_seeds']+p['test_seeds']} for f in FAMILIES})
    root.mkdir(parents=True)
    save(root/'profile.json',p)
    for f in SOURCES:
        t=root/'source-archive'/f;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes((REPO/f).read_bytes())
    return p


def integrity(root):
    p=read(root/'profile.json')
    if p['config']!=CONFIG or p['python']!=sys.version:raise ValueError('changed profile')
    for f,h in p['sources'].items():
        if file_sha(REPO/f)!=h:raise ValueError('changed source '+f)
    if p['tasks_sha256']!=sha({f:{str(s):task(f,s) for s in p['fit_seeds']+p['test_seeds']} for f in FAMILIES}):
        raise ValueError('changed generator')
    return p


def train(p,journal=None):
    sandbox._set_level('S2v')
    library=RefinementLibrary()
    memory=ArcMemory()
    fit=[]; receipts={f:[] for f in FAMILIES}
    for family in FAMILIES:
        for seed in p['fit_seeds']:
            public=solver_input(task(family,seed))
            result=solve(public,library,journal=journal,**CONFIG)
            if result['program'] is None:
                raise RuntimeError('training synthesis failed: '+family)
            receipt=memory.remember(public,result['program'],library,'synthetic-fit:'+family+':'+str(seed),
                                    work=result['metrics']['primitive_calls'])
            receipts[family].append(receipt)
            fit.append({'family':family,'seed':seed,'result':result,'receipt':receipt})
    # Serialization + replay is part of the operational transfer path.
    memory=ArcMemory.restore(json.loads(json.dumps(memory.state())),library)
    return library,memory,fit,receipts


def run(root,phase):
    p=integrity(root)
    journal=None
    if phase=='primary':
        from echo_arc.observe import Journal
        journal=Journal(REPO/'lab/observability'/root.name/'transfer.jsonl')
    lib,memory,fit,receipts=train(p,journal)
    save(root/phase/'memory.json',memory.state());save(root/phase/'fit.json',fit)
    memories={'memory':memory,'reset':None,'no_refinement':None,
              'remove_formative':memory.ablate(receipts['composition']),
              'remove_control':memory.ablate(receipts['objects'])}
    rows=[]
    for family in FAMILIES:
        for seed in p['test_seeds']:
            private=task(family,seed);public=solver_input(private)
            for arm in ARMS:
                start=time.process_time()
                result=solve(public,lib,memory=memories[arm],refinement=arm!='no_refinement',journal=journal,**CONFIG)
                cost=time.process_time()-start
                correct=result['program'] is not None and result['predictions']==[e['output'] for e in private['test']]
                row={'family':family,'seed':seed,'arm':arm,'result':result,'correct':correct,'cpu_seconds':cost}
                rows.append(row);save(root/phase/arm/(family+'-'+str(seed)+'.json'),row)
            save(root/'status.json',{'phase':phase,'completed':len(rows),'total':len(FAMILIES)*len(p['test_seeds'])*len(ARMS)})
    if journal is not None:journal.close()
    integrity(root)
    totals={}
    for family in (*FAMILIES,'all'):
        totals[family]={}
        for arm in ARMS:
            group=[r for r in rows if r['arm']==arm and (family=='all' or r['family']==family)]
            totals[family][arm]={'solved':sum(r['correct'] for r in group),'tasks':len(group),
              'primitive_calls':sum(r['result']['metrics']['primitive_calls'] for r in group),
              'trials':sum(r['result']['metrics']['trials'] for r in group),
              'memory_reads':sum(r['result']['metrics']['memory_reads'] for r in group),
              'cpu_seconds':sum(r['cpu_seconds'] for r in group)}
    indexed={(r['family'],r['seed'],r['arm']):r for r in rows}
    losses=[(f,s) for f in FAMILIES for s in p['test_seeds']
            if indexed[f,s,'reset']['correct'] and not indexed[f,s,'memory']['correct']]
    full=totals['all']['memory'];reset=totals['all']['reset'];comp=totals['composition']
    saved_work=1-full['primitive_calls']/max(1,reset['primitive_calls'])
    # Count acquisition again in the finite sequence, not only amortized reuse.
    fit_work=sum(r['result']['metrics']['primitive_calls'] for r in fit)
    save(root/phase/'rows.json',rows)
    summary={'totals':totals,'memory_work_reduction':saved_work,'fit_search_primitive_calls':fit_work,
      'work_reduction_including_fit_search':1-(full['primitive_calls']+fit_work)/max(1,reset['primitive_calls']),
      'losses_vs_reset':losses,'scope':'new instances of four constructed families; not official ARC',
      'gates':{'memory_reuse':not losses and full['solved']>=reset['solved'] and saved_work>=.20,
        'causal_withdrawal':comp['remove_formative']['primitive_calls']>comp['remove_control']['primitive_calls']
                              and comp['remove_control']['solved']>=comp['remove_formative']['solved'],
        'refinement':comp['reset']['solved']>comp['no_refinement']['solved'] and all(
            totals[f]['reset']['solved']>=totals[f]['no_refinement']['solved'] for f in FAMILIES)}}
    if phase=='audit':
        previous=read(root/'primary/rows.json')
        for old,new in zip(previous,rows,strict=True):
            if sha(old['result'])!=sha(new['result']) or old['correct']!=new['correct']:
                raise RuntimeError('transfer replay differs')
        if sha(read(root/'primary/fit.json'))!=sha(fit):raise RuntimeError('acquisition replay differs')
        summary['replays_identical']=len(rows);summary['fit_replays_identical']=len(fit)
    save(root/(phase+'-summary.json'),summary)
    save(root/'status.json',{'phase':phase,'stage':'DONE','completed':len(rows)})
    print(json.dumps({k:v for k,v in summary.items() if k!='totals'}),flush=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=('prepare','run','audit'));ap.add_argument('--root',type=Path,required=True)
    args=ap.parse_args()
    if args.command=='prepare':prepare(args.root)
    else:run(args.root,'audit' if args.command=='audit' else 'primary')
