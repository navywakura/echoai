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

def download(url, destination, expected):
    h=hashlib.sha256();partial=destination.with_suffix('.part')
    with urllib.request.urlopen(url,timeout=90) as response, partial.open('wb') as target:
        while chunk:=response.read(8*1024*1024): h.update(chunk);target.write(chunk)
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
        model=SCRATCH/MODEL_FILE
        print('Downloading pinned 14B Q4_K_M (8.99 GB)',flush=True)
        download('https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF/resolve/'+MODEL_REV+'/'+MODEL_FILE,model,MODEL_SHA)
        env=dict(os.environ)
        libraries=sorted({str(p.parent) for p in (SCRATCH/'bin').rglob('*.so*')})
        env['LD_LIBRARY_PATH']=':'.join(libraries+[env.get('LD_LIBRARY_PATH','')])
        with (ROOT/'llama-gpu.log').open('w') as log:
            server=subprocess.Popen([str(binary),'--model',str(model),'--alias','pcworld-qwen25-coder14b',
                '--host','127.0.0.1','--port','8785','--ctx-size','4096','--parallel','1',
                '--threads','4','--n-gpu-layers','99','--device','CUDA0','--verbosity','4'],
                stdout=log,stderr=subprocess.STDOUT,env=env)
        ready=time.monotonic()+180
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
        offload=re.findall(r'offloaded (\d+)/(\d+) layers to GPU',text)
        if not offload or not any(int(a)>0 for a,b in offload): raise RuntimeError('GPU offload not proven; no CPU fallback')
        report['gpu_offload']=offload;report['gpu_loaded']=gpu_info()
        report['setup_seconds']=round(time.monotonic()-started,3)
        sys.path.insert(0,str(ROOT/'connector'))
        from pcworld.provider import HTTPProvider
        config=bundle['config'];provider=HTTPProvider(config)
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
