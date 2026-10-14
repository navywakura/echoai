"""Separate process entry point. Never import this module in the online actor."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from contextlib import contextmanager

NAMESPACE='swebench'
SERVICE_ROOT='/opt/repoworld-httpbin'
SERVICE_PYTHON='/opt/miniconda3/envs/testbed/bin/python'
SERVICE_TRUST='/opt/miniconda3/envs/testbed/lib/python3.9/site-packages/certifi/cacert.pem'


def pytest_reporting_profile(image):
    """Pin rendering only; failed assertions must still produce FAILED states.

    Public BASE can crash while rendering a failed assertion's traceback. The
    upstream --tb=no option avoids that rendering, retaining the official -rA
    result summaries. This changes neither test inputs nor validity criteria.
    """
    image=str(image).removeprefix('docker.io/')
    if image!='swebench/sweb.eval.x86_64.pytest-dev_1776_pytest-7168:latest':return None
    profile=dict(schema='repoworld.pytest-reporting.v1',image=image,
        image_digest='sha256:fa2614449afb464c272c3bd0c5ebc66d7cd6a046b4a98ac65ee1b0df2594a9ff',
        environment={'PYTEST_ADDOPTS':'--tb=no'})
    raw=json.dumps(profile,sort_keys=True,separators=(',',':')).encode()
    return {**profile,'sha256':hashlib.sha256(raw).hexdigest()}


def validate_reporting_lock(profile,locked):
    if locked.get('reporting_profile_sha256')!=(profile['sha256'] if profile else None):
        raise ValueError('final reporting profile differs from locked preflight')


def httpbin_profile(image):
    """An operator-pinned, public dependency; never selected from sealed tests.

    Requests' public BASE uses both HTTPBIN_URL and literal httpbin.org URLs.
    Both resolve to the real upstream httpbin application inside network=none.
    No test content, reference patch or expected result enters this profile.
    """
    image=str(image).removeprefix('docker.io/')
    if not image.startswith('swebench/sweb.eval.x86_64.psf_1776_requests-'):
        return None
    path=os.environ.get('REPOWORLD_CURATOR_SERVICES')
    digest=os.environ.get('REPOWORLD_CURATOR_SERVICES_SHA256','')
    if not path or not re.fullmatch('[0-9a-f]{64}',digest):
        raise ValueError('pinned Requests service manifest required')
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('service manifest changed')
    profile=json.loads(raw)
    if profile.get('schema')=='repoworld.curator-httpbin-set.v1':
        profile=profile.get('profiles',{}).get(image,{})
    if profile.get('schema')!='repoworld.curator-httpbin.v1' or profile.get('image')!=image:
        raise ValueError('service image/profile mismatch')
    bundle=Path(profile['bundle'])
    if not bundle.is_absolute() or bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('private absolute service bundle required')
    files=profile['files'];actual={}
    for file in bundle.rglob('*'):
        if file.is_symlink():raise ValueError('service links forbidden')
        if file.is_file():actual[str(file.relative_to(bundle))]=hashlib.sha256(file.read_bytes()).hexdigest()
        elif not file.is_dir():raise ValueError('service special files forbidden')
    if actual!=files or not {'ca.pem','key.pem','trust.pem','lib/httpbin/core.py'}<=set(files):
        raise ValueError('service bundle bytes changed or incomplete')
    expected_trust=('/testbed/requests/cacert.pem' if image=='swebench/sweb.eval.x86_64.psf_1776_requests-2674:latest' else SERVICE_TRUST)
    if profile.get('trust_store')!=expected_trust or profile.get('off_host_redirect_alias')!='www.google.co.uk':
        raise ValueError('service trust/redirect profile mismatch')
    return {**profile,'manifest_sha256':digest}


# Only a process supervisor: all HTTP behavior belongs to the pinned upstream
# WSGI application. Separate interpreters keep service dependencies out of tests.
HTTPBIN_SERVER=r'''
import os, subprocess, sys, time
env={'PATH':'/usr/bin:/bin','PYTHONPATH':'/opt/repoworld-httpbin/lib',
     'PYTHONDONTWRITEBYTECODE':'1','HOME':'/tmp','LANG':'C.UTF-8'}
base=[sys.executable,'-m','gunicorn','--workers','2','--threads','4',
      '--access-logfile','/dev/null','--error-logfile','/tmp/repoworld-httpbin.log']
children=[]
try:
    children.append(subprocess.Popen(base+['--bind','127.0.0.1:80','httpbin:app'],env=env,cwd='/'))
    children.append(subprocess.Popen(base+['--bind','127.0.0.1:443',
        '--certfile','/opt/repoworld-httpbin/ca.pem','--keyfile','/opt/repoworld-httpbin/key.pem',
        'httpbin:app'],env=env,cwd='/'))
    while all(p.poll() is None for p in children):time.sleep(.2)
finally:
    for p in children:
        if p.poll() is None:p.terminate()
    for p in children:
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait()
'''

HTTPBIN_READY=r'''
import ssl, urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile='/opt/repoworld-httpbin/ca.pem')))
for scheme in ('http','https'):
    with opener.open(scheme+'://httpbin.org/status/204',timeout=1) as r:assert r.status==204
'''


def start_httpbin(container):
    container.exec_run([SERVICE_PYTHON,'-I','-c',HTTPBIN_SERVER],workdir='/',detach=True)
    deadline=time.monotonic()+30
    while time.monotonic()<deadline:
        result=container.exec_run([SERVICE_PYTHON,'-I','-c',HTTPBIN_READY],workdir='/')
        if result.exit_code==0:return
        time.sleep(.2)
    raise RuntimeError('loopback_httpbin_not_ready')


def validate_service_lock(profile,locked):
    expected=profile['manifest_sha256'] if profile else None
    if locked.get('service_manifest_sha256')!=expected:
        raise ValueError('final service differs from locked preflight')


def restrict_containers():
    """Same official grader/image, explicit offline resource policy for all arms."""
    from docker.models.containers import ContainerCollection,Container
    if getattr(ContainerCollection,'_repoworld_offline',False):return
    original=ContainerCollection.create
    original_start=Container.start
    def create(self,*args,**kwargs):
        image=kwargs.get('image',args[0] if args else '')
        profile=httpbin_profile(image)
        reporting=pytest_reporting_profile(image)
        kwargs.update(network_mode='none',mem_limit=4*1024**3,pids_limit=128,cap_drop=['ALL'])
        if reporting:
            if self.client.images.get(image).id!=reporting['image_digest']:raise ValueError('reporting runtime image changed')
            environment=kwargs.get('environment') or {}
            if isinstance(environment,list):environment=dict(v.split('=',1) for v in environment)
            kwargs['environment']={**environment,**reporting['environment']}
        if profile:
            if self.client.images.get(image).id!=profile['image_digest']:raise ValueError('service runtime image changed')
            kwargs.setdefault('volumes',{})[profile['bundle']]={'bind':SERVICE_ROOT,'mode':'ro,Z'}
            # Public BASE's direct Session.send bypasses REQUESTS_CA_BUNDLE.
            # Add our CA to certifi's original roots, outside candidate sources.
            kwargs['volumes'][str(Path(profile['bundle'])/'trust.pem')]={'bind':profile['trust_store'],'mode':'ro,Z'}
            kwargs.setdefault('extra_hosts',{})['httpbin.org']='127.0.0.1'
            # Public BASE uses this second authority solely as a redirect target.
            # Real upstream httpbin serves it; Requests still handles the redirect
            # and strips credentials based on the distinct authority itself.
            kwargs['extra_hosts']['www.google.co.uk']='127.0.0.1'
            kwargs.setdefault('sysctls',{})['net.ipv4.ip_unprivileged_port_start']='0'
            environment=kwargs.get('environment') or {}
            if isinstance(environment,list):environment=dict(v.split('=',1) for v in environment)
            kwargs['environment']={**environment,'HTTPBIN_URL':'http://httpbin.org/',
                'REQUESTS_CA_BUNDLE':SERVICE_ROOT+'/ca.pem','CURL_CA_BUNDLE':SERVICE_ROOT+'/ca.pem',
                'HTTP_PROXY':'','HTTPS_PROXY':'','ALL_PROXY':'','NO_PROXY':'*',
                'http_proxy':'','https_proxy':'','all_proxy':'','no_proxy':'*'}
        container=original(self,*args,**kwargs)
        container._repoworld_httpbin=profile
        container._repoworld_reporting=reporting
        return container
    def start(self,*args,**kwargs):
        result=original_start(self,*args,**kwargs)
        if getattr(self,'_repoworld_httpbin',None):start_httpbin(self)
        return result
    ContainerCollection.create=create
    Container.start=start
    ContainerCollection._repoworld_offline=True


@contextmanager
def control_image(client, key, *, allow_pull=False, evict=False):
    """Bound disk growth; never remove an image that predated this acquisition."""
    import docker, shutil
    if type(evict) is not bool:raise ValueError('evict_pulled_images must be boolean')
    pulled=False
    try:image=client.images.get(key)
    except docker.errors.ImageNotFound:
        if not allow_pull:raise RuntimeError('official_image_missing')
        if shutil.disk_usage('.').free<12*1024**3:raise RuntimeError('insufficient_free_disk_for_image')
        existing_ids={value.id for value in client.images.list(all=True)}
        image=client.images.pull(key);pulled=image.id not in existing_ids
    try:yield image
    finally:
        if pulled and evict:client.images.remove(image.id,force=False)


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
            with control_image(client,spec.instance_image_key,allow_pull=request.get('allow_pull',False),evict=request.get('evict_pulled_images',False)) as image:
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
                        profile=getattr(container,'_repoworld_httpbin',None)
                        if profile:entry['service_manifest_sha256']=profile['manifest_sha256']
                        reporting=getattr(container,'_repoworld_reporting',None)
                        if reporting:entry['reporting_profile_sha256']=reporting['sha256']
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
            entry['valid']=False
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
    deadline=time.monotonic()+6900  # Aggregate bound below the supervisor's 7200 s.
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
        validate_service_lock(httpbin_profile(spec.instance_image_key),lock)
        validate_reporting_lock(pytest_reporting_profile(spec.instance_image_key),lock)
        images[lock['instance_id']]=lock['official_image_digest']
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
    predictions={r['instance_id']:r['model_patch'] for r in (json.loads(line) for line in Path(request['predictions']).read_text().splitlines())}
    result={}
    for identifier,spec in specs.items():
        with control_image(client,spec.instance_image_key,
                allow_pull=request.get('evict_pulled_images',False),evict=request.get('evict_pulled_images',False)) as image:
            if image.id!=images[identifier]:raise ValueError('official image digest mismatch')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise RuntimeError('curator_aggregate_deadline')
            process=subprocess.run([sys.executable,'-I','-c',code,request['harness'],str(Path(__file__).resolve()),*args,
                '--instance_ids',identifier],check=False,timeout=remaining)
            if client.images.get(spec.instance_image_key).id!=images[identifier]:raise ValueError('image changed during evaluation')
            folder=Path('logs/run_evaluation')/request['run_id']/request['run_id']/identifier
            result[identifier]=collect_result(spec,folder,predictions[identifier],get_logs_eval)
            result[identifier]['harness_exit_code']=process.returncode
    Path('verdicts.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--controls':controls(sys.argv[2])
    else:main(sys.argv[1])
