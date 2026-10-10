"""Read-only projection of actual Kaggle records into the local development terminal."""
import hashlib
import json
import os
from pathlib import Path
import time
HERE=Path(__file__).resolve().parent
os.environ['KAGGLE_API_TOKEN']=Path('/home/roger/.kaggleapikey').read_text().strip()
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi();api.authenticate()
REF='rogeernavarro/echo45-s6b24-20261009'
seen=set();finished=set()

def save(name,value):
    p=HERE/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(value)+'\n');t.replace(p)

while True:
    try:
        if (HERE/'pipeline-status.json').exists() and json.loads((HERE/'pipeline-status.json').read_text())['stage'] in ('COMPLETE','INSTRUMENT_BLOCKED'):break
        if not (HERE/'submitted.json').exists():time.sleep(30);continue
        version=json.loads((HERE/'submitted.json').read_text())['versionNumber']
        if version in finished:time.sleep(30);continue
        with (HERE/'live-follow.jsonl').open('a') as raw,(HERE/'live-readable.log').open('a') as display:
            for event in api.kernels_logs_stream(REF):
                key=hashlib.sha256(json.dumps([version,event],sort_keys=True).encode()).hexdigest()
                if key in seen:continue
                seen.add(key);raw.write(json.dumps(dict(version=version,event=event))+'\n');raw.flush()
                data=event.get('data','')
                for line in data.splitlines():
                    try:v=json.loads(line)
                    except ValueError:continue
                    if isinstance(v,dict) and v.get('condition')=='S6-B24':
                        save('live-scientific-status.json',dict(observed_at=time.time(),version=version,status=v))
                        display.write(json.dumps(v,ensure_ascii=False)+'\n');display.flush()
                if any(s in data for s in ('Traceback','INSTRUMENT_BLOCKED','CUDA error','out of memory')):
                    save('live-error.json',dict(version=version,event=event))
        state=str(api.kernels_status(REF).status).rsplit('.',1)[-1]
        if state in ('COMPLETE','ERROR','CANCELLED','CANCEL_ACKNOWLEDGED'):finished.add(version)
    except Exception as exc:save('live-collector-error.json',dict(at=time.time(),type=type(exc).__name__))
    time.sleep(30)
