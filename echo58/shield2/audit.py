"""Recompute controller and actuator decisions, learning and totals from recorded states."""
import argparse
import gzip
from pathlib import Path
from .core import Controller,ARMS,export_table
from .custody import read,digest,sha,write


def require(ok,msg):
 if not ok:raise ValueError(msg)


def audit_episode(path):
 from .boundary import action
 path=Path(path);r=read(path);require(r['status']=='complete','instrumental failure')
 trace=path.parent/r['trace'];require(sha(trace)==r['trace_sha'],'trace hash')
 c=Controller(r['arm'],r['initial_table'],r['learning']);cost=goals=steps=0;raw=ret=0.;prev='0'*64
 counts=[0,0,0];last=None
 observed={'components':{},'cost_speed_mm_sum':0,'cost_steps':0,'extra_brakes':{'speed':0,'budget':0}}
 with gzip.open(trace,'rt') as f:
  header=__import__('json').loads(next(f));h=header.pop('hash')
  require(header['prev']==prev and digest(header)==h,'header chain');prev=h
  identity={'seed':r['seed'],'arm':r['arm'],'learning':r['learning'],
            'initial_table_sha':digest(r['initial_table']),'context':r['identity']['context']}
  require(header['data']=={'kind':'episode_header','identity':identity} and r['identity']==identity,'episode identity')
  for line in f:
   p=__import__('json').loads(line);h=p.pop('hash');require(p['prev']==prev and digest(p)==h,'chain');prev=h
   row=p['data'];require(row['step']==steps,'step order')
   if last is not None:
    require(not last['term'] and not last['trunc'],'steps after termination')
    require(last['after']==row['before'],'state continuity')
   for s in (row['before'],row['after']):
    require(s['vf_mm']==int(round(1000*s['vf'])) and s['speed_mm']==int(round(1000*s['speed'])),'velocity normalization')
   s=row['before'];d=c.decide(s['lid'],s['move'],s['speed_mm'],s['vf_mm'],cost)
   require(d==row['decision'],'decision');require(action(d,s['vf']).tolist()==row['action'],'actuator')
   require(row['cost']==int(row['raw_cost']>0),'binary cost');cost+=row['cost'];raw+=row['raw_cost'];ret+=row['reward']
   require(row['cumulative_cost']==cost,'cumulative cost');goals+=row['goal'];steps+=1;counts[d['verdict']]+=1
   for channel,value in row['cost_components'].items():
    observed['components'][channel]=observed['components'].get(channel,0)+value
   if row['cost']:
    observed['cost_steps']+=1;observed['cost_speed_mm_sum']+=row['before']['speed_mm']
   observed['extra_brakes']['speed']+=d['speed_brake'];observed['extra_brakes']['budget']+=d['budget_brake']
   c.observe(row['after']['lid'],row['cost']);last=row
 require(steps>0 and (steps==1000 or last['term'] or last['trunc']),'incomplete episode')
 for name,value in [('steps',steps),('cost',cost),('raw_cost',raw),('return',ret),('goals',goals),
                    ('verdicts',counts),('last_hash',prev),('final_table',export_table(c.gate)),
                    ('term',last['term']),('trunc',last['trunc'])]:require(r[name]==value,'aggregate '+name)
 return {**r,'observed':observed}


def summary(rows):
 out={a:{'episodes':len(rr),'steps':sum(x['steps'] for x in rr),'cost':sum(x['cost'] for x in rr),
  'over25':sum(x['cost']>25 for x in rr),'goals':sum(x['goals'] for x in rr),
  'raw_cost':sum(x['raw_cost'] for x in rr),'return':sum(x['return'] for x in rr),
  'max_cost':max((x['cost'] for x in rr),default=0)} for a in ARMS if (rr:=[r for r in rows if r['arm']==a])}
 for a,s in out.items():
  rr=[r for r in rows if r['arm']==a];components={};speed_sum=count=0;brakes={'speed':0,'budget':0}
  for r in rr:
   o=r['observed'];speed_sum+=o['cost_speed_mm_sum'];count+=o['cost_steps']
   for k,v in o['components'].items():components[k]=components.get(k,0)+v
   for k in brakes:brakes[k]+=o['extra_brakes'][k]
  s.update(components=components,cost_step_mean_speed_mm=speed_sum/count if count else None,
   verdicts=[sum(r['verdicts'][i] for r in rr) for i in range(3)],extra_brakes=brakes,
   worst=[{'seed':r['seed'],'cost':r['cost'],'goals':r['goals']} for r in sorted(rr,key=lambda r:(-r['cost'],r['seed']))[:5]])
 return out


def utility(s):
 a,l,b=s['adaptive'],s['legacy'],s['slow']
 tests={'tail_present':l['over25']>0,'fewer_tails':a['over25']<l['over25'],
  'less_cost':a['cost']<l['cost'],'progress':a['goals']>0 and 5*a['goals']>=4*l['goals'],
  'beats_slow':a['cost']<=b['cost'] and a['goals']>=b['goals'] and (a['cost']<b['cost'] or a['goals']>b['goals'])}
 return {'checks':tests,'pass':all(tests.values()),'scope':'development only'}


def audit(root):
 from .bench import agenda,check_sources,verify_lifecycle,context
 root=Path(root);check_sources(root);verify_lifecycle(root);require(read(root/'agenda.json')==agenda(),'agenda')
 receipts=[];table=None;training=[];diagnostics=[]
 for job in agenda():
  p=root/'episodes'/f"{job['phase']}-{job['arm']}-{job['seed']}.json"
  r=audit_episode(p);require(r['seed']==job['seed'] and r['arm']==job['arm'],'identity')
  require(r['learning']==(job['phase']=='train'),'learning phase')
  require(r['identity']['context']==context(root,job),'run/phase commitment')
  if job['phase']=='train':
   if table is not None:require(r['initial_table']==table,'learning continuity')
   else:require(all(v==0 for k in ('n','k') for vals in r['initial_table'][k].values() for v in vals),'fresh table')
   table=r['final_table'];training.append(r)
  else:
   require(r['initial_table']==table and r['final_table']==table,'frozen table')
   if job['phase']=='validation':receipts.append(r)
   else:diagnostics.append(r)
 require(read(root/'learned-table.json')==table,'persisted learned table')
 require(read(root/'table-freeze.json')['sha']==digest(table),'table commitment')
 s=summary(receipts);out={'audit':'recorded_trace_consistency_pass','scope':'controller/action/learning replay from recorded states, not MuJoCo replay',
  'episodes':len(agenda()),'training':summary(training),'diagnostic':summary(diagnostics),'validation':s,'utility':utility(s)}
 write(root/'audit.json',out);return out

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root');args=p.parse_args();print(__import__('json').dumps(audit(args.root),indent=2))
