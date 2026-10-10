"""B15 experiment selection from measured development operations, not labels.

An applicability witness proves only that a setting can change at a read. The
resulting action sequence and utility still have to be measured by the verifier.
"""
from collections import Counter

from echo_arc import repair_memory as memory
from echo_arc.contrastive_evidence import require_development
from echo_arc.contrastive_grammar import PARAMETERS, witnesses
from echo_arc.feasible_grammar import canonical

FAMILY = {'REVALIDATE_NOOP': 'prediction', 'HOLD': 'waiting', 'COOLDOWN_CAP': 'waiting'}
FOCUS = {'REVALIDATE_NOOP': 'CONTRADICTION', 'HOLD': 'WAIT', 'COOLDOWN_CAP': 'WAIT'}


def operator(event):
    items = (event.get('proposal') or {}).get('patches', [])
    if len(items) != 1 or len(items[0]['set']) != 1:
        return None
    value = next(iter(items[0]['set']))
    return value if value in PARAMETERS else None


def measured(event):
    d = event.get('development', {})
    if d and d.get('origin') != 'DEVELOPMENT_A':
        raise ValueError('protected evidence cannot drive experiment selection')
    return operator(event) is not None and bool(event.get('A')) and bool(d)


def statistics(current, history):
    result = {p: dict(measured_total=0, measured_on_base=0, changed_total=0,
                      repeated_on_base=0, losses_on_base=0, residual_gain=0) for p in PARAMETERS}
    base = memory.sha(current)
    for event in history:
        if not measured(event):
            continue
        entry = result[operator(event)]
        entry['measured_total'] += 1
        entry['changed_total'] += int(event['development'].get('changed_games', 0) > 0)
        if event.get('base_sha256') != base:
            continue
        entry['measured_on_base'] += 1
        entry['repeated_on_base'] += int(bool(event.get('equivalent_calls')))
        entry['losses_on_base'] += event['development'].get('losses', 0)
        # Accepted gains belong to an older base after promotion. Rejected gain
        # remains a refinement opportunity, not an accepted performance claim.
        entry['residual_gain'] = max(entry['residual_gain'], max(0, event['A'].get('gain', 0)))
    return result


def paused_family(current, history):
    """One next-call family pause after two fruitless same-base measurements."""
    if len(history) < 2:
        return None
    a, b = history[-2:]
    if not all(measured(e) and e.get('base_sha256') == memory.sha(current)
               and e['verdict'] in ('V3', 'V4') for e in (a, b)):
        return None
    if FAMILY[operator(a)] != FAMILY[operator(b)]:
        return None
    repeat = a['development'].get('behavior_sha256') == b['development'].get('behavior_sha256')
    if repeat or all(e['A'].get('gain', 0) <= 0 for e in (a, b)):
        return FAMILY[operator(b)]
    return None


def target_for(current, history, available):
    own = [e for e in history if e.get('base_sha256') == memory.sha(current)]
    candidates = [e for e in own if measured(e) and operator(e) in available
                  and e.get('target_id') is None and e['verdict'] in ('V3', 'V4')
                  and e['A'].get('gain', 0) > 0
                  and sum(x.get('target_id') is not None and memory.root_id(x, own) == e['id']
                          for x in own) < 3]
    return max(candidates, key=lambda e: (e['A']['gain'], -e['development'].get('losses', 0),
                                         -e['id']), default=None)


def select(rows, arm, current, history, index):
    require_development(rows)
    if arm not in ('echo', 'fijo'):
        raise ValueError('unknown arm')
    observations = [witnesses([r]) for r in rows]
    pools = {p: [i for i, w in enumerate(observations) if w[p]] for p in PARAMETERS}
    available = [p for p in PARAMETERS if pools[p]]
    pause = paused_family(current, history)
    unpaused = [p for p in available if FAMILY[p] != pause]
    # A heuristic must not empty the available language.
    if unpaused:
        available = unpaused
    else:
        pause = None
    stats = statistics(current, history)
    if not available:
        return dict(selected=[], parameter=None, focus='NO_SIGNAL', target=None,
                    statistics=stats, paused_family=pause)
    target = None
    if arm == 'fijo':
        cycle = PARAMETERS[index % len(PARAMETERS):] + PARAMETERS[:index % len(PARAMETERS)]
        parameter = next(p for p in cycle if p in available)
    else:
        untried = [p for p in available if stats[p]['measured_total'] == 0]
        target = target_for(current, history, available) if not untried else None
        if untried:
            parameter = untried[0]
        elif target:
            parameter = operator(target)
        else:
            def priority(p):
                s = stats[p]
                return ((2 + s['residual_gain']) / (1 + s['measured_on_base'] +
                        s['repeated_on_base'] + s['losses_on_base']), -PARAMETERS.index(p))
            parameter = max(available, key=priority)
    def signal(i):
        counts = rows[i]['diagnostics']['counts']
        return counts.get('contradictory_noop' if parameter == 'REVALIDATE_NOOP'
                          else 'wait_without_progress', 0)
    order = sorted(pools[parameter], key=lambda i: (rows[i]['levels_completed'],
                    -signal(i) if arm == 'echo' else 0, i))
    selected = []
    if target:
        selected = [c['case_index'] for c in target['development']['contrasts']
                    if c['case_index'] in order]
    # Retain evidence-bearing cases; no rotation into an unrelated mechanism.
    selected = list(dict.fromkeys(selected + order))[:3]
    return dict(selected=selected, parameter=parameter, focus='REFINE' if target else FOCUS[parameter],
                target=target, statistics=stats, paused_family=pause)


def numeric_points(points, limit):
    """Actual joint observations, numeric extrema first, then stable order.

    Per-feature ranges are descriptive marginals, never invented joint points.
    Omitted extrema remain visible in ranges even when the point budget is small.
    """
    if not points or limit <= 0:
        return []
    ordered = sorted(points, key=lambda w: tuple(w['features'][k] for k in memory.FEATURES))
    varying = [k for k in memory.FEATURES if len({w['features'][k] for w in ordered}) > 1]
    extrema = []
    for k in varying:
        extrema += [min(ordered, key=lambda w: w['features'][k]), max(ordered, key=lambda w: w['features'][k])]
    selected = []
    for w in extrema + ordered:
        if canonical(w) not in {canonical(x) for x in selected}:
            selected.append(w)
        if len(selected) == limit:
            break
    return selected


def case_data(rows, parameter, point_limit=4, numeric=True):
    require_development(rows)
    result = []
    for index, row in enumerate(rows):
        points = witnesses([row]).get(parameter, [])
        if numeric:
            selected = numeric_points(points, point_limit)
        else:
            old = sorted(points, key=lambda w: (w['features']['stagnation'], canonical(w)))
            selected = list({canonical(w): w for w in old[:1] + old[-1:]}.values())[:point_limit]
        constant = {k: points[0]['features'][k] for k in memory.FEATURES
                    if points and len({w['features'][k] for w in points}) == 1}
        columns = [k for k in memory.FEATURES if k not in constant] if points else []
        summary = dict(constant=constant, columns=columns,
                       points=[[w['features'][k] for k in columns] for w in selected],
                       sampled_joint_points=len(selected), total_joint_points=len(points))
        # The ablation's old summary deliberately omits the new range/frequency
        # evidence. This condition is calibration only, never the main pilot.
        if numeric:
            d = row['diagnostics']
            readings = (d['consumers'] if parameter == 'HOLD' else d['contradiction_features']
                        if parameter == 'REVALIDATE_NOOP' else d['feature_counts'])
            frequencies = Counter()
            for w in readings:
                if parameter == 'HOLD' and w['parameter'] != 'HOLD':
                    continue
                if parameter == 'COOLDOWN_CAP' and w['features']['hold_remaining'] <= 0:
                    continue
                frequencies[tuple(w['features'][k] for k in memory.FEATURES)] += w.get('count', 1)
            summary['ranges'] = {k: [min(w['features'][k] for w in points),
                                       max(w['features'][k] for w in points)] for k in columns}
            summary['frequencies'] = [frequencies[tuple(w['features'][k] for k in memory.FEATURES)]
                                      for w in selected]
        result.append(dict(case=index, levels=row['levels_completed'],
            counts={k: row['diagnostics']['counts'].get(k, 0) for k in
                    ('contradictory_noop', 'wait_without_progress', 'progress')},
            operator=parameter, observations=summary))
    return result
