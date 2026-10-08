"""A smaller, witnessed repair question; protected feedback stays a boolean."""
from echo_arc import stale_transition as patch
from echo_arc.feasible_grammar import build_schema, canonical, public_features
from echo_arc.repair_loop_requests import feedback


def select(rows, arm):
    if arm not in ('echo', 'fijo') or any(r['origin'] != 'DEVELOPMENT_A' for r in rows):
        raise ValueError('development-only paired request')
    failing = [(i, row) for i, row in enumerate(rows) if row['levels_completed'] < 5]
    if arm == 'fijo':
        selected = sorted(failing, key=lambda pair: (pair[1]['levels_completed'], pair[0]))
    else:
        selected = sorted(failing, key=lambda pair: (
            -bool(pair[1]['diagnostics']['contradiction_features']), -pair[1]['levels_completed'],
            -pair[1]['diagnostics']['counts'].get('contradictory_noop', 0), pair[0]))
    return [row for _, row in selected[:3]]


def requests(arm, round_id, count, current, measured, history):
    selected = select(measured['rows'], arm)
    schema = build_schema(selected, history)
    cases = []
    for index, row in enumerate(selected):
        witnesses = row['diagnostics']['contradiction_features']
        features = [public_features(w['features']) for w in witnesses]
        ranges = {key: [min(f[key] for f in features), max(f[key] for f in features)]
                  for key in patch.FEATURES} if features else {}
        # First/last by stagnation are actual joint observations. Ranges alone
        # are not treated as evidence of an unobserved combination of features.
        ordered = sorted(features, key=lambda f: (f['stagnation'], canonical(f)))
        examples = [ordered[0], ordered[-1]] if len(ordered) > 1 else ordered
        cases.append({'case': index, 'levels': row['levels_completed'],
                      'contradictions': sum(w['count'] for w in witnesses),
                      'feature_ranges': ranges, 'joint_observations': examples})
    prompt = ('Propose one JSON repair: {"patches":[{"set":{"REVALIDATE_NOOP":N},"when":{FEATURE:[OP,INT]}}]}. '
              'N is 1..8, OP eq/ge/le, one to three AND conditions. The operation revises a prediction '
              'of movement to a self-loop after N observed no-change contradictions under the condition; '
              'it clears the queued plan. Later movement can replace that prediction. Historical facts '
              'are retained. No revision on GAME OVER or level change. '
              'The decoder permits only conditions matching an actual joint contradiction observation '
              'in these cases, excludes disabled N=0 and your exact previous proposals. This mechanical '
              'check does not prove consecutive evidence, changed actions, usefulness or safety against '
              'regression. If no eligible condition remains, return {"patches":[]}. '
              'Need >=2 extra training levels, no individual training or protected level/score loss. '
              'Feature ranges do not imply every combination was observed. '
              'Current accepted program: ' + canonical(current['program']) + '. '
              'Your own measured attempts: ' + canonical(feedback(history)) + '. ')
    if arm == 'echo':
        prompt += ('ECHO selected unresolved transition contradictions, prioritizing cases close to success. '
                   'Repair that observed failure. If an earlier repair gained levels but was rejected, '
                   'refine its scope or evidence threshold. If it changed no actions, change the repair. ')
    else:
        prompt += 'Here are three incomplete tasks. Propose a general repair that helps solve them. '
    prompt += 'Protected rejection gives no private details. Observations: ' + canonical(cases) + '. Return JSON only.'
    return [{'id': round_id * count + offset, 'type': 'FEASIBLE_TRANSITION' if arm == 'echo' else 'GENERIC',
             'prompt': prompt, 'guard_schema': schema} for offset in range(count)]
