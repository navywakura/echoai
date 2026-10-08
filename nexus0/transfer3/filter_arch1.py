"""ARCH-1 filter: does plan commitment make model precision pay?

Plans A and B both found a perfectly learned body parameter to be useless. The
common explanation offered was architectural: an agent that replans from scratch
every step cannot profit from precision. This filter tests that explanation
directly, by varying only how many actions of a plan the agent commits to.

The prediction, written before running: the oracle's advantage over the nominal
arm is zero at commitment 1 and grows with commitment, because a wrong model
derails a committed plan and a right one does not. If the advantage stays flat,
the architectural explanation is wrong and gets retracted.

Filter, not a campaign: no school, no cage, no candidate, no B/C.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import costs_a2, gain_b1
from .filter_b1 import MOVE_LIMIT, RESERVE, ROOMS, ROOM_SEED
from .planner_arch1 import CommittedPlanner
from .rehearsal import ROOT, inventory
from .space_a2 import suite

COMMITMENTS = (1, 2, 3, 4, 6)

PROTOCOL = dict(version='arch1-filter', scope='pre-campaign-filter-not-a-campaign',
    question='does plan commitment make model precision pay',
    hypothesis='step-by-step replanning absorbs model error, so precision cannot pay',
    prediction='oracle advantage is zero at commitment 1 and grows with commitment',
    retraction_rule='a flat advantage retracts the architectural explanation',
    commitments=list(COMMITMENTS), conditions=gain_b1.CONDITIONS,
    rooms=ROOMS, room_seed=ROOM_SEED, reserve_constant=RESERVE,
    gates_applied_to_committed_actions=True, derailed_plans_are_abandoned=True,
    rooms_aligned=True,
    alignment_rationale='actions are world-frame, so a gain on action 0 is exercised '
                        'in only about a quarter of rotated rooms; a mechanism filter '
                        'must exercise the mechanism it is testing',
    commitment_one_reproduces_history=True,
    isolated=False, school=False, campaign_ready=False)


def episode(seed, gains, believed, commitment):
    room = gain_b1.GainRoom(seed, gain_b1.declared_body(), gains, aligned=True)
    agent = CommittedPlanner(gain_b1.programmed(believed), room.goal,
                             costs_a2.nominal(), reserve=RESERVE, commitment=commitment)
    status, decision = 'move_limit', None
    for _ in range(MOVE_LIMIT):
        decision = agent.decide(room.scan())
        if decision['status'] not in ('moving', 'returning'):
            status = decision['status']
            break
        room.step(bytes.fromhex(decision['wsp'])[13])
    return dict(seed=seed, reached=status == 'reached', energy=240-room.energy,
                moves=room.steps, collisions=room.collisions,
                prediction_errors=decision['prediction_errors'],
                commitments_kept=agent.commitments_kept,
                commitments_derailed=agent.commitments_derailed)


def totals(rows):
    return dict(episodes=len(rows), reached=sum(r['reached'] for r in rows),
                energy=sum(r['energy'] for r in rows),
                collisions=sum(r['collisions'] for r in rows),
                prediction_errors=sum(r['prediction_errors'] for r in rows),
                commitments_kept=sum(r['commitments_kept'] for r in rows),
                commitments_derailed=sum(r['commitments_derailed'] for r in rows))


def run(*, progress=False):
    rooms, ledger = suite(ROOM_SEED, ROOMS, [], gain_b1.declared_body())
    seeds = [r['seed'] for r in rooms]
    grid = {}
    for name, gains in gain_b1.CONDITIONS.items():
        beliefs = dict(nominal=(1, 1, 1, 1), oracle=tuple(gains))
        steps = {}
        for commitment in COMMITMENTS:
            arms = {label: totals([episode(s, gains, believed, commitment) for s in seeds])
                    for label, believed in beliefs.items()}
            steps[str(commitment)] = dict(commitment=commitment, arms=arms,
                missions_delta=arms['oracle']['reached']-arms['nominal']['reached'],
                energy_delta=arms['oracle']['energy']-arms['nominal']['energy'],
                oracle_beats_nominal=bool(arms['oracle']['reached'] > arms['nominal']['reached']
                                          or (arms['oracle']['reached'] == arms['nominal']['reached']
                                              and arms['oracle']['energy'] < arms['nominal']['energy'])))
            if progress:
                print(name, 'commitment', commitment, 'missions delta',
                      steps[str(commitment)]['missions_delta'], flush=True)
        deltas = [steps[str(c)]['missions_delta'] for c in COMMITMENTS]
        grid[name] = dict(gains=list(gains), steps=steps, missions_delta_by_commitment=deltas,
                          advantage_grows=deltas[-1] > deltas[0])
    non_trivial = [n for n, g in gain_b1.CONDITIONS.items() if max(g) > 1]
    manifest = inventory()
    for path in ('tests/test_transfer3_arch1.py', 'docs/TRANSFER3-ARCH1-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, rooms=rooms, ledger=ledger,
        conditions=grid,
        commitment_helps=any(grid[n]['advantage_grows'] for n in non_trivial),
        any_commitment_wins=any(grid[n]['steps'][str(c)]['oracle_beats_nominal']
                                for n in non_trivial for c in COMMITMENTS),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or 'commitment_helps' not in report:
        raise ValueError('report schema')
    if canonical_bytes(run(progress=progress)) != canonical_bytes(report):
        raise ValueError('ARCH-1 filter does not reconstruct')
    return dict(replay_valid=True, report_sha256=sha256_bytes(canonical_bytes(report)),
                transfer3_green=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'audit'])
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    if args.command == 'audit':
        print(json.dumps(audit(loads_strict(args.report.read_bytes()), progress=True), sort_keys=True))
        return
    if args.report.exists():
        raise FileExistsError('preserve every public attempt')
    report = run(progress=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('xb') as stream:
        stream.write(canonical_bytes(report))
    print(json.dumps(dict(commitment_helps=report['commitment_helps'],
        any_commitment_wins=report['any_commitment_wins'],
        conditions={n: dict(gains=c['gains'],
            missions_delta_by_commitment=c['missions_delta_by_commitment'],
            steps={k: dict(missions=[v['arms']['oracle']['reached'], v['arms']['nominal']['reached']],
                           energy=[v['arms']['oracle']['energy'], v['arms']['nominal']['energy']],
                           kept=[v['arms']['oracle']['commitments_kept'], v['arms']['nominal']['commitments_kept']],
                           derailed=[v['arms']['oracle']['commitments_derailed'], v['arms']['nominal']['commitments_derailed']])
                   for k, v in c['steps'].items()})
            for n, c in report['conditions'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
