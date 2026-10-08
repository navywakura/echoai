"""Declared B13 restart with a private native CPU runtime; scientific code reused."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import FunctionType, SimpleNamespace

from seed import s6b13 as b
from seed import s6b13_model as m

REPO = b.REPO
ORIGINAL = REPO / 'lab/seed/s6b13-20261003'
ROOT = REPO / 'lab/seed/s6b13-native-20261003'
RUNTIME = REPO / 'lab/tools/llama-b5904-native'
CALIBRATION = REPO / 'lab/seed/s6b13-native-calibration-20261003'
BASE_SOURCES = list(b.SOURCES)
ADDED_SOURCES = ['seed/s6b13_runtime1.py', 'tests/test_s6b13_runtime1.py',
                 'docs/ECHO45-S6-B13-RUNTIME1.md', 'lab/tools/llama-b5904-native/manifest.json']
ORIGINAL_OLD = b.parent.old
ORIGINAL_RUN = subprocess.run


def runtime_manifest():
    manifest = json.loads((RUNTIME / 'manifest.json').read_text())
    if manifest['source_clean'] is not True:
        raise RuntimeError('native source tree was modified before the build')
    if manifest['commit'] != '79e0b68c178656bb0632cb8602d2940b755077f8':
        # The exact upstream commit, not a moving branch or an installed alias.
        raise RuntimeError('unexpected native runtime source')
    for path, expected in manifest['artifacts'].items():
        if m.digest_file(REPO / path) != expected:
            raise RuntimeError('native runtime artifact changed: ' + path)
    return manifest


def profile():
    original = json.loads((ORIGINAL / 'profile.json').read_text())
    for path, expected in original['sources'].items():
        if hashlib.sha256((REPO / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError('original frozen B13 source changed')
    closed = json.loads((ORIGINAL / 'closed.json').read_text())
    if closed['result'] != 'INCOMPLETE_RUNTIME_REPLACED' or closed['exam_opened'] is not False:
        raise RuntimeError('original CPU run must be preserved and closed as incomplete')
    identity = m.identity()
    calibration = json.loads((CALIBRATION / 'calls/short/result.json').read_text())
    long_calibration = json.loads((CALIBRATION / 'calls/long/result.json').read_text())
    parity = json.loads((CALIBRATION / 'tokenizer-parity.json').read_text())
    for receipt in (calibration, long_calibration):
        if receipt['profile_sha256'] != b.sha(identity) or receipt['answer'] != b.canonical(b.patch.EMPTY):
            raise RuntimeError('native CPU transport calibrations required')
    if parity['valid'] is not True or parity['tokens'] != 1372 \
            or parity['new_tokenizer_sha256'] != m.digest_file(m.TOKENIZER):
        raise RuntimeError('tokenizer parity required')
    independent = json.loads((b.independent.ROOT / 'audit.json').read_text())
    if not independent['valid'] or independent['profile_sha256'] != b.sha(b.independent.integrity()):
        raise RuntimeError('PROBE2 audit custody mismatch')
    return dict(sources=b.hashes(), configuration=b.config(), model=identity,
                runtime=b.parent.capacity.previous.runtime(), native_runtime=runtime_manifest(),
                original_profile_sha256=b.sha(original), original_closure_sha256=b.sha(closed),
                independent_probe2_audit_sha256=b.sha(independent),
                transport_calibration_sha256=b.sha(calibration),
                long_calibration_sha256=b.sha(long_calibration), tokenizer_parity_sha256=b.sha(parity),
                restart='all proposals and games restart; no results pooled with original CPU run')


def worker_init():
    ORIGINAL_OLD.worker_init()
    configure()


def measurement(namespace='primary'):
    if namespace not in ('primary', 'pilot-independent', 'campaign-independent', 'exam'):
        raise ValueError('unknown measurement namespace')
    out = ROOT / namespace
    out.mkdir(parents=True, exist_ok=True)
    return FunctionType(b.parent.measure.__code__, dict(b.parent.measure.__globals__,
        ROOT=out, LIVE=out / 'ephemeral-journals', integrity=b.integrity, A=b.A, B=b.B,
        play_one=b.play_one, status=status, WORKERS=b.WORKERS, reserve_games=b.reserve_games,
        old=b.old), 'measure', b.parent.measure.__defaults__)


def audit_dispatch(command, *args, **kwargs):
    command = list(command)
    if '-m' not in command or command[command.index('-m') + 1] != 'seed.s6b13':
        raise RuntimeError('unexpected child process requested by scientific runner')
    command[command.index('-m') + 1] = 'seed.s6b13_runtime1'
    return ORIGINAL_RUN(command, *args, **kwargs)


def status(stage, **fields):
    value = dict(at=b.now(), condition='S6-B13-R1-NATIVE', stage=stage, **fields)
    b.atomic(ROOT / 'status.json', value)
    print(b.canonical(value), flush=True)


def publish(stage):
    green = False
    lines = ['# S6-B13-R1 — ejecución CPU nativa privada', '', 'Estado: **' + stage + '**.', '',
             'Reinicio completo de B13 con el mismo GGUF, peticiones, gramática, semillas y puertas.',
             'La ejecución original se conserva incompleta; sus resultados no se agregan a esta condición.', '']
    for phase in ('pilot', 'campaign'):
        if (ROOT / (phase + '.json')).exists():
            result = json.loads((ROOT / (phase + '.json')).read_text())
            lines += [phase + ': ' + b.canonical({k: result[k] for k in ('paired_A', 'accepted_echo', 'promote')}), '']
    if (ROOT / 'exam/audit.json').exists():
        exam = json.loads((ROOT / 'exam/audit.json').read_text())
        green = exam['green'] and set(exam['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(exam['checks'].values())
        lines += ['Examen: ' + b.canonical(exam['checks']), 'Totales: ' + b.canonical(exam['totals']), '']
    lines += ['S6 verde: **' + ('sí' if green else 'no') + '**.', '',
              '[Adenda](ECHO45-S6-B13-RUNTIME1.md) · [Estado](../lab/seed/s6b13-native-20261003/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B13-RUNTIME1-RESULTS.md').write_text('\n'.join(lines))
    begin, end = '<!-- S6B13R1-BEGIN -->', '<!-- S6B13R1-END -->'
    block = (begin + '\n**S6-B13-R1: ' + stage + '; S6 ' + ('verde' if green else 'abierto') + '.** '
             'Reinicio declarado con runtime CPU nativo; criterios científicos y modelo conservados. '
             'Los resultados parciales del runtime anterior quedan separados. '
             '[Adenda](ECHO45-S6-B13-RUNTIME1.md) · [Resultado](ECHO45-S6-B13-RUNTIME1-RESULTS.md).\n' + end)
    for name in ('NOW.md', 'ECHO45-ECHO5-ROADMAP.md'):
        path = REPO / 'docs' / name
        text = path.read_text()
        if begin in text:
            first, rest = text.split(begin, 1)
            text = first + block + rest.split(end, 1)[1]
        else:
            first, rest = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + rest
        old_row = next((line for line in text.splitlines() if '| S6 B1–B5 |' in line), None)
        if old_row:
            text = text.replace(old_row, '| ' + ('✅' if green else '❌') + ' | S6 B1–B5 | B13-R1: '
                                + stage + '; ' + ('auditado' if green else 'todavía pendiente') + ' |', 1)
        path.write_text(text)


def configure():
    m.CLI, m.TOKENIZER = RUNTIME / 'build/bin/llama-cli', RUNTIME / 'build/bin/llama-tokenize'
    m.TIMEOUT = 1800
    b.ROOT = ROOT
    b.SOURCES = list(dict.fromkeys(BASE_SOURCES + ADDED_SOURCES))
    b.profile, b.status, b.publish = profile, status, publish
    b.old = SimpleNamespace(worker_init=worker_init, accounting=ORIGINAL_OLD.accounting)
    b.reserve_games = FunctionType(b.parent.reserve_games.__code__,
        dict(b.parent.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=b.MAX_GAMES))
    b._play = FunctionType(b.parent.play_one.__code__, dict(b.parent.play_one.__globals__,
        ROOT=ROOT, A=b.A, B=b.B, EXAM_SEEDS=b.EXAM_SEEDS))
    b.measurement = measurement
    b.subprocess = SimpleNamespace(run=audit_dispatch)


configure()


if __name__ == '__main__':
    from seed import s6b13_runtime1 as r1
    r1.b.main(sys.argv[1:])
