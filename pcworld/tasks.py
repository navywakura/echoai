"""Small, public development fixtures, NOT independent benchmark tasks.

The larger task-count dry run is a resource estimate; these four properties and
value variants cannot replace 60 independent repair/data/filesystem problems.
"""
import json
from .verifier import VERSION

DESCRIPTIONS={
 'sum_positive':'Return the sum of strictly positive integers in the JSON input list; empty input yields 0.',
 'unique_sorted':'Return the ascending list of distinct integers from the JSON input list.',
 'mean_fraction':'Return the exact mean as a reduced fraction object {numerator: integer, denominator: positive integer}. Input is nonempty.',
 'count_distinct':'Return the number of distinct integers in the JSON input list; duplicates count once.'}
INITIAL={
 'sum_positive':'result = sum(values)',
 'unique_sorted':'result = sorted(values)',
 'mean_fraction':"result = {'numerator': sum(values), 'denominator': 1}",
 'count_distinct':'result = len(values)'}
FIXTURE_SOLUTIONS={
 'sum_positive':'result = sum(x for x in values if x > 0)',
 'unique_sorted':'result = sorted(set(values))',
 'mean_fraction':"from fractions import Fraction\nf = Fraction(sum(values), len(values))\nresult = {'numerator':f.numerator, 'denominator':f.denominator}",
 'count_distinct':'result = len(set(values))'}

def program(body):
    return 'import json, sys\nvalues=json.load(sys.stdin)\n'+body+'\nprint(json.dumps(result,sort_keys=True))\n'

def development_tasks(count=4):
    if type(count) is not int or not 1<=count<=4: raise ValueError('1..4 distinct development fixtures; not a scientific pilot')
    return [{'id':'dev-'+p,'property':p,'description':description,'initial':program(INITIAL[p]),
             'public_inputs':[[1,2]],'development_inputs':[[-3,2,2],[0,0,0],[4,-1,4,2]]+([] if p=='mean_fraction' else [[]]),
             'checker':VERSION,'family':p,'split':'development'}
            for p,description in list(DESCRIPTIONS.items())[:count]]

class FixtureProvider:
    """Engineered I/O fixture; no model, no learned solution capability."""
    model='scripted-fixture-v1'
    is_llm=False
    def call(self,role,task,context,*,max_tokens=2048,total_token_budget=None,deadline=None):
        if role in ('critic','self_review'):
            value={'claim_id':task['property'],'input':[-3,2,2],
                   'oracle_reference':VERSION,'preconditions':['integer-list']}
        else: value={'content':program(FIXTURE_SOLUTIONS[task['property']])}
        return value, {'tokens':0,'llm_calls':0,'fixture_calls':1}
