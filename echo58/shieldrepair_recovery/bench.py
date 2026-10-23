"""Explicit one-process-per-case continuation. Never executes a complete receipt."""
import argparse
from datetime import datetime,timezone
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from ..shield2.custody import canonical,digest,read,sha,write
from ..shieldrepair.bench import check_sources,context,receipt_hashes,stem,training_barrier,validation_job
from ..shieldrepair.protocol import agenda,key
from .core import compare_prefix,extract_prefix,require,resource_caps,verify_files

PARTIALS=('r1-validation-repair-72000','r1-validation-legacy-72001',
          'r1-validation-slow-72001','r1-validation-repair-72001')


def now():return datetime.now(timezone.utc).isoformat()


def jobs_for_receipts(root):
 root=Path(root);scheduled={stem(root,j).with_suffix('.json').name:j for j in agenda()}
 paths=list((root/'episodes').glob('*.json'))
 require(all(p.name in scheduled for p in paths),'unscheduled original receipt')
 names={p.name for p in paths}
 return [j for j in agenda() if stem(root,j).with_suffix('.json').name in names]


def original_phase_prefix(root):
 root=Path(root);paths=sorted((root/'phases').glob('*.json'))
 expected=('run_start','train_start','train_end','tables_frozen','validation_start')
 require(len(paths)==5 and not (root/'completed.json').exists(),'original must remain visibly interrupted')
 previous='0'*64;last=read(root/'freeze.json')['created_utc']
 for index,(path,name) in enumerate(zip(paths,expected)):
  event=read(path);require(event['index']==index and event['event']==name and event['prev']==previous and event['utc']>=last,'original phase prefix')
  previous=sha(path);last=event['utc']
 require(read(paths[0])['details']=={'freeze_sha':sha(root/'freeze.json'),'agenda_sha':sha(root/'agenda.json')},'original run commitment')
 require(read(paths[2])['details']=={'receipts':receipt_hashes(root,'train')},'original completed training commitment')
 require(read(paths[3])['details']=={'commit_sha':sha(root/'tables-committed.json')},'original tables phase')
 require(read(root/'tables-committed.json')['tables']==training_barrier(root),'original table barrier')
 return {str(p.relative_to(root)):sha(p) for p in paths}


def recovery_sources():
 base=Path(__file__).resolve().parents[2]
 return [*sorted(Path(__file__).parent.glob('*.py')),base/'tests/test_echo58_shieldrepair_recovery.py',
         base/'ECHO-5.8/docs/E-FINAL-INCIDENT-20261023.md']


def prepare(root):
 root=Path(root).resolve();check_sources(root);original_phase_prefix(root)
 require(not list(root.glob('*failure.json')),'existing original failure marker')
 complete=jobs_for_receipts(root);require(len(complete)==232,'exactly232 original complete receipts')
 require(sum(j['phase']=='train' for j in complete)==80,'all80 original learning episodes present')
 known={key(j) for j in complete};pending=[j for j in agenda() if key(j) not in known]
 require(len(pending)==148 and all(j['phase']=='validation' for j in pending),'exact pending148 validation agenda')
 immutable={}
 for job in complete:
  path=stem(root,job).with_suffix('.json');receipt=read(path)
  require(receipt['status']=='complete' and receipt['identity']['context']==context(root,job),'complete original identity')
  trace=stem(root,job).with_suffix('.jsonl.gz')
  require(receipt['trace']==trace.name and sha(trace)==receipt['trace_sha'],'complete original trace hash')
  for p in (path,trace):immutable[str(p.relative_to(root))]=sha(p)
 for p in (root/'freeze.json',root/'agenda.json',root/'started.json',root/'tables-committed.json',
           root/'tables/r0.json',root/'tables/r1.json',*sorted((root/'phases').glob('*.json'))):immutable[str(p.relative_to(root))]=sha(p)
 orphan_paths=[p for p in (root/'episodes').glob('*.jsonl.gz') if not p.with_suffix('').with_suffix('.json').exists()]
 require({p.name for p in orphan_paths}=={name+'.jsonl.gz' for name in PARTIALS},'exact four interrupted traces')
 incident=root/'incident';incident.mkdir(exist_ok=False)
 (incident/'original').mkdir();(incident/'prefix').mkdir();partials={}
 # Archive copies and extracted prefixes first; original paths stay untouched until manifest fsync.
 for path in sorted(orphan_paths):
  parsed=extract_prefix(path);rows=parsed.pop('rows');target=incident/'original'/path.name
  shutil.copy2(path,target)
  with target.open('rb') as stream:os.fsync(stream.fileno())
  require(sha(path)==sha(target),'archived interrupted trace byte identity')
  prefix=incident/'prefix'/(path.name+'.jsonl')
  with prefix.open('x') as stream:
   for row in rows:stream.write(canonical(row)+'\n')
   stream.flush();os.fsync(stream.fileno())
  partials[path.name]={'original_path':str(path.relative_to(root)),'archive_path':str(target.relative_to(incident)),
    'sha':sha(path),'bytes':path.stat().st_size,'prefix_path':str(prefix.relative_to(incident)),
    'prefix_sha':sha(prefix),**parsed,'gzip_error':'missing gzip end-of-stream trailer' if not parsed['gzip_complete'] else None}
 for name in ('live.jsonl','run.log'):
  source=root/name
  if source.exists():shutil.copy2(source,incident/'original'/name)
 manifest={'utc':now(),'original_protocol':'interrupted_global_oom','freeze_sha':sha(root/'freeze.json'),
   'complete_receipts':232,'complete_learning':80,'complete_validation':152,'remaining':148,
   'immutable_files':immutable,'partials':partials,'pending_agenda_sha':digest(pending),
   'scope':'only four interrupted jobs without receipts may be reconstructed; no completed episode rerun'}
 write(incident/'manifest.json',manifest);write(incident/'agenda.json',pending)
 archives={};sources={}
 for index,path in enumerate(recovery_sources()):
  target=incident/'frozen'/f'{index:03d}-{path.name}';target.parent.mkdir(exist_ok=True);shutil.copy2(path,target)
  sources[str(path.resolve())]=sha(path);archives[str(target.relative_to(incident))]=sha(target)
 write(incident/'freeze.json',{'utc':now(),'sources':sources,'archives':archives,
  'original_freeze_sha':sha(root/'freeze.json'),'incident_manifest_sha':sha(incident/'manifest.json'),
  'agenda_sha':sha(incident/'agenda.json')})
 # Manifest exists and its archive hashes have been verified before any original route is released.
 for path in orphan_paths:
  require(sha(path)==partials[path.name]['sha'],'partial changed during preservation');path.unlink()
 write(incident/'archive-complete.json',{'utc':now(),'manifest_sha':sha(incident/'manifest.json'),'archived':4})
 return {'incident':str(incident),'complete_preserved':232,'pending':148,
         'valid_transitions':sum(p['valid_transitions'] for p in partials.values())}


def check_recovery(root):
 root=Path(root).resolve();incident=root/'incident';check_sources(root);original_phase_prefix(root)
 freeze=read(incident/'freeze.json');manifest=read(incident/'manifest.json')
 require(sha(root/'freeze.json')==freeze['original_freeze_sha']==manifest['freeze_sha'],'original freeze binding')
 require(sha(incident/'manifest.json')==freeze['incident_manifest_sha'],'incident manifest binding')
 require(sha(incident/'agenda.json')==freeze['agenda_sha'] and digest(read(incident/'agenda.json'))==manifest['pending_agenda_sha'],'recovery agenda binding')
 verify_files(root,manifest['immutable_files'])
 for path,h in freeze['sources'].items():require(sha(path)==h,'recovery source '+path)
 verify_files(incident,freeze['archives'])
 for name,p in manifest['partials'].items():
  require(sha(incident/p['archive_path'])==p['sha'] and sha(incident/p['prefix_path'])==p['prefix_sha'],'preserved partial '+name)
 require(read(incident/'archive-complete.json')['manifest_sha']==sha(incident/'manifest.json'),'archival completion binding')
 return manifest


def event(root,name,**details):
 incident=Path(root)/'incident';paths=sorted((incident/'events').glob('*.json'))
 previous=sha(paths[-1]) if paths else '0'*64
 path=incident/'events'/f'{len(paths):04d}-{name}.json'
 write(path,{'utc':now(),'index':len(paths),'event':name,'prev':previous,'details':details});return path


def child(root,command,job=None):
 incident=Path(root)/'incident';name=command if job is None else f"r{job['replica']}-{job['arm']}-{job['seed']}"
 path=incident/'logs'/(name+'.log');path.parent.mkdir(exist_ok=True)
 args=[sys.executable,'-m','echoai.echo58.shieldrepair_recovery.bench',command,str(root)]
 if job is not None:args+=['--job',canonical(job)]
 with path.open('x') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)


def verify_prefix(root,job):
 incident=Path(root)/'incident';name=stem(root,job).with_suffix('.jsonl.gz').name
 partial=read(incident/'manifest.json')['partials'].get(name)
 if partial is None:return None
 original=[json.loads(line) for line in (incident/partial['prefix_path']).read_text().splitlines()]
 reconstructed=extract_prefix(stem(root,job).with_suffix('.jsonl.gz'))
 require(reconstructed['gzip_complete'],'reconstructed trace incomplete')
 return compare_prefix(original,reconstructed['rows'])


def verify_complete(root):
 root=Path(root).resolve();incident=root/'incident';check_recovery(root)
 require(not (incident/'failure.json').exists(),'recorded recovery failure')
 done=read(incident/'completed.json')
 require(done['total_episodes']==380 and done['new_episodes']==148 and done['original_contract_full_green'] is False,'explicit interrupted protocol and complete recovered sample')
 require(done['audit_sha']==sha(incident/'audit.json'),'final audit binding')
 paths=sorted((incident/'events').glob('*.json'));require(len(paths)==152,'final recovery event count')
 previous='0'*64
 for index,path in enumerate(paths):
  entry=read(path);require(entry['index']==index and entry['prev']==previous,'final event chain');previous=sha(path)
 require(read(paths[-1])['event']=='recorded_audit_complete' and read(paths[-1])['details']=={'audit_sha':sha(incident/'audit.json')},'final audit phase')
 jobs=jobs_for_receipts(root);require(len(jobs)==380,'all380 complete receipts present')
 for job in jobs:
  receipt=read(stem(root,job).with_suffix('.json'));require(receipt['status']=='complete' and receipt['trace_sha']==sha(stem(root,job).with_suffix('.jsonl.gz')),'final receipt trace')
 for path,job in zip(paths[2:150],read(incident/'agenda.json')):
  entry=read(path);require(entry['details']['job']==job and entry['details']['receipt_sha']==sha(stem(root,job).with_suffix('.json')),'recovered receipt commitment')
 return {'status':'pass','episodes':380,'original_complete_unchanged':232,'original_protocol':'interrupted_oom','original_contract_full_green':False}


def run(root):
 root=Path(root).resolve();incident=root/'incident'
 require(not any((incident/name).exists() for name in ('started.json','completed.json','failure.json')),'recovery already attempted; no automatic retry')
 active=None
 try:
  caps=resource_caps();check_recovery(root)
  for job in read(incident/'agenda.json'):
   require(not stem(root,job).with_suffix('.json').exists() and not stem(root,job).with_suffix('.jsonl.gz').exists(),'pending job already has output')
  write(incident/'started.json',{'utc':now(),'freeze_sha':sha(incident/'freeze.json'),'caps':caps,'original_protocol':'interrupted'})
  event(root,'recovery_start',freeze_sha=sha(incident/'freeze.json'),resource_caps=caps)
  child(root,'verify-existing');event(root,'original_232_verified',audit_sha=sha(incident/'existing-audit.json'))
  from ..shieldrepair.boundary import live
  live(root,{'event':'infrastructure_recovery_start','original_protocol':'interrupted_oom','remaining':148,'workers':1})
  for job in read(incident/'agenda.json'):
   active=job;check_recovery(root)
   require(not stem(root,job).with_suffix('.json').exists() and not stem(root,job).with_suffix('.jsonl.gz').exists(),'never repeat a complete or attempted recovered case')
   child(root,'one',job);receipt=read(stem(root,job).with_suffix('.json'))
   require(receipt['status']=='complete','recovery episode instrumental failure')
   comparison=verify_prefix(root,job)
   event(root,'episode_complete',job=job,receipt_sha=sha(stem(root,job).with_suffix('.json')),prefix=comparison)
   progress={'event':'recovery_episode_complete','job':job,'cost':receipt['cost'],'goals':receipt['goals'],'prefix':comparison}
   live(root,progress);print(canonical(progress),flush=True)
  check_recovery(root);write(incident/'simulations-complete.json',{'utc':now(),'new_complete':148,'total':380})
  event(root,'all_simulations_complete',episodes=380);child(root,'audit')
  event(root,'recorded_audit_complete',audit_sha=sha(incident/'audit.json'))
  write(incident/'completed.json',{'utc':now(),'total_episodes':380,'new_episodes':148,'audit_sha':sha(incident/'audit.json'),
   'original_protocol':'interrupted_oom','original_contract_full_green':False,
   'resources':resource_caps()})
 except BaseException:
  write(incident/'failure.json',{'utc':now(),'active':active,'traceback':traceback.format_exc(),'green_blocked':True});raise


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','run','one','verify-existing','audit','verify-complete'))
 parser.add_argument('root');parser.add_argument('--job');args=parser.parse_args();root=Path(args.root).resolve()
 if args.command=='prepare':print(canonical(prepare(root)))
 elif args.command=='run':run(root)
 elif args.command=='verify-complete':print(canonical(verify_complete(root)))
 elif args.command=='one':
  resource_caps();check_recovery(root);job=json.loads(args.job)
  require(job in read(root/'incident/agenda.json'),'scheduled recovery job')
  require(not stem(root,job).with_suffix('.json').exists() and not stem(root,job).with_suffix('.jsonl.gz').exists(),'one never overwrites an existing episode')
  result=validation_job(root,job,read(root/'tables'/f"r{job['replica']}.json"));require(result['status']=='complete','case incomplete')
 else:
  resource_caps()
  from .audit import audit
  print(canonical(audit(root,existing_only=args.command=='verify-existing')))
