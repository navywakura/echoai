"""B16: preserve local level gains in feedback without weakening acceptance.

These are empirical development contrasts, not causal certificates. A locally
useful rejected proposal may be refined; aggregate V3 and protected V4 remain
unchanged and still reject every individual regression.
"""
from itertools import zip_longest

from echo_arc import contrastive_evidence as original
from echo_arc import repair_experiments as experiments, repair_memory as memory
from echo_arc.contrastive_grammar import witnesses


def comparison(before, after):
    value = original.comparison(before, after)  # Pairing and origin validation.
    pairs = list(zip(before['rows'], after['rows'], strict=True))
    delta = [a['levels_completed'] - b['levels_completed'] for b, a in pairs]
    score_delta = [a['score'] - b['score'] for b, a in pairs]
    losses = sorted([i for i in range(len(pairs)) if delta[i] < 0 or score_delta[i] < -1e-10],
                    key=lambda i: (delta[i], score_delta[i], i))
    level_gains = sorted([i for i, d in enumerate(delta) if d > 0], key=lambda i: (-delta[i], i))
    score_gains = sorted([i for i, d in enumerate(score_delta) if d > 1e-10], key=lambda i: (-score_delta[i], i))
    changed = [i for i, (b, a) in enumerate(pairs) if b['actions'] != a['actions']]
    # The highest local level gain always appears within the first two items.
    # A score-only improvement in an already solved task cannot displace it.
    selected = list(dict.fromkeys(losses[:1] + level_gains[:1] + losses[1:2] +
                                 level_gains[1:] + score_gains + changed))[:3]
    contrasts = []
    for i in selected:
        b, a = pairs[i]
        first = next((n for n, (x, y) in enumerate(zip_longest(b['actions'], a['actions'])) if x != y), None)
        item = dict(case_index=i, effect='loss' if i in losses else 'gain' if delta[i] > 0 or score_delta[i] > 1e-10 else 'changed',
                    levels=[b['levels_completed'], a['levels_completed']], score=[b['score'], a['score']],
                    level_gain=max(0, delta[i]), level_loss=max(0, -delta[i]),
                    actions_per_level=[b['actions_per_level'], a['actions_per_level']],
                    first_different_action=first, sequence=[])
        if first is not None:
            item['sequence'] = [dict(before=original.step(b, n), candidate=original.step(a, n))
                                for n in range(max(0, first-1), first+1)]
        contrasts.append(item)
    return dict(value, contrasts=contrasts, gross_level_gain=sum(max(0, d) for d in delta),
                gross_level_loss=sum(max(0, -d) for d in delta), level_gain_cases=len(level_gains))


def target_for(current, history, available):
    own = [e for e in history if e.get('base_sha256') == memory.sha(current)]
    candidates = [e for e in own if experiments.measured(e) and experiments.operator(e) in available
        and e.get('target_id') is None and e['verdict'] in ('V3', 'V4')
        and e['development'].get('gross_level_gain', 0) > 0
        and sum(x.get('target_id') is not None and memory.root_id(x, own) == e['id'] for x in own) < 3]
    return max(candidates, key=lambda e: (e['development']['gross_level_gain'],
                -e['development'].get('gross_level_loss', 0), -e['development']['losses'], -e['id']), default=None)


def select(rows, arm, current, history, index):
    selection = experiments.select(rows, arm, current, history, index)
    if arm != 'echo':
        return selection
    observations = [witnesses([row]) for row in rows]
    available = [p for p in experiments.PARAMETERS if any(o[p] for o in observations)
                 and experiments.FAMILY[p] != selection['paused_family']]
    target = target_for(current, history, available)
    if target is None:
        return selection
    parameter = experiments.operator(target)
    pool = [i for i, o in enumerate(observations) if o[parameter]]
    selected = [c['case_index'] for c in target['development']['contrasts'] if c['case_index'] in pool]
    selected = list(dict.fromkeys(selected + sorted(pool, key=lambda i: (rows[i]['levels_completed'], i))))[:3]
    # A promising measured local gain receives a bounded repair opportunity
    # before cold-start exploration of another operator. Family pauses still apply.
    return dict(selection, parameter=parameter, selected=selected, focus='REFINE', target=target)


def contrasts(event, limit=2):
    """Named feature values, lossless delta encoding for the paired observation.

    Reconstructed values must be exactly the recorded first-divergence values.
    No protected examples, world IDs, coordinates or suggested guard are added.
    """
    if not event:
        return []
    d = event.get('development', {})
    if d.get('origin') != 'DEVELOPMENT_A':
        raise ValueError('only development contrasts allowed')
    result = []
    for c in d['contrasts'][:limit]:
        sequence = []
        for pair in c['sequence'][-1:]:
            b, a = pair['before'], pair['candidate']
            if b and a and 'features' in b and 'features' in a:
                sequence.append(dict(before=b, candidate=dict(
                    feature_changes={k: v for k, v in a['features'].items() if b['features'][k] != v},
                    action=a['action'], outcome=a['outcome'])))
            else:
                sequence.append(dict(before=b, candidate=a))
        result.append(dict(effect=c['effect'], levels=c['levels'], score=c['score'], sequence=sequence))
    return result
