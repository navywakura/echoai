"""Private S6-B13, sequential local proposals and unchanged scientific gates."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time
from types import FunctionType

from seed import s6b11 as parent, s6probe2 as probe, s6probe2_independent as independent
from seed import s6b13_prompt as prompts, s6b13_model as model
from seed.game_selfimprove_b5 import no_regressions
from seed.game_selfimprove import journal as s6_journal
from echo_arc import contrastive_evidence as evidence

REPO = parent.REPO
ROOT = REPO / 'lab/seed/s6b13-20261003'
A = parent.A
B = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(26320, 26340)]
EXAM_SEEDS = tuple(range(26400, 26460))
SEEDS, CAMPAIGN_SEEDS = (697001, 697017, 697029), (707001,)
WORKERS, MAX_GAMES, MAX_CALLS = 4, 64000, 96
Execution, strategy, patch, old = parent.Execution, parent.strategy, parent.patch, parent.old
atomic, canonical, sha, now = parent.atomic, parent.canonical, parent.sha, parent.now
NEW_SOURCES = ['seed/s6b13.py', 'seed/s6b13_prompt.py', 'seed/s6b13_model.py',
               'seed/s6b13_exam.py', 'tests/test_s6b13.py', 'docs/ECHO45-S6-B13-DESIGN.md']
DEV_FILES = sorted(str(p.relative_to(REPO)) for p in
                   (REPO / 'lab/kaggle/s6b2-20260927/development_environments').rglob('*')
                   if p.is_file() and p.suffix in ('.py', '.json'))
SOURCES = list(dict.fromkeys(probe.SOURCES + independent.SOURCES + NEW_SOURCES + DEV_FILES))
_journal = None


def config():
    return {'A': A, 'B': B, 'exam_seeds': EXAM_SEEDS, 'pilot_seeds': SEEDS,
            'campaign_seeds': CAMPAIGN_SEEDS, 'pilot_rounds': 6, 'campaign_rounds': 30,
            'calls_per_arm_round': 1, 'workers': WORKERS, 'max_games': MAX_GAMES,
            'max_model_calls': MAX_CALLS, 'random_control': '18 pilot proposals, uniform legal grammar',
            'target_max_attempts': 3, 'initial_policy': strategy(),
            'criteria': 'unchanged V1-V4, B1-B5, paired pilot 2/3 wins and no losses',
            'private': True, 'paid': False, 'manual_positive_controls_in_prompts': False}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def profile():
    audit = json.loads((independent.ROOT / 'audit.json').read_text())
    if not audit.get('valid') or not audit.get('independent_execution') or audit['games'] != 240:
        raise RuntimeError('independent PROBE2 execution required before B13')
    if audit['profile_sha256'] != sha(independent.integrity()):
        raise RuntimeError('independent replay custody changed')
    model_identity = model.identity()
    calibration = json.loads((REPO / 'lab/seed/s6b13-transport-20261003/calls/calibration/result.json').read_text())
    if calibration['profile_sha256'] != sha(model_identity) or calibration['answer'] != canonical(patch.EMPTY):
        raise RuntimeError('matching CPU transport calibration required')
    return {'sources': hashes(), 'configuration': config(), 'model': model.identity(),
            'runtime': parent.capacity.previous.runtime(),
            'probe2_profile_sha256': sha(probe.integrity()), 'probe2_audit_sha256': sha(audit),
            'transport_calibration_sha256': sha(calibration)}


def integrity():
    value = json.loads((ROOT / 'profile.json').read_text())
    if value != json.loads(canonical(profile())):
        raise RuntimeError('B13 sources, model, configuration or provenance changed')
    return value


def prepare():
    if (ROOT / 'profile.json').exists():
        return integrity()
    value = profile()
    for source in SOURCES:
        target = ROOT / 'source-archive' / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / source).read_bytes())
    atomic(ROOT / 'profile.json', value)
    atomic(ROOT / 'prepared.json', {'at': now(), 'profile_sha256': sha(value), 'exam_opened': False})
    publish('PREPARED')
    return value


def status(stage, **fields):
    row = dict(at=now(), stage=stage, condition='S6-B13', **fields)
    atomic(ROOT / 'status.json', row)
    print(canonical(row), flush=True)


def visible(kind, **fields):
    if _journal is not None:
        s6_journal(_journal, dict(kind=kind, **fields))


reserve_games = FunctionType(parent.reserve_games.__code__,
    dict(parent.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=MAX_GAMES))
_play = FunctionType(parent.play_one.__code__, dict(parent.play_one.__globals__,
    ROOT=ROOT, A=A, B=B, EXAM_SEEDS=EXAM_SEEDS))


def play_one(item):
    value, spec, directory = item
    if tuple(spec) not in A + B and not (spec[0] in (2, 3) and spec[1] in EXAM_SEEDS
                                        and spec[2] in (0, 1, 2) and spec[3] == 2000):
        raise ValueError('outside the preregistered partitions')
    cache = None
    if directory:
        path = Path(directory).resolve()
        relative = path.relative_to(ROOT.resolve())
        if relative.parts[0] not in ('primary', 'pilot-independent', 'campaign-independent') \
                or len(relative.parts) != 5 or relative.parts[1] != 'ephemeral-journals' \
                or tuple(spec) not in A:
            raise ValueError('invalid development journal destination')
        partition, digest, key = relative.parts[2:]
        if partition not in ('main', 'replay') or digest != Execution.digest(value):
            raise ValueError('invalid journal partition')
        frozen = json.loads((ROOT / 'profile.json').read_text())
        if key != sha({'profile': sha(frozen), 'candidate': value, 'spec': tuple(spec), 'observed': True}):
            raise ValueError('invalid journal key')
        cache = ROOT / relative.parts[0] / 'cache' / partition / (key + '.json')
    started = time.monotonic()
    row = _play(item)
    if spec[1] in EXAM_SEEDS:
        row['origin'] = 'RESERVED_EXAM_S6B13'
    if cache is not None:
        atomic(cache, {'key': key, 'digest': sha(row), 'record': row})
        shutil.rmtree(directory)  # Durable record first, bounded disk use second.
    atomic(ROOT / 'worker-metrics' / (sha([value, spec, directory, os.getpid()]) + '.json'),
           {'seconds': time.monotonic() - started, 'rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    return row


def measurement(namespace='primary'):
    if namespace not in ('primary', 'pilot-independent', 'campaign-independent', 'exam'):
        raise ValueError('unknown measurement namespace')
    out = ROOT / namespace
    out.mkdir(parents=True, exist_ok=True)
    return FunctionType(parent.measure.__code__, dict(parent.measure.__globals__,
        ROOT=out, LIVE=out / 'ephemeral-journals', integrity=integrity, A=A, B=B,
        play_one=play_one, status=status, WORKERS=WORKERS, reserve_games=reserve_games),
        'measure', parent.measure.__defaults__)


def difference(before, after):
    return {'before': before['levels'], 'after': after['levels'],
            'before_levels': before['levels'], 'after_levels': after['levels'],
            'gain': after['levels'] - before['levels'], 'score_before': before['score'],
            'score_after': after['score'], 'before_trace': before['trace_digest'],
            'after_trace': after['trace_digest'],
            'loss_indices': [i for i, (old_row, new_row) in enumerate(zip(before['rows'], after['rows'], strict=True))
                             if new_row['levels_completed'] < old_row['levels_completed'] or
                             new_row['score'] + 1e-10 < old_row['score']]}


def reproduced(measure, label, policy, specs, observed=True):
    result = measure(label, policy, specs, observed=observed)
    replay = measure(label + '/replay', policy, specs, observed=observed, replay=True)
    if result['trace_digest'] != replay['trace_digest']:
        raise RuntimeError('determinism failure; stop, do not count a negative candidate: ' + label)
    return result


def verify(measure, label, req, answer, current, before_a, before_b):
    event = {'base_sha256': sha(current), 'target_id': req.get('target_id')}
    try:
        proposal = prompts.check_answer(answer, req)
        candidate = strategy(program=patch.append(current['program'], proposal))
    except ValueError as exc:
        return current, before_a, before_b, dict(event, verdict='V1', reason=str(exc))
    event.update(proposal=proposal, candidate=candidate)
    after_a = reproduced(measure, label + '/A', candidate, A)
    event.update(A=difference(before_a, after_a), development=evidence.comparison(before_a, after_a))
    if after_a['levels'] < before_a['levels'] + 2 or not no_regressions(before_a, after_a):
        return current, before_a, before_b, dict(event, verdict='V3', reason='under +2 or individual A regression')
    after_b = reproduced(measure, label + '/B', candidate, B, observed=False)
    event['B'] = difference(before_b, after_b)  # Never included in the model prompt.
    if not no_regressions(before_b, after_b):
        return current, before_a, before_b, dict(event, verdict='V4', reason='individual protected B regression')
    return candidate, after_a, after_b, dict(event, verdict='accepted', reason='unchanged V1-V4 pass')


def raw_step(measure, label, current, answer):
    try:
        proposal = patch.parse(answer)
        candidate = strategy(program=patch.append(current['program'], proposal))
    except ValueError:
        return current, {'source_answer_sha256': sha(answer), 'verdict': 'V1', 'strategy': current}
    # Same ECHO proposals, appended in order. Utility and protected conservation
    # are not consulted. Instrument failures stop the run instead of disappearing.
    reproduced(measure, label + '/raw-A', candidate, A)
    return candidate, {'source_answer_sha256': sha(answer), 'verdict': 'EXECUTABLE',
                       'strategy': candidate, 'V3': 'OMITTED', 'V4': 'OMITTED'}


def phase_shape(phase):
    if phase == 'pilot':
        return 6, 1, SEEDS
    if phase == 'campaign':
        return 30, 1, CAMPAIGN_SEEDS
    raise ValueError('unknown phase')


def run_phase(phase, audit=False):
    rounds, _, seeds = phase_shape(phase)
    frozen = integrity()
    measure = measurement(phase + '-independent' if audit else 'primary')
    baseline_a = measure('baseline/A', strategy(), A)
    baseline_b = measure('baseline/B', strategy(), B, observed=False)
    arms = ('fijo', 'echo', 'random') if phase == 'pilot' else ('fijo', 'echo')
    actors = {(seed, arm): dict(current=strategy(), a=baseline_a, b=baseline_b, history=[])
              for seed in seeds for arm in arms}
    raw, verdicts, raw_events = strategy(), [], []
    for index in range(rounds):
        for (seed, arm), actor in actors.items():
            call_id = f'{phase}/{arm}-{seed}/{index:03d}'
            req = prompts.request('fijo' if arm == 'random' else arm, index, actor['current'], actor['a'], actor['history'])
            if arm == 'random':
                req.update(type='RANDOM', prompt_variants=[])
            saved_path = ROOT / 'steps' / (call_id + '.json')
            saved = json.loads(saved_path.read_text()) if saved_path.exists() else None
            if audit and not saved:
                raise RuntimeError('audit found a missing original step')
            if saved and saved['request_sha256'] != sha(req):
                raise RuntimeError('request reconstruction differs')
            if not audit:
                atomic(ROOT / 'progress.json', dict(at=now(), phase=phase, arm=arm, seed=seed,
                       round=index + 1, rounds=rounds, call=call_id, completed_steps=len(verdicts)))
                status('PROPOSING', phase=phase, arm=arm, seed=seed, round=index + 1)
            sampling_seed = seed + index * 1000
            if arm == 'random':
                answer = prompts.random_answer(req, sampling_seed)
                response = {'answer': answer, 'usage': {'input_tokens': 0, 'max_output_tokens': 0}}
            else:
                if audit or saved:
                    response = model.load(call_id, req, sampling_seed, ROOT, sha(frozen), audit_tokens=audit)
                else:
                    response = model.propose(call_id, req, sampling_seed, ROOT, sha(frozen), MAX_CALLS)
                answer = response['answer']
            if not audit and not saved and arm != 'random':
                visible('requests', requests={call_id: [dict(id=index, type=req['type'],
                        prompt=req['prompt_variants'][response.get('variant', 0)])]})
                visible('answers', answers={'arms': {call_id: [{'id': index, 'answer': answer}]}})
            actor['current'], actor['a'], actor['b'], event = verify(measure, call_id, req,
                    answer, actor['current'], actor['a'], actor['b'])
            behavior = event.get('development', {}).get('behavior_sha256')
            event.update(id=index, arm=arm, seed=seed, type=req['type'], answer=answer, usage=response['usage'],
                         equivalent_calls=[e['id'] for e in actor['history'] if behavior and
                            e.get('development', {}).get('behavior_sha256') == behavior])
            actor['history'].append(event)
            record = {'event': event, 'request_sha256': sha(req), 'profile_sha256': sha(frozen)}
            if phase == 'campaign' and arm == 'echo':
                raw, raw_event = raw_step(measure, call_id, raw, answer)
                record['raw'] = raw_event
                raw_events.append(raw_event)
            if saved:
                if canonical(saved) != canonical(record):
                    raise RuntimeError('independent verifier reconstruction differs: ' + call_id)
            else:
                atomic(saved_path, record)
                visible('verdict', **event)
            verdicts.append(event)
            if not audit:
                status('VERDICT', phase=phase, arm=arm, seed=seed, round=index + 1,
                       verdict=event['verdict'], gain=event.get('A', {}).get('gain'))
                publish('PILOT_RUNNING' if phase == 'pilot' else 'CAMPAIGN_RUNNING')
    finals = [dict(arm=arm, seed=seed, strategy=a['current'], A=a['a']['levels'], B=a['b']['levels'])
              for (seed, arm), a in actors.items()]
    accepted = sum(v['arm'] == 'echo' and v['verdict'] == 'accepted' for v in verdicts)
    promote, totals, pairs = parent.promotion([f for f in finals if f['arm'] != 'random'], accepted, phase)
    result = dict(promote=promote, accepted_echo=accepted, paired_A=totals, pairs=pairs, finals=finals,
                  raw=raw, raw_events=raw_events, verdicts=verdicts, profile_sha256=sha(frozen),
                  model_calls=rounds * len(seeds) * 2, random_proposals=18 if phase == 'pilot' else 0,
                  exam_opened=False)
    if audit:
        original = json.loads((ROOT / (phase + '.json')).read_text())
        if canonical(result) != canonical(original):
            raise RuntimeError('independent phase result differs')
        if os.getpid() == json.loads((ROOT / (phase + '-process.json')).read_text())['pid']:
            raise RuntimeError('audit must run in a separate process')
        atomic(ROOT / (phase + '-audit.json'), dict(valid=True, profile_sha256=sha(integrity()),
               cache_root=str(ROOT / (phase + '-independent') / 'cache'), verdicts_rebuilt=len(verdicts),
               independent_execution=True, pid=os.getpid(), exam_opened=False))
    else:
        atomic(ROOT / (phase + '.json'), result)
    return result


def preflight():
    if (ROOT / 'preflight.json').exists():
        if json.loads((ROOT / 'preflight.json').read_text())['profile_sha256'] != sha(integrity()):
            raise RuntimeError('preflight custody mismatch')
        return
    measure = measurement()
    result = reproduced(measure, 'baseline/A', strategy(), A)
    reference = json.loads((probe.p1.frozen.ROOT / 'measurements/baseline/A.json').read_text())
    if result['trace_digest'] != reference['trace_digest']:
        raise RuntimeError('SEMILLA no longer reproduces the frozen original')
    controls = [A[i] for i in (0, 20, 59, 79)]
    plain = measure('preflight/plain', strategy(), controls, observed=False)
    if any(not parent.capacity.same_behavior(r, result['rows'][A.index(tuple(r[k] for k in
                       ('version', 'seed', 'rep', 'budget')))]) for r in plain['rows']):
        raise RuntimeError('observer affected behavior')
    reproduced(measure, 'baseline/B', strategy(), B, observed=False)
    atomic(ROOT / 'preflight.json', dict(at=now(), profile_sha256=sha(integrity()),
           valid=True, A_levels=result['levels'], observer_parity=True, exam_opened=False))


def publish(stage):
    lines = ['# S6-B13 — refinamiento secuencial privado', '', 'Estado: **' + stage + '**.', '',
             'Qwen3-4B local congelado; una propuesta por llamada, objetivo de refinamiento persistente,',
             'descarte de valores inertes y control aleatorio de la gramática. Todos parten de SEMILLA.',
             'Los controles humanos de PROBE2 permanecen fuera de las peticiones al modelo.', '']
    for phase in ('pilot', 'campaign'):
        if (ROOT / (phase + '.json')).exists():
            result = json.loads((ROOT / (phase + '.json')).read_text())
            lines += [phase + ': ' + canonical({k: result[k] for k in ('paired_A', 'accepted_echo', 'promote')}), '']
    green = False
    if (ROOT / 'exam/audit.json').exists():
        exam = json.loads((ROOT / 'exam/audit.json').read_text())
        green = exam['green'] and set(exam['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(exam['checks'].values())
        lines += ['Examen: ' + canonical(exam['checks']), 'Totales: ' + canonical(exam['totals']), '']
    lines += ['S6 verde: **' + ('sí' if green else 'no') + '**. Investigación privada, sin publicación automática.', '',
              '[Contrato](ECHO45-S6-B13-DESIGN.md) · [Estado](../lab/seed/s6b13-20261003/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B13-RESULTS.md').write_text('\n'.join(lines))
    begin, end = '<!-- S6B13-BEGIN -->', '<!-- S6B13-END -->'
    block = (begin + '\n**S6-B13: ' + stage + '; S6 ' + ('verde' if green else 'todavía abierto') + '.** '
             'Trabajo reanudado por petición del propietario. PROBE2 reproducido en 240 partidas '
             'independientes (378 → 383); ese control humano no entra en los prompts. '
             'B13 prueba descubrimiento autónomo, con criterios V1–V4 y B1–B5 intactos. '
             '[Contrato](ECHO45-S6-B13-DESIGN.md) · [Resultado](ECHO45-S6-B13-RESULTS.md).\n' + end)
    for name in ('NOW.md', 'ECHO45-ECHO5-ROADMAP.md'):
        path = REPO / 'docs' / name
        text = path.read_text()
        if begin in text:
            first, rest = text.split(begin, 1)
            text = first + block + rest.split(end, 1)[1]
        else:
            first, rest = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + rest
        if name == 'ECHO45-ECHO5-ROADMAP.md':
            old_row = next((line for line in text.splitlines() if '| S6 B1–B5 |' in line), None)
            if old_row:
                text = text.replace(old_row, '| ' + ('✅' if green else '❌') + ' | S6 B1–B5 | B13: '
                    + stage + '; ' + ('criterios superados y auditados' if green else
                                      'descubrimiento autónomo, conservación y examen pendientes') + ' |', 1)
        path.write_text(text)


def follow():
    global _journal
    prepare()
    with (ROOT / 'owner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (ROOT / 'closed.json').exists():
            return
        _journal = ROOT / 'live/journal.jsonl'
        visible('proposal', type='PREFLIGHT', verdict='parity pending',
                prompt='B13: reproducir SEMILLA, comprobar observador y conservar B antes del piloto.')
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
                with (ROOT / (phase + '-audit-process.log')).open('a') as log:
                    subprocess.run([sys.executable, '-u', '-m', 'seed.s6b13', 'audit', phase],
                                   stdout=log, stderr=subprocess.STDOUT, check=True)
            if not result['promote']:
                reason = phase.upper() + '_NO_PROMOTION'
                atomic(ROOT / 'closed.json', dict(at=now(), result=reason, s6_green=False, exam_opened=False))
                status('CLOSED', result=reason, s6_green=False)
                publish(reason)
                return
        policies = {'semilla': strategy(), 'sinfiltro': result['raw'],
                    **{f['arm']: f['strategy'] for f in result['finals']}}
        atomic(ROOT / 'strategies.json', policies)
        atomic(ROOT / 'completed.json', dict(at=now(), profile_sha256=sha(integrity()),
               sources=hashes(), strategies_sha256=sha(policies)))
        from seed import s6b13_exam
        s6b13_exam.run()
        exam = json.loads((ROOT / 'exam/audit.json').read_text())
        atomic(ROOT / 'closed.json', dict(at=now(), result='EXAM_CLOSED', s6_green=exam['green'],
               checks=exam['checks'], exam_opened=True))
        status('CLOSED', s6_green=exam['green'], checks=exam['checks'])
        publish('EXAM_CLOSED')


def main(args):
    try:
        if args == ['prepare']:
            prepare()
        elif args == ['follow']:
            follow()
        elif len(args) == 2 and args[0] == 'audit':
            run_phase(args[1], audit=True)
        else:
            raise SystemExit('use prepare, follow, audit pilot/campaign')
    except Exception as exc:
        status('BLOCKED_INSTRUMENT', reason=type(exc).__name__ + ': ' + str(exc))
        publish('BLOCKED_INSTRUMENT')
        raise
if __name__ == '__main__':
    from seed import s6b13
    s6b13.main(sys.argv[1:])
