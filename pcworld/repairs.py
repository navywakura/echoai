"""Six new development families with induced bugs, not real-world issue claims.

Finite references stay in the supervisor. Actor input contains only the public
specification, the current candidate and previously observed counterexamples.
"""
import csv
import io
import itertools
import random
import re

VERSION='pcworld-repair-reference-1'
NAMES=('intervals','records','path','csv','pagination','dependencies')

def _integer(x): return type(x) is int and -10000<=x<=10000
def _name(x): return type(x) is str and bool(re.fullmatch(r'[a-z]{1,8}',x))

def repair_domain(prop,x):
    name=prop.removeprefix('repair.')
    if prop!='repair.'+name or name not in NAMES: return False
    if name=='intervals':
        return (type(x) is list and len(x)<=32 and all(type(p) is list and len(p)==2 and
                all(_integer(v) for v in p) and p[0]<=p[1] for p in x))
    if name=='records':
        return (type(x) is list and len(x)<=32 and all(type(p) is dict and set(p)=={'id','value'}
                and _name(p['id']) and _integer(p['value']) for p in x))
    if name=='path': return type(x) is str and len(x)<=512 and bool(re.fullmatch(r'/[a-z./]*',x))
    if name=='csv':
        if type(x) is not str or len(x)>512 or any(ord(c)<32 and c not in '\n\r\t' for c in x): return False
        try:
            rows=list(csv.reader(io.StringIO(x,newline=''),strict=True))
            return len(rows)==1 and len(rows[0])<=32
        except (csv.Error,ValueError): return False
    if name=='pagination':
        return (type(x) is dict and set(x)=={'items','offset','limit'} and type(x['items']) is list
                and len(x['items'])<=64 and all(_integer(i) for i in x['items'])
                and _integer(x['offset']) and _integer(x['limit']))
    if name=='dependencies':
        return (type(x) is dict and set(x)=={'nodes','edges'} and type(x['nodes']) is list
                and len(x['nodes'])<=6 and all(_name(n) for n in x['nodes']) and len(set(x['nodes']))==len(x['nodes'])
                and type(x['edges']) is list and len(x['edges'])<=24 and all(type(e) is list and len(e)==2
                and all(type(n) is str and n in x['nodes'] for n in e) for e in x['edges']))
    return False

def repair_reference(prop,x):
    if not repair_domain(prop,x): raise ValueError('outside repair domain')
    name=prop.split('.')[1]
    if name=='intervals':
        # Connected components of interval-overlap graph; independent from
        # the usual sorted greedy implementation suggested by the task.
        groups=[tuple(p) for p in x]
        changed=True
        while changed:
            changed=False
            for i,a in enumerate(groups):
                for j in range(i+1,len(groups)):
                    b=groups[j]
                    if max(a[0],b[0])<=min(a[1],b[1]):
                        groups[i]=(min(a[0],b[0]),max(a[1],b[1]));groups.pop(j);changed=True;break
                if changed: break
        return [list(p) for p in sorted(groups)]
    if name=='records': return [p for i,p in enumerate(x) if not any(q['id']==p['id'] for q in x[:i])]
    if name=='path':
        # Repeated lexical cancellation of components; no filesystem access.
        parts=[p for p in x.split('/') if p not in ('','.')]
        while '..' in parts:
            i=parts.index('..');parts[max(0,i-1):i+1]=[]
        return '/'+('/'.join(parts))
    if name=='csv': return next(csv.reader(io.StringIO(x,newline=''),strict=True))
    if name=='pagination':
        return [v for i,v in enumerate(x['items']) if max(0,x['offset'])<=i<max(0,x['offset'])+max(0,x['limit'])]
    if name=='dependencies':
        for order in itertools.permutations(sorted(x['nodes'])):
            if all(order.index(a)<order.index(b) for a,b in x['edges']): return list(order)
        return None

def _program(body):
    return 'import json, sys\nx=json.load(sys.stdin)\n'+body+'\nprint(json.dumps(result))\n'

def input_schema(name):
    integer={'type':'integer','minimum':-10000,'maximum':10000}
    label={'type':'string','pattern':'^[a-z]{1,8}$'}
    def array(items,maximum): return {'type':'array','items':items,'maxItems':maximum}
    def obj(properties): return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    if name=='intervals': return array({**array(integer,2),'minItems':2},32)
    if name=='records': return array(obj({'id':label,'value':integer}),32)
    if name in ('path','csv'): return {'type':'string','maxLength':512}
    if name=='pagination': return obj({'items':array(integer,64),'offset':integer,'limit':integer})
    if name=='dependencies': return obj({'nodes':array(label,6),'edges':array({**array(label,2),'minItems':2},24)})
    raise ValueError('unknown domain')

def repair_tasks(count=6):
    if type(count) is not int or not 1<=count<=6: raise ValueError('1..6 independent development families')
    specs=[
      ('intervals','Given at most 32 closed integer intervals [start,end], -10000<=start<=end<=10000, merge every overlapping or touching interval. Return sorted disjoint intervals. Empty -> [].',
       "result=[]\nfor lo,hi in sorted(x):\n if result and lo < result[-1][1]: result[-1][1]=hi\n else: result.append([lo,hi])",
       [[[1,2],[4,5]]], [[[1,4],[2,3]],[[1,2],[2,4]],[],[[5,7],[1,6],[2,3]]]),
      ('records','List of <=32 objects {id: lowercase letters length1..8, value: integer -10000..10000}. Return first record for each id, in first-occurrence order; ignore later values with the same id.',
       "result=list({p['id']:p for p in x}.values())",
       [[{'id':'a','value':1},{'id':'b','value':2}]],
       [[{'id':'b','value':2},{'id':'b','value':3}],[],[{'id':'b','value':0},{'id':'a','value':1},{'id':'b','value':2}]]),
      ('path','Normalize an absolute POSIX path (<=512 characters, lowercase letters, dots and slashes only) lexically. Drop empty and dot components; dotdot removes the previous component without traversing above root. Do not touch the filesystem. Root is /; otherwise no trailing slash.',
       "result='/'+'/'.join(p for p in x.split('/') if p and p!='.')",
       ['/a//./b/'], ['/a/../b','/../../x','/','/one/two/../../three']),
      ('csv','Parse one valid CSV record from a JSON string, <=512 characters and <=32 fields. Comma delimiter, double-quote quoting, doubled double-quotes inside quoted fields. Preserve field spaces and quoted newlines. Return the list of field strings.',
       "result=x.strip().split(',')",
       ['a,b,c'], ['"a,b",c','"a""b",c',' a , b ','"one\ntwo",three']),
      ('pagination','Input object {items: <=64 integers -10000..10000, offset: integer -10000..10000, limit: integer -10000..10000}. Clamp offset and limit separately to at least zero, then return at most limit items starting at offset, preserving order.',
       "result=x['items'][x['offset']:x['offset']+x['limit']]",
       [{'items':[1,2,3],'offset':1,'limit':2}],
       [{'items':[1,2,3],'offset':-1,'limit':2},{'items':[1,2,3],'offset':1,'limit':-1},{'items':[],'offset':0,'limit':2},{'items':[1,2],'offset':9,'limit':1}]),
      ('dependencies','Input {nodes: <=6 unique lowercase names length1..8, edges: <=24 pairs [a,b] of existing names meaning a must precede b}. Duplicate edges have no extra effect. Return lexicographically smallest valid topological order of all nodes, or null for a cycle (including self edges). Empty nodes -> [].',
       "result=sorted(x['nodes'])",
       [{'nodes':['b','a'],'edges':[['a','b']]}],
       [{'nodes':['a','b'],'edges':[['b','a']]},{'nodes':['a'],'edges':[['a','a']]},{'nodes':[],'edges':[]},{'nodes':['a','b','c'],'edges':[['c','a'],['c','a']]}])]
    return [{'id':'repair-'+name,'property':'repair.'+name,'family':name,'description':description,
             'input_schema':description,'preconditions':['repair-'+name+'-domain-v1'],'checker':VERSION,
             'input_json_schema':input_schema(name),
             'initial':_program(body),'public_inputs':public,'development_inputs':hidden,
             'split':'development','provenance':'induced defect, newly authored family; not a public issue benchmark'}
            for name,description,body,public,hidden in specs[:count]]

def repair_task_variants(count=12,*,seed=41):
    """Seeded value variants of the six exposed families, not new domains.

    Only public examples reach model prompts. Evaluation cases are fixed in the
    task manifest before launch and must never be used to tune this policy.
    """
    if type(count) is not int or not 1<=count<=24 or count%len(NAMES):
        raise ValueError('task count must be a multiple of six, from 6 to 24')
    if type(seed) is not int or not 0<=seed<=2**31-1: raise ValueError('invalid task seed')
    base={task['family']:task for task in repair_tasks()}
    rng=random.Random(seed);result=[];per_family=count//len(NAMES)
    for variant in range(per_family):
        labels=rng.sample('abcdefghijklmnopqrstuvwxyz',12)
        values=[rng.randint(-5000,5000) for _ in range(24)]
        for family in NAMES:
            task=dict(base[family]);task['id']=f'repair-v2-{family}-{variant:02d}'
            task['variant']=variant;task['variant_seed']=seed
            task['split']='development'
            task['provenance']='seeded value variant of an exposed repair-v1 family; not an independent bug-family confirmation'
            a,b,c,d=labels[:4];n=values[variant*6:(variant+1)*6]
            if family=='intervals':
                lo,mid,hi=sorted(n[:3]);
                if mid<=lo: mid=lo+1
                if hi<=mid: hi=mid+2
                task['public_inputs']=[[[lo,lo+1],[hi,hi+1]]]
                task['development_inputs']=[[[lo,mid],[mid,hi]],[[lo,hi],[lo+1,mid]],[]]
            elif family=='records':
                task['public_inputs']=[[{'id':a,'value':n[0]},{'id':b,'value':n[1]}]]
                task['development_inputs']=[ [{'id':a,'value':n[0]},{'id':a,'value':n[1]}],
                    [{'id':b,'value':n[0]},{'id':a,'value':n[1]},{'id':b,'value':n[2]}], []]
            elif family=='path':
                task['public_inputs']=[f'/{a}/{b}']
                task['development_inputs']=[f'/{a}/../{b}',f'/../../{a}',f'/{a}//./{b}/']
            elif family=='csv':
                task['public_inputs']=[f'{a},{b},{c}']
                task['development_inputs']=[f'"{a},{b}",{c}',f'"{a}""{b}",{c}',
                    f' {a} , {b} ',f'"{a}\n{b}",{c}']
            elif family=='pagination':
                items=[n[0],n[1],n[2],n[3]]
                task['public_inputs']=[{'items':items,'offset':1,'limit':2}]
                task['development_inputs']=[{'items':items,'offset':-1,'limit':2},
                    {'items':items,'offset':1,'limit':-1},{'items':[],'offset':0,'limit':2},
                    {'items':items,'offset':1,'limit':0}]
            else:
                nodes=sorted((a,b,c))
                task['public_inputs']=[{'nodes':nodes,'edges':[[nodes[0],nodes[1]]]}]
                task['development_inputs']=[
                    {'nodes':[a],'edges':[[a,a]]},
                    {'nodes':[a,b,c],'edges':[[a,b]]},
                    {'nodes':[a,b,c],'edges':[[c,a],[a,b],[c,a]]},
                    {'nodes':[a,b,c],'edges':[]}]
            result.append(task)
    return result
