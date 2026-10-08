"""Bounded investigator archive. Rejected hypotheses never become stable policy."""
from collections import Counter

from seed.game_selfimprove import sha

LIMIT = 32


def entries(policy, history):
    if len(history) > LIMIT:
        raise ValueError('investigator archive budget exceeded')
    result = []
    for event in history:
        if event.get('base_sha256') != sha(policy):
            raise ValueError('foreign investigator base')
        d = event.get('development')
        if d is None:
            continue
        if d.get('origin') != 'DEVELOPMENT_A':
            raise ValueError('protected investigator evidence')
        if d.get('consumer_parameter') != 'HOLD':
            raise ValueError('unexpected mechanism')
        effects = d['case_effects']
        result.append(dict(event=event, id=event['id'],
            gain=sum(x['level_delta'] for x in effects),
            losses=sum(x['level_delta'] < 0 or x['score_delta'] < -1e-10 for x in effects),
            worst_level=min(x['level_delta'] for x in effects),
            worst_score=min(x['score_delta'] for x in effects),
            signature=sha([(x['case_index'], x['level_delta']) for x in effects if x['level_delta'] > 0]),
            proposal_sha256=sha(event['proposal']),
            trajectory_sha256=event.get('trajectory_sha256'),
            consumption_sha256=sha(d['candidate_consumers'])))
    return result


def parent(policy, history, objective):
    archive = entries(policy, history)
    children = Counter(e.get('target_id') for e in history)
    eligible = [x for x in archive if children[x['id']] < 2 and
                x['event']['development'].get('gross_level_gain', 0) > 0]
    if not eligible:
        return None
    if objective not in ('repair-loss', 'increase-gain'):
        raise ValueError('unknown repair objective')
    preferred = ([x for x in eligible if x['gain'] >= 2 and x['losses'] > 0]
                 if objective == 'repair-loss' else
                 [x for x in eligible if x['gain'] > 0 and x['losses'] == 0])
    pool = preferred or eligible
    family_use = Counter()
    by_id = {x['id']: x for x in archive}
    for e in history:
        if e.get('target_id') in by_id:
            family_use[by_id[e['target_id']]['signature']] += 1
    chosen = min(pool, key=lambda x: (family_use[x['signature']], children[x['id']],
                                     x['losses'], -x['gain'], -x['worst_score'], x['id']))
    return chosen['event']


def repair_score(proposal, target, policy, history):
    """Rank empirical counterexamples; zero burden is never a safety proof."""
    guard = proposal['patches'][0]['when']
    value = proposal['patches'][0]['set']['HOLD']
    from echo_arc.feasible_grammar import matches, canonical
    from seed.s6b13_prompt import effective
    from echo_arc.repair_memory import root_id
    events = [x['event'] for x in entries(policy, history)]
    root = root_id(target, events)
    related = [e for e in events if root_id(e, events) == root]
    gain = 0
    for effect in target['development']['case_effects']:
        if effect['level_delta'] > 0:
            reads = target['development']['candidate_consumers'][effect['case_index']]
            if any(matches(guard, r['features']) and
                   r['value'] != effective('HOLD', r['features'], policy) for r in reads):
                gain += effect['level_delta']
    loss_contexts = set()
    for e in related:
        if e['proposal']['patches'][0]['set']['HOLD'] != value:
            continue
        for effect in e['development']['case_effects']:
            if effect['level_delta'] < 0 or effect['score_delta'] < -1e-10:
                for r in e['development']['candidate_consumers'][effect['case_index']]:
                    if r['value'] != effective('HOLD', r['features'], policy) and matches(guard, r['features']):
                        loss_contexts.add(canonical(r['features']))
    return dict(predicted_gain_coverage=gain, associated_loss_contexts=len(loss_contexts),
                attribution='association within value/lineage; requires full simulation')
