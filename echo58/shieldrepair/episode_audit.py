"""Recompute controller and actuator decisions, learning and totals from recorded states."""
import argparse
import gzip
from pathlib import Path
from .core import Controller,ARMS,export_table
from ..shield2.custody import read,digest,sha,write


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
