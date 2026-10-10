"""Frozen B11: contrasting development evidence and autonomous repair selection."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import fcntl
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
import multiprocessing
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
from types import FunctionType, SimpleNamespace

from seed import s6b10 as parent, s6_precise_capacity as capacity, game_selfimprove_b5 as base
from seed.game_selfimprove import canonical, sha, journal
from echo_arc import contrastive_evidence as evidence, contrastive_requests as prompts

REPO = parent.REPO
ROOT = REPO / 'lab/seed/s6b11-20260929'
BASE = REPO / 'lab/kaggle/s6b11-20260929'
LIVE = REPO / 'lab/observability/s6b11-20260929'
A = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(40)]
B = [(v, seed, 0, 2000) for v in (2, 3) for seed in range(24920, 24940)]
EXAM_SEEDS = tuple(range(25000, 25060))
SEEDS, CAMPAIGN_SEEDS = (675001, 675017, 675029), (685001,)
MODEL, REVISION = parent.MODEL, parent.REVISION
CACHE_REF, CACHE_MANIFEST = parent.CACHE_REF, parent.CACHE_MANIFEST
Execution, strategy, patch, old, now = parent.Execution, parent.strategy, parent.patch, parent.old, parent.now
WORKERS, MAX_GAMES = 4, 64000
SOURCES = list(dict.fromkeys(parent.SOURCES + [
    'echo_arc/contrastive_evidence.py', 'echo_arc/contrastive_grammar.py', 'echo_arc/contrastive_requests.py',
    'seed/s6b11.py', 'seed/s6b11_exam.py', 'tests/test_s6b11.py',
    'lab/kaggle/s6b11-20260929/generate.py', 'lab/kaggle/s6b11-20260929/transport.py',
    'docs/ECHO45-S6-B11-DESIGN.md']))


def atomic(path, value):
    """Durable checkpoint before publication; damaged/ambiguous state is refused."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with temporary.open('w') as stream:
        stream.write(canonical(value) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def config():
    return {'A': A, 'B': B, 'exam_seeds': EXAM_SEEDS, 'pilot_seeds': SEEDS,
            'campaign_seeds': CAMPAIGN_SEEDS, 'pilot_rounds': 6, 'pilot_calls_per_arm_round': 1,
            'campaign_rounds': 6, 'campaign_calls_per_arm_round': 5,
            'calls_including_calibration': 100, 'cpu_jobs': 12, 'job_seconds': 3600,
            'paid': False, 'workers': WORKERS, 'max_cpu_games': MAX_GAMES,
            'backend': 'cpu-dynamic-int8', 'criteria': 'unchanged V1-V4 and B1-B5',
            'promotion': 'ECHO accepts; sum A > FIJO; >=2/3 pilot pairs win and none lose; campaign also wins',
            'operators': ['REVALIDATE_NOOP', 'HOLD', 'COOLDOWN_CAP'],
            'prior_human_or_model_policies_in_prompts': False,
            'feedback': 'own A contrasts and measured behavioral duplicates, same interface both arms',
            'protected_feedback': 'verdict only; no B observations', 'observer': 'all A, no B or exam'}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def profile():
    return {'sources': hashes(), 'configuration': config(), 'parent_profile_sha256': sha(parent.integrity()),
            'parent_audit_sha256': sha(json.loads((parent.ROOT / 'pilot-audit.json').read_text())),
            'cache_manifest_sha256': hashlib.sha256(CACHE_MANIFEST.read_bytes()).hexdigest(),
            'runtime': capacity.previous.runtime(), 'backend': 'cpu-dynamic-int8', 'threads': 4}


def integrity():
    value = json.loads((ROOT / 'profile.json').read_text())
    if value != json.loads(canonical(profile())):
        raise RuntimeError('frozen B11 sources/configuration/runtime changed')
    return value


def prepare():
    assert json.loads((parent.ROOT / 'closed.json').read_text())['result'] == 'PILOT_NO_PROMOTION'
    assert json.loads((parent.ROOT / 'pilot-audit.json').read_text())['valid']
    value = profile()
    if (ROOT / 'profile.json').exists():
        return integrity()
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
    row = {'at': now(), 'stage': stage, 'condition': 'S6-B11', **fields}
    atomic(ROOT / 'status.json', row)
    print(canonical(row), flush=True)


def reserve_games(count):
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'budget.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = ROOT / 'budget.json'
        prior = json.loads(path.read_text()) if path.exists() else {'scheduled_games': 0}
        total = prior['scheduled_games'] + count
        if total > MAX_GAMES:
            raise RuntimeError('preregistered game budget exhausted')
        atomic(path, {'scheduled_games': total, 'cap': MAX_GAMES, 'at': now(),
                      'includes': 'training, replay, audit, exam; interrupted scheduled work still counts'})


def play_one(item):
    from echo_arc import agent, runner
    from echo_arc.temporal_bench import _gym_env
    from echo_arc.observe import Journal
    value, spec, directory = item
    version, seed, rep, budget = spec
    reserved = seed in EXAM_SEEDS
    development = tuple(spec) in A
    assert version in (2, 3) and budget == 2000
    assert (reserved and rep in (0, 1, 2)) or tuple(spec) in A or tuple(spec) in B
    assert directory is None or development
    if reserved:
        assert (ROOT / 'exam/opened.json').exists(), 'reserved evaluation requires promotion and policy freeze'
        assert not (ROOT / 'exam/audit.json').exists(), 'closed exam cannot be reopened'
    agent._COMP_CACHE.clear()
    signal.alarm(240)
    recorder = None
    try:
        env = _gym_env(version, seed)
        counted = old.accounting().ResetCounter(env)
        if directory:
            path = Path(directory) / 'arc-decisions.jsonl'
            if path.exists():
                path = path.with_name('arc-decisions-recovery-' + str(os.getpid()) + '.jsonl')
            recorder = evidence.Recorder(Journal(path), origin='DEVELOPMENT_A', program=value['program'])
            recorder.write(kind='start', origin='DEVELOPMENT_A', agent='s6b11', budget=budget,
                           strategy_sha256=Execution.digest(value))
            recorder.write(kind='game', game=env.game_id)
        record = Execution.play(counted, budget, runner.seed_for(env.game_id, rep), value, recorder)
        record.update(version=version, seed=seed, rep=rep, budget=budget, game=env.game_id,
                      family=env.game.fam, baseline=env.baseline_actions, policy_sha256=Execution.digest(value),
                      automatic_reset_indices=counted.automatic,
                      origin='RESERVED_EXAM_S6B11' if reserved else 'DEVELOPMENT_A' if development else 'PROTECTED_B')
        record['score'] = runner.official_game_score(record['actions_per_level'], env.baseline_actions)
        if recorder:
            record['episodes'], record['diagnostics'] = recorder.episodes(), recorder.summary()
            evidence.align_steps(record)
            assert len(record['diagnostics']['trajectory']['steps']) == len(record['actions'])
        assert counted.emitted == len(record['actions'])
        old.accounting().check_record(record)
        return record
    finally:
        if recorder:
            recorder.write(kind='end', status='closed')
            recorder.close()
        signal.alarm(0)


def measure(label, value, specs, observed=True, replay=False):
    value = Execution.validate(value)
    frozen = integrity()
    partition = 'replay' if replay else 'main'
    records, jobs = {}, []
    for spec in specs:
        spec = tuple(spec)
        visible = observed and spec in A
        key = sha({'profile': sha(frozen), 'candidate': value, 'spec': spec, 'observed': visible})
        path = ROOT / 'cache' / partition / (key + '.json')
        if path.exists():
            saved = json.loads(path.read_text())
            assert saved['key'] == key and sha(saved['record']) == saved['digest'], 'damaged cache; preserve and inspect'
            records[spec] = saved['record']
        else:
            directory = str(LIVE / partition / Execution.digest(value) / key) if visible else None
            jobs.append((value, spec, directory))
    if jobs:
        if shutil.disk_usage(ROOT).free < 12 * 1024**3:
            raise RuntimeError('less than 12 GiB free; preserve artifacts and stop before scheduling')
        reserve_games(len(jobs))
        with ProcessPoolExecutor(max_workers=WORKERS, mp_context=multiprocessing.get_context('spawn'),
                                 initializer=old.worker_init) as pool:
            pending = [pool.submit(play_one, item) for item in jobs]
            for future in as_completed(pending):
                row = future.result()
                spec = tuple(row[k] for k in ('version', 'seed', 'rep', 'budget'))
                key = sha({'profile': sha(frozen), 'candidate': value, 'spec': spec, 'observed': observed and spec in A})
                atomic(ROOT / 'cache' / partition / (key + '.json'), {'key': key, 'digest': sha(row), 'record': row})
                records[spec] = row
                status('MEASURING', label=label, completed=len(records), total=len(specs))
    rows = [records[tuple(spec)] for spec in specs]
    result = {'levels': sum(r['levels_completed'] for r in rows), 'score': sum(r['score'] for r in rows),
              'rows': rows, 'trace_digest': sha(rows)}
    integrity()
    atomic(ROOT / 'measurements' / (label + '.json'), result)
    return result


def verifier(measurement):
    def verify(label, answer, current, before_a, before_b):
        captured = {}
        def capture(name, *args, **kwargs):
            result = measurement(name, *args, **kwargs)
            if name == label + '/A':
                captured['a'] = result
            return result
        native = FunctionType(base.verify.__code__, dict(base.verify.__globals__, A=A, B=B,
            strategy=strategy, patch=patch, c=SimpleNamespace(measure=capture, result=capacity.result)))
        value, a, b, verdict = native(label, answer, current, before_a, before_b)
        if 'a' in captured:
            verdict['development'] = evidence.comparison(before_a, captured['a'])
        return value, a, b, verdict
    return verify


requests = prompts.requests
raw_step = FunctionType(parent.raw_step.__code__, dict(parent.raw_step.__globals__, A=A, B=B,
                        patch=patch, strategy=strategy))


def phase_shape(phase):
    if phase not in ('pilot', 'campaign'):
        raise ValueError('unknown phase')
    return (6, 1, SEEDS) if phase == 'pilot' else (6, 5, CAMPAIGN_SEEDS)


def generator():
    spec = spec_from_file_location('_s6b11_generator', BASE / 'generate.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_model(stage, requests_expected=None):
    assert json.loads((BASE / stage / 'terminal.json').read_text())['status'] == 'COMPLETE'
    native = parent.parent.parent.audit_model
    return FunctionType(native.__code__, dict(native.__globals__, BASE=BASE, generator=generator,
                                             integrity=integrity))(stage, requests_expected)


def promotion(finals, accepted, phase):
    pairs = []
    for seed in sorted({r['seed'] for r in finals}):
        pair = {r['arm']: r['A'] for r in finals if r['seed'] == seed}
        pairs.append({'seed': seed, **pair})
    sums = {arm: sum(pair[arm] for pair in pairs) for arm in ('echo', 'fijo')}
    wins = sum(p['echo'] > p['fijo'] for p in pairs)
    losses = sum(p['echo'] < p['fijo'] for p in pairs)
    qualified = bool(accepted and sums['echo'] > sums['fijo'] and losses == 0 and
                     wins >= (2 if phase == 'pilot' else 1))
    return qualified, sums, pairs


def run_phase(phase, audit=False):
    rounds, count, seeds = phase_shape(phase)
    measurement = measure if not audit else FunctionType(measure.__code__, dict(measure.__globals__,
        ROOT=ROOT / (phase + '-audit'), LIVE=LIVE / (phase + '-audit')), 'measure', measure.__defaults__)
    verify = verifier(measurement)
    baseline_a = measurement('baseline/A', strategy(), A)
    baseline_b = measurement('baseline/B', strategy(), B, observed=False)
    actors = {f'local-{arm}-{seed}': {'current': strategy(), 'a': baseline_a, 'b': baseline_b, 'history': []}
              for seed in seeds for arm in ('fijo', 'echo')}
    all_verdicts, raw = [], strategy()
    for r in range(rounds):
        stage = ('p' if phase == 'pilot' else 'c') + str(r)
        batches = {key: requests(key.split('-')[1], r, count, v['current'], v['a'], v['history'])
                   for key, v in actors.items()}
        saved_path = ROOT / phase / f'round-{r}.json'
        saved = json.loads(saved_path.read_text()) if saved_path.exists() else None
        if audit or saved:
            assert saved and saved['requests'] == batches, 'request reconstruction differs'
            response = audit_model(stage, batches)
        else:
            journal(ROOT / 'live/journal.jsonl', {'kind': 'requests', 'phase': phase, 'round': r, 'requests': batches})
            response = generator().propose(stage, batches, {k: int(k.rsplit('-', 1)[-1]) + r * 1000 for k in batches})
            journal(ROOT / 'live/journal.jsonl', {'kind': 'answers', 'phase': phase, 'round': r, 'answers': response})
        verdicts, raw_events = [], []
        for key, actor in actors.items():
            arm, seed = key.split('-')[1], int(key.rsplit('-', 1)[-1])
            for request, answer in zip(batches[key], response['arms'][key], strict=True):
                label = f"{phase}/{key}/{request['id']}"
                actor['current'], actor['a'], actor['b'], event = verify(label, answer['answer'],
                    actor['current'], actor['a'], actor['b'])
                event.update(arm=arm, seed=seed, id=request['id'], type=request['type'], answer=answer['answer'],
                             prompt_sha256=sha(request['prompt']), usage=answer['usage'])
                behavior = event.get('development', {}).get('behavior_sha256')
                event['equivalent_calls'] = [v['id'] for v in actor['history'] if behavior and
                    v.get('development', {}).get('behavior_sha256') == behavior]
                actor['history'].append(event)
                verdicts.append(event)
                if not audit and not saved:
                    journal(ROOT / 'live/journal.jsonl', dict(kind='verdict', phase=phase, **event))
                    status('VERDICT', phase=phase, arm=arm, seed=seed, call=request['id'],
                           verdict=event['verdict'], gain=event.get('A', {}).get('gain'),
                           equivalent_calls=event['equivalent_calls'])
                if phase == 'campaign' and arm == 'echo':
                    raw, entry = raw_step(label, raw, answer['answer'], measurement)
                    raw_events.append(entry)
        record = {'requests': batches, 'verdicts': verdicts, 'raw': raw_events, 'profile_sha256': sha(integrity())}
        if saved:
            assert canonical(saved) == canonical(record), 'independent verifier reconstruction differs'
        else:
            atomic(saved_path, record)
        all_verdicts.extend(verdicts)
        if not audit:
            publish('PILOT_RUNNING' if phase == 'pilot' else 'CAMPAIGN_RUNNING')
    finals = [{'arm': k.split('-')[1], 'seed': int(k.rsplit('-', 1)[-1]), 'strategy': v['current'],
               'A': v['a']['levels'], 'B': v['b']['levels']} for k, v in actors.items()]
    accepted = sum(v['arm'] == 'echo' and v['verdict'] == 'accepted' for v in all_verdicts)
    promote, totals, pairs = promotion(finals, accepted, phase)
    result = {'promote': promote, 'accepted_echo': accepted, 'paired_A': totals, 'pairs': pairs,
              'verdicts': all_verdicts, 'finals': finals, 'raw': raw,
              'distinct_development_behaviors': len({v['development']['behavior_sha256'] for v in all_verdicts if 'development' in v}),
              'calls': rounds * count * 2 * len(seeds) + 2, 'profile_sha256': sha(integrity()), 'exam_opened': False}
    if audit:
        assert result == json.loads((ROOT / (phase + '.json')).read_text())
        assert os.getpid() != json.loads((ROOT / (phase + '-process.json')).read_text())['pid']
        atomic(ROOT / (phase + '-audit.json'), {'valid': True, 'verdicts_rebuilt': len(all_verdicts),
               'profile_sha256': sha(integrity()), 'audit_pid': os.getpid(), 'exam_opened': False})
    else:
        atomic(ROOT / (phase + '.json'), result)
    return result


def preflight():
    if (ROOT / 'preflight.json').exists():
        assert json.loads((ROOT / 'preflight.json').read_text())['profile_sha256'] == sha(integrity())
        return
    a = measure('baseline/A', strategy(), A)
    previous = json.loads((parent.ROOT / 'measurements/baseline/A.json').read_text())
    for row in previous['rows']:
        same = next(r for r in a['rows'] if (r['version'], r['seed']) == (row['version'], row['seed']))
        assert capacity.same_behavior(row, same), 'original baseline changed'
    parity_specs = [(2, 0, 0, 2000), (3, 19, 0, 2000), (2, 20, 0, 2000), (3, 39, 0, 2000)]
    plain = measure('preflight/plain', strategy(), parity_specs, observed=False)
    for row in plain['rows']:
        same = next(r for r in a['rows'] if (r['version'], r['seed']) == (row['version'], row['seed']))
        assert capacity.same_behavior(row, same), 'observer changed behavior'
    measure('baseline/B', strategy(), B, observed=False)
    atomic(ROOT / 'preflight.json', {'at': now(), 'pass': True, 'original_A_parity': True,
           'observer_parity_games': len(parity_specs), 'A_levels': a['levels'], 'A_games': len(A),
           'exam_opened': False, 'profile_sha256': sha(integrity())})
    publish('PREFLIGHT_COMPLETE')


def publish(stage):
    lines = ['# S6-B11 · aprendizaje a partir de contrastes', '', f'Estado: **{stage}**.', '',
             'Desarrollo ampliado a 80 partidas; validación protegida y reserva nuevas.',
             'Mismos V1–V4 y B1–B5. Propuestas Qwen, selección ECHO, verificación y conservación separadas.',
             'Los cinco criterios finales deben pasar para declarar S6 verde.', '']
    for phase in ('pilot', 'campaign'):
        path = ROOT / (phase + '.json')
        if path.exists():
            result = json.loads(path.read_text())
            lines += [phase + ': ' + canonical({k: result[k] for k in
                      ('paired_A', 'accepted_echo', 'promote', 'distinct_development_behaviors')}), '']
    green = False
    path = ROOT / 'exam/audit.json'
    if path.exists():
        value = json.loads(path.read_text())
        green = value['green'] and set(value['checks']) == {'B1', 'B2', 'B3', 'B4', 'B5'} and all(value['checks'].values())
        lines += ['Criterios: ' + canonical(value['checks']), 'Totales: ' + canonical(value['totals']), '']
    lines += ['[Contrato](ECHO45-S6-B11-DESIGN.md) · [Estado](../lab/seed/s6b11-20260929/status.json).', '']
    (REPO / 'docs/ECHO45-S6-B11-RESULTS.md').write_text('\n'.join(lines))
    begin, end = '<!-- S6B11-RESULT-BEGIN -->', '<!-- S6B11-RESULT-END -->'
    block = (begin + '\n**S6-B11 — ' + stage + '. S6 ' + ('VERDE' if green else 'todavía no verde') +
             '.** Desarrollo ampliado, contrastes antes/después y selección adaptativa; conservación estricta. '
             '[Contrato](ECHO45-S6-B11-DESIGN.md) · [Resultado](ECHO45-S6-B11-RESULTS.md) · '
             '[Estado](../lab/seed/s6b11-20260929/status.json).\n' + end)
    for name in ('NOW.md', 'STATUS.md', 'ECHO45-ECHO5-ROADMAP.md'):
        target = REPO / 'docs' / name
        text = target.read_text()
        if begin in text:
            prefix, suffix = text.split(begin, 1)
            text = prefix + block + suffix.split(end, 1)[1]
        else:
            first, remainder = text.split('\n', 1)
            text = first + '\n\n' + block + '\n' + remainder
        target.write_text(text)


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
            with (ROOT / (phase + '-audit-process.log')).open('a') as log:
                subprocess.run([sys.executable, '-u', '-m', 'seed.s6b11', 'audit', phase], check=True,
                               stdout=log, stderr=subprocess.STDOUT)
        assert json.loads((ROOT / (phase + '-audit.json')).read_text())['valid']
        if not result['promote']:
            reason = phase.upper() + '_NO_PROMOTION'
            atomic(ROOT / 'closed.json', {'at': now(), 'result': reason, 's6_green': False, 'exam_opened': False})
            publish(reason)
            status('CLOSED', result=reason, s6_green=False, exam_opened=False)
            return
    policies = {'semilla': strategy(), 'sinfiltro': result['raw'],
                **{row['arm']: row['strategy'] for row in result['finals']}}
    atomic(ROOT / 'strategies.json', policies)
    atomic(ROOT / 'completed.json', {'at': now(), 'sources': hashes(), 'strategies_sha256': sha(policies),
                                     'profile_sha256': sha(integrity())})
    from seed import s6b11_exam
    s6b11_exam.run()
    audit = json.loads((ROOT / 'exam/audit.json').read_text())
    atomic(ROOT / 'closed.json', {'at': now(), 'result': 'EXAM_CLOSED', 's6_green': audit['green'],
                                 'checks': audit['checks'], 'exam_opened': True})
    publish('EXAM_CLOSED')
    status('CLOSED', s6_green=audit['green'], checks=audit['checks'])


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
    from seed import s6b11
    s6b11.main(sys.argv[1:])
