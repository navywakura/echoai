"""Plan A2: prospective public confirmation of the frozen turn-only candidate.

Rooms come from the two-wall generator, disjoint from every public shape spent
so far and from the school. The exam runs in the cage, so the agent cannot read
geometry, seeds or the evaluator's cost table. The candidate is frozen before
the exam rooms are drawn and never touched again.

This is level 2 of the contract — a prospective public confirmation. It is not
the sealed A→B→C campaign and cannot set `transfer3_green`.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import costs_a2, policy, space_a2
from .planner_a2 import CostPlanner
from .rehearsal import ROOT, inventory
from .rehearsal_v4 import significance
from .transport_a2 import CagedPlanner

RESERVE = costs_a2.RESERVE_DEFAULT
SCHOOL_BUDGET = 16
SCHOOL_SEED = 20264801
EXAM_SEED = 20265001
SCHOOL_ROOMS = 8
EXAM_ROOMS = 128
MOVE_LIMIT = 65
ALPHA_DENOMINATOR = 240

CONDITIONS = dict(primary=dict(base=(4, 4, 4, 4), turn=4),
                  negative_control=dict(base=(4, 4, 4, 4), turn=0))

PROTOCOL = dict(version='a2', scope='public-prospective-confirmation-not-campaign',
    candidate='turn_only: learn the turn term, keep the nominal base',
    # Both the candidate form and the room seeds are fixed in the contract
    # before execution, so neither is chosen after seeing an exam.
    candidate_form_declared_before_execution=True,
    room_seeds_declared_before_execution=True,
    generator='space_a2 two-wall rooms; 11638 canonical shapes, zero overlap with spent',
    school_seed=SCHOOL_SEED, school_rooms=SCHOOL_ROOMS, school_budget=SCHOOL_BUDGET,
    exam_seed=EXAM_SEED, exam_rooms=EXAM_ROOMS, isolated=True,
    conditions=CONDITIONS, arms=['nominal', 'candidate'],
    reserve_constant=RESERVE, reserve_identical_in_every_arm=True,
    primary_cost='simulated energy on joint successes',
    alpha_denominator=ALPHA_DENOMINATOR,
    alpha_rationale='kept at the A1 v2 Bonferroni level although one primary endpoint '
                    'would not require it, so the threshold never loosens',
    negative_control_rule='a gain under turn 0 invalidates the run whatever the primary says',
    learning_in_exam=False, campaign_ready=False)


def school(seeds, body, budget=SCHOOL_BUDGET):
    """Learn from observed energy only. Local, uncaged, and reported in full."""
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
        violations, status = 0, 'move_limit'
        imagined = 0
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


def totals(rows):
    return dict(episodes=len(rows), reached=sum(r['reached'] for r in rows),
                energy=sum(r['energy'] for r in rows), moves=sum(r['moves'] for r in rows),
                turns=sum(r['turns'] for r in rows),
                collisions=sum(r['collisions'] for r in rows),
                reserve_violations=sum(r['reserve_violations'] for r in rows),
                false_facts=sum(r['false_facts'] for r in rows),
                imagined_writes=sum(r['imagined_writes'] for r in rows),
                calibrations_unchanged=all(r['calibration_unchanged'] for r in rows))


def compare(rows, baseline):
    if [r['seed'] for r in rows] != [r['seed'] for r in baseline]:
        raise ValueError('unpaired trials')
    wins = losses = joint = 0
    pairs = []
    for a, b in zip(rows, baseline):
        both = a['reached'] and b['reached']
        gain = b['energy']-a['energy'] if both else 0
        joint += gain
        wins += both and gain > 0
        losses += both and gain < 0
        pairs.append(dict(seed=a['seed'], reached=[a['reached'], b['reached']],
                          energy=[a['energy'], b['energy']], gain=gain))
    return dict(wins=wins, losses=losses, ties=len(pairs)-wins-losses, pairs=pairs,
                joint_success_energy_saved=joint,
                new_failures=sum(b['reached'] and not a['reached'] for a, b in zip(rows, baseline)),
                recovered=sum(a['reached'] and not b['reached'] for a, b in zip(rows, baseline)),
                all_case_energy_saved=sum(b['energy']-a['energy'] for a, b in zip(rows, baseline)),
                p_one_sided=significance(wins, losses))


def judge(primary, control, taught, nominal_totals, candidate_totals):
    p = primary['p_one_sided']
    control_clean = control['joint_success_energy_saved'] <= 0
    result = dict(
        hard_constraints=bool(candidate_totals['collisions'] == 0 and
                              candidate_totals['reserve_violations'] == 0 and
                              candidate_totals['false_facts'] == 0 and
                              candidate_totals['imagined_writes'] == 0 and
                              candidate_totals['calibrations_unchanged']),
        no_new_failures=primary['new_failures'] == 0,
        saves_energy=primary['joint_success_energy_saved'] > 0,
        amortised=taught['energy']+candidate_totals['energy'] < nominal_totals['energy'],
        negative_control_clean=control_clean,
        significant=p['numerator']*ALPHA_DENOMINATOR <= p['denominator'],
        school_plus_exam_energy=taught['energy']+candidate_totals['energy'],
        nominal_exam_energy=nominal_totals['energy'])
    result['plan_a2_confirmation_pass'] = all(
        result[k] for k in ('hard_constraints', 'no_new_failures', 'saves_energy',
                            'amortised', 'negative_control_clean', 'significant'))
    return result


def run(*, progress=False):
    history = loads_strict((ROOT/'lab/transfer3/rehearsal-v4.json').read_bytes())
    v8 = loads_strict((ROOT/'lab/transfer3/rooms-v8.json').read_bytes())
    spent = [r['shape'] for r in history['school_rooms']+history['exam_rooms']
             + history['excluded_rooms']]+[r['shape'] for r in v8['new_rooms']]
    school_rooms, school_ledger = space_a2.suite(SCHOOL_SEED, SCHOOL_ROOMS, spent)
    exam_rooms, exam_ledger = space_a2.suite(
        EXAM_SEED, EXAM_ROOMS, spent+[r['shape'] for r in school_rooms])
    school_seeds = [r['seed'] for r in school_rooms]
    campaigns = {}
    for name, spec in CONDITIONS.items():
        body = space_a2.Body(**spec)
        taught = school(school_seeds, body)
        candidate = costs_a2.turn_only(taught['payload'])
        payloads = dict(nominal=costs_a2.nominal(), candidate=candidate)
        exams = {}
        for arm, payload in payloads.items():
            exams[arm] = []
            for i, room in enumerate(exam_rooms):
                exams[arm].append(episode(room['seed'], body, payload))
                if progress and (i+1) % 32 == 0:
                    print(name, arm, i+1, '/', len(exam_rooms), flush=True)
        campaigns[name] = dict(condition=body.as_dict(), school=taught,
            learned=taught['payload'], candidate=candidate,
            totals={arm: totals(rows) for arm, rows in exams.items()},
            versus_nominal=compare(exams['candidate'], exams['nominal']), exams=exams)
    verdict = judge(campaigns['primary']['versus_nominal'],
                    campaigns['negative_control']['versus_nominal'],
                    campaigns['primary']['school'],
                    campaigns['primary']['totals']['nominal'],
                    campaigns['primary']['totals']['candidate'])
    manifest = inventory()
    for path in ('tests/test_transfer3_a2.py', 'docs/TRANSFER3-PLAN-A2-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest,
        spent_public_shapes=len(set(spent)),
        school_rooms=school_rooms, exam_rooms=exam_rooms,
        ledger=dict(school=school_ledger, exam=exam_ledger),
        campaigns=campaigns, verdict=verdict,
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or 'verdict' not in report:
        raise ValueError('report schema')
    if canonical_bytes(run(progress=progress)) != canonical_bytes(report):
        raise ValueError('Plan A2 confirmation does not reconstruct')
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
    print(json.dumps(dict(verdict=report['verdict'],
        campaigns={name: dict(condition=c['condition'], candidate=c['candidate'],
            totals=c['totals'],
            versus_nominal={k: c['versus_nominal'][k] for k in
                            ('wins', 'losses', 'ties', 'new_failures', 'recovered',
                             'joint_success_energy_saved', 'p_one_sided')})
            for name, c in report['campaigns'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
