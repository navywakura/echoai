"""Installable source/CLI entrypoint. Scientific gates remain independent."""
from __future__ import annotations
import argparse,json,os,subprocess,sys
from pathlib import Path
from . import __version__
from .tools import source_setup
ROOT=Path(__file__).resolve().parent

def backend(root=ROOT):
 state=Path(os.getenv('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'echoai';state.mkdir(parents=True,exist_ok=True)
 path=state/'development-backend.json'
 tests=[{'id':name,'title':title,'kind':'development','default':name=='core-test',
         'argv':[sys.executable,'-m','echoai','devrun',name],'cwd':str(root),'timeout':180}
        for name,title in (('core-test','Core · deterministic policy and evidence checks'),('grid-test','Grid memory · development contracts'))]
 path.write_text(json.dumps({'schema':'echo-nexus-backend-v1','name':f'ECHO {__version__}','tests':tests},indent=2))
 return path

def launch_tui(root=ROOT,extra=None):
 try:import echo_nexus
 except ImportError:
  print('Install the bundled TUI: python -m pip install ./harness/echo-nexus');return 1
 return subprocess.call([sys.executable,'-m','echo_nexus','--backend',str(backend(root)),*(extra or [])],cwd=root)

def dev_main():
 from .harness.localdev.__main__ import main as dev
 return dev()

def memory_demo(path):
 from .echo58.memx.memory import Memory
 from .echo58.wspfiles.memory import export_memory, load_memory
 try:
  memory=Memory()
  for _ in range(3):memory.observe(7,16,'ENTER',0,'HURT')
  export_memory(memory,path,provenance={'source_kind':'synthetic getting-started example'})
  restored=load_memory(path)
  print(json.dumps({'observations':len(restored.records),'new_object_prediction':restored.recall(99,16,'ENTER',0),'memory_file':str(path)},indent=2))
  return 0
 except (OSError,ValueError,TypeError) as exc:
  print(str(exc),file=sys.stderr);return 2


def main(argv=None):
 p=argparse.ArgumentParser(description=f'ECHO {__version__} · memory, local tools and simulation')
 p.add_argument('--version',action='version',version=__version__)
 sub=p.add_subparsers(dest='cmd')
 for name in ('info','verify','doctor','backend'):sub.add_parser(name)
 s=sub.add_parser('memory',help='Inspect, verify or convert WSP memory');s.add_argument('args',nargs=argparse.REMAINDER)
 s=sub.add_parser('demo',help='Learn a role and save it in WSP');s.add_argument('--memory',type=Path,default=Path('echo-memory.wsp'))
 s=sub.add_parser('setup');s.add_argument('action',nargs='?',default='menu',choices=('menu','verify','doctor','list'))
 s=sub.add_parser('devrun');s.add_argument('name');s.add_argument('--allow-modified',action='store_true')
 s=sub.add_parser('tui');s.add_argument('args',nargs=argparse.REMAINDER)
 s=sub.add_parser('connect');s.add_argument('--name',default='neocortex');s.add_argument('--default',action='store_true');s.add_argument('args',nargs=argparse.REMAINDER)
 args=p.parse_args(argv)
 if args.cmd=='info':print(json.dumps({'version':__version__,'status':'stable','runtime':'cpu','memory':'MEMORIA-X / WSP','interface':'echoai','adviser':'optional','source_root':str(ROOT)},indent=2));return 0
 if args.cmd=='memory':return subprocess.call([sys.executable,'-m','echoai.echo58.wspfiles',*args.args])
 if args.cmd=='demo':return memory_demo(args.memory)
 if args.cmd in ('verify','doctor'):return source_setup.main([args.cmd,'--root',str(ROOT)])
 if args.cmd=='backend':print(str(backend()));return 0
 if args.cmd=='setup':return source_setup.main([args.action,'--root',str(ROOT)])
 if args.cmd=='devrun':return source_setup.run(ROOT,'echoai',args.name,args.allow_modified)
 if args.cmd=='connect':
  try:
   from echo_nexus.connections import parse,name
   from echo_nexus.config import load_config,save_config
   value=parse(args.args);config=load_config();profile=name(args.name);config.setdefault('connections',{})[profile]=value
   if args.default:config['default_connection']=profile
   save_config(config);print('Saved connection reference: '+profile+'. No model request sent.');return 0
  except (ImportError,ValueError) as exc:print(str(exc));return 1
 return launch_tui(ROOT,args.args if args.cmd=='tui' else None)

if __name__=='__main__':raise SystemExit(main())
