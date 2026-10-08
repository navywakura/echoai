"""Real-history context regression and conservative replay exclusion checks.

This does not play games or generate proposals. The local GGUF tokenizer is
used only to count actual input IDs; all histories are existing development data.
"""
import copy
import json
from pathlib import Path
from unittest.mock import patch as mock

from seed import s6b14 as r
from seed import s6b14_prompt as p
from echo_arc import repair_memory as mem

OUT = r.ROOT / 'qualification'


def read(path):
    return json.loads(path.read_text())


def validate_context(name, req, latest):
    counts = []
    path = OUT / (name + '.txt')
    path.parent.mkdir(parents=True, exist_ok=True)
    for text in req['prompt_variants']:
        data = json.loads(text.split('DATA=', 1)[1].split('\nJSON only.', 1)[0])
        if data['latest_attempt'] != p.receipt(latest):
            raise AssertionError('latest outcome lost in a context variant')
        if latest and data['latest_attempt']['protected_rejection'] != (latest['verdict'] == 'V4'):
            raise AssertionError('protected rejection bit lost')
    for variant, text in enumerate(req['prompt_variants']):
        path.write_text(r.model.chat(text))
        tokens = r.model.tokenize(path)
        counts.append(len(tokens))
        if len(tokens) <= r.model.MAX_INPUT:
            break
    else:
        raise AssertionError('no bounded context variant for ' + name + ': ' + str(counts))
    result = dict(name=name, variant=variant, token_counts=counts, input_tokens=len(tokens),
                  latest_preserved=True, prompt_sha256=r.model.digest_file(path), focus=req['type'])
    r.b.atomic(path.with_suffix('.json'), result)
    return result


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = read(r.PREVIOUS / 'primary/measurements/baseline/A.json')
    contexts, forced, duplicate_checks, cooldown_checks = [], [], [], []
    for arm in ('echo', 'fijo'):
        for seed in (697001, 697017, 697029):
            current, measured, history = r.b.strategy(), baseline, []
            for i in range(6):
                old_request = read(r.PREVIOUS / f'calls/pilot/{arm}-{seed}/{i:03d}/request.json')
                req = p.context(arm, i, current, measured, history)
                if req['type'] in ('CONTRADICTION', 'WAIT'):
                    if not all(mem.signal(measured['rows'][j], req['type']) > 0 for j in req['selected_cases']):
                        raise AssertionError('selected a case without the requested signal')
                contexts.append(validate_context(f'{arm}-{seed}-{i:03d}', req, history[-1] if history else None))
                if old_request['type'] == 'REFINE':
                    target = next(e for e in history if e['id'] == old_request['target_id'])
                    selected = [c['case_index'] for c in target['development']['contrasts']][:3]
                    with mock.object(mem, 'select', return_value=(selected, 'REFINE', target, mem.statistics(history))):
                        force = p.context(arm, i, current, measured, history)
                    forced.append(validate_context(f'forced-refine-{seed}-{i:03d}', force, history[-1]))
                event = read(r.PREVIOUS / f'steps/pilot/{arm}-{seed}/{i:03d}.json')['event']
                paused = mem.cooldown(current, history)
                if paused:
                    cooldown_checks.append(dict(arm=arm, seed=seed, round=i+1, paused=paused,
                        would_block_old_setting=event['proposal']['patches'][0]['set'] in paused))
                for prior in history:
                    if event.get('development', {}).get('behavior_sha256') != prior.get('development', {}).get('behavior_sha256') \
                            or event['base_sha256'] != prior['base_sha256'] or prior['verdict'] != 'V3' \
                            or event['proposal']['patches'][0]['set'] != prior['proposal']['patches'][0]['set']:
                        continue
                    candidate_rows = read(r.PREVIOUS / f'primary/measurements/pilot/{arm}-{seed}/{prior["id"]:03d}/A.json')['rows']
                    certified = dict(prior, decision_certificate=mem.certificate(candidate_rows, current, prior['candidate']))
                    item = event['proposal']['patches'][0]
                    parameter, value = next(iter(item['set'].items()))
                    schema = dict(version=11, origin='DEVELOPMENT_A', excluded=[],
                                  groups=[dict(parameter=parameter, value=value, guards=[item['when']])])
                    pruned = mem.prune_repeated_failures(schema, measured['rows'], current, [certified])
                    duplicate_checks.append(dict(arm=arm, seed=seed, earlier=prior['id'], later=i,
                        proven_excluded=pruned['equivalent_V3_exclusions'] == 1,
                        certificate_points=len(certified['decision_certificate']['points'])))
                    break
                history.append(event)
                if event['verdict'] == 'accepted':
                    current = event['candidate']
                    measured = read(r.PREVIOUS / f'primary/measurements/pilot/{arm}-{seed}/{i:03d}/A.json')
    # Stress all 32 legal policy slots, rather than assuming only one is accepted.
    full = r.b.strategy(program={'patches': [
        {'set': {'HOLD': i}, 'when': {'reset_known': ['eq', 1], 'pending_effect': ['eq', 0],
                                      'world_events': ['ge', 128]}} for i in range(32)]})
    recent = copy.deepcopy(read(r.PREVIOUS / 'steps/pilot/echo-697017/003.json')['event'])
    recent['base_sha256'] = mem.sha(full)
    with mock.object(mem, 'select', return_value=([0, 51, 59], 'REFINE', recent, mem.statistics([recent]))):
        stress = p.context('echo', 1, full, baseline, [recent])
    maximum = validate_context('32-policy-slots', stress, recent)
    original_sources = read(r.PREVIOUS / 'profile.json')['sources']
    for name, expected in original_sources.items():
        if r.model.digest_file(r.REPO / name) != expected:
            raise AssertionError('original experiment changed')
    tests = (r.REPO / 'lab/s6b14-tests.log').read_text()
    if '\nOK\n' not in tests or 'FAILED' in tests:
        raise AssertionError('test run must pass')
    (OUT / 'tests.log').write_text(tests)
    for name in r.SOURCES:
        snapshot = OUT / 'source-archive' / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes((r.REPO / name).read_bytes())
    result = dict(valid=True, at=r.b.now(), new_games=0, new_model_calls=0,
                  prior_sources_unchanged=True, contexts=contexts, forced_refinements=forced,
                  maximum_policy_context=maximum, observed_duplicate_checks=duplicate_checks,
                  observed_cooldown_checks=cooldown_checks,
                  tests_log_sha256=r.model.digest_file(OUT / 'tests.log'),
                  sources={name: r.model.digest_file(r.REPO / name) for name in r.SOURCES})
    r.b.atomic(r.ROOT / 'validation.json', result)
    print(r.b.canonical(dict(valid=True, contexts=len(contexts), forced=len(forced),
        max_input_tokens=max(x['input_tokens'] for x in contexts + forced + [maximum]),
        same_behavior_pairs=len(duplicate_checks), safely_pruned=sum(x['proven_excluded'] for x in duplicate_checks),
        cooldown_settings_changed=sum(x['would_block_old_setting'] for x in cooldown_checks),
        new_games=0, new_model_calls=0)), flush=True)


if __name__ == '__main__':
    run()
