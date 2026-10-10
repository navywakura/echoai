"""B16 prompts retain B15 bounds and grammar, adding faithful local outcomes."""
import json
from types import FunctionType, SimpleNamespace

from seed import s6b15_prompt as previous
from echo_arc import repair_outcomes as outcomes

patch, canonical = previous.patch, previous.canonical
program, random_answer, gbnf, check_answer = previous.program, previous.random_answer, previous.gbnf, previous.check_answer


def receipt(event):
    value = previous.receipt(event)
    if value is not None:
        d = event.get('development', {})
        value.update(gross_level_gain=d.get('gross_level_gain'), gross_level_loss=d.get('gross_level_loss'))
    return value


def context(arm, index, current, measured, history, *, numeric=True):
    selector = SimpleNamespace(**{k: getattr(previous.experiments, k) for k in ('case_data', 'operator')},
                               select=outcomes.select)
    formatter = SimpleNamespace(contrasts=outcomes.contrasts)
    function = FunctionType(previous.context.__code__, dict(previous.context.__globals__,
        experiments=selector, compact=formatter, receipt=receipt), previous.context.__name__, previous.context.__defaults__)
    function.__kwdefaults__ = previous.context.__kwdefaults__
    req = function(arm, index, current, measured, history, numeric=numeric)
    target = next((e for e in history if e['id'] == req['target_id']), None) if req['target_id'] is not None else None
    variants = []
    for text in req['prompt_variants']:
        head, data = text.split('DATA=', 1)
        payload = json.loads(data.split('\nJSON only.', 1)[0])
        if target:
            # Both signs remain mandatory even in the smallest context variant.
            payload['target_contrasts'] = outcomes.contrasts(target, 2)
            if payload['latest_attempt'] and payload['latest_attempt']['attempt'] == target['id']:
                payload['latest_contrasts'] = []  # Already present under target_contrasts.
        cases = payload['cases']
        common = dict(cases[0]['observations']['constant']) if cases else {}
        for case in cases[1:]:
            common = {k:v for k,v in common.items() if case['observations']['constant'].get(k) == v}
        for case in cases:
            case['observations']['constant'] = {k:v for k,v in case['observations']['constant'].items() if k not in common}
        payload['shared_reading_constants'] = common
        # Explicitly identify the proposal being repaired, separate from the
        # accepted policy. This is the agent's own proposal, not a supplied winner.
        payload['repair_target_json'] = target['proposal'] if target else None
        variants.append(head +
            'Local level gains and losses are reported separately; a positive local gain is not acceptance. '
            'For a rejected target, preserve its useful cases while changing scope or value to avoid losses. '
            'Paired candidate feature_changes replace those keys in before.features. '
            'shared_reading_constants apply to every case, alongside its observations.constant. '
            'These observations do not prove which earlier control read caused the change. '
            'DATA=' + canonical(payload) + '\nJSON only.')
    return dict(req, prompt_variants=variants, feedback_version='B16-local-level-outcomes')


def request(arm, index, current, measured, history, *, numeric=True, bind=True):
    function = FunctionType(previous.request.__code__, dict(previous.request.__globals__, context=context),
                            previous.request.__name__, previous.request.__defaults__)
    function.__kwdefaults__ = previous.request.__kwdefaults__
    return function(arm, index, current, measured, history, numeric=numeric, bind=bind)
