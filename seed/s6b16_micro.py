"""Paired sequential calibration: B15 controller versus B16, A only."""
import json
import time
from collections import Counter

from seed import s6b16 as r, s6b15_micro as prior_micro, s6b15_prompt as prior_prompt
from echo_arc import repair_outcomes as outcomes, repair_memory as memory

ARMS = ('previous', 'updated')
SEEDS = (740101, 740117, 740129)
ROUNDS = 4
reference = prior_micro.reference


def gate(cells):
    return any(c['arm']=='updated' and c['gain']>=2 and not c['loss_indices']
               and c['levels']==378+c['gain'] and c['reproduced']
               and c['actual_operator']==c['requested_operator'] for c in cells)


def request(arm, index, policy, measured, history):
    # Round zero is byte-identical in the two arms, with paired sampling seeds.
    # Thereafter only that arm's observations and attempts drive its controller.
    prompt = prior_prompt if arm=='previous' or index==0 else r.prompts
    return prompt.request('echo', index+1, policy, measured, history)


def evaluate(measure, label, req, response, policy, baseline, history, arm, index):
    event = dict(base_sha256=r.b.sha(policy), id=index+1, type=req['type'], target_id=req.get('target_id'),
                 answer=response['answer'], usage=response['usage'], equivalent_calls=[])
    summary = dict(cell=label, arm=arm, round=index, requested_operator=req['requested_operator'],
        actual_operator=None, levels=None, gain=0, loss_indices=[], passes_A=False, reproduced=False,
        input_tokens=response['usage']['input_tokens'])
    try:
        proposal = r.prompts.check_answer(response['answer'], req)
        candidate = r.b.strategy(program=r.b.patch.append(policy['program'],proposal))
    except ValueError as exc:
        return dict(event,verdict='V1',reason=str(exc)),dict(summary,verdict='V1')
    after=r.b.reproduced(measure,label+'/A',candidate,r.b.A)
    diff=r.b.difference(baseline,after)
    cmp=outcomes.original.comparison if arm=='previous' else outcomes.comparison
    development=cmp(baseline,after)
    passed=diff['gain']>=2 and not diff['loss_indices']
    actual=next(iter(proposal['patches'][0]['set'])) if proposal['patches'] else None
    # No protected verification in calibration. A_ONLY_PASS is not acceptance.
    event.update(proposal=proposal,candidate=candidate,A=diff,development=development,
                 verdict='A_ONLY_PASS' if passed else 'V3',
                 equivalent_calls=[e['id'] for e in history if e.get('development',{}).get('behavior_sha256')==development['behavior_sha256']])
    if not passed and actual:
        event['decision_certificate']=memory.certificate(after['rows'],policy,candidate)
    summary.update(actual_operator=actual,levels=after['levels'],gain=diff['gain'],loss_indices=diff['loss_indices'],
                   passes_A=passed,reproduced=True,trace_digest=after['trace_digest'],
                   verdict=event['verdict'],proposal=proposal)
    return event,summary


def run():
    frozen=r.b.integrity()
    if (r.ROOT/'micro.json').exists():
        r.micro_gate()
        return json.loads((r.ROOT/'micro.json').read_text())
    r.publish('MICRO_RUNNING')
    start=time.monotonic()
    policy,reference_a,initial=reference()
    measure=r.measurement('primary')
    def only_a(label,candidate,specs,**kwargs):
        if list(map(tuple,specs))!=list(map(tuple,r.b.A)) or kwargs.get('observed',True) is not True:
            raise ValueError('micro can only evaluate observed full development A')
        return measure(label,candidate,specs,**kwargs)
    baseline=r.b.reproduced(only_a,'micro/baseline/A',policy,r.b.A)
    if baseline!=reference_a:
        raise RuntimeError('micro base/replay does not reproduce B14 378 exactly')
    actors={(seed,arm):list(initial) for seed in SEEDS for arm in ARMS}
    cells=[]
    for index in range(ROUNDS):
        for (seed,arm),history in actors.items():
            call=f'micro/{arm}-{seed}/{index:03d}'
            req=request(arm,index,policy,baseline,history)
            sampling_seed=seed+index*1000
            record_path=r.ROOT/'micro-records'/(call+'.json')
            if record_path.exists():
                saved=json.loads(record_path.read_text())
                if saved['request_sha256']!=r.b.sha(req) or saved['profile_sha256']!=r.b.sha(frozen):
                    raise RuntimeError('micro history reconstruction mismatch')
                r.model.load(call,req,sampling_seed,r.ROOT,r.b.sha(frozen),audit_tokens=True)
                event,summary=saved['event'],saved['summary']
            else:
                r.status('MICRO_PROPOSING',cell=call,completed=len(cells),total=24,round=index+1)
                if (r.ROOT/'calls'/call/'result.json').exists():
                    response=r.model.load(call,req,sampling_seed,r.ROOT,r.b.sha(frozen),audit_tokens=True)
                else:
                    response=r.model.propose(call,req,sampling_seed,r.ROOT,r.b.sha(frozen),r.b.MAX_CALLS)
                r.b.visible('requests',requests={call:[dict(id=index+1,type=req['type'],prompt=req['prompt_variants'][response['variant']])]})
                r.b.visible('answers',answers={'arms':{call:[dict(id=index+1,answer=response['answer'])]}})
                event,summary=evaluate(only_a,call,req,response,policy,baseline,history,arm,index)
                r.b.atomic(record_path,dict(event=event,summary=summary,request_sha256=r.b.sha(req),profile_sha256=r.b.sha(frozen)))
                r.b.visible('verdict',**event)
            history.append(event)
            cells.append(summary)
            r.status('MICRO_RESULT',cell=call,completed=len(cells),total=24,levels=summary['levels'],
                     gain=summary['gain'],losses=len(summary['loss_indices']))
    artifacts=[r.ROOT/'primary/measurements/micro/baseline/A.json',r.ROOT/'primary/measurements/micro/baseline/A/replay.json']
    for cell in cells:
        artifacts += [r.ROOT/'micro-records'/(cell['cell']+'.json'),r.ROOT/'calls'/cell['cell']/'result.json']
        if cell['reproduced']:
            artifacts += [r.ROOT/'primary/measurements'/cell['cell']/p for p in ('A.json','A/replay.json')]
    summary={arm:dict(proposals=sum(c['arm']==arm for c in cells),
        passes_A=sum(c['arm']==arm and c['passes_A'] for c in cells),
        best_levels=max((c['levels'] for c in cells if c['arm']==arm and c['levels'] is not None),default=None),
        actual_operators=dict(Counter(c['actual_operator'] for c in cells if c['arm']==arm))) for arm in ARMS}
    result=dict(valid=True,promote=gate(cells),profile_sha256=r.b.sha(frozen),at=r.b.now(),
        cells=cells,summary=summary,model_calls=24,protected_games=0,exam_opened=False,
        pilot_uses_micro_answers=False,seconds_this_invocation=time.monotonic()-start,
        artifacts={str(p.relative_to(r.ROOT)):r.model.digest_file(p) for p in artifacts})
    r.b.atomic(r.ROOT/'micro.json',result)
    r.publish('MICRO_PASSED' if result['promote'] else 'MICRO_NO_PROMOTION')
    return result
