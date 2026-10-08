"""Instrument qualification using existing B14 A records and real token counts.

No generated proposals or new games; this receipt is frozen before the micro.
"""
import copy
import json
from unittest.mock import patch as mock

from seed import s6b15 as r, s6b15_micro as micro
from echo_arc import repair_experiments as ex

OUT = r.ROOT / 'qualification'


def read(path):
    return json.loads(path.read_text())


def validate_context(name, req, latest):
    path = OUT / (name + '.txt')
    path.parent.mkdir(parents=True, exist_ok=True)
    for variant in req['prompt_variants']:
        data = json.loads(variant.split('DATA=', 1)[1].split('\nJSON only.', 1)[0])
        if data['latest_attempt'] != r.prompts.receipt(latest):
            raise AssertionError('mandatory latest receipt was lost')
    counts = []
    for index, variant in enumerate(req['prompt_variants']):
        path.write_text(r.model.chat(variant))
        counts.append(len(r.model.tokenize(path)))
        if counts[-1] <= r.model.MAX_INPUT:
            break
    else:
        raise AssertionError('context overflow: ' + name + ': ' + str(counts))
    result = dict(name=name, variant=index, token_counts=counts, input_tokens=counts[-1],
                  requested_operator=req['requested_operator'], latest_preserved=True,
                  prompt_sha256=r.model.digest_file(path))
    r.b.atomic(path.with_suffix('.json'), result)
    return result


def run():
    if (r.ROOT / 'profile.json').exists():
        raise RuntimeError('cannot rewrite qualification after freeze')
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = read(r.PREVIOUS / 'primary/measurements/baseline/A.json')
    contexts = []
    for arm in ('echo', 'fijo'):
        for seed in (698001, 698017, 698029):
            current, measured, history = r.b.strategy(), baseline, []
            for index in range(6):
                req = r.prompts.context(arm, index, current, measured, history)
                contexts.append(validate_context(f'{arm}-{seed}-{index:03d}', req, history[-1] if history else None))
                event = read(r.PREVIOUS / f'steps/pilot/{arm}-{seed}/{index:03d}.json')['event']
                history.append(event)
                if event['verdict'] == 'accepted':
                    current = event['candidate']
                    measured = read(r.PREVIOUS / f'primary/measurements/pilot/{arm}-{seed}/{index:03d}/A.json')
    current, measured, history = micro.reference()
    samples = []
    for binding, numeric in micro.CELLS:
        req = r.prompts.request('echo', 1, current, measured, history, bind=binding, numeric=numeric)
        samples.append(validate_context(f'micro-b{int(binding)}-n{int(numeric)}', req, history[-1]))
        if req['requested_operator'] != 'HOLD':
            raise AssertionError('incorporated +13 must not preempt untried HOLD')
        if binding:
            if {g['parameter'] for g in req['guard_schema']['groups']} != {'HOLD'}:
                raise AssertionError('binding failed')
    # Directly verify the observed B14 defect, not a synthetic replacement.
    actual = ex.case_data([measured['rows'][53]], 'HOLD', 2)[0]['observations']
    before = ex.case_data([measured['rows'][53]], 'HOLD', 2, numeric=False)[0]['observations']
    world = actual['columns'].index('world_events')
    if actual['ranges']['world_events'] != [14, 899] or {w[world] for w in actual['points']} != {14, 899}:
        raise AssertionError('real HOLD numeric extrema lost')
    if 14 in {w[world] for w in before['points']}:
        raise AssertionError('old-summary forensic reproduction changed')
    # All 32 legal slots plus a rejected target and latest target feedback.
    full = r.b.strategy(program={'patches': [
        {'set': {'HOLD': i}, 'when': {'reset_known': ['eq', 1], 'pending_effect': ['eq', 0],
                                    'world_events': ['ge', 128]}} for i in range(32)]})
    target = copy.deepcopy(history[-1])
    target.update(verdict='V3', base_sha256=r.b.sha(full), target_id=None)
    selection = dict(selected=[53, 18, 4], parameter='REVALIDATE_NOOP', focus='REFINE',
                     target=target, statistics=ex.statistics(full, [target]), paused_family=None)
    with mock.object(ex, 'select', return_value=selection):
        stress = r.prompts.context('echo', 1, full, measured, [target])
    maximum = validate_context('32-policy-slots', stress, target)
    for name, expected in read(r.PREVIOUS / 'profile.json')['sources'].items():
        if r.model.digest_file(r.REPO / name) != expected:
            raise AssertionError('B14 source changed: ' + name)
    tests = (r.REPO / 'lab/s6b15-tests.log').read_text()
    if '\nOK\n' not in tests or 'FAILED' in tests:
        raise AssertionError('instrument tests must pass')
    (OUT / 'tests.log').write_text(tests)
    result = dict(valid=True, at=r.b.now(), new_games=0, new_model_calls=0,
                  prior_sources_unchanged=True, contexts=contexts, micro_contexts=samples,
                  maximum_policy_context=maximum, observed_numeric_fix=dict(before=before, after=actual),
                  tests_log_sha256=r.model.digest_file(OUT / 'tests.log'),
                  sources={name: r.model.digest_file(r.REPO / name) for name in r.SOURCES})
    r.b.atomic(r.ROOT / 'validation.json', result)
    print(r.b.canonical(dict(valid=True, contexts=len(contexts), micro_contexts=len(samples),
        max_input_tokens=max(x['input_tokens'] for x in contexts + samples + [maximum]),
        real_numeric_extrema=[14, 899], new_games=0, new_model_calls=0)), flush=True)


if __name__ == '__main__':
    run()
