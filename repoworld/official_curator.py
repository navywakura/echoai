"""Separate process entry point. Never import this module in the online actor."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

NAMESPACE='swebench'


def restrict_containers():
    """Same official grader/image, explicit offline resource policy for all arms."""
    from docker.models.containers import ContainerCollection
    original=ContainerCollection.create
    def create(self,*args,**kwargs):
        kwargs.update(network_mode='none',mem_limit=4*1024**3,pids_limit=128,cap_drop=['ALL'])
        return original(self,*args,**kwargs)
    ContainerCollection.create=create


def controls(request_path):
    """Curator-only empty/gold environment controls BEFORE any actor is run."""
    request=json.loads(Path(request_path).read_bytes());sys.path.insert(0,request['harness'])
    import docker
    import pyarrow.parquet as pq
    import shutil
    from pathlib import PurePosixPath
    from swebench.harness.test_spec.test_spec import make_test_spec
    from swebench.harness.docker_build import build_container,setup_logger,close_logger
    from swebench.harness.docker_utils import copy_to_container,exec_run_with_timeout,cleanup_container
    from swebench.harness.grading import get_eval_report,get_logs_eval
    restrict_containers()
    source=Path(request['dataset'])
    with source.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=request['dataset_sha256']:raise ValueError('curator source changed')
    wanted={r['instance_id'] for r in request['instances']}
    rows={r['instance_id']:r for r in pq.read_table(source).to_pylist() if r['instance_id'] in wanted}
    client=docker.from_env();result=[]
    for identifier in sorted(wanted):
        row=rows[identifier];entry=dict(instance_id=identifier,base_commit=row['base_commit'],valid=False)
        try:
            spec=make_test_spec(row,namespace=NAMESPACE)
            try:image=client.images.get(spec.instance_image_key)
            except docker.errors.ImageNotFound:
                if not request.get('allow_pull'):raise RuntimeError('official_image_missing')
                if shutil.disk_usage('.').free<12*1024**3:raise RuntimeError('insufficient_free_disk_for_image')
                image=client.images.pull(spec.instance_image_key)
            entry['official_image_digest']=image.id
            entry['official_eval_script_sha256']=hashlib.sha256(spec.eval_script.encode()).hexdigest()
            fields={k:row[k] for k in ('test_patch','FAIL_TO_PASS','PASS_TO_PASS')}
            entry['sealed_tests_sha256']=hashlib.sha256(json.dumps(fields,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
            if not spec.FAIL_TO_PASS:raise RuntimeError('zero_FAIL_TO_PASS')
            observed={}
            for kind in ('empty','gold'):
                folder=Path(identifier)/kind;folder.mkdir(parents=True,exist_ok=True)
                logger=setup_logger(identifier+'-'+kind,folder/'control.log');container=None
                try:
                    run_id='echo-controls-'+kind+'-'+hashlib.sha256((identifier+image.id).encode()).hexdigest()[:16]
                    container=build_container(spec,client,run_id,logger,False,False);container.start()
                    patch=row['patch'] if kind=='gold' else ''
                    if patch:
                        file=folder/'model.patch';file.write_text(patch);copy_to_container(container,file,PurePosixPath('/tmp/model.patch'))
                        applied=container.exec_run(['git','apply','/tmp/model.patch'],workdir='/testbed',user='root')
                        if applied.exit_code:raise RuntimeError('gold_patch_did_not_apply')
                    file=folder/'eval.sh';file.write_text(spec.eval_script);copy_to_container(container,file,PurePosixPath('/eval.sh'))
                    text,timed_out,elapsed=exec_run_with_timeout(container,'/bin/bash /eval.sh',600)
                    if timed_out:raise RuntimeError('control_timeout')
                    if len(text.encode())>4*1024**2:raise RuntimeError('control_output_limit')
                    log=folder/'test_output.txt';log.write_text(text)
                    prediction=dict(instance_id=identifier,model_name_or_path='environment-control',model_patch=patch)
                    report=get_eval_report(spec,prediction,str(log),include_tests_status=True)[identifier]
                    states,found=get_logs_eval(spec,str(log))
                    present=all(t in states and states[t] not in ('SKIPPED',) for t in spec.FAIL_TO_PASS+spec.PASS_TO_PASS)
                    p2p=all(states.get(t) in ('PASSED','XFAIL') for t in spec.PASS_TO_PASS)
                    f2p=all(states.get(t) in ('PASSED','XFAIL') for t in spec.FAIL_TO_PASS)
                    observed[kind]=dict(raw_resolved=report['resolved'],valid=found and present and p2p and (f2p if kind=='gold' else not f2p),
                        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),elapsed_seconds=elapsed)
                    (folder/'report.json').write_text(json.dumps(report))
                finally:
                    if container is not None:cleanup_container(client,container,logger)
                    close_logger(logger)
            if client.images.get(spec.instance_image_key).id!=image.id:raise RuntimeError('official_image_changed')
            entry.update(empty_patch_resolved=observed['empty']['raw_resolved'],gold_patch_resolved=observed['gold']['raw_resolved'],
                valid=all(v['valid'] for v in observed.values()) and not observed['empty']['raw_resolved'] and observed['gold']['raw_resolved'],controls=observed)
        except Exception as exc:
            # Export only an error class/code; never a traceback containing sealed
            # tests, expected answers or reference implementation into online use.
            entry['error']=str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
        result.append(entry);Path('controls.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def collect_result(spec,folder,patch,parser):
    required=spec.FAIL_TO_PASS+spec.PASS_TO_PASS
    result=dict(official_report=None,observed_states={},found=False,required_count=len(required),
        nonempty_f2p=bool(spec.FAIL_TO_PASS),all_required_observed=False,report_sha256=None,log_sha256=None,
        evidence_status='no_patch' if not patch else 'missing_official_evidence')
    if not patch or not(folder/'report.json').is_file() or not(folder/'test_output.txt').is_file():return result
    reports=json.loads((folder/'report.json').read_bytes())
    identifier=spec.instance_id
    if set(reports)!={identifier}:raise ValueError('official report instance mismatch')
    states,found=parser(spec,str(folder/'test_output.txt'))
    result.update(official_report=reports[identifier],observed_states=states,found=found,
        all_required_observed=all(states.get(t) in ('PASSED','XFAIL') for t in required),
        report_sha256=hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),
        log_sha256=hashlib.sha256((folder/'test_output.txt').read_bytes()).hexdigest(),evidence_status='observed')
    return result


def main(request_path):
    request=json.loads(Path(request_path).read_bytes())
    path=Path(request['dataset'])
    with path.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=request['dataset_sha256']:raise ValueError('dataset changed')
    # Strictly after global freeze (enforced by the parent capability boundary).
    if path.suffix=='.parquet':
        import pyarrow.parquet as pq
        rows=pq.read_table(path).to_pylist()
    else:rows=json.loads(path.read_bytes())
    sys.path.insert(0,request['harness'])
    import docker
    restrict_containers()
    from swebench.harness.test_spec.test_spec import make_test_spec
    from swebench.harness.grading import get_logs_eval
    from swebench.harness.run_evaluation import main as evaluate
    selected={r['instance_id']:r for r in rows if r['instance_id'] in {i['instance_id'] for i in request['instances']}}
    client=docker.from_env();specs={};images={}
    for lock in request['instances']:
        row=selected[lock['instance_id']];spec=make_test_spec(row,namespace=NAMESPACE);specs[lock['instance_id']]=spec
        image=client.images.get(spec.instance_image_key)
        if image.id!=lock['official_image_digest']:raise ValueError('official image digest mismatch')
        images[lock['instance_id']]=image.id
        if hashlib.sha256(spec.eval_script.encode()).hexdigest()!=lock['official_eval_script_sha256']:raise ValueError('eval script mismatch')
        sealed={k:row[k] for k in ('test_patch','FAIL_TO_PASS','PASS_TO_PASS')}
        raw=json.dumps(sealed,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
        if hashlib.sha256(raw).hexdigest()!=lock['sealed_tests_sha256']:raise ValueError('sealed tests mismatch')
    # Local JSON pins dataset bytes rather than resolving a mutable Hub alias.
    Path('dataset.json').write_text(json.dumps(list(selected.values())))
    args=['--dataset_name',str(Path('dataset.json').resolve()),'--predictions_path',request['predictions'],
          '--run_id',request['run_id'],'--max_workers','1','--timeout','1800','--cache_level','instance','--clean','False','--namespace',NAMESPACE]
    # Running the CLI preserves the pinned version's own argument validation.
    code=('import sys,runpy;sys.path.insert(0,sys.argv.pop(1));'
          'helper=runpy.run_path(sys.argv.pop(1));helper["restrict_containers"]();'
          'runpy.run_module("swebench.harness.run_evaluation",run_name="__main__")')
    process=subprocess.run([sys.executable,'-I','-c',code,request['harness'],str(Path(__file__).resolve()),*args],check=False,timeout=7000)
    predictions={r['instance_id']:r['model_patch'] for r in (json.loads(line) for line in Path(request['predictions']).read_text().splitlines())}
    result={}
    for identifier,spec in specs.items():
        if client.images.get(spec.instance_image_key).id!=images[identifier]:raise ValueError('image changed during evaluation')
        folder=Path('logs/run_evaluation')/request['run_id']/request['run_id']/identifier
        result[identifier]=collect_result(spec,folder,predictions[identifier],get_logs_eval)
        result[identifier]['harness_exit_code']=process.returncode
    Path('verdicts.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--controls':controls(sys.argv[2])
    else:main(sys.argv[1])
