"""B20 development-only bounded HOLD search; never imports experiment results.

Observational signatures order finite search. They are NOT certificates about
unexecuted trajectories. Acceptance always belongs to the independent runner.
"""
import heapq
from collections import Counter, defaultdict
from functools import lru_cache
from itertools import combinations

from echo_arc import cost_guard_search as b19
from echo_arc import guard_search, precise_patch, precise_patch_grammar
from echo_arc.contrastive_evidence import require_development
from echo_arc.feasible_grammar import canonical, matches
from seed.game_selfimprove import sha
from seed.s6b13_prompt import effective

THRESHOLDS = (0,1,2,4,8,16,20,32,40,64,80,128)
VALUES = (0,1,2,4,8,12,16,20,24,32)
MAX_CHILDREN = 3
POOL_LIMIT = 2048


@lru_cache(maxsize=1)
def atoms():
    return tuple((key,op,value) for key,(lo,hi) in sorted(precise_patch.FEATURES.items())
                 for op,value in ((('eq',0),('eq',1)) if (lo,hi)==(0,1) else
                                  tuple((op,v) for op in ('ge','le') for v in THRESHOLDS if lo<=v<=hi)))


def language_sha():
    return sha(dict(version=20,atoms=atoms(),max_literals=3,distinct_features=True,values=VALUES))


def legal(guard):
    return 1<=len(guard)<=3 and all((k,*test) in atoms() for k,test in guard.items())


def own(current,history):
    return guard_search.own(current,history)


def target_for(current,history):
    events=own(current,history)
    counts=Counter(e.get('target_id') for e in events)
    candidates=[e for e in events if e.get('verdict')=='V3'
                and e.get('proposal',{}).get('patches')
                and set(e['proposal']['patches'][0]['set'])=={'HOLD'}
                and e['development'].get('gross_level_gain',0)>0
                and counts[e['id']]<MAX_CHILDREN]
    # Separate outcome signatures preserve complementary branches. Equal
    # signatures prefer the less explored member, never reset its family cap.
    groups=defaultdict(list)
    for e in candidates:
        d=e['development']
        signature=tuple((x['case_index'],x['level_delta']) for x in d['case_effects'] if x['level_delta']>0)
        groups[signature].append(e)
    if not groups:return None
    family_counts=Counter()
    by_id={e['id']:e for e in events}
    for child in events:
        parent=by_id.get(child.get('target_id'))
        if parent:
            signature=tuple((x['case_index'],x['level_delta']) for x in parent['development']['case_effects'] if x['level_delta']>0)
            family_counts[signature]+=1
    eligible=[]
    for signature,group in groups.items():
        if family_counts[signature]>=6:continue
        best=min(group,key=lambda e:(counts[e['id']],e['development']['losses'],e['development']['score_loss'],-e['development']['gross_level_gain'],e['id']))
        # Every active gain branch gets a turn before another consumes all slots.
        eligible.append((family_counts[signature],best['development']['gross_level_gain']<2,
                         best['development']['losses'],best['id'],best))
    return min(eligible,key=lambda x:x[:-1])[-1] if eligible else None


def points_for(rows,history,current):
    require_development(rows)
    points={}
    for row in rows:
        for read in row['diagnostics']['consumers']:
            if read['parameter']=='HOLD':points[canonical(read['features'])]=read['features']
    for event in own(current,history):
        d=event['development']
        if d.get('consumer_parameter')!='HOLD':continue
        if len(d['candidate_consumers'])!=len(rows):raise ValueError('incomplete consumption evidence')
        for case in d['candidate_consumers']:
            for read in case:points[canonical(read['features'])]=read['features']
    return [points[k] for k in sorted(points)]


def pool(rows,history,current,library='expanded'):
    """Enumerate all syntax, group observed signatures for bounded exploration.

    Rotation chooses another representative after a group has been measured.
    No group is declared impossible; counts expose all reductions and truncation.
    """
    points=points_for(rows,history,current)
    if not points:return [],dict(syntax=0,signatures=0,retained=0,truncated=False)
    atom_list=atoms(); masks=[]
    for key,op,value in atom_list:
        masks.append(sum(1<<i for i,f in enumerate(points) if matches({key:[op,value]},f)))
    used={canonical(e['proposal']['patches'][0]['when']) for e in own(current,history) if e.get('proposal',{}).get('patches')}
    representatives={};total=0
    def consider(guard,mask):
        nonlocal total
        total+=1
        if not mask:return
        encoded=canonical(guard)
        key=(encoded in used,len(guard),sha(guard))
        old=representatives.get(mask)
        if old is None or key<old[0]:representatives[mask]=(key,guard)
    if library=='old':
        for guard in precise_patch_grammar.conditions():
            mask=(1<<len(points))-1
            for k,t in guard.items():mask &= masks[atom_list.index((k,*t))]
            consider(guard,mask)
    elif library=='expanded':
        for size in (1,2,3):
            for indices in combinations(range(len(atom_list)),size):
                if len({atom_list[i][0] for i in indices})!=size:continue
                mask=(1<<len(points))-1
                for i in indices:mask &= masks[i]
                # Counting includes the incompatible syntax; it is not hidden.
                total+=1
                if not mask:continue
                guard={atom_list[i][0]:list(atom_list[i][1:]) for i in indices}
                total-=1;consider(guard,mask)
    else:raise ValueError('unknown library')
    all_guards=[g for _,g in representatives.values()]
    # A bounded, outcome-independent cap. All common arms have identical access.
    retained=sorted(all_guards,key=lambda g:(len(g),sha(g)))[:POOL_LIMIT]
    return retained,dict(language_sha256=language_sha(),library=library,syntax=total,
        signatures=len(all_guards),retained=len(retained),truncated=len(all_guards)>POOL_LIMIT,
        reduction='observational grouping for exploration, not semantic pruning',points=len(points))


def schema(guards,rows,current,history):
    reads=[x for r in rows for x in r['diagnostics']['consumers'] if x['parameter']=='HOLD']
    groups=[]
    for value in VALUES:
        allowed=[g for g in guards if any(matches(g,x['features']) and effective('HOLD',x['features'],current)!=value for x in reads)]
        if allowed:groups.append(dict(parameter='HOLD',value=value,guards=allowed))
    return dict(version=11,origin='DEVELOPMENT_A',groups=groups,
                excluded=[p for e in own(current,history) for p in e.get('proposal',{}).get('patches',[])])


def request(kind,index,current,measured,history,library='expanded'):
    if kind not in ('old','new'):raise ValueError('unknown controller')
    rows=measured['rows'];require_development(rows)
    events=own(current,history)
    guards,coverage=pool(rows,history,current,library)
    # Preserve a measured parent's exact scope for controlled dose contrasts;
    # observational representative rotation must not remove that experiment.
    for event in events:
        for item in event.get('proposal',{}).get('patches',[]):
            if legal(item['when']) and item['when'] not in guards:
                guards.append(item['when'])
    shared=schema(guards,rows,current,history)
    if kind=='old':
        target=b19.target_for(current,history,['HOLD'])
        ranked=b19.rank(shared,rows,target,history,current)
    else:
        target=target_for(current,history)
        ranked=rank_new(shared,rows,current,events,target,index)
    return dict(id=index+1,type='REFINE' if target else 'WAIT',target_id=target['id'] if target else None,
        target_parameter='HOLD' if target else None,requested_operator='HOLD',operator_binding=True,
        guard_schema=shared,shortlist=ranked,prompt_variants=[],model_call_required=False,
        evidence=guard_search.feedback(target),selection_mode='B20-'+kind,coverage=coverage)


def rank_new(schema,rows,current,events,target,index):
    from echo_arc.contrastive_grammar import choices
    excluded={canonical(e['proposal']) for e in events if e.get('proposal')}
    # A duration experiment keeps the parent's scope fixed. Scope experiments
    # keep its value fixed. Unknown doses are not penalized as if already tested.
    initial=target['proposal']['patches'][0]['set']['HOLD'] if target else 0
    trials=[e for e in events if target and e.get('target_id')==target['id']]
    dose=bool(target and len(trials)==2)
    same_guard=target['proposal']['patches'][0]['when'] if target else None
    values=[v for v in VALUES if v>initial] if dose else [initial]
    if dose:values=values[:1]
    positive={x['case_index']:x['level_delta'] for x in target['development']['case_effects'] if x['level_delta']>0} if target else {}
    # Associate exact changed readings with the gain/loss of THEIR lineage and
    # dose; do not convert associations into exclusion certificates.
    root=lambda e: __import__('echo_arc.repair_memory',fromlist=['root_id']).root_id(e,events)
    family=[e for e in events if target and root(e)==root(target)]
    def contexts(e,case):
        return [x for x in e['development']['candidate_consumers'][case]
                if x['value']!=effective('HOLD',x['features'],current)]
    negative=[]
    for e in family:
        value=e['proposal']['patches'][0]['set'].get('HOLD')
        for effect in e['development']['case_effects']:
            if effect['level_delta']<0 or effect['score_delta'] < -1e-10:
                negative.extend((value,x['features']) for x in contexts(e,effect['case_index']))
    candidates=[]
    for parameter,value,guards in choices(schema):
        if parameter!='HOLD' or value not in values:continue
        for guard in guards:
            if dose and guard!=same_guard:continue
            proposal={'patches':[{'set':{'HOLD':value},'when':guard}]}
            if canonical(proposal) in excluded:continue
            if any(guard_search.consumption_equivalent(proposal,e,current) for e in events if e['verdict']=='V3'):continue
            positive_hits={i: any(matches(guard,x['features']) for x in contexts(target,i)) for i in positive} if target else {}
            predicted=sum(gain for i,gain in positive.items() if positive_hits[i])
            loss_contexts={canonical(f) for v,f in negative if v==value and matches(guard,f)}
            burden=len(loss_contexts)
            total=sum(matches(guard,x['features']) for r in rows for x in r['diagnostics']['consumers'] if x['parameter']=='HOLD')
            key=(predicted<2,burden,-predicted,len(guard),sha(proposal)) if target else (-total,len(guard),sha(proposal))
            candidates.append((key,dict(proposal=proposal,predicted_gain_coverage=predicted,
                 loss_context_burden=burden,contrast='fixed-scope-dose' if dose else 'fixed-dose-scope',
                 causal_status='association only; fresh execution required')))
    return [dict(item,rank=i+1) for i,(_,item) in enumerate(heapq.nsmallest(8,candidates,key=lambda x:x[0]))]


def answer(request):
    return canonical(request['shortlist'][0]['proposal'] if request['shortlist'] else {'patches':[]})
