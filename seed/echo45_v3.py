"""Private ECHO-4.5 V3 candidate: relational memory, delayed policy and guide."""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent))
from seed.arc_memory import ArcMemory, sha
from seed.arc_delayed_policy import ArcPolicy
from seed.relational_dsl import RelationalLibrary
from seed.relational_solver import solve
from seed.verified_program_guide import ProgramGuide, solve as guided_solve
from echoai.seed.refinement import solver_input


def load(path):
    if path.stat().st_size>16_000_000:raise ValueError('candidate too large')
    doc=json.loads(path.read_text());p=doc['payload']
    if sha(p)!=doc['sha256'] or p['schema']!='echo45-relational-v3':
        raise ValueError('candidate checksum or schema mismatch')
    from seed.relational_campaign import SOURCES
    if set(p['sources'])!=set(SOURCES):raise ValueError('candidate runtime manifest incomplete')
    for f,digest in p['sources'].items():
        if hashlib.sha256((ROOT/f).read_bytes()).hexdigest()!=digest:raise ValueError('candidate runtime changed: '+f)
    return p,ArcMemory.restore(p['memory'],RelationalLibrary()),ArcPolicy.restore(p['policy'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('task',type=Path)
    parser.add_argument('--candidate',type=Path,required=True);parser.add_argument('--guide',type=Path)
    parser.add_argument('--output',type=Path);parser.add_argument('--learn-to',type=Path)
    parser.add_argument('--no-views',action='store_true');parser.add_argument('--first',action='store_true')
    args=parser.parse_args()
    for path in (args.output,args.learn_to):
        if path and path.exists():raise ValueError('new output path required')
    if args.learn_to and args.guide:raise ValueError('guide experiments and memory acquisition are separate')
    if args.learn_to:
        from echoai.seed import gym
        gym._guard(args.task)
        if args.task.stem in set(gym.split()['holdout']):raise ValueError('reserved task unavailable for acquisition')
    p,memory,policy=load(args.candidate)
    public=solver_input(json.loads(args.task.read_text()))
    from echo_arc.observe import Journal
    from seed.relational_campaign import save
    journal=Journal(ROOT/'lab/observability'/('relational-v3-'+uuid.uuid4().hex[:12])/'decisions.jsonl')
    budget=500000;guide_result=None
    try:
        if args.guide:
            guide=ProgramGuide.restore(json.loads(args.guide.read_text()))
            guide_result=guided_solve(public,guide)
            budget-=guide_result['work']
            journal.write(kind='result',agent='verified-program-guide',origin='DEVELOPMENT',result=guide_result)
        if guide_result and guide_result['predictions'] is not None:
            result={'engine':'program-guide','result':guide_result,'release_ready':False,'S6_green':False}
        else:
            r=solve(public,memory=memory,policy=policy,learn=bool(args.learn_to),
                    episode=p.get('next_episode',256),session='candidate/'+sha(p),
                    views=not args.no_views,consistency=not args.first,
                    verification_window=0 if args.first else 32,budget=budget,journal=journal)
            result={'engine':'relational','result':r,'guide_attempt':guide_result,
                    'release_ready':False,'S6_green':False}
            if args.learn_to:
                if r['program'] is None:raise ValueError('no unambiguous verified program to retain')
                receipt=memory.remember(public,r['program'],RelationalLibrary(),
                        'developer-demonstrations:'+sha(public),work=r['metrics']['work'])
                if receipt is None:raise ValueError('memory full; parent unchanged')
                child=deepcopy(p);child.update(memory=memory.state(),policy=policy.state(),
                    next_episode=p.get('next_episode',256)+1,derived_from=sha(p),
                    acquisition={'receipt':receipt,'test_outputs_used':False,'source':sha(public)})
                save(args.learn_to,{'payload':child,'sha256':sha(child)})
        if args.output:save(args.output,result)
        print(json.dumps(result,sort_keys=True))
    finally:journal.close()


if __name__=='__main__':main()
