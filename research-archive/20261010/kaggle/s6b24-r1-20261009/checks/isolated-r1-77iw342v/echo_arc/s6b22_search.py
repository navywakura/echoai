"""B22-S: paired global exploration and two-child, fixed-duration repair.

Pure researcher: only its serialized development observations are inputs.
Association scores order experiments; they never certify the child's outcome.
"""
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
import json
import random

from echo_arc import s6b20_search as language, s6b21_search as common
from echo_arc.contrastive_evidence import require_development
from echo_arc.feasible_grammar import canonical, matches
from seed.game_selfimprove import sha
from seed.s6b13_prompt import effective

VALUES = language.VALUES
ROUNDS = 18
MAX_REPAIRS = 8
KINDS = ('R22', 'M22')


def rng(seed, *parts):
    return random.Random(int(sha(['B22-S', seed, *parts]), 16))


def config():
    return dict(rounds=ROUNDS, max_repairs=MAX_REPAIRS, block_size=2,
                language_sha256=language.language_sha(), values=VALUES,
                global_distribution='1/2 general syntax; 1/2 uniform base-pool guard; uniform HOLD',
                general_distribution='uniform length 1/2/3, feature subset, atom per feature',
                base_pool='B20 expanded, baseline only; no outcome or history rotation',
                local_support='one literal edit: replace/delete/add; at most 3 distinct features',
                parent_order='fewest losing cases, largest net gain, earliest id',
                second_child='maximum observed-mask distance from first, then overlap rank',
                base_policy='accepted B14; no B21 winning policy or rejected history',
                duration_repair=False, model_calls=0)


@lru_cache(maxsize=8)
def base_pool(encoded):
    obj=json.loads(encoded)
    guards, meta=language.pool(obj['rows'], [], obj['policy'])
    return tuple(sorted(guards, key=canonical)), meta


def global_candidate(seed, global_index, policy, rows):
    """The same exogenous stream for R22 and M22, independent of results."""
    value=rng(seed, global_index, 'global-duration').choice(VALUES)
    mode=rng(seed, global_index, 'global-mode').randrange(2)
    pool, meta=base_pool(canonical(dict(policy=policy, rows=rows))) if mode else ((), {})
    if pool:
        guard=rng(seed, global_index, 'global-member').choice(pool)
        source='base-pool'
    else:
        guard=common.sample_guard(rng(seed, global_index, 'global-syntax'))
        source='general'
    proposal=common.validate_proposal({'patches':[{'when':guard, 'set':{'HOLD':value}}]})
    return proposal, dict(global_index=global_index, distribution=source, pool=meta,
                         predicted_gain=None, loss_risk='unknown', measured_effect=None)


def neighbors(guard):
    """All one-literal neighbors; observational equality never removes syntax."""
    if not language.legal(guard):
        raise ValueError('illegal parent guard')
    result={}
    atoms=language.atoms()
    for key in guard:
        reduced={k:list(v) for k,v in guard.items() if k!=key}
        if reduced:
            result[canonical(reduced)]=reduced
        for newkey, op, value in atoms:
            if newkey in reduced:
                continue
            changed=dict(reduced, **{newkey:[op,value]})
            if changed!=guard:
                result[canonical(changed)]=changed
    if len(guard)<3:
        for key,op,value in atoms:
            if key not in guard:
                changed=dict(guard, **{key:[op,value]})
                result[canonical(changed)]=changed
    return [result[k] for k in sorted(result)]


def effects(event):
    cases=event['development']['case_effects']
    loss=[c['case_index'] for c in cases if c['level_delta']<0 or c['score_delta'] < -1e-10]
    return sum(c['level_delta'] for c in cases), loss


def overlap(guard, parent, policy):
    """Mean fraction of distinct effective contexts per case, no dose prediction."""
    groups=defaultdict(list)
    per_case=[]
    for case in parent['development']['case_effects']:
        index=case['case_index']
        reads=parent['development']['candidate_consumers'][index]
        unique={canonical(r['features']):r['features'] for r in reads
                if r['value']!=effective('HOLD',r['features'],policy)}
        hits=sum(matches(guard,f) for f in unique.values())
        fraction=Fraction(hits,len(unique)) if unique else None
        is_loss=case['level_delta']<0 or case['score_delta'] < -1e-10
        is_gain=case['level_delta']>0
        for kind, selected in (('loss',is_loss),('gain',is_gain)):
            if selected:
                groups[kind].append(fraction)
        per_case.append(dict(case_index=index, matching_contexts=hits, contexts=len(unique)))
    def mean(kind):
        values=groups[kind]
        if not values or any(x is None for x in values):
            return None
        return sum(values,Fraction())/len(values)
    return mean('loss'),mean('gain'),per_case


def validate_history(policy, rows, history, index):
    require_development(rows)
    if len(history)!=index or [e['id'] for e in history]!=list(range(1,index+1)):
        raise ValueError('incomplete or reordered history')
    for e in history:
        if e['base_sha256']!=sha(policy):
            raise ValueError('foreign base')
        d=e.get('development')
        if d is None:
            continue
        if d.get('origin')!='DEVELOPMENT_A' or d.get('consumer_parameter')!='HOLD':
            raise ValueError('protected or foreign evidence')
        if len(d['case_effects'])!=len(rows) or len(d['candidate_consumers'])!=len(rows):
            raise ValueError('incomplete case evidence')
        if [c['case_index'] for c in d['case_effects']]!=list(range(len(rows))):
            raise ValueError('reordered case evidence')


def eligible(history):
    return [e for e in history if e.get('development') and effects(e)[0]>=2 and effects(e)[1]]


def repair_candidates(parent, history, policy, seed, child):
    item=parent['proposal']['patches'][0]
    used={canonical(e['proposal']) for e in history if e.get('proposal')}
    options=[]; filtered=0
    observed={canonical(r['features']):r['features'] for e in history if e.get('development')
              for case in e['development']['candidate_consumers'] for r in case}
    points=[observed[k] for k in sorted(observed)]
    first=next((e for e in history if e.get('schedule',{}).get('phase')=='repair'
                and e.get('target_id')==parent['id']),None)
    for guard in neighbors(item['when']):
        proposal={'patches':[{'when':guard,'set':dict(item['set'])}]}
        if canonical(proposal) in used:
            filtered+=1
            continue
        loss,gain,cases=overlap(guard,parent,policy)
        distance=sum(matches(guard,p)!=matches(first['proposal']['patches'][0]['when'],p)
                     for p in points) if child==2 and first else 0
        rank=(loss is None, loss if loss is not None else Fraction(1),
              gain is None, -(gain if gain is not None else Fraction()),
              sha([seed,'repair-tie',parent['id'],child,proposal]))
        if child==2:
            rank=(-distance,)+rank
        options.append((rank,dict(proposal=proposal,
            loss_context_overlap=float(loss) if loss is not None else None,
            gain_context_overlap=float(gain) if gain is not None else None,
            per_case=cases, observed_distance=distance,
            predicted_gain=None, loss_risk='unknown', measured_effect=None)))
    options.sort(key=lambda x:x[0])
    return [x[1] for x in options],filtered


def request(kind,index,seed,policy,base,history):
    if kind not in KINDS or not 0<=index<ROUNDS:
        raise ValueError('unknown arm or slot')
    validate_history(policy,base['rows'],history,index)
    repairs=sum(e['schedule']['phase']=='repair' for e in history)
    global_index=sum(e['schedule']['phase']=='global' for e in history)
    plan=dict(slot=index+1,phase='global',global_index=global_index)
    parent=None; ranking=[];unserved=[];filtered=0
    if kind=='M22':
        served={e['target_id'] for e in history if e.get('schedule',{}).get('phase')=='repair'}
        unavailable={x['parent_id'] for e in history for x in e.get('schedule',{}).get('unserved',[])
                     if x['reason']=='fewer than two legal unmeasured neighbors'}
        if history and history[-1]['schedule'].get('child')==1:
            parent=next(e for e in history if e['id']==history[-1]['target_id'])
            child=2
        else:
            child=1
            candidates=sorted((e for e in eligible(history) if e['id'] not in served|unavailable),
                              key=lambda e:(len(effects(e)[1]),-effects(e)[0],e['id']))
            for e in candidates:
                if repairs+2>MAX_REPAIRS or ROUNDS-index<2:
                    unserved.append(dict(parent_id=e['id'],reason='repair budget' if repairs+2>MAX_REPAIRS else 'remaining slots'))
                    continue
                trial,count=repair_candidates(e,history,policy,seed,1)
                if len(trial)<2:
                    unserved.append(dict(parent_id=e['id'],reason='fewer than two legal unmeasured neighbors'))
                    continue
                parent=e;ranking=trial;filtered=count
                break
        if parent:
            if not ranking:
                ranking,filtered=repair_candidates(parent,history,policy,seed,child)
            if ranking:
                plan.update(phase='repair',child=child,parent_id=parent['id'],
                            repairs_used=repairs,block_size=2,returned_slots=0,
                            candidates=len(ranking),filtered_exact_duplicates=filtered)
            else:
                unserved.append(dict(parent_id=parent['id'],reason='second neighbor unavailable'))
                parent=None;plan['returned_slots']=1
    if parent:
        proposal=ranking[0]['proposal']
        antecedent=dict(parent_id=parent['id'],parent_gain=effects(parent)[0],parent_losses=effects(parent)[1])
    else:
        proposal,sample=global_candidate(seed,global_index,policy,base['rows'])
        plan.update(sample);antecedent=None
    plan['unserved']=unserved
    common.validate_proposal(proposal)
    item=proposal['patches'][0]
    return dict(id=index+1,type='REFINE' if parent else 'WAIT',target_id=parent['id'] if parent else None,
                selection_mode=kind,requested_operator='HOLD',operator_binding=True,
                proposal=proposal,schedule=plan,shortlist=ranking[:8] if ranking else [dict(proposal=proposal)],
                antecedent=antecedent,measured_effect=None,predicted_gain=None,loss_risk='unknown',
                guard_schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],
                                  groups=[dict(parameter='HOLD',value=item['set']['HOLD'],guards=[item['when']])]),
                model_call_required=False,prompt_variants=[])


def from_bytes(data):
    obj=json.loads(data)
    if set(obj)!={'policy','base','own_history','kind','index','seed'}:
        raise ValueError('unexpected investigator input surface')
    return request(obj['kind'],obj['index'],obj['seed'],obj['policy'],obj['base'],obj['own_history'])


validate_proposal=common.validate_proposal
answer=common.answer
