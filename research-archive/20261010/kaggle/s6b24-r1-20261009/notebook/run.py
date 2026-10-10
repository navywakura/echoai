"""Private Kaggle transport for the frozen S6-B24 recovery."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

WORK = Path('/kaggle/working')
PROJECT = WORK / 'b24-r1-project'
RESULTS = WORK / 'b24-r1-results'
ASSETS = Path('/tmp/b24-assets')
MODEL_COMMITS = {
    'N7': ('Qwen/Qwen2.5-Coder-7B-Instruct-GGUF', '13fb94bfda8c8cf22497dc57b78f391a9acb426a',
           'qwen2.5-coder-7b-instruct-q4_k_m.gguf'),
}
LLAMA_COMMIT = '79e0b68c178656bb0632cb8602d2940b755077f8'
BUNDLE_SHA = 'd68e890ce70b4400a6a8e046ef48f536a5fdeac9b5e8674625f8d6bfb1fb611d'
NATIVE_SHA = 'a0dac5390422129b6cf4eacda0746d4e1f7b1ee81edea6c96d9aa5f90128b2f8'
SLICE_SECONDS = 7200
STARTED = __import__('time').time()


def run(args, timeout=3600, cwd=None, env=None):
    print(json.dumps({'command': [str(x) for x in args], 'cwd': str(cwd) if cwd else None}), flush=True)
    subprocess.run([str(x) for x in args], cwd=cwd, env=env, check=True, timeout=timeout)


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def save(path, value):
    target = WORK / path
    tmp = target.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    tmp.replace(target)


def setup_project():
    bundles = list(Path('/kaggle/input').rglob('echo-b24-r1-private.zip'))
    if len(bundles) == 1:
        if digest(bundles[0]) != BUNDLE_SHA: raise RuntimeError('changed private B24 bundle')
        PROJECT.mkdir()
        with zipfile.ZipFile(bundles[0]) as z:
            if z.testzip(): raise RuntimeError('damaged bundle')
            for name in z.namelist():
                if not (PROJECT / name).resolve().is_relative_to(PROJECT):
                    raise RuntimeError('unsafe bundle member')
            z.extractall(PROJECT)
    elif not bundles:
        # Kaggle may unpack ZIP datasets when mounting them as notebook input.
        candidates = [p for p in Path('/kaggle/input').rglob('intent.json')
                      if p.parent.name == 'b24-input']
        if len(candidates) != 1:
            mounts = [str(p) for p in Path('/kaggle/input').iterdir()]
            raise RuntimeError('private B24 dataset intent missing/ambiguous; mounts=' + repr(mounts))
        unpacked = candidates[0].parents[1]
        print('B24_DATASET_MOUNT', unpacked, flush=True)
        shutil.copytree(unpacked, PROJECT)
        intent = json.loads((PROJECT / 'b24-input/intent.json').read_text())
        for name, expected in {**intent['sources'],
                               **{'b24-input/' + k: v for k, v in intent['inputs'].items()},
                               'docs/ECHO45-S6-B24-DESIGN.md': intent['contract_sha256']}.items():
            if digest(PROJECT / name) != expected:
                raise RuntimeError('unpacked bundle file changed: ' + name)
    else:
        raise RuntimeError('ambiguous private B24 bundle')
    return PROJECT / 'b24-input'


def setup_python():
    run([sys.executable, '-m', 'pip', 'install', '-q', 'uv==0.11.32', 'huggingface_hub'], timeout=300)
    uv = shutil.which('uv')
    hf = shutil.which('hf')
    if not uv or not hf: raise RuntimeError('uv/hf CLI missing')
    run([uv, 'python', 'install', '3.12.13'], timeout=600)
    venv = ASSETS / 'python'
    run([uv, 'venv', '--python', '3.12.13', venv])
    python = venv / 'bin/python'
    run([uv, 'pip', 'install', '--python', python, 'numpy==2.3.2', 'arcengine==0.9.3'], timeout=600)
    return python, hf


def setup_llama():
    bundles=list(Path('/kaggle/input').rglob('b24-native.bin'))
    if len(bundles)!=1:
        raise RuntimeError('R1 requires exactly one pinned native archive')
    if digest(bundles[0])!=NATIVE_SHA:
        raise RuntimeError('R1 native archive differs from v1')
    with tarfile.open(bundles[0]) as tar:tar.extractall(ASSETS,filter='data')
    return ASSETS/'cuda-build/bin/llama-cli',ASSETS/'cuda-build/bin/llama-tokenize'


def setup_models(hf):
    from huggingface_hub import HfApi
    api = HfApi(token=False)
    names = {}
    for arm, (repo, revision, filename) in MODEL_COMMITS.items():
        info = api.model_info(repo, revision=revision, files_metadata=True)
        if info.sha != revision: raise RuntimeError('model revision moved: ' + arm)
        sibling = next((s for s in info.siblings if s.rfilename == filename), None)
        expected = getattr(sibling, 'lfs', None) if sibling else None
        expected = expected.get('sha256') if isinstance(expected, dict) else getattr(expected, 'sha256', None)
        if not expected: raise RuntimeError('model LFS digest missing: ' + arm)
        dest = ASSETS / 'models' / arm
        dest.mkdir(parents=True)
        run([hf, 'download', repo, filename, '--revision', revision, '--local-dir', dest], timeout=7200)
        path = dest / filename
        if digest(path) != expected: raise RuntimeError('model digest mismatch: ' + arm)
        names[arm] = str(path)
        save('b24-' + arm.lower() + '-asset.json', dict(repo=repo, revision=revision,
             filename=filename, sha256=expected, bytes=path.stat().st_size))
    return names


def export_results():
    if (ASSETS/'cuda-build/bin').exists():
        with tarfile.open(WORK/'b24-native.tar.gz','w:gz') as archive:
            archive.add(ASSETS/'cuda-build/bin',arcname='cuda-build/bin')
    if not RESULTS.exists(): return
    for name in ('status.json', 'budget.json', 'micro.json', 'finalists.json',
                 'transfer.json', 'closed.json', 'arithmetic-review.json', 'model-budget.json', 'estimate.json'):
        source = RESULTS / name
        if source.is_file(): shutil.copy2(source, WORK / ('b24-' + name))
    if (RESULTS / 'format-preflight/receipt.json').is_file():
        shutil.copy2(RESULTS / 'format-preflight/receipt.json', WORK / 'b24-format-receipt.json')
    with tarfile.open(WORK / 'b24-evidence.tar.gz', 'w:gz') as archive:
        archive.add(RESULTS, arcname='b24-r1-results')


def main():
    ASSETS.mkdir()
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                         capture_output=True, text=True, check=True).stdout.strip().splitlines()
    if len(gpu) != 2 or any('T4' not in line for line in gpu):
        raise RuntimeError('frozen two-T4 profile unavailable: ' + repr(gpu))
    save('b24-hardware.json', dict(gpus=gpu, tensor_split='1,1', llama_commit=LLAMA_COMMIT))
    bundle_input = setup_project()
    python, hf = setup_python()
    cli, tokenizer = setup_llama()
    models = setup_models(hf)
    env = dict(os.environ, PYTHONPATH=str(PROJECT), OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               B23_GBNF_VALIDATOR=str(ASSETS / 'cuda-build/bin/test-gbnf-validator'))
    registry = WORK / 'b24-models.json'
    # Registry is generated from the pinned single model and exact native binaries.
    code="""import sys
from pathlib import Path
from seed import s6b24_model as m
from seed.s6b11 import atomic
p,cli,tok,out=sys.argv[1:]
s=dict(family='Qwen2.5-Coder-Instruct',repo='Qwen/Qwen2.5-Coder-7B-Instruct-GGUF',revision=m.REVISION,
       model=p,cli=cli,tokenizer=tok,quantization='Q4_K_M',backend='cuda',gpu_layers=99,tensor_split='1,1')
for k in ('model','cli','tokenizer'):s[k+'_sha256']=m.prior.digest_file(Path(s[k]))
s['gguf']=m.prior.gguf_info(p);s['prompt_protocol']=m.prior.prompt_protocol(s)
m.verify_registry({'N7':s});atomic(Path(out),{'N7':s})
"""
    run([python,'-c',code,models['N7'],cli,tokenizer,registry],cwd=PROJECT,env=env,timeout=1800)
    print('B24_R4_ASSETS_READY', flush=True)
    checkpoints=list(Path('/kaggle/input').rglob('b24-checkpoint.bin'))
    if checkpoints:
        if len(checkpoints)!=1:raise RuntimeError('ambiguous evidence checkpoint')
        with tarfile.open(checkpoints[0]) as tar:tar.extractall(WORK,filter='data')
        if json.loads(registry.read_text())!=json.loads((RESULTS/'input/models.json').read_text()):
            raise RuntimeError('resumed native/model registry differs; explicit recovery required')
        print('B24_RESUME_EXACT_PROFILE',flush=True)
    else:
        run([python,'-m','seed.s6b24_cloud','prepare','--input',bundle_input,'--models',registry,'--root',RESULTS],cwd=PROJECT,env=env,timeout=1800)
    print('B24_PREPARED_PROFILE_FROZEN',flush=True)
    env['ECHO_B24_DEADLINE_EPOCH']=str(STARTED+SLICE_SECONDS)
    run([python,'-u','-m','seed.s6b24_cloud','run','--root',RESULTS],cwd=PROJECT,env=env,timeout=41000)
    print('B24_DIAGNOSTIC_COMPLETE', flush=True)


if __name__ == '__main__':
    try:
        main()
    finally:
        export_results()
