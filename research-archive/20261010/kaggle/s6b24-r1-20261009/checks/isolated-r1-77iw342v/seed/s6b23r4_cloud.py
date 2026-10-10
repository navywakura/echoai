"""Freeze and run the private B23-R4 bundle on Kaggle/Colab, using local assets."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from importlib.metadata import version
from seed import s6b23r4 as r, s6b23r4_model as model


def prepare(bundle_input,models,run_root):
    if sys.flags.optimize:raise RuntimeError('optimized Python disables inherited audit checks')
    if ('.'.join(map(str,sys.version_info[:3])),version('numpy'),version('arcengine'))!=('3.12.13','2.3.2','0.9.3'):
        raise RuntimeError('frozen Python 3.12.13 / numpy 2.3.2 / arcengine 0.9.3 required')
    intent=r.read(bundle_input/'intent.json')
    if intent['configuration']!=__import__('json').loads(r.canonical(r.config())):raise RuntimeError('bundle configuration changed')
    for f,h in intent['sources'].items():
        if r.file_sha(r.REPO/f)!=h:raise RuntimeError('bundle source changed: '+f)
    for f,h in intent['inputs'].items():
        if r.file_sha(bundle_input/f)!=h:raise RuntimeError('bundle input changed: '+f)
    contract=r.REPO/'docs/ECHO45-S6-B23-R4-RECOVERY.md'
    if r.file_sha(contract)!=intent['contract_sha256']:raise RuntimeError('contract changed')
    registry=r.read(models);model.verify_pair(registry)
    if (run_root/'input/manifest.json').exists():raise RuntimeError('already frozen; resume with follow')
    run_root.mkdir(parents=True,exist_ok=True)
    log=run_root/'tests-final.log'
    with log.open('w') as stream:
        subprocess.run([sys.executable,'-m','unittest','tests.test_s6b23','tests.test_s6b23r4','-v'],cwd=r.REPO,
                       stdout=stream,stderr=subprocess.STDOUT,check=True)
    dest=run_root/'input';dest.mkdir(parents=True,exist_ok=True)
    for name in intent['inputs']:shutil.copyfile(bundle_input/name,dest/name)
    r.atomic(dest/'models.json',registry)
    m=dict(configuration=r.config(),sources=intent['sources'],
           inputs={p.name:r.file_sha(p) for p in dest.glob('*.json')},
           python='3.12.13',numpy='2.3.2',arcengine='0.9.3',contract_sha256=intent['contract_sha256'],
           tests_sha256=r.file_sha(log),test_sources={f:r.file_sha(r.REPO/f) for f in ('tests/test_s6b23.py','tests/test_s6b23r4.py')})
    r.immutable(dest/'manifest.json',m)
    r.atomic(run_root/'status.json',dict(stage='PREPARED',games_started=False,profile_sha256=r.sha(m)))
    return m


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run'])
    p.add_argument('--input',type=Path,default=Path('b23-input'))
    p.add_argument('--models',type=Path);p.add_argument('--root',type=Path,required=True)
    a=p.parse_args();root=a.root.resolve()
    if a.command=='prepare':
        if a.models is None:p.error('--models is required for prepare')
        prepare(a.input.resolve(),a.models.resolve(),root)
    else:
        env=dict(os.environ,ECHO_B23R4_ROOT=str(root),ECHO_B23R4_INPUT=str(root/'input'),
                 PYTHONPATH=str(r.REPO),PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
        subprocess.run([sys.executable,'-u','-m','seed.s6b23r4','follow'],cwd=r.REPO,env=env,check=True)


if __name__=='__main__':main()
