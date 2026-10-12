"""PCWORLD-1 development commands; confirmation and publishing are not actions."""
import argparse
import json
from pathlib import Path
from .pilot import estimate, run_pilot, audit_run

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='action',required=True)
    pilot=sub.add_parser('pilot');pilot.add_argument('--dry-run',action='store_true')
    pilot.add_argument('--tasks',type=int,default=4);pilot.add_argument('--repetitions',type=int,default=1)
    pilot.add_argument('--provider',choices=['fixture','http'],default='fixture')
    pilot.add_argument('--config',type=Path);pilot.add_argument('--output',type=Path)
    aud=sub.add_parser('audit');aud.add_argument('directory',type=Path)
    args=ap.parse_args(argv)
    if args.action=='audit':
        result=audit_run(args.directory);print(json.dumps(result,indent=2));return int(not result['valid'])
    if args.dry_run:
        print(json.dumps(estimate(tasks=args.tasks,repetitions=args.repetitions),indent=2));return 0
    if args.output is None: ap.error('execution needs a new --output directory')
    if args.repetitions!=1: ap.error('repetitions beyond development dry-run need the scientific pilot contract')
    config=json.loads(args.config.read_text()) if args.config else None
    if args.provider=='http' and config is None: ap.error('--provider http needs explicit --config')
    result=run_pilot(args.output,task_count=args.tasks,provider=args.provider,config=config)
    print(json.dumps({'output':str(args.output),'episodes':len(result['episodes']),
                      'accepted':sum(r['development_accepted'] for r in result['episodes']),
                      'llm_calls':result['llm_calls'],'scientific_claim':False},indent=2))
    return int(not result['sources_unchanged'] or any(r['error'] for r in result['episodes']))
