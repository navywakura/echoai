"""Predeclared development A->B comparison, with frozen shared evidence."""
from pathlib import Path
import json
import time
from .pilot import run_pilot,audit_run,save,source_manifest
from .receipts import ReceiptStore,digest
from .shared import SharedConceptLibrary

SEEDS=(73,74,75)
DONOR='repair-v2-records-00'
TARGET='repair-v2-records-01'

def metrics(episode):
    return {k:episode[k] for k in ('development_accepted','tokens','llm_calls','repair_attempts','wall_ms','host_cpu_us','error')} | {
        'tools':episode['budget']['used']['tools'],
        'critic_calls':episode['budget']['used']['critic_calls'],
        'accepted_without_repair':episode['development_accepted'] and episode['repair_attempts']==0,
        'counterexamples':len(episode['counterexamples'])}

def publication_matches(lesson,publication,donor_path):
    provenance=lesson.get('provenance',{})
    return (digest(lesson)==publication.get('lesson_sha256') and
        all(provenance.get(k)==v for k,v in {
            'run_dir':str(Path(donor_path).resolve()),'task_id':DONOR,
            'arm':'E','author_agent_id':'AGENT_A'}.items()))

def run_settings_match(contract,runtime_id):
    return bool(runtime_id) and all(contract.get(k)==v for k,v in {
        'runtime_snapshot':runtime_id,'arms':['E'],'suite':'repair-v2',
        'cache_properties':False,'seeded_diagnostic':False,
        'episode_wall_seconds':900,'task_families':['records']}.items())


def run_transfer(output,*,config,runtime,model_evidence=None):
    """No fallback donor, adaptive seeds, target publication or protocol shortcuts."""
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    receipts=ReceiptStore(output/'receipts',output/'authority')
    sequence=[(seed,condition) for index,seed in enumerate(SEEDS)
              for condition in (('isolated','cooperative') if index%2==0 else ('cooperative','isolated'))]
    contract={'schema':'pcworld.transfer.v1','sources':source_manifest(),'donor':DONOR,'target':TARGET,
              'task_seed':47,'sequence':sequence,'config':config,'donor_model_seed':73,
              'protocol':'expanded-v2 / unchanged E acceptance','scientific_claim':False,
              'comparison':'prior witnessed recipe vs empty library; no concept abstraction claim'}
    # Canonicalize tuples before hashing (receipt canonical JSON rejects tuples).
    contract['sequence']=[list(x) for x in sequence]
    save(output/'contract.json',contract);receipts.append({'kind':'transfer_contract','contract':contract})
    result={'schema':'pcworld.transfer-result.v1','status':'running','receivers':[],
            'scientific_claim':False,'donor_run':'donor','donor':None,'publication':None}
    save(output/'result.json',result)
    def execute(name,task,seed,library=None):
        report=run_pilot(output/name,task_count=12,arms=('E',),provider='http',
            config={**config,'seed':seed},suite='repair-v2',runtime=runtime,task_seed=47,
            task_families=['records'],task_ids=[task],probe_catalog='expanded-v2',
            episode_wall_seconds=900,model_evidence=model_evidence,shared_library=library)
        audit=audit_run(output/name);save(output/name/'audit.json',audit)
        if not audit['valid']:raise ValueError('invalid run audit: '+name)
        return report['episodes'][0]
    try:
        donor=execute('donor',DONOR,73);result['donor']=metrics(donor)
        if not donor['development_accepted'] or not donor['counterexamples_repaired']:
            result['status']='no_eligible_donor'
            return result
        shared=SharedConceptLibrary(output/'shared-library')
        empty=SharedConceptLibrary(output/'empty-library')
        start=time.monotonic_ns();cpu=time.process_time_ns()
        lesson=shared.publish_from_run(output/'donor',DONOR,'E',author_agent_id='AGENT_A')
        result['publication']={'lesson_sha256':digest(lesson),'tools':1,
            'wall_us':(time.monotonic_ns()-start)//1000,'cpu_us':(time.process_time_ns()-cpu)//1000,
            'library_identity':shared.identity(),'empty_library_identity':empty.identity()}
        receipts.append({'kind':'publication','publication':result['publication']})
        save(output/'result.json',result)
        for seed,condition in sequence:
            name=f'{seed}-{condition}'
            # Reopen and authenticate persistent evidence; target CAM is new each run.
            library=SharedConceptLibrary(output/('shared-library' if condition=='cooperative' else 'empty-library'))
            episode=execute(name,TARGET,seed,library)
            row={'run':name,'condition':condition,'seed':seed,'agent_id':f'AGENT_B_{seed}_{condition}',
                 **metrics(episode),'shared_memory':episode['shared_memory']}
            result['receivers'].append(row)
            receipts.append({'kind':'receiver_result','result':row})
            save(output/'result.json',result)
        result['status']='complete'
        return result
    except Exception as exc:
        result['status']='error';result['error']=type(exc).__name__+': '+str(exc)[:240]
        raise
    finally:
        result['sources_unchanged']=source_manifest()==contract['sources']
        save(output/'result.json',result)
        receipts.append({'kind':'transfer_result','result_sha256':digest(result)})


def audit_transfer(output):
    """Replay all underlying checks and authenticate the paired study manifest."""
    output=Path(output);errors=[];total=0
    try:
        result=json.loads((output/'result.json').read_text())
        contract=json.loads((output/'contract.json').read_text())
        journal=ReceiptStore(output/'receipts',output/'authority')
        records=journal.records
        if not journal.audit()['ok'] or records[0]['body']!={'kind':'transfer_contract','contract':contract}:
            errors.append('transfer contract custody differs')
        if records[-1]['body']!={'kind':'transfer_result','result_sha256':digest(result)}:
            errors.append('transfer result custody differs')
        expected_sequence=[[seed,condition] for i,seed in enumerate(SEEDS)
            for condition in (('isolated','cooperative') if i%2==0 else ('cooperative','isolated'))]
        if (contract['sequence']!=expected_sequence or contract['donor']!=DONOR or
            contract['target']!=TARGET or contract['task_seed']!=47 or contract['donor_model_seed']!=73):
            errors.append('study contract differs from preregistered sequence')
        if contract['sources']!=source_manifest() or not result['sources_unchanged']:
            errors.append('transfer sources changed')
        names=['donor']+[r['run'] for r in result['receivers']]
        for name in names:
            audited=audit_run(output/name);total+=audited.get('records',0)
            if not audited['valid']:errors.append({'run':name,'audit':audited})
        donor=json.loads((output/'donor/result.json').read_text())['episodes'][0]
        if result['donor']!=metrics(donor):errors.append('donor metrics differ')
        if donor['task']!=DONOR or donor['arm']!='E':errors.append('wrong donor task/arm')
        from .repairs import repair_task_variants
        from .adversarial import fixed_order
        expected_tasks={t['id']:dict(t,probe_catalog='expanded-v2',probe_order_seed=20261013)
                        for t in repair_task_variants(12,seed=47)}
        for task in expected_tasks.values():task['fixed_probe_order']=list(fixed_order(task))
        donor_contract=ReceiptStore(output/'donor/receipts',output/'donor/authority').records[0]['body']
        runtime_id=donor_contract.get('runtime_snapshot')
        for name in names:
            rc=ReceiptStore(output/name/'receipts',output/name/'authority').records[0]['body']
            if not run_settings_match(rc,runtime_id):errors.append('runtime or episode settings differ')
            expected_id=DONOR if name=='donor' else TARGET
            tasks=json.loads((output/name/'tasks.json').read_text())
            if tasks!=[expected_tasks[expected_id]]:errors.append('task differs from predeclared variant')
        dc=json.loads((output/'donor/provider.json').read_text())['config']
        if dc!={**contract['config'],'seed':73}:errors.append('donor model differs')
        if result['status']=='complete':
            if [[r['seed'],r['condition']] for r in result['receivers']]!=contract['sequence']:
                errors.append('paired order or seeds differ')
            if not donor['development_accepted'] or not donor['counterexamples_repaired']:
                errors.append('ineligible donor')
            pub=[r['body'].get('publication') for r in records if r['body'].get('kind')=='publication']
            if pub!=[result['publication']]:errors.append('publication cost custody differs')
            recorded=[r['body']['result'] for r in records if r['body'].get('kind')=='receiver_result']
            if recorded!=result['receivers']:errors.append('receiver custody differs')
            shared=SharedConceptLibrary(output/'shared-library')
            empty=SharedConceptLibrary(output/'empty-library')
            lesson=shared.lookup(expected_tasks[TARGET])
            if (len(lesson)!=1 or not publication_matches(lesson[0],result['publication'],output/'donor') or
                    result['publication']['library_identity']!=shared.identity() or
                    result['publication']['empty_library_identity']!=empty.identity() or
                    empty.lookup(expected_tasks[TARGET])):
                errors.append('frozen library conditions differ')
            for row in result['receivers']:
                run=output/row['run'];ep=json.loads((run/'result.json').read_text())['episodes'][0]
                if any(row[k]!=v for k,v in metrics(ep).items()) or row['shared_memory']!=ep['shared_memory']:
                    errors.append('receiver metrics differ')
                provider=json.loads((run/'provider.json').read_text())['config']
                if provider!={**contract['config'],'seed':row['seed']}:
                    errors.append('receiver model configuration differs')
                rc=ReceiptStore(run/'receipts',run/'authority').records[0]['body']
                lib=output/('shared-library' if row['condition']=='cooperative' else 'empty-library')
                if rc.get('shared_library',{}).get('path')!=str(lib.resolve()):
                    errors.append('wrong condition library')
                if ep['task']!=TARGET or ep['arm']!='E':errors.append('wrong target task/arm')
        elif (result['status']!='no_eligible_donor' or result['receivers'] or
              (donor['development_accepted'] and donor['counterexamples_repaired'])):
            errors.append('incomplete transfer experiment')
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,IndexError) as exc:
        errors.append(type(exc).__name__+': '+str(exc)[:200])
    return {'valid':not errors,'errors':errors,'records':total,'scientific_claim':False,
            'scope':'paired provenance and underlying run audits; not proof of general co-learning'}
