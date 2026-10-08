"""Freeze R4 from exact R3 source bytes and explicit, separately named changes."""
import json
from pathlib import Path
import zipfile
from seed import s6b23r4 as r

CONTRACT = 'docs/ECHO45-S6-B23-R4-RECOVERY.md'
R3 = r.REPO / 'lab/kaggle/s6b23-20261008/r3'
OUTPUT = r.REPO / 'lab/kaggle/s6b23-20261008/r4'
NEW_FILES = ['echo_arc/s6b23r4_search.py', 'seed/s6b23r4.py', 'seed/s6b23r4_model.py',
             'seed/s6b23r4_preflight.py', 'seed/s6b23r4_review.py', 'seed/s6b23r4_cloud.py',
             'seed/s6b23r4_build.py', 'tests/test_s6b23r4.py', CONTRACT]


def package():
    parent_zip = R3 / 'dataset/echo-b23-private.zip'
    if r.file_sha(parent_zip) != '46208bd294c7d34190c343c67879662cd2f8aa93c22f5dc13611e48a4d002a23':
        raise RuntimeError('R3 original package changed')
    closed_path = R3 / 'r3-output/b23-closed.json'
    audit_path = R3 / 'r3-output/b23-arithmetic-review.json'
    closed, audit = r.read(closed_path), r.read(audit_path)
    if not closed['valid'] or not audit['valid'] or closed['transfer'] or closed['exam_opened']:
        raise RuntimeError('R3 must be closed, audited, without retention exposure')
    dest = OUTPUT / 'dataset/echo-b23-private.zip'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(parent_zip) as z:
        prior_intent = json.loads(z.read('b23-input/intent.json'))
        for name, digest in prior_intent['sources'].items():
            if r.file_sha(r.REPO / name) != digest:
                raise RuntimeError('R3 frozen source changed: ' + name)
        files = dict(prior_intent['sources'])
        bootstrap = ['seed/s6b23_build.py', 'seed/s6b23_cloud.py', 'seed/s6b23_report.py',
                     'tests/test_s6b23.py', 'tests/__init__.py']
        # All executable bytes, tests and contract are in custody, not LLM input.
        for name in bootstrap + NEW_FILES:
            files[name] = r.file_sha(r.REPO / name)
        inputs = {name: z.read('b23-input/' + name) for name in ('baseline.json', 'exposure-registry.json')}
    receipt = dict(condition='S6-B23-R4', prior_condition='S6-B23-R3',
                   parent_bundle_sha256=r.file_sha(parent_zip), closed_sha256=r.file_sha(closed_path),
                   audit_sha256=r.file_sha(audit_path), retention_opened=False,
                   controls='R3 historical references; not researcher inputs')
    inputs['recovery-parent.json'] = r.canonical(receipt).encode()
    import hashlib
    intent = dict(configuration=r.config(), sources=files,
                  inputs={k: hashlib.sha256(v).hexdigest() for k, v in inputs.items()},
                  contract_sha256=r.file_sha(r.REPO / CONTRACT), games_started=False, models_ready=False)
    with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(r.REPO / name, name)
        for name, data in inputs.items():
            z.writestr('b23-input/' + name, data)
        z.writestr('b23-input/intent.json', r.canonical(intent))
        z.writestr('requirements-b23.txt', 'numpy==2.3.2\narcengine==0.9.3\n')
    r.atomic(OUTPUT / 'intent.json', intent)
    result = dict(path=str(dest), sha256=r.file_sha(dest), private=True, published=False,
                  configuration_sha256=r.sha(r.config()), sources=len(files))
    r.atomic(OUTPUT / 'package.json', result)
    print(r.canonical(result))
    return result


if __name__ == '__main__':
    package()
