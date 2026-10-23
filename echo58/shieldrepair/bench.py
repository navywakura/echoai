"""Two fresh learning lineages; a global table barrier before paired validation."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import importlib.metadata as metadata
from pathlib import Path
import platform
import shutil
import traceback
from .core import Controller,export_table
from ..shield2.custody import read,write,sha,digest,canonical
from ..shield2.bench import event
from .protocol import REPLICAS,agenda,key,require

TASK='SafetyCarGoal2-v0'


def now():return datetime.now(timezone.utc).isoformat()


def stem(root,job):
 return Path(root)/'episodes'/f"r{job['replica']}-{job['phase']}-{job['arm']}-{job['seed']}"


def context(root,job):
 root=Path(root).resolve()
 return {'run':str(root),'phase':job['phase'],'replica':job['replica'],
         'freeze_sha':sha(root/'freeze.json'),'agenda_sha':sha(root/'agenda.json')}


def source_paths():
 from ..shieldconfirm.bench import source_paths as inherited_sources
 base=Path(__file__).resolve().parents[2]
 return [*inherited_sources(),*sorted((base/'echo58/shieldrepair').glob('*.py')),
  base/'tests/test_echo58_shieldrepair.py',base/'tests/test_echo58_shieldrepair_boundary.py',
  base/'ECHO-5.8/docs/E-FINAL-DESIGN-20261023.md',base/'ECHO-5.8/docs/E-FINAL-PLAN-20261023.md',
  base/'lab/echo58/shieldrepair/final-20261023-r1/prior-inspection.json']


def prepare(root):
 root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
 require(not (root/'freeze.json').exists() and not (root/'episodes').exists(),'prepare cannot overwrite frozen/started run')
 require({p.name for p in root.iterdir()}<={'prior-inspection.json','live.jsonl'},'only prior inspection permitted before prepare')
 try:
  sources={};archives={}
  for index,path in enumerate(source_paths()):
   sources[str(path)]=sha(path);target=root/'frozen'/f'{index:03d}-{path.name}'
   target.parent.mkdir(exist_ok=True);shutil.copy2(path,target);archives[str(target.relative_to(root))]=sha(target)
  versions={p:metadata.version(p) for p in ('safety-gymnasium','mujoco','numpy','gymnasium')}
  dependencies={};dist=metadata.distribution('safety-gymnasium')
  for item in dist.files:
   path=Path(dist.locate_file(item)).resolve()
   if path.is_file() and '__pycache__' not in str(path) and path.suffix!='.pyc':dependencies[str(path)]=sha(path)
  write(root/'freeze.json',{'sources':sources,'archives':archives,'dependencies':dependencies,'versions':versions,
   'python':platform.python_version(),'created_utc':now(),'task':TASK,'agenda_sha':digest(agenda())})
  write(root/'agenda.json',agenda())
 except BaseException:
  write(root/'failure.json',{'active':{'phase':'prepare'},'traceback':traceback.format_exc(),'utc':now()});raise
 return root


def check_sources(root):
 root=Path(root);f=read(root/'freeze.json')
 require(f['python']==platform.python_version(),'interpreter version')
 require(f['versions']=={p:metadata.version(p) for p in f['versions']},'package versions')
 require(f['task']==TASK and f['agenda_sha']==digest(agenda()) and read(root/'agenda.json')==agenda(),'fixed agenda')
 for path,h in {**f['sources'],**f['dependencies']}.items():require(sha(path)==h,'source/dependency '+path)
 for path,h in f['archives'].items():require(sha(root/path)==h,'archived source '+path)


def train_replica(root,replica):
 from echoai.shield1.run import make,new_gate
 from .boundary import play
 env=None
 try:
  env=make(TASK);controller=Controller('legacy',export_table(new_gate(env,'ECHO-L')),learning=True)
  for job in agenda():
   if job['phase']!='train' or job['replica']!=replica:continue
   r=play(env,controller,job['seed'],stem(root,job),context(root,job))
   from .boundary import live
   live(root,{'event':'training_episode_complete','job':job,'cost':r['cost'],'goals':r['goals']})
   require(r['status']=='complete','training step failure: '+canonical(job))
  table=export_table(controller.gate)
 finally:
  if env is not None:env.close()
 write(Path(root)/'tables'/f'r{replica}.json',table)
 return {'replica':replica,'table_sha':digest(table)}


def validation_job(root,job,table):
 from echoai.shield1.run import make
 from .boundary import play
 env=None
 try:
  env=make(TASK)
  return play(env,Controller(job['arm'],table),job['seed'],stem(root,job),context(root,job))
 finally:
  if env is not None:env.close()


def receipt_hashes(root,phase):
 return {stem(root,j).with_suffix('.json').name:sha(stem(root,j).with_suffix('.json')) for j in agenda() if j['phase']==phase}


def training_barrier(root):
 """Both complete lineages and disk tables are mandatory before validation."""
 root=Path(root);commits={}
 for rep in REPLICAS:
  table=None
  for job in agenda():
   if job['phase']!='train' or job['replica']!=rep:continue
   r=read(stem(root,job).with_suffix('.json'))
   require(r['status']=='complete' and r['learning'] is True,'complete training required')
   require(r['seed']==job['seed'] and r['arm']=='legacy' and r['identity']['context']==context(root,job),'training identity')
   if table is None:
    require(all(v==0 for k in ('n','k') for values in r['initial_table'][k].values() for v in values),'fresh independent table')
   else:require(r['initial_table']==table,'training lineage')
   table=r['final_table']
  path=root/'tables'/f'r{rep}.json';require(read(path)==table,'persisted table lineage')
  commits[str(rep)]={'file':str(path.relative_to(root)),'sha':sha(path),'table_sha':digest(table)}
 return commits


def verify_lifecycle(root):
 root=Path(root)
 require(not (root/'failure.json').exists() and not list(root.rglob('*.failure.json')),'recorded instrument failure')
 require((root/'started.json').is_file() and (root/'completed.json').is_file(),'run incomplete')
 expected=('run_start','train_start','train_end','tables_frozen','validation_start','validation_end','run_end')
 paths=sorted((root/'phases').glob('*.json'));require(len(paths)==len(expected),'missing phase commitments')
 previous='0'*64;last=read(root/'freeze.json')['created_utc']
 for index,(path,name) in enumerate(zip(paths,expected)):
  e=read(path);require(e['index']==index and e['event']==name and e['prev']==previous and e['utc']>=last,'phase ordering')
  if name=='run_start':require(e['details']=={'freeze_sha':sha(root/'freeze.json'),'agenda_sha':sha(root/'agenda.json')},'run commitment')
  if name in ('train_end','validation_end'):require(e['details']=={'receipts':receipt_hashes(root,name[:-4])},'phase receipt commitment')
  if name=='tables_frozen':require(e['details']=={'commit_sha':sha(root/'tables-committed.json')},'table phase commitment')
  previous=sha(path);last=e['utc']
 start=read(paths[0]);end=read(paths[-1]);done=read(root/'completed.json')
 require(read(root/'started.json')=={'utc':start['utc'],'phase_sha':sha(paths[0])},'start marker')
 require(end['details']=={'episodes':380} and done=={'utc':last,'episodes':380,'phase_sha':previous},'completion marker')
 commits=read(root/'tables-committed.json')
 require(read(paths[2])['utc']<=commits['utc']<=read(paths[3])['utc'],'table commitment chronology')
 require(commits['tables']==training_barrier(root),'both frozen table commitments')
 expected_names={stem(root,j).with_suffix('.json').name for j in agenda()}
 require({p.name for p in (root/'episodes').glob('*.json')}==expected_names,'exact episode set')
 expected_traces={stem(root,j).with_suffix('.jsonl.gz').name for j in agenda()}
 require({p.name for p in (root/'episodes').glob('*.jsonl.gz')}==expected_traces,'exact trace set')
 for job in agenda():
  receipt=read(stem(root,job).with_suffix('.json'))
  require(receipt['trace']==stem(root,job).with_suffix('.jsonl.gz').name,'scheduled trace binding')
 return True


def run(root):
 root=Path(root).resolve()
 if ((root/'started.json').exists() or (root/'completed.json').exists()
     or (root/'failure.json').exists() or list((root/'phases').glob('*.json'))):
  raise FileExistsError('already attempted; preserve evidence, no automatic retry')
 active={'phase':'preflight','job':None}
 try:
  check_sources(root)
  p=event(root,'run_start',freeze_sha=sha(root/'freeze.json'),agenda_sha=sha(root/'agenda.json'))
  write(root/'started.json',{'utc':read(p)['utc'],'phase_sha':sha(p)})
  active['phase']='train'
  _execute(root,active)
 except BaseException:
  write(root/'failure.json',{'active':active,'traceback':traceback.format_exc(),'utc':now()});raise


def _execute(root,active):
 event(root,'train_start');failures=[]
 with ProcessPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(train_replica,str(root),rep):rep for rep in REPLICAS}
  for future in as_completed(futures):
   rep=futures[future];active['job']={'replica':rep}
   try:print(canonical({'training_complete':future.result()}),flush=True)
   except BaseException:
    write(root/f'train-r{rep}.failure.json',{'replica':rep,'traceback':traceback.format_exc(),'utc':now()});failures.append(rep)
 if failures:raise RuntimeError('training failures: all validation blocked')
 commits=training_barrier(root);event(root,'train_end',receipts=receipt_hashes(root,'train'))
 write(root/'tables-committed.json',{'utc':now(),'tables':commits})
 event(root,'tables_frozen',commit_sha=sha(root/'tables-committed.json'))
 active.update(phase='validation',job=None);check_sources(root);event(root,'validation_start')
 tables={rep:read(root/'tables'/f'r{rep}.json') for rep in REPLICAS};failures=[]
 with ProcessPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(validation_job,str(root),j,tables[j['replica']]):j for j in agenda() if j['phase']=='validation'}
  for future in as_completed(futures):
   job=futures[future];active['job']=job
   try:
    result=future.result();require(result['status']=='complete','episode failure')
    progress={'event':'validation_episode_complete','job':job,'cost':result['cost'],'goals':result['goals']}
    from .boundary import live
    live(root,progress);print(canonical(progress),flush=True)
   except BaseException:
    write(stem(root,job).with_suffix('.failure.json'),{'job':job,'traceback':traceback.format_exc(),'utc':now()});failures.append(job)
 if failures:raise RuntimeError('validation failures: green blocked')
 event(root,'validation_end',receipts=receipt_hashes(root,'validation'))
 check_sources(root);p=event(root,'run_end',episodes=380)
 write(root/'completed.json',{'utc':read(p)['utc'],'episodes':380,'phase_sha':sha(p)})

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=('prepare','run'));parser.add_argument('root');a=parser.parse_args()
 print(prepare(a.root)) if a.command=='prepare' else run(a.root)
