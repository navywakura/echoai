"""Private B24 launch/collection/checkpoint continuation; no scientific source edits."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

HERE=Path(__file__).resolve().parent
REF='rogeernavarro/echo45-s6b24-20261009'
CHECKPOINT='rogeernavarro/echo45-s6b24-checkpoint-20261009'
os.environ['KAGGLE_API_TOKEN']=Path('/home/roger/.kaggleapikey').read_text().strip()
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiDownloadKernelOutputRequest
import requests
api=KaggleApi();api.authenticate()


def read(path):return json.loads(Path(path).read_text())
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,sort_keys=True)+'\n');tmp.replace(path)
def wire(obj):return json.loads(str(obj))
def status(stage,**kw):
    d=dict(at=time.time(),stage=stage,ref=REF,**kw);save(HERE/'pipeline-status.json',d);print(json.dumps(d),flush=True)
def seconds(value):
    # SDK currently renders decimal durations as "9403.355.0s".
    match=re.match(r'^(\d+(?:\.\d+)?)',str(value))
    if not match:raise ValueError('unknown quota duration')
    return float(match.group(1))
def quota():
    q=wire(api.quota_view());g=q['gpuQuota']
    return max(0,seconds(g['totalTimeAllowed'])-seconds(g['timeUsed'])-seconds(g['timeReserved'])),q['quotaRefreshTime']
def launch():
    if (HERE/'submission-pending.json').exists():raise RuntimeError('ambiguous prior submission requires reconciliation')
    save(HERE/'submission-pending.json',dict(at=time.time(),ref=REF))
    r=wire(api.kernels_push(str(HERE/'notebook'),acc='NvidiaTeslaT4',timeout='14400'))
    if r.get('error') or any(r.get(k) for k in ('invalidDatasetSources','invalidKernelSources','invalidCompetitionSources','invalidModelSources')):
        save(HERE/'submission-error.json',r);raise RuntimeError('Kaggle rejected submission')
    save(HERE/'submitted.json',r);save(HERE/f"submitted-v{r['versionNumber']}.json",r)
    (HERE/'submission-pending.json').unlink();status('SUBMITTED',version=r['versionNumber'],url=r['url'])
    return r

def download(version,name,dest):
    if dest.exists():return
    with api.build_kaggle_client() as client:
        req=ApiDownloadKernelOutputRequest();req.owner_slug='rogeernavarro';req.kernel_slug=REF.split('/')[1]
        req.file_path=name;req.version_number=version
        response=client.kernels.kernels_api_client.download_kernel_output(req)
        with requests.get(response.url,stream=True,timeout=(30,120)) as result:
            result.raise_for_status();dest.parent.mkdir(parents=True,exist_ok=True)
            tmp=dest.with_suffix(dest.suffix+'.partial')
            with tmp.open('wb') as f:
                for chunk in result.iter_content(4*1024*1024):f.write(chunk)
            tmp.replace(dest)

def collect(version):
    dest=HERE/f'output-v{version}'
    download(version,'b24-status.json',dest/'b24-status.json')
    st=read(dest/'b24-status.json')
    for name in ('b24-evidence.tar.gz','b24-native.tar.gz','b24-models.json'):
        download(version,name,dest/name)
    if st['stage']=='CLOSED':
        for name in ('b24-closed.json','b24-arithmetic-review.json','b24-micro.json','b24-transfer.json'):
            download(version,name,dest/name)
    save(dest/'collection.json',dict(version=version,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir() if p.is_file() and p.name!='collection.json'}))
    return dest,st

def checkpoint_dataset(dest,version):
    folder=HERE/'checkpoint-dataset';folder.mkdir(exist_ok=True)
    save(folder/'dataset-metadata.json',dict(id=CHECKPOINT,title='echo45-s6b24-checkpoint-20261009',licenses=[{'name':'other'}],description='Private exact B24 continuation receipts and native binaries; no credentials.'))
    receipt=HERE/f'checkpoint-upload-v{version}.json'
    if not receipt.exists():
        # Non-archive suffix keeps Kaggle from automatically unpacking checkpoints.
        for source,target in (('b24-evidence.tar.gz','b24-checkpoint.bin'),('b24-native.tar.gz','b24-native.bin')):
            shutil.copyfile(dest/source,folder/target)
        if (HERE/'checkpoint-created.json').exists():
            r=wire(api.dataset_create_version(str(folder),f'B24 exact continuation after kernel version {version}',quiet=True,convert_to_csv=False))
        else:
            r=wire(api.dataset_create_new(str(folder),public=False,quiet=True,convert_to_csv=False))
            save(HERE/'checkpoint-created.json',r)
        if r.get('error'):raise RuntimeError('checkpoint upload rejected')
        save(receipt,r)
    metadata=read(HERE/'notebook/kernel-metadata.json')
    metadata['dataset_sources']=['rogeernavarro/echo45-s6b24-private-20261009',CHECKPOINT]
    save(HERE/'notebook/kernel-metadata.json',metadata)


def follow():
    errors=0
    while True:
        try:
            if not (HERE/'submitted.json').exists():
                left,refresh=quota()
                if left<10800:
                    status('WAITING_GPU_QUOTA',seconds_available=left,refresh=refresh);time.sleep(60);continue
                launch()
            submission=read(HERE/'submitted.json');v=submission['versionNumber']
            remote=wire(api.kernels_status(REF));state=remote['status']
            if state not in ('COMPLETE','ERROR','CANCELLED'):
                status('REMOTE_'+state,version=v);errors=0;time.sleep(60);continue
            dest,st=collect(v)
            if st['stage']=='CLOSED':
                closed=read(dest/'b24-closed.json');review=read(dest/'b24-arithmetic-review.json')
                if not closed['valid'] or not review['valid']:raise RuntimeError('invalid remote closure')
                status('COMPLETE',version=v,closed=closed,receipt=str(dest/'collection.json'));return
            if st['stage']!='CHECKPOINT_READY':
                status('INSTRUMENT_BLOCKED',version=v,remote_status=st);return
            checkpoint_dataset(dest,v)
            left,refresh=quota()
            if left<10800:
                status('WAITING_GPU_QUOTA',version=v,seconds_available=left,refresh=refresh,checkpoint=str(dest));errors=0;time.sleep(60);continue
            launch();errors=0
        except Exception as exc:
            errors+=1;status('COLLECTION_OR_TRANSPORT_ERROR',error_type=type(exc).__name__,consecutive=errors)
            if errors>=10:raise
            time.sleep(min(60,5*errors))


if __name__=='__main__':
    with (HERE/'manager.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if sys.argv[1:]==['follow']:follow()
        elif sys.argv[1:]==['launch']:launch()
        else:raise ValueError('launch or follow')
