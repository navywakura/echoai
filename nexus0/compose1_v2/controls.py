"""Executable negative controls and retained tampering of a valid A flight.

Tampering is explicitly offline. No unsafe mutant is flown on hardware.
"""
import copy
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from echoai.nexus0.compose1.model import Effects
from echoai.nexus0.compose1.bench import save
from echoai.nexus0.fusion1.bench import seal
from echoai.nexus0.fusion1.core import packet
from .controller import Composer
from .development import ROOT, train
from .functional import mission
from .space import DIRECTIONS, Space
from .evaluate import audit_session


def software():
    model = train()
    full = mission(model, 20261902, 'dynamic', 'echo32')
    short = mission(model, 20261902, 'dynamic', 'one_step')
    checks = dict(horizon_replaced=full['reached'] and short['reached'] and full['steps'] < short['steps'])
    frame = Space(20261901).scan()
    agent = Composer(Effects().snapshot(), (4, 0, 0))
    ordinary = agent.decide(frame)
    mutant = Composer(Effects().snapshot(), (4, 0, 0))
    with patch.object(mutant.model, 'predict', side_effect=lambda a: DIRECTIONS[a]):
        forged = mutant.decide(frame)
    checks['T_ignored'] = bytes.fromhex(ordinary['wsp'])[1] == 14 and bytes.fromhex(forged['wsp'])[1] == 11
    try:
        Composer(model, (4, 0, 0)).decide(dict(frame, private_map=sorted(Space(20261901).solids)))
        checks['private_map'] = False
    except ValueError:
        checks['private_map'] = True
    physical = dict(physical=True, now_ns=1_000_000_000, odometry=[0, 0, 0], energy=240,
        station_observed=False, cells=[dict(position=[1, 0, 0], sources=[dict(source=s,
        wsp=packet(0, 40).hex(), capture_ns=1, delivered_ns=1, raw_sha256='a'*64) for s in ('depth', 'lidar')])])
    regular = Composer(model, (2, 0, 0)); stale = Composer(model, (2, 0, 0), 'no_expiry')
    regular.update(physical); stale.update(physical)
    checks['expired_evidence'] = not regular.free((1, 0, 0)) and stale.free((1, 0, 0))

    class WriteRollout(Composer):
        def search(self, target):
            answer = super().search(target)
            self.model.observe_effect(True, 0, (1, 0, 0))
            return answer

    with patch('echoai.nexus0.compose1_v2.functional.Composer', WriteRollout):
        written = mission(model, 20261901, 'static', 'echo32')
    checks['rollout_write'] = not written['model_unchanged']
    regular = Composer(model, (0, 0, 0)); false = Composer(model, (0, 0, 0), 'goal_is_fact')
    frame = dict(now_ns=0, odometry=[0, 0, 0], energy=240, station_observed=False, cells=[])
    checks['invented_arrival'] = regular.decide(frame)['status'] != 'reached' and false.decide(frame)['status'] == 'reached'
    unsafe = mission(model, 20261901, 'low_energy', 'ignore_reserve')
    safe = mission(model, 20261901, 'low_energy', 'echo32')
    checks['ignored_reserve'] = unsafe['reserve_violations'] > 0 and safe['reserve_violations'] == 0
    return checks


def tamper_flight(source, destination, kind):
    # Copy evidence except large immutable ULogs; link those read-only by
    # convention and never modify them in any mutation below.
    def copy_file(src, dst):
        if str(src).endswith('.ulg'):
            Path(dst).symlink_to(Path(src).resolve())
            return dst
        return shutil.copy2(src, dst)
    shutil.copytree(source, destination, copy_function=copy_file, symlinks=True)
    def alter(name, fn, lines=False):
        path = destination/name
        rows = [json.loads(s) for s in path.read_text().splitlines()] if lines else json.loads(path.read_text())
        fn(rows)
        path.write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in rows) if lines else json.dumps(rows, sort_keys=True))
    if kind == 'prediction_after_action':
        def reorder(rows):
            i = next(i for i, r in enumerate(rows) if r.get('side') == 'agent')
            rows[i-1], rows[i] = rows[i], rows[i-1]
        alter('journal.jsonl', reorder, True)
    elif kind == 'wsp_changed':
        def swap(rows):
            row = next(r for r in rows if r['kind'] == 'command')
            w = bytearray.fromhex(row['wsp']); w[13] ^= 1; row['wsp'] = w.hex()
        alter('out/mission.jsonl', swap, True)
    elif kind == 'waypoint_changed':
        def waypoint(rows):
            next(r for r in rows if r['kind'] == 'ack')['target_local_mm'][0] += 3000
        alter('out/mission.jsonl', waypoint, True)
    elif kind == 'pose_jump':
        def jump(rows):
            rows[len(rows)//2]['body'][1] += 20
        alter('out/private.jsonl', jump, True)
    elif kind == 'pose_actuation':
        alter('out/result.json', lambda r: r.update(body_pose_writes=1))
    elif kind == 'ulog_changed':
        alter('out/result.json', lambda r: r.update(ulog_sha256='0'*64))
    else:
        raise ValueError(kind)
    return audit_session(destination)


def run(source, label='round-1'):
    root = ROOT/'controls'/label
    root.mkdir(parents=True, exist_ok=False)
    baseline = audit_session(source)
    if not baseline['evidence_valid'] or not baseline['execution_green'] or not baseline['reached']:
        raise ValueError('controls require a valid, successful A flight')
    checks = software()
    mutations = {}
    for name in ('prediction_after_action', 'wsp_changed', 'waypoint_changed', 'pose_jump', 'pose_actuation', 'ulog_changed'):
        result = tamper_flight(source, root/name, name)
        mutations[name] = result
        checks[name] = not result['evidence_valid'] or not result['execution_green']
    report = seal(dict(checks=checks, mutations=mutations, baseline=baseline,
                       controls_green=all(checks.values()), source=str(source)))
    save(root/'report.json', report)
    print(json.dumps(dict(checks=checks, controls_green=report['controls_green']), sort_keys=True))
    return report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--label', default='round-1')
    args = parser.parse_args()
    raise SystemExit(0 if run(args.source, args.label)['controls_green'] else 1)
