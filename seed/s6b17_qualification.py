"""Qualify B17 orchestration and context using fixtures, never generate or play."""
import copy
import json

from seed import s6b17 as r
from echo_arc import guard_synthesis as synthesis
from tests.test_s6b17_timeline import row as fixture_row

OUT=r.ROOT/'qualification'


def context(name,req,latest):
    path=OUT/(name+'.txt');counts=[]
    for variant,text in enumerate(req['prompt_variants']):
        data=json.loads(text.split('DATA=',1)[1].split('\nJSON only.',1)[0])
        formatter=r.prompts.receipt if req.get('feedback_version')=='B17-control-consumption' else r.prompts.prior.receipt
        if data['latest_attempt']!=formatter(latest):
            raise AssertionError('latest receipt lost: '+name)
        path.write_text(r.model.chat(text))
        counts.append(len(r.model.tokenize(path)))
        if counts[-1]<=r.model.MAX_INPUT: break
    else:
        raise AssertionError('context overflow: '+name+': '+str(counts))
    if req.get('shortlist'):
        for item in req['shortlist']:
            r.prompts.check_answer(r.canonical(item['proposal']),req)
    result=dict(name=name,variant=variant,input_tokens=counts[-1],token_counts=counts,
                target_id=req['target_id'],latest_preserved=True,prompt_sha256=r.file_sha(path))
    r.atomic(path.with_suffix('.json'),result)
    return result


def empty_timeline(measured):
    measured=copy.deepcopy(measured)
    for row in measured['rows']:
        row['diagnostics']['control_timeline']=dict(version=1,reads=[])
    return measured


def run():
    if (r.ROOT/'profile.json').exists(): raise RuntimeError('B17 already frozen')
    OUT.mkdir(parents=True,exist_ok=True)
    r.previous_closure()
    policy,base,initial=r.reference_module.reference()
    contexts=[]
    for arm in r.ARMS:
        req=r.prompts.request(arm,0,policy,base,initial)
        contexts.append(context('initial-'+arm,req,initial[-1]))
    fixtures=[]
    for offset,label in enumerate(('micro/updated-740117/000','micro/updated-740117/001')):
        after=r.read(r.PREVIOUS/'primary/measurements'/label/'A.json')
        event=copy.deepcopy(r.read(r.PREVIOUS/'micro-records'/(label+'.json'))['event'])
        event.update(id=offset+1,target_id=offset or None,base_sha256=r.sha(policy),verdict='V3')
        # Old aggregate-only records have no temporal measurements. Empty
        # timelines here mean unavailable evidence, never inferred timestamps.
        event['development']=synthesis.comparison(empty_timeline(base),empty_timeline(after),'HOLD')
        fixtures.append(event)
    for count in (1,2):
        for arm in ('synth','hybrid'):
            history=initial+fixtures[:count]
            req=r.prompts.request(arm,count,policy,base,history)
            if req['target_id']!=count: raise AssertionError('not refining best descendant')
            contexts.append(context(f'partial-{count}-{arm}',req,history[-1]))
    # Format stress only, using the unit test's synthetic temporal fixture.
    # These links are never experimental evidence or runtime initial memory.
    before=[fixture_row(0),fixture_row(1)]
    after=[fixture_row(0,value=2),fixture_row(1,value=2)]
    after[0]['levels_completed']=5;after[1]['score']=0.1
    for row in after: row['actions'][-1]=['K',5,None]
    links=r.timeline.links({'rows':before},{'rows':after},'HOLD')
    history=initial+copy.deepcopy(fixtures)
    history[-1]['development']['control_links']=links
    req=r.prompts.request('hybrid',2,policy,base,history)
    payload=json.loads(req['prompt_variants'][0].split('DATA=',1)[1].split('\nJSON only.',1)[0])
    if len(payload['control_consumption_links'])!=2 or any(x['features']['pending_effect']!=0 for x in payload['control_consumption_links']):
        raise AssertionError('actual read features lost in context')
    contexts.append(context('synthetic-delayed-feedback-format',req,history[-1]))
    for index in range(3,8):
        child=copy.deepcopy(history[-1]);child.update(id=index,target_id=index-1)
        history.append(child)
    contexts.append(context('last-round-context',r.prompts.request('hybrid',7,policy,base,history),history[-1]))
    tests=(r.REPO/'lab/s6b17-tests.log').read_text()
    regression=(r.REPO/'lab/s6b17-previous-regression.log').read_text()
    if any('\nOK\n' not in log or 'FAILED' in log for log in (tests,regression)):
        raise AssertionError('current tests and prior-controller regression tests must pass')
    (OUT/'tests.log').write_text(tests+'\nPrevious frozen controllers:\n'+regression)
    result=dict(valid=True,at=r.now(),new_games=0,new_model_calls=0,contexts=contexts,
        synthetic_temporal_fixture_only=True,prior_failed_records_used_for_context_qualification_only=True,
        no_fixture_is_runtime_initial_memory=True,tests_log_sha256=r.file_sha(OUT/'tests.log'),sources=r.hashes())
    r.atomic(r.ROOT/'validation.json',result)
    print(r.canonical(dict(valid=True,contexts=len(contexts),max_input_tokens=max(c['input_tokens'] for c in contexts),
        new_games=0,new_model_calls=0)),flush=True)


if __name__=='__main__':run()
