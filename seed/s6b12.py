"""B12: inherited, byte-identical audited pilot; fresh bounded-context campaign."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import FunctionType

from seed import s6b11 as parent, s6b11_recovery2 as pilot_transport
from echo_arc import context_requests as prompts

REPO = parent.REPO
ROOT = REPO / 'lab/seed/s6b12-20260930'
BASE = REPO / 'lab/kaggle/s6b12-20260930'
LIVE = REPO / 'lab/observability/s6b12-20260930'
A, B, SEEDS = parent.A, parent.B, parent.SEEDS
EXAM_SEEDS, CAMPAIGN_SEEDS = tuple(range(25100, 25160)), (705001,)
MODEL, REVISION = parent.MODEL, parent.REVISION
CACHE_REF, CACHE_MANIFEST = parent.CACHE_REF, parent.CACHE_MANIFEST
Execution, strategy, patch, old, now = parent.Execution, parent.strategy, parent.patch, parent.old, parent.now
atomic, canonical, sha = parent.atomic, parent.canonical, parent.sha
WORKERS, MAX_GAMES = 4, 64000
SOURCES = list(dict.fromkeys(parent.SOURCES + list(pilot_transport.SOURCES) + [
    'echo_arc/context_requests.py', 'echo_arc/context_tokenizer.py',
    'seed/s6b12.py', 'seed/s6b12_exam.py', 'seed/s6b12_background.py',
    'lab/kaggle/s6b12-20260930/generate.py', 'lab/kaggle/s6b12-20260930/transport.py',
    'tests/test_s6b12.py', 'docs/ECHO45-S6-B12-DESIGN.md']))


def config():
    return dict(parent.config(), exam_seeds=EXAM_SEEDS, campaign_seeds=CAMPAIGN_SEEDS,
                pilot='B11 audited qualification, all 36 prompts unchanged by the context rule',
                new_calls_including_calibration=62, inherited_calls=38, prior_unused_campaign_calls=17,
                cpu_jobs=6, input_tokens=6000, context_tiers=6,
                feedback='same B11 evidence selection; identical context budget rule for both arms',
                protected_cohort='B11 reused, verdict-only; new untouched final exam')


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def profile():
    return {'sources': hashes(), 'configuration': config(),
            'parent_profile_sha256': sha(parent.integrity()),
            'pilot_transport_profile_sha256': sha(pilot_transport.integrity()),
            'parent_pilot_sha256': sha(json.loads((parent.ROOT / 'pilot.json').read_text())),
            'parent_pilot_audit_sha256': sha(json.loads((parent.ROOT / 'pilot-audit.json').read_text())),
            'cache_manifest_sha256': hashlib.sha256(CACHE_MANIFEST.read_bytes()).hexdigest(),
            'tokenizer_files': prompts.tokenizer_manifest(),
            'tokenizer_software': {'transformers': '5.0.0', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'},
            'runtime': parent.capacity.previous.runtime(), 'backend': 'cpu-dynamic-int8', 'threads': 4}


def integrity():
    frozen = json.loads((ROOT / 'profile.json').read_text())
    if frozen != json.loads(canonical(profile())):
        raise RuntimeError('B12 frozen sources, tokenizer, provenance or runtime changed')
    return frozen


def prepare():
    if (ROOT / 'profile.json').exists():
        return integrity()
    assert not (parent.ROOT / 'exam/opened.json').exists()
    assert json.loads((parent.ROOT / 'pilot.json').read_text())['promote']
    assert json.loads((parent.ROOT / 'pilot-audit.json').read_text())['valid']
    assert json.loads((parent.ROOT / 'supervisor.json').read_text())['state'] == 'FINISHED'
    value = profile()
    for source in SOURCES:
        target = ROOT / 'source-archive' / source
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write((REPO / source).read_bytes())
    atomic(ROOT / 'profile.json', value)
    atomic(ROOT / 'prepared.json', {'at': now(), 'profile_sha256': sha(value), 'exam_opened': False})
    publish('PREPARED')
    return value


def status(stage, **fields):
    value = {'at': now(), 'stage': stage, 'condition': 'S6-B12', **fields}
    atomic(ROOT / 'status.json', value)
    print(canonical(value), flush=True)


reserve_games = FunctionType(parent.reserve_games.__code__,
    dict(parent.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=MAX_GAMES))
_play = FunctionType(parent.play_one.__code__, dict(parent.play_one.__globals__,
    ROOT=ROOT, LIVE=LIVE, A=A, B=B, EXAM_SEEDS=EXAM_SEEDS))


def play_one(item):
    result = _play(item)
    if result['origin'] == 'RESERVED_EXAM_S6B11':
        result['origin'] = 'RESERVED_EXAM_S6B12'
    return result


measure = FunctionType(parent.measure.__code__, dict(parent.measure.__globals__,
    ROOT=ROOT, LIVE=LIVE, integrity=integrity, play_one=play_one, status=status, reserve_games=reserve_games),
    'measure', parent.measure.__defaults__)
verifier, raw_step, promotion, requests = parent.verifier, parent.raw_step, parent.promotion, prompts.requests
phase_shape = FunctionType(parent.phase_shape.__code__, dict(parent.phase_shape.__globals__,
    SEEDS=SEEDS, CAMPAIGN_SEEDS=CAMPAIGN_SEEDS))


def generator():
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('_s6b12_generator', BASE / 'generate.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_model(stage, requests_expected=None):
    if stage.startswith('p'):
        result = pilot_transport.audit_model(stage, requests_expected)
        payload = json.loads((parent.BASE / stage / 'payload.json').read_text())
        for arm, batch in payload['requests'].items():
            counts = prompts.count_many([r['prompt'] for r in batch])
            for request, answer, counted in zip(batch, result['arms'][arm], counts, strict=True):
                assert counted['tokens'] <= prompts.LIMIT
                assert counted['tokens'] == answer['usage']['prompt_tokens']
                unchanged = prompts.bounded(request, lambda _: counted)
                assert unchanged['context']['tier'] == 0 and unchanged['prompt'] == request['prompt']
                assert {k: v for k, v in unchanged.items() if k != 'context'} == request
        return result
    assert json.loads((BASE / stage / 'terminal.json').read_text())['status'] == 'COMPLETE'
    native = parent.parent.parent.parent.audit_model
    result = FunctionType(native.__code__, dict(native.__globals__, BASE=BASE,
        generator=generator, integrity=integrity))(stage, requests_expected)
    generator().audit_transport(stage)
    return result


run_phase = FunctionType(parent.run_phase.__code__, dict(parent.run_phase.__globals__,
    ROOT=ROOT, LIVE=LIVE, measure=measure, verifier=verifier, requests=requests,
    generator=generator, audit_model=audit_model, phase_shape=phase_shape,
    integrity=integrity, publish=lambda stage: publish(stage), status=status),
    'run_phase', parent.run_phase.__defaults__)
preflight = FunctionType(parent.preflight.__code__, dict(parent.preflight.__globals__,
    ROOT=ROOT, parent=parent, measure=measure, integrity=integrity,
    publish=lambda stage: publish(stage)), 'preflight', parent.preflight.__defaults__)


def inherit_pilot():
    frozen = integrity()
    for i in range(6):
        audit_model('p' + str(i))
    original = json.loads((parent.ROOT / 'pilot.json').read_text())
    audit = json.loads((parent.ROOT / 'pilot-audit.json').read_text())
    assert original['promote'] and audit['valid'] and audit['verdicts_rebuilt'] == 36
    summary = {k: original[k] for k in ('promote', 'accepted_echo', 'paired_A', 'pairs',
                                      'distinct_development_behaviors', 'calls', 'exam_opened')}
    summary.update(inherited=True, origin='S6-B11', original_sha256=sha(original),
                   profile_sha256=sha(frozen), policies_transferred_to_campaign=False)
    atomic(ROOT / 'pilot.json', summary)
    atomic(ROOT / 'pilot-audit.json', {'valid': True, 'inherited': True,
        'original_audit_sha256': sha(audit), 'original_verdicts_rebuilt': 36,
        'unchanged_requests_checked': 36, 'max_input_tokens': 6000,
        'profile_sha256': sha(frozen), 'audit_pid': os.getpid(), 'exam_opened': False})
    publish('PILOT_INHERITANCE_VERIFIED')


def publish(stage):
    lines = ['# S6-B12 · contexto acotado y campaña nueva', '', f'Estado: **{stage}**.', '',
             'Piloto B11 heredado con identidad de las 36 peticiones y auditoría previa verificadas.',
             'Campaña nueva desde programa vacío; 6000 tokens máximos por petición en ambos brazos.',
             'V1–V4 y B1–B5 conservan sus condiciones.', '']
    for phase in ('pilot', 'campaign'):
        path = ROOT / (phase + '.json')
        if path.exists():
            result = json.loads(path.read_text())
            lines += [phase + ': ' + canonical({k: result[k] for k in
                      ('paired_A', 'accepted_echo', 'promote', 'distinct_development_behaviors')}), '']
    green = False
    path = ROOT / 'exam/audit.json'
    if path.exists():
        result = json.loads(path.read_text())
        green = result['green'] and set(result['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(result['checks'].values())
        lines += ['Criterios: ' + canonical(result['checks']), 'Totales: ' + canonical(result['totals']), '']
    if stage == 'PENDING_ERROR':
        lines += ['Incidencia: ' + canonical(json.loads((ROOT / 'status.json').read_text())), '']
    lines += ['S6 verde: **' + str(green) + '**. ECHO-4.5 requiere también las demás puertas de su roadmap.', '',
              '[Contrato](ECHO45-S6-B12-DESIGN.md) · [Estado](../lab/seed/s6b12-20260930/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B12-RESULTS.md').write_text('\n'.join(lines))
    begin, end = '<!-- S6B12-RESULT-BEGIN -->', '<!-- S6B12-RESULT-END -->'
    block = (begin + '\n**S6-B12 — ' + stage + '. S6 ' + ('VERDE' if green else 'todavía no verde') +
             '.** Contexto verificado antes de inferencia, piloto previo auditado y campaña nueva. '
             '[Contrato](ECHO45-S6-B12-DESIGN.md) · [Resultados](ECHO45-S6-B12-RESULTS.md).\n' + end)
    for name in ('NOW.md', 'STATUS.md', 'ECHO45-ECHO5-ROADMAP.md'):
        path = REPO / 'docs' / name
        text = path.read_text()
        if begin in text:
            first, remaining = text.split(begin, 1)
            text = first + block + remaining.split(end, 1)[1]
        else:
            first, remaining = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + remaining
        path.write_text(text)


def follow():
    prepare()
    if (ROOT / 'closed.json').exists():
        return
    if not (ROOT / 'pilot-audit.json').exists():
        status('PILOT_INHERITANCE_AUDIT')
        subprocess.run([sys.executable, '-m', 'seed.s6b12', 'inherit-pilot'], check=True)
    preflight()
    path = ROOT / 'campaign.json'
    if path.exists():
        result = json.loads(path.read_text())
    else:
        atomic(ROOT / 'campaign-process.json', {'at': now(), 'pid': os.getpid()})
        result = run_phase('campaign')
    if not (ROOT / 'campaign-audit.json').exists():
        status('AUDIT', phase='campaign')
        with (ROOT / 'campaign-audit-process.log').open('a') as log:
            subprocess.run([sys.executable, '-u', '-m', 'seed.s6b12', 'audit', 'campaign'],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    assert json.loads((ROOT / 'campaign-audit.json').read_text())['valid']
    if not result['promote']:
        atomic(ROOT / 'closed.json', {'at': now(), 'result': 'CAMPAIGN_NO_PROMOTION',
                                      's6_green': False, 'exam_opened': False})
        publish('CAMPAIGN_NO_PROMOTION')
        status('CLOSED', result='CAMPAIGN_NO_PROMOTION', s6_green=False, exam_opened=False)
        return
    policies = {'semilla': strategy(), 'sinfiltro': result['raw'],
                **{r['arm']: r['strategy'] for r in result['finals']}}
    atomic(ROOT / 'strategies.json', policies)
    atomic(ROOT / 'completed.json', {'at': now(), 'sources': hashes(),
                                     'strategies_sha256': sha(policies), 'profile_sha256': sha(integrity())})
    from seed import s6b12_exam
    if not (ROOT / 'exam/audit.json').exists():
        s6b12_exam.run()
    audit = json.loads((ROOT / 'exam/audit.json').read_text())
    assert set(audit['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'}
    assert audit['green'] == all(audit['checks'].values())
    atomic(ROOT / 'closed.json', {'at': now(), 'result': 'EXAM_CLOSED', 's6_green': audit['green'],
                                 'checks': audit['checks'], 'exam_opened': True})
    publish('EXAM_CLOSED')
    status('CLOSED', s6_green=audit['green'], checks=audit['checks'])


def main(args):
    try:
        if args == ['prepare']:
            prepare()
        elif args == ['inherit-pilot']:
            inherit_pilot()
        elif args == ['follow']:
            follow()
        elif args == ['audit', 'campaign']:
            (ROOT / 'campaign-audit').mkdir(parents=True, exist_ok=True)
            run_phase('campaign', audit=True)
        else:
            raise SystemExit('use prepare, inherit-pilot, follow, audit campaign')
    except Exception as exc:
        status('PENDING_ERROR', error=type(exc).__name__, message=str(exc))
        publish('PENDING_ERROR')
        raise


if __name__ == '__main__':
    from seed import s6b12
    s6b12.main(sys.argv[1:])
