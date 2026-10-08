"""B13: own-evidence target memory, current-aware grammar, bounded prompts."""
import json
import random

from echo_arc import stale_transition as patch
from echo_arc import contrastive_requests as previous
from echo_arc.contrastive_evidence import feedback, require_development
from echo_arc.contrastive_grammar import build_schema, choices, witnesses, validate_answer
from echo_arc.feasible_grammar import canonical, matches
from seed.game_selfimprove import sha

FEATURE_ORDER = tuple(sorted(patch.FEATURES))


def compact_features(value):
    """Lossless feature-table encoding, with column order supplied in prompt."""
    if isinstance(value, list):
        return [compact_features(v) for v in value]
    if isinstance(value, dict):
        return {k: [v[name] for name in FEATURE_ORDER]
                if k == 'features' and isinstance(v, dict) and set(v) == set(FEATURE_ORDER)
                else compact_features(v) for k, v in value.items()}
    return value


def effective(parameter, features, current):
    settings, _ = patch.settings(current['program'], features)
    value = settings.get(parameter, patch.DEFAULTS[parameter])
    return min(features['hold_remaining'], value) if parameter == 'COOLDOWN_CAP' else value


def schema_for(rows, current, history):
    """No benefit ranking: remove controls identical at all relevant observations."""
    schema = build_schema(rows, history)
    observations = witnesses(rows)
    groups = []
    for parameter, value, guards in choices(schema):
        ws = observations[parameter]
        kept = []
        for guard in guards:
            if any(matches(guard, w['features']) and
                   effective(parameter, w['features'], current) !=
                   (min(w['features']['hold_remaining'], value) if parameter == 'COOLDOWN_CAP' else value)
                   for w in ws):
                kept.append(guard)
        if kept:
            groups.append(dict(parameter=parameter, value=value, guards=kept))
    return dict(schema, groups=groups)


def target_for(current, history):
    """Keep an improving rejected target up to three attempts on the same base."""
    base = sha(current)
    candidates = [e for e in history if e.get('base_sha256') == base
                  and e['verdict'] not in ('accepted', 'V1', 'V2')
                  and e.get('A', {}).get('gain', 0) > 0 and e.get('proposal')]
    candidates = [e for e in candidates
                  if sum(x.get('target_id') == e['id'] for x in history
                         if x.get('base_sha256') == base) < 3]
    if not candidates:
        return None
    # Continue an active target rather than anchoring on the accepted program.
    active = history[-1].get('target_id') if history else None
    return next((e for e in candidates if e['id'] == active),
                max(candidates, key=lambda e: (e['A']['gain'],
                    -e.get('development', {}).get('losses', 0), -e['id'])))


def request(arm, index, current, measured, history):
    rows = measured['rows']
    require_development(rows)
    target = target_for(current, history) if arm == 'echo' else None
    if target:
        selected = [rows[c['case_index']] for c in target['development']['contrasts']]
        selected += [r for r in rows if not any(r is x for x in selected)]
        selected, focus = selected[:3], 'REFINE'
    else:
        # Expired targets must not re-enter through the previous selector.
        clean = [e for e in history if e['verdict'] == 'accepted' or e.get('A', {}).get('gain', 0) <= 0]
        selected, focus = previous.select(rows, arm, clean, index)
    own_feedback = feedback(history)
    target_public = feedback([target])[0] if target else None
    case_evidence = previous.cases(selected)
    head = (
        'Return one JSON repair, one control and 1 to 3 AND guards (eq/ge/le). '
        'Goal: gain at least 2 development levels with no per-game level or score loss. '
        'REVALIDATE_NOOP 1..8 replaces a movement prediction with its observed self-loop after N '
        'consecutive no-change contradictions and clears its plan. '
        'HOLD sets the duration of future waiting after trying a known reset key. '
        'COOLDOWN_CAP clamps a wait already in progress. '
        'Broad changes can hurt useful waiting or planning. Conditions use observed features only. '
        'Grammar excludes previously tried patches and values identical to the accepted policy at '
        'all witnessed control opportunities. Applicability is not evidence of benefit. '
        'Use no task identifiers, coordinates or hidden state. '
        'Control bounds: ' + canonical({p: patch.LIMITS[p] for p in ('HOLD', 'COOLDOWN_CAP')}) + '. '
        'Feature bounds: ' + canonical(patch.FEATURES) + '. '
        'Guard thresholds for nonbinary features: 0,1,2,4,8,16,20,32,40,64,80,128 within bounds. '
    )
    if target:
        parameter = next(iter(target['proposal']['patches'][0]['set']))
        instruction = ('REFINEMENT TARGET (your rejected repair, not the accepted program): '
                       + canonical(target_public) + '. Keep control ' + parameter
                       + '; refine its value or scope using the observed gain/loss contrasts. '
                       'A contrast marks first divergence, not proof of cause. ')
    elif arm == 'echo':
        instruction = ('ECHO selected focus ' + focus + ' from its own measured attempts. '
                       'CONTRADICTION means incorrect movement predictions; WAIT means costly '
                       'waiting opportunities; GENERALIZE means seek useful scope beyond past success. ')
    else:
        instruction = 'Here are three incomplete tasks. Propose a general repair that helps solve them. '
    # Explicit semantic compaction, selected by actual model-token count. Never
    # slice a prompt or remove the target, its contrasts, or the current policy.
    variants = []
    for keep, compact in ((4, False), (2, False), (0, False), (0, True)):
        shown = case_evidence
        active_instruction = instruction
        column_help = ''
        if compact:
            shown = [dict(c, observed_control_opportunities={p: ws[:1] for p, ws in
                         c['observed_control_opportunities'].items()}) for c in shown]
            shown = compact_features(shown)
            column_help = 'Numeric arrays named features use this exact column order: ' + canonical(FEATURE_ORDER) + '. '
            if target:
                active_instruction = instruction.replace(canonical(target_public), canonical(compact_features(target_public)))
        variants.append(head + column_help + active_instruction + 'Accepted policy: ' + canonical(current['program'])
                        + '. Own recent feedback: ' + canonical(own_feedback[-keep:] if keep else [])
                        + '. Three development cases: ' + canonical(shown) + '. JSON only.')
    return {'id': index, 'type': focus, 'target_id': target['id'] if target else None,
            'target_parameter': next(iter(target['proposal']['patches'][0]['set'])) if target else None,
            'prompt_variants': variants, 'guard_schema': schema_for(rows, current, history)}


def check_answer(text, req):
    proposal = validate_answer(text, req['guard_schema'])
    if req.get('target_parameter') and proposal['patches']:
        if set(proposal['patches'][0]['set']) != {req['target_parameter']}:
            raise ValueError('refinement addressed a different control; call still counts')
    return proposal


def random_answer(req, seed):
    """Uniform over legal patches, not over operators of different sizes."""
    allowed = choices(req['guard_schema'])
    total = sum(len(guards) for _, _, guards in allowed)
    if not total:
        return canonical(patch.EMPTY)
    index = random.Random(seed).randrange(total)
    for parameter, value, guards in allowed:
        if index < len(guards):
            return canonical({'patches': [{'set': {parameter: value}, 'when': guards[index]}]})
        index -= len(guards)
    raise AssertionError('unreachable')


def gbnf(schema):
    """Share repeated finite guard sets to bound llama.cpp grammar size."""
    alternatives, definitions, seen = [], [], {}
    literal = lambda s: json.dumps(s, ensure_ascii=True)
    for parameter, value, guards in choices(schema):
        key = sha(guards)
        if key not in seen:
            name = 'guards' + str(len(seen))
            seen[key] = name
            definitions.append(name + ' ::= ' + ' | '.join(literal(canonical(g)) for g in guards))
        alternatives.append(literal('{"patches":[{"set":' + canonical({parameter: value}) + ',"when":')
                            + ' ' + seen[key] + ' ' + literal('}]}'))
    return 'root ::= ' + (' | '.join(alternatives) if alternatives else literal(canonical(patch.EMPTY))) \
        + '\n' + '\n'.join(definitions) + '\n'
