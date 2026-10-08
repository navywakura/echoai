"""Public v6 screening: one budgeted school, two exports, frozen v4 criterion.

Not a campaign and not B/C. The rooms, the budget and the pass criterion are
taken from the v4 report and its module without modification, so the only thing
this run varies is how unsampled planar actions are transferred.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import policy, school_v6
from .rehearsal import ROOT, inventory
from .rehearsal_v2 import episode
from .rehearsal_v3 import summary
from .rehearsal_v4 import screen, PROTOCOL as V4_PROTOCOL

PROTOCOL = dict(version=6, scope='public-screening-not-campaign',
    budget=V4_PROTOCOL['budget'], rooms=V4_PROTOCOL,
    arms=['scratch', 'baseline', 'pessimistic'],
    factor='transfer of unsampled planar actions',
    floor='per-row min(sampled)-1, clamped at -127',
    school='repair_v5: real terminality, one scan per timestamp, checked CAM',
    school_reward='progress', failure_bonus=-32,
    replication_target='v4 corrected screen',
    criterion='rehearsal_v4.screen unchanged',
    learning_in_exam=False, campaign_ready=False)


def run(*, isolated=False, progress=False):
    history_path = ROOT/'lab/transfer3/rehearsal-v4.json'
    history = loads_strict(history_path.read_bytes())
    for path, digest in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != digest:
            raise ValueError('V4 frozen source changed: '+path)
    seeds = [room['seed'] for room in history['school_rooms']]
    rooms = history['exam_rooms']
    school = school_v6.train(seeds, PROTOCOL['budget'])
    payloads = dict(scratch=policy.scratch(), baseline=school['payload'],
                    pessimistic=school_v6.export_pessimistic(school['payload'],
                                                             school['counts']))
    exams = {}
    for arm, payload in payloads.items():
        exams[arm] = []
        for i, room in enumerate(rooms):
            exams[arm].append(episode(policy.restore(payload).snapshot(),
                                      room['seed'], isolated=isolated)[0])
            if progress and (i+1) % 16 == 0:
                print(arm, i+1, '/', len(rooms), flush=True)
    screens = {arm: screen(exams[arm], exams['scratch'], school)
               for arm in ('baseline', 'pessimistic')}
    # The registered prediction: the v5 repairs must not move these rooms.
    target = history['screens']['corrected']
    replication = {key: [screens['baseline'][key], target[key]]
                   for key in ('wins', 'losses', 'ties', 'new_failures',
                               'joint_success_saved_moves')}
    manifest = inventory()
    for path in ('tests/test_transfer3_v6.py', 'docs/TRANSFER3-V6-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, isolated=isolated,
        history_sha256=sha256_bytes(history_path.read_bytes()),
        school_rooms=history['school_rooms'], exam_rooms=rooms, school=school,
        payload_rows={arm: len(p['q']) for arm, p in payloads.items()},
        payloads=payloads, exams=exams,
        totals={arm: summary(rows) for arm, rows in exams.items()},
        screens=screens, replication=replication,
        baseline_replicates_v4=all(a == b for a, b in replication.values()),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or type(report.get('isolated')) is not bool:
        raise ValueError('report schema')
    if canonical_bytes(run(isolated=report['isolated'], progress=progress)) != canonical_bytes(report):
        raise ValueError('V6 screening does not reconstruct')
    return dict(replay_valid=True, report_sha256=sha256_bytes(canonical_bytes(report)),
                transfer3_green=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'audit'])
    parser.add_argument('report', type=Path)
    parser.add_argument('--isolated', action='store_true')
    args = parser.parse_args()
    if args.command == 'audit':
        print(json.dumps(audit(loads_strict(args.report.read_bytes()), progress=True), sort_keys=True))
        return
    if args.report.exists():
        raise FileExistsError('preserve every public attempt')
    report = run(isolated=args.isolated, progress=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('xb') as stream:
        stream.write(canonical_bytes(report))
    print(json.dumps(dict(
        baseline_replicates_v4=report['baseline_replicates_v4'],
        replication=report['replication'], payload_rows=report['payload_rows'],
        school={k: report['school'][k] for k in
                ('moves', 'features', 'feature_action_pairs', 'terminal_updates',
                 'failure_bonus_applied')},
        totals=report['totals'],
        screens={arm: {k: v[k] for k in ('wins', 'losses', 'ties', 'new_failures',
                                         'joint_success_saved_moves',
                                         'train_plus_exam_moves', 'p_one_sided',
                                         'development_screen_pass')}
                 for arm, v in report['screens'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
