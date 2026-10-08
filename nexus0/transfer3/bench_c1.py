"""Plan C1 bench: camera extrinsic calibration. Pilot, confirmation, audit.

Room-block design: every room is examined under all nine mount offsets and the
room, not the row, is the statistical unit. Hard constraints are adjudicated
outside the agent, every step: a true-cost reserve judge, and a check that no
cell the agent admits is actually occupied.

Manifest by conservative import closure (the B2 method), so adding an unrelated
module does not invalidate an audit while changing a dependency does.
"""
import argparse
import ast
from collections import deque
from importlib.util import resolve_name
from math import comb
from pathlib import Path

from echoai.nexus0.compose1.controller import add
from echoai.nexus0.compose1.space import DIRECTIONS
from echoai.nexus0.sim3.canon import canonical_bytes, loads_strict, sha256_bytes
from . import calib_c1, policy, school_c1
from .camera_c1 import OFFSETS, OffsetRoom, declared_body
from .planner_c1 import CalibratedPlanner
from .rehearsal_v2 import shape
from .space_a2 import suite
from .transport_c1 import Caged, MODULES, PARENT_MODULES

ROOT = Path(__file__).resolve().parents[2]
RESERVE = 6
MARGIN = 10
PRIORS = {'prior_x': (1, 0), 'prior_d': (1, 1)}
PROBES = ((20271001, 32, 'suite'), (20272001, 40, 'raw'))

PROTOCOL = dict(version='c1', conditions=[list(o) for o in OFFSETS], reserve=RESERVE, margin=MARGIN,
    arms=['nominal', 'learned']+sorted(PRIORS), priors={k: list(v) for k, v in PRIORS.items()},
    school=dict(gym_seed=school_c1.GYM_SEED, gyms=school_c1.GYMS, moves=school_c1.GYM_MOVES),
    development_seed=20268001, development_count=24,
    confirmation_seed=20274001, confirmation_count=64,
    probe_seeds_excluded=[list(p) for p in PROBES],
    alpha_denominator=240, primary='paired room-block mission completions over nine mount offsets',
    safety='no admitted cell may be occupied; checked outside the agent every step',
    campaign_enabled=False, learning_in_exam=False)


def dependency_paths(entries):
    """Conservative static import closure; the algorithm introduced in bench_b2."""
    pending, seen = list(entries), set()

    def locate(module):
        if not module:
            return None
        base = ROOT.parent.joinpath(*module.split('.'))
        for p in (base.with_suffix('.py'), base/'__init__.py'):
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
        package = '.'.join(path.relative_to(ROOT.parent).with_suffix('').parts[:-1])
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = resolve_name('.'*node.level+(node.module or ''), package) if node.level else node.module
                names = [base]+[base+'.'+a.name for a in node.names if base and a.name != '*']
            else:
                continue
            for name in names:
                target = locate(name)
                if target is not None:
                    pending.append(target)
                    for i in range(1, len(name.split('.'))):
                        init = ROOT.parent.joinpath(*name.split('.')[:i])/'__init__.py'
                        if init.is_file():
                            pending.append(init)
    return sorted(seen)


def manifest():
    here = Path(__file__)
    entries = [here, here.with_name('consumer_c1.py'),
               ROOT/'tests/test_transfer3_c1.py', ROOT/'docs/TRANSFER3-PLAN-C1-DESIGN.md']
    entries += [ROOT/'nexus0'/p for p in MODULES]+[ROOT.parent/p for p in PARENT_MODULES]
    return {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else '../'+str(p.relative_to(ROOT.parent)):
            sha256_bytes(p.read_bytes()) for p in dependency_paths(entries)}


def verify_manifest(saved):
    for path, expected in saved.items():
        target = ROOT.parent/path[3:] if path.startswith('../') else ROOT/path
        if sha256_bytes(target.read_bytes()) != expected:
            raise ValueError('dependency changed: '+path)


def true_home_costs(room):
    """Uniform true cost to the start over the real free cells. Agent-independent."""
    free = room.domain-room.solids
    distances, queue = {room.start: 0}, deque([room.start])
    while queue:
        p = queue.popleft()
        for a in range(4):
            q = add(p, DIRECTIONS[a])
            if q in free and q not in distances:
                distances[q] = distances[p]+4
                queue.append(q)
    return distances


class Local:
    """Uncaged path for development and tests; same agent, same reporting."""
    def __init__(self, model, goal, camera, *, reserve):
        self.agent = CalibratedPlanner(model, goal, camera, reserve=reserve)
        self.ready = dict(offset=list(self.agent.offset), model_sha256=self.agent.model.fingerprint())

    def call(self, frame):
        decision = self.agent.decide(frame)
        decision['admitted'] = self.agent.admitted()
        return decision

    def frozen_check(self):
        return dict(offset=list(self.agent.offset), model_sha256=self.agent.model.fingerprint(),
                    learning=self.agent.learning)

    def close(self):
        pass


def episode(seed, offset, camera, *, isolated=True):
    world = OffsetRoom(seed, declared_body(), offset)
    model = policy.restore(policy.scratch()).snapshot()
    agent = (Caged if isolated else Local)(model, world.goal, camera, reserve=RESERVE)
    home = true_home_costs(world)
    base_offset, base_model = agent.ready['offset'], agent.ready['model_sha256']
    unsafe = violations = imagined = 0
    unchanged, chain = True, '0'*64
    frame = world.scan()
    try:
        for _ in range(66):
            decision = agent.call(frame)
            status = decision['status']
            unsafe += sum(1 for p in decision['admitted'] if tuple(p) not in world.domain-world.solids)
            imagined += decision['imagined_writes'] != 0
            unchanged &= decision['model_sha256'] == base_model
            consequence = None
            if status in ('moving', 'returning'):
                w = bytes.fromhex(decision['wsp'])
                if len(w) != 16 or w[1] != 11 or not 0 <= w[13] < 4:
                    raise ValueError('bad executed WSP')
                consequence = world.step(w[13])
                violations += world.pos not in home or world.energy < home[world.pos]+MARGIN
            chain = sha256_bytes(canonical_bytes(dict(previous=chain, frame=frame,
                                                      decision=decision, consequence=consequence)))
            if consequence is None:
                break
            frame = world.scan()
        else:
            raise ValueError('missing terminal decision')
        final = agent.frozen_check()
        unchanged &= final['model_sha256'] == base_model and final['offset'] == base_offset \
            and not final['learning'] and base_offset == camera['offset']
        reached = status == 'reached'
        return dict(seed=seed, status=status, reached=reached, moves=world.steps,
                    energy=240-world.energy, collisions=world.collisions,
                    reserve_violations=violations, unsafe_admissions=unsafe,
                    false_facts=int(reached and not (world.pos == world.goal and frame['station_observed'])),
                    imagined_writes=imagined, calibration_unchanged=bool(unchanged), trace_sha256=chain)
    finally:
        agent.close()


def sign_test(wins, losses):
    n = wins+losses
    return dict(numerator=sum(comb(n, k) for k in range(wins, n+1)), denominator=2**n)


def evaluate(conditions, schools, *, confirm):
    first = next(iter(conditions.values()))
    n = len(first['learned'])
    comparisons = {}
    for name in ['nominal']+sorted(PRIORS):
        wins = losses = gained = lost = 0
        for i in range(n):
            balance = 0
            for arms in conditions.values():
                a, b = arms['learned'][i], arms[name][i]
                if a['seed'] != b['seed']:
                    raise ValueError('unpaired rooms')
                balance += int(a['reached'])-int(b['reached'])
                gained += a['reached'] and not b['reached']
                lost += b['reached'] and not a['reached']
            wins += balance > 0
            losses += balance < 0
        comparisons[name] = dict(block_wins=wins, block_losses=losses, gained=gained, lost=lost,
                                 p=sign_test(wins, losses))
    totals = {arm: dict(reached=sum(r['reached'] for arms in conditions.values() for r in arms[arm]),
                        energy=sum(r['energy'] for arms in conditions.values() for r in arms[arm]))
              for arm in first}
    hard = all(r['collisions'] == r['reserve_violations'] == r['unsafe_admissions'] ==
               r['false_facts'] == r['imagined_writes'] == 0 and r['calibration_unchanged']
               for arms in conditions.values() for rows in arms.values() for r in rows)
    main = comparisons['nominal']
    school_energy = sum(s['energy'] for s in schools.values())
    checks = dict(hard_constraints=hard, no_new_failures=main['lost'] == 0,
                  more_missions=totals['learned']['reached'] > totals['nominal']['reached'],
                  amortised=school_energy+totals['learned']['energy'] <= totals['nominal']['energy'],
                  beyond_fixed_priors=all(totals['learned']['reached'] > totals[p]['reached'] for p in PRIORS))
    if confirm:
        checks['significant'] = main['p']['numerator']*PROTOCOL['alpha_denominator'] <= main['p']['denominator']
    return dict(comparisons=comparisons, totals=totals, checks=checks, passes=all(checks.values()),
                significance_applied=confirm, school_energy=school_energy)


def probe_shapes():
    shapes = set()
    for start, count, kind in PROBES:
        if kind == 'suite':
            shapes |= {r['shape'] for r in suite(start, count, [], declared_body())[0]}
        else:
            shapes |= {shape(OffsetRoom(s, declared_body(), (0, 0))) for s in range(start, start+count)}
    return shapes


def past_shapes():
    shapes = set()

    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get('shape'), str):
                shapes.add(value['shape'])
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            for v in value:
                walk(v)
    for p in sorted((ROOT/'lab/transfer3').glob('*.json')):
        if not p.name.startswith('plan-c1-'):
            walk(loads_strict(p.read_bytes()))
    shapes |= probe_shapes()
    shapes |= {r['shape'] for r in school_c1.gym_rooms()}
    return sorted(shapes)


def run(stage, *, isolated=True, pilot=None, excluded=None, progress=False):
    before = manifest()
    if stage == 'confirm' and (not isolated or pilot is None or pilot['stage'] != 'pilot'
                               or not pilot['verdict']['passes'] or not pilot['isolated']):
        raise ValueError('confirmation requires a passing isolated pilot')
    schools = {f'{o[0]},{o[1]}': school_c1.train(o) for o in OFFSETS}
    for s in schools.values():
        school_c1.replay(s)
    if stage == 'pilot':
        excluded = []
        start, count = PROTOCOL['development_seed'], PROTOCOL['development_count']
    else:
        excluded = past_shapes() if excluded is None else excluded
        start, count = PROTOCOL['confirmation_seed'], PROTOCOL['confirmation_count']
    rooms, ledger = suite(start, count, excluded, declared_body())
    conditions = {}
    for o in OFFSETS:
        key = f'{o[0]},{o[1]}'
        payloads = dict(nominal=calib_c1.nominal(), learned=schools[key]['payload'],
                        **{name: calib_c1.prior(v) for name, v in PRIORS.items()})
        cache, arms = {}, {}
        for name, payload in payloads.items():
            signature = tuple(payload['offset'])
            if signature not in cache:
                cache[signature] = [episode(r['seed'], o, payload, isolated=isolated) for r in rooms]
            arms[name] = cache[signature]
            if progress:
                print(stage, 'offset', o, name, 'reached', sum(r['reached'] for r in arms[name]), flush=True)
        conditions[key] = arms
    verify_manifest(before)
    return dict(protocol=PROTOCOL, stage=stage, isolated=isolated, inventory=before,
                schools=schools, rooms=rooms, ledger=ledger, excluded=excluded,
                conditions=conditions, verdict=evaluate(conditions, schools, confirm=stage == 'confirm'),
                pilot=pilot if stage == 'confirm' else None,
                transfer3_green=False, campaign_C_opened=False)


def audit(report, progress=False):
    verify_manifest(report['inventory'])
    expected = run(report['stage'], isolated=report['isolated'], pilot=report['pilot'],
                   excluded=report['excluded'], progress=progress)
    if canonical_bytes(expected) != canonical_bytes(report):
        raise ValueError('C1 replay mismatch')
    return dict(replay_valid=True, sha256=sha256_bytes(canonical_bytes(report)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['pilot', 'confirm', 'audit'])
    p.add_argument('path', type=Path)
    p.add_argument('--local', action='store_true')
    p.add_argument('--pilot', type=Path)
    args = p.parse_args()
    if args.command == 'audit':
        print(audit(loads_strict(args.path.read_bytes()), progress=True))
        return
    if args.path.exists():
        raise FileExistsError('preserve every attempt')
    pilot = loads_strict(args.pilot.read_bytes()) if args.pilot else None
    result = run(args.command, isolated=not args.local, pilot=pilot, progress=True)
    with args.path.open('xb') as f:
        f.write(canonical_bytes(result))
    print(result['verdict']['checks'], result['verdict']['passes'], flush=True)


if __name__ == '__main__':
    main()
