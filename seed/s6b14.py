"""B14: repaired experiment controller; frozen B13 executor and gates reused."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from types import FunctionType, SimpleNamespace

from seed import s6b13 as b
from seed import s6b13_model as model
from seed import s6b14_prompt as prompts
from echo_arc import repair_memory

REPO = b.REPO
ROOT = REPO / 'lab/seed/s6b14-20261004'
PREVIOUS = REPO / 'lab/seed/s6b13-native-20261003'
NATIVE = REPO / 'lab/tools/llama-b5904-native'
OLD = b.parent.old
ORIGINAL_VERIFY, ORIGINAL_CONFIG, ORIGINAL_PLAY = b.verify, b.config, b.play_one
SOURCES = list(json.loads((PREVIOUS / 'profile.json').read_text())['sources']) + [
    'echo_arc/repair_memory.py', 'seed/s6b14_prompt.py', 'seed/s6b14.py',
    'tests/test_s6b14_policy.py', 'tests/test_s6b14_runner.py',
    'seed/s6b14_qualification.py', 'docs/ECHO45-S6-B14-DESIGN.md']


def configuration():
    return dict(ORIGINAL_CONFIG(), condition='S6-B14',
                mandatory_latest_receipt=True, exploration_before_exploitation=True,
                selector_accounting='all attempts; refinement descendants charged to root mechanism',
                duplicate_rule='same-base V3 failure, same control/value, all candidate A decisions',
                diversity_cooldown='one proposal after an observed repeated failure; heuristic, shared arms',
                previous_campaign_results_in_prompts=False)


def profile():
    previous = json.loads((PREVIOUS / 'profile.json').read_text())
    for name, expected in previous['sources'].items():
        if hashlib.sha256((REPO / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('frozen B13 source changed: ' + name)
    for name, expected in previous['native_runtime']['artifacts'].items():
        if model.digest_file(REPO / name) != expected:
            raise RuntimeError('native binary changed')
    identity = model.identity()
    if identity != previous['model']:
        raise RuntimeError('model or inference budget changed')
    validation = json.loads((ROOT / 'validation.json').read_text())
    if validation['valid'] is not True or validation['new_games'] != 0 or validation['new_model_calls'] != 0:
        raise RuntimeError('local instrument qualification required')
    if validation['sources'] != b.hashes() or validation['tests_log_sha256'] != \
            model.digest_file(ROOT / 'qualification/tests.log'):
        raise RuntimeError('qualification does not match final sources or tests')
    return dict(sources=b.hashes(), configuration=configuration(), model=identity,
                runtime=b.parent.capacity.previous.runtime(), native_runtime=previous['native_runtime'],
                previous_profile_sha256=b.sha(previous),
                previous_pilot_sha256=b.sha(json.loads((PREVIOUS / 'pilot.json').read_text())),
                instrument_validation_sha256=b.sha(validation))


def previous_closed():
    audit, closed = PREVIOUS / 'pilot-audit.json', PREVIOUS / 'closed.json'
    if not audit.exists() or not closed.exists():
        return False
    a, c = json.loads(audit.read_text()), json.loads(closed.read_text())
    p = json.loads((PREVIOUS / 'profile.json').read_text())
    if a.get('valid') is not True or a.get('independent_execution') is not True \
            or a.get('profile_sha256') != b.sha(p) or a.get('verdicts_rebuilt') != 54 \
            or c.get('result') != 'PILOT_NO_PROMOTION' or c.get('s6_green') is not False \
            or c.get('exam_opened') is not False:
        raise RuntimeError('previous condition did not close with the required valid audit')
    return dict(audit_sha256=b.sha(a), closure_sha256=b.sha(c), profile_sha256=b.sha(p))


def worker_init():
    OLD.worker_init()
    configure()


def play_one(item):
    row = ORIGINAL_PLAY(item)
    if item[1][1] in b.EXAM_SEEDS:
        row['origin'] = 'RESERVED_EXAM_S6B14'
    return row


def measurement(namespace='primary'):
    if namespace not in ('primary', 'pilot-independent', 'campaign-independent', 'exam'):
        raise ValueError('unknown measurement namespace')
    out = ROOT / namespace
    out.mkdir(parents=True, exist_ok=True)
    return FunctionType(b.parent.measure.__code__, dict(b.parent.measure.__globals__,
        ROOT=out, LIVE=out / 'ephemeral-journals', integrity=b.integrity, A=b.A, B=b.B,
        play_one=b.play_one, status=status, WORKERS=b.WORKERS, reserve_games=b.reserve_games,
        old=b.old), 'measure', b.parent.measure.__defaults__)


def verify(measure, label, request, answer, current, before_a, before_b):
    captured = {}
    def capture(name, *args, **kwargs):
        result = measure(name, *args, **kwargs)
        if name == label + '/A':
            captured['a'] = result
        return result
    policy, a, protected, event = ORIGINAL_VERIFY(capture, label, request, answer, current, before_a, before_b)
    if event['verdict'] == 'V3' and 'a' in captured:
        event['decision_certificate'] = repair_memory.certificate(captured['a']['rows'], current, event['candidate'])
    return policy, a, protected, event


def audit_dispatch(command, *args, **kwargs):
    command = list(command)
    if '-m' not in command or command[command.index('-m') + 1] != 'seed.s6b13':
        raise RuntimeError('unexpected audit entry point')
    command[command.index('-m') + 1] = 'seed.s6b14'
    return subprocess.run(command, *args, **kwargs)


def status(stage, **fields):
    value = dict(at=b.now(), condition='S6-B14', stage=stage, **fields)
    b.atomic(ROOT / 'status.json', value)
    print(b.canonical(value), flush=True)


def publish(stage):
    green = False
    lines = ['# S6-B14 — memoria de experimentos y selección corregidas', '',
             'Estado: **' + stage + '**.', '',
             'Recibo reciente obligatorio, evidencia pertinente, exploración contabilizada y',
             'exclusión de fallos V3 equivalentes sobre las trayectorias completas de desarrollo.', '']
    for phase in ('pilot', 'campaign'):
        path = ROOT / (phase + '.json')
        if path.exists():
            value = json.loads(path.read_text())
            lines += [phase + ': ' + b.canonical({k: value[k] for k in ('paired_A', 'accepted_echo', 'promote')}), '']
    if (ROOT / 'exam/audit.json').exists():
        value = json.loads((ROOT / 'exam/audit.json').read_text())
        green = value['green'] and set(value['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(value['checks'].values())
        lines += ['Examen: ' + b.canonical(value['checks']), 'Totales: ' + b.canonical(value['totals']), '']
    lines += ['S6 verde: **' + ('sí' if green else 'no') + '**.', '',
              'Los tests del instrumento no acreditan una ventaja de ECHO. B13 permanece intacto.',
              '[Contrato](ECHO45-S6-B14-DESIGN.md) · [Estado](../lab/seed/s6b14-20261004/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B14-RESULTS.md').write_text('\n'.join(lines))
    begin, end = '<!-- S6B14-BEGIN -->', '<!-- S6B14-END -->'
    block = (begin + '\n**S6-B14: ' + stage + '; S6 ' + ('verde' if green else 'abierto') + '.** '
             'Controlador de experimentos corregido; mismo modelo y requisitos. '
             '[Contrato](ECHO45-S6-B14-DESIGN.md) · [Resultado](ECHO45-S6-B14-RESULTS.md).\n' + end)
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
            text = text.replace(old_row, '| ' + ('✅' if green else '❌') + ' | S6 B1–B5 | B14: '
                                + stage + '; ' + ('auditado' if green else 'pendiente de demostrar') + ' |', 1)
        path.write_text(text)


def configure():
    b.ROOT = ROOT
    b.SOURCES = list(dict.fromkeys(SOURCES))
    b.B = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(27420, 27440)]
    b.EXAM_SEEDS = tuple(range(27500, 27560))
    b.SEEDS, b.CAMPAIGN_SEEDS = (698001, 698017, 698029), (708001,)
    model.CLI, model.TOKENIZER = NATIVE / 'build/bin/llama-cli', NATIVE / 'build/bin/llama-tokenize'
    model.TIMEOUT = 1800
    b.prompts, b.verify, b.play_one = prompts, verify, play_one
    b.profile, b.config, b.status, b.publish = profile, configuration, status, publish
    b.old = SimpleNamespace(worker_init=worker_init, accounting=OLD.accounting)
    b.reserve_games = FunctionType(b.parent.reserve_games.__code__,
        dict(b.parent.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=b.MAX_GAMES))
    b._play = FunctionType(b.parent.play_one.__code__, dict(b.parent.play_one.__globals__,
        ROOT=ROOT, A=b.A, B=b.B, EXAM_SEEDS=b.EXAM_SEEDS))
    b.measurement = measurement
    b.subprocess = SimpleNamespace(run=audit_dispatch, STDOUT=subprocess.STDOUT)


def dispatch(args):
    if args == ['wait-follow']:
        b.prepare()
        publish('WAITING_B13_AUDIT')
        status('WAITING_B13_AUDIT', games_started=False)
        while not previous_closed():
            b.integrity()
            time.sleep(30)
        b.atomic(ROOT / 'previous-audit-gate.json', previous_closed())
        publish('PREFLIGHT_RUNNING')
        (ROOT / 'live').mkdir(exist_ok=True)
        with (ROOT / 'observer-process.log').open('a') as log:
            subprocess.Popen([sys.executable, str(REPO / 'observe.py'), '--launch', str(ROOT / 'live/journal.jsonl')],
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        b.main(['follow'])
    elif args == ['prepare']:
        b.prepare()
    elif len(args) == 2 and args[0] == 'audit' and args[1] in ('pilot', 'campaign'):
        if not previous_closed():
            raise RuntimeError('previous independent audit must close first')
        b.main(args)
    else:
        raise SystemExit('use prepare, wait-follow, audit pilot/campaign')


def main(args):
    try:
        dispatch(args)
    except Exception as exc:
        status('BLOCKED_INSTRUMENT', reason=type(exc).__name__ + ': ' + str(exc))
        publish('BLOCKED_INSTRUMENT')
        raise


if __name__ == '__main__':
    from seed import s6b14
    s6b14.main(sys.argv[1:])
else:
    configure()
