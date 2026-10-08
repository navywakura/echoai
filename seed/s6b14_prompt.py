"""B14 bounded prompts: mandatory latest receipt, relevant cases and replay memory."""
from echo_arc import repair_memory as memory
from echo_arc import contrastive_requests as examples
from echo_arc.contrastive_evidence import require_development
from echo_arc.contrastive_grammar import witnesses
from seed import s6b13_prompt as previous

patch, canonical = previous.patch, previous.canonical
FEATURES = memory.FEATURES
PARAMETERS = ('REVALIDATE_NOOP', 'HOLD', 'COOLDOWN_CAP')
OPS = ('eq', 'ge', 'le')
check_answer, random_answer, gbnf = previous.check_answer, previous.random_answer, previous.gbnf


def program(value):
    """Lossless compact policy syntax, decoded by the fixed legend in every prompt."""
    if value is None:
        return None
    value = patch.validate(value)
    return [[PARAMETERS.index(next(iter(item['set']))), next(iter(item['set'].values())),
             [[FEATURES.index(k), OPS.index(op), n] for k, (op, n) in sorted(item['when'].items())]]
            for item in value['patches']]


def receipt(event):
    value = memory.receipt(event)
    if value is not None:
        value['proposal'] = program(value['proposal'])
    return value


def contrasts(event, limit=2):
    """Both signs when present; observed first divergence is not a causal proof."""
    if not event:
        return []
    d = event.get('development', {})
    if d.get('origin') != 'DEVELOPMENT_A':
        raise ValueError('only development contrasts allowed')
    output = []
    for c in d['contrasts'][:limit]:
        sequence = []
        for pair in c['sequence'][-1:]:
            point = {}
            for name in ('before', 'candidate'):
                step = pair[name]
                if step is None:
                    point[name] = None
                elif step.get('automatic_reset'):
                    point[name] = {'automatic_reset': True}
                else:
                    point[name] = dict(features=[step['features'][k] for k in FEATURES],
                                       action=step['action'], outcome=step['outcome'])
            sequence.append(point)
        output.append(dict(effect=c['effect'], levels=c['levels'], score=c['score'], sequence=sequence))
    return output


def case_data(rows, count, minimal):
    output = []
    for c in examples.cases(rows):
        opportunities = {}
        for p, points in c['observed_control_opportunities'].items():
            chosen = points[:count]
            opportunities[p] = [dict(features=[w['features'][k] for k in FEATURES],
                                     **{k: v for k, v in w.items() if k != 'features'}) for w in chosen]
        output.append(dict(case=c['case'], levels=c['levels'], counts=c['counts'],
                           **({} if minimal else {'opportunities': opportunities})))
    return output


HEAD = (
    'Return one JSON patch with one set control and 1..3 AND conditions when. '
    'Output full control/feature names, using eq/ge/le. Need >=2 more development levels '
    'and no individual level or score loss. REVALIDATE_NOOP revises a false movement '
    'prediction after N repeated no-change contradictions, clearing the plan. HOLD sets '
    'future waits after trying a known reset. COOLDOWN_CAP shortens a wait already running. '
    'Grammar admits witnessed controls, removes exact repeats and some proven repeated '
    'V3 failures on complete prior A trajectories. V4 equivalents are not proof-excluded. '
    'A repeated failed control/value can be paused for one call to diversify exploration; '
    'that pause is a heuristic, not a claim that every scope fails. '
    'Do not use task IDs, coordinates or hidden information. '
    'Compact policies/receipts encode each patch as [control_index,value,conditions]; '
    'each condition is [feature_index,operator_index,threshold]. '
    'Control order=' + canonical(PARAMETERS) + '; feature order=' + canonical(FEATURES)
    + '; operator order=' + canonical(OPS) + '. Features arrays follow that feature order. '
    'Bounds=' + canonical({k: patch.LIMITS[k] for k in PARAMETERS}) + '. '
    'First-divergence contrasts describe observations, not proof of causation. '
    'A protected rejection supplies no protected examples. '
)


def context(arm, index, current, measured, history):
    rows = measured['rows']
    require_development(rows)
    selected, focus, target, stats = memory.select(rows, arm, current, history, index)
    selected_rows = [rows[i] for i in selected]
    latest = history[-1] if history else None
    target_latest = next((e for e in reversed(history) if target is not None and
                          e.get('base_sha256') == memory.sha(current) and
                          memory.root_id(e, history) == target['id']), None)
    parameter = next(iter(target['proposal']['patches'][0]['set'])) if target else None
    if arm == 'fijo':
        instruction = 'Here are up to three incomplete tasks. Propose a general repair that helps solve them. '
    elif target:
        instruction = ('Refine the rejected target. Keep control ' + parameter +
                       '. Use both the original target and its latest outcome; do not repeat failed behavior. ')
    else:
        instruction = ('ECHO focus=' + focus + '. CONTRADICTION repairs false predictions; WAIT repairs '
                       'costly waiting; GENERALIZE seeks coverage across observed cases while retaining '
                       'past successes. New mechanisms receive a trial before further exploitation. ')
    required = dict(accepted_policy=program(current['program']), latest_attempt=receipt(latest),
                    target=receipt(target), latest_target_attempt=receipt(target_latest),
                    diversity_cooldown=memory.cooldown(current, history))
    if arm == 'echo':
        required['mechanism_statistics'] = stats
    variants = []
    # The latest outcome is mandatory in every variant. Reduce optional earlier
    # contrasts/cases first. Exact token counting still chooses the first fit.
    for recent, contrast_limit, point_count, minimal_cases in (
            (3, 2, 2, False), (1, 2, 1, False), (0, 1, 1, False), (0, 0, 0, True)):
        payload = dict(required, recent_earlier=[receipt(e) for e in history[max(0, len(history)-1-recent):-1]] if recent else [],
                       target_contrasts=contrasts(target, contrast_limit) if target and contrast_limit else [],
                       latest_contrasts=contrasts(latest, contrast_limit) if latest and latest.get('development') and contrast_limit else [],
                       cases=case_data(selected_rows, point_count, minimal_cases))
        variants.append(HEAD + instruction + 'DATA=' + canonical(payload) + '\nJSON only.')
    return dict(id=index, type=focus, target_id=target['id'] if target else None,
                target_parameter=parameter, prompt_variants=variants,
                selected_cases=selected, selection_statistics=stats)


def request(arm, index, current, measured, history):
    value = context(arm, index, current, measured, history)
    schema = previous.schema_for(measured['rows'], current, history)
    proven = memory.prune_repeated_failures(schema, measured['rows'], current, history)
    value['guard_schema'] = memory.apply_cooldown(proven, current, history)
    return value
