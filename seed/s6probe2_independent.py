"""Independent replay of PROBE2's base and both V3 survivors, A only."""
import hashlib
import json
from pathlib import Path
import sys
from types import FunctionType

from seed import s6b11, s6probe1 as p1, s6probe2 as p2
from echo_arc import stale_transition as patch
from echo_arc.observe import Journal

REPO = p2.REPO
ROOT = REPO / 'lab/seed/s6probe2-independent-20261003'
LIVE = ROOT / 'journals'
EPHEMERAL = ROOT / 'ephemeral-journals'
A, WORKERS, MAX_GAMES = p2.A, 4, 320
atomic, sha, canonical, now = p2.atomic, p2.sha, p2.canonical, p2.now
SOURCES = ['seed/s6probe2_independent.py', 'docs/ECHO45-S6-PROBE2-INDEPENDENT.md']


def profile():
    return {'probe2_profile_sha256': sha(p2.integrity()),
            'probe2_result_sha256': hashlib.sha256((p2.ROOT / 'result.json').read_bytes()).hexdigest(),
            'sources': {s: hashlib.sha256((REPO / s).read_bytes()).hexdigest() for s in SOURCES},
            'configuration': {'A': A, 'survivors': [28, 33], 'workers': WORKERS,
                              'max_games': MAX_GAMES, 'B_measured': False, 'exam_opened': False}}


def integrity():
    frozen = json.loads((ROOT / 'profile.json').read_text())
    if frozen != json.loads(canonical(profile())):
        raise RuntimeError('independent audit sources or PROBE2 changed')
    return frozen


def status(stage, **fields):
    value = dict(at=now(), stage=stage, **fields)
    atomic(ROOT / 'status.json', value)
    print(canonical(value), flush=True)


reserve_games = FunctionType(s6b11.reserve_games.__code__,
    dict(s6b11.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=MAX_GAMES))
_play = FunctionType(s6b11.play_one.__code__, dict(s6b11.play_one.__globals__,
    ROOT=ROOT, LIVE=LIVE, A=A, B=[], EXAM_SEEDS=()))
play_one = FunctionType(p1.play_one.__code__, dict(p1.play_one.__globals__, __name__=__name__,
    ROOT=ROOT, LIVE=LIVE, EPHEMERAL=EPHEMERAL, _play=_play, A=A), 'play_one')
_measure = FunctionType(p1._measure.__code__, dict(p1._measure.__globals__,
    ROOT=ROOT, integrity=integrity, play_one=play_one, status=status,
    reserve_games=reserve_games, WORKERS=WORKERS, A=A), '_measure')
measure = _measure(EPHEMERAL)


def run():
    ROOT.mkdir(parents=True, exist_ok=True)
    if not (ROOT / 'profile.json').exists():
        frozen = profile()
        for source in SOURCES:
            target = ROOT / 'source-archive' / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / source).read_bytes())
        atomic(ROOT / 'profile.json', frozen)
    frozen = integrity()
    if (ROOT / 'audit.json').exists():
        return json.loads((ROOT / 'audit.json').read_text())
    journal_path = ROOT / ('decisions-' + str(__import__('os').getpid()) + '.jsonl')
    journal = Journal(journal_path)
    journal.write(kind='start', agent='PROBE2 independent replay', origin='DEVELOPMENT_A', budget=240)
    try:
        base = p1.base_program()
        policies = [('base', base, 'measurements/base/A.json')]
        for index in (28, 33):
            receipt = json.loads((p2.ROOT / f'verified/{index:04d}.json').read_text())
            policy = p2.strategy(program=patch.append(base['program'], receipt['proposal']))
            policies.append((str(index), policy, f'measurements/full/{index:04d}.json'))
        results, baseline = {}, None
        for name, policy, reference in policies:
            status('REPLAY', candidate=name)
            measured = measure(name, policy, A)
            expected = json.loads((p2.ROOT / reference).read_text())
            if measured['trace_digest'] != expected['trace_digest']:
                raise RuntimeError('independent replay differs: ' + name)
            if name == 'base':
                baseline = measured
            elif not p1.passes_v3(baseline, measured):
                raise RuntimeError('survivor does not pass unchanged V3: ' + name)
            results[name] = {'levels': measured['levels'], 'score': measured['score'],
                             'trace_sha256': measured['trace_digest'], 'games': len(A),
                             'equal_to_probe2': True}
            journal.write(kind='result', result=dict(candidate=name, **results[name]))
        receipt = dict(at=now(), valid=True, profile_sha256=sha(integrity()),
                       probe2_profile_sha256=frozen['probe2_profile_sha256'],
                       cache_root=str(ROOT / 'cache'), games=240, sample_results=results,
                       B_measured=False, exam_opened=False, model_calls=0,
                       independent_execution=True, S6_green=False)
        atomic(ROOT / 'audit.json', receipt)
        status('DONE', games=240, valid=True)
        return receipt
    except Exception as exc:
        status('BLOCKED', reason=type(exc).__name__ + ': ' + str(exc))
        raise
    finally:
        journal.close()


if __name__ == '__main__':
    run()
