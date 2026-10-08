"""Controlled stress of the unchanged guide backend; no ARC solver or LLM."""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor,as_completed
import math
import multiprocessing
import os
from pathlib import Path
import random
import resource
import statistics
import sys
import time

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from seed.integration_campaign import read,save,file_sha
from seed.arc_memory import sha

CONFIG={'units':[65536,500000],'loads':[256,1024,4096,16384,65536],
        'seeds':list(range(46001,46021)),'features':8,'labels':32,'repetitions':2,
        'queries':512,'corrupt_features':[0,2],'workers':4,'primary_load':16384,
        'bootstrap_seed':46099,'bootstrap_samples':10000}
SOURCES=('seed/associative_stress.py','seed/kenyon_capacity.py',
         'docs/ECHO45-ASSOCIATIVE-STRESS-DESIGN.md')


class Probe(SparsePrimitiveGuide):
    @staticmethod
    def features(task):return task['encoded_features']


def feature(seed,context,j):return f'context:{seed}:{context}:bit:{j}'


def prepare(root):
    if root.exists():raise ValueError('fresh output required')
    p={'config':CONFIG,'sources':{f:file_sha(REPO/f) for f in SOURCES},'python':sys.version,
       'scope':'backend associative recall; encoder and program verification bypassed by declared probe'}
    root.mkdir(parents=True);save(root/'profile.json',p)
    for f in SOURCES:
        d=root/'source-archive'/f;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes((REPO/f).read_bytes())


def integrity(root):
    p=read(root/'profile.json')
    if p['config']!=CONFIG or p['python']!=sys.version:raise ValueError('changed profile')
    for f,h in p['sources'].items():
        if file_sha(REPO/f)!=h:raise ValueError('changed source: '+f)
    return p


def cell_metrics(scores,target):
    ranking=sorted(scores,key=lambda k:(-scores[k],k));rank=ranking.index(target)+1
    return (int(rank==1),int(rank<=5),1/rank,scores[target]-max(v for k,v in scores.items() if k!=target))


def one(args):
    seed,phase=args;names=tuple(f'p{i:02d}' for i in range(CONFIG['labels']))
    banks={n:Probe(n,names) for n in CONFIG['units']};exact=Counter()
    rng=random.Random(seed);label_permutation=list(names);rng.shuffle(label_permutation)
    cpu_fit={n:0. for n in banks};rows=[];previous=0;journal=None
    if phase=='primary':
        from echo_arc.observe import Journal
        journal=Journal(REPO/'lab/observability/capacity-stress-20261002'/f'{seed}-{os.getpid()}.jsonl')
    for count in CONFIG['loads']:
        for context in range(previous,count):
            target=label_permutation[context%len(names)]
            feats=[feature(seed,context,j) for j in range(CONFIG['features'])]
            for f in feats:exact[f,target]+=CONFIG['repetitions']
            for n,g in banks.items():
                start=time.process_time()
                for f in feats:
                    indices=g._indices(f,target)
                    for _ in range(CONFIG['repetitions']):
                        for index in indices:g.weights[index]=min(255,g.weights[index]+1)
                cpu_fit[n]+=time.process_time()-start
        previous=count
        chosen=random.Random(seed+count).sample(range(count),min(CONFIG['queries'],count))
        for corrupt in CONFIG['corrupt_features']:
            totals={str(n):[0.,0.,0.,0.] for n in banks};totals['exact']=[0.,0.,0.,0.]
            errors={str(n):0. for n in banks};query_cpu={str(n):0. for n in banks}
            noise=random.Random(seed*100+count+corrupt)
            for context in chosen:
                target=label_permutation[context%len(names)]
                feats=[feature(seed,context,j) for j in range(CONFIG['features'])]
                for j in noise.sample(range(len(feats)),corrupt):
                    foreign=(context+noise.randrange(1,count))%count
                    feats[j]=feature(seed,foreign,j)
                scores_exact={name:8*sum(exact[f,name] for f in feats) for name in names}
                totals['exact']=[a+b for a,b in zip(totals['exact'],cell_metrics(scores_exact,target))]
                for n,g in banks.items():
                    start=time.process_time()
                    scores=g.probs({'encoded_features':feats})
                    metric=cell_metrics(scores,target)
                    query_cpu[str(n)]+=time.process_time()-start
                    totals[str(n)]=[a+b for a,b in zip(totals[str(n)],metric)]
                    raw_target=sum(g.weights[i] for f in feats for i in g._indices(f,target))
                    errors[str(n)]+=abs(raw_target-scores_exact[target])
            row={'seed':seed,'contexts':count,'corrupt_features':corrupt,'queries':len(chosen),
              'metrics':{n:dict(zip(('accuracy','top5','mrr','mean_margin'),[v/len(chosen) for v in vals])) for n,vals in totals.items()},
              'banks':{str(n):{'nonzero':sum(v>0 for v in g.weights),'saturated_255':sum(v==255 for v in g.weights),
                  'max_weight':max(g.weights),'vector_bytes':len(g.weights),
                  'mean_absolute_target_score_error':errors[str(n)]/len(chosen)} for n,g in banks.items()},
              'fit_cpu_seconds':{str(n):v for n,v in cpu_fit.items()},'query_cpu_seconds':query_cpu,
              'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            rows.append(row)
            if journal:journal.write(kind='refinement_result',agent='capacity-probe',origin='SYNTHETIC_DEVELOPMENT',
                  status='MEASURED',seed=seed,contexts=count,corrupt_features=corrupt,metrics=row['metrics'])
    if journal:journal.close()
    return rows


def deterministic(rows):
    return [{k:v for k,v in row.items() if k not in ('fit_cpu_seconds','query_cpu_seconds','rss_kib')} for row in rows]


def run(root,phase='primary',pilot=False):
    profile=integrity(root)
    seeds=CONFIG['seeds'][:2] if pilot or phase=='audit' else CONFIG['seeds']
    pending=[s for s in seeds if not (root/phase/f'{s}.json').exists()]
    for s in set(seeds)-set(pending):
        if read(root/phase/f'{s}.json')['profile_sha256']!=sha(profile):raise ValueError('foreign cached seed')
    start=time.monotonic()
    with ProcessPoolExecutor(CONFIG['workers'],mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(one,(s,phase)):s for s in pending}
        for f in as_completed(futures):
            s=futures[f];rows=f.result();save(root/phase/f'{s}.json',{'profile_sha256':sha(profile),'rows':rows})
            if phase=='audit' and deterministic(rows)!=deterministic(read(root/'primary'/f'{s}.json')['rows']):
                raise RuntimeError('replay mismatch')
            save(root/'status.json',{'phase':phase,'finished_seeds':len(list((root/phase).glob('*.json'))),
                 'total_seeds':len(seeds),'seconds':time.monotonic()-start})
            print(s,phase,'done',flush=True)
    integrity(root)
    if phase=='audit':
        for s in seeds:
            if deterministic(read(root/'audit'/f'{s}.json')['rows'])!=deterministic(read(root/'primary'/f'{s}.json')['rows']):
                raise RuntimeError('cached audit mismatch')
        save(root/'audit.json',{'valid':True,'seeds':seeds,'profile_sha256':sha(profile)})
    if phase=='primary' and not pilot:summarize(root)


def summarize(root):
    rows=[r for s in CONFIG['seeds'] for r in read(root/'primary'/f'{s}.json')['rows']]
    curve=[]
    for count in CONFIG['loads']:
        for corrupt in CONFIG['corrupt_features']:
            subset=[r for r in rows if r['contexts']==count and r['corrupt_features']==corrupt]
            curve.append({'contexts':count,'corrupt_features':corrupt,
             'accuracy':{n:statistics.mean(r['metrics'][n]['accuracy'] for r in subset) for n in ('65536','500000','exact')}})
    primary=[r for r in rows if r['contexts']==CONFIG['primary_load'] and r['corrupt_features']==0]
    delta=[r['metrics']['500000']['accuracy']-r['metrics']['65536']['accuracy'] for r in primary]
    rng=random.Random(CONFIG['bootstrap_seed'])
    samples=sorted(statistics.mean(rng.choices(delta,k=len(delta))) for _ in range(CONFIG['bootstrap_samples']))
    ci=[samples[int(.025*len(samples))],samples[int(.975*len(samples))]]
    nonzero=[x for x in delta if x!=0];positive=sum(x>0 for x in nonzero)
    p=sum(math.comb(len(nonzero),k) for k in range(positive,len(nonzero)+1))/2**len(nonzero) if nonzero else 1.
    means={n:statistics.mean(r['metrics'][n]['accuracy'] for r in primary) for n in ('65536','500000','exact')}
    green=means['500000']>=.95 and means['65536']<=.90 and statistics.mean(delta)>=.05 and ci[0]>0 and p<.01 and means['exact']>=.99
    save(root/'summary.json',{'curve':curve,'primary':{'mean_accuracy':means,'difference':statistics.mean(delta),
       'paired_seed_bootstrap_95':ci,'one_sided_sign_p':p,'green':green},
       'scope':'associative backend recall under declared load; not ARC, neuron dynamics or global memory capacity'})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','pilot','run','audit'));p.add_argument('--root',type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':prepare(a.root)
    else:run(a.root,'audit' if a.command=='audit' else 'primary',a.command=='pilot')
