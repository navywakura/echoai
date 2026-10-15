"""Repo prompts through the inference-only relay, with persistent identities."""
import hashlib
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from ..pcworld.provider import HTTPProvider, ProviderFailure, _deadline
from ..pcworld.protocol import load_json
from ..pcworld.receipts import canonical


class ContextOverflow(ProviderFailure): pass
class InferencePending(ProviderFailure): pass


def _whole_lines(text,limit):
    kept=[];size=0
    for line in text.splitlines(keepends=True):
        cost=len(line.encode())
        if size+cost>limit:break
        kept.append(line);size+=cost
    return ''.join(kept)


def _project_messages(messages,source_limit,detail_limit):
    """Display projection only: no source bytes, authority or system policy edits."""
    projected=[]
    for message in messages:
        if message['role']!='user':projected.append(dict(message));continue
        try:context=json.loads(message['content'])
        except (ValueError,TypeError):projected.append(dict(message));continue
        if not isinstance(context,dict):projected.append(dict(message));continue
        for field in ('issue_page','issue'):
            if isinstance(context.get(field),str):
                raw=context[field].encode()
                if len(raw)>detail_limit:
                    context[field]=raw[:detail_limit].decode('utf-8',errors='ignore')
                    context[field+'_visible_bytes']=len(context[field].encode())
                    context[field+'_omitted_bytes']=len(raw)-len(context[field].encode())
        evidence=context.get('source_evidence');feedback=context.get('feedback')
        if isinstance(evidence,dict) and isinstance(evidence.get('lines'),list):
            lines=evidence['lines']
            if isinstance(feedback,dict) and feedback.get('lines') and all(x in lines for x in feedback['lines']):
                feedback.pop('lines');feedback['source_lines_receipt']=evidence.get('receipt_id')
            recent=evidence.get('recent_range') or evidence.get('locus') or {}
            start=recent.get('start',lines[0]['number'] if lines else 1);end=recent.get('end',start)
            ranked=sorted(lines,key=lambda x:(not start<=x['number']<=end,abs(x['number']-start),x['number']))
            chosen=[];size=0
            for line in ranked:
                cost=len(canonical(line))
                if size+cost>source_limit:continue
                chosen.append(line);size+=cost
            evidence['lines']=sorted(chosen,key=lambda x:x['number'])
            evidence['projection_omitted_lines']=len(lines)-len(chosen)
            if len(chosen)<len(lines):
                evidence['projection_note']='Some observed lines omitted from this prompt; file_view retrieves exact missing ranges.'
        for field in ('current_diff',):
            if isinstance(context.get(field),str):
                text=context[field];context[field]=_whole_lines(text,detail_limit)
                if context[field]!=text:context[field+'_omitted_bytes']=len(text.encode())-len(context[field].encode())
        if isinstance(context.get('candidates'),list):
            for candidate in context['candidates']:
                if isinstance(candidate,dict) and isinstance(candidate.get('patch'),str):
                    old=candidate['patch'];candidate['patch']=_whole_lines(old,detail_limit)
                    candidate['patch_omitted_bytes']=len(old.encode())-len(candidate['patch'].encode())
        if isinstance(context.get('lessons'),list):
            lessons=context['lessons'];kept=[];size=0
            for lesson in lessons:
                cost=len(canonical(lesson))
                if size+cost>detail_limit:break
                kept.append(lesson);size+=cost
            context['lessons']=kept
            if len(kept)<len(lessons):context['lessons_omitted']=len(lessons)-len(kept)
        if isinstance(feedback,dict):
            for field in ('detail','stdout','stderr','outline','summary','diagnostic'):
                if isinstance(feedback.get(field),str) and len(feedback[field].encode())>detail_limit:
                    old=feedback[field];feedback[field]=_whole_lines(old,detail_limit)
                    feedback[field+'_omitted_bytes']=len(old.encode())-len(feedback[field].encode())
            for field in ('lines','symbols','matches'):
                if isinstance(feedback.get(field),list):
                    old=feedback[field];kept=[];size=0
                    for item in old:
                        cost=len(canonical(item))
                        if size+cost>detail_limit:break
                        kept.append(item);size+=cost
                    feedback[field]=kept
                    if len(kept)<len(old):feedback[field+'_omitted']=len(old)-len(kept)
            if isinstance(feedback.get('states'),dict) and len(canonical(feedback['states']))>detail_limit:
                states=feedback['states'];kept={};size=0
                for key,value in sorted(states.items(),key=lambda x:(x[1] in ('PASSED','XFAIL'),x[0])):
                    cost=len(canonical({key:value}))
                    if size+cost>detail_limit:continue
                    kept[key]=value;size+=cost
                feedback['states']=kept;feedback['states_omitted']=len(states)-len(kept)
        projected.append({**message,'content':json.dumps(context,ensure_ascii=False,separators=(',',':'))})
    return projected


def provider_identity(config):
    # A tunnel origin/credential can rotate while the same durable relay and
    # model are retained. Experimental settings cannot change on resume.
    return {k:v for k,v in config.items() if k not in ('endpoint','tokenize_endpoint','template_endpoint','key_env')}


def validate_model_config(config,contract):
    model=contract['model']
    if (config.get('backend')!='llama_cpp' or config.get('revision')!=model['revision']
        or config.get('context_tokens')!=model['context_tokens']
        or config.get('max_output_tokens')!=model['max_output_tokens']
        or config.get('temperature_milli')!=round(model['temperature']*1000)
        or config.get('timeout_seconds')!=contract['budget_per_issue_all_roles']['provider_deadline_seconds']):
        raise ValueError('provider settings differ from the registered experiment')


def close_pending_generations(receipts,budget):
    """At a hard stop, charge unknown delivery at its reserved upper bound.

    This does not claim the worker has terminated or that usage was observed.
    A late result cannot change an already frozen submission or refund a call.
    """
    for key,binding in list(budget.bindings.items()):
        if not key.startswith('generation:') or binding['ticket'] not in budget._pending:continue
        request_id=key[len('generation:'):]
        rows=[r['body'] for r in receipts.records if r['body'].get('request_id')==request_id]
        if not rows:continue  # Another I2 branch owns that request.
        observed=[r for r in rows if r.get('event')=='repoworld.provider-response']
        if observed:
            budget.settle(binding['ticket'],observed[-1]['cost']);continue
        closed=[r for r in rows if r.get('event')=='repoworld.provider-abandoned']
        if not closed:
            cost={k:v for k,v in budget._pending[binding['ticket']].items() if k!='fuel'}
            receipts.append(dict(event='repoworld.provider-abandoned',request_id=request_id,ticket=binding['ticket'],
                cost=cost,usage_observed=False,charge_basis='reservation_upper_bound',reason='episode hard stop'))
        else:cost=closed[-1]['cost']
        budget.settle(binding['ticket'],cost)


class RepoProvider(HTTPProvider):
    def __init__(self,config):
        super().__init__(config)
        if config.get('backend')!='llama_cpp' or config.get('context_tokens')!=4096 or config['max_output_tokens']>768:
            raise ValueError('RepoWorld requires pinned llama.cpp 4096/768 configuration')

    def _retry(self,endpoint,payload,*,request_id,deadline):
        # Only a relay declaring durable request-ID deduplication is supported.
        # Payload is unwrapped by the relay; llama.cpp never receives this key.
        payload={**payload,'request_id':request_id}
        for attempt in range(4):
            try: return self._post(endpoint,payload,timeout=max(.01,min(240,deadline-time.monotonic())))
            except urllib.error.HTTPError as exc:
                if exc.code not in (429,502,503,504): raise ProviderFailure('non-retryable relay HTTP '+str(exc.code)) from exc
            except (OSError,TimeoutError,socket.timeout): pass
            left=deadline-time.monotonic()
            if attempt==3 or left<=0: raise InferencePending('remote request unresolved; same ID retained, no free retry')
            time.sleep(min(2**attempt,left))

    def verify_worker(self,contract,lock=None):
        validate_model_config(self.config,contract)
        url=urllib.parse.urlsplit(self.config['endpoint'])
        endpoint=urllib.parse.urlunsplit((url.scheme,url.netloc,'/health','',''))
        headers={}
        if self.config.get('key_env'):headers['Authorization']='Bearer '+os.environ.get(self.config['key_env'],'')
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):return None
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
        with opener.open(urllib.request.Request(endpoint,headers=headers),timeout=10) as response:
            health=load_json(response.read(65537),max_bytes=65536)
        meta=health.get('metadata') or {};model=contract['model']
        if health.get('durable_request_ids') is not True or health.get('worker_ready') is not True or health.get('stopped'):
            raise ProviderFailure('durable ready relay required')
        if meta.get('model_sha256')!=model['sha256'] or meta.get('model_revision')!=model['revision'] or meta.get('llama_release')!=model['llama_cpp_ref']:
            raise ProviderFailure('worker model/server identity mismatch')
        if [str(model['required_offloaded_layers'])]*2 not in [list(x) for x in meta.get('gpu_offload',[])]:
            raise ProviderFailure('required GPU layer offload not observed')
        if lock and meta.get('server_sha256')!=lock['llama_cpp_binary_sha256']:raise ProviderFailure('worker executable differs from lock')
        return meta

    def prepare(self,messages,request_id,deadline):
        with _deadline(deadline):
            seen=set();counts=[]
            for level,limits in enumerate((None,(6000,1800),(3000,1200),(1500,800),(600,400))):
                view=messages if limits is None else _project_messages(messages,*limits)
                digest=hashlib.sha256(canonical(view)).hexdigest()
                if digest in seen:continue
                seen.add(digest)
                if len(canonical(view))>60000:continue
                prefix=request_id if level==0 else request_id+'-fit'+str(level)
                template=self._retry(self.config['template_endpoint'],dict(messages=view,add_generation_prompt=True),
                                     request_id=prefix+'-template',deadline=deadline)['prompt']
                if type(template) is not str:raise ProviderFailure('invalid template')
                if len(template.encode())>65536:continue
                tokens=self._retry(self.config['tokenize_endpoint'],dict(content=template,add_special=False,parse_special=True),
                                   request_id=prefix+'-tokenize',deadline=deadline)['tokens']
                if not isinstance(tokens,list) or not tokens or any(type(t) is not int or t<0 for t in tokens):raise ProviderFailure('invalid tokenizer')
                counts.append(len(tokens))
                if len(tokens)<=3200:
                    self.last_context_projection=dict(compacted=level>0,level=level,token_counts=counts,
                        original_messages_sha256=hashlib.sha256(canonical(messages)).hexdigest(),projected_messages_sha256=digest)
                    return template,tokens
            raise ContextOverflow('formatted prompt cannot fit 3200 tokens without changing system policy; observed counts '+str(counts))

    def complete(self,prompt,*,schema,max_tokens,request_id,deadline,sample_seed=None):
        with _deadline(deadline):
            return self._retry(self.config['endpoint'],dict(prompt=prompt,n_predict=max_tokens,
                temperature=self.config['temperature_milli']/1000,seed=self.config['seed'] if sample_seed is None else sample_seed,
                cache_prompt=False,stream=False,json_schema=schema),request_id=request_id,deadline=deadline)

    def stop(self):
        """Ask the worker to end after its bounded in-flight operation."""
        url=urllib.parse.urlsplit(self.config['endpoint'])
        endpoint=urllib.parse.urlunsplit((url.scheme,url.netloc,'/stop','',''))
        try:
            response=self._post(endpoint,{},timeout=5)
            return dict(requested=response.get('status')=='stop',termination_confirmed=False)
        except (OSError,ProviderFailure):return dict(requested=False,termination_confirmed=False)


def generate_repo(messages,response_schema,*,budget,provider,deadline,request_id,receipts,role='agent',token_ceiling=None,sample_seed=None):
    identity=hashlib.sha256(canonical(dict(messages=messages,schema=response_schema,role=role,sample_seed=sample_seed))).hexdigest()
    rows=[r['body'] for r in receipts.records if r['body'].get('request_id')==request_id]
    ready=[r for r in rows if r.get('event')=='repoworld.provider-response']
    if ready:
        r=ready[-1]
        if r['identity']!=identity: raise ValueError('replayed generation identity differs')
        if r['ticket'] in budget._pending: budget.settle(r['ticket'],r['cost'])
        if not r['usage_valid']:raise ProviderFailure('replayed response has invalid usage')
        return r['output']
    intents=[r for r in rows if r.get('event')=='repoworld.provider-intent']
    if intents:
        intent=intents[-1]
        if intent['identity']!=identity: raise ValueError('pending generation identity differs')
        prompt=intent['prompt'];count=intent['prompt_tokens'];cap=intent['completion_cap'];ticket=intent['ticket']
    else:
        prepared=[r for r in rows if r.get('event')=='repoworld.provider-prepared']
        if prepared:
            previous=prepared[-1]
            if previous['identity']!=identity:raise ValueError('prepared generation identity differs')
            prompt=previous['prompt'];count=previous['prompt_tokens'];cap=previous['completion_cap']
        else:
            prompt,tokens=provider.prepare(messages,request_id,deadline)
            count=len(tokens)
            if not 0<count<=3200: raise ContextOverflow('full formatted prompt exceeds 3200 tokens')
            remaining=budget.report()['remaining']['tokens']
            if token_ceiling is not None: remaining=min(remaining,token_ceiling)
            cap=min(768,remaining-count)
            if cap<=0: raise ContextOverflow('no completion space in role/global allocation')
            # Fix the cost BEFORE reserving it. A crash between reservation and
            # intent must not recompute a smaller cap from already held funds.
            receipts.append(dict(event='repoworld.provider-prepared',request_id=request_id,identity=identity,
                prompt=prompt,prompt_tokens=count,completion_cap=cap,
                **({'context_projection':provider.last_context_projection} if hasattr(provider,'last_context_projection') else {})))
        costs=dict(tokens=count+cap,llm_calls=1)
        if role=='critic': costs['critic_calls']=1
        ticket=budget.reserve_for('generation:'+request_id,costs)
        intent=dict(event='repoworld.provider-intent',request_id=request_id,identity=identity,
                    prompt=prompt,prompt_tokens=count,completion_cap=cap,ticket=ticket,role=role)
        receipts.append(intent)
    # Network ambiguity leaves the reservation intact and generation resumable.
    try:response=provider.complete(prompt,schema=response_schema,max_tokens=cap,request_id=request_id,deadline=deadline,sample_seed=sample_seed)
    except ProviderFailure as exc:raise InferencePending('generation unresolved; reservation retained') from exc
    n=response.get('tokens_predicted');n_in=response.get('tokens_evaluated')
    valid=type(n) is int and 0<=n<=cap and n_in==count
    cost=dict(tokens=count+n if valid else count+cap,llm_calls=1)
    if role=='critic': cost['critic_calls']=1
    try: output=load_json(response.get('content',''),max_bytes=65536) if valid else {'invalid_response':True}
    except ValueError: output={'invalid_json':True}
    receipts.append(dict(event='repoworld.provider-response',request_id=request_id,identity=identity,
        ticket=ticket,cost=cost,output=output,usage_valid=valid,response_sha256=hashlib.sha256(canonical(response)).hexdigest()))
    budget.settle(ticket,cost)
    if not valid: raise ProviderFailure('response usage inconsistent; reservation charged')
    return output
