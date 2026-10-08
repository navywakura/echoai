"""Real, zero-game, neutral format gate. Separate ledger; no training or feedback."""
from pathlib import Path
from seed import s6b23r4_model as model
from echo_arc import s6b23r4_search as search
from seed.game_selfimprove import canonical, sha
from seed.s6b11 import atomic

SEED = 823900


def cases():
    proposals = [
        {'patches': [{'when': {'body_known': ['eq', 0]}, 'set': {'HOLD': 4}}]},
        {'patches': [{'when': {'body_known': ['eq', 1], 'click_only': ['eq', 0]}, 'set': {'HOLD': 8}}]},
        {'patches': [{'when': {'body_known': ['eq', 0], 'click_only': ['eq', 1], 'count_known': ['eq', 0]}, 'set': {'HOLD': 12}}]},
        {'patches': [{'when': {'click_only': ['eq', 0]}, 'set': {'HOLD': 16}}]},
    ]
    instructions = [
        'Copy the required_output exactly as JSON.',
        'Construct one patch: HOLD is 8; body_known equals 1 AND click_only equals 0.',
        'Construct one patch: HOLD is 12; body_known equals 0 AND click_only equals 1 AND count_known equals 0.',
        'The invalid output has HOLD as [16]. Fix only that type error to integer 16; keep click_only equals 0.',
    ]
    result = []
    for index, (expected, task) in enumerate(zip(proposals, instructions)):
        payload = dict(search.format_fields(), task=task, purpose='Neutral protocol test, no game utility or evidence.',
                       allowed_atoms={'body_known': [['eq', 0], ['eq', 1]],
                                      'click_only': [['eq', 0], ['eq', 1]], 'count_known': [['eq', 0], ['eq', 1]]})
        if index == 0:
            payload['required_output'] = expected
        if index == 3:
            payload['invalid_output'] = {'patches': [{'when': {'click_only': ['eq', 0]}, 'set': {'HOLD': [16]}}]}
        result.append(dict(expected=expected, request=dict(prompt=canonical(payload),
                           model_call_required=True, type='FORMAT_PROBE', predicted_gain=None, measured_effect=None)))
    return result


def verify(root, registry, profile):
    import json
    folder = root / 'format-preflight'
    receipt = json.loads((folder / 'receipt.json').read_text())
    expected_calls = [f'{arm}/{i:03d}' for arm in ('N14', 'N7') for i in range(4)]
    expected = dict(valid=True, profile_sha256=profile, cases_sha256=sha(cases()),
                    grammar_sha256=sha(model.grammar()), model_calls=8, games_started=False,
                    calls=expected_calls)
    if receipt != expected:
        raise RuntimeError('format receipt mismatch')
    ledger = json.loads((folder / 'model-budget.json').read_text())
    if ledger['calls'] != expected_calls:
        raise RuntimeError('format call accounting mismatch')
    for arm in ('N14', 'N7'):
        for index, case in enumerate(cases()):
            call_dir = folder / 'calls' / arm / f'{index:03d}'
            result = model.load(call_dir, case['request'], arm, SEED + index, profile)
            if not result['transport_ok'] or result['proposal'] != case['expected']:
                raise RuntimeError('format inference differs from required output')
            if json.loads((call_dir / 'command.json').read_text()) != model.command(registry[arm], call_dir / 'prompt.txt', SEED + index):
                raise RuntimeError('format command differs')
    return receipt


def run(root, registry, profile, status):
    folder = root / 'format-preflight'
    if (folder / 'receipt.json').exists():
        return verify(root, registry, profile)
    folder.mkdir(parents=True, exist_ok=True)
    for arm in ('N14', 'N7'):
        for index, case in enumerate(cases()):
            status('FORMAT_PREFLIGHT', arm=arm, slot=index + 1, total_slots=4, games_started=False)
            result = model.propose(folder, registry, arm, index, case['request'], SEED + index, profile)
            if result['proposal'] != case['expected']:
                atomic(folder / 'blocked.json', dict(arm=arm, slot=index, reason='synthetic instruction mismatch'))
                raise RuntimeError('format gate: syntactically legal response did not follow the neutral instruction')
            status('FORMAT_CASE_PASS', arm=arm, slot=index + 1, games_started=False)
    atomic(folder / 'receipt.json', dict(valid=True, profile_sha256=profile,
        cases_sha256=sha(cases()), grammar_sha256=sha(model.grammar()), model_calls=8,
        games_started=False, calls=[f'{arm}/{i:03d}' for arm in ('N14', 'N7') for i in range(4)]))
    receipt = verify(root, registry, profile)
    status('FORMAT_PREFLIGHT_PASS', model_calls=8, games_started=False)
    return receipt
