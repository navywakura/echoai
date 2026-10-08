"""Declared execution-time extension. Frozen B12 inference and gates are preserved."""
import ast
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import FunctionType, SimpleNamespace

from seed import s6b12 as s
from seed.s6b11_recovery2 import pack, unpack

ROOT = s.ROOT / 'runtime-recovery1'
BASE = s.BASE / 'runtime-recovery1'
UNIT = 'echoai-s6b12-recovery1'
TIMEOUT = 7200
STAGES = tuple('c' + str(i) for i in range(2, 6))
SOURCES = ('seed/s6b12_recovery1.py', 'lab/kaggle/s6b12-20260930/recovery_transport1.py',
           'tests/test_s6b12_recovery1.py', 'docs/ECHO45-S6-B12-RECOVERY1.md')
original_generator, original_audit = s.generator, s.audit_model


def digest(data):
    return hashlib.sha256(data).hexdigest()


def preserved_paths():
    paths = [s.ROOT / 'campaign' / ('round-' + str(i) + '.json') for i in range(2)]
    paths += [s.BASE / 'c2' / n for n in ('payload.json', 'answers.json', 'submission.json',
        'submitted.json', 'terminal.json', 'notebook/run.py', 'notebook/kernel-metadata.json',
        'packed/package.json', 'packed/intent.json', 'packed/submitted.json',
        'packed/notebook/run.py', 'packed/notebook/kernel-metadata.json',
        'output/answers.json', 'output/context-preflight.json', 'output/weights-receipt.json',
        'output/transport-receipt.json', 'output/echo45-s6b12-c2-20260930.log')]
    return paths


def profile():
    return {'condition': 'S6-B12-R1', 'original_profile_sha256': s.sha(s.integrity()),
        'sources': {name: digest((s.REPO / name).read_bytes()) for name in SOURCES},
        'preserved_artifacts': {str(p.relative_to(s.REPO)): digest(p.read_bytes()) for p in preserved_paths()},
        'configuration': {'stages': list(STAGES), 'job_seconds_cap': TIMEOUT,
            'total_scheduled_remote_seconds_cap': 39600, 'original_completed_prefix': {'fijo': 5, 'echo': 2},
            'require_exact_prefix_replay': True, 'requests_changed': False, 'inference_changed': False,
            'additional_logical_proposals': 0, 'additional_completed_replays': 7,
            'interrupted_compute_included_in_original_job_cap': True}}


def integrity():
    frozen = json.loads((ROOT / 'profile.json').read_text())
    assert frozen == profile(), 'R1 sources or preserved evidence changed after freezing'
    return frozen


def prepare():
    if (ROOT / 'profile.json').exists():
        return integrity()
    assert not (s.ROOT / 'exam/opened.json').exists() and not (s.ROOT / 'closed.json').exists()
    assert json.loads((s.ROOT / 'supervisor.json').read_text())['state'] == 'FINISHED'
    assert json.loads((s.BASE / 'c2/terminal.json').read_text())['status'] == 'CANCEL_ACKNOWLEDGED'
    assert not any(s.BASE.glob('c[3-5]/submitted.json')) and not any(BASE.glob('c*/submitted.json'))
    for stage in ('c0', 'c1'):
        original_audit(stage)
    original_generator().audit_transport('c2')
    partial = json.loads((s.BASE / 'c2/answers.json').read_text())
    assert not partial['complete']
    assert {a.split('-')[1]: len(v) for a, v in partial['arms'].items()} == {'fijo': 5, 'echo': 2}
    inspection = transport('inspect')
    assert inspection['complete_inventory'] and not inspection['recovery_jobs']
    value = profile()
    for name in SOURCES:
        target = ROOT / 'source-archive' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write((s.REPO / name).read_bytes())
    for name in ('status.json', 'supervisor.json', 'progress.json'):
        s.atomic(ROOT / ('original-' + name), json.loads((s.ROOT / name).read_text()))
    s.atomic(ROOT / 'inspection.json', inspection)
    s.atomic(ROOT / 'profile.json', value)
    s.atomic(ROOT / 'prepared.json', {'at': s.now(), 'profile_sha256': s.sha(value), 'exam_opened': False})
    return value


def transport(command, *args):
    result = subprocess.run(['/home/roger/.venvs/kaggle/bin/python',
        str(s.BASE / 'recovery_transport1.py'), command, *map(str, args)],
        text=True, capture_output=True, timeout=300)
    if result.returncode:
        ROOT.mkdir(parents=True, exist_ok=True)
        with (ROOT / 'transport-errors.log').open('a') as stream:
            stream.write(command + '\n' + result.stdout + result.stderr + '\n')
        raise RuntimeError('R1 transport interrupted; immutable job must be reconciled')
    return json.loads(result.stdout.splitlines()[-1])


def metadata(stage):
    assert stage in STAGES
    value = original_generator().metadata(stage)
    value['id'] = 'rogeernavarro/echo45-s6b12-r1-' + stage + '-20260930'
    value['title'] = value['id'].split('/')[1]
    return value


def payload_for(stage, requests, seeds):
    assert stage in STAGES
    gen = original_generator()
    return {'round': int(stage[1:]), 'requests': requests, 'requests_sha256': s.sha(requests),
            'sources': {p: (s.REPO / p).read_text() for p in gen.CODE},
            'source_digest': s.sha(s.integrity()), 'cpu_profile_sha256': s.sha(s.profile()),
            'model': {'id': s.MODEL, 'revision': s.REVISION, 'seeds': seeds,
                      'temperature': .7, 'top_p': .95, 'max_new_tokens': 900}}


def ensure_prefix_replay(partial, completed):
    assert partial['complete'] is False and completed['complete'] is True
    for name in ('profile', 'requests_sha256', 'calibration'):
        assert completed[name] == partial[name], 'c2 replay provenance differs: ' + name
    assert set(partial['arms']) == set(completed['arms'])
    counts = {}
    for arm, prefix in partial['arms'].items():
        assert completed['arms'][arm][:len(prefix)] == prefix, 'c2 saved answer changed: ' + arm
        counts[arm] = len(prefix)
    assert sum(counts.values()) == 7
    return {'exact_saved_answers_reproduced': sum(counts.values()), 'by_arm': counts,
            'partial_sha256': s.sha(partial), 'completed_sha256': s.sha(completed)}


def check_source(source, payload):
    code = source.decode()
    parsed = ast.parse(code)
    encoded = next(node.value.args[0].args[0].value for node in parsed.body
                   if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and
                       target.id == 'payload' for target in node.targets))
    assert json.loads(base64.b64decode(encoded)) == payload, 'embedded payload differs'
    assert code == original_generator().template().replace('PAYLOAD', repr(encoded)), 'inference source differs'


def build_job(stage, requests, seeds):
    frozen = integrity()
    folder = BASE / stage
    payload = payload_for(stage, requests, seeds)
    path = folder / 'payload.json'
    if path.exists():
        assert json.loads(path.read_text()) == payload
    else:
        s.atomic(path, payload)
    if stage == 'c2':
        assert payload == json.loads((s.BASE / stage / 'payload.json').read_text())
        source = (s.BASE / stage / 'notebook/run.py').read_bytes()
    else:
        source = original_generator().template().replace('PAYLOAD',
            repr(base64.b64encode(json.dumps(payload).encode()).decode())).encode()
    compile(source, '<B12-R1-frozen-inference>', 'exec')
    destination = folder / 'notebook'
    destination.mkdir(parents=True, exist_ok=True)
    code_path = destination / 'run.py'
    if code_path.exists():
        # JSON key order in regenerated inputs is immaterial: the archived
        # payload and original embedded source are validated by audit_model.
        if stage == 'c2':
            assert code_path.read_bytes() == source
        source = code_path.read_bytes()
    else:
        code_path.write_bytes(source)
    check_source(source, payload)
    s.atomic(destination / 'kernel-metadata.json', metadata(stage))
    intent = {'ref': metadata(stage)['id'], 'wrapper_sha256': digest(source)}
    if (folder / 'submission.json').exists():
        assert json.loads((folder / 'submission.json').read_text()) == intent
    else:
        s.atomic(folder / 'submission.json', intent)
    code, receipt = pack(source, s.sha(frozen))
    assert unpack(code) == source
    packed = folder / 'packed/notebook'
    packed.mkdir(parents=True, exist_ok=True)
    if (packed / 'run.py').exists():
        assert (packed / 'run.py').read_text() == code
    else:
        (packed / 'run.py').write_text(code)
    s.atomic(packed / 'kernel-metadata.json', metadata(stage))
    s.atomic(folder / 'packed/package.json', dict(receipt,
        submitted_wrapper_sha256=digest(code.encode()), ref=metadata(stage)['id']))
    return folder, packed


def audit_transport(stage):
    frozen = integrity()
    folder = BASE / stage
    source = (folder / 'notebook/run.py').read_bytes()
    code, receipt = pack(source, s.sha(frozen))
    assert (folder / 'packed/notebook/run.py').read_text() == code and unpack(code) == source
    assert json.loads((folder / 'output/transport-receipt.json').read_text()) == receipt
    sent = json.loads((folder / 'submitted.json').read_text())
    assert sent['submitted'] and sent['ref'] == metadata(stage)['id']
    assert sent['cpu_seconds_cap'] == TIMEOUT and sent['gpu'] is False
    assert sent['transport_wrapper_sha256'] == digest(code.encode())
    assert sent['executed_source_sha256'] == digest(source)
    assert sent == json.loads((folder / 'packed/submitted.json').read_text())
    assert json.loads((folder / 'packed/notebook/kernel-metadata.json').read_text()) == metadata(stage)
    payload = json.loads((folder / 'payload.json').read_text())
    expected = {arm: [{'id': r['id'], **r['context']} for r in batch]
                for arm, batch in payload['requests'].items()}
    assert json.loads((folder / 'output/context-preflight.json').read_text()) == expected
    remote = json.loads((folder / 'output/answers.json').read_text())
    assert remote == json.loads((folder / 'answers.json').read_text())
    result = {'valid': True, 'stage': stage, 'profile_sha256': s.sha(frozen), **receipt}
    if stage == 'c2':
        assert source == (s.BASE / 'c2/notebook/run.py').read_bytes()
        assert payload == json.loads((s.BASE / 'c2/payload.json').read_text())
        result['prefix_replay'] = ensure_prefix_replay(
            json.loads((s.BASE / 'c2/answers.json').read_text()), remote)
    return result


def audit_model(stage, requests_expected=None):
    if stage not in STAGES:
        return original_audit(stage, requests_expected)
    integrity()
    assert json.loads((BASE / stage / 'terminal.json').read_text())['status'] == 'COMPLETE'
    native = s.parent.parent.parent.parent.audit_model
    result = FunctionType(native.__code__, dict(native.__globals__, BASE=BASE,
        generator=original_generator, integrity=s.integrity))(stage, requests_expected)
    receipt = audit_transport(stage)
    s.atomic(ROOT / 'receipts' / (stage + '.json'), receipt)
    return result


def propose(stage, requests, seeds):
    integrity()
    assert stage in STAGES
    folder = BASE / stage
    if (folder / 'terminal.json').exists():
        assert json.loads((folder / 'terminal.json').read_text())['status'] == 'COMPLETE', \
            'failed R1 job preserved; no second inference retry'
        return audit_model(stage, requests)
    folder, packed = build_job(stage, requests, seeds)
    if not (folder / 'submitted.json').exists():
        s.atomic(folder / 'submitted.json', transport('push', packed))
    ref = metadata(stage)['id']
    while True:
        state = transport('status', ref)['status']
        status('CPU_INFERENCE', job=stage, status=state, ref=ref)
        if state in ('COMPLETE', 'ERROR', 'CANCELLED', 'CANCEL_ACKNOWLEDGED'):
            break
        time.sleep(30)
    s.atomic(folder / 'terminal.json', {'at': s.now(), 'status': state})
    collect(stage)
    assert state == 'COMPLETE', 'failed R1 job preserved; no second inference retry'
    return audit_model(stage, requests)


def collect(stage):
    folder = BASE / stage
    transport('output', metadata(stage)['id'], folder / 'output')
    answers = folder / 'output/answers.json'
    if answers.exists():
        s.atomic(folder / 'answers.json', json.loads(answers.read_text()))


def generator():
    return SimpleNamespace(propose=propose)


def status(stage, **fields):
    s.status(stage, recovery_condition='S6-B12-R1', **fields)


def publish(stage):
    s.publish(stage)
    path = s.REPO / 'docs/ECHO45-S6-B12-RESULTS.md'
    path.write_text(path.read_text() + '\nContinuación bajo **S6-B12-R1**: límite remoto ampliado, '
        'coste de reproducción atribuido y siete respuestas previas exigidas idénticas. '
        '[Adenda y diagnóstico](ECHO45-S6-B12-RECOVERY1.md).\n')
    begin, end = '<!-- S6B12-R1-BEGIN -->', '<!-- S6B12-R1-END -->'
    block = (begin + '\n**S6-B12-R1 — ' + stage + '.** Recuperación declarada del límite remoto; '
        'mismas propuestas y criterios, reproducción exacta obligatoria de las siete respuestas guardadas. '
        '[Adenda](ECHO45-S6-B12-RECOVERY1.md) · [Seguimiento](ECHO45-S6-B12-LIVE.md).\n' + end)
    for name in ('NOW.md', 'STATUS.md', 'ECHO45-ECHO5-ROADMAP.md'):
        path = s.REPO / 'docs' / name
        text = path.read_text()
        if begin in text:
            first, rest = text.split(begin, 1)
            text = first + block + rest.split(end, 1)[1]
        else:
            first, rest = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + rest
        path.write_text(text)


run_phase = FunctionType(s.run_phase.__code__, dict(s.run_phase.__globals__,
    generator=generator, audit_model=audit_model, publish=publish, status=status),
    'run_phase', s.run_phase.__defaults__)


def audit_campaign():
    integrity()
    (s.ROOT / 'campaign-audit').mkdir(parents=True, exist_ok=True)
    run_phase('campaign', audit=True)
    receipts = [audit_transport(stage) for stage in STAGES]
    s.atomic(ROOT / 'campaign-audit.json', {'valid': True, 'profile_sha256': s.sha(integrity()),
        'audit_pid': os.getpid(), 'receipts': receipts,
        'campaign_sha256': digest((s.ROOT / 'campaign.json').read_bytes()),
        'original_audit_sha256': s.sha(json.loads((s.ROOT / 'campaign-audit.json').read_text()))})


def follow():
    integrity()
    if (s.ROOT / 'closed.json').exists():
        return
    assert json.loads((s.ROOT / 'pilot-audit.json').read_text())['valid']
    s.preflight()
    # A network interruption while collecting a finished job must not trigger
    # another inference. Collection is idempotent and all bytes are audited.
    for stage in STAGES:
        folder = BASE / stage
        if (folder / 'terminal.json').exists():
            assert json.loads((folder / 'terminal.json').read_text())['status'] == 'COMPLETE', 'failed R1 job preserved'
            collect(stage)
    path = s.ROOT / 'campaign.json'
    if path.exists():
        result = json.loads(path.read_text())
    else:
        s.atomic(s.ROOT / 'campaign-process.json', {'at': s.now(), 'pid': os.getpid()})
        result = run_phase('campaign')
    if not (ROOT / 'campaign-audit.json').exists():
        status('AUDIT', phase='campaign')
        publish('RECOVERY1_CAMPAIGN_AUDIT')
        with (s.ROOT / 'campaign-audit-process.log').open('a') as stream:
            subprocess.run([sys.executable, '-u', '-m', 'seed.s6b12_recovery1', 'audit'],
                           stdout=stream, stderr=subprocess.STDOUT, check=True)
    audit = json.loads((ROOT / 'campaign-audit.json').read_text())
    assert audit['valid'] and audit['profile_sha256'] == s.sha(integrity())
    assert audit['campaign_sha256'] == digest(path.read_bytes())
    assert json.loads((s.ROOT / 'campaign-audit.json').read_text())['valid']
    if not result['promote']:
        s.atomic(s.ROOT / 'closed.json', {'at': s.now(), 'result': 'CAMPAIGN_NO_PROMOTION',
            's6_green': False, 'exam_opened': False, 'recovery_profile_sha256': s.sha(integrity())})
        publish('CAMPAIGN_NO_PROMOTION')
        status('CLOSED', result='CAMPAIGN_NO_PROMOTION', s6_green=False, exam_opened=False)
        return
    policies = {'semilla': s.strategy(), 'sinfiltro': result['raw'],
                **{r['arm']: r['strategy'] for r in result['finals']}}
    s.atomic(s.ROOT / 'strategies.json', policies)
    s.atomic(s.ROOT / 'completed.json', {'at': s.now(), 'sources': s.hashes(),
        'strategies_sha256': s.sha(policies), 'profile_sha256': s.sha(s.integrity()),
        'recovery_profile_sha256': s.sha(integrity())})
    # The existing exam checks B5 by calling s.audit_model for every stage.
    # Bind the extension audit without modifying any frozen file or solver.
    s.audit_model = audit_model
    from seed import s6b12_exam
    if not (s.ROOT / 'exam/audit.json').exists():
        s6b12_exam.run()
    exam = json.loads((s.ROOT / 'exam/audit.json').read_text())
    assert set(exam['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'}
    assert exam['green'] == all(exam['checks'].values())
    s.atomic(s.ROOT / 'closed.json', {'at': s.now(), 'result': 'EXAM_CLOSED',
        's6_green': exam['green'], 'checks': exam['checks'], 'exam_opened': True,
        'recovery_profile_sha256': s.sha(integrity())})
    publish('EXAM_CLOSED')
    status('CLOSED', s6_green=exam['green'], checks=exam['checks'])


def run():
    from seed.s6b12_background import notify
    with (s.ROOT / 'supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        integrity()
        for attempt in range(1, 4):
            s.atomic(s.ROOT / 'supervisor.json', {'at': s.now(), 'pid': os.getpid(),
                'state': 'RUNNING', 'unit': UNIT, 'attempt': attempt, 'condition': 'S6-B12-R1'})
            with (ROOT / 'process.log').open('a') as stream:
                result = subprocess.run([sys.executable, '-u', '-m', 'seed.s6b12_recovery1', 'follow'],
                    cwd=s.REPO, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
            failed = any(json.loads(p.read_text())['status'] != 'COMPLETE' for p in BASE.glob('c*/terminal.json'))
            current = json.loads((s.ROOT / 'status.json').read_text())
            recoverable = current.get('message') == 'R1 transport interrupted; immutable job must be reconciled'
            if not result.returncode or failed or not recoverable or attempt == 3:
                break
            time.sleep(30)
        s.atomic(s.ROOT / 'supervisor.json', {'at': s.now(), 'pid': os.getpid(),
            'state': 'FINISHED', 'unit': UNIT, 'attempts': attempt,
            'exit_code': result.returncode, 'condition': 'S6-B12-R1'})
        notify()
        return result.returncode


def start():
    integrity()
    assert not (s.ROOT / 'closed.json').exists()
    for unit in (UNIT, 'echoai-s6b12'):
        active = subprocess.run(['systemctl', '--user', 'is-active', unit + '.service'], capture_output=True, text=True)
        assert active.stdout.strip() not in ('active', 'activating'), 'S6 already running'
    publish('RECOVERY1_STARTING')
    subprocess.run(['systemd-run', '--user', '--collect', '--unit=' + UNIT,
        '--property=Restart=no', '--property=KillMode=control-group',
        '--property=WorkingDirectory=' + str(s.REPO),
        '--property=StandardOutput=append:' + str(ROOT / 'supervisor.log'), '--property=StandardError=inherit',
        'systemd-inhibit', '--what=sleep:idle', '--mode=block', '--who=echoAI',
        '--why=S6-B12-R1 campaign and audit in progress',
        sys.executable, '-u', '-m', 'seed.s6b12_recovery1', 'run'], check=True)
    s.atomic(ROOT / 'launch.json', {'at': s.now(), 'unit': UNIT, 'profile_sha256': s.sha(integrity()),
                                  'restart': 'no', 'sleep_inhibitor': 'sleep:idle'})


def main(args):
    try:
        if args == ['prepare']:
            prepare()
        elif args == ['start']:
            start()
        elif args == ['run']:
            raise SystemExit(run())
        elif args == ['follow']:
            follow()
        elif args == ['audit']:
            audit_campaign()
        else:
            raise SystemExit('use prepare, start, run, follow or audit')
    except Exception as exc:
        status('PENDING_ERROR', error=type(exc).__name__, message=str(exc))
        publish('PENDING_ERROR')
        raise


if __name__ == '__main__':
    main(sys.argv[1:])
