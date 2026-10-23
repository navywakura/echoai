"""Prospective fixed paired development tasks, committed before search starts."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import platform
import shutil
import time
import traceback
from .api import BASE,BEAMS,Budget,data,actor,config,Recorder
from ..shield2.custody import canonical,digest,read,write,sha


def now():return datetime.now(timezone.utc).isoformat()


def agenda():
 ledger=Budget(20_000_000);initial=ledger.snapshot();rows=[]
 for family in data.FAMILIES:
  for i in range(4):
   rows.append({'family':family,'index':i,'seed':data._seed(37_000_000,'independent',family,i,ledger)})
 final=ledger.snapshot()
 return rows,{'initial':initial,'initial_sha':digest(initial),'final':final,'final_sha':digest(final)}


def sources():
 files=[*sorted((BASE/'echo58/searchrepair').glob('*.py')),BASE/'echo58/shield2/custody.py',
  BASE/'tests/test_echo58_searchrepair.py',BASE/'ECHO-5.8/docs/E-BUSQUEDA-REPAIR-DESIGN.md',
  BASE/'__init__.py',BASE/'echo58/__init__.py']
 files += [BASE/f'ECHO-5/src/echo5/{n}.py' for n in ('__init__','budget','concepts','grounding','legacy','programs','solver','trace','search_cache','transfer_independent')]
 files += [BASE/f'seed/{n}.py' for n in ('__init__','dsl','learn','refinement','relational_dsl')]
 return files+[BASE/'echo_arc/__init__.py',BASE/'echo_arc/observe.py']


def prepare(root):
 root=Path(root).resolve();root.mkdir(parents=True,exist_ok=False);files=sources();archives={}
 for i,p in enumerate(files):
  dest=root/'frozen'/f'{i:03d}-{p.name}';dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest)
  archives[str(dest.relative_to(root))]=sha(dest)
 write(root/'freeze.json',{'sources':{str(p):sha(p) for p in files},'archives':archives,
                         'python':platform.python_version(),'utc':now()})
 jobs,ledger=agenda();write(root/'agenda.json',jobs);write(root/'seed-ledger.json',ledger);case_files={}
 for index,j in enumerate(jobs):
  case=data.make_case(j['seed'],j['family']);evaluation=Budget(20_000_000)
  public=data.public_task(case,ledger=evaluation)
  if digest(public)!=case['public_sha256']:raise ValueError('public identity')
  for name,obj in [(f'private/{index:02d}.json',case),(f'public/{index:02d}.json',public),
                   (f'copy-cost/{index:02d}.json',evaluation.snapshot())]:
   write(root/name,obj);case_files[name]=sha(root/name)
 write(root/'prepared.json',{'utc':now(),'freeze_sha':sha(root/'freeze.json'),
  'agenda_sha':sha(root/'agenda.json'),'seed_ledger_sha':sha(root/'seed-ledger.json'),'cases':case_files})
 return root


def check_prepared(root):
 root=Path(root);freeze=read(root/'freeze.json');p=read(root/'prepared.json')
 if freeze['python']!=platform.python_version():raise ValueError('interpreter changed')
 for path,h in freeze['sources'].items():
  if sha(path)!=h:raise ValueError('source changed: '+path)
 for path,h in freeze['archives'].items():
  if sha(root/path)!=h:raise ValueError('source archive changed')
 for name,key in [('freeze.json','freeze_sha'),('agenda.json','agenda_sha'),('seed-ledger.json','seed_ledger_sha')]:
  if sha(root/name)!=p[key]:raise ValueError('prepared commitment '+name)
 for name,h in p['cases'].items():
  if sha(root/name)!=h:raise ValueError('case changed')
 expected,ledger=agenda()
 if read(root/'agenda.json')!=expected or read(root/'seed-ledger.json')!=ledger:raise ValueError('agenda/seed ledger')
 return p


def run(root):
 root=Path(root).resolve();prepared=check_prepared(root)
 write(root/'started.json',{'utc':now(),'prepared_sha':sha(root/'prepared.json')})
 active=None
 try:
  for index,job in enumerate(read(root/'agenda.json')):
   for beam in BEAMS:
    active={'index':index,'beam':beam};stem=f'{index:02d}-beam{beam}';path=root/'results'/f'{stem}.json'
    journal_path=root/'thought'/f'{stem}.jsonl';public=read(root/'public'/f'{index:02d}.json')
    identity={'index':index,'beam':beam,'public_sha':digest(public),'prepared_sha':sha(root/'prepared.json')}
    t=time.monotonic();cpu=time.process_time()
    with Recorder(journal_path) as journal:
     journal.write(kind='search_repair_begin',identity=identity,configuration=config(beam),budget=2_000_000)
     result=actor(public,beam,journal)
     journal.write(kind='search_repair_end',identity=identity,status=result['status'],result_sha=digest(result))
    row={'identity':identity,'result':result,'wall_seconds':time.monotonic()-t,'cpu_seconds':time.process_time()-cpu,
         'journal':str(journal_path.relative_to(root)),'journal_sha':sha(journal_path),'completed_utc':now()}
    write(path,row)
    print(canonical({'completed':active,'status':result['status'],'work':result['metrics']['used']}),flush=True)
  check_prepared(root)
  write(root/'completed.json',{'utc':now(),'prepared_sha':sha(root/'prepared.json'),
      'results':{str(p.relative_to(root)):sha(p) for p in sorted((root/'results').glob('*.json'))}})
 except BaseException:
  write(root/'failure.json',{'active':active,'traceback':traceback.format_exc(),'utc':now()});raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=('prepare','run'));p.add_argument('root');a=p.parse_args()
 if a.command=='prepare':print(prepare(a.root))
 else:run(a.root)
