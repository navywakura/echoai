"""B10: witnessed guard decoding, paired model choices and unchanged exam gates."""
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
import subprocess
import sys
from types import FunctionType

from seed import s6b9 as parent, s6_precise_capacity as capacity
from seed.game_selfimprove import atomic, canonical, sha, journal, events
from echo_arc import feasible_requests as prompts
from echo_arc.transition_evidence import Recorder

REPO = parent.REPO
ROOT = REPO / 'lab/seed/s6b10-20260929'
BASE = REPO / 'lab/kaggle/s6b10-20260929'
LIVE = REPO / 'lab/observability/s6b10-20260929'
A, B = parent.A, parent.B
EXAM_SEEDS = tuple(range(24800, 24860))
SEEDS, CAMPAIGN_SEEDS = (655001, 655017, 655029), (665001,)
MODEL, REVISION, CACHE_REF, CACHE_MANIFEST = parent.MODEL, parent.REVISION, parent.CACHE_REF, parent.CACHE_MANIFEST
Execution, strategy, patch, old, now = parent.Execution, parent.strategy, parent.patch, parent.old, parent.now
SOURCES = list(dict.fromkeys(parent.SOURCES + ['echo_arc/transition_evidence.py', 'echo_arc/feasible_grammar.py',
    'echo_arc/feasible_requests.py', 'seed/s6b10.py', 'seed/s6b10_exam.py', 'tests/test_s6b10.py',
    'lab/kaggle/s6b10-20260929/generate.py', 'lab/kaggle/s6b10-20260929/transport.py',
    'docs/ECHO45-S6-B10-DESIGN.md']))


def config():
    return dict(parent.config(), exam_seeds=EXAM_SEEDS, pilot_seeds=SEEDS, campaign_seeds=CAMPAIGN_SEEDS,
                proposal_language='REVALIDATE_NOOP 1..8; witnessed guards; exact own-history novelty',
                missing_witnesses='empty proposal, counted and verified', max_cpu_games=40000)


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def profile():
    return dict(parent.profile(), sources=hashes(), configuration=config(),
                parent_profile_sha256=sha(parent.integrity()),
                parent_pilot_sha256=sha(json.loads((parent.ROOT / 'pilot.json').read_text())),
                parent_audit_sha256=sha(json.loads((parent.ROOT / 'pilot-audit.json').read_text())))


def integrity():
    value = json.loads((ROOT / 'profile.json').read_text())
    assert value == json.loads(canonical(profile())), 'frozen B10 source changed'
    return value


def prepare():
    assert json.loads((parent.ROOT / 'closed.json').read_text())['result'] == 'PILOT_NO_PROMOTION'
    assert json.loads((parent.ROOT / 'pilot-audit.json').read_text())['valid']
    value = profile()
    if (ROOT / 'profile.json').exists():
        integrity()
        return
    for name in SOURCES:
        dest = ROOT / 'source-archive' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((REPO / name).read_bytes())
    atomic(ROOT / 'profile.json', value)
    atomic(ROOT / 'prepared.json', {'at': now(), 'profile_sha256': sha(value)})


def status(stage, **fields):
    row = {'at': now(), 'stage': stage, 'condition': 'S6-B10', **fields}
    atomic(ROOT / 'status.json', row)
    print(canonical(row), flush=True)


bound_play_one = FunctionType(parent.play_one.__code__, dict(parent.play_one.__globals__, ROOT=ROOT,
    EXAM_SEEDS=EXAM_SEEDS, Recorder=Recorder), 'play_one', parent.play_one.__defaults__)


def play_one(item):
    record = bound_play_one(item)
    if item[1][1] in EXAM_SEEDS:
        record['origin'] = 'RESERVED_EXAM_S6B10'
    return record


measure = FunctionType(capacity.measure.__code__, dict(parent.measure.__globals__, ROOT=ROOT, LIVE=LIVE,
    integrity=integrity, status=status, play_one=play_one), 'measure', capacity.measure.__defaults__)
verifier, raw_step, requests = parent.verifier, parent.raw_step, prompts.requests


def phase_shape(phase):
    assert phase in ('pilot', 'campaign')
    return (3, 1, SEEDS) if phase == 'pilot' else (6, 5, CAMPAIGN_SEEDS)


def generator():
    spec = spec_from_file_location('_s6b10_generator', BASE / 'generate.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_phase(phase, index):
    return json.loads((ROOT / phase / f'round-{index}.json').read_text())


def audit_model(stage, requests_expected=None):
    assert json.loads((BASE / stage / 'terminal.json').read_text())['status'] == 'COMPLETE'
    audit = FunctionType(parent.parent.audit_model.__code__, dict(parent.parent.audit_model.__globals__,
        BASE=BASE, generator=generator, integrity=integrity))
    return audit(stage, requests_expected)


run_phase = FunctionType(parent.run_phase.__code__, dict(parent.run_phase.__globals__, ROOT=ROOT, LIVE=LIVE,
    measure=measure, verifier=verifier, integrity=integrity, status=status, requests=requests,
    generator=generator, audit_model=audit_model, raw_step=raw_step, load_phase=load_phase,
    phase_shape=phase_shape), 'run_phase', parent.run_phase.__defaults__)
preflight = FunctionType(parent.preflight.__code__, dict(parent.preflight.__globals__, ROOT=ROOT,
    measure=measure, integrity=integrity), 'preflight', parent.preflight.__defaults__)


def publish(stage):
    lines = ['# S6-B10 · condiciones compatibles con observaciones', '', f'Estado: **{stage}**.', '',
             'CPU int8, modelo fijado; ambos brazos comparten la comprobación mecánica de condiciones.',
             'Ninguna reparación humana en los prompts. Solo B1–B5 permiten declarar S6 verde.', '']
    for phase in ('pilot', 'campaign'):
        path = ROOT / (phase + '.json')
        if path.exists():
            result = json.loads(path.read_text())
            lines.append(phase + ': ' + canonical({k: result[k] for k in ('paired_A', 'accepted_echo', 'promote')}))
    path = ROOT / 'exam/audit.json'
    if path.exists():
        audit = json.loads(path.read_text())
        lines += ['', 'Criterios: ' + canonical(audit['checks']), 'Totales: ' + canonical(audit['totals'])]
    lines += ['', '[Contrato](ECHO45-S6-B10-DESIGN.md) · [Estado](../lab/seed/s6b10-20260929/status.json) ·',
              '[Auditoría del piloto](../lab/seed/s6b10-20260929/pilot-audit.json).', '']
    (REPO / 'docs/ECHO45-S6-B10-RESULTS.md').write_text('\n'.join(lines))


def follow():
    prepare()
    if (ROOT / 'closed.json').exists():
        return
    preflight()
    for phase in ('pilot', 'campaign'):
        path = ROOT / (phase + '.json')
        if path.exists():
            result = json.loads(path.read_text())
        else:
            atomic(ROOT / (phase + '-process.json'), {'at': now(), 'pid': os.getpid()})
            result = run_phase(phase)
        if not (ROOT / (phase + '-audit.json')).exists():
            status('AUDIT', phase=phase)
            with (ROOT / (phase + '-audit-process.log')).open('a') as stream:
                subprocess.run([sys.executable, '-m', 'seed.s6b10', 'audit', phase], check=True,
                               stdout=stream, stderr=subprocess.STDOUT)
        if phase == 'pilot' and not result['promote']:
            atomic(ROOT / 'closed.json', {'at': now(), 'result': 'PILOT_NO_PROMOTION',
                                         's6_green': False, 'exam_opened': False})
            publish('PILOT_NO_PROMOTION')
            status('CLOSED', s6_green=False)
            return
    policies = {'semilla': strategy(), 'sinfiltro': result['raw'],
                **{row['arm']: row['strategy'] for row in result['finals']}}
    atomic(ROOT / 'strategies.json', policies)
    atomic(ROOT / 'completed.json', {'at': now(), 'sources': hashes(), 'strategies_sha256': sha(policies),
                                     'profile_sha256': sha(integrity())})
    from seed import s6b10_exam
    s6b10_exam.run()
    audit = json.loads((ROOT / 'exam/audit.json').read_text())
    atomic(ROOT / 'closed.json', {'at': now(), 'result': 'EXAM_CLOSED',
                                 's6_green': audit['green'], 'checks': audit['checks']})
    publish('EXAM_CLOSED')
    status('CLOSED', s6_green=audit['green'])


def main(args):
    try:
        if args == ['prepare']:
            prepare()
        elif args == ['preflight']:
            prepare()
            preflight()
        elif args == ['follow']:
            follow()
        elif len(args) == 2 and args[0] == 'audit':
            run_phase(args[1], audit=True)
        else:
            raise SystemExit('use prepare, preflight, follow, audit pilot/campaign')
    except Exception as exc:
        status('PENDING_ERROR', error=type(exc).__name__, message=str(exc))
        publish('PENDING_ERROR')
        raise


if __name__ == '__main__':
    from seed import s6b10
    s6b10.main(sys.argv[1:])
