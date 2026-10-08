"""Bounded public Plan B2; exact replay, dependency closure, no real B/C."""
import argparse
import ast
from collections import deque
from importlib.util import resolve_name
from math import comb
from pathlib import Path
import sys

from echoai.nexus0.sim3.canon import canonical_bytes, loads_strict, sha256_bytes
from echoai.nexus0.compose1.controller import add
from echoai.nexus0.fusion1.core import unpack
from . import calib_b2, costs_a2, school_b2
from .gain_b1 import GainRoom, declared_body
from .planner_b2 import Planner
from .transport_b2 import Caged, MODULES, PARENT_MODULES
from .space_a2 import suite
from .rehearsal_v4 import significance

ROOT = Path(__file__).resolve().parents[2]
CONDITIONS = (1,2,3)
PROTOCOL = dict(version='b2',conditions=list(CONDITIONS),aligned=True,reserve=6,
    school_moves=8,school_energy=32,development_seed=20268001,development_count=24,
    confirmation_seed=20269001,confirmation_count=256,alpha_denominator=240,
    primary='paired room-block mission completions over three gains',
    margin=10,campaign_enabled=False,learning_in_exam=False)


def dependency_paths(entries):
    """Conservative static closure, including function-local imports and packages."""
    pending, seen = list(entries), set()
    def locate(module):
        if not module:
            return None
        base = ROOT.parent.joinpath(*module.split('.'))
        for p in (base.with_suffix('.py'),base/'__init__.py'):
            if p.is_file():
                return p.resolve()
        return None
    while pending:
        path = Path(pending.pop()).resolve()
        if path in seen:
            continue
        if not path.is_file():
            raise ValueError('missing dependency: '+str(path))
        seen.add(path)
        if path.suffix != '.py':
            continue
        relative = path.relative_to(ROOT.parent).with_suffix('')
        parts = list(relative.parts)
        package = '.'.join(parts[:-1])
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom):
                base = resolve_name('.'*node.level+(node.module or ''),package) if node.level else node.module
                names = [base]+[base+'.'+a.name for a in node.names if base and a.name != '*']
            else:
                continue
            for name in names:
                target = locate(name)
                if target is not None:
                    pending.append(target)
                    # Package initializers can carry dependencies too.
                    for i in range(1,len(name.split('.'))):
                        init = ROOT.parent.joinpath(*name.split('.')[:i])/'__init__.py'
                        if init.is_file():
                            pending.append(init)
    return sorted(seen)


def manifest():
    entries = [Path(__file__),Path(__file__).with_name('consumer_b2.py'),
               ROOT/'tests/test_transfer3_b2.py',ROOT/'docs/TRANSFER3-PLAN-B2-DESIGN.md']
    entries += [ROOT/'nexus0'/p for p in MODULES]+[ROOT.parent/p for p in PARENT_MODULES]
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else '../'+str(p.relative_to(ROOT.parent)):
            sha256_bytes(p.read_bytes()) for p in dependency_paths(entries)}


def verify_manifest(saved):
    for path, expected in saved.items():
        if sha256_bytes((ROOT/path).read_bytes()) != expected:
            raise ValueError('dependency changed: '+path)


def true_home_costs(room):
    """Directed real burst graph, independent of every agent belief/gate."""
    free = room.domain-room.solids
    reverse = {p:[] for p in free}
    for p in free:
        for a in range(4):
            q = p
            for _ in range(room.gains[a]):
                nxt = add(q,calib_b2.AXES[a])
                if nxt not in free:
                    break
                q = nxt
            if q != p:
                reverse[q].append(p)
    distances, queue = {room.start:0}, deque([room.start])
    while queue:
        q = queue.popleft()
        for p in reverse[q]:
            if p not in distances:
                distances[p] = distances[q]+4
                queue.append(p)
    return distances


def observed_free(frame):
    # Same two-source admission for the noiseless static fixture. Both must
    # explicitly assert free; absence and conflict never authorize movement.
    return {tuple(c['position']) for c in frame['cells']
            if all(unpack(bytes.fromhex(c[k]))[:2] == (0,40) for k in ('depth','lidar'))}


def episode(seed, gain, payload, *, safe, isolated=True):
    world = GainRoom(seed,declared_body(),(gain,1,1,1),aligned=True)
    agent = Caged(payload,world.goal,safe=safe) if isolated else Planner(
        calib_b2.restore(payload).snapshot(),world.goal,costs_a2.nominal(),reserve=6,safe=safe)
    base = agent.ready['model_sha256'] if isolated else agent.model.fingerprint()
    home = true_home_costs(world)
    violations = unseen = imagined = 0
    unchanged = True
    chain, actions = '0'*64, []
    frame = world.scan()
    try:
        for _ in range(65):
            decision = agent.call(frame) if isolated else agent.decide(frame)
            status = decision['status']
            unchanged &= decision['model_sha256'] == base
            imagined += decision['imagined_writes'] != 0
            consequence = None
            if status in ('moving','returning'):
                w = bytes.fromhex(decision['wsp'])
                if len(w) != 16 or w[1] != 11 or not 0 <= w[13] < 4:
                    raise ValueError('bad executed WSP')
                a = w[13]
                before = world.pos
                consequence = world.step(a)
                q = before
                free = observed_free(frame)
                for _ in range(consequence['cells']):
                    q = add(q,calib_b2.AXES[a])
                    unseen += q not in free
                violations += world.pos not in home or world.energy < home[world.pos]+10
                actions.append(a)
            chain = sha256_bytes(canonical_bytes(dict(previous=chain,frame=frame,
                                                      decision=decision,consequence=consequence)))
            if consequence is None:
                break
            frame = world.scan()
        else:
            raise ValueError('missing terminal decision')
        final = agent.frozen_check() if isolated else dict(model_sha256=agent.model.fingerprint(),learning=agent.learning)
        unchanged &= final['model_sha256'] == base and not final['learning']
        reached = status == 'reached'
        return dict(seed=seed,status=status,reached=reached,moves=world.steps,energy=240-world.energy,
                    collisions=world.collisions,reserve_violations=violations,unobserved_segments=unseen,
                    false_facts=int(reached and not (world.pos == world.goal and frame['station_observed'])),
                    imagined_writes=imagined,model_unchanged=bool(unchanged),
                    prediction_errors=decision['prediction_errors'],actions=actions,trace_sha256=chain)
    finally:
        if isolated:
            agent.close()


def evaluate(conditions, schools, *, confirm):
    names = ('nominal','prior2','prior3')
    comparisons = {}
    for name in names:
        first = next(iter(conditions.values()))
        n = len(first['learned'])
        wins = losses = gained = lost = joint_saved = all_saved = 0
        for i in range(n):
            balance = 0
            for arms in conditions.values():
                a,b = arms['learned'][i],arms[name][i]
                if a['seed'] != b['seed']:
                    raise ValueError('unpaired rooms')
                balance += int(a['reached'])-int(b['reached'])
                gained += a['reached'] and not b['reached']
                lost += b['reached'] and not a['reached']
                all_saved += b['energy']-a['energy']
                if a['reached'] and b['reached']:
                    joint_saved += b['energy']-a['energy']
            wins += balance > 0
            losses += balance < 0
        comparisons[name] = dict(block_wins=wins,block_losses=losses,gained=gained,lost=lost,
            joint_saved=joint_saved,all_saved=all_saved,p=significance(wins,losses))
    hard = all(r['collisions']==r['reserve_violations']==r['false_facts']==r['imagined_writes']==r['unobserved_segments']==0
               and r['model_unchanged'] for arms in conditions.values() for rows in arms.values() for r in rows)
    main = comparisons['nominal']
    school_energy = sum(s['energy'] for s in schools.values())
    checks = dict(hard_constraints=hard,no_new_failures=main['lost']==0,
        more_missions=main['gained']>main['lost'],joint_saving=main['joint_saved']>0,
        amortised=main['all_saved']>school_energy,
        beyond_fixed_priors=all(c['gained']>c['lost'] for k,c in comparisons.items() if k!='nominal'),
        significant=(main['p']['numerator']*240 <= main['p']['denominator']) if confirm else True)
    return dict(comparisons=comparisons,checks=checks,passes=all(checks.values()),school_energy=school_energy)


def past_shapes():
    shapes = set()
    # All already-existing reports, read one at a time. Only explicit geometry
    # records count; gain/condition changes do not make new shapes.
    def walk(value):
        if isinstance(value,dict):
            if isinstance(value.get('shape'),str):
                shapes.add(value['shape'])
            for v in value.values():
                walk(v)
        elif isinstance(value,list):
            for v in value:
                walk(v)
    for p in sorted((ROOT/'lab/transfer3').glob('*.json')):
        if p.name.startswith('plan-b2-'):
            continue
        walk(loads_strict(p.read_bytes()))
    return sorted(shapes)


def run(stage, safe, *, isolated=True, pilot=None, progress=False, excluded=None):
    before = manifest()
    if stage == 'confirm' and (not isolated or pilot is None or not pilot['verdict']['passes']
                               or pilot['safe'] != safe or pilot['stage'] != 'pilot'):
        raise ValueError('confirmation requires passing isolated pilot')
    schools = {str(g):school_b2.train((g,1,1,1)) for g in CONDITIONS}
    for g,s in schools.items():
        school_b2.replay(s)
        if s['payload']['gains'] != [int(g),1,1,1]:
            raise ValueError('school did not identify condition')
    excluded = [] if stage == 'pilot' else (past_shapes() if excluded is None else excluded)
    start,count = (20268001,24) if stage == 'pilot' else (20269001,256)
    rooms,ledger = suite(start,count,excluded,declared_body())
    conditions, summaries = {}, {}
    for g in CONDITIONS:
        payloads = dict(nominal=calib_b2.prior(1),prior2=calib_b2.prior(2),prior3=calib_b2.prior(3),
                        learned=schools[str(g)]['payload'])
        cache, arms = {}, {}
        for name,payload in payloads.items():
            signature = tuple(payload['gains'])
            if signature not in cache:
                cache[signature] = [episode(r['seed'],g,payload,safe=safe,isolated=isolated) for r in rooms]
            arms[name] = cache[signature]
            if progress:
                print(stage,'safe',safe,'gain',g,name,'reached',sum(r['reached'] for r in arms[name]),flush=True)
        conditions[str(g)] = arms
        summaries[str(g)] = {name:dict(reached=sum(r['reached'] for r in rows),
            energy=sum(r['energy'] for r in rows),reserve_violations=sum(r['reserve_violations'] for r in rows),
            unobserved_segments=sum(r['unobserved_segments'] for r in rows)) for name,rows in arms.items()}
    verify_manifest(before)
    return dict(protocol=PROTOCOL,stage=stage,safe=safe,isolated=isolated,inventory=before,
                schools=schools,rooms=rooms,ledger=ledger,excluded=excluded,conditions=conditions,
                summaries=summaries,verdict=evaluate(conditions,schools,confirm=stage=='confirm'),
                pilot=pilot if stage=='confirm' else None,
                transfer3_green=False,campaign_C_opened=False)


def audit(report, progress=False):
    verify_manifest(report['inventory'])
    expected = run(report['stage'],report['safe'],isolated=report['isolated'],pilot=report['pilot'],
                   excluded=report['excluded'],progress=progress)
    if canonical_bytes(expected) != canonical_bytes(report):
        raise ValueError('B2 replay mismatch')
    return dict(replay_valid=True,sha256=sha256_bytes(canonical_bytes(report)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['pilot','confirm','audit'])
    p.add_argument('path',type=Path)
    p.add_argument('--safe',action='store_true')
    p.add_argument('--local',action='store_true')
    p.add_argument('--pilot',type=Path)
    args = p.parse_args()
    if args.command == 'audit':
        print(audit(loads_strict(args.path.read_bytes()),progress=True));return
    if args.path.exists():
        raise FileExistsError('preserve attempts')
    pilot = loads_strict(args.pilot.read_bytes()) if args.pilot else None
    result = run(args.command,args.safe,isolated=not args.local,pilot=pilot,progress=True)
    with args.path.open('xb') as f:
        f.write(canonical_bytes(result))
    print(result['verdict'],flush=True)


if __name__ == '__main__':
    main()
