"""Room diversity at fixed school budget. One factor: how many distinct rooms.

Nested room sets, so the smallest arm is also the replication control. Consumes
public canonical shapes, which the design document declares and the report
counts.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import policy, school_v6
from .curve_v7 import coverage, conflict, train_traced
from .rehearsal import ROOT, inventory
from .rehearsal_v2 import suite, episode
from .rehearsal_v3 import summary
from .rehearsal_v4 import screen, PROTOCOL as V4_PROTOCOL

NEW_ROOM_SEED = 20264701

PROTOCOL = dict(version=8, scope='public-diversity-not-candidate-selection',
    budget=V4_PROTOCOL['budget'], room_counts=[4, 8, 12], nested_rooms=True,
    new_room_seed=NEW_ROOM_SEED, exports=['baseline', 'pessimistic'],
    rooms=V4_PROTOCOL, school_reward='progress', failure_bonus=-32,
    criterion='rehearsal_v4.screen unchanged',
    independent_tests=False, learning_in_exam=False, campaign_ready=False)


def run(*, isolated=False, progress=False):
    history_path = ROOT/'lab/transfer3/rehearsal-v4.json'
    history = loads_strict(history_path.read_bytes())
    for path, digest in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != digest:
            raise ValueError('V4 frozen source changed: '+path)
    base = history['school_rooms']
    rooms = history['exam_rooms']
    spent = [r['shape'] for r in base+rooms+history['excluded_rooms']]
    extra, ledger = suite(NEW_ROOM_SEED, max(PROTOCOL['room_counts'])-len(base), spent)
    pool = [dict(seed=r['seed'], shape=r['shape']) for r in base]+extra
    if len({r['shape'] for r in pool}) != len(pool):
        raise ValueError('nested school sets must stay shape-disjoint')
    scratch_exam = [episode(policy.restore(policy.scratch()).snapshot(), room['seed'],
                            isolated=isolated)[0] for room in rooms]
    steps = {}
    for count in PROTOCOL['room_counts']:
        seeds = [r['seed'] for r in pool[:count]]
        traced = train_traced(seeds, PROTOCOL['budget'])
        school = school_v6.train(seeds, PROTOCOL['budget'])
        if school['payload'] != traced['payload']:
            raise ValueError('traced and plain schools diverge')
        payloads = dict(baseline=school['payload'],
                        pessimistic=school_v6.export_pessimistic(school['payload'],
                                                                 school['counts']))
        exams, screens = {}, {}
        for arm, payload in payloads.items():
            exams[arm] = [episode(policy.restore(payload).snapshot(), room['seed'],
                                  isolated=isolated)[0] for room in rooms]
            screens[arm] = screen(exams[arm], scratch_exam, school)
            if progress:
                print(count, arm, screens[arm]['wins'], screens[arm]['losses'],
                      screens[arm]['development_screen_pass'], flush=True)
        steps[str(count)] = dict(room_count=count, school_seeds=seeds,
            school=school['episodes'], moves=school['moves'],
            coverage=coverage(school['counts']), conflict=conflict(traced['returns']),
            failure_bonus_applied=school['failure_bonus_applied'],
            payload_rows={arm: len(p['q']) for arm, p in payloads.items()},
            payloads=payloads, exams=exams,
            totals={arm: summary(rows) for arm, rows in exams.items()},
            screens=screens)
    manifest = inventory()
    for path in ('tests/test_transfer3_v8.py', 'docs/TRANSFER3-V8-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, isolated=isolated,
        history_sha256=sha256_bytes(history_path.read_bytes()),
        exam_rooms=rooms, school_pool=pool, new_rooms=extra, ledger=ledger,
        public_shapes_spent_before=len(set(spent)),
        public_shapes_spent_by_this_run=len(extra),
        scratch=dict(exams=scratch_exam, totals=summary(scratch_exam)), steps=steps,
        any_screen_passed=any(s['screens'][arm]['development_screen_pass']
                              for s in steps.values() for arm in s['screens']),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or type(report.get('isolated')) is not bool:
        raise ValueError('report schema')
    if canonical_bytes(run(isolated=report['isolated'], progress=progress)) != canonical_bytes(report):
        raise ValueError('V8 diversity run does not reconstruct')
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
    print(json.dumps(dict(spent=report['public_shapes_spent_by_this_run'],
        scratch=report['scratch']['totals'],
        steps={count: dict(coverage=step['coverage'], conflict=step['conflict'],
            totals=step['totals'], screens={arm: {k: v[k] for k in
                ('wins', 'losses', 'ties', 'new_failures', 'joint_success_saved_moves',
                 'train_plus_exam_moves', 'development_screen_pass')}
                for arm, v in step['screens'].items()})
            for count, step in report['steps'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
