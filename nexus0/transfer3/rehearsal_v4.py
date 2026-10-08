"""Equal-budget, prospectively specified public screening; not sealed B/C."""
import argparse
import json
from math import comb
from pathlib import Path
from . import policy
from .budget_school import train
from .school_v3 import VARIANTS
from .rehearsal_v2 import suite, episode
from .rehearsal_v3 import compare, summary
from .rehearsal import ROOT, inventory
from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict

PROTOCOL = dict(version=4, scope='public-screening-not-campaign', budget=128,
    exam_start=20264601, exam_count=64, variants=VARIANTS,
    candidates=3, one_sided_sign_alpha_denominator=60,
    reject_new_failures=True, learning_in_exam=False, campaign_ready=False)


def significance(wins, losses):
    if any(type(v) is not int or v<0 for v in (wins, losses)):
        raise ValueError('sign counts')
    n = wins+losses
    return dict(numerator=sum(comb(n,k) for k in range(wins,n+1)), denominator=2**n)


def screen(rows, baseline, school):
    result = compare(rows, baseline)
    result['p_one_sided'] = significance(result['wins'], result['losses'])
    result['new_failures'] = sum(b['reached'] and not a['reached'] for a,b in zip(rows,baseline))
    result['joint_success_saved_moves'] = sum(b['moves']-a['moves'] for a,b in zip(rows,baseline)
                                             if a['reached'] and b['reached'])
    result['all_case_saved_moves'] = sum(b['moves']-a['moves'] for a,b in zip(rows,baseline))
    result['train_plus_exam_moves'] = school['moves']+sum(a['moves'] for a in rows)
    p = result['p_one_sided']
    valid = all(r['collisions']==r['reserve_violations']==r['false_facts']==0 and
                r['model_unchanged'] and all(row['decision']['imagined_writes']==0 for row in r['rows']) for r in rows)
    result['development_screen_pass'] = bool(valid and result['new_failures']==0 and
        result['wins']>result['losses'] and result['joint_success_saved_moves']>0 and
        p['numerator']*PROTOCOL['one_sided_sign_alpha_denominator'] <= p['denominator'])
    return result


def run(*, isolated=False, progress=False):
    history_path = ROOT/'lab/transfer3/rehearsal-v3.json'
    history = loads_strict(history_path.read_bytes())
    for path, digest in history['inventory'].items():
        if sha256_bytes((ROOT/path).read_bytes()) != digest:
            raise ValueError('V3 frozen source changed: '+path)
    seeds = [r['seed'] for r in history['school_rooms']]
    forbidden = [r['shape'] for r in history['school_rooms']+history['exam_rooms']]
    rooms, ledger = suite(PROTOCOL['exam_start'], PROTOCOL['exam_count'], forbidden)
    schools = {variant: train(seeds,variant,PROTOCOL['budget']) for variant in VARIANTS}
    payloads = dict(scratch=policy.scratch(), **{k:s['payload'] for k,s in schools.items()})
    exams = {}
    for arm,payload in payloads.items():
        exams[arm] = []
        for i,room in enumerate(rooms):
            exams[arm].append(episode(policy.restore(payload).snapshot(),room['seed'],isolated=isolated)[0])
            if progress and (i+1)%16==0:
                print(arm,i+1,'/',len(rooms),flush=True)
    manifest = inventory()
    for path in ('tests/test_transfer3_v4.py','docs/TRANSFER3-V4-DESIGN.md'):
        manifest[path] = sha256_bytes((ROOT/path).read_bytes())
    return dict(protocol=PROTOCOL,inventory=manifest,isolated=isolated,
        history_sha256=sha256_bytes(history_path.read_bytes()),
        school_rooms=history['school_rooms'], excluded_rooms=history['exam_rooms'],
        exam_rooms=rooms,ledger=ledger,schools=schools,exams=exams,
        totals={k:summary(rows) for k,rows in exams.items()},
        screens={k:screen(exams[k],exams['scratch'],s) for k,s in schools.items()},
        transfer3_green=False,campaign_C_opened=False)


def audit(report, *, progress=False):
    if type(report) is not dict or type(report.get('isolated')) is not bool:
        raise ValueError('report schema')
    expected=run(isolated=report['isolated'],progress=progress)
    if canonical_bytes(expected)!=canonical_bytes(report):
        raise ValueError('V4 does not reconstruct')
    return dict(replay_valid=True,report_sha256=sha256_bytes(canonical_bytes(report)),transfer3_green=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['run','audit'])
    parser.add_argument('report',type=Path)
    parser.add_argument('--isolated',action='store_true')
    args=parser.parse_args()
    if args.command=='audit':
        print(json.dumps(audit(loads_strict(args.report.read_bytes()),progress=True),sort_keys=True))
        return
    if args.report.exists():raise FileExistsError('preserve public attempts')
    report=run(isolated=args.isolated,progress=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('xb') as stream:stream.write(canonical_bytes(report))
    print(json.dumps(dict(totals=report['totals'],screens={k:{f:v[f] for f in
        ('wins','losses','ties','new_failures','p_one_sided','development_screen_pass')}
        for k,v in report['screens'].items()}),sort_keys=True))


if __name__=='__main__':main()
