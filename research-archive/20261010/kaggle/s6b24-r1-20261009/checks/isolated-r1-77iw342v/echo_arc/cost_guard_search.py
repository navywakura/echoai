"""B19: acceptance-aware development search; no protected data or known guard.

Coverage is only a ranking heuristic. A saved read is not a simulator and no
candidate is accepted without real paired execution and independent replay.
"""
from collections import Counter
from types import FunctionType, SimpleNamespace
from echo_arc import guard_search as old, guard_synthesis as prior
from echo_arc import repair_memory as memory, repair_experiments as experiments
from echo_arc.contrastive_evidence import require_development
from echo_arc.contrastive_grammar import choices
from echo_arc.feasible_grammar import canonical, matches
from seed.s6b13_prompt import effective

VALUES = (0,1,2,4,8,12,16,20,24,32,40)

def target_for(current,history,available):
    events=old.own(current,history)
    eligible=[e for e in events if e.get('verdict')=='V3'
              and experiments.operator(e) in available
              and e['development'].get('gross_level_gain',0)>0]
    # Reaching the required gain with fewer losses is preferable to preserving
    # every speculative gain at the expense of conservation.
    def quality(e):
        d=e['development'];net=d['gross_level_gain']-d['gross_level_loss']
        return (net>=2,-d['losses'],-d['score_loss'],net,-e['id'])
    return max(eligible,key=quality,default=None)

select = FunctionType(prior.select.__code__, dict(prior.select.__globals__,target_for=target_for))

def rank(schema,rows,target,history,current):
    require_development(rows)
    if target is None:return prior.ranked(schema,rows,target,history)
    events=old.own(current,history)
    if target not in events:raise ValueError('foreign target')
    parameter=experiments.operator(target)
    if parameter!='HOLD':return old.rank(schema,rows,target,history,current)
    initial=target['proposal']['patches'][0]['set'][parameter]
    # Every third refinement examines a less aggressive duration as well as
    # scope; the other two retain the selected target value. Hard run cap is
    # outside this module. Values come from the declared control bounds.
    count=sum(experiments.operator(e)==parameter for e in events)
    larger=[v for v in VALUES if initial<v<40]
    value=larger[min(count//3-1,len(larger)-1)] if count%3==0 and larger else initial
    positive={x['case_index']:x['level_delta'] for x in target['development']['case_effects'] if x['level_delta']>0}
    negative={}
    for e in events:
        d=e['development']
        if d.get('consumer_parameter')!=parameter:continue
        reads=d.get('candidate_consumers')
        if reads is None or len(reads)!=len(rows):raise ValueError('incomplete candidate consumption evidence')
        for effect in d['case_effects']:
            if effect['level_delta']>=0 and effect['score_delta']>=-1e-10:continue
            seen=negative.setdefault(effect['case_index'],{})
            counts=Counter();vectors={}
            for x in reads[effect['case_index']]:
                # A late consumption with the baseline value is a consequence
                # along the changed trajectory, not another intervention by
                # this patch. Keep every genuinely changed read, including
                # late ones; do not blame all ordinary HOLD reads for a loss.
                if x['value']==effective(parameter,x['features'],current):continue
                key=canonical(x['features']);counts[key]+=x['count'];vectors[key]=x['features']
            for key,n in counts.items():seen[key]=(vectors[key],max(n,seen.get(key,(None,0))[1]))
    ranked=[]
    for p,v,guards in choices(schema):
        if (p,v)!=(parameter,value):continue
        for guard in guards:
            proposal={'patches':[{'set':{p:v},'when':guard}]}
            if any(old.consumption_equivalent(proposal,e,current) for e in events if e.get('verdict')=='V3'):continue
            predicted_gain=sum(gain for i,gain in positive.items() if any(
                matches(guard,x['features']) for x in rows[i]['diagnostics']['consumers'] if x['parameter']==p))
            burden=sum(n for case in negative.values() for f,n in case.values() if matches(guard,f))
            key=(predicted_gain<2,burden,len(guard),canonical(guard))
            ranked.append((key,dict(proposal=proposal,predicted_gain_coverage=predicted_gain,
                loss_read_burden=burden,changed_value=value!=initial,
                evidence='heuristic only; own development candidate reads')))
    return [dict(item,rank=i+1) for i,(_,item) in enumerate(sorted(ranked,key=lambda x:x[0])[:8])]

_request=FunctionType(old.request.__code__,dict(old.request.__globals__,
    prior=SimpleNamespace(select=select),rank=rank))

def request(arm,index,current,measured,history):
    if arm=='guard_only':return old.request('hybrid',index,current,measured,history)
    out=_request(arm,index,current,measured,history)
    if index>0:out['feedback_version']='B19-gain-threshold-cost-first-value-refinement'
    return out

comparison=old.comparison
deterministic_answer=old.deterministic_answer
