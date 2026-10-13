"""Read-only custody replay and measured export; no missing-key creation."""
import hashlib
import json
from pathlib import Path
from ..pcworld.receipts import canonical, _atomic_write
from .evaluator import existing_receipts,validate_frozen_set
from .accounting import LIMITS
from .calibration import source_manifest
from .dataset import sha256_file


def audit_episode(directory):
    directory=Path(directory);store=existing_receipts(directory);rows=store.records
    finals=[r for r in rows if r['body'].get('event')=='repoworld.episode-frozen']
    if len(finals)!=1:raise ValueError('episode not frozen exactly once')
    saved=json.loads((directory/'submission.json').read_bytes())
    result=finals[0]['body']['result']
    if saved!={'result':result,'receipt_id':finals[0]['sha256']}:raise ValueError('submission custody mismatch')
    if hashlib.sha256(result['model_patch'].encode()).hexdigest()!=result['diff_sha256']:raise ValueError('submission patch hash')
    budget=result['budget']
    if budget['limits']!=LIMITS or budget['pending'] or budget['frozen'] or budget['overruns'] or any(budget['used'].get(k,0)>v for k,v in LIMITS.items()):raise ValueError('invalid/pending episode budget')
    budgets=[r['body']['state'] for r in rows if r['body'].get('event')=='repoworld.budget']
    if not budgets or budgets[-1]['_used']!=budget['used']:raise ValueError('budget checkpoint mismatch')
    tokens=calls=0;requests=set();records=len(rows);regressions=set();blocked=set();proposals=set();branch_finals=[]
    paths=[directory/'main'] if result['arm']!='I2' else [directory/'branch-0',directory/'branch-1']
    all_rows=list(rows)
    from .workspace import Workspace
    for path in paths:
        journal=existing_receipts(path);entries=journal.records;records+=len(entries);all_rows+=entries
        frozen=[r['body']['result'] for r in entries if r['body'].get('event')=='repoworld.branch-frozen']
        if len(frozen)!=1:raise ValueError('missing/duplicate branch freeze')
        branch_finals.append(frozen[0])
        # Workspace constructor would create missing authority; already checked.
        ws=Workspace(path)
        if ws.current.id!=frozen[0]['candidate_id'] or ws.final_diff()!=frozen[0]['model_patch']:raise ValueError('retained snapshot/export mismatch')
        for r in entries:
            b=r['body'];event=b.get('event')
            if event=='repoworld.stage':proposals.add((str(path),b['candidate']))
            if event=='repoworld.public-decision' and b['status']=='PUBLIC_REGRESSION':
                key=(str(path),b['candidate']);regressions.add(key)
                if not b['retain']:blocked.add(key)
            if event=='repoworld.public-check' and 'observation' in b:
                if hashlib.sha256(canonical(b['observation'])).hexdigest()!=b['evidence_blob_sha256']:raise ValueError('public execution blob hash')
                if not b['observation']['isolation']['job_empty']:raise ValueError('surviving process evidence')
    usage_complete=True
    for r in all_rows:
        b=r['body']
        if b.get('event') in ('repoworld.provider-response','repoworld.provider-abandoned'):
            abandoned=b['event']=='repoworld.provider-abandoned'
            if b['request_id'] in requests or (not abandoned and not b['usage_valid']):raise ValueError('duplicate or invalid usage')
            if abandoned:
                usage_complete=False
                bindings=[r['body']['bindings'].get('generation:'+b['request_id']) for r in rows if r['body'].get('event')=='repoworld.budget']
                binding=next((v for v in reversed(bindings) if v),None)
                if not binding or binding['ticket']!=b['ticket'] or binding['request']!=b['cost']:raise ValueError('unknown delivery charge differs from original reservation')
            requests.add(b['request_id']);tokens+=b['cost']['tokens'];calls+=1
    if tokens!=budget['used']['tokens'] or calls!=budget['used']['llm_calls']:raise ValueError('role/token totals differ from accounting')
    selected=branch_finals[result.get('selected_branch',0)]
    if selected['diff_sha256']!=result['diff_sha256']:raise ValueError('selected branch differs from submission')
    return dict(valid=True,token_usage_complete=usage_complete,result=result,receipts=records,proposed_patches=len(proposals),
                public_regressions=len(regressions),regressions_blocked=len(blocked))


def audit_study(directory,sealed_dir,sample_path,*,export=None):
    directory=Path(directory);sealed_dir=Path(sealed_dir)
    from .study import validate_seal,require_gate,study_identity
    seal=validate_seal(sealed_dir,sample_path)
    contract=json.loads((sealed_dir/'SWE-CONTRACT.json').read_bytes());lock=json.loads((sealed_dir/'SWE-RUN-LOCK.json').read_bytes())
    schedule=json.loads((sealed_dir/'schedule.json').read_bytes());sample=json.loads(Path(sample_path).read_bytes())
    if hashlib.sha256(canonical(source_manifest())).hexdigest()!=lock['code_manifest_sha256']:raise ValueError('source identity mismatch')
    validate_frozen_set(directory/'frozen',schedule,lock_sha256=hashlib.sha256(canonical(lock)).hexdigest())
    frozen=json.loads((directory/'frozen/freeze.json').read_bytes())['value']['entries']
    run=existing_receipts(directory)
    offline=require_gate(seal['gates']['offline-preflight']['directory'],'offline-preflight')
    calibration=require_gate(seal['gates']['remote-calibration']['directory'],'remote-calibration')
    identity=study_identity(sealed_dir,offline['registry_sha256'],calibration['model_config_sha256'])
    starts=[r['body'] for r in run.records if r['body'].get('event')=='repoworld.study-start']
    if starts!=[dict(event='repoworld.study-start',identity=identity)]:raise ValueError('study journal belongs to another lock/configuration')
    completed={r['body']['cell_id']:r['body'] for r in run.records if r['body'].get('event') in ('repoworld.cell-completed','repoworld.cell-not-started')}
    if set(completed)!={r['cell_id'] for r in schedule}:raise ValueError('incomplete authenticated schedule')
    episodes={}
    for cell in schedule:
        key=cell['cell_id'];unstarted=completed[key]['event']=='repoworld.cell-not-started'
        if unstarted:
            if any(r['body'].get('event')=='repoworld.cell-start' and r['body']['cell_id']==key for r in run.records):raise ValueError('attempted row claimed as not_started')
            result=completed[key]['result']
            if result['status']!='not_started' or result['model_patch'] or any(result['budget']['used'].values()):raise ValueError('invalid not_started evidence')
            episode=dict(valid=True,token_usage_complete=True,result=result,receipts=1,proposed_patches=0,public_regressions=0,regressions_blocked=0)
        else:episode=audit_episode(directory/'episodes'/key)
        if hashlib.sha256(canonical(episode['result'])).hexdigest()!=completed[key]['submission_sha256']:raise ValueError('cell submission changed')
        seal=frozen[key]
        if seal['submission_sha256']!=completed[key]['submission_sha256'] or seal['diff_sha256']!=episode['result']['diff_sha256'] or (seal['instance_id'],seal['arm'])!=(cell['instance_id'],cell['arm']):
            raise ValueError('frozen patch does not match authenticated episode')
        if (episode['result']['instance_id'],episode['result']['arm'],episode['result']['seed'])!=(cell['instance_id'],cell['arm'],cell['seed']):raise ValueError('cell assignment mismatch')
        if not unstarted:
            initial=next(r['body']['identity'] for r in existing_receipts(directory/'episodes'/key).records if r['body'].get('event')=='repoworld.episode-start')
            locked=next(r for r in lock['instances'] if r['instance_id']==cell['instance_id'])
            if initial['runtime']!=locked['online_rootfs_sha256'] or initial['base_id']!=locked['online_tree_sha256'] or initial['check_plan_sha256']!=locked['public_checks_sha256']:
                raise ValueError('episode runtime/base/checks differ from study lock')
            if hashlib.sha256(canonical(initial['provider'])).hexdigest()!=calibration['model_config_sha256']:
                raise ValueError('episode provider differs from calibrated experiment')
        episodes[key]=episode
    report=dict(valid=True,episodes=len(episodes),receipts=sum(e['receipts'] for e in episodes.values()),
                official_evaluation=False,source_manifest=source_manifest(),
                not_started=sum(e['result']['status']=='not_started' for e in episodes.values()),
                unknown_usage_episodes=sum(not e['token_usage_complete'] for e in episodes.values()))
    if export is not None:
        # Final outcomes must be sealed by the curator, not arbitrary JSON given
        # to the plotter. The online runner cannot append to this authority.
        finals=existing_receipts(directory/'curator-results')
        outcomes={r['body']['cell_id']:r['body']['outcome'] for r in finals.records if r['body'].get('event')=='repoworld.final-outcome'}
        if set(outcomes)!=set(episodes):raise ValueError('official outcomes incomplete')
        for key,evidence in episodes.items():
            if outcomes[key]['patch_sha256']!=evidence['result']['diff_sha256']:raise ValueError('curator graded a different patch')
        report['official_evaluation']=True;report['curator_head']=finals.head
        report_sha=hashlib.sha256(canonical(report)).hexdigest()
        data=dict(schema_version='repoworld.analysis.v1',data_kind='measured',
            contract_sha256=sha256_file(sealed_dir/'SWE-CONTRACT.json'),audit_report_sha256=report_sha,
            primary_instances=[r['instance_id'] for r in sample['primary']],primary_seeds=contract['model']['seeds'],
            primary=[],memory_chains=[],memory=[])
        for cell in schedule:
            evidence=episodes[cell['cell_id']];result=evidence['result'];outcome=outcomes[cell['cell_id']]
            status='not_started' if result['status']=='not_started' else 'resolved' if outcome['echo_verified_resolved'] else 'unresolved'
            reason=outcome['validity_reason']+(' ; token cost includes an unobserved reservation upper bound' if not evidence['token_usage_complete'] else '')
            row=dict(instance_id=cell['instance_id'],status=status,
                tokens=result['budget']['used']['tokens'],wall_seconds=result['wall_seconds'],
                official_raw_resolved=outcome['official_raw_resolved'],echo_verified_resolved=outcome['echo_verified_resolved'],validity_reason=reason)
            if cell['phase']=='primary':data['primary'].append(dict(row,repo=cell['repo'],arm=cell['arm'],seed=cell['seed'],
                **{k:evidence[k] for k in ('proposed_patches','public_regressions','regressions_blocked')}))
            if cell['phase']=='memory':data['memory'].append(dict(row,chain_id=cell['chain_id'],position=cell['position'],condition=cell['condition']))
        for chain in sample['memory_chains']:
            donors=[episodes[c['cell_id']]['result'] for c in schedule if c['phase']=='memory_donor' and c['chain_id']==chain['chain_id']]
            data['memory_chains'].append(dict(chain_id=chain['chain_id'],repo=chain['donor']['repo'],
                donor_tokens=sum(d['budget']['used']['tokens'] for d in donors),donor_wall_seconds=sum(d['wall_seconds'] for d in donors),
                target_instances=[r['instance_id'] for r in chain['targets']]))
        import jsonschema
        schema=Path(__file__).resolve().parents[1]/'ECHO-5.1/docs/swebench/SWE-RESULTS.schema.json'
        jsonschema.Draft202012Validator(json.loads(schema.read_bytes())).validate(data)
        _atomic_write(Path(export),canonical(data));_atomic_write(Path(export).with_suffix('.audit.json'),canonical(report))
    return report
