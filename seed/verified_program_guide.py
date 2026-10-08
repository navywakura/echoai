"""Sparse guide for verified executable schemas over color/translation invariant motifs.

Capacity study: associations are acquired, queries change color and placement.
No generalization of arbitrary program labels to unseen motifs is claimed.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import json

from echoai.seed import dsl
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from echoai.seed.refinement import VIEWS, transform, solver_input
from seed.relational_dsl import Work

PROGRAMS = tuple((trim, view, scale) for trim in (False, True) for view in VIEWS for scale in (1, 2))
NAMES = tuple('schema:'+str(i) for i in range(len(PROGRAMS)))


def motif(g, work):
    work.add('encode_cells', len(g)*len(g[0]))
    cells = [(y,x) for y,r in enumerate(g) for x,c in enumerate(r) if c]
    if not cells:
        raise ValueError('empty motif')
    y0,y1=min(y for y,x in cells),max(y for y,x in cells)
    x0,x1=min(x for y,x in cells),max(x for y,x in cells)
    shape = tuple(tuple(int(bool(c)) for c in r[x0:x1+1]) for r in g[y0:y1+1])
    token = sha256(json.dumps(shape,separators=(',',':')).encode()).hexdigest()
    return tuple('motif:'+str(i)+':'+token for i in range(8))


def execute(g, index, work):
    if type(index) is not int or not 0 <= index < len(PROGRAMS):
        raise ValueError('unknown program')
    trim,view,scale=PROGRAMS[index]
    work.add('program_cells',len(g)*len(g[0]))
    if trim:
        cells=[(y,x) for y,r in enumerate(g) for x,c in enumerate(r) if c]
        if not cells:raise ValueError('empty object')
        y0,y1=min(y for y,x in cells),max(y for y,x in cells)
        x0,x1=min(x for y,x in cells),max(x for y,x in cells)
        g=dsl.G(r[x0:x1+1] for r in g[y0:y1+1])
    for name in view:
        work.add('program_cells',len(g)*len(g[0]));g=transform(g,(name,))
    if scale==2:
        work.add('program_cells',4*len(g)*len(g[0]));g=dsl.up2(g)
    return g


class ProgramGuide:
    def __init__(self,units=500000):
        self.bank=SparsePrimitiveGuide(units,NAMES)
        self.examples=0

    def observe(self,task,program,work):
        public=solver_input(task)
        for pair in public['train']:
            prediction=execute(pair['input'],program,work)
            work.add('verification_cells',len(pair['output'])*len(pair['output'][0]))
            if prediction!=pair['output']:raise ValueError('unverified program')
        features=set.intersection(*(set(motif(p['input'],work)) for p in public['train']))
        if len(features)!=8:raise ValueError('one invariant motif per association required')
        name=NAMES[program]
        for feature in sorted(features):
            work.add('hash_probes',8)
            for i in self.bank._indices(feature,name):
                self.bank.weights[i]=min(255,self.bank.weights[i]+1)
        self.examples+=1

    def rank(self,public,work):
        features=set.intersection(*(set(motif(p['input'],work)) for p in public['train']))
        scores={}
        for name in NAMES:
            score=0
            for feature in sorted(features):
                work.add('hash_probes',8)
                score+=sum(self.bank.weights[i] for i in self.bank._indices(feature,name))
            scores[name]=score
        return sorted(range(len(NAMES)),key=lambda i:(-scores[NAMES[i]],i))

    def state(self):
        payload={'schema':'verified-program-guide-1','units':self.bank.units,'names':NAMES,
                 'examples':self.examples,'weights':base64.b64encode(self.bank.weights).decode()}
        return {'payload':payload,'sha256':sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()}

    @classmethod
    def restore(cls,state):
        p=state['payload']
        if sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()!=state['sha256']:
            raise ValueError('corrupted guide')
        if p['schema']!='verified-program-guide-1' or tuple(p['names'])!=NAMES:
            raise ValueError('guide vocabulary mismatch')
        obj=cls(p['units']);weights=base64.b64decode(p['weights'],validate=True)
        if len(weights)!=obj.bank.units:raise ValueError('guide length mismatch')
        obj.bank.weights=bytearray(weights);obj.examples=p['examples']
        return obj


def solve(task,guide=None,*,candidates=1,budget=100000):
    if type(candidates)is not int or not 1<=candidates<=32:
        raise ValueError('one to 32 program candidates')
    public=solver_input(task);work=Work(budget)
    order=guide.rank(public,work) if guide else list(range(32))
    for index in order[:candidates]:
        valid=True
        for pair in public['train']:
            prediction=execute(pair['input'],index,work)
            work.add('verification_cells',len(pair['output'])*len(pair['output'][0]))
            if prediction!=pair['output']:
                valid=False;break
        if valid:
            query=tuple(execute(p['input'],index,work) for p in public['test'])
            return {'predictions':query,'program':index,'work':work.used,'counts':work.counts,
                    'candidate_rank':order.index(index)+1,'test_verified':False}
    return {'predictions':None,'program':None,'work':work.used,'counts':work.counts,
            'candidate_rank':None,'test_verified':False}
