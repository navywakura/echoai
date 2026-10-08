"""Pinned local GGUF transport. No API, downloads, or implicit model fallback."""
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import time

from seed.s6b13_model import digest_file, chat
from seed.s6b11 import atomic
from seed.game_selfimprove import canonical, sha
from echo_arc.s6b23_search import validate_proposal

MAX_INPUT, MAX_OUTPUT, CONTEXT = 8192, 768, 9216
MAX_CALLS, TIMEOUT = 36, 900


def gguf_info(path):
    """Inspect metadata and tensor shapes, never allocate/read weight tensors."""
    scalar = {0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}
    with Path(path).open('rb') as stream:
        def unpack(fmt):
            size = struct.calcsize('<'+fmt); data = stream.read(size)
            if len(data) != size: raise ValueError('truncated GGUF')
            return struct.unpack('<'+fmt, data)[0]
        def string():
            size = unpack('Q')
            if size > 16*1024*1024: raise ValueError('GGUF string too large')
            data = stream.read(size)
            if len(data) != size: raise ValueError('truncated GGUF string')
            return data.decode('utf-8')
        def value(kind, depth=0):
            if kind in scalar: return unpack(scalar[kind])
            if kind == 8: return string()
            if kind == 9 and depth == 0:
                element, count = unpack('I'), unpack('Q')
                if count > 2_000_000: raise ValueError('GGUF array too large')
                for _ in range(count): value(element, 1)
                return None
            raise ValueError('unsupported GGUF metadata type')
        if stream.read(4) != b'GGUF' or unpack('I') != 3: raise ValueError('GGUF v3 required')
        tensors, keys = unpack('Q'), unpack('Q')
        if tensors > 200_000 or keys > 100_000: raise ValueError('invalid GGUF header')
        meta = {}
        for _ in range(keys):
            key = string(); item = value(unpack('I'))
            if key.startswith('general.') or key == 'tokenizer.chat_template': meta[key] = item
        params = 0
        for _ in range(tensors):
            string(); dimensions = unpack('I')
            if not 1 <= dimensions <= 4: raise ValueError('invalid tensor dimensions')
            params += math.prod(unpack('Q') for _ in range(dimensions))
            unpack('I'); unpack('Q')
        return dict(parameters=params, architecture=meta.get('general.architecture'),
                    file_type=meta.get('general.file_type'), name=meta.get('general.name'),
                    template_sha256=sha(meta.get('tokenizer.chat_template')))


def verify_pair(registry):
    if set(registry) != {'N7','N14'}: raise ValueError('both N7 and N14 required')
    common = ('family','quantization','backend','cli_sha256','tokenizer_sha256','gpu_layers','tensor_split')
    for key in common:
        if registry['N7'][key] != registry['N14'][key]: raise ValueError('model pair differs: '+key)
    if registry['N7']['family'] != 'Qwen2.5-Coder-Instruct': raise ValueError('frozen family required')
    if registry['N7']['quantization'] != 'Q4_K_M': raise ValueError('frozen quantization required')
    for arm, spec in registry.items():
        size=7 if arm=='N7' else 14
        if spec['repo']!=f'Qwen/Qwen2.5-Coder-{size}B-Instruct-GGUF': raise ValueError('wrong model repository')
        if spec['backend'] not in ('cpu','cuda'): raise ValueError('unsupported backend')
        if type(spec['gpu_layers']) is not int or not 0 <= spec['gpu_layers'] <= 999: raise ValueError('gpu layers')
        if not re.fullmatch(r'\d+(?:,\d+)*', spec['tensor_split']): raise ValueError('tensor split')
        if not re.fullmatch(r'[0-9a-f]{40}', spec['revision']): raise ValueError('immutable model revision required')
        for key in ('model','cli','tokenizer'):
            if not re.fullmatch(r'[0-9a-f]{64}', spec[key+'_sha256']): raise ValueError('asset digest required')
            if digest_file(Path(spec[key])) != spec[key+'_sha256']: raise ValueError('asset changed: '+key)
        info = gguf_info(spec['model']); low, high = (6e9,9e9) if arm=='N7' else (12e9,16e9)
        if not low <= info['parameters'] <= high or info['architecture'] != 'qwen2' or info['file_type'] != 15:
            raise ValueError('GGUF architecture, size or quantization mismatch: '+arm)
        if info != spec['gguf']: raise ValueError('GGUF metadata changed')
    # --no-conversation consumes our rendered ChatML, not the embedded Jinja.
    # Retain each embedded template's hash, but validate the effective protocol.
    for spec in registry.values():
        if spec.get('prompt_protocol') != prompt_protocol(spec):
            raise ValueError('effective prompt protocol changed')
    if registry['N7']['prompt_protocol'] != registry['N14']['prompt_protocol']:
        raise ValueError('effective ChatML tokenization differs')
    if registry['N7']['model_sha256'] == registry['N14']['model_sha256']: raise ValueError('same weights in both arms')
    return True


def config():
    return dict(max_input_tokens=MAX_INPUT,max_output_tokens=MAX_OUTPUT,context=CONTEXT,
                max_calls=MAX_CALLS,timeout_seconds=TIMEOUT,temperature=0.6,top_k=40,top_p=0.95,
                threads=4,template='explicit ChatML, JSON only',grammar_constraint=False,
                template_validation='rendered ChatML and special tokens; R3',
                overflow='stop before inference; never silently truncate',fallback=False)


def tokenize(spec, path, *, add_special=False):
    result = subprocess.run([spec['tokenizer'],'-m',spec['model'],'-f',str(path),'--ids',
                             *([] if add_special else ['--no-bos']),
                             '--no-escape','--log-disable'],capture_output=True,text=True,timeout=120,check=True)
    ids = json.loads(result.stdout)
    if not isinstance(ids,list) or any(type(x) is not int for x in ids): raise ValueError('invalid tokenizer output')
    return ids


def prompt_protocol(spec):
    """Tokenizer-only preflight: no generation, games or research feedback."""
    probe = chat('{"protocol_probe":"B23","values":[0,1,-2]}')
    with tempfile.TemporaryDirectory(prefix='b23-chatml-') as tmp:
        path = Path(tmp)/'input.txt'
        markers = {}
        for marker in ('<|im_start|>', '<|im_end|>'):
            path.write_text(marker, encoding='utf-8')
            ids = tokenize(spec, path)
            if len(ids) != 1:
                raise ValueError('ChatML marker is not one special token: '+marker)
            markers[marker] = ids[0]
        start, end = markers.values()
        if start == end:
            raise ValueError('ChatML role boundaries collide')
        path.write_text(probe, encoding='utf-8')
        ids = tokenize(spec, path)
        if not ids or ids[0] != start or ids.count(start) != 3 or ids.count(end) != 2:
            raise ValueError('rendered ChatML boundaries changed')
        # llama-cli adds model-declared special tokens. Prove that this matches
        # the no-BOS token counting used for the frozen input budget.
        if tokenize(spec, path, add_special=True) != ids:
            raise ValueError('CLI special-token handling differs from token budget')
    return dict(version='B23-CHATML-R3', renderer_sha256=sha(chat('')),
                probe_sha256=sha(probe), markers=markers, probe_tokens=ids,
                embedded_template_used=False, automatic_special_tokens_match=True)


def command(spec, prompt, seed):
    device = (['--device','none','--no-op-offload','--no-kv-offload','-ngl','0'] if spec['backend']=='cpu' else
              ['-ngl',str(spec['gpu_layers']),'--split-mode','layer','--tensor-split',spec['tensor_split']])
    return [spec['cli'],'-m',spec['model'],*device,'-t','4','-tb','4','-c',str(CONTEXT),'-b','128','-ub','64',
            '-n',str(MAX_OUTPUT),'--seed',str(seed),'--temp','0.6','--top-k','40','--top-p','0.95',
            '--no-conversation','--no-display-prompt','--simple-io','--no-context-shift','--no-escape','-f',str(prompt)]


def strict_answer(stdout):
    def pairs(items):
        result = {}
        for key,value in items:
            if key in result: raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    text = stdout.strip()
    for suffix in ('[end of text]','<|im_end|>','<|endoftext|>'):
        if text.endswith(suffix): text = text[:-len(suffix)].strip()
    return validate_proposal(json.loads(text,object_pairs_hook=pairs,
                                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x))))


def load(folder, req, arm, seed, profile):
    value = json.loads((folder/'result.json').read_text())
    for key, expected in dict(request_sha256=sha(req),arm=arm,seed=seed,profile_sha256=profile).items():
        if value[key] != expected: raise RuntimeError('model receipt mismatch: '+key)
    if (folder/'prompt.txt').read_text() != chat(req['prompt']): raise RuntimeError('prompt bytes changed')
    for filename, digest in value['files'].items():
        if digest_file(folder/filename) != digest: raise RuntimeError('model artifact changed: '+filename)
    required={'prompt.txt','tokens.json','command.json','stdout.txt','stderr.txt','output-tokens.json'}
    if set(value['files'])!=required: raise RuntimeError('incomplete model receipt')
    tokens=json.loads((folder/'tokens.json').read_text()); output=json.loads((folder/'output-tokens.json').read_text())
    if set(tokens)!={'N7','N14'} or any(len(t)>MAX_INPUT for t in tokens.values()): raise RuntimeError('input token limits')
    if value['usage']['model_calls']!=1 or value['usage']['max_output_tokens']!=MAX_OUTPUT \
            or value['usage']['input_tokens']!=len(tokens[arm]) or value['usage']['output_tokens']!=len(output):
        raise RuntimeError('model usage receipt mismatch')
    if value['transport_ok']:
        try: proposal = strict_answer((folder/'stdout.txt').read_text())
        except (ValueError,KeyError,TypeError): proposal = None
        if proposal != value['proposal']: raise RuntimeError('model parse receipt changed')
    return value


def propose(root, registry, arm, slot, req, seed, profile):
    folder = root/'calls'/arm/f'{slot:03d}'; call_id = f'{arm}/{slot:03d}'
    if (folder/'result.json').exists(): return load(folder,req,arm,seed,profile)
    ledger_path=root/'model-budget.json'
    if ledger_path.exists() and call_id in json.loads(ledger_path.read_text())['calls']:
        raise RuntimeError('interrupted model call; explicit recovery required')
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'prompt.txt').write_text(chat(req['prompt']))
    # Both tokenizers must fit the identical semantic prompt, including feedback.
    tokens = {k:tokenize(s,folder/'prompt.txt') for k,s in registry.items()}
    atomic(folder/'tokens.json',tokens)
    if any(len(t)>MAX_INPUT for t in tokens.values()):
        atomic(folder/'context-blocked.json',dict(counts={k:len(v) for k,v in tokens.items()},limit=MAX_INPUT))
        raise RuntimeError('essential prompt exceeds frozen context')
    with (root/'model-budget.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        path = root/'model-budget.json'
        ledger = json.loads(path.read_text()) if path.exists() else dict(calls=[],spend_eur=0)
        if call_id in ledger['calls']: raise RuntimeError('interrupted model call; explicit recovery required')
        if len(ledger['calls'])>=MAX_CALLS or sum(x.startswith(arm+'/') for x in ledger['calls'])>=ROUNDS:
            raise RuntimeError('model call budget exhausted')
        ledger['calls'].append(call_id); atomic(path,ledger)
    spec=registry[arm]; cmd=command(spec,folder/'prompt.txt',seed)
    atomic(folder/'command.json',cmd)
    start=time.monotonic(); error=None; proposal=None; returncode=None
    with (folder/'stdout.txt').open('w') as out,(folder/'stderr.txt').open('w') as err:
        try:
            proc=subprocess.run(cmd,stdout=out,stderr=err,timeout=TIMEOUT,check=False)
            returncode=proc.returncode
            if returncode: error='transport return code '+str(returncode)
        except (subprocess.TimeoutExpired,OSError) as exc: error=type(exc).__name__
    elapsed=time.monotonic()-start
    transport_ok=error is None
    if transport_ok:
        try: proposal=strict_answer((folder/'stdout.txt').read_text())
        except (ValueError,KeyError,TypeError) as exc: error='invalid proposal: '+str(exc)
    # Output tokenization is measured too; a damaged tokenizer is an instrument
    # failure, not a zero-cost failed model proposal.
    output_tokens=tokenize(spec,folder/'stdout.txt')
    atomic(folder/'output-tokens.json',output_tokens)
    value=dict(arm=arm,seed=seed,request_sha256=sha(req),profile_sha256=profile,proposal=proposal,
               transport_ok=transport_ok,error=error,returncode=returncode,seconds=elapsed,
               usage=dict(model_calls=1,input_tokens=len(tokens[arm]),output_tokens=len(output_tokens),
                          max_output_tokens=MAX_OUTPUT,gpu_allocation_seconds_upper_bound=(len(spec['tensor_split'].split(','))*elapsed if spec['backend']=='cuda' else 0)),
               files={name:digest_file(folder/name) for name in ('prompt.txt','tokens.json','command.json','stdout.txt','stderr.txt','output-tokens.json')})
    atomic(folder/'result.json',value)
    return load(folder,req,arm,seed,profile)


ROUNDS = 18
