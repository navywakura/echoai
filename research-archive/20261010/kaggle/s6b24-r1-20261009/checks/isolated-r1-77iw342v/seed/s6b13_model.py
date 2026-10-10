"""Local, bounded Qwen proposals with exact tokenizer and immutable receipts."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from seed.game_selfimprove import sha, canonical
from seed.s6b11 import atomic
from seed.s6b13_prompt import gbnf

MODEL = Path('/home/roger/models/qwen3-4b-instruct-2507/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf')
MODEL_SHA = '2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e'
CLI, TOKENIZER = Path('/usr/bin/llama-cli'), Path('/usr/bin/llama-tokenize')
MAX_INPUT, MAX_OUTPUT, CONTEXT, TIMEOUT = 3072, 160, 4096, 900


@lru_cache(maxsize=8)
def _digest(path, size, modified):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def digest_file(path):
    st = Path(path).stat()
    return _digest(str(path), st.st_size, st.st_mtime_ns)


def identity():
    if digest_file(MODEL) != MODEL_SHA:
        raise RuntimeError('local model weights changed')
    return {'model': str(MODEL), 'model_sha256': MODEL_SHA,
            'cli_sha256': digest_file(CLI), 'tokenizer_sha256': digest_file(TOKENIZER),
            'backend': 'CPU only, Q4_K_M', 'threads': 4, 'temperature': 0.6,
            'top_k': 40, 'top_p': 0.95, 'context': CONTEXT,
            'max_input_tokens': MAX_INPUT, 'max_output_tokens': MAX_OUTPUT, 'timeout_s': TIMEOUT}


def environment():
    return dict(os.environ, HIP_VISIBLE_DEVICES='-1', ROCR_VISIBLE_DEVICES='-1',
                OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')


def chat(text):
    return ('<|im_start|>system\nReturn one executable JSON proposal, no prose.'
            '<|im_end|>\n<|im_start|>user\n' + text + '<|im_end|>\n<|im_start|>assistant\n')


def tokenize(path):
    result = subprocess.run([str(TOKENIZER), '-m', str(MODEL), '-f', str(path),
                             '--ids', '--no-bos', '--no-escape', '--log-disable'],
                            env=environment(), capture_output=True, text=True, timeout=60, check=True)
    tokens = json.loads(result.stdout)
    if not isinstance(tokens, list) or any(type(t) is not int for t in tokens):
        raise RuntimeError('unexpected tokenizer output')
    return tokens


def command(prompt, grammar, seed):
    return [str(CLI), '--device', 'none', '--no-op-offload', '--no-kv-offload',
            '-m', str(MODEL), '-ngl', '0', '-t', '4', '-tb', '4', '-c', str(CONTEXT),
            '-b', '128', '-ub', '64', '-n', str(MAX_OUTPUT), '--seed', str(seed),
            '--temp', '0.6', '--top-k', '40', '--top-p', '0.95', '--no-conversation',
            '--no-display-prompt', '--simple-io', '--no-context-shift', '--no-escape',
            '--grammar-file', str(grammar), '-f', str(prompt)]


def answer_text(stdout):
    text = stdout.strip()
    for suffix in ('[end of text]', '<|im_end|>', '<|endoftext|>'):
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
    # Do not rescue arbitrary prose or silently pick one of multiple answers.
    try:
        value = json.loads(text)
    except ValueError:
        return text
    return canonical(value)


def load(call_id, req, seed, root, profile_sha, *, audit_tokens=False):
    folder = root / 'calls' / call_id
    value = json.loads((folder / 'result.json').read_text())
    expected = {'request_sha256': sha(req), 'seed': seed, 'profile_sha256': profile_sha}
    if any(value.get(k) != v for k, v in expected.items()):
        raise RuntimeError('model receipt does not match reconstructed request')
    if json.loads((folder / 'request.json').read_text()) != req:
        raise RuntimeError('saved request modified')
    if (folder / 'grammar.gbnf').read_text() != gbnf(req['guard_schema']):
        raise RuntimeError('grammar modified')
    if (folder / 'prompt.txt').read_text() != chat(req['prompt_variants'][value['variant']]):
        raise RuntimeError('prompt modified')
    for filename, digest in value['files'].items():
        if digest_file(folder / filename) != digest:
            raise RuntimeError('model artifact modified: ' + filename)
    if value['answer'] != answer_text((folder / 'stdout.txt').read_text()):
        raise RuntimeError('answer differs from model stdout')
    tokens = json.loads((folder / 'tokens.json').read_text())
    if value['usage']['input_tokens'] != len(tokens) or len(tokens) > MAX_INPUT:
        raise RuntimeError('input budget mismatch')
    counts = value['variant_token_counts']
    if len(counts) != value['variant'] + 1 or counts[-1] != len(tokens) \
            or any(n <= MAX_INPUT for n in counts[:-1]):
        raise RuntimeError('context compaction receipt mismatch')
    if audit_tokens and tokenize(folder / 'prompt.txt') != tokens:
        raise RuntimeError('independent tokenization differs from model receipt')
    if value['usage']['max_output_tokens'] != MAX_OUTPUT:
        raise RuntimeError('output budget changed')
    if json.loads((folder / 'command.json').read_text()) != command(folder / 'prompt.txt', folder / 'grammar.gbnf', seed):
        raise RuntimeError('command changed')
    return value


def propose(call_id, req, seed, root, profile_sha, max_calls):
    folder = root / 'calls' / call_id
    if (folder / 'result.json').exists():
        return load(call_id, req, seed, root, profile_sha)
    folder.mkdir(parents=True, exist_ok=True)
    reserved = root / 'model-budget.json'
    budget = json.loads(reserved.read_text()) if reserved.exists() else {'calls': [], 'spend_eur': 0}
    if call_id in budget['calls']:
        raise RuntimeError('interrupted model call; retain evidence and declare recovery before retry')
    if len(budget['calls']) >= max_calls:
        raise RuntimeError('model call cap reached')
    atomic(folder / 'request.json', req)
    counts = []
    for variant, text in enumerate(req['prompt_variants']):
        prompt = folder / 'prompt.txt'
        prompt.write_text(chat(text))
        tokens = tokenize(prompt)
        counts.append(len(tokens))
        if len(tokens) <= MAX_INPUT:
            break
    else:
        atomic(folder / 'context-blocked.json', {'token_counts': counts, 'limit': MAX_INPUT})
        raise RuntimeError('essential target/evidence exceeds frozen context; no truncation')
    atomic(folder / 'tokens.json', tokens)
    grammar = folder / 'grammar.gbnf'
    grammar.write_text(gbnf(req['guard_schema']))
    cmd = command(prompt, grammar, seed)
    atomic(folder / 'command.json', cmd)
    budget['calls'].append(call_id)
    atomic(reserved, budget)
    started = time.monotonic()
    with (folder / 'stdout.txt').open('w') as out, (folder / 'stderr.txt').open('w') as err:
        proc = subprocess.run(cmd, env=environment(), stdout=out, stderr=err, timeout=TIMEOUT, check=False)
    if proc.returncode:
        atomic(folder / 'failed.json', {'returncode': proc.returncode, 'seconds': time.monotonic() - started})
        raise RuntimeError('local model transport failed: ' + str(proc.returncode))
    value = {'request_sha256': sha(req), 'seed': seed, 'profile_sha256': profile_sha,
             'variant': variant, 'variant_token_counts': counts,
             'answer': answer_text((folder / 'stdout.txt').read_text()),
             'usage': {'input_tokens': len(tokens), 'max_output_tokens': MAX_OUTPUT},
             'seconds': time.monotonic() - started,
             'files': {p: digest_file(folder / p) for p in
                       ('stdout.txt', 'stderr.txt', 'tokens.json', 'prompt.txt', 'grammar.gbnf', 'command.json')}}
    atomic(folder / 'result.json', value)
    return load(call_id, req, seed, root, profile_sha)
