"""Bounded guard search and lineage selection from own development evidence."""
from echo_arc import repair_experiments as experiments, repair_memory as memory
from echo_arc import repair_outcomes as previous, consumption_timeline as timeline
from echo_arc.contrastive_grammar import choices, witnesses
from echo_arc.contrastive_evidence import require_development
from echo_arc.feasible_grammar import canonical, matches

MAX_DESCENDANTS = 7
SHORTLIST = 8


def comparison(before,after,parameter):
    result=previous.comparison(before,after)
    effects=[dict(case_index=i,level_delta=a['levels_completed']-b['levels_completed'],
                  score_delta=a['score']-b['score'])
             for i,(b,a) in enumerate(zip(before['rows'],after['rows'],strict=True))]
    return dict(result,case_effects=effects,score_loss=sum(max(0,-e['score_delta']) for e in effects),
                control_links=timeline.links(before,after,parameter))


def quality(event):
    d=event['development']
    return (d.get('gross_level_gain',0),-d.get('gross_level_loss',0),
            -d.get('losses',0),-d.get('score_loss',0))


def target_for(current,history,available):
    own=[e for e in history if e.get('base_sha256')==memory.sha(current)]
    candidates=[]
    for event in own:
        if not experiments.measured(event) or experiments.operator(event) not in available \
                or event['verdict'] not in ('V3','V4') or event['development'].get('gross_level_gain',0)<=0:
            continue
        root=memory.root_id(event,own)
        lineage=[e for e in own if memory.root_id(e,own)==root]
        if any(e['verdict']=='A_ONLY_PASS' for e in lineage):
            continue
        if sum(e.get('target_id') is not None for e in lineage)>=MAX_DESCENDANTS:
            continue
        candidates.append(event)
    return max(candidates,key=lambda e:(quality(e),-e['id']),default=None)


def select(rows,arm,current,history,index):
    require_development(rows)
    selection=experiments.select(rows,arm,current,history,index)
    if arm!='echo':
        return selection
    observations=[witnesses([r]) for r in rows]
    available=[p for p in experiments.PARAMETERS if any(w[p] for w in observations)]
    target=target_for(current,history,available)
    if target is None:
        # The legacy selector must not reopen a lineage that this controller
        # closed on an A-only success or on its finite repair budget.
        if selection['target'] is not None:
            parameter=selection['parameter']
            pool=[i for i,w in enumerate(observations) if w[parameter]]
            signal='contradictory_noop' if parameter=='REVALIDATE_NOOP' else 'wait_without_progress'
            selected=sorted(pool,key=lambda i:(rows[i]['levels_completed'],
                -rows[i]['diagnostics']['counts'].get(signal,0),i))[:3]
            return dict(selection,target=None,focus=experiments.FOCUS[parameter],selected=selected)
        return selection
    parameter=experiments.operator(target)
    pool=[i for i,w in enumerate(observations) if w[parameter]]
    selected=[c['case_index'] for c in target['development']['contrasts'] if c['case_index'] in pool]
    selected=list(dict.fromkeys(selected+sorted(pool,key=lambda i:(rows[i]['levels_completed'],i))))[:3]
    # Repair has its own hard cap. Aggregate-negative results do not cancel a
    # useful lineage; the next distinct guard must still pass unchanged V3.
    return dict(selection,parameter=parameter,selected=selected,focus='REFINE',target=target,
                paused_family=None,lineage_root=memory.root_id(target,history))


def ranked(schema,rows,target,history):
    """Return at most eight hypotheses. No trace-based utility is certification.

    Fresh mechanisms start with the minimum applicable value and broadest
    observed scope. Repairs retain their best descendant's value while varying
    guards. A union of observed lineage loss cases preserves earlier counterexamples.
    """
    require_development(rows)
    groups=choices(schema)
    if not groups:
        return []
    parameter=experiments.operator(target) if target else groups[0][0]
    candidates=[(v,g) for p,v,gs in groups if p==parameter for g in gs]
    if not candidates:
        return []
    value=target['proposal']['patches'][0]['set'][parameter] if target else min(v for v,_ in candidates)
    guards=[g for v,g in candidates if v==value]
    if not guards:
        return []  # Exhaustion is recorded; never silently change a target's value.
    positive=set(); negative=set()
    if target:
        if target['development']['origin']!='DEVELOPMENT_A':
            raise ValueError('protected target forbidden')
        positive={e['case_index'] for e in target['development']['case_effects'] if e['level_delta']>0}
        root=memory.root_id(target,history)
        for e in history:
            if e.get('base_sha256')==target['base_sha256'] and memory.root_id(e,history)==root:
                d=e.get('development',{})
                if d and d.get('origin')!='DEVELOPMENT_A':
                    raise ValueError('protected counterexample forbidden')
                negative.update(x['case_index'] for x in d.get('case_effects',[])
                                if x['level_delta']<0 or x['score_delta'] < -1e-10)
    if any(i<0 or i>=len(rows) for i in positive|negative):
        raise ValueError('unpaired counterexample index')
    reads={}
    for i,row in enumerate(rows):
        if parameter=='HOLD':
            reads[i]=[(x['features'],x['count']) for x in row['diagnostics']['consumers'] if x['parameter']=='HOLD']
        elif parameter=='COOLDOWN_CAP':
            reads[i]=[(x['features'],x['count']) for x in row['diagnostics']['feature_counts'] if x['features']['hold_remaining']>value]
        else:
            reads[i]=[(x['features'],x['count']) for x in row['diagnostics']['contradiction_features']]
    scored=[]
    for guard in guards:
        cover={i:sum(n for f,n in rs if matches(guard,f)) for i,rs in reads.items()}
        gain_coverage=sum(cover[i]>0 for i in positive)
        loss_burden=sum(cover[i] for i in negative)
        total=sum(cover.values())
        key=(-gain_coverage,loss_burden,len(guard),canonical(guard)) if target else (-total,len(guard),canonical(guard))
        scored.append((key,dict(proposal={'patches':[{'set':{parameter:value},'when':guard}]},
                               gain_case_coverage=gain_coverage,loss_read_burden=loss_burden,
                               total_observed_reads=total)))
    return [dict(item,rank=i+1) for i,(_,item) in enumerate(sorted(scored,key=lambda x:x[0])[:SHORTLIST])]


def temporal_feedback(target,limit=2):
    if not target:
        return []
    d=target['development']
    if d.get('origin')!='DEVELOPMENT_A':
        raise ValueError('protected evidence forbidden')
    links=d.get('control_links',[])
    losses=sorted([e for e in links if e['levels'][1]<e['levels'][0] or e['score'][1]<e['score'][0]-1e-10],
                  key=lambda e:(e['levels'][1]-e['levels'][0],e['score'][1]-e['score'][0]))
    gains=sorted([e for e in links if e['levels'][1]>e['levels'][0]],key=lambda e:e['levels'][0]-e['levels'][1])
    selected=(losses[:1]+gains[:1]+losses[1:]+gains[1:])[:limit]
    return [{k:v for k,v in item.items() if k not in ('case_index','read_action_index','first_action_divergence')}
            for item in selected]
