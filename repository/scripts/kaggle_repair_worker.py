"""GPU-only proposer diagnostic. NEVER execute generated code in this notebook.

The preparer embeds this worker with two observed repair contexts, provider.py
and protocol.py. All downloads are pinned and checked. Outputs are untrusted
proposals for subsequent local Bubblewrap verification, not task successes.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = Path('/kaggle/working')
SCRATCH = Path('/kaggle/temp/echo51-repair')
MODEL_REV = 'd0a692ef765eefbf2fabb130b3cb2e8917e3d225'
MODEL_FILE = 'qwen2.5-coder-14b-instruct-q4_k_m.gguf'
MODEL_SHA = 'c1e659736d89ac1065fb495330fb824d94001974a4bfa78e7270e43476a8d940'
ASSETS = (
    ('llama-b11577-bin-ubuntu-cuda-12.8-x64.tar.gz', '97f565404b734b4da785953099a38d5554727f8816212debfe33846bfb89a9fc'),
    ('cudart-llama-b11577-bin-ubuntu-cuda-12.8-x64.tar.gz', 'b4372b9e608e20bede6808d42105ca4d8b5c22b9777fca52d3040c3816cce5f0'),
)

def model_profile(name):
    profiles={
        'qwen25-coder14b':{'repo':'Qwen/Qwen2.5-Coder-14B-Instruct-GGUF',
            'revision':MODEL_REV,'file':MODEL_FILE,'sha256':MODEL_SHA,'bytes':8988110272,
            'alias':'pcworld-qwen25-coder14b','layers':49,'devices':['CUDA0']},
        'qwen25-coder32b':{'repo':'Qwen/Qwen2.5-Coder-32B-Instruct-GGUF',
            'revision':'9d3053fce650fe1cdbdb75998c2a87add9d178ef',
            'file':'qwen2.5-coder-32b-instruct-q4_k_m.gguf',
            'sha256':'4d64b316b5e6319d9613e0d97935d9ebd631fc7e334da400d00085eca749d085',
            'bytes':19851335872,'alias':'pcworld-qwen25-coder32b','layers':65,
            'devices':['CUDA0','CUDA1']}}
    if name not in profiles:raise ValueError('unknown pinned GPU model')
    return profiles[name]

def validate_provider_profile(config,profile):
    expected={'model':profile['alias'],'revision':profile['revision'],
              'tokenizer':'embedded GGUF '+profile['sha256'],
              'context_tokens':4096,'quantization':'Q4_K_M'}
    if any(config.get(k)!=v for k,v in expected.items()):
        raise ValueError('provider configuration differs from pinned GPU model')

def server_command(binary,model,profile):
    args=[str(binary),'--model',str(model),'--alias',profile['alias'],
          '--host','127.0.0.1','--port','8785','--ctx-size','4096','--parallel','1',
          '--threads','4','--n-gpu-layers','99','--device',','.join(profile['devices']),
          '--verbosity','4']
    if len(profile['devices'])==2:
        args+=['--split-mode','layer','--tensor-split','1,1','--fit','off']
    return args

def verify_offload(text,profile):
    offload=re.findall(r'offloaded (\d+)/(\d+) layers to GPU',text)
    if not any(int(a)==int(b)==profile['layers'] for a,b in offload):
        raise RuntimeError('all model layers must be on GPU; no CPU fallback')
    buffers={name:float(mib) for name,mib in re.findall(
        r'(CUDA\d+) model buffer size\s*=\s*([0-9.]+) MiB',text)}
    if any(buffers.get(device,0)<1024 for device in profile['devices']):
        raise RuntimeError('required GPU model buffers not proven')
    return {'gpu_offload':offload,'gpu_model_buffers_mib':buffers}


def download(url, destination, expected):
    h=hashlib.sha256();partial=destination.with_suffix('.part');received=0;next_progress=1024**3
    with urllib.request.urlopen(url,timeout=90) as response, partial.open('wb') as target:
        while chunk:=response.read(8*1024*1024):
            h.update(chunk);target.write(chunk);received+=len(chunk)
            if received>=next_progress:
                print('DOWNLOAD',destination.name,received,'bytes',flush=True)
                next_progress+=1024**3
    if h.hexdigest()!=expected: raise ValueError('download SHA256 mismatch: '+destination.name)
    partial.replace(destination)

def gpu_info():
    return subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.used,driver_version',
                                     '--format=csv,noheader'],text=True,timeout=15).strip()

def main():
    started=time.monotonic();server=None
    report={'schema':'pcworld.gpu-proposer-diagnostic.v1','scientific_claim':False,
            'candidate_executed_on_kaggle':False,'records':[],'errors':[],
            'model_revision':MODEL_REV,'model_sha256':MODEL_SHA,'llama_release':'b11577'}
    try:
        bundle=json.loads((ROOT/'repair-input.json').read_text())
        profile=model_profile(bundle.get('gpu_model','qwen25-coder14b'))
        validate_provider_profile(bundle['config'],profile)
        report.update(model_profile=bundle.get('gpu_model','qwen25-coder14b'),
                      model_revision=profile['revision'],model_sha256=profile['sha256'],
                      model_bytes=profile['bytes'],model_file=profile['file'],
                      requested_devices=profile['devices'])
        report['input_sha256']=hashlib.sha256((ROOT/'repair-input.json').read_bytes()).hexdigest()
        report['gpu_before']=gpu_info()
        print('GPU',report['gpu_before'],flush=True)
        SCRATCH.mkdir(parents=True,exist_ok=True)
        for name,sha in ASSETS:
            path=SCRATCH/name
            download('https://github.com/ggml-org/llama.cpp/releases/download/b11577/'+name,path,sha)
            with tarfile.open(path) as archive: archive.extractall(SCRATCH/'bin',filter='data')
            path.unlink()
        binary=next((SCRATCH/'bin').rglob('llama-server'))
        report['server_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
        if len(report['gpu_before'].splitlines())<len(profile['devices']):
            raise RuntimeError('not enough GPUs for the pinned profile')
        model=SCRATCH/profile['file']
        print('Downloading pinned '+profile['alias']+' ('+str(profile['bytes'])+' bytes)',flush=True)
        download('https://huggingface.co/'+profile['repo']+'/resolve/'+profile['revision']+'/'+profile['file'],
                 model,profile['sha256'])
        if model.stat().st_size!=profile['bytes']:raise ValueError('model byte size differs')
        env=dict(os.environ)
        libraries=sorted({str(p.parent) for p in (SCRATCH/'bin').rglob('*.so*')})
        env['LD_LIBRARY_PATH']=':'.join(libraries+[env.get('LD_LIBRARY_PATH','')])
        with (ROOT/'llama-gpu.log').open('w') as log:
            server=subprocess.Popen(server_command(binary,model,profile),
                stdout=log,stderr=subprocess.STDOUT,env=env)
        ready=time.monotonic()+300
        while time.monotonic()<ready:
            if server.poll() is not None: raise RuntimeError('GPU server exited; see llama-gpu.log')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8785/health',timeout=2) as response:
                    if json.load(response).get('status')=='ok': break
            except Exception: time.sleep(1)
        else: raise TimeoutError('GPU model load timeout')
        text=(ROOT/'llama-gpu.log').read_text()
        report['gpu_loaded']=gpu_info()
        report['compute_processes']=subprocess.check_output(
            ['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],
            text=True,timeout=15).strip()
        report.update(verify_offload(text,profile))
        report['setup_seconds']=round(time.monotonic()-started,3)
        sys.path.insert(0,str(ROOT/'connector'))
        from pcworld.provider import HTTPProvider
        config=bundle['config'];provider=HTTPProvider(config)
        if bundle.get('relay'):
            from inference_relay import run_worker
            report['schema']='pcworld.gpu-inference-relay.v1'
            (ROOT/'gpu-proposer-results.json').write_text(json.dumps(report,indent=2)+'\n')
            report['relay_result']=run_worker(**bundle['relay'],ready_metadata={k:v for k,v in report.items() if k not in ('records','errors')})
        for job in bundle['jobs']:
            t=time.monotonic();record={'task':job['id'],'job_sha256':hashlib.sha256(
                json.dumps(job,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
            try:
                output,usage=provider.call('propose',job['task'],job['context'],
                    max_tokens=768,total_token_budget=job.get('total_token_budget',25000),
                    deadline=time.monotonic()+300)
                record.update(output=output,usage=usage)
            except Exception as exc:
                record.update(error=type(exc).__name__+': '+str(exc),usage=getattr(exc,'usage',None))
            record['wall_seconds']=round(time.monotonic()-t,3);report['records'].append(record)
            (ROOT/'gpu-proposer-results.json').write_text(json.dumps(report,indent=2)+'\n')
            print('PROPOSAL',job['id'],'seconds',record['wall_seconds'],'error',record.get('error'),flush=True)
        report['gpu_after']=gpu_info()
    except Exception as exc:
        report['errors'].append(type(exc).__name__+': '+str(exc))
        raise
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try: server.wait(timeout=10)
            except subprocess.TimeoutExpired: server.kill();server.wait()
        report['total_seconds']=round(time.monotonic()-started,3)
        (ROOT/'gpu-proposer-results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__': main()
