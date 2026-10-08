"""Plan A1 v2: the two degenerate controls of A1, replaced.

A1 is frozen and not imported for its criteria, only for its episode, school and
comparison machinery, which the amendment does not change. What changes is which
arms count as controls and the significance threshold, both declared beforehand
in TRANSFER3-PLAN-A1-V2-DESIGN.md.
"""
import argparse
import json
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from . import calib_a1
from .body_a1 import CostBody
from .rehearsal import ROOT, inventory
from .screen_a1 import (RESERVE, SCHOOL_BUDGET, compare, episode, oracle_payload,
                        school, totals)

CONDITIONS = ['flat', 'turn4', 'turn8', 'skew_turn6']
# Never the condition itself, and never `flat`, whose calibration is the prior.
CROSSED_SOURCE = {'flat': 'turn4', 'turn4': 'turn8',
                  'turn8': 'skew_turn6', 'skew_turn6': 'turn4'}
ALPHA_DENOMINATOR = 60*len(CONDITIONS)
DIAGNOSTIC = {'diag_skew0': (4, 4, 4, 4), 'diag_skew1': (4, 5, 4, 4),
              'diag_skew2': (3, 5, 4, 4)}
DIAGNOSTIC_TURN = 6

PROTOCOL = dict(version='a1-v2', scope='public-development-screen-not-campaign',
    amends='plan-a1', conditions=CONDITIONS, crossed_source=CROSSED_SOURCE,
    arms=['nominal', 'learned', 'turn_ablated', 'crossed'],
    reported_but_not_criterion=['permuted'], ceiling='oracle',
    content_controls=['turn_ablated', 'crossed'],
    alpha_denominator=ALPHA_DENOMINATOR,
    alpha_rationale='Bonferroni over the four declared campaigns',
    school_budget=SCHOOL_BUDGET, reserve_constant=RESERVE,
    diagnostic=dict(bases=DIAGNOSTIC, turn=DIAGNOSTIC_TURN,
                    candidate=False, counted_in_multiplicity=False),
    learning_in_exam=False, campaign_ready=False)


def turn_ablated(payload):
    """Learned base, prior turn. The turn term is the only non-conservative part."""
    calib_a1.validate(payload)
    out = dict(payload, turn=calib_a1.NOMINAL_TURN)
    calib_a1.validate(out)
    return out


def screen(arm_rows, nominal_rows, arm_school, controls):
    result = compare(arm_rows, nominal_rows)
    total = totals(arm_rows)
    p = result['p_one_sided']
    result['school_energy'] = arm_school['energy']
    result['school_plus_exam_energy'] = arm_school['energy']+total['energy']
    result['nominal_exam_energy'] = totals(nominal_rows)['energy']
    result['amortised'] = result['school_plus_exam_energy'] < result['nominal_exam_energy']
    result['beats'] = {name: versus['joint_success_energy_saved'] > 0
                       for name, versus in controls.items()}
    result['plan_a1_v2_development_pass'] = bool(
        total['collisions'] == 0 and total['reserve_violations'] == 0 and
        total['false_facts'] == 0 and total['calibrations_unchanged'] and
        result['new_failures'] == 0 and result['joint_success_energy_saved'] > 0 and
        result['amortised'] and
        all(result['beats'][name] for name in PROTOCOL['content_controls']) and
        p['numerator']*ALPHA_DENOMINATOR <= p['denominator'])
    return result


def taught_payloads(school_seeds):
    return {name: school(school_seeds, CostBody.named(name))
            for name in set(CONDITIONS) | set(CROSSED_SOURCE.values())}


def run(*, progress=False):
    history_path = ROOT/'lab/transfer3/rehearsal-v4.json'
    history = loads_strict(history_path.read_bytes())
    for path, digest in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != digest:
            raise ValueError('V4 frozen source changed: '+path)
    school_seeds = [r['seed'] for r in history['school_rooms']]
    rooms = [r['seed'] for r in history['exam_rooms']]
    schools = taught_payloads(school_seeds)
    campaigns = {}
    for name in CONDITIONS:
        body = CostBody.named(name)
        taught = schools[name]
        payloads = dict(nominal=calib_a1.nominal(), learned=taught['payload'],
                        turn_ablated=turn_ablated(taught['payload']),
                        crossed=schools[CROSSED_SOURCE[name]]['payload'],
                        permuted=calib_a1.permuted(taught['payload']),
                        oracle=oracle_payload(body))
        exams = {arm: [episode(seed, body, payload) for seed in rooms]
                 for arm, payload in payloads.items()}
        controls = {arm: compare(exams['learned'], exams[arm])
                    for arm in ('turn_ablated', 'crossed', 'permuted')}
        degenerate = {arm: payloads[arm] == payloads['learned']
                      for arm in ('turn_ablated', 'crossed', 'permuted')}
        campaigns[name] = dict(condition=body.as_dict(), school=taught, payloads=payloads,
            calibration_error=calib_a1.error_against(taught['payload'], body),
            degenerate_controls=degenerate,
            totals={arm: totals(rows) for arm, rows in exams.items()},
            versus_controls=controls,
            versus_nominal={arm: compare(exams[arm], exams['nominal'])
                            for arm in payloads if arm != 'nominal'},
            screen=screen(exams['learned'], exams['nominal'], taught,
                          {k: v for k, v in controls.items() if k in PROTOCOL['content_controls']}),
            exams=exams)
        if progress:
            s = campaigns[name]['screen']
            print(name, 'W/L', s['wins'], s['losses'], 'saved', s['joint_success_energy_saved'],
                  'beats', s['beats'], 'pass', s['plan_a1_v2_development_pass'], flush=True)
    diagnostic = {}
    for label, base in DIAGNOSTIC.items():
        body = CostBody(base=base, turn=DIAGNOSTIC_TURN)
        taught = school(school_seeds, body)
        rows = {arm: [episode(seed, body, payload) for seed in rooms] for arm, payload in
                (('nominal', calib_a1.nominal()), ('learned', taught['payload']))}
        versus = compare(rows['learned'], rows['nominal'])
        diagnostic[label] = dict(base=list(base), turn=DIAGNOSTIC_TURN,
            asymmetry=max(base)-min(base), school=taught,
            calibration_error=calib_a1.error_against(taught['payload'], body),
            totals={arm: totals(r) for arm, r in rows.items()},
            versus_nominal=versus, candidate=False)
        if progress:
            print(label, 'asimetria', max(base)-min(base), 'ahorro',
                  versus['joint_success_energy_saved'], flush=True)
    manifest = inventory()
    for path in ('tests/test_transfer3_a1_v2.py', 'docs/TRANSFER3-PLAN-A1-V2-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL, inventory=manifest,
        history_sha256=sha256_bytes(history_path.read_bytes()),
        school_seeds=school_seeds, exam_seeds=rooms, campaigns=campaigns,
        diagnostic=diagnostic,
        any_condition_passed=any(c['screen']['plan_a1_v2_development_pass']
                                 for c in campaigns.values()),
        transfer3_green=False, campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or 'campaigns' not in report:
        raise ValueError('report schema')
    if canonical_bytes(run(progress=progress)) != canonical_bytes(report):
        raise ValueError('Plan A1 v2 screen does not reconstruct')
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
    print(json.dumps(dict(
        campaigns={name: dict(degenerate=c['degenerate_controls'],
            totals={a: {k: t[k] for k in ('reached', 'energy', 'turns', 'reserve_violations')}
                    for a, t in c['totals'].items()},
            screen={k: c['screen'][k] for k in ('wins', 'losses', 'ties', 'new_failures',
                'recovered', 'joint_success_energy_saved', 'school_plus_exam_energy',
                'nominal_exam_energy', 'amortised', 'beats', 'p_one_sided',
                'plan_a1_v2_development_pass')})
            for name, c in report['campaigns'].items()},
        diagnostic={k: dict(asymmetry=v['asymmetry'],
            saved=v['versus_nominal']['joint_success_energy_saved'],
            reached=[v['totals']['learned']['reached'], v['totals']['nominal']['reached']],
            moves=[v['totals']['learned']['moves'], v['totals']['nominal']['moves']])
            for k, v in report['diagnostic'].items()}), sort_keys=True))


if __name__ == '__main__':
    main()
