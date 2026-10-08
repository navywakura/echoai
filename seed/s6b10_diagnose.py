"""Post-mortem of existing B10 artifacts; no inference, games or exam access."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from seed import s6b10 as s
from echo_arc.feasible_grammar import validate_answer

OUT = s.REPO / 'lab/seed/s6b10-diagnosis-20260929'


def main():
    receipts = {}

    def read(path):
        raw = path.read_bytes()
        receipts[str(path.relative_to(s.REPO))] = hashlib.sha256(raw).hexdigest()
        return json.loads(raw)

    profile = s.integrity()
    pilot = read(s.ROOT / 'pilot.json')
    audit = read(s.ROOT / 'pilot-audit.json')
    closed = read(s.ROOT / 'closed.json')
    assert audit['valid'] and audit['verdicts_rebuilt'] == len(pilot['verdicts']) == 18
    assert closed['result'] == 'PILOT_NO_PROMOTION' and not closed['s6_green']
    assert not (s.ROOT / 'exam/opened.json').exists()
    baseline = {part: read(s.ROOT / f'measurements/baseline/{part}.json') for part in ('A', 'B')}
    behavior = {'A': defaultdict(list), 'AB': defaultdict(list)}
    guards, programs, details = Counter(), set(), []
    measures = {}
    for verdict in pilot['verdicts']:
        label = f"local-{verdict['arm']}-{verdict['seed']}/{verdict['id']}"
        programs.add(s.canonical(verdict['proposal']))
        guards.update(verdict['proposal']['patches'][0]['when'].keys())
        row = {key: verdict[key] for key in ('arm', 'seed', 'id', 'proposal', 'verdict')}
        parts = []
        for part in ('A', 'B'):
            value = read(s.ROOT / f'measurements/pilot/{label}/{part}.json')
            assert value['trace_digest'] == s.sha(value['rows'])
            assert len(value['rows']) == len(baseline[part]['rows']) == 40
            measures[(label, part)] = value
            changes = []
            for index, (before, after) in enumerate(zip(baseline[part]['rows'], value['rows'])):
                if before['levels_completed'] != after['levels_completed'] or abs(before['score'] - after['score']) > 1e-10:
                    changes.append({'index': index, 'family': before['family'],
                        'levels': [before['levels_completed'], after['levels_completed']],
                        'score': [before['score'], after['score']],
                        'actions_per_level': [before['actions_per_level'], after['actions_per_level']]})
            row[part] = {'levels': value['levels'], 'score_sum': value['score'], 'changes': changes,
                'level_losses': [i for i, (a, b) in enumerate(zip(baseline[part]['rows'], value['rows']))
                                 if b['levels_completed'] < a['levels_completed']],
                'score_losses': [i for i, (a, b) in enumerate(zip(baseline[part]['rows'], value['rows']))
                                 if b['score'] + 1e-10 < a['score']]}
            assert sorted(set(row[part]['level_losses'] + row[part]['score_losses'])) == verdict[part]['loss_indices']
            parts.append([{k: game[k] for k in ('actions', 'frames', 'levels_completed', 'score', 'resets', 'actions_per_level')}
                          for game in value['rows']])
            if part == 'A':
                behavior['A'][s.sha(parts[0])].append(label)
        behavior['AB'][s.sha(parts)].append(label)
        details.append(row)

    # This was a human instrument control fixed and measured BEFORE B9/B10.
    # Only test its availability in the frozen language, never inject it into prompts.
    control_root = s.REPO / 'lab/seed/s6-transition-capacity-20260929'
    control_profile = read(control_root / 'profile.json')
    control = next(row['candidate']['program'] for row in control_profile['controls'] if row['name'] == 'stuck_4')
    assert read(control_root / 'audit.json')['valid']
    human_allowed = []
    evidence = defaultdict(list)
    for stage in ('p0', 'p1', 'p2'):
        payload = read(s.BASE / stage / 'payload.json')
        for arm, requests in payload['requests'].items():
            for request in requests:
                validate_answer(s.canonical(control), request['guard_schema'])
                human_allowed.append({'stage': stage, 'arm': arm, 'id': request['id']})
                observed = json.loads(request['prompt'].split('Observations: ', 1)[1].removesuffix('. Return JSON only.'))
                evidence[arm].append({'stage': stage, 'observations_sha256': s.sha(observed)})

    all_b_losses = {i for row in details for i in row['B']['score_losses']}
    assert len(all_b_losses) == 1
    index = next(iter(all_b_losses))
    old = baseline['B']['rows'][index]
    trial_rows = [measures[(f"local-{v['arm']}-{v['seed']}/{v['id']}", 'B')]['rows'][index] for v in pilot['verdicts']]
    paired = []
    for seed in s.SEEDS:
        for round_id in range(3):
            labels = [f'local-{arm}-{seed}/{round_id}' for arm in ('fijo', 'echo')]
            group = next(items for items in behavior['AB'].values() if labels[0] in items)
            paired.append({'seed': seed, 'round': round_id, 'same_measured_behavior': labels[1] in group})
    report = {'at': datetime.now(timezone.utc).isoformat(), 'profile_sha256': s.sha(profile),
        'scope': 'post-mortem; existing development A and protected B artifacts; no reserved exam or new execution',
        'protected_data_policy': 'B diagnosis is not model input or permission to tune to these cases; use fresh protection in a new protocol',
        'baseline': {k: {'levels': v['levels'], 'score_sum': v['score'], 'games': len(v['rows'])} for k, v in baseline.items()},
        'verdicts': dict(Counter(v['verdict'] for v in details)), 'unique_programs': len(programs),
        'behavior_groups': {k: list(v.values()) for k, v in behavior.items()}, 'guard_feature_counts': dict(guards),
        'human_control_preexisting_and_legal_requests': len(human_allowed),
        'selected_evidence_per_actor': dict(evidence), 'paired_behavior': paired,
        'all_proposals_gain_A_levels': all(v['A']['levels'] == baseline['A']['levels'] + 8 for v in details),
        'any_individual_level_regression_A_or_B': any(v[p]['level_losses'] for v in details for p in ('A', 'B')),
        'all_B_aggregate_levels_and_score_improve': all(v['B']['levels'] > baseline['B']['levels'] and
             v['B']['score_sum'] > baseline['B']['score'] for v in details),
        'sole_protected_score_regression': {'index': index, 'baseline_levels': old['levels_completed'],
             'candidate_levels': sorted({v['levels_completed'] for v in trial_rows}), 'baseline_score': old['score'],
             'candidate_score_range': [min(v['score'] for v in trial_rows), max(v['score'] for v in trial_rows)],
             'relative_score_loss_percent_range': [min(100*(old['score']-v['score'])/old['score'] for v in trial_rows),
                                                   max(100*(old['score']-v['score'])/old['score'] for v in trial_rows)],
             'last_level_baseline_actions': old['actions_per_level'][-1],
             'last_level_candidate_actions_range': [min(v['actions_per_level'][-1] for v in trial_rows),
                                                    max(v['actions_per_level'][-1] for v in trial_rows)]},
        'candidate_details': details, 'input_sha256': receipts}
    s.atomic(OUT / 'report.json', report)
    print(s.canonical({key: report[key] for key in ('unique_programs', 'verdicts', 'all_proposals_gain_A_levels',
        'any_individual_level_regression_A_or_B', 'all_B_aggregate_levels_and_score_improve',
        'human_control_preexisting_and_legal_requests', 'sole_protected_score_regression')}))
    print(s.canonical({'distinct_behaviors': {k: len(v) for k, v in behavior.items()},
        'same_behavior_pairs': sum(row['same_measured_behavior'] for row in paired),
        'distinct_observation_sets_per_actor': {k: len({v['observations_sha256'] for v in rows}) for k, rows in evidence.items()}}))


if __name__ == '__main__':
    main()
