"""B21-A: seeded joint duration/guard search, with no experiment artifact reads."""
from collections import Counter, defaultdict
import random
import json

from echo_arc import s6b20_search as baseline, s6b21_archive as archive
from echo_arc.feasible_grammar import canonical, matches
from echo_arc.contrastive_evidence import require_development
from seed.game_selfimprove import sha

VALUES = baseline.VALUES
ROUNDS = 18
GENERAL_POOL = 64
REPAIR_POOL = 128


def rng(seed, *parts):
    return random.Random(int(sha(['B21-A', seed, *parts]), 16))


def config():
    return dict(values=VALUES, rounds=ROUNDS, general_pool=GENERAL_POOL,
                repair_pool=REPAIR_POOL, archive_limit=archive.LIMIT,
                grammar_sha256=baseline.language_sha(), general_length='uniform 1,2,3',
                general_features='uniform distinct feature subset',
                general_atoms='uniform legal atom per feature',
                inactive_guards_allowed=True, max_children=2)


def agenda(seed):
    durations = list(VALUES)
    rng(seed, 'durations').shuffle(durations)
    first = rng(seed, 'modes').randrange(2)
    plan = [dict(slot=i+1, phase='coverage', mode=('diversity', 'general')[(i+first)%2], value=v)
            for i, v in enumerate(durations)]
    goals = ('repair-loss', 'increase-gain', 'increase-gain', 'repair-loss')
    for j in range(8):
        if j % 2 == 0:
            k = j//2
            plan.append(dict(slot=11+j, phase='repair', mode=('scope', 'duration')[k%2], objective=goals[k]))
        else:
            plan.append(dict(slot=11+j, phase='explore', mode=('general', 'diversity')[(j//2)%2]))
    return plan


def sample_guard(randomizer):
    by_key = defaultdict(list)
    for key, op, value in baseline.atoms():
        by_key[key].append([op, value])
    size = randomizer.choice((1, 2, 3))
    keys = sorted(randomizer.sample(sorted(by_key), size))
    return {key: randomizer.choice(by_key[key]) for key in keys}


def signature(guard, points):
    return sha([matches(guard, p) for p in points])


def general_guard(seed, index):
    # No rejection for inactive or previously tested guards: every legal guard
    # retains support. Such attempts still consume a logical slot.
    return sample_guard(rng(seed, index, 'general'))


def diversity_guard(seed, index, rows, policy, history, *, adaptive=True):
    points = baseline.points_for(rows, history, policy)
    guards, coverage = baseline.pool(rows, history, policy)
    sampled = rng(seed, index, 'signature-members')
    guards.extend(sample_guard(sampled) for _ in range(GENERAL_POOL))
    grouped = defaultdict(list)
    for guard in {canonical(g): g for g in guards}.values():
        grouped[signature(guard, points)].append(guard)
    if not grouped:
        return general_guard(seed, index), dict(signatures=0)
    seen = Counter(signature(e['proposal']['patches'][0]['when'], points) for e in history if e.get('proposal')) if adaptive else Counter()
    least = min(seen[k] for k in grouped)
    candidates = sorted(k for k in grouped if seen[k] == least)
    selected = rng(seed, index, 'signature').choice(candidates)
    used = {canonical(e['proposal']['patches'][0]['when']) for e in history if e.get('proposal')}
    members = sorted(grouped[selected], key=canonical)
    fresh = [g for g in members if canonical(g) not in used] if adaptive else members
    guard = rng(seed, index, 'member').choice(fresh or members)
    return guard, dict(coverage, sampled_members=GENERAL_POOL, signature=selected,
                       minimum_prior_exposures=least, points_sha256=sha(points))


def validate_proposal(proposal):
    p = baseline.precise_patch.validate(proposal)
    if len(p['patches']) != 1:
        raise ValueError('exactly one patch')
    item = p['patches'][0]
    if set(item['set']) != {'HOLD'} or item['set']['HOLD'] not in VALUES or not baseline.legal(item['when']):
        raise ValueError('outside the common B21-A language')
    return p


def request(kind, index, seed, policy, measured, history, accepted=()):
    if kind not in ('b20', 'random', 'balanced') or not 0 <= index < ROUNDS:
        raise ValueError('unknown search or slot')
    rows = measured['rows']; require_development(rows)
    archive.entries(policy, history)
    if kind == 'b20':
        return baseline.request('new', index, policy, measured, list(accepted)+history)
    plan = agenda(seed)[index]
    target = None; coverage = {}; ranking = []
    if kind == 'random':
        mode = 'general' if rng(seed, index, 'distribution').randrange(2) else 'diversity'
        value = rng(seed, index, 'uniform-duration').choice(VALUES)
        # The random control has no loss/gain feedback or adaptive exposure.
        guard, coverage = (general_guard(seed, index), {}) if mode == 'general' else diversity_guard(seed, index, rows, policy, history, adaptive=False)
        plan = dict(slot=index+1, phase='random', mode=mode, value=value)
    else:
        if plan['phase'] == 'repair':
            target = archive.parent(policy, history, plan['objective'])
        if target is not None:
            old = target['proposal']['patches'][0]
            if plan['mode'] == 'duration':
                proposals = [{'patches':[{'when':old['when'], 'set':{'HOLD':v}}]} for v in VALUES if v != old['set']['HOLD']]
            else:
                guards, coverage = baseline.pool(rows, history, policy)
                draws = rng(seed, index, 'repair-sample')
                guards.extend(sample_guard(draws) for _ in range(REPAIR_POOL))
                proposals = [{'patches':[{'when':g, 'set':dict(old['set'])}]} for g in guards if g != old['when']]
            used = {canonical(e['proposal']) for e in history if e.get('proposal')}
            for proposal in {canonical(p):p for p in proposals}.values():
                if canonical(proposal) in used:continue
                metrics = archive.repair_score(proposal, target, policy, history)
                ranking.append(dict(proposal=proposal, **metrics))
            ranking.sort(key=lambda x:(x['predicted_gain_coverage']<2, x['associated_loss_contexts'],
                                       -x['predicted_gain_coverage'], sha([seed,index,x['proposal']])))
        if ranking:
            guard = ranking[0]['proposal']['patches'][0]['when']
            value = ranking[0]['proposal']['patches'][0]['set']['HOLD']
        else:
            if target is not None or plan['phase']=='repair':
                plan = dict(plan, fallback='no legal untried repair; explore', mode='general')
                target = None
            counts = Counter(e['proposal']['patches'][0]['set']['HOLD'] for e in history if e.get('proposal'))
            value = plan.get('value')
            if value is None:
                least = min(counts[v] for v in VALUES)
                value = rng(seed,index,'least-duration').choice([v for v in VALUES if counts[v]==least])
            guard, coverage = (general_guard(seed,index),{}) if plan['mode']=='general' else diversity_guard(seed,index,rows,policy,history)
    proposal = validate_proposal({'patches':[{'when':guard,'set':{'HOLD':value}}]})
    shortlist = ranking[:8] if ranking else [dict(proposal=proposal)]
    return dict(id=index+1, type='REFINE' if target else 'WAIT', target_id=target['id'] if target else None,
                requested_operator='HOLD', operator_binding=True, selection_mode='B21-A-'+kind,
                schedule=plan, search_seed=seed, proposal=proposal, shortlist=shortlist,
                guard_schema=dict(version=11,origin='DEVELOPMENT_A',excluded=[],
                                  groups=[dict(parameter='HOLD',value=value,guards=[guard])]),
                coverage=coverage, model_call_required=False, prompt_variants=[],
                evidence=baseline.guard_search.feedback(target),
                input_sha256=sha(dict(policy=policy,rows=rows,history=history)),
                reason='seeded joint coverage / measured counterexamples; judge remains external')


def answer(request):
    return canonical(request.get('proposal') or (request['shortlist'][0]['proposal'] if request['shortlist'] else {'patches':[]}))


def from_bytes(data):
    """The investigator's entire data surface; no filesystem, model or evaluator."""
    obj=json.loads(data)
    if set(obj)!={'policy','base','own_history','accepted_history','kind','index','seed'}:
        raise ValueError('unexpected investigator input surface')
    return request(obj['kind'],obj['index'],obj['seed'],obj['policy'],obj['base'],
                   obj['own_history'],obj['accepted_history'])
