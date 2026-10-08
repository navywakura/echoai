"""S6-PROBE2: directed capacity control for HOLD 0/1, selected after PROBE1.

Same base (B12 final program, 378 A levels), same B12 grammar, one proposal.
No model, no protected B, no reserved exam. A53 and the other game numbers
only choose which A games are measured; no policy input sees them.

Soundness of the screen: HOLD is consumed at one traced site
(`self.hold = self.HOLD`). If no base HOLD read of a game matches the guard,
that game's deterministic run is identical to the base run. Each candidate is
therefore screened on exactly the A games it touches; survivors and a fixed
sample are then measured on all 80 A games, which also tests the argument.
"""
from collections import Counter
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
from types import FunctionType

from seed import s6b11, s6probe1 as p1
from echo_arc import stale_transition as patch
from echo_arc.contrastive_evidence import BEHAVIOR, FEATURE_ORDER, behavior_digest
from echo_arc.contrastive_grammar import build_schema, choices
from echo_arc.feasible_grammar import matches

REPO = p1.REPO
ROOT = REPO / 'lab/seed/s6probe2-20261001'
LIVE = REPO / 'lab/observability/s6probe2-20261001'
EPHEMERAL = ROOT / 'ephemeral-journals'
A = p1.A
strategy, atomic, canonical, sha, now = p1.strategy, p1.atomic, p1.canonical, p1.sha, p1.now
WORKERS = 4
VALUES, TARGET_GAME = (0, 1), 53                    # selection only, never a policy input
REPLAY_EVERY, SOUNDNESS_POSITIONS, MAX_VERIFIED, ESTIMATE_CANDIDATES = 10, (0, 200, 400, 600, 800), 30, 5
PROBE1_RESULT_SHA = '16afe62ed26ff783f320fe65cc998103e0587683dbced0318b60b17a9102ba64'
PROBE1_AUDIT = REPO / 'lab/seed/s6probe1-20260930-audit/audit.json'
PROBE1_CONTROLS = (77, 178)                          # PROBE1 singles reproduced inside the screen
# Preregistered from the PROBE1-cached 378 rows; the probe's own base must reproduce them.
UNIVERSE, TOUCHING, SIGNATURES = 1004, 874, 126
PLAN_SHA = 'a725b39f44d9fa1257ac0d621274b7c27a1494c927e354895061c021191be66b'
MAX_GAMES = 14544
SOURCES = list(dict.fromkeys(p1.SOURCES + [
    'seed/s6probe2.py', 'tests/test_s6probe2.py', 'docs/ECHO45-S6-PROBE2-DESIGN.md']))


def config():
    return {'selection': 'directed after PROBE1: HOLD 0/1 proposals whose guard matches a base HOLD read in A53',
            'base_trace_sha256': p1.BASE_TRACE, 'base_levels': p1.BASE_LEVELS, 'A': A,
            'B': 'never measured', 'exam': 'never opened', 'model_calls': 0,
            'language': 'B12 contrastive grammar over all 80 A rows, one proposal, no exclusions',
            'values': VALUES, 'target_game': TARGET_GAME, 'universe': UNIVERSE, 'touching': TOUCHING,
            'signatures': SIGNATURES, 'plan_sha256': PLAN_SHA,
            'screen': 'games whose base HOLD reads match the guard; survivor = no level/score loss there '
                      'and >= +2 levels there',
            'verdict': 'native V3 on all 80 A games plus identical full replay',
            'replay': 'screen replay at plan index % 10 == 0; full replay for every verified survivor',
            'soundness_sample': SOUNDNESS_POSITIONS, 'max_verified_survivors': MAX_VERIFIED,
            'soundness_schedule': 'during full run, immediately after each sampled screen; not during estimate',
            'probe1_controls': PROBE1_CONTROLS, 'workers': WORKERS, 'max_games': MAX_GAMES}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def probe1_closure():
    """PROBE1 finished with its contracted result and an independent re-execution exists."""
    result = (p1.ROOT / 'result.json').read_bytes()
    audit = json.loads(PROBE1_AUDIT.read_text())
    sample = {int(i) for i in audit.get('sample_single_indices', [])}
    cache = Path(audit.get('cache_root') or str(p1.ROOT)).resolve()
    if (hashlib.sha256(result).hexdigest() != PROBE1_RESULT_SHA or audit.get('valid') is not True
            or not {2, 31, *PROBE1_CONTROLS} <= sample
            or cache.is_relative_to(p1.ROOT.resolve()) or not cache.is_dir()
            or audit.get('probe1_profile_sha256') != sha(p1.integrity())
            or audit.get('probe1_result_sha256') != PROBE1_RESULT_SHA
            or any(audit.get(k) is not True for k in ('baseline_reproduced', 'source_archive_valid',
                                                     'plans_reconstructed', 'development_only'))
            or audit.get('B_measured') is not False or audit.get('exam_opened') is not False):
        raise RuntimeError('PROBE1 result or its independent audit is missing or inconsistent')
    for index in (2, 31, *PROBE1_CONTROLS):
        checked = audit.get('sample_results', {}).get(str(index), {})
        original = json.loads((p1.ROOT / f'singles/{index:03d}.json').read_text())
        if checked.get('equal_to_probe1') is not True or checked.get('games') != len(A) \
                or checked.get('trace_sha256') != original['trace_sha256']:
            raise RuntimeError('independent sample receipt does not match PROBE1')
    return {'result_sha256': PROBE1_RESULT_SHA, 'audit_sha256': sha(audit)}


def profile():
    return {'sources': hashes(), 'configuration': config(), 'probe1_profile_sha256': sha(p1.integrity()),
            'probe1_closure': probe1_closure(), 'base': p1.base_program(),
            'runtime': s6b11.capacity.previous.runtime(), 'backend': 'cpu', 'threads': 4}


def integrity():
    value = json.loads((ROOT / 'profile.json').read_text())
    if value != json.loads(canonical(profile())):
        raise RuntimeError('PROBE2 sources, PROBE1 closure or runtime changed')
    return value


def prepare():
    if PLAN_SHA is None or MAX_GAMES is None:
        raise RuntimeError('plan and budget are not frozen yet')
    if (ROOT / 'profile.json').exists():
        return integrity()
    value = profile()
    for source in SOURCES:
        target = ROOT / 'source-archive' / source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / source).read_bytes())
    atomic(ROOT / 'profile.json', value)
    atomic(ROOT / 'prepared.json', {'at': now(), 'profile_sha256': sha(value)})
    return value


def status(stage, **fields):
    value = {'at': now(), 'stage': stage, 'condition': 'S6-PROBE2', **fields}
    atomic(ROOT / 'status.json', value)
    print(canonical(value), flush=True)


# PROBE1's custody machinery, rebound to PROBE2 directories (no second implementation).
reserve_games = FunctionType(s6b11.reserve_games.__code__,
    dict(s6b11.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=MAX_GAMES))
_play = FunctionType(s6b11.play_one.__code__, dict(s6b11.play_one.__globals__,
    ROOT=ROOT, LIVE=LIVE, A=A, B=[], EXAM_SEEDS=()))
# __name__ makes spawn workers unpickle this function from seed.s6probe2, not PROBE1's.
play_one = FunctionType(p1.play_one.__code__, dict(p1.play_one.__globals__, __name__=__name__,
    ROOT=ROOT, LIVE=LIVE, EPHEMERAL=EPHEMERAL, _play=_play, A=A), 'play_one')
_measure = FunctionType(p1._measure.__code__, dict(p1._measure.__globals__,
    ROOT=ROOT, integrity=integrity, play_one=play_one, status=status,
    reserve_games=reserve_games, WORKERS=WORKERS, A=A), '_measure')
measure_kept, measure_ephemeral = _measure(LIVE), _measure(EPHEMERAL)


# ---------------------------------------------------------------- plan ----

def hold_reads(rows):
    """Base HOLD reads per A game, with the public features seen at the read."""
    out = {}
    for g, row in enumerate(rows):
        found = [{k: e['features'][k] for k in FEATURE_ORDER}
                 for e in row['diagnostics']['consumers'] if e['parameter'] == 'HOLD']
        if any(e['value'] != patch.DEFAULTS['HOLD'] for e in row['diagnostics']['consumers']
               if e['parameter'] == 'HOLD'):
            raise RuntimeError('base HOLD read differs from the default; touch rule not derived')
        if found:
            out[g] = found
    return out


def plan(rows):
    """All legal HOLD 0/1 proposals touching A53; signature representatives first."""
    reads = hold_reads(rows)
    universe = [(value, guard) for parameter, value, guards in choices(build_schema(rows, []))
                if parameter == 'HOLD' and value in VALUES for guard in guards]
    items = []
    for value, guard in universe:
        touched = {g: [i for i, f in enumerate(fs) if matches(guard, f)] for g, fs in reads.items()}
        touched = {g: ix for g, ix in touched.items() if ix}
        if TARGET_GAME not in touched:
            continue
        proposal = {'patches': [{'set': {'HOLD': value}, 'when': guard}]}
        items.append({'proposal': proposal, 'touched_games': sorted(touched),
                      'signature': sha([value, sorted(touched.items())])})
    representative = {}
    for item in sorted(items, key=lambda x: canonical(x['proposal'])):
        representative.setdefault(item['signature'], canonical(item['proposal']))
    key = lambda x: (len(x['touched_games']), canonical(x['proposal']))
    first = sorted((x for x in items if representative[x['signature']] == canonical(x['proposal'])), key=key)
    rest = sorted((x for x in items if representative[x['signature']] != canonical(x['proposal'])), key=key)
    ordered = [dict(x, stage=1) for x in first] + [dict(x, stage=2) for x in rest]
    return {'universe': len(universe), 'touching': len(items), 'signatures': len(representative),
            'plan': [dict(x, index=i) for i, x in enumerate(ordered)]}


def budget(items):
    """Fixed games plus a reserve for verified survivors; interrupted work counts."""
    screen = sum(len(x['touched_games']) for x in items)
    replays = sum(len(x['touched_games']) for x in items if x['index'] % REPLAY_EVERY == 0)
    soundness = sum(len(A) - len(items[i]['touched_games']) for i in SOUNDNESS_POSITIONS if i < len(items))
    survivors = MAX_VERIFIED * 2 * len(A)
    return {'base': 2 * len(A), 'screen': screen, 'screen_replays': replays, 'soundness': soundness,
            'survivor_reserve': survivors, 'total': 2 * len(A) + screen + replays + soundness + survivors}


# ----------------------------------------------------------------- run ----

def specs(games):
    return [A[g] for g in games]


def behavior(row):
    return sha({k: row[k] for k in BEHAVIOR})


def screen(item, base, before):
    started = time.monotonic()
    value = strategy(program=patch.append(base['program'], item['proposal']))
    games = item['touched_games']
    label = f"screen/{item['index']:04d}"
    measured = measure_ephemeral(label, value, specs(games))
    effect = [[games[i], dl, ds, ch] for i, dl, ds, ch in
              p1.effects({'rows': [before['rows'][g] for g in games]}, measured)]
    row = dict(p1.summarize(effect), effects=effect, screen_trace_sha256=measured['trace_digest'],
               record_sha256={str(g): sha(r) for g, r in zip(games, measured['rows'])})
    row['survivor'] = row['gain_levels'] >= 2 and not row['loss_games']
    if item['index'] % REPLAY_EVERY == 0:
        repeat = measure_kept(label + '/replay', value, specs(games), replay=True)
        row['replay_ok'] = repeat['trace_digest'] == measured['trace_digest']
        if not row['replay_ok']:
            atomic(ROOT / 'failures' / (label.replace('/', '-') + '.json'), dict(item, **row))
            raise RuntimeError('PROBE2 screen replay mismatch; stop without a capacity conclusion')
    row['seconds'] = round(time.monotonic() - started, 3)
    return row


def full(item, base, before, replay):
    """All 80 A games; cached screen games are reused, the rest are measured now."""
    value = strategy(program=patch.append(base['program'], item['proposal']))
    label = f"full/{item['index']:04d}"
    measured = measure_ephemeral(label, value, A)
    effect = p1.effects(before, measured)
    untouched = [g for g in range(len(A)) if g not in item['touched_games']]
    identical = all(behavior(measured['rows'][g]) == behavior(before['rows'][g]) for g in untouched)
    row = dict(p1.summarize(effect), levels=measured['levels'], trace_sha256=measured['trace_digest'],
               effects=effect, passes_v3=p1.passes_v3(before, measured), untouched_identical=identical)
    if not identical:
        atomic(ROOT / 'failures' / (label.replace('/', '-') + '.json'), dict(item, **row))
        raise RuntimeError('an untouched A game changed: the screen argument failed; stop')
    if replay:
        repeat = measure_kept(label + '/replay', value, A, replay=True)
        row['replay_ok'] = repeat['trace_digest'] == measured['trace_digest']
        if not row['replay_ok']:
            atomic(ROOT / 'failures' / (label.replace('/', '-') + '.json'), dict(item, **row))
            raise RuntimeError('PROBE2 full replay mismatch; stop without a capacity conclusion')
    return row


def probe1_control(item, row):
    """Screen records of PROBE1 singles 77/178 must equal PROBE1's cached records."""
    p1_profile = json.loads((p1.ROOT / 'profile.json').read_text())
    value = strategy(program=patch.append(p1.base_program()['program'], item['proposal']))
    for g in item['touched_games']:
        key = sha({'profile': sha(p1_profile), 'candidate': value, 'spec': tuple(A[g]), 'observed': True})
        record = json.loads((p1.ROOT / 'cache/main' / (key + '.json')).read_text())['record']
        if sha(record) != row['record_sha256'][str(g)]:
            raise RuntimeError(f'PROBE1 control differs in A game {g}; stop')


def frozen_plan(before):
    path = ROOT / 'plan.json'
    if not path.exists():
        value = plan(before['rows'])
        if ((value['universe'], value['touching'], value['signatures']) != (UNIVERSE, TOUCHING, SIGNATURES)
                or sha(value['plan']) != PLAN_SHA):
            raise RuntimeError('PROBE2 plan differs from the preregistered plan')
        atomic(path, value)
    value = json.loads(path.read_text())
    if sha(value['plan']) != PLAN_SHA or budget(value['plan'])['total'] != MAX_GAMES:
        raise RuntimeError('saved PROBE2 plan or budget differs from the preregistered values')
    return value['plan']


def controls(items):
    found = {}
    for index in PROBE1_CONTROLS:
        proposal = canonical(json.loads((p1.ROOT / f'singles/{index:03d}.json').read_text())['proposal'])
        found[index] = next(x['index'] for x in items if canonical(x['proposal']) == proposal)
    return found


def run(limit=None):
    prepare()
    base, before = p1_base()
    items = frozen_plan(before)
    control_positions = {v: k for k, v in controls(items).items()}
    screened = []
    checks = []
    for item in items[:limit]:
        out = ROOT / 'screen' / f"{item['index']:04d}.json"
        if not out.exists():
            row = screen(item, base, before)
            if item['index'] in control_positions:
                probe1_control(item, row)
                row['probe1_control'] = control_positions[item['index']]
            atomic(out, dict(item, **row))
        saved = json.loads(out.read_text())
        if any(saved.get(k) != v for k, v in item.items()) or saved.get('replay_ok') is False:
            raise RuntimeError('saved screen differs from plan or failed its replay')
        if item['index'] in control_positions:
            probe1_control(item, saved)
        screened.append(saved)
        if limit is None and item['index'] in SOUNDNESS_POSITIONS:
            checks.append(_full_saved(item, base, before, 'soundness', replay=False))
        done = [s['seconds'] for s in screened]
        status('SCREEN', completed=len(screened), total=len(items),
               survivors=sum(s['survivor'] for s in screened),
               projected_remaining_hours=round(sum(done) / len(done) * (len(items) - len(screened)) / 3600, 2))
    if limit is not None:
        metrics = [json.loads(p.read_text()) for p in (ROOT / 'worker-metrics').glob('*.json')]
        atomic(ROOT / 'estimate.json', {'at': now(), 'candidates': len(screened),
               'seconds': [s['seconds'] for s in screened],
               'games': [len(s['touched_games']) for s in screened],
               'games_reserved': json.loads((ROOT / 'budget.json').read_text())['scheduled_games'],
               'workers': WORKERS, 'max_worker_rss_kib': max((m['max_rss_kib'] for m in metrics), default=None),
               'free_disk_bytes': shutil.disk_usage(ROOT).free, 'full_run_started': False})
        status('ESTIMATE_READY', candidates=len(screened), full_run_started=False)
        return
    missing = set(controls(items).values()) - {s['index'] for s in screened}
    if missing:
        raise RuntimeError('PROBE1 controls were not screened')
    survivors = [s for s in screened if s['survivor']]
    verified = [_full_saved(items[s['index']], base, before, 'verified', replay=True)
                for s in survivors[:MAX_VERIFIED]]
    report(items, screened, checks, survivors, verified)


def _full_saved(item, base, before, kind, replay):
    out = ROOT / kind / f"{item['index']:04d}.json"
    if not out.exists():
        atomic(out, dict(item, **full(item, base, before, replay)))
    saved = json.loads(out.read_text())
    if any(saved.get(k) != v for k, v in item.items()) or saved.get('replay_ok') is False:
        raise RuntimeError('saved full measurement differs from plan or failed its replay')
    return saved


def p1_base():
    """Base on A with replay; must equal the B12/PROBE1 378 measurement."""
    base = p1.base_program()
    a = measure_kept('base/A', base, A)
    repeat = measure_kept('base/replay-A', base, A, replay=True)
    parity = {'levels': a['levels'], 'trace_sha256': a['trace_digest'],
              'replay_trace_sha256': repeat['trace_digest'], 'behavior_sha256': behavior_digest(a['rows'])}
    valid = (a['levels'], a['trace_digest'], repeat['trace_digest'], parity['behavior_sha256']) == \
        (p1.BASE_LEVELS, p1.BASE_TRACE, p1.BASE_TRACE, p1.BASE_BEHAVIOR)
    atomic(ROOT / 'parity.json', dict(parity, valid=valid))
    if not valid:
        raise RuntimeError('base does not reproduce the B12 378 measurement')
    return base, a


def conclusion(screened, survivors, verified, total):
    passed = [v for v in verified if v['passes_v3'] and v.get('replay_ok') is True]
    lines = []
    if passed:
        lines.append(f'{len(passed)} propuesta(s) individual(es) HOLD 0/1 pasan V3 en las 80 partidas A con '
                     'replay idéntico: el lenguaje actual alcanza V3 desde 378 en A (control de capacidad, '
                     'V4 sin evaluar; no es descubrimiento autónomo ni cierre de S6).')
    if len(screened) < total or len(survivors) > len(verified):
        lines.append('Medición incompleta: '
                     f'{len(screened)}/{total} cribados, {len(verified)}/{len(survivors)} supervivientes verificados.')
    elif not passed:
        lines.append('Sin solución en esta búsqueda dirigida y con este presupuesto '
                     f'({len(screened)} propuestas HOLD 0/1 que tocan A53; {len(survivors)} supervivientes del '
                     f'cribado; {len(verified)} verificados en A completo). No demuestra que el lenguaje esté agotado.')
    return {'passes': len(passed), 'text': lines}


def report(items, screened, checks, survivors, verified):
    by_stage = lambda rows: dict(Counter(str(r['stage']) for r in rows))
    summary = {'at': now(), 'profile_sha256': sha(integrity()), 'model_calls': 0, 'B_measured': False,
               'exam_opened': False, 'universe': UNIVERSE, 'touching': TOUCHING, 'signatures': SIGNATURES,
               'screened': len(screened), 'screened_by_stage': by_stage(screened),
               'screen_gain_histogram': dict(Counter(str(s['gain_levels']) for s in screened)),
               'screen_with_A53_gain': sum(TARGET_GAME in s['level_gain_games'] for s in screened),
               'screen_A53_gain_without_any_screen_loss': sum(
                   TARGET_GAME in s['level_gain_games'] and not s['loss_games'] for s in screened),
               'screen_loss_games': dict(Counter(str(g) for s in screened for g in s['loss_games'])),
               'survivors': [s['index'] for s in survivors], 'survivors_by_stage': by_stage(survivors),
               'verified': [{k: v[k] for k in ('index', 'levels', 'gain_levels', 'loss_games', 'passes_v3',
                                               'replay_ok')} for v in verified],
               'soundness_checks': [{k: c[k] for k in ('index', 'untouched_identical', 'levels')} for c in checks],
               'screen_replays': sum('replay_ok' in s for s in screened),
               'conclusion': conclusion(screened, survivors, verified, len(items)),
               'budget': json.loads((ROOT / 'budget.json').read_text())}
    atomic(ROOT / 'result.json', summary)
    lines = ['# S6-PROBE2 · resultados', '', 'Búsqueda dirigida tras PROBE1. Control de capacidad: 0 llamadas al '
             'modelo; B y examen sin tocar. Sus soluciones no se atribuyen a ECHO ni se muestran a ningún modelo.', '']
    lines += summary['conclusion']['text'] + ['', '```json', json.dumps(summary, indent=1, sort_keys=True),
                                               '```', '', '[Contrato](ECHO45-S6-PROBE2-DESIGN.md).', '']
    (REPO / 'docs/ECHO45-S6-PROBE2-RESULTS.md').write_text('\n'.join(lines))
    status('DONE', **summary['conclusion'])


def main(args):
    if args not in (['prepare'], ['estimate'], ['run']):
        raise SystemExit('use prepare, estimate, run')
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'process.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if args == ['prepare']:
                prepare()
            elif args == ['estimate']:
                run(limit=ESTIMATE_CANDIDATES)
            else:
                run()
        except Exception as exc:
            status('BLOCKED', error=type(exc).__name__, message=str(exc))
            raise


if __name__ == '__main__':
    from seed import s6probe2
    s6probe2.main(sys.argv[1:])
