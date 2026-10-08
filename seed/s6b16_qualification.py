"""Existing-record qualification of B16; no new games or generated proposals."""
import copy
import json

from seed import s6b16 as r, s6b16_micro as micro, s6b15_prompt as old
from echo_arc import repair_outcomes as outcomes

OUT=r.ROOT/'qualification'


def read(path): return json.loads(path.read_text())


def validate_context(name,req,latest):
    path=OUT/(name+'.txt')
    path.parent.mkdir(parents=True,exist_ok=True)
    variants=[]
    for text in req['prompt_variants']:
        data=json.loads(text.split('DATA=',1)[1].split('\nJSON only.',1)[0])
        if data['latest_attempt']!=r.prompts.receipt(latest):
            raise AssertionError('lost latest receipt')
        if req['target_id'] is not None:
            shown=data['target_contrasts']
            if not any(c['levels'][1]>c['levels'][0] for c in shown):
                raise AssertionError('lost local level gain during compaction')
            if latest['development']['losses'] and not any(c['effect']=='loss' for c in shown):
                raise AssertionError('lost regression during compaction')
        variants.append(data)
    counts=[]
    for i,text in enumerate(req['prompt_variants']):
        path.write_text(r.model.chat(text))
        counts.append(len(r.model.tokenize(path)))
        if counts[-1]<=r.model.MAX_INPUT: break
    else: raise AssertionError('no context fits: '+name+': '+str(counts))
    result=dict(name=name,variant=i,token_counts=counts,input_tokens=counts[-1],target=req['target_id'],
                latest_preserved=True,paired_target_outcomes_preserved=True,prompt_sha256=r.model.digest_file(path))
    r.b.atomic(path.with_suffix('.json'),result)
    return result


def run():
    if (r.ROOT/'profile.json').exists(): raise RuntimeError('qualification already frozen')
    OUT.mkdir(parents=True,exist_ok=True)
    if not r.previous_closed(): raise RuntimeError('prior micro not audited')
    policy,base,initial=micro.reference()
    contexts=[]
    for arm in ('fijo','echo'):
        req=r.prompts.context(arm,1,policy,base,initial)
        contexts.append(validate_context('initial-'+arm,req,initial[-1]))
    feedback_cases=[]
    for cell in read(r.PREVIOUS/'micro.json')['cells']:
        label=cell['cell']
        after=read(r.PREVIOUS/'primary/measurements'/label/'A.json')
        response=read(r.PREVIOUS/'calls'/label/'result.json')
        proposal=r.b.patch.parse(response['answer'])
        candidate=r.b.strategy(program=r.b.patch.append(policy['program'],proposal))
        d=outcomes.comparison(base,after)
        event=dict(id=1,target_id=None,base_sha256=r.b.sha(policy),verdict='V3',type='WAIT',proposal=proposal,
            candidate=candidate,A=r.b.difference(base,after),development=d,equivalent_calls=[])
        history=initial+[event]
        for arm in ('fijo','echo'):
            req=r.prompts.context(arm,2,policy,base,history)
            contexts.append(validate_context(label.replace('/','-')+'-'+arm,req,event))
        previous=outcomes.original.comparison(base,after)
        feedback_cases.append(dict(cell=label,gross_level_gain=d['gross_level_gain'],net_gain=event['A']['gain'],
            old_cases=[c['case_index'] for c in previous['contrasts'][:2]],
            new_cases=[c['case_index'] for c in d['contrasts'][:2]]))
    # Stress mandatory gain/loss contrast preservation with a full legal policy.
    cell=next(c for c in read(r.PREVIOUS/'micro.json')['cells'] if c['cell']=='micro/b1-n1-730101')
    after=read(r.PREVIOUS/'primary/measurements'/cell['cell']/'A.json')
    full=r.b.strategy(program={'patches':[{'set':{'HOLD':i},'when':{'reset_known':['eq',1],
        'pending_effect':['eq',0],'world_events':['ge',128]}} for i in range(32)]})
    target=dict(id=1,target_id=None,base_sha256=r.b.sha(full),verdict='V3',type='WAIT',proposal=cell['proposal'],
                A=r.b.difference(base,after),development=outcomes.comparison(base,after),equivalent_calls=[])
    maximum=validate_context('32-rules-and-local-refinement',r.prompts.context('echo',2,full,base,[target]),target)
    for name,digest in read(r.PREVIOUS/'profile.json')['sources'].items():
        if r.model.digest_file(r.REPO/name)!=digest: raise AssertionError('frozen source changed: '+name)
    tests=(r.REPO/'lab/s6b16-tests.log').read_text()
    if '\nOK\n' not in tests or 'FAILED' in tests: raise AssertionError('tests must pass')
    (OUT/'tests.log').write_text(tests)
    result=dict(valid=True,at=r.b.now(),new_games=0,new_model_calls=0,contexts=contexts,
                maximum_policy_context=maximum,feedback_cases=feedback_cases,prior_sources_unchanged=True,
                tests_log_sha256=r.model.digest_file(OUT/'tests.log'),sources={n:r.model.digest_file(r.REPO/n) for n in r.SOURCES})
    r.b.atomic(r.ROOT/'validation.json',result)
    print(r.b.canonical(dict(valid=True,contexts=len(contexts)+1,
        max_input_tokens=max(c['input_tokens'] for c in contexts+[maximum]),new_games=0,new_model_calls=0)),flush=True)


if __name__=='__main__': run()
