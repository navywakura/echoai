"""Acquire verified demonstration programs into a new development candidate.

The parent artifact is never overwritten. This is supervised demonstration
acquisition, not S6, autonomous code modification or a passed private exam.
"""
from __future__ import annotations
import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO.parent))
from seed.echo45_grid_v2 import load, predict
from seed.arc_memory import sha,ArcMemory
from seed.integration_campaign import save,file_sha
from echoai.seed.refinement import solver_input
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide


def acquire(candidate,task,source,*,journal=None):
    original,lib,old_memory,old_guides=candidate
    public=solver_input(task)
    before=sha(original)
    result=predict(public,candidate,journal=journal)['result']
    if result['program'] is None:raise ValueError('no verified program to retain')
    memory=ArcMemory.restore(old_memory.state(),lib)
    receipt=memory.remember(public,result['program'],lib,source,work=result['metrics']['primitive_calls'])
    if receipt is None:raise ValueError('bounded memory is full; parent retained')
    payload=deepcopy(original);payload['memory']=memory.state()
    updated=[]
    for units,original_guide in old_guides.items():
        guide=deepcopy(original_guide)
        # Relational extensions without a primitive recognized by this frozen
        # associative guide stay in memory; no fabricated guide training.
        recognized={s[0] for s in result['program']} & set(guide.names)
        if recognized:
            guide.observe(public,result['program'],lib)
            payload['guides'][str(units)]['weights']=base64.b64encode(guide.weights).decode('ascii')
            payload['guides'][str(units)]['examples']=guide.examples
            updated.append(units)
    payload['derived_from']=before
    payload['acquisition']={'source':source,'input_sha256':sha(public),'receipt':receipt,
        'program':result['program'],'guides_updated':updated,'test_outputs_used':False,
        'algorithm_sha256':file_sha(Path(__file__)), 'search_metrics':result['metrics'],
        'scope':'demonstration acquisition; not an autonomous S6 improvement'}
    if sha(original)!=before:raise RuntimeError('parent artifact mutated')
    return {'sha256':sha(payload),'payload':payload}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('task',type=Path);ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    if args.output.exists():raise ValueError('new candidate path required')
    from echoai.seed import gym
    gym._guard(args.task)
    if args.task.stem in set(gym.split()['holdout']):raise ValueError('gym holdout is unavailable for acquisition')
    from echo_arc.observe import Journal
    journal=Journal(REPO/'lab/observability'/('arc-memory-learn-'+uuid.uuid4().hex[:12])/'decisions.jsonl')
    try:
        result=acquire(load(args.candidate),json.loads(args.task.read_text()),
                       'developer-demonstrations:'+file_sha(args.task),journal=journal)
        save(args.output,result)
    finally:journal.close()
    print(json.dumps({'candidate':str(args.output),'sha256':result['sha256'],
                     'acquisition':result['payload']['acquisition']}))


if __name__=='__main__':main()
