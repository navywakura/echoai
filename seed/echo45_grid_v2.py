"""V2 entry point for the ECHO-4.5 grid development candidate.

export writes a bounded, hashed JSON candidate; solve requires only that file
and the existing DSL. Learning and private evaluation answers are not part of
the solve path. This does not replace NEXUS-0 or any frozen experiment.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import sys
import uuid

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from echoai.seed import sandbox
from echoai.seed.refinement import RefinementLibrary, solver_input
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from seed.arc_memory import ArcMemory, sha
from seed.integrated_grid_v2 import solve

ENGINE_SOURCES=('seed/echo45_grid_v2.py','seed/integrated_grid_v2.py','seed/arc_memory.py',
                'seed/refinement.py','seed/learn.py','seed/dsl.py','seed/sandbox.py',
                'seed/kenyon_capacity.py','seed/village2.py','seed/village3.py',
                'seed/village3_factorized.py','seed/village3_efficient.py',
                'seed/village3_receipts.py','seed/game_selfimprove.py',
                'seed/integration_campaign.py','seed/integration_revision.py','seed/integrated_grid.py')


def export(campaign,output):
    from seed.integration_campaign import integrity, fitted, file_sha, save
    from seed.integration_revision import integrity as revision_integrity
    revision,p=revision_integrity(campaign)
    lib,memory,guides,cost=fitted(p)
    payload={'schema':1,'name':'echo-4.5-integrated-grid-v2-development',
             's6_deferred':True,'release_ready':False,'level':'S2v',
             'library':p['state'],'memory':memory.state(),'search':{
                 k:p['config'][k] for k in ('max_trials','max_depth','beam_width','verification_window')},
             'guides':{str(n):{'units':n,'names':g.names,'examples':g.examples,
                                  'weights':base64.b64encode(g.weights).decode('ascii')}
                       for n,g in guides.items()},
             'profile_sha256':sha(revision),'fit_profile_sha256':sha(p),'fit_cpu_seconds':cost,
             'sources':{f:file_sha(REPO/f) for f in ENGINE_SOURCES}}
    if output.exists():raise ValueError('new export path required')
    save(output,{'sha256':sha(payload),'payload':payload})
    return {'file':str(output),'sha256':sha(payload),'receipts':len(memory.actor.diary),
            'guides':sorted(guides),'release_ready':False}


def load(path):
    from seed.integration_campaign import file_sha
    if path.stat().st_size>8_000_000:raise ValueError('candidate exceeds size limit')
    document=json.loads(path.read_text());p=document['payload']
    if document['sha256']!=sha(p) or p['schema']!=1:raise ValueError('candidate hash or schema invalid')
    if set(p['sources'])!=set(ENGINE_SOURCES):raise ValueError('incomplete runtime manifest')
    for f,h in p['sources'].items():
        if f not in ENGINE_SOURCES or file_sha(REPO/f)!=h:raise ValueError('candidate runtime changed')
    sandbox._set_level(p['level'])
    lib=RefinementLibrary(p['library']['concepts'],p['library']['prior'])
    memory=ArcMemory.restore(p['memory'],lib)
    guides={}
    for n,row in p['guides'].items():
        if int(n)!=row['units']:raise ValueError('guide units mismatch')
        guide=SparsePrimitiveGuide(row['units'],row['names'])
        weights=base64.b64decode(row['weights'],validate=True)
        if len(weights)!=row['units']:raise ValueError('guide weight length mismatch')
        guide.weights=bytearray(weights);guide.examples=row['examples'];guides[int(n)]=guide
    return p,lib,memory,guides


def predict(task,candidate,*,guide_units=None,use_memory=True,views=False,consistency=True,journal=None):
    p,lib,memory,guides=candidate
    # Strip answers at the boundary, including when a developer gives a labelled JSON file.
    public=solver_input(task)
    if guide_units is not None and guide_units not in guides:raise ValueError('guide unavailable')
    result=solve(public,lib,memory=memory if use_memory else None,
                 guide=guides.get(guide_units),views=views,consistency=consistency,journal=journal,**p['search'])
    return {'candidate_sha256':sha(p),'result':result,'release_ready':False,'S6_green':False}


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    ex=sub.add_parser('export');ex.add_argument('--campaign',type=Path,required=True);ex.add_argument('--output',type=Path,required=True)
    run=sub.add_parser('solve');run.add_argument('task',type=Path);run.add_argument('--candidate',type=Path,required=True)
    run.add_argument('--guide',choices=('none','640','65536','500000'),default='none')
    run.add_argument('--no-memory',action='store_true');run.add_argument('--views',action='store_true')
    run.add_argument('--first',action='store_true',help='first verified prediction instead of consistency ranking')
    run.add_argument('--output',type=Path)
    args=ap.parse_args()
    if args.command=='export':result=export(args.campaign,args.output)
    else:
        from echo_arc.observe import Journal
        from seed.integration_campaign import save
        journal=Journal(REPO/'lab/observability'/('echo45-grid-v2-'+uuid.uuid4().hex[:12])/'decisions.jsonl')
        try:
            result=predict(json.loads(args.task.read_text()),load(args.candidate),
                 guide_units=None if args.guide=='none' else int(args.guide),use_memory=not args.no_memory,
                 views=args.views,consistency=not args.first,journal=journal)
        finally:journal.close()
        if args.output:
            if args.output.exists():raise ValueError('new output path required')
            save(args.output,result)
    print(json.dumps(result,sort_keys=True),flush=True)


if __name__=='__main__':main()
