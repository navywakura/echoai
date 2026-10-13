#!/usr/bin/env python3
"""Local RepoWorld development entry point. No scientific/GPU launch command."""
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
    args=parser.parse_args()
    if args.command=='test':
        import unittest
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_repoworld_*.py',top_level_dir=str(ROOT))
        return not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
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
