"""B18: bounded search over own candidate consumption evidence.

The LLM proposes a mechanism; the core covers ranked, untried scopes. This
module never reads experiment artifacts or supplies a known successful guard.
"""
from collections import Counter
from echo_arc import guard_synthesis as prior, repair_memory as memory
from echo_arc import repair_experiments as experiments
from echo_arc.contrastive_evidence import require_development
from echo_arc.contrastive_grammar import choices
from echo_arc.feasible_grammar import canonical, matches
from seed import s6b13_prompt as grammar, s6b17_prompt as prompts


def comparison(before, after, parameter):
    result = prior.comparison(before, after, parameter)
    # Complete real consumption contexts, including those absent from the base.
    result['candidate_consumers'] = [
        [dict(features=x['features'], count=x['count'], value=x['value'])
         for x in row['diagnostics']['consumers'] if x['parameter'] == parameter]
        for row in after['rows']]
    result['consumer_parameter'] = parameter
    return result


def own(current, history):
    events = [e for e in history if e.get('base_sha256') == memory.sha(current)
              and e.get('development')]
    for e in events:
        if e['development']['origin'] != 'DEVELOPMENT_A':
            raise ValueError('only own development evidence allowed')
    return events


def consumption_equivalent(proposal, event, current):
    """Certificate restricted to the sole HOLD consumption site.

    With the same deterministic base, same HOLD value and no other mutation,
    equal guard truth on every actual HOLD read preserves every action by
    induction. Patch-hit counters are telemetry, not behavior. A certificate
    must include ALL cases, not just the base or regressive cases.
    """
    if event.get('base_sha256') != memory.sha(current): return False
    d = event.get('development', {})
    if d.get('origin') != 'DEVELOPMENT_A': raise ValueError('protected certificate')
    old = event.get('proposal', {}).get('patches', [])
    new = proposal.get('patches', [])
    reads = d.get('candidate_consumers')
    if len(old) != 1 or len(new) != 1 or reads is None: return False
    if d.get('consumer_parameter') != 'HOLD' or set(old[0]['set']) != {'HOLD'} \
            or new[0]['set'] != old[0]['set']: return False
    if len(reads) != len(d['case_effects']) or len(reads) == 0:
        raise ValueError('incomplete consumption certificate')
    return all(matches(old[0]['when'], x['features']) == matches(new[0]['when'], x['features'])
               for case in reads for x in case)


def rank(schema, rows, target, history, current):
    require_development(rows)
    if not target: return prior.ranked(schema, rows, target, history)
    events = own(current, history)
    if target not in events: raise ValueError('foreign target')
    parameter = experiments.operator(target)
    value = target['proposal']['patches'][0]['set'][parameter]
    if parameter != 'HOLD': return prior.ranked(schema, rows, target, history)
    root = memory.root_id(target, history)
    lineage = [e for e in events if memory.root_id(e, history) == root]
    positive = {x['case_index'] for x in target['development']['case_effects'] if x['level_delta'] > 0}
    negative = {}
    for e in lineage:
        d = e['development']
        reads = d.get('candidate_consumers')
        if d.get('consumer_parameter') != parameter or reads is None or len(reads) != len(rows):
            raise ValueError('complete own candidate consumption evidence required')
        for effect in d['case_effects']:
            if effect['level_delta'] >= 0 and effect['score_delta'] >= -1e-10: continue
            i = effect['case_index']; found = negative.setdefault(i, {})
            counts = Counter()
            vectors = {}
            for x in reads[i]:
                key = canonical(x['features']); counts[key] += x['count']; vectors[key] = x['features']
            for key,n in counts.items():
                found[key] = (vectors[key], max(found.get(key, (None, 0))[1], n))
    candidates = []
    for p, v, guards in choices(schema):
        if (p, v) != (parameter, value): continue
        for guard in guards:
            proposal = {'patches':[{'set':{p:v}, 'when':guard}]}
            if any(consumption_equivalent(proposal, e, current) for e in events
                   if e.get('verdict') == 'V3'): continue
            cover = sum(any(matches(guard, x['features']) for x in rows[i]['diagnostics']['consumers']
                            if x['parameter'] == parameter) for i in positive)
            burden = sum(n for case in negative.values() for f,n in case.values() if matches(guard,f))
            key = (-cover, burden, len(guard), canonical(guard))
            candidates.append((key, dict(proposal=proposal,gain_case_coverage=cover,
                                         loss_read_burden=burden, evidence='own candidate consumptions')))
    return [dict(x, rank=i+1) for i,(_,x) in enumerate(sorted(candidates,key=lambda x:x[0])[:8])]


def feedback(target, limit=4):
    if not target: return []
    d = target['development']
    if d['origin'] != 'DEVELOPMENT_A': raise ValueError('protected feedback')
    reads = d.get('candidate_consumers', [])
    if not reads: return prior.temporal_feedback(target)
    effects = d['case_effects']
    losses = sorted((x for x in effects if x['level_delta'] < 0 or x['score_delta'] < -1e-10),
                    key=lambda x:(x['level_delta'],x['score_delta']))
    gains = sorted((x for x in effects if x['level_delta'] > 0), key=lambda x:-x['level_delta'])
    result = []
    for effect in losses[:1] + gains[:1]:
        case = reads[effect['case_index']]
        # Contrast varying feature values, including later values absent at the
        # first intervention. Never interpret every read of a lost game as causal.
        varying = sorted(k for k in case[0]['features'] if len({x['features'][k] for x in case})>1) if case else []
        selected = []
        for key in varying:
            for item in (min(case,key=lambda x:x['features'][key]),max(case,key=lambda x:x['features'][key])):
                if item not in selected: selected.append(item)
        selected += [x for x in case if x not in selected]
        result.append(dict(level_delta=effect['level_delta'],score_delta=effect['score_delta'],
            observed_candidate_consumptions=selected[:limit],
            causal_status='observed contexts; final gain/loss is not individual-read causation'))
    return result


def request(arm, index, current, measured, history):
    if arm == 'llm_selector':
        return prompts.request('hybrid', index, current, measured, history)
    if arm not in ('synth','hybrid'): raise ValueError('unknown B18 arm')
    if arm == 'hybrid' and index == 0:
        return prompts.request('hybrid', index, current, measured, history)
    rows = measured['rows']; selection = prior.select(rows,'echo',current,history,index+1)
    parameter,target = selection['parameter'],selection['target']
    schema = grammar.schema_for([rows[i] for i in selection['selected']],current,history)
    schema['groups'] = [dict(parameter=p,value=v,guards=gs) for p,v,gs in choices(schema) if p==parameter]
    schema = memory.prune_repeated_failures(schema,rows,current,history)
    short = rank(schema,rows,target,history,current)
    groups = []
    for item in short:
        one = item['proposal']['patches'][0]; p,v = next(iter(one['set'].items()))
        found = next((g for g in groups if (g['parameter'],g['value'])==(p,v)),None)
        if found is None: found=dict(parameter=p,value=v,guards=[]);groups.append(found)
        found['guards'].append(one['when'])
    return dict(id=index+1,type='REFINE' if target else selection['focus'],
        requested_operator=parameter,target_id=target['id'] if target else None,
        target_parameter=parameter if target else None,operator_binding=True,
        guard_schema=dict(schema,groups=groups),shortlist=short,
        prompt_variants=[],feedback_version='B18-own-candidate-consumption',
        evidence=feedback(target),selection_mode='core-rank-first-finite-search',
        model_call_required=False)


def deterministic_answer(req):
    return prompts.deterministic_answer(req)
