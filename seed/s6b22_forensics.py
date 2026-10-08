"""Read-only B22 postmortem. No simulator, model, or experiment runner imports.

Recompute all 288 decisions from the 924 recorded measurements. Write only
to a separate analysis directory; B22's sources and receipts stay frozen.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

EPS = 1e-10
REPO = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def score_parts(row):
    denominator = sum(range(1, len(row['baseline']) + 1))
    return [100 * i * (min(reference / row['actions_per_level'][i-1], 1) ** 2
            if i <= len(row['actions_per_level']) and row['actions_per_level'][i-1] else 0)
            / denominator for i, reference in enumerate(row['baseline'], 1)] if denominator else []


def delta(base, after):
    require(len(base['rows']) == len(after['rows']), 'different cohort lengths')
    effects = []
    for i, (b, a) in enumerate(zip(base['rows'], after['rows'])):
        require(all(b[k] == a[k] for k in ('version', 'seed', 'rep', 'budget')), 'different case identity')
        effects.append(dict(case_index=i, level_delta=a['levels_completed']-b['levels_completed'],
                            score_delta=a['score']-b['score']))
    losses = [e['case_index'] for e in effects if e['level_delta'] < 0 or e['score_delta'] < -EPS]
    return dict(gain=after['levels']-base['levels'], loss_indices=losses,
                score_delta=after['score']-base['score']), effects


def category(change):
    if change['loss_indices']:
        return 'individual_loss'
    if change['gain'] >= 2:
        return 'pass'
    return 'conservative_plus_one' if change['gain'] == 1 else 'no_level_gain'


def matches(guard, features):
    for key, (op, value) in guard.items():
        actual = features[key]
        if op not in ('eq', 'le', 'ge'):
            raise ValueError('unknown guard operator')
        if not (actual == value if op == 'eq' else actual <= value if op == 'le' else actual >= value):
            return False
    return True


class Reader:
    def __init__(self, root):
        self.root = root
        self.hashes = {}
        self.measurements = 0

    def read(self, relative):
        data = (self.root / relative).read_bytes()
        self.hashes[str(relative)] = hashlib.sha256(data).hexdigest()
        return json.loads(data)

    def triple(self, namespace, label):
        suffix = Path(label + '.json')
        before = self.read(Path(namespace) / 'measurements' / suffix)
        replay = self.read(Path(namespace) / 'measurements' / label / 'replay.json')
        independent = self.read(Path(namespace + '-audit') / 'measurements' / suffix)
        require(before == replay == independent, f'replay or audit mismatch: {namespace}/{label}')
        receipt = self.read(Path(namespace) / 'audits' / suffix)
        require(receipt['valid'] and receipt['measurement_sha256'] == sha(before), 'invalid receipt')
        require(before['trace_digest'] == sha(before['rows']), 'invalid trace digest')
        require(before['levels'] == sum(r['levels_completed'] for r in before['rows']), 'level sum differs')
        require(before['score'] == sum(r['score'] for r in before['rows']), 'score sum differs')
        for row in before['rows']:
            require(math.isfinite(row['score']), 'nonfinite score')
            require(math.isclose(sum(score_parts(row)), row['score'], abs_tol=EPS, rel_tol=0), 'score formula differs')
        self.measurements += 3
        return before


def summarize(rows):
    return dict(attempts=len(rows), categories=dict(Counter(r['category'] for r in rows)),
                unchanged_actions=sum(r['changed_cases'] == 0 for r in rows),
                inactive_on_baseline=sum(r['inactive_on_baseline'] for r in rows),
                distinct_proposals=len({r['proposal_sha256'] for r in rows}),
                durations=dict(sorted(Counter(r['hold'] for r in rows).items())),
                repairs=sum(r['phase'] == 'repair' for r in rows))


def investigate(root):
    reader = Reader(root)
    closed = reader.read('closed.json')
    require(closed['valid'] and not closed['exam_opened'], 'B22 closure invalid')
    manifest = reader.read('input/manifest.json')
    for category_name, directory in [('sources', REPO), ('inputs', root/'input')]:
        for name, digest in manifest[category_name].items():
            require(hashlib.sha256((directory/name).read_bytes()).hexdigest() == digest,
                    f'frozen {category_name} changed: {name}')
    frozen_audit = reader.read('arithmetic-review.json')
    require(frozen_audit['valid'] and frozen_audit['model_calls'] == 0, 'invalid previous audit')
    micro = reader.read('micro.json')
    records = []
    baselines = {}
    events = {}
    all_reads = []
    for name, kind, seed in manifest['configuration']['cells']:
        base = reader.triple('s-'+name, 'baseline')
        baselines[name] = base
        reads = [r for row in base['rows'] for r in row['diagnostics']['consumers'] if r['parameter'] == 'HOLD']
        if not all_reads:
            all_reads = reads
        history = {}
        for cell in (c for c in micro['cells'] if c['arm'] == name):
            index = cell['slot']-1
            step = reader.read(f'steps/{name}/{index:03d}.json')
            e = step['event']
            request = reader.read(f'requests/{name}/{index:03d}.json')['request']
            require(e['proposal'] == request['proposal'], 'proposal/request mismatch')
            require(e['proposal_sha256'] == sha(e['proposal']), 'proposal digest mismatch')
            after = reader.triple('s-'+name, f'candidate/{index:03d}')
            change, effects = delta(base, after)
            require(change == e['A'] == cell['diff'], 'decision arithmetic mismatch')
            require(effects == e['development']['case_effects'], 'feedback differs from measurements')
            require((category(change) == 'pass') == (e['verdict'] == 'A_ONLY_PASS'), 'verdict mismatch')
            require(e['usage'] == dict(model_calls=0, input_tokens=0, output_tokens=0), 'unexpected model use')
            patch = e['proposal']['patches'][0]
            inactive = not any(matches(patch['when'], r['features']) for r in reads)
            changed = sum(b['actions'] != a['actions'] for b, a in zip(base['rows'], after['rows']))
            require(changed == e['development']['changed_games'], 'changed games mismatch')
            require(not inactive or changed == 0, 'baseline inactivity argument refuted')
            schedule = e['schedule']
            best = request['shortlist'][0]
            parent = history.get(e['target_id'])
            row = dict(arm=name, kind=kind, seed=seed, slot=index+1, phase=schedule['phase'],
                       source=schedule.get('distribution', 'repair'), global_index=schedule['global_index'],
                       parent_id=e['target_id'], child=schedule.get('child'), hold=patch['set']['HOLD'],
                       guard=canonical(patch['when']), gain=change['gain'], losses=len(change['loss_indices']),
                       loss_indices=change['loss_indices'], score_delta=change['score_delta'],
                       category=category(change), changed_cases=changed, inactive_on_baseline=inactive,
                       proposal_sha256=e['proposal_sha256'], behavior_sha256=e['behavior_sha256'],
                       loss_overlap=best.get('loss_context_overlap'), gain_overlap=best.get('gain_context_overlap'),
                       parent_gain=parent['A']['gain'] if parent else None,
                       parent_losses=len(parent['A']['loss_indices']) if parent else None,
                       cases=effects)
            records.append(row)
            history[e['id']] = e
        events[name] = history
    require(len(records) == 288, 'unexpected B22 attempt count')
    # The two arms share the same global stream, so candidates are not independent trials.
    paired_global = 0
    for seed in manifest['configuration']['seeds']:
        random_rows = [r for r in records if r['arm'] == f'R22-{seed}']
        adaptive = [r for r in records if r['arm'] == f'M22-{seed}' and r['phase'] == 'global']
        for r in adaptive:
            require(r['proposal_sha256'] == random_rows[r['global_index']]['proposal_sha256'], 'paired stream differs')
            paired_global += 1
    broad = {}
    for phase in ('micro', 'broad'):
        base = reader.triple('v-'+phase, 'baseline')
        after = reader.triple('v-'+phase, 'candidate')
        change, effects = delta(base, after)
        changed = []
        for i, (b, a) in enumerate(zip(base['rows'], after['rows'])):
            if b['actions'] == a['actions'] and not effects[i]['level_delta'] and abs(effects[i]['score_delta']) <= EPS:
                continue
            divergence = next((j for j,(x,y) in enumerate(zip(b['actions'],a['actions'])) if x != y),
                              min(len(b['actions']),len(a['actions'])))
            changed.append(dict(case_index=i, version=b['version'], seed=b['seed'],
                before_levels=b['levels_completed'], after_levels=a['levels_completed'],
                before_score=b['score'], after_score=a['score'], score_delta=effects[i]['score_delta'],
                score_change_pct=100*(a['score']/b['score']-1) if b['score'] else None,
                before_actions_per_level=b['actions_per_level'], after_actions_per_level=a['actions_per_level'],
                before_score_parts=score_parts(b), after_score_parts=score_parts(a),
                first_action_divergence=divergence,
                before_resets=b['resets'], after_resets=a['resets']))
        broad[phase] = dict(before=base['levels'], after=after['levels'], diff=change, changed=changed)
    summaries = {kind:summarize([r for r in records if r['kind'] == kind]) for kind in ('R22','M22')}
    repair = {}
    for child in (1,2):
        rows = [r for r in records if r['child'] == child]
        repair[str(child)] = dict(summarize(rows),
            all_loss_overlap_zero=all(r['loss_overlap'] == 0 for r in rows),
            all_loss_overlap_one=all(r['loss_overlap'] == 1 for r in rows),
            actual_regressions=sum(r['losses'] > 0 for r in rows),
            reduced_loss_cases=sum(r['losses'] < r['parent_losses'] for r in rows))
    require(reader.measurements == 924, 'unexpected measurement total')
    summary = dict(valid=True, scope='read-only existing measurements, source hashes, requests and arithmetic; no new games',
        source_run=str(root), closed=closed, official_audit=frozen_audit,
        recomputed_measurements=reader.measurements, recomputed_attempts=len(records),
        checked_sources=len(manifest['sources']), checked_inputs=len(manifest['inputs']),
        models_used=0, all=summarize(records), arms=summaries, repairs=repair,
        paired_global_proposals=paired_global,
        by_source={source:summarize([r for r in records if r['source'] == source]) for source in ('general','base-pool','repair')},
        baseline_consumption_features={k:sorted({r['features'][k] for r in all_reads}) for k in all_reads[0]['features']},
        validation=broad,
        budget_note='11976 physical games belong to B22; this analysis launches zero games and zero model calls',
        inference_limit='absence of passes in these sampled runs does not establish grammar exhaustion or future impossibility')
    return summary, records, reader.hashes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=REPO/'lab/seed/s6b22-20261006')
    parser.add_argument('--out',type=Path,default=REPO/'lab/seed/s6b22-forensics-20261007')
    args=parser.parse_args()
    root,out=args.root.resolve(),args.out.resolve()
    require(out != root and root not in out.parents, 'analysis output must be outside frozen run')
    summary,records,hashes=investigate(root)
    out.mkdir(parents=True,exist_ok=True)
    (out/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (out/'proposals.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    (out/'input-hashes.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n')
    columns=[k for k in records[0] if k != 'cases']
    with (out/'proposals.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for row in records:writer.writerow({k:row[k] for k in columns})
    print(json.dumps({k:summary[k] for k in ('valid','recomputed_measurements','recomputed_attempts','all','arms','repairs')},ensure_ascii=False))


if __name__ == '__main__':
    main()
