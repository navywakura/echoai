"""Public functional development only. Never opens or generates campaign B/C."""
import argparse
import json
from pathlib import Path

from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1_v3.space import Space, DIRECTIONS, add
from echoai.nexus0.compose1_v3.functional import mission
from echoai.nexus0.fusion1.core import unpack
from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes, loads_strict
from .model import export, restore, scratch

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = dict(scope='public-functional-rehearsal', version=1,
                school_seeds=list(range(20264201, 20264205)), school_steps=24,
                exam_seeds=list(range(20264301, 20264309)),
                conditions=['static', 'dynamic', 'closed', 'low_energy'],
                arms=['transfer', 'scratch', 'programmed'],
                learning_in_exam=False, campaign_ready=False)


def geometry(space):
    """Planar diagnostic invariant to translation, D4 rotations/reflections.

Not the final SDF/material audit. Labels, seeds and package names are absent.
"""
    variants = []
    for reflect in (1, -1):
        for rotation in range(4):
            def transform(p):
                x, y, z = p
                x *= reflect
                for _ in range(rotation):
                    x, y = -y, x
                return x, y, z
            domain = [transform(p) for p in space.domain]
            origin = tuple(min(p[i] for p in domain) for i in range(3))
            def normalize(points):
                return sorted([v-origin[i] for i, v in enumerate(transform(p))] for p in points)
            variants.append(canonical_bytes(dict(domain=normalize(space.domain),
                solids=normalize(space.solids), start=normalize([space.start]),
                goal=normalize([space.goal]))))
    return sha256_bytes(min(variants))


def school():
    """Supervised public kinematic calibration, not autonomous exploration.

Teacher knows the action interface and selects collision-free practice moves.
The model receives only actual before/after displacement after world.step.
Both teacher knowledge and this training expense are explicitly reported.
"""
    model = Effects()
    episodes = []
    for seed in PROTOCOL['school_seeds']:
        world = Space(seed)
        rows = []
        for turn in range(PROTOCOL['school_steps']):
            before = world.scan()
            # Teacher uses public sensor packets, not the private map.
            available = {tuple(c['position']) for c in before['cells']
                         if unpack(bytes.fromhex(c['lidar']))[0] == 0 and
                         unpack(bytes.fromhex(c['depth']))[0] == 0}
            actions = [(turn+i) % 4 for i in range(4)]
            action = next(a for a in actions if add(tuple(before['odometry']), DIRECTIONS[a]) in available)
            consequence = world.step(action)
            after = world.scan()
            delta = tuple(b-a for a, b in zip(before['odometry'], after['odometry']))
            if consequence['blocked'] or sum(abs(x) for x in delta) != 1:
                raise ValueError('school movement not observed')
            model.observe_effect(True, action, delta)
            rows.append(dict(before=before, action=action, consequence=consequence, after=after))
        episodes.append(dict(seed=seed, geometry=geometry(world), rows=rows))
    payload = export(model)
    if len(payload['effects']) != 4:
        raise ValueError('insufficient school action coverage')
    return dict(episodes=episodes, transfer=payload,
                training_moves=sum(len(e['rows']) for e in episodes),
                training_cost_sim_u=sum(r['consequence']['cost'] for e in episodes for r in e['rows']))


def programmed():
    """Diagnostic control: same planner, action effects supplied by programmer."""
    model = Effects()
    for a in range(4):
        for _ in range(2):
            model.observe_effect(True, a, DIRECTIONS[a])
    return export(model)


def stable(row):
    # Wall time is measured by the old runner but cannot be a replay equality.
    return {k: v for k, v in row.items() if k != 'performance'}


def inventory():
    # Public development manifest, not a freeze or an external commitment.
    paths = sorted((ROOT/'nexus0').rglob('*.py'))
    paths += [ROOT.parent/name for name in ('core/cam.py', 'core/qn.py', 'core/wsp.py')]
    return {str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else Path('..')/p.name):
            sha256_bytes(p.read_bytes()) for p in paths}


def run(*, isolated=False):
    training = school()
    payloads = dict(transfer=training['transfer'], scratch=scratch(), programmed=programmed())
    snapshots = {name: restore(value).snapshot() for name, value in payloads.items()}
    rows = []
    for i, seed in enumerate(PROTOCOL['exam_seeds']):
        condition = PROTOCOL['conditions'][i % len(PROTOCOL['conditions'])]
        fingerprint = geometry(Space(seed, condition))
        for arm in PROTOCOL['arms']:
            row = stable(mission(snapshots[arm], seed, condition, 'echo32', isolated=isolated))
            rows.append(dict(arm=arm, geometry=fingerprint, result=row))
    totals = {}
    for arm in PROTOCOL['arms']:
        results = [r['result'] for r in rows if r['arm'] == arm]
        totals[arm] = dict(episodes=len(results), reached=sum(r['reached'] for r in results),
            moves=sum(r['steps'] for r in results),
            collisions=sum(r['collisions'] for r in results),
            reserve_violations=sum(r['reserve_violations'] for r in results),
            false_facts=sum(r['false_facts'] for r in results),
            models_unchanged=all(r['model_unchanged'] and r['imagined_writes'] == 0 for r in results))
    school_geometry = {e['geometry'] for e in training['episodes']}
    exam_geometry = {r['geometry'] for r in rows}
    return dict(protocol=PROTOCOL, inventory=inventory(), training=training,
                payloads=payloads, episodes=rows, totals=totals,
                distinct_school_geometries=len(school_geometry),
                distinct_exam_geometries=len(exam_geometry),
                geometry_overlap=sorted(school_geometry & exam_geometry),
                isolated=isolated, transfer3_green=False, campaign_C_opened=False)


def audit(report):
    if type(report) is not dict or type(report.get('isolated')) is not bool:
        raise ValueError('report schema')
    expected = run(isolated=report['isolated'])
    if canonical_bytes(report) != canonical_bytes(expected):
        raise ValueError('public rehearsal does not reconstruct')
    return dict(replay_valid=True, transfer3_green=False,
                report_sha256=sha256_bytes(canonical_bytes(report)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['run', 'audit'])
    parser.add_argument('report', type=Path)
    parser.add_argument('--isolated', action='store_true')
    args = parser.parse_args()
    if args.command == 'audit':
        print(json.dumps(audit(loads_strict(args.report.read_bytes())), sort_keys=True))
    else:
        if args.report.exists():
            raise FileExistsError('public runs are not overwritten')
        report = run(isolated=args.isolated)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open('xb') as stream:
            stream.write(canonical_bytes(report))
        print(json.dumps(dict(totals=report['totals'], geometry_overlap=report['geometry_overlap'],
                              transfer3_green=False, isolated=report['isolated']), sort_keys=True))


if __name__ == '__main__':
    main()
