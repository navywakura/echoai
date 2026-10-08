"""Lossless transport extension for the unchanged, frozen B11 experiment."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import FunctionType
import zlib

from seed import s6b11 as s

ROOT = s.ROOT / 'transport-recovery'
SOURCES = ('seed/s6b11_recovery.py', 'seed/s6b11_background.py',
           'lab/kaggle/s6b11-20260929/recovery_transport.py',
           'tests/test_s6b11_recovery.py', 'docs/ECHO45-S6-B11-TRANSPORT-RECOVERY.md')
native_generator, native_audit_model = s.generator, s.audit_model


def digest(data):
    return hashlib.sha256(data).hexdigest()


def profile():
    return {'original_profile_sha256': s.sha(s.integrity()),
            'sources': {name: digest((s.REPO / name).read_bytes()) for name in SOURCES},
            'change': 'zlib/base64 lossless outer transport; exact original source executed',
            'inference_settings_changed': False, 'requests_changed': False,
            'sampling_seeds_changed': False, 'additional_model_calls': 0}


def integrity():
    frozen = json.loads((ROOT / 'profile.json').read_text())
    assert frozen == profile(), 'transport extension changed after freezing'
    return frozen


def prepare():
    value = profile()
    if (ROOT / 'profile.json').exists():
        return integrity()
    inspection = json.loads((s.BASE / 'submission-inspection.json').read_text())
    assert inspection['complete_inventory'] and not inspection['b11'], 'prior submission unresolved'
    assert not any(s.BASE.glob('p*/answers.json')) and not (s.ROOT / 'exam/opened.json').exists()
    for name in SOURCES:
        target = ROOT / 'source-archive' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write((s.REPO / name).read_bytes())
    s.atomic(ROOT / 'profile.json', value)
    s.atomic(ROOT / 'inspection-before-recovery.json', inspection)
    for name in ('status.json', 'supervisor.json'):
        s.atomic(ROOT / ('original-' + name), json.loads((s.ROOT / name).read_text()))
    return value


def pack(source, recovery_sha):
    receipt = {'transport_profile_sha256': recovery_sha, 'executed_source_sha256': digest(source),
               'executed_source_bytes': len(source)}
    encoded = base64.b64encode(zlib.compress(source, level=9)).decode()
    code = ('import base64 as _b11_b64, zlib as _b11_zlib, hashlib as _b11_hash, json as _b11_json\n'
            'from pathlib import Path as _b11_Path\n'
            '_b11_source = _b11_zlib.decompress(_b11_b64.b64decode(' + repr(encoded) + '))\n'
            '_b11_receipt = ' + repr(receipt) + '\n'
            'assert _b11_hash.sha256(_b11_source).hexdigest() == _b11_receipt["executed_source_sha256"]\n'
            'assert len(_b11_source) == _b11_receipt["executed_source_bytes"]\n'
            '_b11_Path("/kaggle/working/transport-receipt.json").write_text(_b11_json.dumps(_b11_receipt))\n'
            'exec(compile(_b11_source, "<B11-frozen-inference>", "exec"), globals(), globals())\n')
    compile(code, '<B11-packed-transport>', 'exec')
    return code, receipt


def unpack(code):
    parsed = ast.parse(code)
    assignment = next(n for n in parsed.body if isinstance(n, ast.Assign) and
                      any(isinstance(t, ast.Name) and t.id == '_b11_source' for t in n.targets))
    return zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value.args[0].args[0])))


def package(stage):
    frozen = integrity()
    folder = s.BASE / stage
    original = (folder / 'notebook/run.py').read_bytes()
    intent = json.loads((folder / 'submission.json').read_text())
    assert intent['wrapper_sha256'] == digest(original)
    code, receipt = pack(original, s.sha(frozen))
    assert unpack(code) == original
    destination = folder / 'transport/notebook'
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'run.py').exists():
        assert (destination / 'run.py').read_text() == code
    else:
        (destination / 'run.py').write_text(code)
    metadata = json.loads((folder / 'notebook/kernel-metadata.json').read_text())
    assert metadata == native_generator().metadata(stage)
    s.atomic(destination / 'kernel-metadata.json', metadata)
    s.atomic(folder / 'transport/package.json', dict(receipt,
        submitted_wrapper_sha256=digest(code.encode()), submitted_wrapper_bytes=len(code.encode()),
        ref=metadata['id'], original_intent_sha256=s.sha(intent)))
    return destination


def transport_call(command, *args):
    process = subprocess.run(['/home/roger/.venvs/kaggle/bin/python',
        str(s.BASE / 'recovery_transport.py'), command, *map(str, args)],
        capture_output=True, text=True, timeout=180)
    if process.returncode:
        ROOT.mkdir(parents=True, exist_ok=True)
        with (ROOT / 'transport-errors.log').open('a') as stream:
            stream.write(command + '\n' + process.stdout + process.stderr + '\n')
        raise RuntimeError('transport extension failed; inspect preserved transport-errors.log')
    return json.loads(process.stdout.splitlines()[-1])


def transport(command, *args):
    if command == 'push':
        stage = Path(args[0]).parent.name
        return transport_call('push', package(stage))
    return native_generator().transport(command, *args)


def audit_transport(stage):
    frozen = integrity()
    folder = s.BASE / stage
    original = (folder / 'notebook/run.py').read_bytes()
    expected_code, expected_receipt = pack(original, s.sha(frozen))
    packed = (folder / 'transport/notebook/run.py').read_text()
    assert packed == expected_code and unpack(packed) == original
    package_receipt = json.loads((folder / 'transport/package.json').read_text())
    submitted = json.loads((folder / 'submitted.json').read_text())
    remote_receipt = json.loads((folder / 'output/transport-receipt.json').read_text())
    assert remote_receipt == expected_receipt
    assert submitted['transport_wrapper_sha256'] == package_receipt['submitted_wrapper_sha256'] == digest(packed.encode())
    assert submitted['submitted'] and submitted['ref'] == package_receipt['ref'] == native_generator().metadata(stage)['id']
    assert submitted['executed_source_sha256'] == digest(original)
    assert json.loads((folder / 'transport/submitted.json').read_text()) == submitted
    assert json.loads((folder / 'transport/notebook/kernel-metadata.json').read_text()) == native_generator().metadata(stage)
    return {'stage': stage, 'valid': True, **expected_receipt,
            'submitted_wrapper_sha256': digest(packed.encode())}


def generator():
    module = native_generator()
    native_propose = FunctionType(module.propose.__code__, dict(module.propose.__globals__, transport=transport))
    def propose(stage, requests, seeds):
        integrity()
        folder = s.BASE / stage
        # Only this recorded, inspected initial failure may be recovered.
        if (folder / 'submission.json').exists() and not (folder / 'submitted.json').exists():
            assert stage == 'p0' and (ROOT / 'inspection-before-recovery.json').exists()
            submitted = transport('push', folder / 'notebook')
            s.atomic(folder / 'submitted.json', submitted)
        result = native_propose(stage, requests, seeds)
        audit_transport(stage)
        return result
    module.propose = propose
    return module


def audit_model(stage, requests_expected=None):
    result = native_audit_model(stage, requests_expected)
    audit_transport(stage)
    return result


def audit_completed():
    integrity()
    receipts = [audit_transport(folder.name) for folder in sorted(s.BASE.iterdir())
                if folder.is_dir() and (folder / 'terminal.json').exists() and
                json.loads((folder / 'terminal.json').read_text())['status'] == 'COMPLETE']
    s.atomic(ROOT / 'audit.json', {'valid': True, 'stages': receipts, 'profile_sha256': s.sha(integrity())})


def follow():
    integrity()
    s.generator, s.audit_model = generator, audit_model
    from seed import s6b11_exam as exam
    native_exam = exam.run
    def guarded_exam():
        subprocess.run([sys.executable, '-m', 'seed.s6b11_recovery', 'audit'], check=True)
        receipt = json.loads((ROOT / 'audit.json').read_text())
        assert {r['stage'] for r in receipt['stages']} == {p + str(i) for p in ('p', 'c') for i in range(6)}
        native_exam()
    exam.run = guarded_exam
    s.main(['follow'])
    subprocess.run([sys.executable, '-m', 'seed.s6b11_recovery', 'audit'], check=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['follow']:
        follow()
    elif sys.argv[1:] == ['audit']:
        audit_completed()
    else:
        raise SystemExit('use prepare, follow, audit')
