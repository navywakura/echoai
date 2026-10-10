"""B17: same legal language, mechanical scope search and bounded LLM choice."""
from echo_arc import guard_synthesis as synthesis, repair_memory as memory
from echo_arc import repair_experiments as experiments
from echo_arc.contrastive_grammar import choices
from seed import s6b13_prompt as grammar, s6b15_prompt as bound, s6b16_prompt as prior

canonical,check_answer=grammar.canonical,bound.check_answer


def receipt(event):
    result=prior.receipt(event)
    if result is not None:
        # The B17 prompt uses named controls/features throughout; an indexed
        # legacy receipt without its column legend would lose meaning.
        result['proposal']=event.get('proposal')
    return result


def request(arm,index,current,measured,history):
    if arm=='b16' or (arm=='hybrid' and index==0):
        return prior.request('echo',index+1,current,measured,history)
    if arm not in ('synth','hybrid'):
        raise ValueError('unknown micro arm')
    rows=measured['rows']
    selection=synthesis.select(rows,'echo',current,history,index+1)
    parameter,target=selection['parameter'],selection['target']
    schema=grammar.schema_for([rows[i] for i in selection['selected']],current,history)
    schema['groups']=[dict(parameter=p,value=v,guards=gs) for p,v,gs in choices(schema) if p==parameter]
    schema=memory.prune_repeated_failures(schema,rows,current,history)
    short=synthesis.ranked(schema,rows,target,history) if target or arm=='synth' else []
    if target or arm=='synth':
        groups=[]
        for item in short:
            patch=item['proposal']['patches'][0]
            p,v=next(iter(patch['set'].items()))
            group=next((g for g in groups if g['parameter']==p and g['value']==v),None)
            if group is None:
                group=dict(parameter=p,value=v,guards=[]);groups.append(group)
            group['guards'].append(patch['when'])
        schema=dict(schema,groups=groups)
    latest=history[-1] if history else None
    payload=dict(accepted_policy=current['program'],requested_operator=parameter,
        best_partial_target=target['proposal'] if target else None,
        target_outcome=receipt(target),latest_attempt=receipt(latest),
        control_consumption_links=synthesis.temporal_feedback(target),
        ranked_scopes=short,limited_to_development=True)
    if not target:
        payload['observed_cases']=experiments.case_data([rows[i] for i in selection['selected']],parameter,2,True)
    head=(
        'Return exactly one JSON patch in the allowed grammar, no prose. '
        'Goal: >=2 extra development levels and no individual level or score loss. '
        'REVALIDATE_NOOP repairs a false movement prediction; HOLD sets future waits after a known reset; '
        'COOLDOWN_CAP shortens an active wait. A target repairs your own best partial proposal. '
        'For a target, keep its control value and choose an untested guard from ranked_scopes. '
        'Ranks maximize coverage of cases that gained levels and minimize readings touched in cases '
        'that lost; these are uncertain screening heuristics, not proof of utility. '
        'control_consumption_links show features when the control was actually read, and later outcomes. '
        'An eventual loss does not make every read in that game harmful. '
        'Use only supplied public features, never game identifiers or coordinates. '
        'Each proposal still needs full execution and replay. If the grammar is empty, return {"patches":[]}. '
    )
    return dict(id=index+1,type='REFINE' if target else selection['focus'],
        target_id=target['id'] if target else None,
        target_parameter=experiments.operator(target) if target else None,
        requested_operator=parameter,operator_binding=True,selected_cases=selection['selected'],
        family_cooldown=selection['paused_family'],lineage_root=memory.root_id(target,history) if target else None,
        applicability_scope='selected development readings',guard_schema=schema,feedback_version='B17-control-consumption',
        shortlist=short,selection_statistics=selection['statistics'],
        prompt_variants=[head+'DATA='+canonical(payload)+'\nJSON only.'])


def deterministic_answer(req):
    if not req.get('shortlist'):
        return canonical(grammar.patch.EMPTY)
    answer=canonical(req['shortlist'][0]['proposal'])
    check_answer(answer,req)
    return answer
