"""Private B15 condition; frozen B13 execution and scientific gates reused."""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import FunctionType, SimpleNamespace

from seed import s6b13 as b, s6b13_model as model, s6b15_prompt as prompts
from echo_arc import repair_memory, repair_experiments

REPO = b.REPO
ROOT = REPO / 'lab/seed/s6b15-20261004'
PREVIOUS = REPO / 'lab/seed/s6b14-20261004'
NATIVE = REPO / 'lab/tools/llama-b5904-native'
OLD = b.parent.old
ORIGINAL_VERIFY, ORIGINAL_CONFIG, ORIGINAL_PLAY = b.verify, b.config, b.play_one
SOURCES = list(json.loads((PREVIOUS / 'profile.json').read_text())['sources']) + [
    'echo_arc/repair_experiments.py', 'seed/s6b15_prompt.py', 'seed/s6b15.py',
    'seed/s6b15_micro.py', 'seed/s6b15_qualification.py',
    'tests/test_s6b15_policy.py', 'tests/test_s6b15_runner.py', 'docs/ECHO45-S6-B15-DESIGN.md']


def configuration():
    return dict(ORIGINAL_CONFIG(), condition='S6-B15', operator_binding=True,
        applicability_scope='selected operator reads in selected development cases',
        selector_credit='actual measured operator; residual credit only on current base',
        fixed_control='cyclic REVALIDATE_NOOP, HOLD, COOLDOWN_CAP; shared availability/family pause',
        random_control='18 pilot samples uniform over legal patches within the fixed scheduled operator',
        family_pause='one call after two fruitless same-base measurements in a family; fallback if sole family',
        summary='numeric extrema, all variable-feature ranges and sampled reading frequencies',
        micro=dict(cells=4, seeds=[730101, 730117, 730129], max_calls=12, max_games=2080,
                   factors=['operator binding', 'numeric summary'],
                   promotion='at least one bound/numeric proposal gains >=2 A levels without individual loss; exact replay'),
        initial_micro_policy='B14 accepted 378-level policy, development calibration only',
        micro_history_in_pilot=False, mandatory_latest_receipt=True,
        duplicate_rule='same-base V3, same setting, identical predicates on complete candidate A decisions',
        previous_campaign_results_in_prompts=False)


def previous_closed():
    paths = [PREVIOUS / n for n in ('pilot-audit.json', 'closed.json', 'profile.json')]
    if not all(p.exists() for p in paths):
        return False
    a, c, p = [json.loads(path.read_text()) for path in paths]
    if a.get('valid') is not True or a.get('independent_execution') is not True \
            or a.get('profile_sha256') != b.sha(p) or a.get('verdicts_rebuilt') != 54 \
            or c.get('result') != 'PILOT_NO_PROMOTION' or c.get('s6_green') is not False \
            or c.get('exam_opened') is not False:
        raise RuntimeError('B14 must have a valid independent negative closure')
    return dict(audit_sha256=b.sha(a), closure_sha256=b.sha(c), profile_sha256=b.sha(p))


def profile():
    previous = json.loads((PREVIOUS / 'profile.json').read_text())
    for name, expected in previous['sources'].items():
        if model.digest_file(REPO / name) != expected:
            raise RuntimeError('frozen B14 source changed: ' + name)
    for name, expected in previous['native_runtime']['artifacts'].items():
        if model.digest_file(REPO / name) != expected:
            raise RuntimeError('native binary changed')
    identity = model.identity()
    if identity != previous['model']:
        raise RuntimeError('model or inference budget changed')
    validation = json.loads((ROOT / 'validation.json').read_text())
    if validation['valid'] is not True or validation['new_games'] != 0 or validation['new_model_calls'] != 0:
        raise RuntimeError('local instrument qualification required')
    if validation['sources'] != b.hashes() or validation['tests_log_sha256'] != model.digest_file(ROOT / 'qualification/tests.log'):
        raise RuntimeError('qualification does not match final sources or tests')
    return dict(sources=b.hashes(), configuration=configuration(), model=identity,
                runtime=b.parent.capacity.previous.runtime(), native_runtime=previous['native_runtime'],
                previous_closure=previous_closed(), instrument_validation_sha256=b.sha(validation))


def worker_init():
    OLD.worker_init()
    configure()


def play_one(item):
    row = ORIGINAL_PLAY(item)
    if item[1][1] in b.EXAM_SEEDS:
        row['origin'] = 'RESERVED_EXAM_S6B15'
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
    actual = repair_experiments.operator(event)
    event['experiment'] = dict(requested_operator=request['requested_operator'], proposed_operator=actual,
        measured_operator=actual if repair_experiments.measured(event) else None,
        changed_games=event.get('development', {}).get('changed_games', 0),
        selected_cases=request['selected_cases'], operator_binding=request['operator_binding'],
        family_cooldown=request['family_cooldown'], call_consumed=True)
    if event['verdict'] == 'V3' and actual and 'a' in captured:
        event['decision_certificate'] = repair_memory.certificate(captured['a']['rows'], current, event['candidate'])
    return policy, a, protected, event


def audit_dispatch(command, *args, **kwargs):
    command = list(command)
    if '-m' not in command or command[command.index('-m') + 1] != 'seed.s6b13':
        raise RuntimeError('unexpected audit entry point')
    command[command.index('-m') + 1] = 'seed.s6b15'
    return subprocess.run(command, *args, **kwargs)


def status(stage, **fields):
    value = dict(at=b.now(), condition='S6-B15', stage=stage, **fields)
    b.atomic(ROOT / 'status.json', value)
    print(b.canonical(value), flush=True)


def publish(stage):
    green = False
    lines = ['# S6-B15 — experimentos ligados a su operador', '', 'Estado: **' + stage + '**.', '',
        'Foco ligado a operador y casos seleccionados; contabilidad de pruebas medidas, crédito por',
        'base vigente, pausa de familias repetidas y resumen numérico. FIJO usa rotación de operadores.', '']
    if (ROOT / 'micro.json').exists():
        micro = json.loads((ROOT / 'micro.json').read_text())
        lines += ['Microensayo: ' + b.canonical({k: micro[k] for k in ('valid', 'promote', 'cells')}), '']
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
        'El microensayo mide reparación instrumental y capacidad de desarrollo; no acredita S6.',
        'B14 permanece cerrado y sus fuentes intactas. Investigación privada.', '',
        '[Contrato](ECHO45-S6-B15-DESIGN.md) · [Estado](../lab/seed/s6b15-20261004/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B15-RESULTS.md').write_text('\n'.join(lines))
    begin, end = '<!-- S6B15-BEGIN -->', '<!-- S6B15-END -->'
    block = (begin + '\n**S6-B15: ' + stage + '; S6 ' + ('verde' if green else 'abierto') + '.** '
        'Nueva condición después del empate auditado B14. Microensayo 2×2 → piloto → auditoría → campaña → examen, '
        'con puertas V1–V4 y B1–B5. [Contrato](ECHO45-S6-B15-DESIGN.md) · [Resultado](ECHO45-S6-B15-RESULTS.md).\n' + end)
    for name in ('NOW.md', 'ECHO45-ECHO5-ROADMAP.md', 'RXLABS_STATUS.md'):
        path = REPO / 'docs' / name
        text = path.read_text()
        if begin in text:
            first, rest = text.split(begin, 1)
            text = first + block + rest.split(end, 1)[1]
        else:
            first, rest = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + rest
        row = next((line for line in text.splitlines() if '| S6 B1–B5 |' in line), None)
        if row:
            text = text.replace(row, '| ' + ('✅' if green else '❌') + ' | S6 B1–B5 | B15: ' + stage
                                + '; ' + ('auditado' if green else 'pendiente de demostrar') + ' |', 1)
        path.write_text(text)


def configure():
    b.ROOT, b.SOURCES = ROOT, list(dict.fromkeys(SOURCES))
    b.B = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(28520, 28540)]
    b.EXAM_SEEDS = tuple(range(28600, 28660))
    b.SEEDS, b.CAMPAIGN_SEEDS = (710101, 710117, 710129), (720101,)
    b.MAX_CALLS = 108  # 12 diagnostic + 36 pilot + 60 campaign.
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


def micro_gate():
    from seed import s6b15_micro
    value = json.loads((ROOT / 'micro.json').read_text())
    if value.get('valid') is not True or value.get('profile_sha256') != b.sha(b.integrity()):
        raise RuntimeError('valid micro qualification required')
    expected = {f'micro/b{int(binding)}-n{int(numeric)}-{seed}' for seed in s6b15_micro.SEEDS
                for binding, numeric in s6b15_micro.CELLS}
    if len(value['cells']) != 12 or {c['cell'] for c in value['cells']} != expected \
            or value['promote'] != s6b15_micro.gate(value['cells']):
        raise RuntimeError('micro cells or promotion mismatch')
    for path, digest in value['artifacts'].items():
        if model.digest_file(ROOT / path) != digest:
            raise RuntimeError('micro artifact changed: ' + path)
    return value['promote']


def dispatch(args):
    if args == ['prepare']:
        b.prepare()
    elif args == ['follow']:
        if not previous_closed():
            raise RuntimeError('B14 independent audit must close first')
        b.prepare()
        with (ROOT / 'pipeline.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if (ROOT / 'closed.json').exists():
                return
            b.atomic(ROOT / 'previous-audit-gate.json', previous_closed())
            b._journal = ROOT / 'live/journal.jsonl'
            (ROOT / 'live').mkdir(exist_ok=True)
            with (ROOT / 'observer-process.log').open('a') as log:
                subprocess.Popen([sys.executable, str(REPO / 'observe.py'), '--launch', str(b._journal)],
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            from seed import s6b15_micro
            s6b15_micro.run()
            if not micro_gate():
                b.atomic(ROOT / 'closed.json', dict(at=b.now(), result='MICRO_NO_PROMOTION',
                         s6_green=False, exam_opened=False))
                status('CLOSED', result='MICRO_NO_PROMOTION', s6_green=False)
                publish('MICRO_NO_PROMOTION')
                return
            b.follow()
    elif len(args) == 2 and args[0] == 'audit' and args[1] in ('pilot', 'campaign'):
        if not previous_closed() or not micro_gate():
            raise RuntimeError('previous closure and micro gate required before audit')
        b.main(args)
    else:
        raise SystemExit('use prepare, follow, audit pilot/campaign')


def main(args):
    try:
        dispatch(args)
    except Exception as exc:
        status('BLOCKED_INSTRUMENT', reason=type(exc).__name__ + ': ' + str(exc))
        publish('BLOCKED_INSTRUMENT')
        raise


if __name__ == '__main__':
    from seed import s6b15
    s6b15.main(sys.argv[1:])
else:
    configure()
