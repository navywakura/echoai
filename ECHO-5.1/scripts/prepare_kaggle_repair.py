"""Prepare (do not submit) a private GPU proposer diagnostic from observed cases.

Upload allowlist: connector source, worker, explicit repair contexts. No oracle,
private checks, receipt authority, credential, model weight or full repo bundle.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def collect_jobs(run):
    episodes=json.loads((run/'result.json').read_text())['episodes']
    tasks={t['id']:t for t in json.loads((run/'tasks.json').read_text())}
    jobs=[]
    for ep in episodes:
        directory=run/(ep['task']+'-'+ep['arm'])
        records=[json.loads(l)['body'] for l in (directory/'thought.jsonl').read_text().splitlines()]
        repair=next((r for r in records if r.get('role')=='propose' and r.get('repair_feedback')),None)
        if repair is None: continue
        task=tasks[ep['task']]
        source=(directory/'snapshots'/repair['snapshot']/'tree/solution.py').read_text()
        feedback=repair['repair_feedback']
        jobs.append({'id':task['id'],'task':{k:task[k] for k in
            ('description','property','checker','input_schema','input_json_schema','preconditions')},
            'context':{'snapshot':repair['snapshot'],'source':source,'sample_index':0,
                       'evidence':[],'counterexamples':[p['input'] for p in feedback['failures']],
                       'repair_feedback':feedback}})
    if not jobs: raise ValueError('no witnessed repair prompts available')
    return jobs

def prepare(run,output,slug):
    episodes=json.loads((run/'result.json').read_text())['episodes']
    if not any(e['counterexamples_repaired'] and e['final_cases_passed'] for e in episodes):
        raise ValueError('local repair prerequisite not passed; GPU submission remains disabled')
    jobs=collect_jobs(run)
    config_path=run/'provider.json'
    config=(json.loads(config_path.read_text())['config'] if config_path.exists() else
            json.loads((ROOT/'ECHO-5.1/docs/QWEN-LOCAL-REPAIR.example.json').read_text()))
    config.update(model='pcworld-qwen25-coder14b',revision='d0a692ef765eefbf2fabb130b3cb2e8917e3d225',
                  tokenizer='embedded GGUF c1e659736d89ac1065fb495330fb824d94001974a4bfa78e7270e43476a8d940')
    bundle={'schema':'pcworld.gpu-repair-input.v1','scientific_claim':False,
            'local_run_result_sha256':hashlib.sha256((run/'result.json').read_bytes()).hexdigest(),
            'jobs':jobs,'config':config}
    write_bundle(bundle,output,slug)

def write_bundle(bundle,output,slug):
    output.mkdir(parents=True,exist_ok=False)
    sources={'repair-input.json':json.dumps(bundle,indent=2)+'\n',
             'connector/pcworld/__init__.py':'',
             'connector/pcworld/provider.py':(ROOT/'pcworld/provider.py').read_text(),
             'connector/pcworld/protocol.py':(ROOT/'pcworld/protocol.py').read_text(),
             'proposer-worker.py':Path(__file__).with_name('kaggle_repair_worker.py').read_text()}
    encoded={k:base64.b64encode(v.encode()).decode() for k,v in sources.items()}
    wrapper='''import base64,json,os,signal,subprocess,sys
from pathlib import Path
root=Path('/kaggle/working')
for name,data in EMBEDDED.items():
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(data))
process=subprocess.Popen([sys.executable,str(root/'proposer-worker.py')],start_new_session=True)
try:
    code=process.wait(timeout=3000)
except subprocess.TimeoutExpired:
    os.killpg(process.pid,signal.SIGKILL);process.wait()
    raise RuntimeError('GPU diagnostic exceeded 50-minute total ceiling')
raise SystemExit(code)
'''.replace('EMBEDDED',repr(encoded))
    (output/'kernel.py').write_text(wrapper)
    meta={'id':slug,'title':slug.split('/')[-1],'code_file':'kernel.py','language':'python',
          'kernel_type':'script','is_private':True,'enable_gpu':True,'enable_tpu':False,
          'enable_internet':True,'dataset_sources':[],'competition_sources':[],
          'kernel_sources':[],'model_sources':[],'machine_shape':'NvidiaTeslaT4'}
    (output/'kernel-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    (output/'input-local.json').write_text(sources['repair-input.json'])
    (output/'upload-manifest.json').write_text(json.dumps({k:hashlib.sha256(v.encode()).hexdigest()
                                                        for k,v in sources.items()},indent=2)+'\n')
    compile(wrapper,'kernel.py','exec')
    print(json.dumps({'jobs':len(bundle['jobs']),'private':True,'submission_performed':False,'path':str(output)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--slug',default='rogeernavarro/echo51-repair-proposer14b-20261013')
    a=p.parse_args();prepare(a.run,a.output,a.slug)
