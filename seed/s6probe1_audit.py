"""Independent PROBE1 re-execution, using frozen actors in a separate cache."""
import fcntl
import hashlib
import json
from pathlib import Path
from types import FunctionType

from seed import s6b11, s6probe1 as p1
from echo_arc import stale_transition as patch
from echo_arc.contrastive_evidence import behavior_digest

ROOT = p1.REPO / 'lab/seed/s6probe1-20260930-audit'
LIVE = ROOT / 'journals'
EPHEMERAL = ROOT / 'ephemeral-journals'
A = p1.A
SAMPLE = (2, 31, 77, 178)
WORKERS, MAX_GAMES = 4, 480
sha, atomic = p1.sha, p1.atomic


def fingerprint():
    return {'probe1_profile_sha256': sha(p1.integrity()),
            'probe1_result_sha256': hashlib.sha256((p1.ROOT / 'result.json').read_bytes()).hexdigest(),
            'audit_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'sample_single_indices': list(SAMPLE), 'workers': WORKERS, 'max_games': MAX_GAMES}


def integrity():
    saved = json.loads((ROOT / 'profile.json').read_text())
    if saved != fingerprint():
        raise RuntimeError('audit source or PROBE1 changed')
    return saved


def status(stage, **fields):
    value = dict(at=p1.now(), stage=stage, condition='PROBE1-INDEPENDENT-AUDIT', **fields)
    atomic(ROOT / 'status.json', value)
    print(p1.canonical(value), flush=True)


reserve_games = FunctionType(s6b11.reserve_games.__code__,
    dict(s6b11.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=MAX_GAMES))
_play = FunctionType(s6b11.play_one.__code__, dict(s6b11.play_one.__globals__,
    ROOT=ROOT, LIVE=LIVE, A=A, B=[], EXAM_SEEDS=()))
play_one = FunctionType(p1.play_one.__code__, dict(p1.play_one.__globals__,
    __name__=__name__, ROOT=ROOT, LIVE=LIVE, EPHEMERAL=EPHEMERAL, _play=_play), 'play_one')
_measure = FunctionType(p1._measure.__code__, dict(p1._measure.__globals__,
    ROOT=ROOT, integrity=integrity, play_one=play_one, status=status,
    reserve_games=reserve_games, WORKERS=WORKERS), '_measure')
measure = _measure(LIVE)


def original_rows(value):
    profile = p1.integrity()
    rows = []
    for spec in A:
        key = sha(dict(profile=sha(profile), candidate=value, spec=tuple(spec), observed=True))
        saved = json.loads((p1.ROOT / 'cache/main' / (key + '.json')).read_text())
        if saved['key'] != key or saved['digest'] != sha(saved['record']):
            raise RuntimeError('damaged original cache')
        rows.append(saved['record'])
    return rows


def inspect_original(base, rows):
    profile = p1.integrity()
    for source, digest in profile['sources'].items():
        if hashlib.sha256((p1.ROOT / 'source-archive' / source).read_bytes()).hexdigest() != digest:
            raise RuntimeError('original source archive differs')
    e0 = p1.census(rows, base['program'], p1.known_positive())
    if sha({k: e0[k] for k in ('inert', 'classes', 'tracked')}) != p1.E0_SHA:
        raise RuntimeError('E0 reconstruction differs')
    plan = p1.sample(e0, p1.known_positive())
    if sha(plan) != p1.PLAN_SHA or plan != json.loads((p1.ROOT / 'singles-plan.json').read_text())['plan']:
        raise RuntimeError('single plan differs')
    singles = [json.loads((p1.ROOT / 'singles' / f'{i:03d}.json').read_text()) for i in range(200)]
    pair_plan = p1.select_pairs(singles)
    if pair_plan != json.loads((p1.ROOT / 'pairs-plan.json').read_text())['plan']:
        raise RuntimeError('pair plan differs')
    policies = {p1.Execution.digest(base): base}
    for item, row in zip(plan, singles, strict=True):
        if any(row.get(k) != v for k, v in item.items()):
            raise RuntimeError('single result escaped plan')
        value = p1.strategy(program=patch.append(base['program'], row['proposal']))
        policies[p1.Execution.digest(value)] = value
    for i, item in enumerate(pair_plan):
        row = json.loads((p1.ROOT / 'pairs' / f'{i:03d}.json').read_text())
        if any(row.get(k) != v for k, v in item.items()):
            raise RuntimeError('pair result escaped plan')
        value = p1.strategy(program=p1.pair_program(base, *(singles[j] for j in item['pair'])))
        policies[p1.Execution.digest(value)] = value
    count = 0
    for cache in sorted((p1.ROOT / 'cache').glob('*/*.json')):
        saved = json.loads(cache.read_text()); record = saved['record']
        spec = tuple(record[k] for k in ('version', 'seed', 'rep', 'budget'))
        if spec not in A or record['origin'] != 'DEVELOPMENT_A':
            raise RuntimeError('original cache contains non-development measurement')
        value = policies[record['policy_sha256']]
        key = sha(dict(profile=sha(profile), candidate=value, spec=spec, observed=True))
        if saved['key'] != key or cache.stem != key or saved['digest'] != sha(record):
            raise RuntimeError('original cache key or record digest differs')
        count += 1
        if count % 1000 == 0:
            status('INSPECTING_ORIGINAL_CACHE', checked=count)
    if count != 22160 or json.loads((p1.ROOT / 'budget.json').read_text())['scheduled_games'] != count:
        raise RuntimeError('original cache/budget count differs')
    return {'source_archive_valid': True, 'plans_reconstructed': True, 'cache_records_checked': count,
            'development_only': True}


def run():
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'process.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not (ROOT / 'profile.json').exists():
            atomic(ROOT / 'profile.json', fingerprint())
            atomic(ROOT / 'sample-plan.json', {'at': p1.now(), 'sample': list(SAMPLE),
                'reason': 'negative control 2, loss-free +1 control 31, target controls 77 and 178',
                'games': MAX_GAMES, 'runtime': 'frozen B12 Python 3.12', 'B_measured': False,
                'exam_opened': False})
        integrity()
        base = p1.base_program()
        old = original_rows(base)
        inspected = inspect_original(base, old)
        before = measure('base/A', base, A)
        replay = measure('base/replay-A', base, A, replay=True)
        if before['trace_digest'] != p1.BASE_TRACE or replay['trace_digest'] != p1.BASE_TRACE \
                or before['levels'] != 378 or behavior_digest(before['rows']) != p1.BASE_BEHAVIOR:
            raise RuntimeError('independent baseline parity failed')
        results = {}
        for index in SAMPLE:
            source = json.loads((p1.ROOT / 'singles' / f'{index:03d}.json').read_text())
            value = p1.strategy(program=patch.append(base['program'], source['proposal']))
            measured = measure(f'singles/{index:03d}', value, A)
            if measured['trace_digest'] != source['trace_sha256'] \
                    or measured['rows'] != original_rows(value) \
                    or p1.effects(before, measured) != source['effects'] \
                    or p1.passes_v3(before, measured) != source['passes_v3']:
                raise RuntimeError(f'independent candidate {index} differs')
            results[str(index)] = {'trace_sha256': measured['trace_digest'],
                'levels': measured['levels'], 'equal_to_probe1': True, 'games': len(A)}
            atomic(ROOT / 'sample-results.json', results)
        integrity()
        receipt = dict(at=p1.now(), valid=True, **fingerprint(), **inspected,
            cache_root=str((ROOT / 'cache').resolve()), baseline_reproduced=True,
            sample_results=results, games_scheduled=json.loads((ROOT / 'budget.json').read_text())['scheduled_games'],
            B_measured=False, exam_opened=False)
        atomic(ROOT / 'audit.json', receipt)
        status('DONE', valid=True, sample=list(SAMPLE))


if __name__ == '__main__':
    from seed import s6probe1_audit
    try:
        s6probe1_audit.run()
    except Exception as exc:
        s6probe1_audit.status('BLOCKED', error=type(exc).__name__, message=str(exc))
        raise
