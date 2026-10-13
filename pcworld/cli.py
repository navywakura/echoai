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
    pilot.add_argument('--suite',choices=['fixtures','repair-v1','repair-v2'],default='fixtures')
    pilot.add_argument('--task-seed',type=int,default=41)
    pilot.add_argument('--task-families',nargs='+')
    pilot.add_argument('--episode-wall-seconds',type=int,default=300)
    pilot.add_argument('--runtime',type=Path);pilot.add_argument('--cache-properties',action='store_true')
    pilot.add_argument('--arms',nargs='+',choices=['S','I2','F','E'],default=['S','I2','F','E'])
    pilot.add_argument('--seeded-diagnostic',action='store_true')
    pilot.add_argument('--model-evidence',type=Path)
    runtime=sub.add_parser('runtime');runtime.add_argument('operation',choices=['build','export','import','verify'])
    runtime.add_argument('directory',type=Path);runtime.add_argument('--archive',type=Path)
    runtime.add_argument('--expected-id')
    aud=sub.add_parser('audit');aud.add_argument('directory',type=Path)
    args=ap.parse_args(argv)
    if args.action=='runtime':
        from .runtime import build_runtime,load_runtime,export_runtime,import_runtime
        if args.operation=='build': image=build_runtime(args.directory)
        elif args.operation=='import':
            if not args.archive or not args.expected_id: ap.error('import needs archive and expected-id')
            image=import_runtime(args.archive,args.directory,expected_id=args.expected_id)
        else:
            image=load_runtime(args.directory)
            if args.operation=='export':
                if not args.archive: ap.error('export needs archive')
                export_runtime(image,args.archive)
        print(json.dumps({'runtime_snapshot':image.id,'dependencies_pinned':True,'arbitrary_execution_cacheable':False}))
        return 0
    if args.action=='audit':
        result=audit_run(args.directory);print(json.dumps(result,indent=2));return int(not result['valid'])
    if args.dry_run:
        count=args.tasks
        if args.task_families:
            from .repairs import repair_tasks,repair_task_variants,NAMES
            if args.suite=='fixtures' or not set(args.task_families)<=set(NAMES): ap.error('invalid repair family filter')
            tasks=repair_task_variants(count,seed=args.task_seed) if args.suite=='repair-v2' else repair_tasks(count)
            count=sum(t['family'] in args.task_families for t in tasks)
        print(json.dumps(estimate(tasks=count,repetitions=args.repetitions,arms=len(args.arms),
                                 episode_wall_seconds=args.episode_wall_seconds),indent=2));return 0
    if args.output is None: ap.error('execution needs a new --output directory')
    if args.repetitions!=1: ap.error('repetitions beyond development dry-run need the scientific pilot contract')
    config=json.loads(args.config.read_text()) if args.config else None
    if args.provider=='http' and config is None: ap.error('--provider http needs explicit --config')
    result=run_pilot(args.output,task_count=args.tasks,provider=args.provider,config=config,
        suite=args.suite,runtime=args.runtime,cache_properties=args.cache_properties,arms=args.arms,
        seeded_diagnostic=args.seeded_diagnostic,
        model_evidence=json.loads(args.model_evidence.read_text()) if args.model_evidence else None,
        task_seed=args.task_seed,task_families=args.task_families,episode_wall_seconds=args.episode_wall_seconds)
    print(json.dumps({'output':str(args.output),'episodes':len(result['episodes']),
                      'accepted':sum(r['development_accepted'] for r in result['episodes']),
                      'llm_calls':result['llm_calls'],'scientific_claim':False},indent=2))
    return int(not result['sources_unchanged'] or any(r['error'] for r in result['episodes']))
