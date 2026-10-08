"""Plan A1 development screen: does a learned cost calibration transfer?

School in A rooms, exam in disjoint public rooms with the calibration frozen.
Every arm shares the executable, sensors, planner, gates and reserve constant;
only the calibration vector differs. The oracle arm is an external ceiling and
is excluded from the pass criteria.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import calib_a1, policy
from .body_a1 import CONDITIONS, CostBody, CostSpace, min_cost_between
from .planner_a1 import CostPlanner
from .rehearsal import ROOT, inventory
from .rehearsal_v4 import significance

RESERVE = 4
SCHOOL_BUDGET = 16
EXAM_LIMIT = 65
ALPHA_DENOMINATOR = 60

PROTOCOL = dict(version='a1', scope='public-development-screen-not-campaign',
    question='does a learned movement-cost calibration lower mission energy in new rooms',
    conditions=['flat', 'turn4', 'turn8', 'skew_turn6'],
    cost_family=CONDITIONS, school_budget=SCHOOL_BUDGET,
    school_budget_rationale='four actions x (straight, turning) = 8 observations; doubled',
    reserve_constant=RESERVE, reserve_identical_in_every_arm=True,
    planner='planner_a1.CostPlanner, depth 4, budget 32, shared by every arm',
    primary_cost='simulated energy on joint successes',
    arms=['nominal', 'learned', 'permuted', 'crossed'], ceiling='oracle',
    crossed_source='skew_turn6', q_table_used=False,
    learning_in_exam=False, campaign_ready=False)


def oracle_payload(body):
    return dict(schema=calib_a1.SCHEMA, base=list(body.base), turn=body.turn,
                samples=dict(straight=[0]*4, turning=[0]*4))


def episode(seed, body, calibration, *, learning=False, limit=EXAM_LIMIT):
    world = CostSpace(seed, body)
    agent = CostPlanner(policy.restore(policy.scratch()).snapshot(), world.goal,
                        calibration, learning=learning, reserve=RESERVE)
    start_vector = agent.frozen()
    rows, violations = [], 0
    status = 'move_limit'
    for _ in range(limit):
        frame = world.scan()
        decision = agent.decide(frame)
        if decision['status'] not in ('moving', 'returning'):
            status = decision['status']
            break
        wsp = bytes.fromhex(decision['wsp'])
        if len(wsp) != 16 or wsp[1] != 11 or not 0 <= wsp[13] < 4:
            raise ValueError('planar WSP command')
        action = wsp[13]
        consequence = world.step(action)
        # Adjudicated externally with true costs, identically for every arm.
        home = min_cost_between(world, world.pos, world.start, world.last_action)
        violations += home is None or world.energy < home
        rows.append(dict(action=action, cost=consequence['cost'], energy=world.energy,
                         blocked=consequence['blocked']))
    reached = status == 'reached'
    final = world.scan()
    return dict(seed=seed, status=status, reached=reached, rows=rows,
                energy=240-world.energy, moves=world.steps, turns=world.turns,
                collisions=world.collisions, reserve_violations=violations,
                false_facts=int(reached and not (world.pos == world.goal and final['station_observed'])),
                calibration_unchanged=agent.frozen() == start_vector,
                observations=agent.observations,
                imagined_writes=agent.imagined_writes)


def school(seeds, body, budget=SCHOOL_BUDGET):
    """Spend exactly `budget` executed moves learning from observed energy."""
    if type(budget) is not int or not 1 <= budget <= 512 or not seeds:
        raise ValueError('school budget/seeds')
    calibration = calib_a1.Calibration()
    spent, episodes = 0, []
    while spent < budget:
        if len(episodes) > budget:
            raise ValueError('school cannot spend its budget')
        seed = seeds[len(episodes) % len(seeds)]
        world = CostSpace(seed, body)
        agent = CostPlanner(policy.restore(policy.scratch()).snapshot(), world.goal,
                            calibration.export(), learning=True, reserve=RESERVE)
        # Share one estimator across A episodes so evidence accumulates.
        agent.calibration = calibration
        moves = 0
        for _ in range(min(EXAM_LIMIT, budget-spent)):
            frame = world.scan()
            decision = agent.decide(frame)
            if decision['status'] not in ('moving', 'returning'):
                break
            world.step(bytes.fromhex(decision['wsp'])[13])
            moves += 1
        # One last frame so the final move's energy is observed, not discarded.
        agent.update(world.scan())
        spent += moves
        episodes.append(dict(seed=seed, moves=moves, energy=240-world.energy,
                             collisions=world.collisions))
    payload = calibration.export()
    return dict(payload=payload, moves=spent, episodes=episodes,
                energy=sum(e['energy'] for e in episodes),
                coverage=payload['samples'])


def totals(rows):
    return dict(episodes=len(rows), reached=sum(r['reached'] for r in rows),
                energy=sum(r['energy'] for r in rows), moves=sum(r['moves'] for r in rows),
                turns=sum(r['turns'] for r in rows),
                collisions=sum(r['collisions'] for r in rows),
                reserve_violations=sum(r['reserve_violations'] for r in rows),
                false_facts=sum(r['false_facts'] for r in rows),
                calibrations_unchanged=all(r['calibration_unchanged'] for r in rows))


def compare(rows, baseline):
    if [r['seed'] for r in rows] != [r['seed'] for r in baseline]:
        raise ValueError('unpaired trials')
    pairs, wins, losses = [], 0, 0
    joint = 0
    for a, b in zip(rows, baseline):
        both = a['reached'] and b['reached']
        gain = b['energy']-a['energy'] if both else 0
        joint += gain
        if both and gain > 0:
            wins += 1
        elif both and gain < 0:
            losses += 1
        pairs.append(dict(seed=a['seed'], reached=[a['reached'], b['reached']],
                          energy=[a['energy'], b['energy']], gain=gain))
    return dict(wins=wins, losses=losses, ties=len(pairs)-wins-losses, pairs=pairs,
                joint_success_energy_saved=joint,
                new_failures=sum(b['reached'] and not a['reached'] for a, b in zip(rows, baseline)),
                recovered=sum(a['reached'] and not b['reached'] for a, b in zip(rows, baseline)),
                all_case_energy_saved=sum(b['energy']-a['energy'] for a, b in zip(rows, baseline)),
                p_one_sided=significance(wins, losses))


def screen(arm_rows, nominal_rows, arm_school, versus_permuted, versus_crossed):
    result = compare(arm_rows, nominal_rows)
    total = totals(arm_rows)
    p = result['p_one_sided']
    result['school_energy'] = arm_school['energy']
    result['school_plus_exam_energy'] = arm_school['energy']+total['energy']
    result['nominal_exam_energy'] = totals(nominal_rows)['energy']
    result['amortised'] = result['school_plus_exam_energy'] < result['nominal_exam_energy']
    result['beats_permuted'] = versus_permuted['joint_success_energy_saved'] > 0
    result['beats_crossed'] = versus_crossed['joint_success_energy_saved'] > 0
    result['plan_a1_development_pass'] = bool(
        total['collisions'] == 0 and total['reserve_violations'] == 0 and
        total['false_facts'] == 0 and total['calibrations_unchanged'] and
        result['new_failures'] == 0 and result['joint_success_energy_saved'] > 0 and
        result['amortised'] and result['beats_permuted'] and result['beats_crossed'] and
        p['numerator']*ALPHA_DENOMINATOR <= p['denominator'])
    return result


def run(*, progress=False):
    history_path = ROOT/'lab/transfer3/rehearsal-v4.json'
    history = loads_strict(history_path.read_bytes())
    for path, digest in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != digest:
            raise ValueError('V4 frozen source changed: '+path)
    school_seeds = [r['seed'] for r in history['school_rooms']]
    rooms = [r['seed'] for r in history['exam_rooms']]
    campaigns = {}
    for name in PROTOCOL['conditions']:
        body = CostBody.named(name)
        taught = school(school_seeds, body)
        crossed_body = CostBody.named(PROTOCOL['crossed_source'])
        crossed = school(school_seeds, crossed_body)['payload']
        payloads = dict(nominal=calib_a1.nominal(), learned=taught['payload'],
                        permuted=calib_a1.permuted(taught['payload']), crossed=crossed,
                        oracle=oracle_payload(body))
        exams = {arm: [episode(seed, body, payload) for seed in rooms]
                 for arm, payload in payloads.items()}
        versus_permuted = compare(exams['learned'], exams['permuted'])
        versus_crossed = compare(exams['learned'], exams['crossed'])
        campaigns[name] = dict(condition=body.as_dict(), school=taught, payloads=payloads,
            calibration_error=calib_a1.error_against(taught['payload'], body),
            totals={arm: totals(rows) for arm, rows in exams.items()},
            screen=screen(exams['learned'], exams['nominal'], taught, versus_permuted, versus_crossed),
            versus_permuted=versus_permuted, versus_crossed=versus_crossed,
            versus_nominal={arm: compare(exams[arm], exams['nominal'])
                            for arm in ('learned', 'permuted', 'crossed', 'oracle')},
            exams=exams)
        if progress:
            s = campaigns[name]['screen']
            print(name, 'W/L', s['wins'], s['losses'], 'saved', s['joint_success_energy_saved'],
                  'pass', s['plan_a1_development_pass'], flush=True)
    manifest = inventory()
    for path in ('tests/test_transfer3_a1.py', 'docs/TRANSFER3-PLAN-A1-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest,
        history_sha256=sha256_bytes(history_path.read_bytes()),
        school_seeds=school_seeds, exam_seeds=rooms, campaigns=campaigns,
        any_condition_passed=any(c['screen']['plan_a1_development_pass'] for c in campaigns.values()),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or 'campaigns' not in report:
        raise ValueError('report schema')
    if canonical_bytes(run(progress=progress)) != canonical_bytes(report):
        raise ValueError('Plan A1 screen does not reconstruct')
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
    print(json.dumps({name: dict(condition=c['condition'],
        calibration=c['payloads']['learned'], error=c['calibration_error'],
        school=dict(moves=c['school']['moves'], energy=c['school']['energy'],
                    coverage=c['school']['coverage']),
        totals=c['totals'],
        screen={k: c['screen'][k] for k in ('wins', 'losses', 'ties', 'new_failures',
            'recovered', 'joint_success_energy_saved', 'school_plus_exam_energy',
            'nominal_exam_energy', 'amortised', 'beats_permuted', 'beats_crossed',
            'p_one_sided', 'plan_a1_development_pass')})
        for name, c in report['campaigns'].items()}, sort_keys=True))


if __name__ == '__main__':
    main()
