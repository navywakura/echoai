"""B12: deterministic context budgeting after B11's development-only selection.

Keep fitting prompts byte-identical. First compact repeated feature names
losslessly; remove complete detail units only if the exact tokenizer requires it.
Neither arm, outcomes in protected B, nor a target score select a budget tier.
"""
import copy
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import subprocess

from echo_arc import contrastive_requests as previous
from echo_arc.contrastive_evidence import FEATURE_ORDER
from echo_arc.feasible_grammar import canonical

REPO = Path(__file__).resolve().parents[1]
LIMIT = 6000
TOKEN_FILES = ('config.json', 'merges.txt', 'tokenizer.json', 'tokenizer_config.json', 'vocab.json')
MARK_HISTORY = 'Your own measured attempts '
MARK_CASES = 'Cases: '
LEGEND = 'Compact evidence: every features array uses this exact field order: ' + canonical(FEATURE_ORDER) + '. '


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def count_many(prompts):
    env = dict(os.environ, USE_TORCH='0', USE_TF='0', TRANSFORMERS_VERBOSITY='error',
               TOKENIZERS_PARALLELISM='false', HF_HUB_OFFLINE='1')
    result = subprocess.run([str(REPO / 'lab/tools/s6-context-venv/bin/python'),
                             str(REPO / 'echo_arc/context_tokenizer.py')],
        input=json.dumps(prompts), text=True, capture_output=True, env=env, timeout=120, check=True)
    rows = json.loads(result.stdout)
    if len(rows) != len(prompts):
        raise ValueError('incomplete tokenizer response')
    return rows


@lru_cache(maxsize=512)
def count(prompt):
    return count_many([prompt])[0]


def compact(value):
    if isinstance(value, list):
        return [compact(v) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key == 'features' and isinstance(item, dict):
            if set(item) != set(FEATURE_ORDER):
                raise ValueError('incomplete feature vector')
            result[key] = [item[k] for k in FEATURE_ORDER]
        else:
            result[key] = compact(item)
    return result


def expand(value):
    if isinstance(value, list):
        return [expand(v) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if key == 'features' and isinstance(item, list):
            result[key] = dict(zip(FEATURE_ORDER, item, strict=True))
        else:
            result[key] = expand(item)
    return result


def sections(prompt):
    history_start = prompt.index(MARK_HISTORY) + len(MARK_HISTORY)
    history, size = json.JSONDecoder().raw_decode(prompt[history_start:])
    history_end = history_start + size
    cases_start = prompt.index(MARK_CASES, history_end) + len(MARK_CASES)
    cases, size = json.JSONDecoder().raw_decode(prompt[cases_start:])
    return history_start, history_end, cases_start, cases_start + size, history, cases


def variant(prompt, tier):
    hs, he, cs, ce, history, cases = sections(prompt)
    history, cases = copy.deepcopy(history), copy.deepcopy(cases)
    if tier >= 2:
        for entry in history:
            for contrast in entry.get('contrasts', []):
                contrast['sequence'] = contrast['sequence'][-1:]
    if tier >= 3:
        for entry in history[:-1]:
            for contrast in entry.get('contrasts', []):
                contrast['sequence'] = []
    if tier >= 4:
        for entry in history:
            for contrast in entry.get('contrasts', []):
                contrast['sequence'] = []
    if tier >= 5:
        for case in cases:
            case['observed_control_opportunities'] = {
                p: observations[:1] for p, observations in case['observed_control_opportunities'].items()}
    packed_history, packed_cases = compact(history), compact(cases)
    assert expand(packed_history) == history and expand(packed_cases) == cases
    note = LEGEND
    if tier >= 2:
        note += ('Context budget may omit earlier sequence steps; all listed aggregate outcomes and '
                 'verdicts are retained. Missing details are unknown, not evidence of no effect. ')
    return (note + prompt[:hs] + canonical(packed_history) + prompt[he:cs] +
            canonical(packed_cases) + prompt[ce:])


def bounded(request, counter=count):
    original = request['prompt']
    initial = counter(original)
    selected, receipt, tier = original, initial, 0
    if initial['tokens'] > LIMIT:
        for tier in range(1, 6):
            selected = variant(original, tier)
            receipt = counter(selected)
            if receipt['tokens'] <= LIMIT:
                break
        else:
            raise ValueError('mandatory context exceeds 6000 tokens before submission')
    result = dict(request, prompt=selected)
    result['context'] = {'version': 12, 'limit': LIMIT, 'tier': tier,
                         'original_tokens': initial['tokens'], 'tokens': receipt['tokens'],
                         'original_prompt_sha256': digest(original),
                         'prompt_sha256': digest(selected), 'token_ids_sha256': receipt['token_ids_sha256'],
                         'lossless_evidence': tier <= 1}
    return result


def requests(arm, round_id, count, current, measured, history):
    return [bounded(r) for r in previous.requests(arm, round_id, count, current, measured, history)]


def tokenizer_manifest():
    root = REPO / 'lab/tools/s6-qwen-tokenizer'
    reference = json.loads((REPO / 'lab/kaggle/s6-model-cache-20260929/output/manifest.json').read_text())
    result = {}
    for name in TOKEN_FILES:
        value = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if value != reference['files'][name]['sha256']:
            raise ValueError('tokenizer does not match the pinned Kaggle input')
        result[name] = value
    return result
