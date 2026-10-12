"""Bounded development pipeline and replay audit. No confirmation endpoint.

Fixture results test wiring only. Scoring is outside adaptation, references are
never mounted, and neither roles nor a successful process confer authority.
"""
from __future__ import annotations
import hashlib
import base64
import binascii
import json
from pathlib import Path
import time

from .accounting import Budget, BudgetExceeded
from .receipts import ReceiptStore, canonical, digest
from .snapshots import SnapshotStore, identity
from .runner import execute, environment_identity, DEFAULTS
from .controller import LIMITS, arm_profile, choose, authorize
from .memory import EpisodeMemory
from .tasks import FixtureProvider, development_tasks
from .provider import HTTPProvider, ProviderFailure
from .verifier import check_observation, validate_challenge, VERSION

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/'ECHO-5.1/docs/PCWORLD-1.json'

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(canonical(value)+b'\n')

def estimate(*,tasks=60,repetitions=2):
    if type(tasks) is not int or not 1<=tasks<=10000 or type(repetitions) is not int or not 1<=repetitions<=10:
        raise ValueError('invalid pilot size')
    n=tasks*repetitions*4
    return {'episodes':n,'tokens_ceiling':n*LIMITS['tokens'],'tool_calls_ceiling':n*LIMITS['tools'],
            'cpu_seconds_ceiling':n*LIMITS['cpu_us']//1000000,'llm_calls_ceiling':n*LIMITS['llm_calls'],
            'wall_seconds_ceiling_serial':n*300,'scientific_result':'pending','will_execute':False,
            'monetary_cost':'requires pinned provider pricing and real development consumption',
            'implemented_fixtures':4,'independent_tasks_required':tasks}

class Episode:
    def __init__(self,path,task,arm,provider):
        self.path,self.task,self.arm,self.provider=path,task,arm,provider
        path.mkdir(parents=True,exist_ok=False)
        self.store=SnapshotStore(path/'snapshots')
        self.receipts=ReceiptStore(path/'receipts',path/'authority')
        self.memory=EpisodeMemory(task['id'],arm);self.budget=Budget(LIMITS)
        self.trace=path/'thought.jsonl';self.used_tokens=0;self.real_calls=0;self.fixture_calls=0
        self.start=time.monotonic();self.counterexamples=[];self.last=[];self.steps=0
        self.reviewed_versions=set()
        self.host_cpu_start=time.process_time_ns()
        self.env=environment_identity();self.contract=json.loads(CONTRACT.read_text())
        initial=path/'initial';initial.mkdir();(initial/'solution.py').write_text(task['initial'])
        self.base=self.store.capture(initial)
        self.emit('observation',{'task':task['id'],'arm':arm,'snapshot':self.base.id,
                                'contract_sha256':digest(self.contract),'model':provider.model,
                                'task_sha256':digest(task),
                                'environment':self.env,'public_specification':task['description']})
    def emit(self,kind,body):
        rec=self.receipts.append({'kind':kind,**body})
        event=self.memory.record(rec,kind=kind)
        with self.trace.open('ab') as f: f.write(canonical(event)+b'\n')
        print(json.dumps({'task':self.task['id'],'arm':self.arm,'kind':kind,
                          'status':body.get('status',body.get('operation','recorded'))}),flush=True)
        return rec
    def transition(self,operation):
        self.budget.consume_fuel(operation)
        allowed=time.monotonic()-self.start<300
        event=authorize(operation,eligible=allowed)
        self.emit('decision',event)
        if not event['allowed']: raise BudgetExceeded('episode wall time')
        self.steps+=1
    def call(self,role,snapshot,*,share=True,token_cap=None):
        self.transition(role)
        available=max(0,LIMITS['tokens']-self.used_tokens)
        reserved_tokens=min(available,token_cap) if token_cap is not None else available
        if self.provider.is_llm and reserved_tokens<256: raise BudgetExceeded('tokens')
        request={'llm_calls':int(self.provider.is_llm),'tokens':reserved_tokens if self.provider.is_llm else 0,
                 'tools':int(self.provider.is_llm)}  # Prompt tokenization is charged too.
        if role=='critic': request['critic_calls']=1
        ticket=self.budget.reserve(request)
        context={'snapshot':snapshot.id,'source':self.store.read(snapshot,'solution.py').decode(),
                 'evidence':self.last[-8:] if share else [],
                 'counterexamples':self.counterexamples if share else []}
        try:
            value,usage=self.provider.call(role,self.task,context,max_tokens=min(2048,reserved_tokens or 2048),
                                          total_token_budget=reserved_tokens,deadline=self.start+300)
        except Exception as exc:
            known=getattr(exc,'usage',None)
            actual=({**request,'tokens':known['tokens'],'llm_calls':known['llm_calls']} if known else request)
            self.used_tokens+=actual['tokens'];self.real_calls+=actual['llm_calls']
            self.emit('failure',{'status':'PROVIDER_ERROR','charged':actual,'usage_known':bool(known)})
            self.budget.settle(ticket,actual)
            raise
        actual={'tokens':usage['tokens'],'llm_calls':usage['llm_calls'],'tools':int(self.provider.is_llm)}
        if role=='critic': actual['critic_calls']=1
        self.used_tokens+=actual['tokens'];self.real_calls+=actual['llm_calls']
        self.fixture_calls+=usage.get('fixture_calls',0)
        self.budget.settle(ticket,actual)
        self.emit('proposal',{'role':role,'snapshot':snapshot.id,'payload':value,'usage':usage})
        return value
    def propose(self,snapshot,**kw):
        reply=self.call('propose',snapshot,**kw)
        return self.apply_content(snapshot,reply.get('content') if isinstance(reply,dict) else None)
    def apply_content(self,snapshot,content):
        self.transition('apply_patch');ticket=self.budget.reserve({'tools':1})
        try:
            if not isinstance(content,str): raise ValueError('INVALID_PROPOSAL')
            if len(content.encode())>65536: raise ValueError('OVERSIZED_PROPOSAL')
            old=self.store.read(snapshot,'solution.py')
            result=self.store.apply(snapshot,snapshot.id,[{'path':'solution.py','expected_sha256':hashlib.sha256(old).hexdigest(),
                                    'content':content}],allowed_paths=('solution.py',))
        finally: self.budget.settle(ticket,{'tools':1})
        self.emit('observation',{'operation':'apply_patch','base_snapshot':snapshot.id,
                                'snapshot':result.id,'paths':['solution.py']})
        return result
    def check(self,snapshot,value,*,final=False):
        self.transition('run_python')
        remaining_ms=int((self.start+300-time.monotonic())*1000)
        if remaining_ms<=0: raise BudgetExceeded('episode wall time')
        execution_limits={**DEFAULTS,'wall_ms':min(DEFAULTS['wall_ms'],remaining_ms)}
        ticket=self.budget.reserve({'tools':1,'cpu_us':DEFAULTS['cpu_ms']*1000})
        try:
            observed=execute(snapshot,['/usr/bin/python3','-I','/workspace/solution.py'],
                             stdin=canonical(value),limits=execution_limits)
        except Exception:
            self.budget.settle(ticket,{'tools':1,'cpu_us':DEFAULTS['cpu_ms']*1000})
            raise
        key=identity(snapshot_id=observed['snapshot'],environment=self.env,
                     action={'argv':observed['argv'],'stdin':value},checks={'version':VERSION,'property':self.task['property']},
                     policy=self.contract,seed=0,dataset=None,task=self.task['id'])
        try:
            execution=self.emit('observation',{'status':observed['status'],'experiment_key':key,'execution':observed,
                                              'candidate_snapshot':snapshot.id,'input':value,'cache_reused':False})
        finally:
            # Preserve observed evidence even if measured CPU overshoots a ticket
            # before the watchdog terminates the complete process tree.
            self.budget.settle(ticket,{'tools':1,'cpu_us':observed['resources']['cpu_us']})
        self.transition('check_property');ticket=self.budget.reserve({'tools':1})
        try: prop=check_observation(self.task['property'],value,observed)
        finally: self.budget.settle(ticket,{'tools':1})
        receipt=self.emit('property',{'property':prop,'execution_receipt':execution['sha256'],'final_evaluation':final})
        if not final: self.last.append({**prop,'receipt':receipt['sha256']})
        return prop
    def finish(self,candidate,*,error=None):
        # These development acceptance cases are unavailable to the role context.
        # They are not a sealed scientific confirmation and cannot be reused as one.
        final=[];required=[]
        for value in self.task['public_inputs']+self.counterexamples+self.task['development_inputs']:
            if value not in required: required.append(value)
        if candidate is not None and error is None:
            try:
                for value in required: final.append(self.check(candidate,value,final=True))
            except (BudgetExceeded,RuntimeError,ValueError,OSError) as exc: error=type(exc).__name__+': '+str(exc)[:200]
        accepted=bool(final) and len(final)==len(required) and all(p['status']=='supported' for p in final) and error is None
        result={'task':self.task['id'],'arm':self.arm,'development_accepted':accepted,'error':error,
                'candidate':candidate.id if candidate else None,'final_properties':final,'required_inputs':required,
                'counterexamples':self.counterexamples,'llm_calls':self.real_calls,'fixture_calls':self.fixture_calls,
                'tokens':self.used_tokens,'budget':self.budget.report(),'wall_ms':int((time.monotonic()-self.start)*1000),
                'host_cpu_us':(time.process_time_ns()-self.host_cpu_start)//1000,
                'scientific_claim':False,'q_learning':False,'cortex_calls_native_nexus0':0,
                'destroyed':self.memory.cam.destroyed}
        self.emit('property',{'task_result':result,'scope':'four public development properties only'})
        save(self.path/'result.json',result)
        return result
    def run(self):
        current=self.base;candidate=None;error=None
        try:
            if self.arm=='I2':
                # Two isolated initial contexts, shared total budget; selector sees
                # only public checks. No final/hidden labels select a winner.
                options=[]
                for n in range(2):
                    current=self.propose(current,share=False,token_cap=LIMITS['tokens']//2)
                    score=sum(self.check(current,v)['status']=='supported' for v in self.task['public_inputs'])
                    options.append((score,-n,current))
                    # Second independent sample reads the original source, not first output.
                    if n==0:
                        current=self.apply_content(current,self.task['initial'])
                candidate=max(options,key=lambda row:(row[0],row[1]))[2]
            else:
                for attempt in range(3):
                    current=self.propose(current);candidate=current
                    props=[self.check(current,v) for v in self.task['public_inputs']+self.counterexamples]
                    status=('contradicted' if any(p['status']=='contradicted' for p in props) else
                            'supported' if all(p['status']=='supported' for p in props) else 'unknown')
                    review_used=(current.id in self.reviewed_versions or
                                 (self.arm!='S' and self.budget.report()['used']['critic_calls']>=2))
                    operation=choose(self.arm,has_candidate=True,property_status=status,critic_used=review_used)
                    if operation in ('critic','self_review'):
                        self.reviewed_versions.add(current.id)
                        challenge=self.call(operation,current)
                        valid=validate_challenge(self.task['property'],challenge)
                        if valid['status']=='eligible':
                            prop=self.check(current,valid['input'])
                            if prop['status']=='contradicted':
                                if valid['input'] not in self.counterexamples: self.counterexamples.append(valid['input'])
                                continue
                        if status=='supported': break
                    elif operation=='finish': break
        except (BudgetExceeded,ProviderFailure,ValueError,RuntimeError,OSError) as exc:
            error=type(exc).__name__+': '+str(exc)[:200]
        return self.finish(candidate,error=error)

def source_manifest():
    names=[*ROOT.joinpath('pcworld').glob('*.py'),ROOT/'echo4/code_memory.py',ROOT/'echo4/code_mcp.py',
           ROOT/'harness/localdev/runner.py',ROOT/'harness/localdev/worker.py',CONTRACT,
           ROOT/'core/cam.py',ROOT/'core/wsp.py',ROOT/'core/qn.py',ROOT/'core/dag.py',ROOT/'core/spoke.py',
           ROOT/'nexus0/gate.py',ROOT/'nexus0/attend.py',ROOT/'nexus0/constants.py']
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(names)}

def run_pilot(output,*,task_count=4,arms=('S','I2','F','E'),provider='fixture',split='development',config=None):
    if split!='development': raise ValueError('confirmation disabled; separate frozen contract required')
    tasks=development_tasks(task_count)
    for arm in arms: arm_profile(arm)
    if not arms or len(set(arms))!=len(arms): raise ValueError('distinct arms required')
    if provider=='fixture': model=FixtureProvider()
    elif provider=='http' and config: model=HTTPProvider(config)
    else: raise ValueError('explicit provider and model config required')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    root_receipts=ReceiptStore(output/'receipts',output/'authority')
    manifest=source_manifest();save(output/'sources.json',manifest)
    save(output/'contract.json',json.loads(CONTRACT.read_text()));save(output/'tasks.json',tasks)
    provider_manifest={'kind':provider,'model':model.model,'config':config or {},'contains_credentials':False}
    save(output/'provider.json',provider_manifest)
    root_receipts.append({'kind':'run_contract','tasks_sha256':digest(tasks),'sources_sha256':digest(manifest),
                         'arms':list(arms),'episode_ids':[t['id']+'-'+a for t in tasks for a in arms],
                         'contract_sha256':digest(json.loads(CONTRACT.read_text())),
                         'provider_sha256':digest(provider_manifest)})
    results=[]
    for task in tasks:
        for arm in arms:
            if manifest!=source_manifest(): raise RuntimeError('SOURCES_CHANGED: stop development run')
            results.append(Episode(output/(task['id']+'-'+arm),task,arm,model).run())
    report={'schema':'pcworld.development.v1','provider':provider,'llm_calls':sum(r['llm_calls'] for r in results),
            'episodes':results,'scientific_claim':False,'scientific_result':'pending',
            'E_minus_S':'not estimated from fixtures','E_minus_F':'not estimated from fixtures',
            'sources_unchanged':manifest==source_manifest()}
    save(output/'result.json',report)
    root_receipts.append({'kind':'run_result','result_sha256':digest(report)})
    return report

def audit_run(output):
    try:
        return _audit_run(output)
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,IndexError,RecursionError,binascii.Error) as exc:
        return {'valid':False,'errors':[{'reason':'incomplete or invalid evidence',
                                        'error':type(exc).__name__+': '+str(exc)[:200]}],
                'scientific_claim':False}

def _audit_run(output):
    output=Path(output);report=json.loads((output/'result.json').read_text());errors=[];count=0
    task_list=json.loads((output/'tasks.json').read_text());tasks={t['id']:t for t in task_list}
    root_store=ReceiptStore(output/'receipts',output/'authority')
    if not root_store.audit()['ok']: errors.append({'reason':'root receipt custody failed'})
    if (len(root_store.records)!=2 or root_store.records[1]['body'].get('result_sha256')!=digest(report)):
        errors.append({'reason':'run summary or root custody changed'})
    contract=root_store.records[0]['body']
    if contract['tasks_sha256']!=digest(task_list): errors.append({'reason':'task definitions changed'})
    if contract['provider_sha256']!=digest(json.loads((output/'provider.json').read_text())):
        errors.append({'reason':'provider configuration changed'})
    sources=json.loads((output/'sources.json').read_text())
    if contract['sources_sha256']!=digest(sources) or sources!=source_manifest():
        errors.append({'reason':'source manifest changed or auditing code differs'})
    if contract['contract_sha256']!=digest(json.loads((output/'contract.json').read_text())):
        errors.append({'reason':'contract changed'})
    if contract['episode_ids']!=[r['task']+'-'+r['arm'] for r in report['episodes']]:
        errors.append({'reason':'episode omitted, duplicated or reordered'})
    for episode in report['episodes']:
        path=output/(episode['task']+'-'+episode['arm'])
        store=ReceiptStore(path/'receipts',path/'authority');audit=store.audit()
        if not audit.get('ok'): errors.append({'episode':path.name,'reason':'receipt custody failed'})
        records=store.records;bysha={r['sha256']:r for r in records};count+=len(records)
        snapshots=SnapshotStore(path/'snapshots');checked_snapshots=set()
        for record in records:
            body=record['body']
            for field in ('snapshot','base_snapshot','candidate_snapshot'):
                snapshot_id=body.get(field)
                if snapshot_id and snapshot_id not in checked_snapshots:
                    snapshots.get(snapshot_id)
                    checked_snapshots.add(snapshot_id)
            if 'execution' in body:
                execution=body['execution']
                if execution['snapshot']!=body['candidate_snapshot']:
                    errors.append({'episode':path.name,'reason':'executed snapshot identity differs'})
                for stream in ('stdout','stderr'):
                    raw=base64.b64decode(execution[stream+'_b64'],validate=True)
                    if (hashlib.sha256(raw).hexdigest()!=execution[stream+'_sha256'] or
                            raw.decode(errors='replace')!=execution[stream]):
                        errors.append({'episode':path.name,'reason':'output bytes or digest differ'})
        if records[0]['body'].get('task_sha256')!=digest(tasks[episode['task']]):
            errors.append({'episode':path.name,'reason':'task identity mismatch'})
        final=[]
        for rec in records:
            b=rec['body']
            if b.get('kind')=='property' and 'property' in b:
                e=bysha.get(b['execution_receipt'],{}).get('body',{})
                if 'execution' not in e: errors.append({'episode':path.name,'reason':'missing execution'});continue
                expected=check_observation(tasks[episode['task']]['property'],e['input'],e['execution'])
                if expected!=b['property']: errors.append({'episode':path.name,'reason':'property replay differs'})
                if b.get('final_evaluation'): final.append(expected)
        anchored=[r['body']['task_result'] for r in records if 'task_result' in r['body']]
        if anchored!=[episode]: errors.append({'episode':path.name,'reason':'summary differs from protected receipt'})
        if final!=episode['final_properties']: errors.append({'episode':path.name,'reason':'final property list differs'})
        replay=EpisodeMemory(episode['task'],episode['arm'])
        expected_events=[replay.record(r,kind=r['body']['kind']) for r in records]
        actual_events=[json.loads(line) for line in (path/'thought.jsonl').read_text().splitlines()]
        if actual_events!=expected_events: errors.append({'episode':path.name,'reason':'WSP receipt replay mismatch'})
    return {'valid':not errors,'records':count,'episodes':len(report['episodes']),'errors':errors,
            'scope':'authenticated receipt and independent property replay; no new candidate execution',
            'scientific_claim':False}
