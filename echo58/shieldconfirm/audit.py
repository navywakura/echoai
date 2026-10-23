"""Recorded-state audit of both learning chains and all paired validations."""
import argparse
import json
from pathlib import Path
from ..shield2.audit import audit_episode,summary
from ..shield2.custody import read,write,digest
from .protocol import REPLICAS,agenda,assess,require
from .bench import check_sources,verify_lifecycle,context,stem


def audit(root):
 root=Path(root).resolve();check_sources(root);verify_lifecycle(root)
 tables={};training=[];validation=[]
 for job in agenda():
  r=audit_episode(stem(root,job).with_suffix('.json'))
  require(r['seed']==job['seed'] and r['arm']==job['arm'] and r['identity']['context']==context(root,job),'scheduled episode identity')
  rep=job['replica']
  if job['phase']=='train':
   require(r['learning'] is True,'training learns')
   if rep in tables:require(r['initial_table']==tables[rep],'learning continuity')
   else:require(all(v==0 for k in ('n','k') for values in r['initial_table'][k].values() for v in values),'independent empty initial state')
   tables[rep]=r['final_table'];training.append({**r,'replica':rep,'phase':'train'})
  else:
   require(r['learning'] is False,'validation frozen')
   require(r['initial_table']==r['final_table']==tables[rep],'matching frozen table')
   validation.append({**r,'replica':rep,'phase':'validation'})
 for rep in REPLICAS:require(read(root/'tables'/f'r{rep}.json')==tables[rep],'persisted learned table')
 result={'audit':'recorded_trace_consistency_pass','scope':'decisions/actions/learning replay from recorded states; no MuJoCo replay',
  'episodes':280,'assessment':assess(validation),
  'training':{str(rep):summary([r for r in training if r['replica']==rep]) for rep in REPLICAS},
  'validation':{str(rep):summary([r for r in validation if r['replica']==rep]) for rep in REPLICAS},
  'table_digests':{str(rep):digest(tables[rep]) for rep in REPLICAS}}
 write(root/'audit.json',result);return result

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('root');a=parser.parse_args()
 result=audit(a.root);print(json.dumps({'audit':result['audit'],'assessment':result['assessment']},indent=2))
