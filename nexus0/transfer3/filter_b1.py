"""Plan B1 pre-campaign filter: can the planner profit from a calibrated body?

Applies the rule Plan A left behind — before spending a campaign measuring a
parameter, check that the planner can use its precision and not only its sign.
This is a filter, not a campaign: no cage, no school, no candidate, no B/C. The
`oracle` arm is handed the true gains directly, so it is an upper bound on any
learner; if it cannot beat the nominal arm, no learner can.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import costs_a2, gain_b1
from .planner_b1 import GainPlanner
from .rehearsal import ROOT, inventory
from .space_a2 import suite

RESERVE = 6
ROOM_SEED = 20268001
ROOMS = 24
MOVE_LIMIT = 65

PROTOCOL = dict(version='b1-filter', scope='pre-campaign-filter-not-a-campaign',
    question='does knowing the true actuation gain improve missions at all',
    conditions=gain_b1.CONDITIONS, reserve_constant=RESERVE,
    beliefs='nominal, oracle, and oracle off by plus or minus one',
    oracle_is_an_upper_bound_on_any_learner=True,
    rooms=ROOMS, room_seed=ROOM_SEED, isolated=False, school=False,
    go_rule='oracle must beat nominal on missions and energy in at least one '
            'non-trivial condition, otherwise the plan is dropped before a campaign',
    campaign_ready=False)


def episode(seed, gains, believed, reserve=RESERVE):
    body = gain_b1.declared_body()
    room = gain_b1.GainRoom(seed, body, gains)
    agent = GainPlanner(gain_b1.programmed(believed), room.goal,
                        costs_a2.nominal(), reserve=reserve)
    status = 'move_limit'
    decision = None
    for _ in range(MOVE_LIMIT):
        decision = agent.decide(room.scan())
        if decision['status'] not in ('moving', 'returning'):
            status = decision['status']
            break
        room.step(bytes.fromhex(decision['wsp'])[13])
    return dict(seed=seed, status=status, reached=status == 'reached',
                energy=240-room.energy, moves=room.steps, collisions=room.collisions,
                prediction_errors=decision['prediction_errors'],
                believed_reach=agent.believed_reach())


def beliefs_for(gains):
    top = gains[0]
    return dict(nominal=(1, 1, 1, 1), oracle=tuple(gains),
                over=(min(gain_b1.GAIN_RANGE[1], top+1), 1, 1, 1),
                under=(max(1, top-1), 1, 1, 1))


def totals(rows):
    return dict(episodes=len(rows), reached=sum(r['reached'] for r in rows),
                energy=sum(r['energy'] for r in rows),
                collisions=sum(r['collisions'] for r in rows),
                prediction_errors=sum(r['prediction_errors'] for r in rows))


def run(*, progress=False):
    rooms, ledger = suite(ROOM_SEED, ROOMS, [], gain_b1.declared_body())
    seeds = [r['seed'] for r in rooms]
    conditions = {}
    for name, gains in gain_b1.CONDITIONS.items():
        arms = {}
        for label, believed in beliefs_for(gains).items():
            arms[label] = dict(believed=list(believed),
                               totals=totals([episode(s, gains, believed) for s in seeds]))
        nominal, oracle = arms['nominal']['totals'], arms['oracle']['totals']
        conditions[name] = dict(gains=list(gains), arms=arms,
            oracle_beats_nominal=bool(oracle['reached'] > nominal['reached'] and
                                      oracle['energy'] < nominal['energy']),
            oracle_missions_delta=oracle['reached']-nominal['reached'],
            oracle_energy_delta=oracle['energy']-nominal['energy'])
        if progress:
            print(name, gains, 'oracle beats nominal:',
                  conditions[name]['oracle_beats_nominal'], flush=True)
    non_trivial = [n for n, g in gain_b1.CONDITIONS.items() if max(g) > 1]
    manifest = inventory()
    # Unconditional: a manifest that silently skips a missing file makes the
    # artifact un-auditable the moment that file appears.
    for path in ('tests/test_transfer3_b1.py', 'docs/TRANSFER3-PLAN-B1-FILTER.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, rooms=rooms, ledger=ledger,
        conditions=conditions,
        passes_filter=any(conditions[n]['oracle_beats_nominal'] for n in non_trivial),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or 'passes_filter' not in report:
        raise ValueError('report schema')
    if canonical_bytes(run(progress=progress)) != canonical_bytes(report):
        raise ValueError('Plan B1 filter does not reconstruct')
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
    print(json.dumps(dict(passes_filter=report['passes_filter'],
        conditions={n: dict(gains=c['gains'], oracle_beats_nominal=c['oracle_beats_nominal'],
                            missions_delta=c['oracle_missions_delta'],
                            energy_delta=c['oracle_energy_delta'],
                            arms={a: v['totals'] for a, v in c['arms'].items()})
                    for n, c in report['conditions'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
