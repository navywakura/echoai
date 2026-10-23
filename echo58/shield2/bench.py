"""Fixed prospective development agenda. No historical seeds, exams or retries."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import importlib.metadata as metadata
from pathlib import Path
import platform
import shutil
import traceback
from .core import ARMS,Controller,export_table
from .custody import read,write,sha,digest,canonical

TASK='SafetyCarGoal2-v0'


def agenda():
 return ([{'phase':'train','arm':'legacy','seed':s} for s in range(31000,31040)] +
         [{'phase':'diagnostic','arm':'legacy','seed':s} for s in range(32000,32010)] +
         [{'phase':'validation','arm':a,'seed':s} for s in range(33000,33050) for a in ARMS])


def source_paths():
 base=Path(__file__).resolve().parents[2]
 return [*sorted((base/'shield1').glob('*.py')),*sorted((base/'echo58/shield2').glob('*.py')),
         base/'tests/test_echo58_shield2.py',base/'ECHO-5.8/docs/SHIELD2-DESIGN.md']


def prepare(root):
 root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False)
 files=source_paths();sources={str(p):sha(p) for p in files}
 archives={}
 for i,p in enumerate(files):
  dest=root/'frozen'/f'{i:03d}-{p.name}';dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest);archives[str(dest.relative_to(root))]=sha(dest)
 versions={p:metadata.version(p) for p in ('safety-gymnasium','mujoco','numpy','gymnasium')}
 # Geometry, task code and XML resources are part of environment provenance.
 dist=metadata.distribution('safety-gymnasium');deps={}
 for rel in dist.files:
  p=Path(dist.locate_file(rel)).resolve()
  if p.is_file() and '__pycache__' not in str(p) and p.suffix!='.pyc':deps[str(p)]=sha(p)
 write(root/'freeze.json',{'sources':sources,'archives':archives,'dependencies':deps,'versions':versions,'python':platform.python_version(),
  'task':TASK,'created_utc':datetime.now(timezone.utc).isoformat(),'agenda_sha':digest(agenda())})
 write(root/'agenda.json',agenda())
 return root


def check_sources(root):
 f=read(Path(root)/'freeze.json')
 for p,h in {**f['sources'],**f['dependencies']}.items():
  if sha(p)!=h:raise ValueError('source/dependency changed: '+p)
 if digest(agenda())!=f['agenda_sha']:raise ValueError('agenda changed')
 for p,h in f['archives'].items():
  if sha(Path(root)/p)!=h:raise ValueError('archive changed')
 if platform.python_version()!=f['python']:raise ValueError('interpreter version changed')
 if any(metadata.version(p)!=v for p,v in f['versions'].items()):raise ValueError('package version changed')


def stem(root,j):return Path(root)/'episodes'/f"{j['phase']}-{j['arm']}-{j['seed']}"


def run_job(root,j,table):
 from echoai.shield1.run import make
 from .boundary import play
 env=make(TASK)
 try:return play(env,Controller(j['arm'],table),j['seed'],stem(root,j),context(root,j))
 finally:env.close()


def context(root,job):
 root=Path(root).resolve()
 return {'run':str(root),'phase':job['phase'],'freeze_sha':sha(root/'freeze.json'),
         'agenda_sha':sha(root/'agenda.json')}


def event(root,name,**details):
 root=Path(root);existing=sorted((root/'phases').glob('*.json'))
 entry={'index':len(existing),'event':name,'utc':datetime.now(timezone.utc).isoformat(),
        'prev':sha(existing[-1]) if existing else '0'*64,'details':details}
 path=root/'phases'/f'{len(existing):02d}-{name}.json';write(path,entry);return path


def receipt_hashes(root,phase):
 return {stem(root,j).with_suffix('.json').name:sha(stem(root,j).with_suffix('.json'))
         for j in agenda() if j['phase']==phase}


def verify_lifecycle(root):
 root=Path(root)
 if list(root.rglob('*.failure.json')) or (root/'failure.json').exists():raise ValueError('recorded instrument failure')
 if not (root/'started.json').is_file() or not (root/'completed.json').is_file():raise ValueError('run incomplete')
 expected=('run_start','train_start','train_end','table_frozen','diagnostic_start','diagnostic_end','validation_start','validation_end','run_end')
 paths=sorted((root/'phases').glob('*.json'));prev='0'*64;last=read(root/'freeze.json')['created_utc']
 if len(paths)!=len(expected):raise ValueError('phase commitments missing')
 for i,(path,name) in enumerate(zip(paths,expected)):
  e=read(path)
  if (e['index']!=i or e['event']!=name or e['prev']!=prev or e['utc']<last):raise ValueError('phase ordering')
  if name.endswith('_end') and name!='run_end':
   if e['details']['receipts']!=receipt_hashes(root,name[:-4]):raise ValueError('phase receipt commitment')
  if name=='run_start' and e['details']!=context(root,{'phase':'run'}):raise ValueError('source/agenda commitment')
  if name=='table_frozen' and e['details']!={'table_sha':digest(read(root/'learned-table.json')),
     'freeze_receipt_sha':sha(root/'table-freeze.json')}:raise ValueError('table freeze commitment')
  prev=sha(path);last=e['utc']
 if read(root/'started.json')['utc']!=read(paths[0])['utc']:raise ValueError('start marker')
 if read(root/'completed.json')!={'episodes':250,'last_phase_sha':prev,'utc':last}:raise ValueError('completion marker')
 return True


def run(root):
 root=Path(root);check_sources(root)
 if (root/'started.json').exists():raise FileExistsError('already started; no automatic resume/retry')
 start=event(root,'run_start',**context(root,{'phase':'run'}));write(root/'started.json',{'utc':read(start)['utc']})
 active={'phase':'train','job':None}
 try:_execute(root,active)
 except BaseException:
  write(root/'failure.json',{'active':active,'traceback':traceback.format_exc(),
                            'utc':datetime.now(timezone.utc).isoformat()})
  raise


def _execute(root,active):
 from echoai.shield1.run import make,new_gate
 from .boundary import play
 event(root,'train_start')
 env=make(TASK)
 try:
  controller=Controller('legacy',export_table(new_gate(env,'ECHO-L')),learning=True)
  for j in agenda()[:40]:
   active['job']=j
   r=play(env,controller,j['seed'],stem(root,j),context(root,j))
   if r['status']!='complete':raise RuntimeError('training failed: frozen partial evidence; validation blocked')
  table=export_table(controller.gate)
 finally:env.close()
 event(root,'train_end',receipts=receipt_hashes(root,'train'))
 write(root/'learned-table.json',table)
 write(root/'table-freeze.json',{'sha':digest(table),'utc':datetime.now(timezone.utc).isoformat()})
 event(root,'table_frozen',table_sha=digest(table),freeze_receipt_sha=sha(root/'table-freeze.json'))
 for phase in ('diagnostic','validation'):
  active.update(phase=phase,job=None);check_sources(root);event(root,phase+'_start')
  jobs=[j for j in agenda() if j['phase']==phase];failures=[]
  with ProcessPoolExecutor(max_workers=4) as pool:
   futures={pool.submit(run_job,str(root),j,table):j for j in jobs}
   for future in as_completed(futures):
    j=futures[future];active['job']=j
    try:
     r=future.result()
     if r['status']!='complete':failures.append(j)
     print(canonical({'completed':j,'status':r['status'],'cost':r['cost'],'goals':r['goals']}),flush=True)
    except Exception:
     write(root/'episodes'/f"{j['phase']}-{j['arm']}-{j['seed']}.failure.json",{'job':j,'traceback':traceback.format_exc()})
     failures.append(j)
  if failures:raise RuntimeError('instrumental failures; no valid utility gate: '+canonical(failures))
  event(root,phase+'_end',receipts=receipt_hashes(root,phase))
 end=event(root,'run_end',episodes=250)
 write(root/'completed.json',{'episodes':250,'last_phase_sha':sha(end),'utc':read(end)['utc']})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','run'));p.add_argument('root');a=p.parse_args()
 if a.command=='prepare':print(prepare(a.root))
 else:run(a.root)
