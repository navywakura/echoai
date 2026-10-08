"""S6-PROBE1: capacity control from the audited B12 program (378 A levels).

No model, no protected B, no reserved exam. Measures whether the unchanged
B12 language contains a single proposal, or a pair, that passes V3 on A.
Solutions found here are a human-run capacity control, never autonomous
ECHO discoveries, and are never shown to a model.
"""
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import shutil
import sys
import time
from types import FunctionType

import numpy as np

from seed import s6b11, s6b12 as frozen, s6b12_recovery1 as recovery
from seed.game_selfimprove_b5 import no_regressions
from echo_arc import stale_transition as patch
from echo_arc.contrastive_evidence import FEATURE_ORDER, behavior_digest
from echo_arc.contrastive_grammar import build_schema, choices, validate_answer

REPO = frozen.REPO
ROOT = REPO / 'lab/seed/s6probe1-20260930'
LIVE = REPO / 'lab/observability/s6probe1-20260930'
EPHEMERAL = ROOT / 'ephemeral-journals'
A = frozen.A
Execution, strategy, atomic, canonical, sha, now = (frozen.Execution, frozen.strategy, frozen.atomic,
                                                    frozen.canonical, frozen.sha, frozen.now)
WORKERS, MAX_GAMES = 4, 26000
SINGLES, MIN_PER_OPERATOR, PAIRS, TIER1_PAIRS = 200, 30, 50, 25
SAMPLE_SEED, PAIR_SEED, AUDIT_REPLAY_EVERY, ESTIMATE_CANDIDATES = 20260930, 20261001, 10, 5
# B12 measured the 378 program on A before every post-acceptance proposal.
BASE_TRACE = '4458a4c2e5f4d8ac6c46547fcbc62785e0aca93bd0bdecb6d23d7456d63c2d2c'
BASE_BEHAVIOR = '4cf4148e803f9ce249f443e2bdb730b6bac9e326550dbfea7701f3d40ead93f1'
BASE_LEVELS = 378
# Preregistered from the B12-cached 378 rows; the probe's own base must reproduce them.
E0_SHA = '3b67ba863f12df5e397576fff7d83e4e329ebe2d038cc62478a24efdd72d7940'
PLAN_SHA = 'a0eb472cec52033cea1197f5581e2a1862ea3821de9c2684bf80752b4cf34fcf'
PARAMETERS = ('REVALIDATE_NOOP', 'HOLD', 'COOLDOWN_CAP')
SOURCES = list(dict.fromkeys(frozen.SOURCES + list(recovery.SOURCES) + [
    'seed/s6probe1.py', 'tests/test_s6probe1.py', 'docs/ECHO45-S6-PROBE1-DESIGN.md']))


def config():
    return {'base': 'B12 campaign final program, identical in ECHO and FIJO', 'base_levels': BASE_LEVELS,
            'base_trace_sha256': BASE_TRACE, 'A': A, 'B': 'never measured', 'exam': 'never opened',
            'model_calls': 0, 'language': 'B12 contrastive grammar over all 80 A rows, no exclusions',
            'singles': SINGLES, 'min_per_operator': MIN_PER_OPERATOR, 'pairs': PAIRS,
            'tier1_pairs': TIER1_PAIRS, 'sample_seed': SAMPLE_SEED, 'pair_seed': PAIR_SEED,
            'verdict': 'native V3: A levels >= base+2 and no individual A level/score loss (1e-10)',
            'replay': 'every V3 pass, plus every candidate with index % 10 == 0',
            'journals': 'kept for base and replays; ephemeral for first measurements',
            'replay_failure': 'stop and preserve evidence; no negative capacity conclusion',
            'workers': WORKERS, 'max_games': MAX_GAMES}


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def b12_closure():
    closed = json.loads((frozen.ROOT / 'closed.json').read_text())
    audit = json.loads((frozen.ROOT / 'campaign-audit.json').read_text())
    r1 = json.loads((frozen.ROOT / 'runtime-recovery1/campaign-audit.json').read_text())
    campaign_bytes = (frozen.ROOT / 'campaign.json').read_bytes()
    campaign = json.loads(campaign_bytes)
    original_profile, r1_profile = frozen.integrity(), recovery.integrity()
    if (closed.get('result') != 'CAMPAIGN_NO_PROMOTION' or closed.get('s6_green') is not False
            or closed.get('exam_opened') is not False or (frozen.ROOT / 'exam/opened.json').exists()
            or audit.get('valid') is not True or r1.get('valid') is not True
            or campaign.get('promote') is not False
            or audit.get('profile_sha256') != sha(original_profile)
            or campaign.get('profile_sha256') != sha(original_profile)
            or r1_profile.get('original_profile_sha256') != sha(original_profile)
            or closed.get('recovery_profile_sha256') != sha(r1_profile)
            or r1.get('profile_sha256') != sha(r1_profile)
            or r1.get('original_audit_sha256') != sha(audit)
            or r1.get('campaign_sha256') != hashlib.sha256(campaign_bytes).hexdigest()):
        raise RuntimeError('B12/R1 closure, provenance or unopened exam checks failed')
    return {'closed_sha256': sha(closed), 'audit_sha256': sha(audit),
            'recovery_audit_sha256': sha(r1), 'campaign_sha256': r1['campaign_sha256'],
            'result': closed['result']}


def base_program():
    finals = json.loads((frozen.ROOT / 'campaign.json').read_text())['finals']
    programs = {canonical(Execution.validate(r['strategy'])) for r in finals}
    if len(programs) != 1:
        raise RuntimeError('ECHO and FIJO finals differ; base is ambiguous')
    return Execution.validate(json.loads(programs.pop()))


def profile():
    return {'sources': hashes(), 'configuration': config(), 'b12_profile_sha256': sha(frozen.integrity()),
            'b12_closure': b12_closure(), 'base': base_program(),
            'runtime': s6b11.capacity.previous.runtime(), 'backend': 'cpu', 'threads': 4}


def integrity():
    value = json.loads((ROOT / 'profile.json').read_text())
    if value != json.loads(canonical(profile())):
        raise RuntimeError('PROBE1 sources, B12 closure or runtime changed')
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
    atomic(ROOT / 'prepared.json', {'at': now(), 'profile_sha256': sha(value)})
    return value


def status(stage, **fields):
    value = {'at': now(), 'stage': stage, 'condition': 'S6-PROBE1', **fields}
    atomic(ROOT / 'status.json', value)
    print(canonical(value), flush=True)


reserve_games = FunctionType(s6b11.reserve_games.__code__,
    dict(s6b11.reserve_games.__globals__, ROOT=ROOT, MAX_GAMES=MAX_GAMES))
# B=[] and no exam seeds: the frozen play_one then accepts development A only.
_play = FunctionType(s6b11.play_one.__code__, dict(s6b11.play_one.__globals__,
    ROOT=ROOT, LIVE=LIVE, A=A, B=[], EXAM_SEEDS=()))


def play_one(item):
    value, spec, directory = item
    if tuple(spec) not in A:
        raise ValueError('PROBE1 measures development A only')
    ephemeral = None
    if directory:
        path = Path(directory).resolve()
        allowed = [root.resolve() for root in (EPHEMERAL, LIVE)]
        if not any(path != root and path.is_relative_to(root) for root in allowed):
            raise ValueError('journal path outside PROBE1 observer directories')
        if path.is_relative_to(allowed[0]):
            ephemeral = path
    started = time.monotonic()
    row = _play(item)  # Preserve logs if execution fails.
    if ephemeral is not None:
        # Commit the result before removing its detailed journal. The parent
        # also writes this same cache entry; a crash cannot lose both copies.
        profile_value = json.loads((ROOT / 'profile.json').read_text())
        key = sha({'profile': sha(profile_value), 'candidate': value, 'spec': tuple(spec), 'observed': True})
        expected = (EPHEMERAL / 'main' / Execution.digest(value) / key).resolve()
        if ephemeral != expected:
            raise ValueError('unexpected ephemeral cache directory; journal preserved')
        atomic(ROOT / 'cache/main' / (key + '.json'), {'key': key, 'digest': sha(row), 'record': row})
        shutil.rmtree(ephemeral)
    metric_key = sha({'candidate': value, 'spec': tuple(spec), 'directory': directory})
    atomic(ROOT / 'worker-metrics' / (metric_key + '.json'),
           {'pid': os.getpid(), 'seconds': time.monotonic() - started,
            'max_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'ephemeral_removed': ephemeral is not None})
    return row


def _measure(live):
    native = FunctionType(s6b11.measure.__code__, dict(s6b11.measure.__globals__,
        ROOT=ROOT, LIVE=live, integrity=integrity, play_one=play_one, status=status,
        reserve_games=reserve_games, WORKERS=WORKERS), 'measure', s6b11.measure.__defaults__)
    def measured(label, value, specs, observed=True, replay=False):
        if any(tuple(spec) not in A for spec in specs):
            raise ValueError('PROBE1 measurements and cache reads are development A only')
        return native(label, value, specs, observed=observed, replay=replay)
    return measured


measure_kept, measure_ephemeral = _measure(LIVE), _measure(EPHEMERAL)


def passes_v3(before, after):
    """Native V3 condition from game_selfimprove_b5.verify, without V4."""
    return after['levels'] >= before['levels'] + 2 and no_regressions(before, after)


def effects(before, after):
    """Per-game level delta, score sign and action change, development A only."""
    out = []
    for i, (b, a) in enumerate(zip(before['rows'], after['rows'], strict=True)):
        dl = a['levels_completed'] - b['levels_completed']
        ds = 0 if abs(a['score'] - b['score']) <= 1e-10 else (1 if a['score'] > b['score'] else -1)
        if dl or ds or a['actions'] != b['actions']:
            out.append([i, dl, ds, int(a['actions'] != b['actions'])])
    return out


def summarize(effect):
    return {'gain_levels': sum(dl for _, dl, _, _ in effect),
            'level_gain_games': [i for i, dl, _, _ in effect if dl > 0],
            'loss_games': [i for i, dl, ds, _ in effect if dl < 0 or ds < 0],
            'changed_games': [i for i, _, _, ch in effect if ch]}


# ---------------------------------------------------------------- E0 ----

def decisions(rows, program):
    """Recorded decision features; checks them against the actor's patch_hits."""
    features, noop = [], []
    for g, row in enumerate(rows):
        hits = [0] * len(program['patches'])
        for step in row['diagnostics']['trajectory']['steps']:
            if step is None:
                continue
            f = dict(zip(FEATURE_ORDER, step['f'], strict=True))
            for i in patch.settings(program, f)[1]:
                hits[i] += 1
            features.append(step['f'])
            noop.append(not step['outcome'][0])
        if program['patches'] and hits != row['patch_hits']:
            raise RuntimeError(f'recorded features do not reproduce patch_hits in A game {g}')
    hold = {tuple(e['features'][k] for k in FEATURE_ORDER)
            for row in rows for e in row['diagnostics']['consumers'] if e['parameter'] == 'HOLD'}
    F = np.array(features, dtype=np.int64)
    return {'F': F, 'noop': np.array(noop, bool),
            'hold_read': np.array([tuple(x) in hold for x in F.tolist()], bool)}


def guard_mask(F, guard):
    col = {k: i for i, k in enumerate(FEATURE_ORDER)}
    mask = np.ones(len(F), bool)
    for key, (op, value) in guard.items():
        c = F[:, col[key]]
        mask &= (c == value) if op == 'eq' else (c >= value) if op == 'ge' else (c <= value)
    return mask


def changed_mask(D, program, parameter, value, guard_m):
    """Sound over-approximation of decisions whose consumed value changes.

    Appended last, the candidate wins wherever its guard matches. If this mask
    is empty the deterministic run is identical to the base run:
    REVALIDATE_NOOP is only consumed on no-change steps (base values 0/1 keep
    the evidence empty), HOLD only at its single traced read site, and
    COOLDOWN_CAP only when it lowers the remaining wait (100 is clipped).
    """
    F = D['F']
    if parameter == 'REVALIDATE_NOOP':
        current = np.zeros(len(F), np.int64)
        for item in program['patches']:
            if 'REVALIDATE_NOOP' in item['set']:
                current[guard_mask(F, item['when'])] = item['set']['REVALIDATE_NOOP']
        if current.max() > 1:
            raise RuntimeError('base REVALIDATE_NOOP above 1 breaks the empty-evidence argument')
        return guard_m & (current != value) & D['noop']
    if any(parameter in item['set'] for item in program['patches']):
        raise RuntimeError('base already sets ' + parameter + '; E0 rule not derived for that case')
    if parameter == 'HOLD':
        return guard_m & D['hold_read'] if value != patch.DEFAULTS['HOLD'] else np.zeros(len(F), bool)
    remaining = F[:, FEATURE_ORDER.index('hold_remaining')]
    return guard_m & ((remaining > value) | (remaining == 100))


def census(rows, program, track=()):
    """Grammar candidates grouped by (parameter, value, changed decisions)."""
    D = decisions(rows, program)
    allowed = choices(build_schema(rows, []))
    masks, classes, inert, tracked = {}, {}, [], {t: 'ABSENT' for t in track}
    for parameter, value, guards in allowed:
        for guard in guards:
            key = canonical(guard)
            if key not in masks:
                masks[key] = guard_mask(D['F'], guard)
            changed = changed_mask(D, program, parameter, value, masks[key])
            proposal = {'patches': [{'set': {parameter: value}, 'when': guard}]}
            text = canonical(proposal)
            if text in tracked:
                tracked[text] = None
            if not changed.any():
                inert.append(text)
                continue
            signature = hashlib.sha256(canonical([parameter, value]).encode() +
                                       np.packbits(changed).tobytes()).hexdigest()
            entry = classes.setdefault(signature, {'parameter': parameter, 'value': value,
                                                   'decisions': int(changed.sum()), 'members': 0,
                                                   'representative': None})
            entry['members'] += 1
            if text in tracked:
                tracked[text] = signature
            if entry['representative'] is None or text < entry['representative']:
                entry['representative'] = text
    return {'decisions': len(D['F']), 'candidates': sum(len(g) for _, _, g in allowed),
            'inert': sorted(inert), 'classes': classes, 'tracked': tracked,
            'classes_by_operator': dict(Counter(c['parameter'] for c in classes.values()))}


def b12_soundness(result):
    """Every B12 post-acceptance proposal predicted inert must have changed no action."""
    inert, table, violations = set(result['inert']), Counter(), []
    for r in range(6):
        for v in json.loads((frozen.ROOT / f'campaign/round-{r}.json').read_text())['verdicts']:
            if v['verdict'] == 'accepted' or not v.get('development'):
                continue
            predicted = canonical(v['proposal']) not in inert
            changed = v['development']['changed_games'] > 0
            table[canonical([predicted, changed])] += 1
            if not predicted and changed:
                violations.append([v['arm'], v['id']])
    return {'predicted_effect_vs_measured_change': dict(table), 'violations': violations}


# ------------------------------------------------------------ sampling ----

def known_positive():
    """Distinct B12 proposals rejected with positive A gain from the 378 base."""
    found = []
    for r in range(6):
        for v in json.loads((frozen.ROOT / f'campaign/round-{r}.json').read_text())['verdicts']:
            if v['verdict'] != 'accepted' and v.get('A', {}).get('gain', 0) > 0:
                found.append(canonical(patch.validate(v['proposal'])))
    return sorted(set(found))


def allocate(counts, total, minimum):
    """Proportional to classes, floor `minimum` (capped by availability), largest remainder."""
    fixed, free = {}, dict(counts)
    while True:
        budget = total - sum(fixed.values())
        pool = sum(free.values())
        low = {k: min(n, minimum) for k, n in free.items() if budget * n / pool < min(n, minimum)}
        if not low:
            break
        fixed.update(low)
        free = {k: n for k, n in free.items() if k not in low}
    exact = {k: budget * n / pool for k, n in free.items()}
    share = {k: min(free[k], int(v)) for k, v in exact.items()}
    left = budget - sum(share.values())
    for k in sorted(exact, key=lambda k: (-(exact[k] - int(exact[k])), k)):
        if left and share[k] < free[k]:
            share[k] += 1
            left -= 1
    return dict(fixed, **share)


def sample(result, known):
    classes = result['classes']
    if any(result['tracked'].get(t) in (None, 'ABSENT') for t in known):
        raise RuntimeError('a known positive B12 proposal is inert or outside the grammar')
    known_classes = {result['tracked'][t] for t in known}
    rng = random.Random(SAMPLE_SEED)
    by_operator = {p: sorted(s for s, c in classes.items() if c['parameter'] == p and s not in known_classes)
                   for p in PARAMETERS}
    quota = allocate({p: len(v) for p, v in by_operator.items()}, SINGLES - len(known), MIN_PER_OPERATOR)
    chosen = [{'stratum': 'B12_POSITIVE', 'class': None, 'proposal': json.loads(t)} for t in known]
    for p in PARAMETERS:
        for signature in sorted(rng.sample(by_operator[p], quota[p])):
            chosen.append({'stratum': p, 'class': signature,
                           'proposal': json.loads(classes[signature]['representative'])})
    rng.shuffle(chosen)  # early timing and early results are not operator-ordered
    return [dict(item, index=i) for i, item in enumerate(chosen)]


# --------------------------------------------------------------- pairs ----

def select_pairs(singles):
    """Pre-registered rule over individual A effects only.

    Tier 1: changed games disjoint, ranked by additive level prediction; one
    member may have zero individual gain. Tier 2: different operators that
    touch a common game (possible interaction), zero-gain members allowed,
    seeded uniform draw. Each pair is measured as base + both patches.
    """
    pool = [s for s in singles if s['changed_games'] and s.get('replay_ok', True)]
    tier1, tier2 = [], []
    for i, x in enumerate(pool):
        for y in pool[i + 1:]:
            if canonical(x['proposal']) == canonical(y['proposal']):
                continue
            cx, cy = set(x['changed_games']), set(y['changed_games'])
            key = (x['index'], y['index'])
            if not cx & cy:
                predicted = x['gain_levels'] + y['gain_levels']
                if predicted >= 1:
                    losses = len(set(x['loss_games']) | set(y['loss_games']))
                    tier1.append((-predicted, losses, key))
            elif _operator(x) != _operator(y):
                tier2.append(key)
    tier1 = [key for _, _, key in sorted(tier1)][:TIER1_PAIRS]
    rng = random.Random(PAIR_SEED)
    rest = sorted(set(tier2) - set(tier1))
    tier2 = sorted(rng.sample(rest, min(len(rest), PAIRS - len(tier1))))
    return [{'tier': 1, 'pair': list(k)} for k in tier1] + [{'tier': 2, 'pair': list(k)} for k in tier2]


def _operator(single):
    return next(iter(single['proposal']['patches'][0]['set']))


def pair_program(base, x, y):
    first, second = sorted([x['proposal'], y['proposal']], key=canonical)
    return patch.append(patch.append(base['program'], first), second)


# ----------------------------------------------------------------- run ----

def measure_base():
    base = base_program()
    a = measure_kept('base/A', base, A)
    repeat = measure_kept('base/replay-A', base, A, replay=True)
    parity = {'levels': a['levels'], 'trace_sha256': a['trace_digest'],
              'replay_trace_sha256': repeat['trace_digest'], 'behavior_sha256': behavior_digest(a['rows'])}
    if (a['levels'], a['trace_digest'], repeat['trace_digest'], parity['behavior_sha256']) != \
            (BASE_LEVELS, BASE_TRACE, BASE_TRACE, BASE_BEHAVIOR):
        atomic(ROOT / 'parity.json', dict(parity, valid=False))
        raise RuntimeError('base does not reproduce the B12 378 measurement')
    atomic(ROOT / 'parity.json', dict(parity, valid=True))
    return base, a


def evaluate(label, value, before, replay):
    started = time.monotonic()
    a = measure_ephemeral(label + '/A', value, A)
    effect = effects(before, a)
    row = dict(summarize(effect), levels=a['levels'], trace_sha256=a['trace_digest'],
               effects=effect, passes_v3=passes_v3(before, a), determinism='not_checked')
    if row['passes_v3'] or replay:
        repeat = measure_kept(label + '/replay-A', value, A, replay=True)
        row['replay_ok'] = repeat['trace_digest'] == a['trace_digest']
        row['determinism'] = 'reproduced' if row['replay_ok'] else 'failed'
        if not row['replay_ok']:
            atomic(ROOT / 'failures' / (label + '.json'),
                   dict(row, candidate=value, replay_trace_sha256=repeat['trace_digest']))
            raise RuntimeError('PROBE1 replay mismatch; stop before drawing capacity conclusions')
    row['seconds'] = round(time.monotonic() - started, 3)
    return row


def run(limit=None):
    prepare()
    base, before = measure_base()
    path = ROOT / 'e0.json'
    if not path.exists():
        result = census(before['rows'], base['program'], known_positive())
        result['b12_soundness'] = b12_soundness(result)
        if result['b12_soundness']['violations']:
            raise RuntimeError('E0 inertness prediction contradicted by B12 measurements')
        if sha({k: result[k] for k in ('inert', 'classes', 'tracked')}) != E0_SHA:
            raise RuntimeError('E0 differs from the preregistered census')
        atomic(path, result)
    result = json.loads(path.read_text())
    if sha({k: result[k] for k in ('inert', 'classes', 'tracked')}) != E0_SHA:
        raise RuntimeError('saved E0 differs from the preregistered census')
    path = ROOT / 'singles-plan.json'
    if not path.exists():
        plan = sample(result, known_positive())
        if sha(plan) != PLAN_SHA:
            raise RuntimeError('single-candidate plan differs from the preregistered plan')
        atomic(path, {'known_positive': known_positive(), 'plan': plan})
    plan = json.loads(path.read_text())['plan']
    if sha(plan) != PLAN_SHA:
        raise RuntimeError('saved single-candidate plan differs from the preregistered plan')
    singles = []
    for item in plan[:limit]:
        out = ROOT / 'singles' / f"{item['index']:03d}.json"
        if not out.exists():
            value = strategy(program=patch.append(base['program'], item['proposal']))
            row = evaluate(f"singles/{item['index']:03d}", value, before,
                           replay=item['index'] % AUDIT_REPLAY_EVERY == 0)
            atomic(out, dict(item, **row))
        saved = json.loads(out.read_text())
        if any(saved.get(k) != v for k, v in item.items()) or saved.get('replay_ok') is False:
            raise RuntimeError('saved candidate differs from plan or failed its replay')
        singles.append(saved)
        done = [s['seconds'] for s in singles]
        status('SINGLES', completed=len(singles), total=len(plan),
               mean_seconds=round(sum(done) / len(done), 1),
               projected_remaining_hours=round(sum(done) / len(done) * (len(plan) - len(singles)) / 3600, 2))
    if limit is not None:
        metrics = [json.loads(p.read_text()) for p in (ROOT / 'worker-metrics').glob('*.json')]
        atomic(ROOT / 'estimate.json', {'at': now(), 'candidates': len(singles),
               'seconds': [s['seconds'] for s in singles], 'games_reserved':
               json.loads((ROOT / 'budget.json').read_text())['scheduled_games'],
               'workers': WORKERS, 'max_worker_rss_kib': max((m['max_rss_kib'] for m in metrics), default=None),
               'free_disk_bytes': shutil.disk_usage(ROOT).free,
               'parity_valid': json.loads((ROOT / 'parity.json').read_text())['valid'],
               'full_run_started': False})
        status('ESTIMATE_READY', candidates=len(singles), full_run_started=False)
        return
    path = ROOT / 'pairs-plan.json'
    if not path.exists():
        atomic(path, {'plan': select_pairs(singles)})
    pair_plan = json.loads(path.read_text())['plan']
    if pair_plan != select_pairs(singles):
        raise RuntimeError('saved pair plan differs from the preregistered selection rule')
    by_index = {s['index']: s for s in singles}
    pairs = []
    for n, item in enumerate(pair_plan):
        out = ROOT / 'pairs' / f'{n:03d}.json'
        if not out.exists():
            x, y = (by_index[i] for i in item['pair'])
            value = strategy(program=pair_program(base, x, y))
            atomic(out, dict(item, **evaluate(f'pairs/{n:03d}', value, before,
                                              replay=n % AUDIT_REPLAY_EVERY == 0)))
        saved = json.loads(out.read_text())
        if any(saved.get(k) != v for k, v in item.items()) or saved.get('replay_ok') is False:
            raise RuntimeError('saved pair differs from plan or failed its replay')
        pairs.append(saved)
        status('PAIRS', completed=len(pairs))
    report(result, singles, pairs)


def conclusion(singles, pairs):
    """Wording fixed in the contract; a pass needs V3 and an equal replay."""
    ok = lambda r: r['passes_v3'] and r.get('replay_ok') is True
    single, pair = sum(map(ok, singles)), sum(map(ok, pairs))
    lines = []
    if single:
        lines.append(f'{single} parche(s) individual(es) pasan V3 con replay idéntico: existe al menos '
                     'una solución individual desde 378 (control de capacidad, no descubrimiento autónomo).')
    if pair:
        lines.append(f'{pair} par(es) pasan V3 con replay idéntico: justifica investigar composición. '
                     'No demuestra que ningún parche individual pueda funcionar.')
    if not single and not pair:
        lines.append(f'No encontramos solución con este presupuesto ({len(singles)} individuales, '
                     f'{len(pairs)} pares). No demuestra que el lenguaje esté agotado.')
    return {'single_passes': single, 'pair_passes': pair, 'text': lines}


def report(result, singles, pairs):
    summary = {'at': now(), 'profile_sha256': sha(integrity()), 'model_calls': 0,
               'B_measured': False, 'exam_opened': False,
               'e0': {k: result[k] for k in ('decisions', 'candidates', 'classes_by_operator')},
               'e0_inert': len(result['inert']), 'b12_soundness': result['b12_soundness'],
               'singles': len(singles), 'pairs': len(pairs),
               'gain_histogram_singles': dict(Counter(str(s['gain_levels']) for s in singles)),
               'sample_counts_by_stratum': dict(Counter(s['stratum'] for s in singles)),
               'passes_by_stratum': dict(Counter(s['stratum'] for s in singles
                                                if s['passes_v3'] and s.get('replay_ok') is True)),
               'replay_failures': [s['index'] for s in singles if s.get('replay_ok') is False],
               'conclusion': conclusion(singles, pairs),
               'budget': json.loads((ROOT / 'budget.json').read_text())}
    atomic(ROOT / 'result.json', summary)
    lines = ['# S6-PROBE1 · resultados', '', 'Control de capacidad. 0 llamadas al modelo; B y examen sin tocar.',
             'Sus soluciones no se atribuyen a ECHO ni se muestran a ningún modelo.', '']
    lines += summary['conclusion']['text'] + ['', '```json', json.dumps(summary, indent=1, sort_keys=True),
                                               '```', '', '[Contrato](ECHO45-S6-PROBE1-DESIGN.md).', '']
    (REPO / 'docs/ECHO45-S6-PROBE1-RESULTS.md').write_text('\n'.join(lines))
    status('DONE', **summary['conclusion'])


def wait_estimate():
    """Durable local queue: no games until both B12 audits and closure exist."""
    queued = {'sources': hashes(), 'configuration': config()}
    path = ROOT / 'queued-estimate.json'
    if path.exists() and json.loads(path.read_text())['frozen'] != queued:
        raise RuntimeError('queued estimate changed; reconcile its manifest before restarting')
    atomic(path, {'at': now(), 'frozen': queued, 'action': 'estimate only; never full run'})
    while not (frozen.ROOT / 'closed.json').exists():
        if queued != {'sources': hashes(), 'configuration': config()}:
            raise RuntimeError('PROBE1 changed while queued; no measurements started')
        supervisor_path = frozen.ROOT / 'supervisor.json'
        if supervisor_path.exists():
            supervisor = json.loads(supervisor_path.read_text())
            if supervisor.get('state') == 'FINISHED':
                raise RuntimeError('B12 stopped without audited closure; no measurements started')
        status('WAITING_B12_AUDIT', games_started=False)
        time.sleep(30)
    if queued != {'sources': hashes(), 'configuration': config()}:
        raise RuntimeError('PROBE1 changed while queued; no measurements started')
    b12_closure()  # Includes independent R1 audit and provenance, not just a stopped service.
    run(limit=ESTIMATE_CANDIDATES)


def main(args):
    if args not in (['prepare'], ['estimate'], ['run'], ['wait-estimate']):
        raise SystemExit('use prepare, estimate, run, wait-estimate')
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / 'process.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if args == ['prepare']:
                prepare()
            elif args == ['estimate']:
                run(limit=ESTIMATE_CANDIDATES)
            elif args == ['wait-estimate']:
                wait_estimate()
            else:
                run()
        except Exception as exc:
            status('BLOCKED', error=type(exc).__name__, message=str(exc))
            raise


if __name__ == '__main__':
    from seed import s6probe1
    s6probe1.main(sys.argv[1:])
