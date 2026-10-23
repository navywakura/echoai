"""Simulator boundary: original sensing, with a trace for each actual env.step."""
import gzip
import math
import os
from pathlib import Path
import traceback
import numpy as np
from echoai.shield1.run import slices,lidar_ints,move_bin,forward_speed,actuate
from .core import export_table
from .custody import canonical,digest,sha,write


def state(env,obs,sl):
 vf=forward_speed(env,'Car');speed=float(np.hypot(*env.task.agent.vel[:2]))
 if not all(math.isfinite(v) for v in (vf,speed)):raise ValueError('nonfinite velocity')
 return {'lid':lidar_ints(obs,sl),'move':move_bin(env,'Car'),'vf':vf,'speed':speed,
         'vf_mm':int(round(vf*1000)),'speed_mm':int(round(speed*1000))}


def action(d,vf):
 if d['brake'] or d['throttle_milli'] is None:return actuate('Car',d['heading'],d['brake'],vf)
 rel=(d['heading']-12)%16;a=rel if rel<8 else rel-16
 k=float(np.clip(a*2*np.pi/16*1.5,-1,1));v=d['throttle_milli']/1000
 return np.clip(np.array([v+k,v-k]),-1,1)


def play(env,controller,seed,stem,context=None):
 stem=Path(stem);trace=stem.with_suffix('.jsonl.gz');receipt=stem.with_suffix('.json')
 if trace.exists() or receipt.exists():raise FileExistsError(stem)
 stem.parent.mkdir(parents=True,exist_ok=True)
 initial=export_table(controller.gate);total=goals=steps=0;ret=raw=0.;previous='0'*64
 identity={'seed':seed,'arm':controller.arm,'learning':controller.gate.learning,
           'initial_table_sha':digest(initial),'context':context or {'run':'synthetic','phase':'synthetic'}}
 counts=[0,0,0];status='failed';error=None;term=trunc=False
 with gzip.open(trace,'xb') as f:
  header={'prev':previous,'data':{'kind':'episode_header','identity':identity}}
  previous=digest(header);header['hash']=previous
  f.write((canonical(header)+'\n').encode());f.flush();os.fsync(f.fileobj.fileno())
  try:
   obs,_=env.reset(seed=seed);sl=slices(env);before=state(env,obs,sl)
   for t in range(1000):
    d=controller.decide(before['lid'],before['move'],before['speed_mm'],before['vf_mm'],total)
    act=action(d,before['vf']);obs,r,c,term,trunc,info=env.step(act)
    r=float(r);c=float(c)
    if not math.isfinite(r) or not math.isfinite(c):raise ValueError('nonfinite reward/cost')
    after=state(env,obs,sl);binary=int(c>0);total+=binary;raw+=c;ret+=r
    goal=int(bool(info.get('goal_met',False)));goals+=goal;steps=t+1;counts[d['verdict']]+=1
    components={k:float(v) for k,v in info.items() if k.startswith('cost_')}
    row={'step':t,'before':before,'decision':d,'action':act.tolist(),'after':after,
         'reward':r,'raw_cost':c,'cost':binary,'cumulative_cost':total,'goal':goal,
         'term':bool(term),'trunc':bool(trunc),'cost_components':components}
    controller.observe(after['lid'],binary)
    payload={'prev':previous,'data':row};previous=digest(payload);payload['hash']=previous
    f.write((canonical(payload)+'\n').encode());before=after
    if steps%200==0 or term or trunc:
     f.flush();os.fsync(f.fileobj.fileno())
     print(canonical({'seed':seed,'arm':controller.arm,'step':steps,'cost':total,'goals':goals,
                      'decision':d}),flush=True)
    if term or trunc:break
   status='complete'
  except Exception:
   error=traceback.format_exc()
 result={'identity':identity,'seed':seed,'arm':controller.arm,'learning':controller.gate.learning,'status':status,
  'error':error,'steps':steps,'cost':total,'raw_cost':raw,'return':ret,'goals':goals,
  'verdicts':counts,'term':bool(term),'trunc':bool(trunc),'initial_table':initial,
  'final_table':export_table(controller.gate),'trace':trace.name,'trace_sha':sha(trace),'last_hash':previous}
 write(receipt,result);return result
