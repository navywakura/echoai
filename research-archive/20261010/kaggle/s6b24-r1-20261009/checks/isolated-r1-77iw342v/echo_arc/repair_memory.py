"""Development-only experiment memory and evidence selection for ECHO.

Receipts are observations, not a model's hidden reasoning. Protected outcomes
are represented only by the allowed rejection bit; protected cases never enter.
"""
from bisect import bisect_right
from functools import lru_cache

from echo_arc import stale_transition as patch
from echo_arc.contrastive_evidence import require_development
from echo_arc.contrastive_grammar import choices, witnesses
from echo_arc.feasible_grammar import canonical, matches
from echo_arc.precise_patch_grammar import conditions
from seed.game_selfimprove import sha

FEATURES = tuple(sorted(patch.FEATURES))
KINDS = ('CONTRADICTION', 'WAIT', 'GENERALIZE')


def receipt(event):
    if event is None:
        return None
    d = event.get('development', {})
    if d and d.get('origin') != 'DEVELOPMENT_A':
        raise ValueError('protected receipt evidence forbidden')
    return dict(attempt=event['id'], proposal=event.get('proposal'), verdict=event['verdict'],
                gain=event.get('A', {}).get('gain', 0), losses=d.get('losses', 0),
                protected_rejection=event['verdict'] == 'V4',
                same_as=event.get('equivalent_calls', []))


def root_id(event, history):
    lookup = {e['id']: e for e in history}
    seen = set()
    while event.get('target_id') is not None:
        if event['id'] in seen:
            raise ValueError('cyclic refinement lineage')
        seen.add(event['id'])
        parent = lookup.get(event['target_id'])
        if parent is None or parent.get('base_sha256') != event.get('base_sha256'):
            break
        event = parent
    return event['id']


def target_for(current, history):
    own = [e for e in history if e.get('base_sha256') == sha(current)]
    candidates = [e for e in own if e.get('target_id') is None and e.get('proposal')
                  and e['verdict'] in ('V3', 'V4') and e.get('A', {}).get('gain', 0) > 0]
    candidates = [e for e in candidates if sum(x.get('target_id') is not None and
                   root_id(x, own) == e['id'] for x in own) < 3]
    # End a fruitless refinement streak after an actually observed repeat.
    if own and cooldown(current, own) and own[-1].get('target_id') is not None:
        stalled = root_id(own[-1], own)
        candidates = [e for e in candidates if e['id'] != stalled]
    if not candidates:
        return None
    active = root_id(own[-1], own) if own and own[-1].get('target_id') is not None else None
    return next((e for e in candidates if e['id'] == active),
                max(candidates, key=lambda e: (e['A']['gain'],
                    -e.get('development', {}).get('losses', 0), -e['id'])))


def statistics(history):
    result = {k: dict(trials=0, accepted_gain=0, repeated=0) for k in KINDS}
    lookup = {e['id']: e for e in history}
    for e in history:
        source = lookup.get(root_id(e, history), e)
        kind = source.get('type')
        if kind in result:
            result[kind]['trials'] += 1
            result[kind]['accepted_gain'] += max(0, e.get('A', {}).get('gain', 0)) if e['verdict'] == 'accepted' else 0
            result[kind]['repeated'] += bool(e.get('equivalent_calls'))
    return result


def signal(row, kind):
    d = row['diagnostics']
    if kind == 'CONTRADICTION':
        return d['counts'].get('contradictory_noop', 0)
    if kind == 'WAIT':
        return sum(w['count'] for w in d['consumers'] if w['parameter'] == 'HOLD') + sum(
            w['count'] for w in d['feature_counts'] if w['features']['hold_remaining'] > 0)
    return sum(len(ws) for ws in witnesses([row]).values())


def cooldown(current, history):
    """One-call exploration heuristic, not a proof about untested guard scopes."""
    if not history:
        return []
    latest = history[-1]
    if latest.get('base_sha256') != sha(current) or latest['verdict'] not in ('V3', 'V4') \
            or not latest.get('proposal') or not latest.get('development'):
        return []
    setting = latest['proposal']['patches'][0]['set']
    fingerprint = latest['development']['behavior_sha256']
    repeated = any(e.get('base_sha256') == sha(current) and e['verdict'] in ('V3', 'V4')
                   and e.get('proposal') and e['proposal']['patches'][0]['set'] == setting
                   and e.get('development', {}).get('behavior_sha256') == fingerprint
                   for e in history[:-1])
    return [dict(setting)] if repeated else []


def apply_cooldown(schema, current, history):
    paused = cooldown(current, history)
    groups, excluded = [], 0
    for parameter, value, guards in choices(schema):
        if {parameter: value} in paused:
            excluded += len(guards)
        else:
            groups.append(dict(parameter=parameter, value=value, guards=guards))
    # Do not force abstention solely because a heuristic emptied the language.
    return dict(schema, groups=groups if groups else schema['groups'],
                diversity_cooldown=paused, cooldown_exclusions=excluded if groups else 0)


def select(rows, arm, current, history, index):
    require_development(rows)
    failing = [i for i, r in enumerate(rows) if r['levels_completed'] < 5]
    if arm == 'fijo':
        order = sorted(failing, key=lambda i: (rows[i]['levels_completed'], i))
        selected = (order + [i for i in range(len(rows)) if i not in order])[:3]
        return selected, 'GENERIC', None, {}
    if arm != 'echo':
        raise ValueError('unknown arm')
    pools = {k: [i for i in (list(range(len(rows))) if k == 'GENERALIZE' else failing)
                 if signal(rows[i], k) > 0] for k in KINDS}
    available = [k for k in KINDS if pools[k]]
    stats = statistics(history)  # All attempts count, including expired targets.
    untried = [k for k in available if stats[k]['trials'] == 0]
    target = target_for(current, history)
    if not untried and target:
        selected = list(dict.fromkeys(c['case_index'] for c in target['development']['contrasts']))[:3]
        for i in sorted(range(len(rows)), key=lambda i: (rows[i]['levels_completed'], i)):
            if len(selected) >= 3:
                break
            if i not in selected:
                selected.append(i)
        return selected, 'REFINE', target, stats
    if not available:
        return list(range(min(3, len(rows)))), 'NO_SIGNAL', None, stats
    focus = untried[0] if untried else max(available, key=lambda k:
        ((stats[k]['accepted_gain'] + 2) /
         (stats[k]['trials'] + stats[k]['repeated'] + 1), -KINDS.index(k)))
    order = sorted(pools[focus], key=lambda i: (rows[i]['levels_completed'], -signal(rows[i], focus), i))
    offset = stats[focus]['trials'] % len(order)
    # Rotate only inside the evidence-bearing pool; never pad with irrelevant cases.
    selected = (order[offset:] + order[:offset])[:3]
    return selected, focus, None, stats


@lru_cache(maxsize=1)
def cutpoints():
    cuts = {k: {lo} for k, (lo, hi) in patch.FEATURES.items()}
    for guard in conditions():
        for k, (_, n) in guard.items():
            lo, hi = patch.FEATURES[k]
            cuts[k].update(x for x in (n, n + 1) if lo <= x <= hi)
    return {k: tuple(sorted(v)) for k, v in cuts.items()}


def case_identity(rows):
    return sha([[r[k] for k in ('version', 'seed', 'rep', 'budget')] for r in rows])


def certificate(rows, base, candidate):
    """All candidate A decisions, partitioned without changing any legal guard.

    This is not a signature of the base's opportunities: it covers the entire
    measured candidate trajectory. It is usable only for a same-base V3 failure.
    """
    require_development(rows)
    points, decisions = set(), 0
    cuts = cutpoints()
    for row in rows:
        trajectory = row['diagnostics']['trajectory']
        if tuple(trajectory['features']) != FEATURES:
            raise ValueError('unexpected trace columns')
        if len(trajectory['steps']) != len(row['actions']):
            raise ValueError('unaligned trace')
        for step in trajectory['steps']:
            if step is None:
                continue
            features = step['f']
            if len(features) != len(FEATURES):
                raise ValueError('missing decision features')
            reduced = []
            for k, value in zip(FEATURES, features, strict=True):
                lo, hi = patch.FEATURES[k]
                if type(value) is not int or not lo <= value <= hi:
                    raise ValueError('invalid decision feature')
                reduced.append(cuts[k][bisect_right(cuts[k], value) - 1])
            points.add(tuple(reduced))
            decisions += 1
    if not points or not decisions:
        raise ValueError('empty decision certificate')
    value = dict(version=1, origin='DEVELOPMENT_A', features=list(FEATURES),
                 points=[list(p) for p in sorted(points)], decisions=decisions,
                 cases_sha256=case_identity(rows), base_sha256=sha(base),
                 candidate_sha256=sha(candidate), guard_library_sha256=sha(conditions()))
    return dict(value, sha256=sha(value))


def prune_repeated_failures(schema, rows, current, history):
    """Exclude only guards proven to replay a prior same-base V3 failure on A.

    V4 failures are deliberately excluded from this exclusion rule: identical A
    behavior does not imply identical protected behavior, which may be repaired.
    """
    require_development(rows)
    prior = []
    for e in history:
        cert = e.get('decision_certificate')
        if e.get('verdict') != 'V3' or e.get('base_sha256') != sha(current) or not cert:
            continue
        if cert['sha256'] != sha({k: v for k, v in cert.items() if k != 'sha256'}) \
                or cert['cases_sha256'] != case_identity(rows) or cert['base_sha256'] != sha(current) \
                or cert['candidate_sha256'] != sha(e['candidate']) \
                or cert['guard_library_sha256'] != sha(conditions()) \
                or cert['origin'] != 'DEVELOPMENT_A' or tuple(cert['features']) != FEATURES \
                or not cert['points'] or cert['decisions'] <= 0 \
                or e['candidate']['program'] != patch.append(current['program'], e['proposal']):
            raise ValueError('invalid development equivalence certificate')
        item = e['proposal']['patches'][0]
        parameter, value = next(iter(item['set'].items()))
        points = [dict(zip(FEATURES, p, strict=True)) for p in cert['points']]
        atoms = {}
        def signature(guard, points=points, atoms=atoms):
            mask = (1 << len(points)) - 1
            for k, test in guard.items():
                atom = (k, *test)
                if atom not in atoms:
                    bits = bytearray((len(points) + 7) // 8)
                    for i, f in enumerate(points):
                        if matches({k: test}, f):
                            bits[i // 8] |= 1 << (i % 8)
                    atoms[atom] = int.from_bytes(bits, 'little')
                mask &= atoms[atom]
            return mask
        prior.append((parameter, value, signature, signature(item['when'])))
    groups, excluded = [], 0
    for parameter, value, guards in choices(schema):
        checks = [(sig, old) for p, v, sig, old in prior if (p, v) == (parameter, value)]
        kept = [g for g in guards if not any(sig(g) == old for sig, old in checks)]
        excluded += len(guards) - len(kept)
        if kept:
            groups.append(dict(parameter=parameter, value=value, guards=kept))
    return dict(schema, groups=groups, equivalent_V3_exclusions=excluded)
