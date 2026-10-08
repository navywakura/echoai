"""Public one-factor-at-a-time trials after the single-ingestion correction."""
import argparse
import json
from pathlib import Path
from . import policy, school_v3
from .rehearsal import ROOT, inventory
from .rehearsal_v2 import suite, episode, PROTOCOL as V2_PROTOCOL
from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict

PROTOCOL = dict(version=3, scope='public-development-not-confirmation',
    rooms=V2_PROTOCOL, school_repeats=3, training_move_cap_per_episode=64,
    variants=school_v3.VARIANTS, exploration_period=4,
    primary_comparison='arrival first; moves only on joint success; joint failures tied',
    learning_in_exam=False, campaign_ready=False)


def summary(rows):
    return dict(episodes=len(rows), reached=sum(r['reached'] for r in rows),
        moves=sum(r['moves'] for r in rows),
        collisions=sum(r['collisions'] for r in rows),
        reserve_violations=sum(r['reserve_violations'] for r in rows),
        false_facts=sum(r['false_facts'] for r in rows),
        models_unchanged=all(r['model_unchanged'] for r in rows))


def compare(rows, baseline):
    if [r['seed'] for r in rows] != [r['seed'] for r in baseline]:
        raise ValueError('unpaired trials')
    pairs = []
    for a, b in zip(rows, baseline):
        outcome = (int(a['reached'])-int(b['reached'])) if a['reached'] != b['reached'] else (
            (b['moves'] > a['moves'])-(b['moves'] < a['moves']) if a['reached'] else 0)
        pairs.append(dict(seed=a['seed'], outcome=outcome, moves=[a['moves'], b['moves']],
                          reached=[a['reached'], b['reached']]))
    return dict(wins=sum(p['outcome'] == 1 for p in pairs),
                losses=sum(p['outcome'] == -1 for p in pairs),
                ties=sum(p['outcome'] == 0 for p in pairs), pairs=pairs)


def run(*, isolated=False):
    rooms_a, ledger_a = suite(V2_PROTOCOL['school_seed'], V2_PROTOCOL['school_count'])
    rooms_e, ledger_e = suite(V2_PROTOCOL['exam_seed'], V2_PROTOCOL['exam_count'],
                              [r['shape'] for r in rooms_a])
    # Bind the known public V2 result, never relabel it as independent data.
    history_path = ROOT/'lab/transfer3/rehearsal-v2.json'
    history = loads_strict(history_path.read_bytes())
    if history['school_rooms'] != rooms_a or history['exam_rooms'] != rooms_e:
        raise ValueError('public room identity changed')
    for path, expected in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != expected:
            raise ValueError('V2 source changed: '+path)
    schools, payloads = {}, {'scratch': policy.scratch()}
    for variant in school_v3.VARIANTS:
        payload = policy.scratch()
        rows, counts = [], {}
        for _ in range(PROTOCOL['school_repeats']):
            for room in rooms_a:
                row, payload = school_v3.episode(payload, room['seed'], variant, counts)
                rows.append(row)
        schools[variant] = dict(episodes=rows, counts=counts,
            moves=sum(r['moves'] for r in rows), energy_spent=sum(r['energy_spent'] for r in rows),
            reached=sum(r['status'] == 'reached' for r in rows),
            features=len(counts), feature_action_pairs=sum(sum(n > 0 for n in row) for row in counts.values()),
            features_with_one_action=sum(sum(n > 0 for n in row) == 1 for row in counts.values()),
            exploration_proposals=sum(r['exploration_proposals'] for r in rows))
        payloads[variant] = payload
    exams = {}
    for arm, payload in payloads.items():
        exams[arm] = [episode(policy.restore(payload).snapshot(), room['seed'], isolated=isolated)[0]
                      for room in rooms_e]
    manifest = inventory()
    for path in ('tests/test_transfer3_v3.py', 'docs/TRANSFER3-V3-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, isolated=isolated,
        history_sha256=sha256_bytes(history_path.read_bytes()), school_rooms=rooms_a, exam_rooms=rooms_e,
        ledger=dict(school=ledger_a, exam=ledger_e), schools=schools, payloads=payloads, exams=exams,
        totals={arm: summary(rows) for arm, rows in exams.items()},
        versus_scratch={arm: compare(exams[arm], exams['scratch']) for arm in school_v3.VARIANTS},
        versus_corrected={arm: compare(exams[arm], exams['corrected']) for arm in ('reward_only', 'coverage_only')},
        correction_vs_v2=compare(exams['corrected'], [e['result'] for e in history['episodes'] if e['arm']=='transfer']),
        transfer3_green=False, campaign_C_opened=False)


def audit(report):
    if type(report) is not dict or type(report.get('isolated')) is not bool:
        raise ValueError('report schema')
    if canonical_bytes(run(isolated=report['isolated'])) != canonical_bytes(report):
        raise ValueError('V3 report does not reconstruct')
    return dict(replay_valid=True, report_sha256=sha256_bytes(canonical_bytes(report)), transfer3_green=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'audit'])
    parser.add_argument('report', type=Path)
    parser.add_argument('--isolated', action='store_true')
    args = parser.parse_args()
    if args.command == 'audit':
        print(json.dumps(audit(loads_strict(args.report.read_bytes())), sort_keys=True))
        return
    if args.report.exists():
        raise FileExistsError('preserve public attempts')
    report = run(isolated=args.isolated)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('xb') as stream:
        stream.write(canonical_bytes(report))
    print(json.dumps(dict(totals=report['totals'],
        training={k: {f: v[f] for f in ('moves','features','feature_action_pairs','features_with_one_action')}
                  for k,v in report['schools'].items()},
        versus_corrected={k: {f:v[f] for f in ('wins','losses','ties')}
                          for k,v in report['versus_corrected'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
