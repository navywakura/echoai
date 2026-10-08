"""Preregistered private V3 module comparison. Commands: develop, prepare, run, audit."""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
from echoai.seed.refinement import solver_input
from seed.arc_memory import ArcMemory, sha
from seed.arc_delayed_policy import ArcPolicy
from seed.relational_dsl import RelationalLibrary
from seed.relational_solver import solve
from seed.relational_tasks import task, ambiguous, correct, FAMILIES

CONFIG={'budget':500000,'verification_window':0,'consistency':False}
ARMS={'old_fixed':{'relational':False},'old_policy':{'relational':False,'adaptive':True},
      'new_fixed':{},'new_policy':{'adaptive':True},'no_memory':{'memory_off':True},
      'search_first':{'order':'search_first'},
      'integrated':{'adaptive':True,'views':True,'consistency':True,'verification_window':32},
      'no_refinement':{'memory_off':True,'refinement':False},
      'views':{'memory_off':True,'views':True}}
SOURCES=('seed/relational_dsl.py','seed/arc_delayed_policy.py','seed/relational_solver.py',
         'seed/relational_tasks.py','seed/relational_campaign.py','seed/verified_program_guide.py',
         'seed/arc_memory.py','seed/village2.py','seed/village3.py','seed/village3_receipts.py',
         'seed/village3_factorized.py','seed/village3_efficient.py','seed/refinement.py',
         'seed/dsl.py','seed/learn.py','seed/kenyon_capacity.py',
         'seed/echo45_v3.py','tests/test_relational_v3.py',
         'docs/ECHO45-RELATIONAL-V3-DESIGN.md')


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n');temp.replace(path)


def hashes():return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SOURCES}


def prepare(root):
    if root.exists():raise ValueError('fresh condition required')
    profile={'condition':'ECHO45-RELATIONAL-V3','config':CONFIG,'arms':ARMS,
             'fit_seeds':list(range(47100,47356)),'confirmation_seeds':list(range(48000,48032)),
             'sources':hashes(),'python':sys.version,'scope':'synthetic module transfer; ARC untested; S6 deferred'}
    save(root/'profile.json',{'sha256':sha(profile),'payload':profile})
    for f in SOURCES:
        dest=root/'sources'/f;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ROOT/f).read_bytes())
    save(root/'status.json',{'stage':'PREPARED','games_started':False})


def integrity(root):
    p=json.loads((root/'profile.json').read_text())
    if sha(p['payload'])!=p['sha256'] or p['payload']['sources']!=hashes() or p['payload']['python']!=sys.version:
        raise ValueError('frozen condition changed')
    return p['payload']


def acquire(journal=None):
    memory=ArcMemory(limit=256);lib=RelationalLibrary();fit=[];keys={}
    for family in ('paint','stamp','compose'):
        private=task(family,47000)
        result=solve(private,memory=None,journal=journal,**CONFIG)
        if not result['program']:raise ValueError('failed demonstration acquisition: '+family)
        key=memory.remember(private,result['program'],lib,'V3-development/'+family)
        keys[family]=key;fit.append({'family':family,'result':result})
    memory=ArcMemory.restore(json.loads(json.dumps(memory.state())),lib)
    return memory,fit,keys


def fit_policy(memory,seeds,relational=True,journal=None):
    policy=ArcPolicy();fit=[]
    for episode,seed in enumerate(seeds):
        family=('rotate','paint','stamp','compose')[episode%4]
        result=solve(task(family,seed),memory=memory,policy=policy,learn=True,
                     session='fit',episode=episode,relational=relational,journal=journal,**CONFIG)
        fit.append({'family':family,'seed':seed,'metrics':result['metrics']})
    return policy,fit


def deterministic(value):
    if isinstance(value,dict):return {k:deterministic(v) for k,v in value.items() if k not in ('cpu_seconds',)}
    if isinstance(value,(list,tuple)):return [deterministic(v) for v in value]
    return value


def run(root,phase):
    p=integrity(root);journal=None
    if phase=='primary':
        from echo_arc.observe import Journal
        journal=Journal(ROOT/'lab/observability'/root.name/'journal.jsonl')
    memory,fit,keys=acquire(journal)
    policies={};policy_fits={}
    for label,relational in (('old',False),('new',True)):
        policies[label],policy_fits[label]=fit_policy(memory,p['fit_seeds'],relational,journal)
    # Genuine JSON round trip before frozen evaluation.
    policies={k:ArcPolicy.restore(json.loads(json.dumps(v.state()))) for k,v in policies.items()}
    state_before={k:sha(v.state()) for k,v in policies.items()}
    rows=[]
    for seed in p['confirmation_seeds']:
        for family in FAMILIES:
            private=task(family,seed)
            for arm,settings in ARMS.items():
                options=dict(settings);adaptive=options.pop('adaptive',False)
                use_memory=not options.pop('memory_off',False)
                t=time.process_time()
                result=solve(private,memory=memory if use_memory else None,
                             policy=policies['old' if arm.startswith('old') else 'new'] if adaptive else None,
                             journal=journal,**{**CONFIG,**options})
                row={'seed':seed,'family':family,'arm':arm,'correct':correct(result,private),
                     'result':result,'cpu_seconds':time.process_time()-t}
                rows.append(row)
            save(root/'status.json',{'stage':phase.upper(),'completed':len(rows),
                 'total':len(FAMILIES)*len(ARMS)*len(p['confirmation_seeds'])})
    if any(sha(v.state())!=state_before[k] for k,v in policies.items()):raise RuntimeError('evaluation changed policy')
    withdrawals=[]
    for seed in p['confirmation_seeds']:
        for name,removed in (('intact',[]),('formative',[keys['compose']]),('control',[keys['paint']])):
            result=solve(task('compose',seed),memory=memory.ablate(removed),**CONFIG)
            withdrawals.append({'seed':seed,'arm':name,'correct':correct(result,task('compose',seed)),
                                'work':result['metrics']['work']})
    consistency=[]
    for seed in p['confirmation_seeds']:
        for family,private in (('ambiguous',ambiguous(seed)),('control',task('rotate',seed))):
            for enabled in (False,True):
                result=solve(private,consistency=enabled,verification_window=32)
                consistency.append({'seed':seed,'family':family,'enabled':enabled,
                      'correct':correct(result,private),'committed':result['predictions'] is not None,
                      'work':result['metrics']['work'],'groups':result['metrics']['prediction_groups']})
    totals={}
    for fam in (*FAMILIES,'all'):
        totals[fam]={}
        for arm in ARMS:
            rr=[r for r in rows if r['arm']==arm and (fam=='all' or r['family']==fam)]
            totals[fam][arm]={'solved':sum(r['correct'] for r in rr),'tasks':len(rr),
               'work':sum(r['result']['metrics']['work'] for r in rr),'cpu_seconds':sum(r['cpu_seconds'] for r in rr)}
    def losses(a,b):
        index={(r['seed'],r['family'],r['arm']):r for r in rows}
        return [(s,f) for s in p['confirmation_seeds'] for f in FAMILIES if index[s,f,b]['correct'] and not index[s,f,a]['correct']]
    wt={a:sum(r['work'] for r in withdrawals if r['arm']==a) for a in ('intact','formative','control')}
    cons={}
    for fam in ('ambiguous','control'):
        cons[fam]={}
        for enabled in (False,True):
            rr=[r for r in consistency if r['family']==fam and r['enabled']==enabled]
            cons[fam][str(enabled)]={'correct':sum(r['correct'] for r in rr),
                  'committed':sum(r['committed'] for r in rr),'wrong_commitments':sum(r['committed'] and not r['correct'] for r in rr),'tasks':len(rr)}
    new,fixed,old=totals['all']['new_policy'],totals['all']['new_fixed'],totals['all']['old_fixed']
    reduction=1-new['work']/fixed['work']
    # Primary scheduling population declared before confirmation: equal cheap
    # direct transformations and reusable compositions. Report wider suite too.
    schedule={a:sum(totals[f][a]['work'] for f in ('rotate','compose'))
              for a in ('new_policy','new_fixed','search_first')}
    schedule_reduction=1-schedule['new_policy']/min(schedule['new_fixed'],schedule['search_first'])
    gates={
       'REL':new['solved']>old['solved'] and not losses('new_policy','old_fixed'),
       'MEM':not losses('new_policy','new_fixed') and not losses('new_policy','search_first')
             and schedule_reduction>=.10 and wt['formative']>wt['control']
             and all(r['correct'] for r in withdrawals),
       'SYN':totals['compose']['no_memory']['solved']>totals['compose']['no_refinement']['solved']
             and not losses('no_memory','no_refinement'),
       'VIEW':totals['all']['views']['solved']>totals['all']['no_memory']['solved'] and not losses('views','no_memory'),
       'CONS':cons['ambiguous']['True']['wrong_commitments']==0 and cons['ambiguous']['False']['wrong_commitments']>0
              and cons['control']['True']['correct']==cons['control']['False']['correct']==len(p['confirmation_seeds'])}
    summary={'gates':gates,'totals':totals,'adaptive_work_reduction':reduction,'withdrawal_work':wt,
             'schedule_work':schedule,'schedule_work_reduction':schedule_reduction,
             'consistency':cons,'losses':{a:losses(a,b) for a,b in (('new_policy','new_fixed'),('views','no_memory'))},
             'policy_q':{k:v.q for k,v in policies.items()},'matured':{k:v.matured for k,v in policies.items()},
             'pending':{k:len(v.pending_returns) for k,v in policies.items()},'S6_green':False,'release_ready':False}
    save(root/phase/'rows.json',rows);save(root/phase/'withdrawals.json',withdrawals)
    save(root/phase/'consistency.json',consistency);save(root/phase/'summary.json',summary)
    save(root/phase/'acquisition.json',fit);save(root/phase/'policy-fit.json',policy_fits)
    candidate={'schema':'echo45-relational-v3','memory':memory.state(),
        'policy':policies['new'].state(),'sources':p['sources'],'next_episode':256,
        'release_ready':False,'S6_green':False}
    save(root/phase/'candidate.json',{'payload':candidate,'sha256':sha(candidate)})
    if phase=='audit':
        checked=[]
        for file in ('rows.json','withdrawals.json','consistency.json','summary.json','acquisition.json','policy-fit.json','candidate.json'):
            original=json.loads((root/'primary'/file).read_text());repeat=json.loads((root/'audit'/file).read_text())
            if deterministic(original)!=deterministic(repeat):raise RuntimeError('replay differs: '+file)
            checked.append(file)
        save(root/'audit.json',{'valid':True,'checked':checked,'full_solves':len(rows)+len(withdrawals)+len(consistency),
                              'fit_episodes':2*len(p['fit_seeds']),'scope':'new process, same implementation'})
    if journal:journal.close()
    integrity(root)
    save(root/'status.json',{'stage':'DONE','phase':phase,'gates':gates})
    print(json.dumps({'gates':gates,'work_reduction':reduction,'totals':totals['all']}),flush=True)


def develop():
    from echo_arc.observe import Journal
    import uuid
    journal=Journal(ROOT/'lab/observability'/('relational-development-'+uuid.uuid4().hex[:8])/'journal.jsonl')
    memory,fit,keys=acquire(journal)
    policy,rows=fit_policy(memory,range(47100,47356),journal=journal)
    print('POLICY',policy.q,'matured',policy.matured)
    for f in FAMILIES:
        for a,kw in (('fixed',{}),('policy',{'policy':policy}),('nomemory',{'memory':None}),('views',{'memory':None,'views':True})):
            config={'memory':memory,**kw};results=[]
            for s in range(47000,47004):
                private=task(f,s);r=solve(private,journal=journal,**config,**CONFIG)
                results.append((correct(r,private),r['metrics']['work']))
            print(f,a,sum(r[0] for r in results),sum(r[1] for r in results),flush=True)
    journal.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','run','audit','develop'))
    parser.add_argument('--root',type=Path);a=parser.parse_args()
    if a.command=='develop':develop()
    elif a.command=='prepare':prepare(a.root)
    else:run(a.root,'audit' if a.command=='audit' else 'primary')
