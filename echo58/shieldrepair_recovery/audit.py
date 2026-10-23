"""Recorded-state audit of unchanged original data plus explicit recovered jobs."""
import gzip
import json
from pathlib import Path
from ..shield2.audit import summary
from ..shield2.custody import digest,read,sha,write
from ..shieldrepair.episode_audit import audit_episode
from ..shieldrepair.bench import context,stem
from ..shieldrepair.protocol import agenda,assess,key
from .bench import check_recovery,jobs_for_receipts,verify_prefix
from .core import require


def summary_with_repair(rows):
 result=summary(rows);repair=[{**r,'arm':'slow'} for r in rows if r['arm']=='repair']
 if repair:result['repair']=summary(repair)['slow']
 return result


def audit(root,existing_only=False):
 root=Path(root).resolve();incident=root/'incident';manifest=check_recovery(root)
 require(not (incident/'failure.json').exists(),'recovery instrumental failure recorded')
 if existing_only:
  jobs=jobs_for_receipts(root);require(len(jobs)==232,'before recovery exactly232 old receipts')
  require({stem(root,j).with_suffix('.json').name for j in jobs}=={Path(p).name for p in manifest['immutable_files'] if p.startswith('episodes/') and p.endswith('.json')},'exact preserved receipt set')
 else:
  jobs=agenda();require((incident/'simulations-complete.json').exists(),'simulations not complete')
  require(read(incident/'simulations-complete.json')['total']==380,'expected total380')
  require({p.name for p in (root/'episodes').glob('*.json')}=={stem(root,j).with_suffix('.json').name for j in jobs},'exact380 receipt names')
  require({p.name for p in (root/'episodes').glob('*.jsonl.gz')}=={stem(root,j).with_suffix('.jsonl.gz').name for j in jobs},'exact380 trace names')
 tables={};training=[];validation=[]
 for job in jobs:
  receipt=audit_episode(stem(root,job).with_suffix('.json'));rep=job['replica']
  require(receipt['seed']==job['seed'] and receipt['arm']==job['arm'] and receipt['identity']['context']==context(root,job),'scheduled identity from original freeze')
  if job['phase']=='train':
   require(receipt['learning'] is True,'learning phase')
   if rep in tables:require(receipt['initial_table']==tables[rep],'learning lineage')
   else:require(all(v==0 for name in ('n','k') for values in receipt['initial_table'][name].values() for v in values),'original independent empty table')
   tables[rep]=receipt['final_table'];training.append({**receipt,**job})
  else:
   require(receipt['learning'] is False and receipt['initial_table']==receipt['final_table']==tables[rep],'frozen original table')
   validation.append({**receipt,**job})
 for rep in (0,1):require(read(root/'tables'/f'r{rep}.json')==tables[rep],'persisted original learned table')
 result={'audit':'recorded_trace_consistency_pass','scope':'controller/action/learning replay from recorded states; no physical MuJoCo replay',
  'original_protocol':'interrupted_global_oom','original_contract_full_green':False,
  'episodes':len(jobs),'original_complete_preserved':232,
  'training':{str(rep):summary_with_repair([r for r in training if r['replica']==rep]) for rep in (0,1)},
  'validation':{str(rep):summary_with_repair([r for r in validation if r['replica']==rep]) for rep in (0,1)},
  'table_digests':{str(rep):digest(table) for rep,table in tables.items()}}
 if not existing_only:
  result['numeric_assessment_original_gates']=assess(validation)
  result['recovery']='complete_under_infrastructure_amendment'
  first={}
  for job in jobs:
   if job['phase']!='validation':continue
   with gzip.open(stem(root,job).with_suffix('.jsonl.gz'),'rt') as stream:
    next(stream);state=json.loads(next(stream))['data']['before']
   pair=job['replica'],job['seed']
   if pair in first:require(first[pair]==state,'paired original sensor state equality')
   else:first[pair]=state
  result['pairing']={'triples':len(first),'initial_states':300,'equal':True}
  result['prefixes']={}
  for job in read(incident/'agenda.json'):
   comparison=verify_prefix(root,job)
   if comparison is not None:result['prefixes'][stem(root,job).name]=comparison
  require(len(result['prefixes'])==4,'all four interrupted prefixes compared')
  events=sorted((incident/'events').glob('*.json'));expected=read(incident/'agenda.json')
  require(len(events)==151,'complete recovery event count before final audit marker')
  previous='0'*64;last=read(incident/'started.json')['utc']
  for index,path in enumerate(events):
   event=read(path);require(event['index']==index and event['prev']==previous and event['utc']>=last,'recovery event chain')
   if index==0:require(event['event']=='recovery_start' and event['details']['freeze_sha']==sha(incident/'freeze.json'),'recovery start binding')
   elif index==1:require(event['event']=='original_232_verified' and event['details']['audit_sha']==sha(incident/'existing-audit.json'),'original232 audit commitment')
   elif index<150:
    job=expected[index-2];require(event['event']=='episode_complete' and event['details']['job']==job,'recovery exact sequential agenda')
    require(event['details']['receipt_sha']==sha(stem(root,job).with_suffix('.json')),'recovery receipt phase binding')
    require(event['details']['prefix']==verify_prefix(root,job),'phase prefix result binding')
   else:require(event['event']=='all_simulations_complete' and event['details']=={'episodes':380},'recovery simulations barrier')
   previous=sha(path);last=event['utc']
  result['resource_caps_at_start']=read(incident/'started.json')['caps']
 write(incident/('existing-audit.json' if existing_only else 'audit.json'),result);return result
