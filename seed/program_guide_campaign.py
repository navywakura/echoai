"""Executable associative capacity test; no ARC labels or model calls."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import random
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
from seed.verified_program_guide import ProgramGuide, solve, execute
from seed.relational_dsl import Work
from seed.relational_campaign import save, deterministic
from seed.arc_memory import sha

CONFIG={'seeds':list(range(49100,49108)),'contexts':16384,'queries':512,'observations':2,
        'units':[65536,500000],'max_candidates':1,'budget':100000,'workers':4}
SOURCES=('seed/program_guide_campaign.py','seed/verified_program_guide.py','seed/relational_dsl.py',
         'seed/relational_campaign.py','seed/kenyon_capacity.py','seed/dsl.py','seed/refinement.py',
         'seed/learn.py','docs/ECHO45-RELATIONAL-V3-DESIGN.md')


def reference(g,index):
    """Independent pixel-coordinate judge, not production transform/DSL."""
    if index>=16:
        coords=[(y,x) for y,r in enumerate(g) for x,c in enumerate(r) if c]
        y0,y1=min(y for y,x in coords),max(y for y,x in coords)
        x0,x1=min(x for y,x in coords),max(x for y,x in coords)
        g=[r[x0:x1+1] for r in g[y0:y1+1]]
    orientation=(index//2)%8;h,w=len(g),len(g[0])
    nh,nw=(w,h) if orientation in (1,3,6,7) else (h,w)
    out=[[0]*nw for _ in range(nh)]
    for y,r in enumerate(g):
        for x,c in enumerate(r):
            yp,xp=((y,x),(x,h-1-y),(h-1-y,w-1-x),(w-1-x,y),
                   (y,w-1-x),(h-1-y,x),(x,y),(w-1-x,h-1-y))[orientation]
            out[yp][xp]=c
    if index%2:
        out=[[out[y//2][x//2] for x in range(2*nw)] for y in range(2*nh)]
    return out


def canvas(shape,rng):
    # Nonzero margins vary independently from the rule; total side <= 14.
    top,left,bottom,right=[rng.randrange(1,4) for _ in range(4)]
    h,w=7+top+bottom,7+left+right;color=rng.randrange(1,10)
    g=[[0]*w for _ in range(h)]
    for y in range(7):
        for x in range(7):
            g[top+y][left+x]=color*shape[y][x]
    return g


def item(shape,label,rng):
    a,b=canvas(shape,rng),canvas(shape,rng)
    return {'train':[{'input':a,'output':reference(a,label)}],
            'test':[{'input':b,'output':reference(b,label)}]}


def one(seed,contexts,queries,export=None):
    rng=random.Random(seed);cases=[];seen=set()
    guides={str(n):ProgramGuide(n) for n in CONFIG['units']}
    fitwork={a:Work(10**12) for a in guides};start=time.process_time()
    while len(cases)<contexts:
        shape=[[rng.randrange(2) for _ in range(7)] for _ in range(7)]
        for y,x in ((0,0),(0,6),(6,0),(6,6)):shape[y][x]=1
        key=tuple(tuple(r) for r in shape)
        if key in seen:continue
        seen.add(key);label=rng.randrange(32);private=item(shape,label,rng)
        # Generator output is independently checked against production.
        p=private['train'][0]
        if execute(tuple(map(tuple,p['input'])),label,Work(10**9))!=tuple(map(tuple,p['output'])):
            raise RuntimeError('independent judge differs from executable schema')
        for arm,guide in guides.items():
            for _ in range(CONFIG['observations']):guide.observe(private,label,fitwork[arm])
        cases.append((shape,label))
    fitcpu=time.process_time()-start
    qrng=random.Random(seed+99991);indices=qrng.sample(range(contexts),min(queries,contexts))
    rows=[];start=time.process_time()
    for index in indices:
        shape,label=cases[index];private=item(shape,label,qrng)
        expected=tuple(tuple(tuple(r) for r in p['output']) for p in private['test'])
        for arm,guide,count in [('none',None,1),*[(a,g,1) for a,g in guides.items()],('exhaustive',None,32)]:
            result=solve(private,guide,candidates=count,budget=CONFIG['budget'])
            rows.append({'index':index,'arm':arm,'correct':result['predictions']==expected,
                         'committed':result['predictions'] is not None,'result':result})
    totals={}
    for arm in ('none','65536','500000','exhaustive'):
        rr=[r for r in rows if r['arm']==arm]
        totals[arm]={'solved':sum(r['correct'] for r in rr),'queries':len(rr),
                    'wrong_commitments':sum(r['committed'] and not r['correct'] for r in rr),
                    'work':sum(r['result']['work'] for r in rr)}
    if export:
        save(Path(export),guides['500000'].state())
    return {'seed':seed,'totals':totals,'rows':rows,
            'fit_work':{a:w.used for a,w in fitwork.items()},'fit_cpu_seconds':fitcpu,
            'query_cpu_seconds':time.process_time()-start,'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'weights_sha256':{a:hashlib.sha256(g.bank.weights).hexdigest() for a,g in guides.items()},
            'occupied':{a:sum(bool(v) for v in g.bank.weights) for a,g in guides.items()}}


def hashes():return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SOURCES}


def prepare(root):
    if root.exists():raise ValueError('fresh root required')
    p={'config':CONFIG,'sources':hashes(),'python':sys.version}
    save(root/'profile.json',{'payload':p,'sha256':sha(p)})
    for f in SOURCES:
        dest=root/'sources'/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/f).read_bytes())


def integrity(root):
    p=json.loads((root/'profile.json').read_text())
    if sha(p['payload'])!=p['sha256'] or p['payload']['sources']!=hashes() or p['payload']['config']!=CONFIG:
        raise ValueError('guide condition changed')


def stable(row):
    return {k:v for k,v in deterministic(row).items() if k not in ('fit_cpu_seconds','query_cpu_seconds','rss_kib')}


def run(root,phase):
    integrity(root);results=[]
    from echo_arc.observe import Journal
    journal=Journal(ROOT/'lab/observability'/root.name/(phase+'.jsonl'))
    with ProcessPoolExecutor(CONFIG['workers']) as pool:
        jobs={pool.submit(one,s,CONFIG['contexts'],CONFIG['queries'],
             str(root/phase/'guide500k.json') if s==CONFIG['seeds'][0] else None):s for s in CONFIG['seeds']}
        for f in as_completed(jobs):
            row=f.result();save(root/phase/(str(row['seed'])+'.json'),row);results.append(row)
            if phase=='audit':
                old=json.loads((root/'primary'/(str(row['seed'])+'.json')).read_text())
                if stable(old)!=stable(row):raise RuntimeError('guide replay differs')
            journal.write(kind='result',agent='verified-program-guide',origin='DEVELOPMENT',
                          seed=row['seed'],totals=row['totals'])
            save(root/'status.json',{'phase':phase,'completed':len(results),'total':len(jobs)})
            print(row['seed'],{a:t['solved'] for a,t in row['totals'].items()},flush=True)
    results.sort(key=lambda r:r['seed'])
    totals={a:{k:sum(r['totals'][a][k] for r in results) for k in ('solved','queries','wrong_commitments','work')}
            for a in ('none','65536','500000','exhaustive')}
    differences=[(r['totals']['500000']['solved']-r['totals']['65536']['solved'])/CONFIG['queries'] for r in results]
    green=all(d>0 for d in differences) and sum(differences)/len(differences)>=.05
    green=green and totals['500000']['solved']-totals['none']['solved']>=.05*totals['none']['queries']
    green=green and all(t['wrong_commitments']==0 for t in totals.values()) and totals['exhaustive']['solved']==totals['exhaustive']['queries']
    summary={'GUIDE':green,'totals':totals,'seed_differences':differences,
             'all_positive_sign_p':2**-len(differences) if all(d>0 for d in differences) else None,
             'fit_work':{a:sum(r['fit_work'][a] for r in results) for a in ('65536','500000')},
             'fit_cpu_seconds':sum(r['fit_cpu_seconds'] for r in results),
             'query_cpu_seconds':sum(r['query_cpu_seconds'] for r in results),
             'max_worker_rss_kib':max(r['rss_kib'] for r in results),
             'scope':'verified program retrieval, known motifs transformed; not ARC or novel label inference',
             'S6_green':False,'release_ready':False}
    save(root/phase/'summary.json',summary)
    if phase=='audit':save(root/'audit.json',{'valid':True,'seeds':len(results),'queries_per_arm':totals['500000']['queries']})
    journal.close();integrity(root)
    save(root/'status.json',{'stage':'DONE','phase':phase,'GUIDE':green})
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','run','audit','develop'))
    p.add_argument('--root',type=Path);a=p.parse_args()
    if a.command=='prepare':prepare(a.root)
    elif a.command=='develop':
        r=one(49000,512,64);print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
    else:run(a.root,'audit' if a.command=='audit' else 'primary')
