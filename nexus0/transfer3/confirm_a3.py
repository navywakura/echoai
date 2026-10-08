"""Plan A3: does a learned cost parameter complete more missions in new rooms?

Second primary endpoint tried on this mechanism; the contract says so in its
first paragraph and so does this docstring. Rooms are fresh, the statistic is
McNemar's exact test on discordant pairs, and two programmer-set `guessed` arms
exist so the report can say whether learning beat a hand-set prior.
"""
import argparse
import json
from math import comb
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import costs_a2, policy, space_a2
from .confirm_a2 import MOVE_LIMIT, totals
from .planner_a2 import CostPlanner
from .rehearsal import ROOT, inventory
from .transport_a2 import CagedPlanner

RESERVE = 6
SCHOOL_BUDGET = 16
SCHOOL_SEED = 20265501
EXAM_SEED = 20266001
CONTROL_SEED = 20267001
SCHOOL_ROOMS = 8
EXAM_ROOMS = 256
CONTROL_ROOMS = 64
ALPHA_DENOMINATOR = 240
GUESSES = dict(guessed_low=2, guessed_high=8)

PROTOCOL = dict(version='a3', scope='public-prospective-confirmation-not-campaign',
    question='does a learned cost parameter complete more missions in new rooms',
    second_primary_endpoint_on_this_mechanism=True,
    primary_endpoint='paired mission completions, McNemar exact one-sided',
    reserve_constant=RESERVE,
    reserve_chosen_with='nominal arm only, on rooms already spent in A2',
    school_seed=SCHOOL_SEED, school_rooms=SCHOOL_ROOMS, school_budget=SCHOOL_BUDGET,
    exam_seed=EXAM_SEED, exam_rooms=EXAM_ROOMS,
    control_seed=CONTROL_SEED, control_rooms=CONTROL_ROOMS,
    condition=dict(base=(4, 4, 4, 4), turn=4),
    control_condition=dict(base=(4, 4, 4, 4), turn=0),
    arms=['nominal', 'learned']+sorted(GUESSES), guesses=GUESSES,
    guess_interpretation_rule='if learned beats neither guess, the report must state '
                              'that the transferred content is a programmer prior',
    negative_control_is_tautological_for_this_candidate=True,
    alpha_denominator=ALPHA_DENOMINATOR, isolated=True,
    learning_in_exam=False, campaign_ready=False)


def school(seeds, body, budget=SCHOOL_BUDGET):
    """A1's school with A3's reserve. A2 is frozen, so its constant is not reused."""
    calibration = costs_a2.Calibration()
    spent, episodes = 0, []
    while spent < budget:
        if len(episodes) > budget:
            raise ValueError('school cannot spend its budget')
        seed = seeds[len(episodes) % len(seeds)]
        room = space_a2.Room(seed, body)
        agent = CostPlanner(policy.restore(policy.scratch()).snapshot(), room.goal,
                            calibration.export(), learning=True, reserve=RESERVE)
        agent.calibration = calibration
        moves = 0
        for _ in range(min(MOVE_LIMIT, budget-spent)):
            decision = agent.decide(room.scan())
            if decision['status'] not in ('moving', 'returning'):
                break
            room.step(bytes.fromhex(decision['wsp'])[13])
            moves += 1
        agent.update(room.scan())
        spent += moves
        episodes.append(dict(seed=seed, moves=moves, energy=space_a2.ENERGY-room.energy,
                             collisions=room.collisions))
    payload = calibration.export()
    return dict(payload=payload, moves=spent, episodes=episodes,
                energy=sum(e['energy'] for e in episodes), coverage=payload['samples'])


def episode(seed, body, calibration):
    room = space_a2.Room(seed, body)
    agent = CagedPlanner(policy.restore(policy.scratch()).snapshot(), room.goal,
                         calibration, reserve=RESERVE)
    try:
        baseline = agent.ready['calibration']
        violations, status, imagined = 0, 'move_limit', 0
        for _ in range(MOVE_LIMIT):
            decision = agent.call(room.scan())
            imagined = max(imagined, decision['imagined_writes'])
            if decision['status'] not in ('moving', 'returning'):
                status = decision['status']
                break
            wsp = bytes.fromhex(decision['wsp'])
            if len(wsp) != 16 or wsp[1] != 11 or not 0 <= wsp[13] < 4:
                raise ValueError('planar WSP command')
            room.step(wsp[13])
            home = space_a2.min_cost_between(room, room.pos, room.start, room.last_action)
            violations += home is None or room.energy < home
        final = agent.frozen_check()
        reached = status == 'reached'
        observed = room.scan()
        return dict(seed=seed, status=status, reached=reached,
                    energy=space_a2.ENERGY-room.energy, moves=room.steps, turns=room.turns,
                    collisions=room.collisions, reserve_violations=violations,
                    false_facts=int(reached and not (room.pos == room.goal
                                                     and observed['station_observed'])),
                    calibration_unchanged=final['calibration'] == baseline,
                    imagined_writes=imagined)
    finally:
        agent.close()


def mcnemar(rows, baseline):
    """Exact one-sided test on discordant pairs. Ties carry no information."""
    if [r['seed'] for r in rows] != [r['seed'] for r in baseline]:
        raise ValueError('unpaired trials')
    gained = sum(a['reached'] and not b['reached'] for a, b in zip(rows, baseline))
    lost = sum(b['reached'] and not a['reached'] for a, b in zip(rows, baseline))
    n = gained+lost
    return dict(gained=gained, lost=lost, discordant=n,
                reached=[sum(r['reached'] for r in rows), sum(r['reached'] for r in baseline)],
                p_one_sided=dict(numerator=sum(comb(n, k) for k in range(gained, n+1)),
                                 denominator=2**n))


def guessed(turn):
    return costs_a2.validate(dict(costs_a2.nominal(), turn=turn))


def judge(primary, control, taught, arm_totals, nominal_totals, versus_guesses):
    p = primary['p_one_sided']
    result = dict(
        hard_constraints=bool(arm_totals['collisions'] == 0 and
                              arm_totals['reserve_violations'] == 0 and
                              arm_totals['false_facts'] == 0 and
                              arm_totals['imagined_writes'] == 0 and
                              arm_totals['calibrations_unchanged']),
        more_missions=primary['reached'][0] > primary['reached'][1],
        significant=p['numerator']*ALPHA_DENOMINATOR <= p['denominator'],
        energy_not_worse=taught['energy']+arm_totals['energy'] <= nominal_totals['energy'],
        negative_control_clean=control['gained'] <= control['lost'],
        school_plus_exam_energy=taught['energy']+arm_totals['energy'],
        nominal_exam_energy=nominal_totals['energy'],
        beats_a_hand_set_prior={name: versus['gained'] > versus['lost']
                                for name, versus in versus_guesses.items()})
    result['learning_beyond_a_prior'] = any(result['beats_a_hand_set_prior'].values())
    result['plan_a3_confirmation_pass'] = all(
        result[k] for k in ('hard_constraints', 'more_missions', 'significant',
                            'energy_not_worse', 'negative_control_clean'))
    return result


def run(*, progress=False):
    spent = []
    for name in ('rehearsal-v4', 'rooms-v8', 'plan-a2-confirmation'):
        report = loads_strict((ROOT/f'lab/transfer3/{name}.json').read_bytes())
        for key in ('school_rooms', 'exam_rooms', 'excluded_rooms', 'new_rooms'):
            spent += [r['shape'] for r in report.get(key, [])]
    spent = sorted(set(spent))
    school_rooms, school_ledger = space_a2.suite(SCHOOL_SEED, SCHOOL_ROOMS, spent)
    taken = spent+[r['shape'] for r in school_rooms]
    exam_rooms, exam_ledger = space_a2.suite(EXAM_SEED, EXAM_ROOMS, taken)
    taken += [r['shape'] for r in exam_rooms]
    control_rooms, control_ledger = space_a2.suite(CONTROL_SEED, CONTROL_ROOMS, taken)
    seeds = [r['seed'] for r in school_rooms]

    body = space_a2.Body(**PROTOCOL['condition'])
    taught = school(seeds, body, SCHOOL_BUDGET)
    payloads = dict(nominal=costs_a2.nominal(),
                    learned=costs_a2.turn_only(taught['payload']),
                    **{name: guessed(turn) for name, turn in GUESSES.items()})
    exams = {}
    for arm, payload in payloads.items():
        exams[arm] = []
        for i, room in enumerate(exam_rooms):
            exams[arm].append(episode(room['seed'], body, payload))
            if progress and (i+1) % 64 == 0:
                print('primary', arm, i+1, '/', len(exam_rooms), flush=True)

    control_body = space_a2.Body(**PROTOCOL['control_condition'])
    control_taught = school(seeds, control_body, SCHOOL_BUDGET)
    control_payloads = dict(nominal=costs_a2.nominal(),
                            learned=costs_a2.turn_only(control_taught['payload']))
    control_exams = {arm: [episode(r['seed'], control_body, payload) for r in control_rooms]
                     for arm, payload in control_payloads.items()}

    primary = mcnemar(exams['learned'], exams['nominal'])
    control = mcnemar(control_exams['learned'], control_exams['nominal'])
    versus_guesses = {name: mcnemar(exams['learned'], exams[name]) for name in GUESSES}
    verdict = judge(primary, control, taught, totals(exams['learned']),
                    totals(exams['nominal']), versus_guesses)
    manifest = inventory()
    for path in ('tests/test_transfer3_a3.py', 'docs/TRANSFER3-PLAN-A3-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest, spent_public_shapes=len(spent),
        school_rooms=school_rooms, exam_rooms=exam_rooms, control_rooms=control_rooms,
        ledger=dict(school=school_ledger, exam=exam_ledger, control=control_ledger),
        school=taught, control_school=control_taught, payloads=payloads,
        totals={arm: totals(rows) for arm, rows in exams.items()},
        control_totals={arm: totals(rows) for arm, rows in control_exams.items()},
        primary=primary, negative_control=control, versus_guesses=versus_guesses,
        verdict=verdict, exams=exams, control_exams=control_exams,
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or 'verdict' not in report:
        raise ValueError('report schema')
    if canonical_bytes(run(progress=progress)) != canonical_bytes(report):
        raise ValueError('Plan A3 confirmation does not reconstruct')
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
    print(json.dumps(dict(verdict=report['verdict'], primary=report['primary'],
        negative_control=report['negative_control'],
        versus_guesses=report['versus_guesses'],
        learned_calibration=report['payloads']['learned'],
        totals={a: {k: t[k] for k in ('reached', 'energy', 'turns', 'reserve_violations')}
                for a, t in report['totals'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
