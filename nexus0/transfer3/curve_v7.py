"""Coverage and representation conflict as a function of school budget.

A diagnostic curve over public rooms already used, not eight independent
candidate tests. The school loop is traced here rather than in `school_v6`
because that module is hashed into the v6 artifacts and must not change; the
identity of both schools at the shared budget is asserted, not assumed.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import policy, school_v6
from .rehearsal import ROOT, inventory
from .rehearsal_v2 import Space, episode
from .rehearsal_v3 import summary
from .rehearsal_v4 import screen, PROTOCOL as V4_PROTOCOL
from .repair_v5 import episode as repaired_episode

PROGRESS_RETURN = 7
REGRESS_RETURN = -9
PLANAR = 4

PROTOCOL = dict(version=7, scope='public-curve-not-candidate-selection',
    budgets=[128, 256, 512, 1024], exports=['baseline', 'pessimistic'],
    rooms=V4_PROTOCOL, school_reward='progress', failure_bonus=-32,
    coverage='sampled planar (feature, action) pairs',
    conflict=f'pair observing both a return >= {PROGRESS_RETURN} and <= {REGRESS_RETURN}',
    criterion='rehearsal_v4.screen unchanged',
    independent_tests=False, learning_in_exam=False, campaign_ready=False)


def train_traced(seeds, budget):
    """Same school as `school_v6.train`, keeping each learning target."""
    if type(budget) is not int or not 1 <= budget <= 4096 or not seeds:
        raise ValueError('school budget/seeds')
    payload = policy.scratch()
    counts, returns, episodes = {}, {}, []
    used = 0
    while used < budget:
        if len(episodes) > budget:
            raise ValueError('school cannot spend its budget')
        seed = seeds[len(episodes) % len(seeds)]
        world = Space(seed)
        row = repaired_episode(world, payload, learn=True, reward_kind='progress',
                               failure_bonus=PROTOCOL['failure_bonus'],
                               move_budget=min(64, budget-used))
        payload = row['payload']
        used += row['moves']
        for feature, sampled in row['counts'].items():
            total = counts.setdefault(feature, [0]*PLANAR)
            for action, n in enumerate(sampled):
                total[action] += n
        for entry in row['rows']:
            learning = entry['learning']
            action = bytes.fromhex(entry['decision']['wsp'])[13]
            observed = returns.setdefault(learning['before'], [[] for _ in range(PLANAR)])
            observed[action].append(learning['reward'])
        episodes.append(dict(seed=seed, status=row['status'], moves=row['moves'],
            failure_bonus_applied=sum(bool(r['outcome']) and r['outcome'] != 'reached'
                                      for r in row['rows'])))
    if used != budget:
        raise ValueError('school did not spend exactly its budget')
    return dict(payload=payload, counts=counts, returns=returns, moves=used,
                sim_u=used*4, episodes=episodes,
                failure_bonus_applied=sum(e['failure_bonus_applied'] for e in episodes))


def coverage(counts):
    pairs = sum(sum(n > 0 for n in row) for row in counts.values())
    return dict(features=len(counts), sampled_pairs=pairs,
                possible_pairs=PLANAR*len(counts),
                one_action_features=sum(sum(n > 0 for n in r) == 1 for r in counts.values()),
                samples=sum(sum(r) for r in counts.values()))


def conflict(returns):
    pairs, features = 0, set()
    for feature, actions in returns.items():
        for observed in actions:
            if (any(r >= PROGRESS_RETURN for r in observed) and
                    any(r <= REGRESS_RETURN for r in observed)):
                pairs += 1
                features.add(feature)
    return dict(conflicting_pairs=pairs, conflicting_features=len(features),
                observed_pairs=sum(bool(o) for a in returns.values() for o in a))


def run(*, isolated=False, progress=False):
    history_path = ROOT/'lab/transfer3/rehearsal-v4.json'
    history = loads_strict(history_path.read_bytes())
    for path, digest in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != digest:
            raise ValueError('V4 frozen source changed: '+path)
    seeds = [room['seed'] for room in history['school_rooms']]
    rooms = history['exam_rooms']
    scratch_exam = [episode(policy.restore(policy.scratch()).snapshot(), room['seed'],
                            isolated=isolated)[0] for room in rooms]
    steps = {}
    for budget in PROTOCOL['budgets']:
        school = train_traced(seeds, budget)
        if budget == V4_PROTOCOL['budget']:
            # Registered prediction 1: the traced school is the v6 school.
            if school['payload'] != school_v6.train(seeds, budget)['payload']:
                raise ValueError('traced school diverges from school_v6 at shared budget')
        payloads = dict(baseline=school['payload'],
                        pessimistic=school_v6.export_pessimistic(school['payload'],
                                                                 school['counts']))
        exams, screens = {}, {}
        for arm, payload in payloads.items():
            exams[arm] = [episode(policy.restore(payload).snapshot(), room['seed'],
                                  isolated=isolated)[0] for room in rooms]
            screens[arm] = screen(exams[arm], scratch_exam, school)
            if progress:
                print(budget, arm, screens[arm]['wins'], screens[arm]['losses'],
                      screens[arm]['development_screen_pass'], flush=True)
        steps[str(budget)] = dict(budget=budget, school=school['episodes'],
            moves=school['moves'], coverage=coverage(school['counts']),
            conflict=conflict(school['returns']),
            # A fired failure bonus would shift returns past the regress
            # threshold and contaminate the conflict count.
            failure_bonus_applied=school['failure_bonus_applied'],
            payload_rows={arm: len(p['q']) for arm, p in payloads.items()},
            payloads=payloads, exams=exams,
            totals={arm: summary(rows) for arm, rows in exams.items()},
            screens=screens)
    manifest = inventory()
    for path in ('tests/test_transfer3_v7.py', 'docs/TRANSFER3-V7-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, isolated=isolated,
        history_sha256=sha256_bytes(history_path.read_bytes()),
        school_rooms=history['school_rooms'], exam_rooms=rooms,
        scratch=dict(exams=scratch_exam, totals=summary(scratch_exam)),
        steps=steps, any_screen_passed=any(s['screens'][arm]['development_screen_pass']
                                           for s in steps.values() for arm in s['screens']),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or type(report.get('isolated')) is not bool:
        raise ValueError('report schema')
    if canonical_bytes(run(isolated=report['isolated'], progress=progress)) != canonical_bytes(report):
        raise ValueError('V7 curve does not reconstruct')
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
    print(json.dumps({budget: dict(coverage=step['coverage'], conflict=step['conflict'],
        totals=step['totals'], screens={arm: {k: v[k] for k in
            ('wins', 'losses', 'ties', 'new_failures', 'joint_success_saved_moves',
             'train_plus_exam_moves', 'development_screen_pass')}
            for arm, v in step['screens'].items()})
        for budget, step in report['steps'].items()}, sort_keys=True))


if __name__ == '__main__':
    main()
