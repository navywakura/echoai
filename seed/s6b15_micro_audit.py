"""Read-only reconstruction of B15's closed micro; no new games or inference."""
import json
from collections import Counter
from pathlib import Path

from seed import s6b15 as r, s6b15_micro as micro
from echo_arc.contrastive_grammar import choices, witnesses
from echo_arc.feasible_grammar import matches

OUT = r.REPO / 'lab/seed/s6b15-micro-audit-20261004'


def read(path):
    return json.loads(path.read_text())


def run():
    profile = r.b.integrity()
    saved = read(r.ROOT / 'micro.json')
    assert read(r.ROOT / 'closed.json')['result'] == 'MICRO_NO_PROMOTION'
    assert saved['profile_sha256'] == r.b.sha(profile)
    for name, digest in saved['artifacts'].items():
        assert r.model.digest_file(r.ROOT / name) == digest, name
    baseline = read(r.ROOT / 'primary/measurements/micro/baseline/A.json')
    replay = read(r.ROOT / 'primary/measurements/micro/baseline/A/replay.json')
    assert baseline == replay
    assert r.b.sha(baseline['rows']) == baseline['trace_digest'] == saved['baseline_digest']
    assert baseline['levels'] == sum(x['levels_completed'] for x in baseline['rows']) == 378
    current, reference, history = micro.reference()
    assert baseline == reference
    records, calls, cache_records = [], [], 0
    for cell in saved['cells']:
        name = cell['cell']
        request = r.prompts.request('echo', 1, current, baseline, history,
                                   bind=cell['binding'], numeric=cell['numeric'])
        response = r.model.load(name, request, cell['seed'], r.ROOT, r.b.sha(profile), audit_tokens=True)
        calls.append(name)
        proposal = r.prompts.check_answer(response['answer'], request)
        recorded = read(r.ROOT / (name + '.json'))
        assert recorded['summary'] == cell
        assert recorded['request_sha256'] == r.b.sha(request)
        after = read(r.ROOT / 'primary/measurements' / name / 'A.json')
        again = read(r.ROOT / 'primary/measurements' / name / 'A/replay.json')
        assert after == again
        assert r.b.sha(after['rows']) == after['trace_digest'] == cell['trace_digest']
        levels = sum(x['levels_completed'] for x in after['rows'])
        losses = [i for i, (a, b) in enumerate(zip(baseline['rows'], after['rows'], strict=True))
                  if b['levels_completed'] < a['levels_completed'] or b['score'] + 1e-10 < a['score']]
        gain = levels - 378
        assert (levels, gain, losses, gain >= 2 and not losses) == \
            (cell['levels'], cell['gain'], cell['loss_indices'], cell['passes_A'])
        effects = [dict(index=i, level_delta=b['levels_completed']-a['levels_completed'],
                        score_delta=b['score']-a['score'])
                   for i, (a, b) in enumerate(zip(baseline['rows'], after['rows'], strict=True))
                   if a['levels_completed'] != b['levels_completed'] or abs(b['score']-a['score']) > 1e-10]
        item = proposal['patches'][0]
        parameter = next(iter(item['set']))
        matched = sum(matches(item['when'], w['features']) for row in baseline['rows']
                      for w in witnesses([row])[parameter])
        total = sum(len(witnesses([row])[parameter]) for row in baseline['rows'])
        old_contrasts = r.b.evidence.comparison(baseline, after)['contrasts']
        records.append(dict(cell=name, levels=levels, gain=gain, loss_indices=losses,
            actual_operator=parameter, binding=cell['binding'], numeric=cell['numeric'],
            matches_requested=parameter==request['requested_operator'], replay_identical=True,
            passes_A=gain>=2 and not losses, matched_readings=matched, all_readings=total,
            effects=effects, original_feedback_cases=[c['case_index'] for c in old_contrasts],
            level_gains_missing_in_original_feedback=[e['index'] for e in effects if e['level_delta']>0
                and e['index'] not in [c['case_index'] for c in old_contrasts]]))
    assert len(calls) == len(set(calls)) == 12
    assert calls == read(r.ROOT / 'model-budget.json')['calls']
    assert micro.gate(saved['cells']) is saved['promote'] is False
    for part in ('main', 'replay'):
        for path in (r.ROOT / 'primary/cache' / part).glob('*.json'):
            value = read(path)
            assert r.b.sha(value['record']) == value['digest']
            assert value['record']['origin'] == 'DEVELOPMENT_A'
            spec = tuple(value['record'][k] for k in ('version','seed','rep','budget'))
            assert spec in r.b.A
            cache_records += 1
    assert cache_records == read(r.ROOT / 'budget.json')['scheduled_games'] == 1280
    assert not (r.ROOT / 'pilot.json').exists()
    assert not (r.ROOT / 'preflight.json').exists()
    assert not (r.ROOT / 'exam/opened.json').exists()
    log = (r.ROOT / 'run-process.log').read_text()
    assert not any(x in log for x in ('Traceback (most recent call last)', 'BLOCKED_INSTRUMENT'))
    for path in (r.ROOT / 'calls').rglob('failed.json'):
        raise AssertionError('failed model transport: ' + str(path))
    result = dict(valid=True, at=r.b.now(), profile_sha256=r.b.sha(profile),
        audit_kind='independent reconstruction of stored artifacts; no new execution',
        independent_execution=False, new_games=0, new_model_calls=0, frozen_sources=len(profile['sources']),
        cache_records=cache_records, calls=12, replays_checked=13, promote=False, s6_green=False,
        micro_sha256=r.b.sha(saved), records=records,
        operator_counts={str(binding): dict(Counter(x['actual_operator'] for x in records if x['binding']==binding))
                         for binding in (False,True)})
    r.b.atomic(OUT / 'audit.json', result)
    r.b.atomic(OUT / 'source.json', dict(script_sha256=r.model.digest_file(Path(__file__))))
    print(r.b.canonical({k:v for k,v in result.items() if k != 'records'}), flush=True)


if __name__ == '__main__':
    run()
