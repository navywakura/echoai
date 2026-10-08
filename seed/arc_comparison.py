"""Prepare an auditable, budget-matched follow-up without reopening old exams.

`prepare` reads hashes and already published receipts, not evaluation labels.
Only a fully closed, green S6-B11 can supply the ARC3 candidate. Grid arms
remain explicit aliases until a separate grid-solver experiment is registered.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

from seed.final_eval import digest, solver_input, judge

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'lab/final/echo45-comparison-prep-20260929/v2'
HISTORICAL = REPO / 'lab/final/echo45-20260928'
S6 = REPO / 'lab/seed/s6b11-20260929'
ARC_PYTHON = REPO / 'lab/arc3/ARC-AGI-3-Agents/.venv/bin/python'
PROTECTED = (
    'lab/seed/s6b11-20260929/profile.json',
    'lab/seed/s6b11-20260929/transport-recovery/profile.json',
    'lab/seed/s6b11-20260929/transport-recovery2/profile.json',
    'lab/final/echo45-20260928/profile.json',
    'lab/final/echo45-20260928/audit-recovery/profile.json',
    'lab/seed/village3-receipts-20260929/profile.json',
)
SOURCES = ('seed/arc_comparison.py', 'seed/arc_capabilities.py',
           'tests/test_arc_comparison.py', 'tests/test_arc_capabilities.py',
           'seed/final_eval.py', 'seed/final_arc.py', 'seed/refinement.py',
           'seed/learn.py', 'seed/dsl.py', 'seed/sandbox.py', 'observe.py',
           'docs/ECHO45-ARC-COMPARISON-DESIGN.md')
BUDGET = {'grid_expansions': 400, 'grid_depth': 4, 'grid_attempts': 1,
          'arc_decisions': 2000, 'arc_environment_seed': 0, 'rep': 0,
          'wall_clock_deadline': None, 'model_calls': 0}


def require(value, message):
    if not value:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text())


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    with tmp.open('w') as stream:
        stream.write(json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def freeze_guard(repo=REPO, profiles=PROTECTED):
    """Verify existing manifests; never update or refreeze their sources."""
    files, manifests = {}, {}
    for name in profiles:
        path = repo / name
        manifests[name] = file_sha(path)
        for source, expected in read(path)['sources'].items():
            require((repo / source).is_file(), 'missing protected source: ' + source)
            actual = file_sha(repo / source)
            require(actual == expected, 'protected source changed: ' + source)
            require(source not in files or files[source] == actual, 'incompatible frozen versions')
            files[source] = actual
    return {'profiles': manifests, 'sources': files}


def delta(before, after, denominator):
    require(type(denominator) is int and denominator > 0, 'positive denominator required')
    require(all(type(n) is int and 0 <= n <= denominator for n in (before, after)), 'invalid counts')
    return {'before': before, 'after': after, 'of': denominator, 'absolute': after - before,
            'before_percent': 100 * before / denominator, 'after_percent': 100 * after / denominator,
            'percentage_points': 100 * (after - before) / denominator,
            'relative_percent': None if before == 0 else 100 * (after - before) / before}


def index_rows(rows, key):
    indexed = {row[key]: row for row in rows}
    require(len(indexed) == len(rows), 'duplicate case identity')
    return indexed


def compare_grid_rows(before, after, expected_ids, capability_tags=None):
    left, right = index_rows(before, 'task'), index_rows(after, 'task')
    expected = set(expected_ids)
    require(len(expected) == len(expected_ids) and set(left) == set(right) == expected,
            'incomplete or mismatched grid cohort')
    tags = capability_tags or {tid: ['unclassified'] for tid in expected}
    require(set(tags) == expected and all(tags[t] for t in expected), 'incomplete capability annotations')
    for tid in expected:
        a, b = left[tid], right[tid]
        require(a['public_sha256'] == b['public_sha256'], 'different public task')
        for row in (a, b):
            require(row['budget'] == BUDGET['grid_expansions'] and type(row['correct']) is bool, 'invalid grid receipt')
            result = row['result']
            require(type(result['expansions']) is int and 0 <= result['expansions'] <= row['budget'], 'grid budget exceeded')
            require(result['test_ok'] is None, 'test labels reached the solver')
    groups = sorted({tag for values in tags.values() for tag in values})
    by_capability = {}
    for tag in groups:
        ids = [tid for tid in sorted(expected) if tag in tags[tid]]
        by_capability[tag] = delta(sum(left[t]['correct'] for t in ids), sum(right[t]['correct'] for t in ids), len(ids))
    return {'overall': delta(sum(r['correct'] for r in before), sum(r['correct'] for r in after), len(expected)),
            'gained': sorted(t for t in expected if right[t]['correct'] and not left[t]['correct']),
            'lost': sorted(t for t in expected if left[t]['correct'] and not right[t]['correct']),
            'by_capability': by_capability, 'tags_may_overlap': True,
            'capability_attribution': 'descriptive only; requires separate ablations'}


def historical_baseline():
    profile, audit = read(HISTORICAL / 'profile.json'), read(HISTORICAL / 'audit.json')
    require(audit['criteria']['R4'] is True and audit['source_digest'] == digest(profile), 'historical audit invalid')
    for name in ('grid_expansions', 'grid_depth', 'arc_decisions', 'arc_environment_seed', 'rep'):
        require(profile['configuration'][name] == BUDGET[name], 'historical budget differs')
    result = {'primary_reference': 'ECHO-4.5 measured 2026-09-28, not the older SEMILLA',
              'origin': 'KNOWN_EVALUATION_FOLLOWUP', 'blind_exam': False,
              'audit_sha256': file_sha(HISTORICAL / 'audit.json'),
              'historical_profile_sha256': digest(profile), 'budget': BUDGET, 'grids': {}}
    receipts = {}
    for domain in ('R1', 'R2'):
        ids = [Path(p).stem for p in profile['corpora'][domain]['tasks']]
        folder = HISTORICAL / 'grid' / domain / 'sin_s6'
        require({p.stem for p in folder.glob('*.json')} == set(ids), 'historical grid coverage differs')
        rows = [read(folder / (tid + '.json')) for tid in sorted(ids)]
        expected = audit['grid'][domain]['sin_s6']
        require(digest(rows) == expected['records_digest'], 'historical grid records changed')
        require(all(r['source_digest'] == digest(profile) for r in rows), 'historical grid profile differs')
        check = compare_grid_rows(rows, rows, ids)
        require(check['overall']['before'] == expected['solved'], 'historical grid score differs')
        result['grids'][domain] = {'solved': expected['solved'], 'tasks': expected['tasks'],
                                  'records_digest': digest(rows), 'task_ids': sorted(ids),
                                  'capability_tags': {tid: ['unclassified'] for tid in sorted(ids)}}
        receipts.update({str((folder / (tid + '.json')).relative_to(REPO)): file_sha(folder / (tid + '.json')) for tid in ids})
    expected = audit['arc']['sin_s6']
    arc_arm = expected.get('alias_of', 'sin_s6')
    games = profile['games']
    rows = [read(HISTORICAL / 'arc' / arc_arm / (game + '.json')) for game in games]
    require(digest(rows) == expected['records_digest'], 'historical ARC3 records changed')
    totals = arc_totals(rows)
    require(totals['levels'] == expected['levels'] and totals['of'] == expected['of'] and
            totals['contract_score'] == expected['contract_score'], 'historical ARC3 totals differ')
    require(all(r['source_digest'] == digest(profile) for r in rows), 'historical ARC3 profile differs')
    result['arc3'] = dict(totals, games=games, stored_arm=arc_arm, records_digest=digest(rows))
    receipts.update({str((HISTORICAL / 'arc' / arc_arm / (game + '.json')).relative_to(REPO)):
                     file_sha(HISTORICAL / 'arc' / arc_arm / (game + '.json')) for game in games})
    result['receipts'] = receipts
    return result


def arc_totals(rows):
    from seed.final_arc import accounting
    require(bool(rows), 'empty ARC3 cohort')
    index_rows(rows, 'game')
    for row in rows:
        require(row['budget'] == BUDGET['arc_decisions'], 'unequal ARC3 decision budgets')
        require(row['accounting'] == accounting(row) and row['sdk_counter_verified'] is True, 'invalid ARC3 action accounting')
        per_level = row['accounting']['complete_per_level']
        require(len(row['baseline']) == row['win_levels'] and row['win_levels'] > 0, 'missing level denominators')
        # Recompute the frozen scoring formula without invoking the actor.
        numerator = sum((i + 1) * min(human / agent, 1) ** 2 if agent else 0
                        for i, (agent, human) in enumerate(zip(per_level, row['baseline'])))
        score = 100 * numerator / sum(range(1, row['win_levels'] + 1))
        require(math.isfinite(row['contract_score']) and abs(score - row['contract_score']) < 1e-12, 'ARC3 score differs from actions')
    return {'levels': sum(r['levels_completed'] for r in rows), 'of': sum(r['win_levels'] for r in rows),
            'contract_score': sum(r['contract_score'] for r in rows) / len(rows),
            'decisions': sum(r['accounting']['decisions'] for r in rows),
            'actions': sum(r['accounting']['total_actions'] for r in rows),
            'automatic_resets': sum(r['accounting']['automatic_resets'] for r in rows)}


def compare_arc_rows(before, after, games):
    a, b = index_rows(before, 'game'), index_rows(after, 'game')
    require(len(set(games)) == len(games) and set(a) == set(b) == set(games), 'mismatched ARC3 cohort')
    require(all(a[g]['baseline'] == b[g]['baseline'] and a[g]['win_levels'] == b[g]['win_levels'] for g in games), 'ARC3 levels or baseline changed')
    left, right = arc_totals(before), arc_totals(after)
    return {'levels': delta(left['levels'], right['levels'], left['of']), 'before': left, 'after': right,
            'score_delta': right['contract_score'] - left['contract_score'],
            'games_losing_levels': [g for g in games if b[g]['levels_completed'] < a[g]['levels_completed']],
            'games_losing_score': [g for g in games if b[g]['contract_score'] < a[g]['contract_score'] - 1e-10],
            'per_game': {g: delta(a[g]['levels_completed'], b[g]['levels_completed'], a[g]['win_levels']) for g in games},
            'capability_attribution': 'unclassified official games; causal attribution pending dedicated ablations'}


def prepare(root=ROOT):
    from seed import arc_capabilities as capabilities
    guard = freeze_guard()
    baseline = historical_baseline()
    profile = {'sources': {p: file_sha(REPO / p) for p in SOURCES}, 'protected': guard,
               'baseline_sha256': digest(baseline), 'budget': BUDGET,
               'capability_suite_sha256': digest(capabilities.suite()),
               'capability_configuration': capabilities.CONFIG, 'capability_arms': capabilities.ARMS,
               'python': sys.version, 'candidate': 'UNBOUND_WAIT_S6_GREEN',
               'memory_transfer': 'NOT_IMPLEMENTED; village3E result does not certify ARC transfer'}
    if (root / 'profile.json').exists():
        require(read(root / 'profile.json') == profile, 'preparation already frozen under another profile')
    else:
        save(root / 'baseline.json', baseline)
        save(root / 'capability-suite.json', capabilities.suite())
        for source in SOURCES:
            target = root / 'source-archive' / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / source).read_bytes())
        save(root / 'profile.json', profile)
        save(root / 'prepared.json', {'at': now(), 'profile_sha256': digest(profile), 'evaluation_opened': False})
    prepared(root)
    return {'prepared': True, 'candidate_ready': candidate_available(), 'new_arc_scores': False,
            'baseline': {'ARC1': '31/400', 'ARC2': '0/120', 'ARC3': '11/112'}}


def prepared(root=ROOT):
    profile = read(root / 'profile.json')
    require(profile['sources'] == {p: file_sha(REPO / p) for p in SOURCES}, 'comparison sources changed')
    require(profile['protected'] == freeze_guard(), 'protected manifests changed')
    baseline = read(root / 'baseline.json')
    require(profile['baseline_sha256'] == digest(baseline), 'comparison baseline changed')
    require(file_sha(HISTORICAL / 'audit.json') == baseline['audit_sha256'], 'historical audit changed')
    require(all(file_sha(REPO / p) == expected for p, expected in baseline['receipts'].items()), 'historical receipts changed')
    require(digest(read(root / 'capability-suite.json')) == profile['capability_suite_sha256'], 'stored development suite changed')
    from seed.final_campaign import corpus_metadata
    require(corpus_metadata() == read(HISTORICAL / 'profile.json')['corpora'],
            'evaluation datasets or game implementations changed since the reference')
    return profile


def candidate_available():
    return (S6 / 'closed.json').exists() and read(S6 / 'closed.json').get('s6_green') is True


def validate_release(closed, audit, completed, strategies, s6_profile):
    checks = {name: True for name in ('B1', 'B2', 'B3', 'B4', 'B5')}
    require(closed.get('result') == 'EXAM_CLOSED' and closed.get('s6_green') is True and
            closed.get('exam_opened') is True, 'S6 not closed green; pilot policies are ineligible')
    require(audit.get('green') is True and audit.get('checks') == checks and closed.get('checks') == checks, 'S6 B1-B5 not certified')
    require(audit.get('training_audit') is True and audit.get('model_payload_audit') is True and
            set(audit.get('replays', {})) == set(strategies) and all(audit['replays'].values()), 'S6 audit incomplete')
    require(completed['sources'] == audit['sources'] == s6_profile['sources'] and
            completed['profile_sha256'] == digest(s6_profile), 'S6 release source mismatch')
    require(completed['strategies_sha256'] == audit['strategies_sha256'] == digest(strategies), 'S6 strategies changed')
    require(set(strategies) == {'echo', 'fijo', 'semilla', 'sinfiltro'}, 'S6 four-arm custody incomplete')
    return strategies['echo']


def freeze_candidate(root=ROOT):
    profile = prepared(root)
    require(candidate_available(), 'S6 still pending or red; no pilot candidate may be used')
    names = ['closed.json', 'exam/audit.json', 'completed.json', 'strategies.json', 'profile.json',
             'pilot.json', 'pilot-audit.json', 'campaign.json', 'campaign-audit.json', 'transport-recovery2/audit.json']
    policy = validate_release(*(read(S6 / name) for name in names[:5]))
    from seed.s6_transition_capacity import Execution
    require(Execution.validate(policy) == policy, 'invalid native B11 policy')
    for phase in ('pilot', 'campaign'):
        require(read(S6 / (phase + '.json'))['promote'] is True and read(S6 / (phase + '-audit.json'))['valid'] is True,
                'missing S6 promotion or independent audit')
    transport = read(S6 / 'transport-recovery2/audit.json')
    require(transport['valid'] is True and len(transport['stages']) == 12 and
            {row['stage'] for row in transport['stages']} == {p + str(i) for p in ('p', 'c') for i in range(6)} and
            all(row['valid'] is True for row in transport['stages']), 'transport audit incomplete')
    from seed import s6b11_recovery2
    require(transport['profile_sha256'] == digest(s6b11_recovery2.integrity()), 'transport profile mismatch')
    from seed.final_campaign import arc_runtime
    require(arc_runtime() == read(HISTORICAL / 'profile.json')['arc_runtime'], 'ARC runtime differs from baseline')
    candidate = {'policy': policy, 'profile_sha256': digest(profile),
                 's6_receipts': {n: file_sha(S6 / n) for n in names},
                 'grid_alias': 'historical S2v unchanged; S6-B11 has no grid operations',
                 'origin': 'KNOWN_EVALUATION_FOLLOWUP', 'blind_exam': False}
    if (root / 'candidate.json').exists():
        require(candidate == read(root / 'candidate.json'), 'candidate already frozen differently')
    else:
        save(root / 'candidate.json', candidate)
    return candidate


def arc_one(game, policy, budget=2000, environments=None):
    """Native B11 execution, no recorder, with the historical ARC3 accounting."""
    import arc_agi
    from echo_arc import agent, runner
    from seed.s6_transition_capacity import Execution
    from seed.final_arc import Counter, accounting, protocol_check
    agent._COMP_CACHE.clear()
    arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE,
                            environments_dir=str(environments or REPO / 'lab/arc3/environment_files'))
    desc = next(e for e in arcade.get_environments() if e.game_id == game)
    env = Counter(arcade.make(game, seed=0))
    row = Execution.play(env, budget, runner.seed_for(game, 0), policy)
    require(env.emitted == len(row['actions']), 'ARC3 emitted-action mismatch')
    row.update(game=game, actor={'kind': 's6b11', 'strategy': policy}, budget=budget,
               baseline=list(desc.baseline_actions or []), automatic_reset_indices=env.automatic)
    row['accounting'] = accounting(row)
    row['sdk_counter_verified'] = protocol_check(row)
    row['historical_score'] = runner.official_game_score(row['actions_per_level'], row['baseline'])
    row['contract_score'] = runner.official_game_score(row['accounting']['complete_per_level'], row['baseline'])
    return row


def run_arc(root=ROOT, audit=False):
    require(Path(sys.prefix).resolve() == ARC_PYTHON.parent.parent.resolve(), 'use the managed ARC Python for this measurement')
    profile = prepared(root)
    candidate = freeze_candidate(root)
    baseline = read(root / 'baseline.json')
    directory = root / 'arc3-followup'
    require(not (directory / 'audit.json').exists(), 'follow-up already closed; do not reopen')
    if not audit:
        opened = {'profile_sha256': digest(profile), 'candidate_sha256': digest(candidate),
                  'origin': 'KNOWN_EVALUATION_FOLLOWUP', 'blind_exam': False}
        if (directory / 'opened.json').exists():
            require(read(directory / 'opened.json') == opened, 'different follow-up opening')
        else:
            save(directory / 'opened.json', opened)
    else:
        require((directory / 'measured.json').exists(), 'no complete measurement to audit')
        require(read(directory / 'measured.json')['pid'] != os.getpid(), 'audit must use another process')
    rows = []
    for game in baseline['arc3']['games']:
        path = directory / 'records' / (game + '.json')
        if audit or not path.exists():
            row = arc_one(game, candidate['policy'])
            row.update(source_digest=digest(profile), candidate_sha256=digest(candidate))
            if audit:
                require(digest(row) == digest(read(path)), 'complete independent ARC3 replay differs')
            else:
                save(path, row)
        row = read(path)
        require(row['source_digest'] == digest(profile) and row['candidate_sha256'] == digest(candidate), 'invalid checkpoint')
        rows.append(row)
        save(directory / ('audit-status.json' if audit else 'status.json'), {'at': now(), 'completed': len(rows), 'of': 16})
    historical = [read(HISTORICAL / 'arc' / baseline['arc3']['stored_arm'] / (g + '.json')) for g in baseline['arc3']['games']]
    report = compare_arc_rows(historical, rows, baseline['arc3']['games'])
    prepared(root)
    if audit:
        require(report == read(directory / 'measured.json')['comparison'], 'comparison reconstruction differs')
        save(directory / 'audit.json', {'valid': True, 'replayed': len(rows), 'pid': os.getpid(), 'at': now(),
                                        'candidate_sha256': digest(candidate), 'comparison': report,
                                        'official_gateway_score': False, 's6_verdict_changed': False})
    else:
        save(directory / 'measured.json', {'pid': os.getpid(), 'at': now(), 'comparison': report})
        subprocess.run([str(ARC_PYTHON), '-m', 'seed.arc_comparison', 'audit-arc3'], cwd=REPO, check=True)
    return report


def snapshot(root=ROOT):
    """A dated progress receipt; never consumed by ECHO or its model prompts."""
    rows = [v for p in sorted((S6 / 'pilot').glob('round-*.json')) for v in read(p)['verdicts']]
    accepted = [{k: v.get(k) for k in ('arm', 'seed', 'id', 'type', 'A', 'B')} for v in rows if v['verdict'] == 'accepted']
    record = {'at': now(), 'status': read(S6 / 'status.json'), 'verified_proposals': len(rows),
              'planned_pilot_proposals': 36, 'accepted': accepted,
              'pilot_audit_present': (S6 / 'pilot-audit.json').exists(),
              's6_green': candidate_available(), 'source_receipts': {
                  str(p.relative_to(REPO)): file_sha(p) for p in sorted((S6 / 'pilot').glob('round-*.json'))},
              'independent_audit_required': True, 'official_arc_score': False}
    save(root / 'monitoring' / ('s6-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json'), record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'check', 'snapshot', 'freeze-candidate', 'run-arc3', 'audit-arc3'])
    command = parser.parse_args().command
    if command == 'prepare':
        result = prepare()
    elif command == 'check':
        p = prepared()
        result = {'intact': True, 'protected_sources': len(p['protected']['sources']), 'candidate_ready': candidate_available()}
    elif command == 'snapshot':
        result = snapshot()
    elif command == 'freeze-candidate':
        result = freeze_candidate()
    else:
        result = run_arc(audit=command == 'audit-arc3')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
