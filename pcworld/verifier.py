"""Host-side reference properties. Candidate code is never imported here.

Finite checked input/output relations, not universal Python correctness.
The returned result is a property observation; only a task contract can decide
which set of properties suffices. Host oracle code never enters the sandbox.
"""
from fractions import Fraction
import json
from .protocol import load_json

VERSION='pcworld-reference-1'
PROPERTIES=('sum_positive','unique_sorted','mean_fraction','count_distinct')

def in_domain(prop,value):
    return (prop in PROPERTIES and isinstance(value,list) and len(value)<=64 and
            all(type(x) is int and -10000<=x<=10000 for x in value) and
            (prop!='mean_fraction' or bool(value)))

def reference(prop,value):
    if not in_domain(prop,value): raise ValueError('outside property domain')
    if prop=='sum_positive':
        total=0
        for x in value:
            if x>0: total+=x
        return total
    if prop=='unique_sorted':
        ordered=[]
        for x in value:
            if x not in ordered:
                at=0
                while at<len(ordered) and ordered[at]<x: at+=1
                ordered.insert(at,x)
        return ordered
    if prop=='count_distinct':
        return sum(1 for i,x in enumerate(value) if x not in value[:i])
    if prop=='mean_fraction':
        result=Fraction(sum(Fraction(x) for x in value),len(value))
        return {'numerator':result.numerator,'denominator':result.denominator}
    raise ValueError(prop)

def validate_challenge(prop,challenge):
    if not isinstance(challenge,dict): return {'status':'unknown','reason':'invalid challenge'}
    if challenge.get('abstention') in ('NO_COUNTEREXAMPLE_FOUND','SPEC_AMBIGUOUS'):
        return {'status':'unknown','reason':challenge['abstention']}
    if challenge.get('claim_id')!=prop or not in_domain(prop,challenge.get('input')):
        return {'status':'unknown','reason':'unrecognized property or input outside contract'}
    if challenge.get('oracle_reference')!=VERSION or challenge.get('preconditions')!=['integer-list']:
        return {'status':'unknown','reason':'missing or incompatible oracle/preconditions'}
    return {'status':'eligible','input':challenge['input'],'scope':prop,'checker':VERSION}

def check_observation(prop,value,execution):
    base={'scope':prop,'checker':VERSION,'snapshot':execution.get('snapshot'),'input':value}
    if execution.get('status') not in ('EXITED','FAILED'):
        return {**base,'status':'unknown','reason':'incomplete execution'}
    if not in_domain(prop,value): return {**base,'status':'unknown','reason':'outside domain'}
    if execution.get('exit_code')!=0:
        return {**base,'status':'unknown','reason':'failed execution without a contracted value; not a value counterexample'}
    try:
        output=load_json(execution['stdout'])
    except (ValueError,KeyError):
        return {**base,'status':'unknown','reason':'no valid output artifact'}
    expected=reference(prop,value)
    # Python bool equals int: use canonical typed JSON for this bounded domain.
    if type(output) is not type(expected):
        return {**base,'status':'unknown','reason':'output schema mismatch'}
    if isinstance(output,list) and (len(output)>64 or any(type(x) is not int for x in output)):
        return {**base,'status':'unknown','reason':'output schema mismatch'}
    if isinstance(output,dict) and (set(output)!=set(expected) or any(type(x) is not int for x in output.values())):
        return {**base,'status':'unknown','reason':'output schema mismatch'}
    same=json.dumps(output,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
    return {**base,'status':'supported' if same else 'contradicted','expected':expected,
            'observed':output,'reason':'finite independent reference comparison'}
