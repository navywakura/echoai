"""Private B24 package. Frozen R4 remains byte-identical; no historical controls."""
import hashlib
import json
from pathlib import Path
import zipfile
from seed import s6b24 as r

CONTRACT='docs/ECHO45-S6-B24-DESIGN.md'
OUTPUT=r.REPO/'lab/kaggle/s6b24-20261009'
R4=r.REPO/'lab/kaggle/s6b23-20261008/r4'
NEW_FILES=['echo_arc/s6b24_search.py','seed/s6b24.py','seed/s6b24_model.py',
           'seed/s6b24_preflight.py','seed/s6b24_review.py','seed/s6b24_cloud.py','seed/s6b24_build.py',
           'tests/test_s6b24_search.py','tests/test_s6b24_model.py','tests/test_s6b24_runner.py','tests/test_s6b24_review.py',CONTRACT]


def package():
    parent=R4/'dataset/echo-b23-private.zip'
    if r.file_sha(parent)!='9b9cf90d896ac8da4f49c848373050d9f1d00d6c3b8bcaa5868f47a15c5b3b94':
        raise RuntimeError('frozen R4 package changed')
    closed=R4/'r4-output/b23-closed.json';audit=R4/'r4-output/b23-arithmetic-review.json'
    c,a=r.read(closed),r.read(audit)
    if not c['valid'] or not a['valid'] or c['transfer'] or c['exam_opened'] or c['physical_games']!=924:
        raise RuntimeError('R4 must be completely closed and audited with retention unopened')
    with zipfile.ZipFile(parent) as z:
        original=json.loads(z.read('b23-input/intent.json'));files=dict(original['sources'])
        for name,h in files.items():
            if r.file_sha(r.REPO/name)!=h:raise RuntimeError('frozen R4 source changed: '+name)
        inputs={n:z.read('b23-input/'+n) for n in ('baseline.json','exposure-registry.json')}
    for name in NEW_FILES:files[name]=r.file_sha(r.REPO/name)
    forbidden=('s6b20_capacity.py','FORensics','FORENSICS','PROBE','proposals.csv','human-')
    if any(any(word in name for word in forbidden) for name in files):raise RuntimeError('analyst/control material in package')
    exposure=json.loads(inputs['exposure-registry.json'])
    if not exposure['valid'] or exposure['cohort_sha256']!=r.sha(r.V_NEW):raise RuntimeError('retention exposure mismatch')
    # Prior metadata review plus explicit unopened R3/R4 closures. Researcher never receives this file.
    inputs['parent-closure.json']=r.canonical(dict(condition='S6-B24',parent_bundle_sha256=r.file_sha(parent),
        closed_sha256=r.file_sha(closed),audit_sha256=r.file_sha(audit),retention_opened=False,
        retention_exposure_scope='registered history reviewed in B23; R3 and R4 never qualified for retention; unregistered external exposure unknown')).encode()
    intent=dict(configuration=r.config(),sources=files,inputs={k:hashlib.sha256(v).hexdigest() for k,v in inputs.items()},
                contract_sha256=r.file_sha(r.REPO/CONTRACT),games_started=False,models_ready=False)
    dest=OUTPUT/'dataset/echo-b24-private.zip';dest.parent.mkdir(parents=True,exist_ok=True)
    if (OUTPUT/'submitted.json').exists():raise RuntimeError('already submitted; cannot overwrite frozen bundle')
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in files:z.write(r.REPO/name,name)
        for name,data in inputs.items():z.writestr('b24-input/'+name,data)
        z.writestr('b24-input/intent.json',r.canonical(intent))
        z.writestr('requirements-b24.txt','numpy==2.3.2\narcengine==0.9.3\n')
    r.atomic(OUTPUT/'intent.json',intent)
    result=dict(path=str(dest),sha256=r.file_sha(dest),private=True,published=False,
                configuration_sha256=r.sha(r.config()),sources=len(files))
    r.atomic(OUTPUT/'package.json',result);print(r.canonical(result));return result


if __name__=='__main__':package()
