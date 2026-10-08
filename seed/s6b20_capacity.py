"""Directed capability control, isolated from B20 discovery and model inputs."""
import fcntl
import os
from pathlib import Path
import subprocess
import sys

from seed import s6b20 as r


def run(audit=False):
    r.integrity();plan=r.read(r.INPUT/'capacity-plan.json');fixture=r.read(r.INPUT/'baseline.json')
    policy=fixture['policy'];ns='capacity-audit' if audit else 'capacity'
    execute=r.measure if audit else r.reproduced
    base=execute(ns,'baseline',policy,r.A)
    if r.sha(r.timeline.legacy_rows(base['rows']))!=fixture['screen_trace_sha256']:raise RuntimeError('capacity baseline parity')
    results=[];winners={}
    for item in plan['candidates']:
        candidate=r.engine.strategy(program=r.engine.patch.append(policy['program'],item['proposal']))
        measured=execute(ns,item['name'],candidate,r.A);diff=r.difference(base,measured)
        result=dict(name=item['name'],category=item['category'],diff=diff,passed=r.previous.a_pass(diff))
        results.append(result);r.status('CAPACITY_AUDIT_RESULT' if audit else 'CAPACITY_RESULT',**result)
        if not audit:
            r.journal(r.ROOT/'live/journal.jsonl',dict(kind='verdict',id=len(results)-1,
                arm=item['category'],verdict='CAPACITY_PASS' if result['passed'] else 'V3',
                A=dict(diff,before_levels=base['levels'],after_levels=measured['levels']),
                reason='control dirigido de capacidad; no descubrimiento autónomo'))
        if result['passed'] and item['category'] not in winners:
            winners[item['category']]=dict(name=item['name'],policy=candidate)
    # One first passer per category; no repair after broad evidence is opened.
    broad={};qualified={}
    if winners:
        full=execute(ns,'full-baseline',policy,r.DEVELOPMENT)
        for category,winner in winners.items():
            after=execute(ns,'full-'+category,winner['policy'],r.DEVELOPMENT)
            diff=r.difference(full,after);broad[category]=diff
            if r.previous.a_pass(diff):qualified[category]=winner['name']
    result=dict(valid=True,plan_sha256=r.sha(plan),results=results,broad=broad,qualified=qualified,
        capacity_passed=bool(qualified),autonomous_discovery=False,protected_opened=False,s6_green=False)
    if audit:
        original=r.read(r.ROOT/'capacity.json')
        if original!=result:raise RuntimeError('capacity audit summary differs')
        for path in (r.ROOT/ns/'measurements').glob('*.json'):
            if r.read(path)!=r.read(r.ROOT/'capacity/measurements'/path.name):raise RuntimeError('capacity independent trajectory differs')
        result=dict(result,independent_execution=True,capacity_sha256=r.sha(original))
    r.atomic(r.ROOT/('capacity-audit.json' if audit else 'capacity.json'),result)
    return result


def main(args):
    r.ROOT.mkdir(parents=True,exist_ok=True)
    try:
        if args==['audit']:run(True);return
        if args!=['follow']:raise ValueError('use follow/audit')
        lock=(r.ROOT/'pipeline.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not (r.ROOT/'capacity.json').exists():run()
        if not (r.ROOT/'capacity-audit.json').exists():subprocess.run([sys.executable,'-u','-m','seed.s6b20_capacity','audit'],check=True)
        result=r.read(r.ROOT/'capacity.json');audit=r.read(r.ROOT/'capacity-audit.json')
        if not audit['valid'] or audit['capacity_sha256']!=r.sha(result):raise RuntimeError('capacity audit binding')
        gate=dict(valid=True,capacity_passed=result['capacity_passed'],capacity_sha256=r.sha(result),
            audit_sha256=r.sha(audit),scope='directed development capacity; no solution delivered to discovery',
            physical_games=r.read(r.ROOT/'budget.json')['scheduled_games'],s6_green=False)
        r.atomic(r.ROOT/'capacity-gate.json',gate)
        r.status('CAPACITY_PASSED' if gate['capacity_passed'] else 'CAPACITY_NO_PROMOTION',**gate)
    except Exception as exc:
        r.status('BLOCKED_INSTRUMENT',reason=type(exc).__name__+': '+str(exc));raise


if __name__=='__main__':main(sys.argv[1:])
