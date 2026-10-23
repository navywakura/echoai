#!/usr/bin/env python3
"""Source integrity and a bounded terminal launcher; no scientific certification."""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path

def verify(root: Path) -> dict:
 root=root.resolve();missing=[];changed=[];unsafe=[]
 try:
  manifest=json.loads((root/'SOURCE-MANIFEST.json').read_text());files=manifest['files']
  if not isinstance(files,dict) or not files:raise ValueError('Manifest has no source files')
 except (OSError,ValueError,KeyError,TypeError) as exc:
  return {'valid':False,'error':str(exc),'checked':0,'missing':[],'changed':[],'unsafe':[]}
 for name,sha in files.items():
  parts=Path(name).parts if isinstance(name,str) else ()
  if not parts or Path(name).is_absolute() or '..' in parts or not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):unsafe.append(str(name));continue
  p=root/name
  if not p.resolve().is_relative_to(root) or any((root.joinpath(*parts[:i])).is_symlink() for i in range(1,len(parts)+1)):unsafe.append(name);continue
  if not p.is_file():missing.append(name);continue
  try:
   with p.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
  except OSError:missing.append(name);continue
  if digest!=sha:changed.append(name)
 return {'valid':not(missing or changed or unsafe),'project':manifest.get('project'),'version':manifest.get('version'),'checked':len(files),'missing':missing,'changed':changed,'unsafe':unsafe}

def actions(root,project):
 py=sys.executable
 if project=='echoai':
  return {
   'core-test':[py,'-m','unittest','tests.test_nexus0.TestWorld','tests.test_nexus0.TestTConf','tests.test_nexus0.TestGate','tests.test_nexus0.TestBench','tests.test_qtable','-v'],
   'grid-test':[py,'-m','unittest','tests.test_grid_memory_update','-v'],
   'echo-dev-doctor':[py,'-m','harness.localdev','doctor'],
   'echo-dev-scan':[py,'-m','harness.localdev','scan'],
   'echo-dev-run':[py,'-m','harness.localdev','run'],
  }
 if project=='echoos':
  return {
   'toolchain':['bash','tools/check_toolchain.sh'],
   'build-kernel':['make','ARCH=x86_64','EDITION=universal','-j2','all'],
   'build-isos':['make','ARCH=x86_64','EDITION=universal','iso'],
   'build-arm':['make','build-universal-aarch64'],
   'boot-test':['make','ARCH=x86_64','EDITION=universal','test'],
   'uefi-test':['make','ARCH=x86_64','EDITION=universal','test-uefi'],
   'portability':[py,'tools/portability_gate.py'],
  }
 raise ValueError('Unknown project')

def command(root,project,name):
 registry=actions(root,project)
 if name not in registry:raise ValueError('Unknown action; use list. Sealed research exams are not launchable here.')
 return registry[name]

def doctor(project):
 names=('python3','git','opencode','llama-server','bwrap','echo-nexus','echo-dev') if project=='echoai' else ('clang','nasm','ld.lld','cargo','grub-mkrescue','grub2-mkrescue','xorriso','qemu-system-x86_64','make')
 return {name:shutil.which(name) for name in names}

def run(root,project,name,allow_modified=False):
 integrity=verify(root)
 if not integrity['valid'] and not allow_modified:
  print(json.dumps(integrity,indent=2));print('Source verification failed. Use --allow-modified only for your own development checkout.');return 2
 argv=command(root,project,name)
 print('> '+' '.join(argv),flush=True)
 env=os.environ.copy();env['PYTHONPATH']=str(root)+os.pathsep+str(root.parent)
 logdir=Path(os.getenv('XDG_STATE_HOME',str(Path.home()/'.local/state')))/project/'setup';logdir.mkdir(parents=True,exist_ok=True)
 logfile=logdir/(time.strftime('%Y%m%dT%H%M%S')+'-'+name+'.log')
 try:
  with logfile.open('w') as log:
   process=subprocess.Popen(argv,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   try:
    for line in process.stdout:print(line,end='',flush=True);log.write(line);log.flush()
    code=process.wait()
   except KeyboardInterrupt:
    process.terminate()
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:process.kill();process.wait()
    return 130
 except OSError as exc:print(str(exc));return 1
 print('Log: '+str(logfile));return code

def menu(root,project):
 integrity=verify(root);print('\033[38;5;141m\n  ✦ '+('ECHO-AI 5.8.2' if project=='echoai' else 'echOS 3.0 · kernel source')+'\033[0m')
 print('Source: '+str(root));print('Integrity: '+('PASS' if integrity['valid'] else 'FAIL')+' · '+str(integrity['checked'])+' files')
 registry=list(actions(root,project))
 while True:
  print('\n  v  Verify source\n  d  Detect tools')
  for i,name in enumerate(registry,1):print(f'  {i}  {name}')
  if project=='echoai':print('  t  Launch echo-nexus\n  c  Connection examples')
  print('  q  Exit')
  try:answer=input('  › ').strip().lower()
  except (EOFError,KeyboardInterrupt):return 0
  if answer=='q':return 0
  if answer=='v':print(json.dumps(verify(root),indent=2))
  elif answer=='d':print(json.dumps(doctor(project),indent=2))
  elif answer=='c' and project=='echoai':
   print('/connect api https://provider.example/v1 MODEL API_KEY_ENV\n/connect openrouter free @/path/key-file\n/connect anthropic https://api.anthropic.com/v1 MODEL ANTHROPIC_API_KEY\n/connect local /path/model.gguf\n/connect opencode provider/model\n/connections save NAME')
  elif answer=='t' and project=='echoai':
   from echoai.cli import launch_tui
   launch_tui(root)
  elif answer.isdigit() and 1<=int(answer)<=len(registry):run(root,project,registry[int(answer)-1])
  else:print('Choose a listed action.')

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',nargs='?',default='menu',choices=('menu','verify','doctor','list','run'));parser.add_argument('name',nargs='?');parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--allow-modified',action='store_true');args=parser.parse_args(argv)
 root=args.root.resolve()
 try:project=json.loads((root/'SOURCE-MANIFEST.json').read_text())['project']
 except (OSError,KeyError,ValueError):project='echoai' if (root/'nexus0').is_dir() else 'echoos'
 if args.action=='verify':r=verify(root);print(json.dumps(r,indent=2));return 0 if r['valid'] else 1
 if args.action=='doctor':print(json.dumps(doctor(project),indent=2));return 0
 if args.action=='list':print('\n'.join(actions(root,project)));return 0
 if args.action=='run':return run(root,project,args.name,args.allow_modified)
 return menu(root,project)

if __name__=='__main__':raise SystemExit(main())
