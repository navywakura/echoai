#!/usr/bin/env python3
"""RepoWorld: offline preparation, gated inference, sealed final evaluation."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('echoai',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
package=importlib.util.module_from_spec(spec);sys.modules['echoai']=package;spec.loader.exec_module(package)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('test')
    audit=sub.add_parser('audit-local')
    audit.add_argument('directory',type=Path)
    p=sub.add_parser('calibrate-local')
    for name in ('dataset','runtime','sources','output'): p.add_argument('--'+name,required=True,type=Path)
    p.add_argument('--sample',type=Path,default=ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json')
    for name in ('preflight','smoke','calibrate'):
        q=sub.add_parser(name)
        q.add_argument('--registry',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
        q.add_argument('--contract',type=Path,default=ROOT/'ECHO-5.1/docs/SWE-CONTRACT.json')
        q.add_argument('--sample',type=Path,default=ROOT/'ECHO-5.1/docs/swebench/SWE-SAMPLE.json')
        if name!='preflight':q.add_argument('--instance',required=True)
        if name=='smoke':q.add_argument('--actions',type=Path,required=True)
        if name=='calibrate':
            for key in ('preflight','curator','smoke','provider'):q.add_argument('--'+key,type=Path,required=True)
    q=sub.add_parser('seal')
    for key in ('contract','sample','materials','preflight','curator','smoke','calibration','verification','output'):q.add_argument('--'+key,type=Path,required=True)
    q=sub.add_parser('curator-preflight')
    for key in ('contract','sample','curator','output'):q.add_argument('--'+key,type=Path,required=True)
    q.add_argument('--allow-pull',action='store_true')
    q=sub.add_parser('run')
    for key in ('sealed','registry','sample','provider','output'):q.add_argument('--'+key,type=Path,required=True)
    q.add_argument('--phase',choices=['calibration','primary','guard_ablation','memory_donor','memory'])
    q=sub.add_parser('audit')
    for key in ('directory','sealed','sample'):q.add_argument('--'+key,type=Path,required=True)
    q.add_argument('--export',type=Path)
    q=sub.add_parser('audit-episode');q.add_argument('directory',type=Path)
    q=sub.add_parser('evaluate')
    for key in ('directory','sealed','sample','curator'):q.add_argument('--'+key,type=Path,required=True)
    q=sub.add_parser('verify');q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('status');q.add_argument('directory',type=Path)
    args=parser.parse_args()
    if args.command=='test':
        import unittest
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_repoworld_*.py',top_level_dir=str(ROOT))
        return not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
    if args.command in ('preflight','curator-preflight','smoke','calibrate','seal','run','verify','status'):
        from echoai.repoworld import study
        if args.command in ('preflight','smoke','calibrate'):
            contract=json.loads(args.contract.read_bytes())
            if args.command=='preflight':result=study.preflight(args.registry,contract,args.sample,args.output)
            elif args.command=='smoke':result=study.smoke(args.registry,contract,args.sample,instance_id=args.instance,
                actions=json.loads(args.actions.read_bytes()),output=args.output)
            else:result=study.calibrate_remote(args.registry,contract,args.sample,preflight_dir=args.preflight,curator_dir=args.curator,smoke_dir=args.smoke,
                provider_config=json.loads(args.provider.read_bytes()),instance_id=args.instance,output=args.output)
        elif args.command=='seal':result=study.seal(args.contract,args.sample,json.loads(args.materials.read_bytes()),
            preflight_dir=args.preflight,curator_dir=args.curator,smoke_dir=args.smoke,calibration_dir=args.calibration,verification_dir=args.verification,output=args.output)
        elif args.command=='curator-preflight':
            from echoai.repoworld.evaluator import CuratorCapability
            cap=json.loads(args.curator.read_bytes())
            for k in ('python','harness','dataset','output'):cap[k]=Path(cap[k])
            result=study.curator_preflight(CuratorCapability(**cap),json.loads(args.contract.read_bytes()),args.sample,args.output,allow_pull=args.allow_pull)
        elif args.command=='run':result=study.run_study(args.sealed,args.registry,args.sample,json.loads(args.provider.read_bytes()),args.output,phase=args.phase)
        elif args.command=='verify':
            import subprocess,time,hashlib
            sources=study.source_manifest()
            args.output.mkdir(parents=True,exist_ok=True,mode=0o700);rows=[]
            for name,command in [('repoworld',[sys.executable,str(Path(__file__).resolve()),'test']),
                ('pcworld',[sys.executable,'-I','-B',str(ROOT/'ECHO-5.1/scripts/run.py'),'test']),
                ('design',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_swebench_design_tools.py'])]:
                log=args.output/(name+'.log');started=time.monotonic()
                with log.open('wb') as f:proc=subprocess.run(command,cwd=ROOT,stdout=f,stderr=f,timeout=600)
                rows.append(dict(suite=name,exit_code=proc.returncode,seconds=time.monotonic()-started,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
            result=study.write_gate(args.output,dict(kind='software-verification',valid=all(r['exit_code']==0 for r in rows),suites=rows,gpu_hours=0),source_before=sources)
        else:
            from echoai.repoworld.evaluator import existing_receipts
            records=existing_receipts(args.directory).records
            result=dict(completed=sum(r['body'].get('event')=='repoworld.cell-completed' for r in records),frozen=(args.directory/'frozen/freeze.json').exists())
        print(json.dumps({k:v for k,v in result.items() if k not in ('source_manifest','results','instances')},indent=2))
        return result.get('valid',True) is not True
    if args.command in ('audit','audit-episode','evaluate'):
        from echoai.repoworld.audit import audit_study,audit_episode
        if args.command=='audit-episode':result=audit_episode(args.directory);result.pop('result',None)
        elif args.command=='audit':result=audit_study(args.directory,args.sealed,args.sample,export=args.export)
        else:
            audit_study(args.directory,args.sealed,args.sample)
            from echoai.repoworld.evaluator import evaluate_sealed,CuratorCapability
            cap=json.loads(args.curator.read_bytes())
            for k in ('python','harness','dataset','output'):cap[k]=Path(cap[k])
            result=evaluate_sealed(args.directory/'frozen',json.loads((args.sealed/'schedule.json').read_bytes()),
                curator_capability=CuratorCapability(**cap),run_lock=json.loads((args.sealed/'SWE-RUN-LOCK.json').read_bytes()))
        print(json.dumps({k:v for k,v in result.items() if k!='source_manifest'},indent=2));return 0
    from echoai.repoworld.calibration import run_local, audit_local
    if args.command=='audit-local':
        result=audit_local(args.directory)
        (args.directory/'audit-local.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('valid','receipts','official_evaluation')}))
        return not result['valid']
    result=run_local(dataset=args.dataset,sample=args.sample,runtime=args.runtime,sources=args.sources,output=args.output)
    print(json.dumps({k:result[k] for k in ('valid','completed','passed','llm_calls','swe_resolved')}),flush=True)
    return not result['valid']


if __name__=='__main__': sys.exit(main())
