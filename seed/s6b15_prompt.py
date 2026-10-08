"""B15: operator-bound proposals, selected-case applicability and numeric evidence."""
from echo_arc import repair_experiments as experiments, repair_memory as memory
from echo_arc.contrastive_grammar import choices, validate_answer
from echo_arc.contrastive_evidence import require_development
from seed import s6b13_prompt as grammar, s6b14_prompt as compact

patch, canonical = grammar.patch, grammar.canonical
random_answer, gbnf = grammar.random_answer, grammar.gbnf
program, receipt = compact.program, compact.receipt

HEAD = (
    'Return one JSON patch: one set control and 1..3 AND conditions when, eq/ge/le. '
    'Need >=2 additional development levels with no individual level or score loss. '
    'REVALIDATE_NOOP revises a false movement prediction after N repeated no-change '
    'contradictions, clearing the plan. HOLD sets future waits after trying a known reset. '
    'COOLDOWN_CAP shortens a wait already running. Applicability does not prove benefit. '
    'Numeric ranges are marginal; listed points are actual joint observations at reads. '
    'Look for a scope that preserves useful behavior while repairing the observed failure. '
    'Do not use task IDs, coordinates or hidden information. '
    'Compact policies/receipts use [control_index,value,conditions], each condition '
    '[feature_index,operator_index,threshold]. Control order=' + canonical(compact.PARAMETERS)
    + '; feature order=' + canonical(compact.FEATURES) + '; operator order=' + canonical(compact.OPS)
    + '. Bounds=' + canonical({k: patch.LIMITS[k] for k in compact.PARAMETERS})
    + '. Legal nonbinary guard thresholds within feature bounds: 0,1,2,4,8,16,20,32,40,64,80,128. '
    'First-divergence contrasts are observations, not proof of causation. Protected rejection '
    'provides only a rejection bit, never protected cases. '
)


def context(arm, index, current, measured, history, *, numeric=True):
    rows = measured['rows']
    require_development(rows)
    selection = experiments.select(rows, arm, current, history, index)
    parameter, target = selection['parameter'], selection['target']
    latest = history[-1] if history else None
    target_latest = next((e for e in reversed(history) if target is not None and
                          e.get('base_sha256') == memory.sha(current) and
                          memory.root_id(e, history) == target['id']), None)
    instruction = ('Requested operator=' + str(parameter) + '. ' +
        ('ECHO selected this experiment from its measured development history. ' if arm == 'echo' else
         'Fixed cyclic operator schedule. Propose a general repair for these development cases. '))
    if target:
        instruction += 'Refine the rejected target value or scope using its gain/loss contrasts. '
    required = dict(accepted_policy=program(current['program']), latest_attempt=receipt(latest),
                    target=receipt(target), latest_target_attempt=receipt(target_latest),
                    paused_family=selection['paused_family'])
    if arm == 'echo':
        required['operator_statistics'] = selection['statistics']
    variants = []
    # Latest receipt, current program and target survive every compaction level.
    for recent, contrasts, points in ((2, 2, 4), (0, 1, 2), (0, 0, 2)):
        payload = dict(required,
            recent_earlier=[receipt(e) for e in history[max(0, len(history)-1-recent):-1]] if recent else [],
            target_contrasts=compact.contrasts(target, contrasts) if target and contrasts else [],
            latest_contrasts=compact.contrasts(latest, contrasts) if latest and latest.get('development') and contrasts else [],
            cases=experiments.case_data([rows[i] for i in selection['selected']], parameter, points, numeric))
        variants.append(HEAD + instruction + 'DATA=' + canonical(payload) + '\nJSON only.')
    return dict(id=index, type=selection['focus'], requested_operator=parameter,
                target_id=target['id'] if target else None,
                target_parameter=experiments.operator(target) if target else None,
                selected_cases=selection['selected'], selection_statistics=selection['statistics'],
                family_cooldown=selection['paused_family'], numeric_summary=numeric,
                prompt_variants=variants)


def request(arm, index, current, measured, history, *, numeric=True, bind=True):
    req = context(arm, index, current, measured, history, numeric=numeric)
    rows = measured['rows']
    # Binding also changes the witness domain: an observation in an unrelated
    # game cannot rescue an impossible guard for the selected cases.
    scope = [rows[i] for i in req['selected_cases']] if bind else rows
    schema = grammar.schema_for(scope, current, history)
    if bind:
        schema['groups'] = [dict(parameter=p, value=v, guards=gs) for p, v, gs in choices(schema)
                            if p == req['requested_operator']]
    schema = memory.prune_repeated_failures(schema, rows, current, history)
    req.update(guard_schema=schema, operator_binding=bind,
               applicability_scope='selected' if bind else 'all_development')
    return req


def check_answer(text, req):
    proposal = validate_answer(text, req['guard_schema'])
    if req.get('operator_binding') and proposal['patches'] and \
            set(proposal['patches'][0]['set']) != {req['requested_operator']}:
        raise ValueError('proposal did not address requested operator; call still counts')
    if req.get('target_parameter') and proposal['patches'] and \
            set(proposal['patches'][0]['set']) != {req['target_parameter']}:
        raise ValueError('proposal did not address refinement target; call still counts')
    return proposal
