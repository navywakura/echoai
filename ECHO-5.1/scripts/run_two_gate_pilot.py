"""Supervise one development matrix with GPU inference and local verification.

The caller provides a private control directory. Credentials never enter the
provider manifest; only their environment variable name does. Stop the remote
inference worker even if the local pilot fails. No automatic GPU resubmission.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('echoai',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
package=importlib.util.module_from_spec(spec);sys.modules['echoai']=package;spec.loader.exec_module(package)
from echoai.pcworld.pilot import run_pilot,audit_run,save


def main():
    p=argparse.ArgumentParser();p.add_argument('control',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--runtime',type=Path,required=True)
    a=p.parse_args();secrets=json.loads((a.control/'relay-secrets.json').read_text())
    os.environ['ECHO51_RELAY_CLIENT_TOKEN']=secrets['client_token']
    config=json.loads((a.control/'provider.json').read_text())
    def request(path,body=None):
        req=urllib.request.Request('http://127.0.0.1:8786'+path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Authorization':'Bearer '+secrets['client_token'],'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=5) as r:return json.load(r)
    try:
        until=time.monotonic()+600
        while time.monotonic()<until:
            health=request('/health')
            if health.get('worker_ready'):break
            time.sleep(2)
        else:raise TimeoutError('GPU worker not ready within ten minutes; no pilot started')
        save(a.control/'gpu-ready.json',health)
        print('GPU ready; launching 12 development episodes',flush=True)
        report=run_pilot(a.output,task_count=6,arms=('S','I2','F','E'),provider='http',
            config=config,suite='repair-v2',runtime=a.runtime,task_seed=47,
            task_families=['records','path','pagination'],episode_wall_seconds=900,
            model_evidence=health)
        audit=audit_run(a.output);save(a.output/'audit.json',audit)
        print(json.dumps({'completed':len(report['episodes']),'audit':audit,'scientific_claim':False}),flush=True)
        return int(not audit['valid'])
    finally:
        try:request('/stop',{})
        except Exception as exc:print('Relay stop failed: '+type(exc).__name__,flush=True)

if __name__=='__main__':raise SystemExit(main())
