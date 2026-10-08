"""Adaptive evidence selection versus a fixed generic request, equal interfaces."""
from echo_arc import stale_transition as patch
from echo_arc.contrastive_evidence import feedback, require_development
from echo_arc.contrastive_grammar import build_schema, witnesses
from echo_arc.feasible_grammar import canonical


def select(rows, arm, history, index):
    require_development(rows)
    if arm not in ('echo', 'fijo'):
        raise ValueError('unknown arm')
    failing = [i for i, row in enumerate(rows) if row['levels_completed'] < 5]
    if arm == 'fijo':
        order = sorted(failing, key=lambda i: (rows[i]['levels_completed'], i))
        return [rows[i] for i in (order + [i for i in range(len(rows)) if i not in order])[:3]], 'GENERIC'
    # Refine with own development counterexamples; protected data are absent.
    useful = [e for e in history if e.get('A', {}).get('gain', 0) > 0 and e['verdict'] != 'accepted']
    chosen = []
    if useful:
        best = max(useful, key=lambda e: (e['A']['gain'], e['id']))
        chosen = [c['case_index'] for c in best.get('development', {}).get('contrasts', [])]
        focus = 'REFINE'
    else:
        # Deterministic empirical request scheduling: untried mechanisms first,
        # then accepted A gain per attempt plus diminishing exploration.
        kinds = ('CONTRADICTION', 'WAIT', 'GENERALIZE')
        def priority(kind):
            trials = [e for e in history if e.get('type') == kind]
            gain = sum(max(0, e.get('A', {}).get('gain', 0)) for e in trials if e['verdict'] == 'accepted')
            return (gain + 2) / (len(trials) + 1)
        focus = max(kinds, key=lambda k: (priority(k), -kinds.index(k)))
    def signal(i):
        d = rows[i]['diagnostics']
        if focus == 'WAIT':
            return sum(c['count'] for c in d['consumers'] if c['parameter'] == 'HOLD')
        return d['counts'].get('contradictory_noop', 0)
    pool = failing if focus != 'GENERALIZE' else list(range(len(rows)))
    order = sorted(pool, key=lambda i: (-bool(signal(i)), -rows[i]['levels_completed'], -signal(i), i))
    # Rotate tie/ranked evidence even when every previous repair was rejected.
    if order:
        offset = index % len(order)
        order = order[offset:] + order[:offset]
    chosen = list(dict.fromkeys(chosen + order + list(range(len(rows)))))[:3]
    return [rows[i] for i in chosen], focus


def cases(rows):
    output = []
    for i, row in enumerate(rows):
        evidence = witnesses([row])
        examples = {}
        for parameter, ws in evidence.items():
            ordered = sorted(ws, key=lambda w: (w['features']['stagnation'], canonical(w)))
            examples[parameter] = list({canonical(w): w for w in (ordered[:1] + ordered[-1:])}.values())
        output.append({'case': i, 'levels': row['levels_completed'],
                       'counts': {k: row['diagnostics']['counts'].get(k, 0)
                                  for k in ('contradictory_noop', 'wait_without_progress', 'progress')},
                       'observed_control_opportunities': examples})
    return output


def requests(arm, round_id, count, current, measured, history):
    result = []
    for offset in range(count):
        index = round_id * count + offset
        selected, focus = select(measured['rows'], arm, history, index)
        prompt = (
            'Propose ONE bounded JSON repair: {"patches":[{"set":{PARAM:INT},"when":{FEATURE:[OP,INT]}}]}. '
            'One control, one to three AND conditions, OP eq/ge/le. Need >=2 additional development levels '
            'with no individual development or protected level/score loss. The three available controls are '
            'REVALIDATE_NOOP 1..8: revise a movement prediction to a self-loop after N observed no-change '
            'contradictions under the guard and clear its plan; later movement can restore that prediction. '
            'HOLD: set future waits when a known reset key is tried, not a wait already running. '
            'COOLDOWN_CAP: clamp an existing wait, only affects it below the remaining wait. '
            'Wait limits ' + canonical({p: patch.LIMITS[p] for p in ('HOLD', 'COOLDOWN_CAP')}) + '. '
            'Observable features ' + canonical(patch.FEATURES) + '. '
            'Grammar permits only guards compatible with a joint development observation at a relevant '
            'control opportunity, excludes inert values there and your exact previous proposals. '
            'This does not predict usefulness. Different programs can have identical measured behavior. '
            'A broad guard can alter useful plans or useful waiting. Use actual contrasts, not guessed '
            'private causes. Contrasts show first action divergence and measured outcomes; they do not '
            'prove causality. No task IDs, coordinates, hidden state, solver or protected cases. '
            'Current accepted program ' + canonical(current['program']) + '. '
            'Your own measured attempts ' + canonical(feedback(history)) + '. ')
        if arm == 'fijo':
            prompt += 'Here are three incomplete tasks. Propose a general repair that helps solve them. '
        else:
            prompt += ('ECHO selected focus ' + focus + ' from its own observations and measured attempts. '
                       'Preserve successful behavior while repairing the observed failure. After a rejection, '
                       'refine scope or magnitude using the contrasting development evidence. Avoid repeating '
                       'a measured behavior that failed. If a repair was accepted, seek an additional improvement. ')
        prompt += 'Protected validation supplies no private details. Cases: ' + canonical(cases(selected)) + '. Return JSON only.'
        result.append({'id': index, 'type': focus, 'prompt': prompt,
                       'guard_schema': build_schema(selected, history)})
    return result
