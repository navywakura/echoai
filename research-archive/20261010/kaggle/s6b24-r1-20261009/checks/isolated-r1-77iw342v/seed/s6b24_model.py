"""B24 single pinned 7B transport, exact menu reconstruction and bounded accounting."""
import fcntl
import json
from pathlib import Path
import subprocess
import time
from seed import s6b23_model as prior, s6b23r4_model as r4
from echo_arc import s6b24_search as search
from seed.s6b11 import atomic
from seed.game_selfimprove import sha

MAX_INPUT,MAX_OUTPUT,CONTEXT,TIMEOUT=prior.MAX_INPUT,prior.MAX_OUTPUT,prior.CONTEXT,prior.TIMEOUT
MODEL_SHA='509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c'
REVISION='13fb94bfda8c8cf22497dc57b78f391a9acb426a'
MAX_CALLS=72


def config():
    return dict(prior.config(),max_calls=MAX_CALLS,model_revision=REVISION,model_sha256=MODEL_SHA,
                grammar_constraint=True,model='N7',protocols=['r4-json','candidate-id'],
                logical_batch_size=MAX_INPUT,microbatch_size=64,transport_revision='B24-R1',
                invalid_output='instrument stop; exact reconstruction; no retry')


def verify_registry(registry):
    if set(registry)!={'N7'}:raise ValueError('exactly the frozen 7B required')
    s=registry['N7']
    expected=dict(repo='Qwen/Qwen2.5-Coder-7B-Instruct-GGUF',revision=REVISION,
                  model_sha256=MODEL_SHA,family='Qwen2.5-Coder-Instruct',quantization='Q4_K_M',
                  backend='cuda',gpu_layers=99,tensor_split='1,1')
    for key,value in expected.items():
        if s.get(key)!=value:raise ValueError('model profile differs: '+key)
    for key in ('model','cli','tokenizer'):
        if prior.digest_file(Path(s[key]))!=s[key+'_sha256']:raise ValueError('asset changed: '+key)
    info=prior.gguf_info(s['model'])
    if info!=s['gguf'] or info['parameters']!=7615616512 or info['file_type']!=15 or info['architecture']!='qwen2':
        raise ValueError('GGUF metadata changed')
    if s['prompt_protocol']!=prior.prompt_protocol(s):raise ValueError('ChatML protocol changed')
    return True


def grammar(req):
    if req['selection_protocol']=='r4-json':return r4.grammar()
    if req['selection_protocol']!='candidate-id' or not req['menu']:raise ValueError('unknown/empty selection')
    ids=[item['id'] for item in req['menu']]
    if len(set(ids))!=len(ids):raise ValueError('duplicate candidate ID')
    lit=json.dumps
    return ('root ::= ws '+lit('{')+' ws '+lit('"candidate_id"')+' ws '+lit(':')+' ws choice ws '+lit('}')+' ws\n'
            'choice ::= '+' | '.join(lit(json.dumps(i)) for i in ids)+'\nws ::= [ \\t\\n\\r]{0,4}\n')


def command(spec,prompt,seed,req):
    cmd=prior.command(spec,prompt,seed)
    cmd[cmd.index('-b')+1]=str(MAX_INPUT)  # R1: keep prompt EOG off intermediate chunks.
    return cmd[:-2]+['--grammar',grammar(req)]+cmd[-2:]


def answer(stdout,req):
    if req['selection_protocol']=='r4-json':return prior.strict_answer(stdout)
    text=stdout.strip()
    for suffix in ('[end of text]','<|im_end|>','<|endoftext|>'):
        if text.endswith(suffix):text=text[:-len(suffix)].strip()
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    selection=json.loads(text,object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    return search.reconstruct(req,selection)


def load(folder,req,arm,seed,profile):
    v=json.loads((folder/'result.json').read_text())
    for key,expected in dict(request_sha256=sha(req),arm=arm,seed=seed,profile_sha256=profile).items():
        if v[key]!=expected:raise RuntimeError('model receipt mismatch: '+key)
    if (folder/'prompt.txt').read_text()!=prior.chat(req['prompt']):raise RuntimeError('prompt bytes changed')
    required={'prompt.txt','tokens.json','command.json','stdout.txt','stderr.txt','output-tokens.json'}
    if set(v['files'])!=required:raise RuntimeError('incomplete model receipt')
    for name,h in v['files'].items():
        if prior.digest_file(folder/name)!=h:raise RuntimeError('model artifact changed: '+name)
    t=json.loads((folder/'tokens.json').read_text());out=json.loads((folder/'output-tokens.json').read_text())
    if set(t)!={'N7'} or len(t['N7'])>MAX_INPUT:raise RuntimeError('input token limits')
    if v['usage']['model_calls']!=1 or v['usage']['input_tokens']!=len(t['N7']) or v['usage']['output_tokens']!=len(out) or v['usage']['max_output_tokens']!=MAX_OUTPUT:
        raise RuntimeError('usage receipt mismatch')
    if v['transport_ok']:
        try: proposal=answer((folder/'stdout.txt').read_text(),req)
        except (ValueError,KeyError,TypeError):proposal=None
        if proposal!=v['proposal']:raise RuntimeError('parse receipt changed')
    return v


def propose(root,registry,arm,slot,req,seed,profile):
    folder=root/'calls'/arm/f'{slot:03d}';call_id=f'{arm}/{slot:03d}'
    if (folder/'result.json').exists():
        result=load(folder,req,arm,seed,profile)
        if not result['transport_ok'] or result['proposal'] is None:raise RuntimeError('prior failed model call; explicit recovery required')
        if json.loads((folder/'command.json').read_text())!=command(registry['N7'],folder/'prompt.txt',seed,req):
            raise RuntimeError('model command changed')
        return result
    ledger_path=root/'model-budget.json'
    if ledger_path.exists() and call_id in json.loads(ledger_path.read_text())['calls']:
        raise RuntimeError('interrupted model call; explicit recovery required')
    folder.mkdir(parents=True,exist_ok=True);spec=registry['N7']
    (folder/'prompt.txt').write_text(prior.chat(req['prompt']))
    tokens=prior.tokenize(spec,folder/'prompt.txt');atomic(folder/'tokens.json',{'N7':tokens})
    if len(tokens)>MAX_INPUT:
        atomic(folder/'context-blocked.json',dict(tokens=len(tokens),limit=MAX_INPUT))
        raise RuntimeError('essential prompt exceeds frozen context')
    with (root/'model-budget.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else dict(calls=[],spend_eur=0)
        if call_id in ledger['calls']:raise RuntimeError('interrupted model call; explicit recovery required')
        if len(ledger['calls'])>=MAX_CALLS or sum(x.startswith(arm+'/') for x in ledger['calls'])>=18:
            raise RuntimeError('model call budget exhausted')
        ledger['calls'].append(call_id);atomic(ledger_path,ledger)
    cmd=command(spec,folder/'prompt.txt',seed,req);atomic(folder/'command.json',cmd)
    started=time.monotonic();error=None;proposal=None;returncode=None
    with (folder/'stdout.txt').open('w') as out,(folder/'stderr.txt').open('w') as err:
        try:
            returncode=subprocess.run(cmd,stdout=out,stderr=err,timeout=TIMEOUT,check=False).returncode
            if returncode:error='transport return code '+str(returncode)
        except (subprocess.TimeoutExpired,OSError) as exc:error=type(exc).__name__
    elapsed=time.monotonic()-started;transport_ok=error is None
    if transport_ok:
        try:proposal=answer((folder/'stdout.txt').read_text(),req)
        except (ValueError,KeyError,TypeError) as exc:error='invalid selection: '+str(exc)
    output_tokens=prior.tokenize(spec,folder/'stdout.txt');atomic(folder/'output-tokens.json',output_tokens)
    result=dict(arm=arm,seed=seed,request_sha256=sha(req),profile_sha256=profile,proposal=proposal,
                transport_ok=transport_ok,error=error,returncode=returncode,seconds=elapsed,
                usage=dict(model_calls=1,input_tokens=len(tokens),output_tokens=len(output_tokens),max_output_tokens=MAX_OUTPUT,
                           gpu_allocation_seconds_upper_bound=2*elapsed),
                files={name:prior.digest_file(folder/name) for name in ('prompt.txt','tokens.json','command.json','stdout.txt','stderr.txt','output-tokens.json')})
    atomic(folder/'result.json',result);load(folder,req,arm,seed,profile)
    if not transport_ok or proposal is None:raise RuntimeError('B24 instrument failure: '+str(error))
    return result
