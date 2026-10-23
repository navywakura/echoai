"""Prepare at most one retry, selected solely by fresh public-case failures.

Never consult development/hidden outcomes for routing or feedback. No submission.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
runpy.run_path(str(ROOT/'ECHO-5.1/scripts/run.py'))
from echoai.pcworld.pilot import Episode, save
from echoai.pcworld.tasks import FixtureProvider
from echoai.pcworld.receipts import digest
from echoai.pcworld.runtime import load_runtime
from echoai.pcworld.verifier import check_observation


def prepare(run, inputs, downloaded, runtime_path, output, slug):
    bundle=json.loads(inputs.read_text());report=json.loads(downloaded.read_text())
    if report.get('input_sha256')!=hashlib.sha256(inputs.read_bytes()).hexdigest():
        raise ValueError('input binding differs')
    tasks={t['id']:t for t in json.loads((run/'tasks.json').read_text())}
    records={r['task']:r for r in report['records']}
    runtime=load_runtime(runtime_path);jobs=[]
    evidence=output.with_name(output.name+'-public-evidence');evidence.mkdir(exist_ok=False)
    for job in bundle['jobs']:
        record=records[job['id']]
        if record['job_sha256']!=digest(job): raise ValueError('job binding differs')
        if job['context'].get('sample_index',0)!=0: raise ValueError('only one retry allowed')
        if record.get('error'): continue
        task={**tasks[job['id']],'initial':job['context']['source']}
        ep=Episode(evidence/task['id'],task,'E',FixtureProvider(),runtime=runtime,seeded_diagnostic=True)
        for value in task['public_inputs']: ep.check(ep.base,value)
        for failure in job['context']['repair_feedback']['failures']:
            actual=ep.check(ep.base,failure['input'])
            if actual['status']!='contradicted' or any(actual.get(k)!=failure.get(k) for k in ('observed','expected')):
                raise ValueError('original refutation not reproduced')
        content=record['output']['content'];patch=ep.apply_content(ep.base,content)
        failures=[]
        for value in task['public_inputs']:
            result=ep.check(patch,value)
            if result['status']!='supported': failures.append(ep.last[-1])
        if not failures: continue
        ep.repair_rejection={'code':'REJECTED_REGRESSION','failures':failures,'source':content}
        restored=ep.apply_content(patch,job['context']['source'])
        if restored.id!=ep.base.id: raise ValueError('rollback differs')
        feedback=ep.repair_feedback(ep.base)
        bysha={r['sha256']:r['body'] for r in ep.receipts.records}
        for body in bysha.values():
            if 'property' in body:
                obs=bysha[body['execution_receipt']]
                if check_observation(task['property'],obs['input'],obs['execution'])!=body['property']:
                    raise ValueError('property replay differs')
        audit=ep.receipts.audit()
        if not audit['ok']: raise ValueError('receipt custody failed')
        save(ep.path/'audit.json',{'valid':True,'scope':'public-case property replay and receipt custody'})
        used=record['usage']['provider_usage']['total_tokens']
        jobs.append({**job,'context':{**job['context'],'sample_index':1,'repair_feedback':feedback},
                     'total_token_budget':25000-used,'previous_inference_tokens':used})
    if not jobs: raise ValueError('no failed public case requiring a retry')
    bundle={**bundle,'jobs':jobs,'retry':True,
            'previous_report_sha256':hashlib.sha256(downloaded.read_bytes()).hexdigest()}
    write=runpy.run_path(str(Path(__file__).with_name('prepare_kaggle_repair.py')))['write_bundle']
    write(bundle,output,slug)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('run','inputs','downloaded','runtime','output'):p.add_argument(name,type=Path)
    p.add_argument('--slug',default='navywakura/echo51-repair-proposer14b-20261013')
    a=p.parse_args();prepare(a.run,a.inputs,a.downloaded,a.runtime,a.output,a.slug)
