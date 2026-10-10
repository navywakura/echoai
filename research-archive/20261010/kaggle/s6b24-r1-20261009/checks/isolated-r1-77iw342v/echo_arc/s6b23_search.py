"""B23 investigator: bounded, development-only search; the judge stays external."""
from collections import Counter
from fractions import Fraction
import json

from echo_arc import s6b22_search as old
from echo_arc.feasible_grammar import canonical, matches
from seed.game_selfimprove import sha

KINDS = ('R22', 'M22', 'M23', 'N7', 'N14')
ROUNDS = 18
MAX_REPAIRS = 8
GLOBAL_DRAWS = 64
MAX_CHILDREN = 2
MAX_LINEAGE_REPAIRS = 4
validate_proposal = old.validate_proposal


def config():
    return dict(rounds=ROUNDS, repairs=MAX_REPAIRS, global_draws=GLOBAL_DRAWS,
                max_children=MAX_CHILDREN, max_lineage_repairs=MAX_LINEAGE_REPAIRS,
                eligibility='positive net level gain, including conservative +1',
                parent_order='lineage service count, losses, -gain, newest id',
                repair_modes=['loss-first', 'gain-first', 'balanced'],
                inactive_filter='no matching baseline HOLD consumption only',
                syntax='unchanged B22, one literal edit per child, fixed HOLD',
                original=old.config(), predicted_gain=None)


def inactive(proposal, rows):
    guard = proposal['patches'][0]['when']
    return not any(matches(guard, r['features']) for row in rows
                   for r in row['diagnostics']['consumers'] if r['parameter'] == 'HOLD')


def root_id(event, history):
    by_id = {e['id']: e for e in history}
    seen = set()
    while event.get('target_id') is not None:
        if event['id'] in seen or event['target_id'] not in by_id:
            raise ValueError('broken or cyclic lineage')
        seen.add(event['id'])
        parent = by_id[event['target_id']]
        if parent['id'] >= event['id']:
            raise ValueError('noncausal lineage')
        event = parent
    return event['id']


def parents(history):
    candidates = [e for e in history if e.get('development') and old.effects(e)[0] > 0]
    children = Counter(e.get('target_id') for e in history)
    services = Counter(root_id(e, history) for e in history if e['schedule']['phase'] == 'repair')
    candidates = [e for e in candidates if children[e['id']] < MAX_CHILDREN
                  and services[root_id(e, history)] < MAX_LINEAGE_REPAIRS]
    return sorted(candidates, key=lambda e: (services[root_id(e, history)],
                  len(old.effects(e)[1]), -old.effects(e)[0], -e['id']))


def repairs(parent, history, policy, rows, seed, index, mode):
    used = {canonical(e['proposal']) for e in history if e.get('proposal')}
    patch = parent['proposal']['patches'][0]
    options = []; counts = Counter()
    for guard in old.neighbors(patch['when']):
        proposal = {'patches': [{'when': guard, 'set': dict(patch['set'])}]}
        counts['inspected'] += 1
        if canonical(proposal) in used:
            counts['duplicate'] += 1; continue
        if inactive(proposal, rows):
            counts['inactive'] += 1; continue
        loss, gain, per_case = old.overlap(guard, parent, policy)
        # Unknown associations stay pessimistic, never become predicted results.
        l = loss if loss is not None else Fraction(1)
        g = gain if gain is not None else Fraction(0)
        metrics = (l, -g) if mode == 'loss-first' else (-g, l) if mode == 'gain-first' else (l-g, l, -g)
        rank = metrics + (sha([seed, index, proposal]),)
        options.append((rank, dict(proposal=proposal, loss_context_overlap=float(loss) if loss is not None else None,
                                   gain_context_overlap=float(gain) if gain is not None else None,
                                   per_case=per_case, predicted_gain=None, measured_effect=None)))
    options.sort(key=lambda x: x[0])
    return [x[1] for x in options], dict(counts)


def adaptive(index, seed, policy, base, history):
    old.validate_history(policy, base['rows'], history, index)
    repair_count = sum(e['schedule']['phase'] == 'repair' for e in history)
    global_index = sum(e['schedule']['phase'] == 'global' for e in history)
    plan = dict(slot=index+1, phase='global', global_index=global_index)
    target = None; ranking = []; inspected = []
    if repair_count < MAX_REPAIRS:
        mode = config()['repair_modes'][repair_count % 3]
        for parent in parents(history):
            candidates, counts = repairs(parent, history, policy, base['rows'], seed, index, mode)
            inspected.append(dict(parent_id=parent['id'], **counts))
            if candidates:
                ranking = candidates; target = parent
                plan.update(phase='repair', mode=mode, repairs_used=repair_count,
                            root_id=root_id(parent, history), inspected=inspected)
                break
    if target:
        proposal = ranking[0]['proposal']
    else:
        used = {canonical(e['proposal']) for e in history if e.get('proposal')}
        rejected = []
        for draw in range(GLOBAL_DRAWS):
            proposal, metadata = old.global_candidate(seed, global_index*GLOBAL_DRAWS+draw, policy, base['rows'])
            reason = 'inactive' if inactive(proposal, base['rows']) else 'duplicate' if canonical(proposal) in used else None
            if reason is None:
                break
            rejected.append(dict(proposal_sha256=sha(proposal), reason=reason))
        # A bounded exhausted draw still consumes the final logical slot.
        plan.update(distribution=metadata['distribution'], inspected=inspected,
                    sampled=draw+1, rejected=rejected, exhausted=reason is not None)
    validate_proposal(proposal)
    return dict(id=index+1, type='REFINE' if target else 'WAIT', target_id=target['id'] if target else None,
                selection_mode='M23', requested_operator='HOLD', proposal=proposal, schedule=plan,
                shortlist=ranking[:8], predicted_gain=None, measured_effect=None,
                antecedent=dict(parent_gain=old.effects(target)[0], parent_losses=old.effects(target)[1]) if target else None,
                model_call_required=False)


def read_summary(readings, limit=4):
    """Numeric extremes, plus complete count/hash of omitted observations."""
    unique = {canonical(r): r for r in readings}
    values = [unique[k] for k in sorted(unique)]
    selected = []
    keys = sorted({k for r in values for k in r['features']})
    varying = [k for k in keys if len({r['features'][k] for r in values}) > 1]
    for key in varying:
        for row in (min(values, key=lambda r: r['features'][key]), max(values, key=lambda r: r['features'][key])):
            if row not in selected: selected.append(row)
    selected += [r for r in values if r not in selected]
    return dict(reads=selected[:limit], total=len(readings), unique=len(values),
                omitted=max(0, len(values)-limit), all_sha256=sha(readings))


def model_request(kind, index, seed, policy, base, history):
    old.validate_history(policy, base['rows'], history, index)
    # All attempts and per-case deltas survive. Detailed contexts are restricted
    # to the most recent measured attempt; this rule never depends on model size.
    def effect(c):
        return [c['case_index'],c['level_delta'],format(c['score_delta'],'.4g'),
                int(c['level_delta']<0 or c['score_delta'] < -1e-10)]
    def patch_summary(proposal):
        if proposal is None:return None
        p=proposal['patches'][0]
        return [p['set']['HOLD'],[[k,*test] for k,test in sorted(p['when'].items())]]
    previous = [[e['id'],patch_summary(e.get('proposal')),e['verdict'],e.get('target_id'),
                 e.get('error'),[effect(c) for c in e.get('development',{}).get('case_effects',[])]] for e in history]
    read_columns=sorted(old.language.precise_patch.FEATURES)
    contexts=[]
    def compact(reads):
        summary=read_summary(reads,2)
        packed=[]
        for reading in summary['reads']:
            vector=[reading['features'][k] for k in read_columns]
            if vector not in contexts:contexts.append(vector)
            packed.append([contexts.index(vector),reading['value'],reading['count']])
        return [summary['total'],summary['unique'],summary['omitted'],packed]
    latest = next((e for e in reversed(history) if e.get('development')), None)
    detail = []
    if latest:
        effects=latest['development']['case_effects']
        losses=sorted((c for c in effects if c['level_delta']<0 or c['score_delta'] < -1e-10),
                      key=lambda c:(c['level_delta'],c['score_delta'],c['case_index']))[:2]
        gains=sorted((c for c in effects if c['level_delta']>0),key=lambda c:(-c['level_delta'],c['case_index']))[:1]
        selected={c['case_index']:c for c in losses+gains}
        for i,c in sorted(selected.items()):
            detail.append([effect(c),latest['actions_per_level'][i],compact(latest['development']['candidate_consumers'][i])])
    atoms = {}
    for key, op, value in old.language.atoms(): atoms.setdefault(key, []).append([op, value])
    payload = dict(task='Propose one HOLD patch with >=2 extra levels and zero individual level or score loss.',
        warning='Observed contexts are associations, not proven causes. Do not infer child results from its parent.',
        response_schema={'patches': [{'when': '1 to 3 distinct allowed features: [operator, integer]', 'set': {'HOLD': list(old.VALUES)}}]},
        allowed_atoms=atoms, policy=policy, effect_columns=['case','level_delta','score_delta_4significant_digits','exact_individual_loss'],
        context_columns=read_columns,contexts=contexts,read_columns=['context_id','HOLD_value','count'],
        consumption_columns=['total','unique','omitted','reads'],
        history_columns=['id','patch_[HOLD,guard_triples]','verdict','parent_id','error','effects_all_cases'],
        base_columns=['case','levels','score_4significant_digits','actions_per_level','consumptions'],
        base=[[i,r['levels_completed'],format(r['score'],'.4g'),r['actions_per_level'],
               compact([x for x in r['diagnostics']['consumers'] if x['parameter']=='HOLD'])] for i,r in enumerate(base['rows'])],
        history=previous, latest_measured_id=latest['id'] if latest else None, latest_details=detail,
        latest_detail_columns=['effect','actions_per_level','consumptions'],
        compaction='All level deltas and exact loss flags retained. Display scores rounded to 4 significant digits; judge uses full precision. Latest details: 2 worst losses and 1 largest level gain; at most 2 reads/case. Full observations persist in input receipt.')
    return dict(id=index+1, type='WAIT', target_id=None, selection_mode=kind, requested_operator='HOLD',
                schedule=dict(slot=index+1, phase='model'), model_call_required=True,
                prompt=canonical(payload), predicted_gain=None, measured_effect=None)


def from_bytes(data):
    obj = json.loads(data)
    if set(obj) != {'policy','base','own_history','kind','index','seed'}:
        raise ValueError('unexpected investigator input surface')
    kind, index = obj['kind'], obj['index']
    if kind not in KINDS or not 0 <= index < ROUNDS: raise ValueError('unknown arm or slot')
    args = (index, obj['seed'], obj['policy'], obj['base'], obj['own_history'])
    if kind in old.KINDS: return old.request(kind, *args)
    return adaptive(*args) if kind == 'M23' else model_request(kind, *args)
