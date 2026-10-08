"""Fresh flight campaigns with immutable outputs and fixed v2 bands."""
import copy
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pyulog import ULog
from echoai.nexus0.flight1s import session
from echoai.nexus0.flight1s.runtime import ECHOAI, preflight
from echoai.nexus0.flight1s.bench import WORLD_PROTOCOL, condition_order
from echoai.nexus0.flight1s.v2 import evaluate, protocol
from echoai.nexus0.flight1s.v2.bench import Bench, _episode_case
from echoai.nexus0.sim3.canon import report_sha256, dump_report, sha256_bytes
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET

HERE = Path(__file__).resolve().parent
LAB = ECHOAI / 'lab/flight1s-v3'
RUNNER = HERE / 'assets/flightrunner_configured.py'
CANDIDATES = {
    'delay': {'EKF2_GPS_DELAY': 0},
    'damped': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0, 'MPC_XY_VEL_D_ACC': .4},
    'settled': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0, 'MPC_XY_VEL_D_ACC': .4},
    'damped_7n': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0, 'MPC_XY_VEL_D_ACC': .4},
    'damped_8n': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0, 'MPC_XY_VEL_D_ACC': .4},
    'pd_7n': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0,
              'MPC_XY_VEL_D_ACC': .4, 'MPC_XY_VEL_I_ACC': 0},
    # The simulated GNSS injects sigma 0.2 m but advertises eph 0.9 m, and with
    # GNSS as the only horizontal aiding EKF2 clamps its assumed position noise
    # to EKF2_NOAID_NOISE. 0.5 is that parameter's documented minimum: the
    # closest the configuration can get to the noise the sensor really has.
    'noaid_7n': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0,
                 'MPC_XY_VEL_D_ACC': .4, 'MPC_XY_VEL_I_ACC': 0,
                 'EKF2_NOAID_NOISE': 0.5},
    # Runs on the patched image, where the simulated GNSS finally advertises
    # the 0.2 m sigma it injects. EKF2_GPS_P_NOISE has to come down with it, or
    # max(hacc, gps_pos_noise) would leave the floor at the 0.5 m default.
    'gpsfix_7n': {'EKF2_GPS_DELAY': 0, 'MPC_XY_VEL_P_ACC': 3.0,
                  'MPC_XY_VEL_D_ACC': .4, 'MPC_XY_VEL_I_ACC': 0,
                  'EKF2_GPS_P_NOISE': 0.2},
}

# Candidates that need the corrected sensor label, and the tag that carries it.
PATCHED_IMAGE = 'localhost/echoai-flight1s-px4:v1.15.4-gpseph'
PATCHED_CANDIDATES = {'gpsfix_7n'}


def configuration(candidate):
    historical = protocol.load()
    if historical.sha256 != '8afa05238c27a7869d385bf38f17739b4e34e1e69c610bd88012b6329d7dee99':
        raise ValueError('Historical v2 protocol changed')
    p = copy.deepcopy(historical.data)
    p['px4_parameters'] = dict(CANDIDATES[candidate])
    p['candidate'] = candidate
    p['schema_version'] = 3
    p['profile'] = 'flight1s-x500-v3'
    force = {'damped_7n':7000,'damped_8n':8000,'pd_7n':7000,
             'noaid_7n':7000,'gpsfix_7n':7000}.get(candidate,5000)
    p['disturbance']['force_mn'] = force
    p['stimulus']['commanded_impulse_mn_s'] = protocol.commanded_impulse_mn_s(force)
    p['stimulus']['free_delta_v_mm_s'] = protocol.free_delta_v_mm_s(force)
    if candidate == 'settled':
        p['stages']['stabilize_ms'] = 20000
    p['image'] = PATCHED_IMAGE if candidate in PATCHED_CANDIDATES else 'stock'
    return p


def validate_configuration(p):
    """Only the preregistered PX4 parameters/preparation can differ from v2."""
    candidate = p.get('candidate')
    if candidate not in CANDIDATES or p != configuration(candidate):
        raise ValueError('configuration differs from frozen v2 bands/candidate')
    return True


def patched_runtime(lock):
    """Point the runtime at the patched image and prove the patch is inside it.

    The PX4 git commit is unchanged, so the commit alone would not reveal the
    edit. What identifies it is the rebuilt binary's digest and the diff the
    build stored, and both are recorded here.
    """
    import copy as _copy
    import subprocess as _sub
    out = _sub.run(['podman', 'run', '--rm', '--pull=never', '--network=none',
                    PATCHED_IMAGE, 'bash', '-lc',
                    'grep -c "sensor_gps.eph = 0.2f;" '
                    '/opt/PX4-Autopilot/src/modules/simulation/sensor_gps_sim/'
                    'SensorGpsSim.cpp; cat /opt/px4-binary.sha256; '
                    'cat /opt/gps-eph.patch'],
                   capture_output=True, text=True, timeout=300)
    if out.returncode != 0:
        raise RuntimeError('patched image unusable: ' + out.stderr[-300:])
    lines = out.stdout.splitlines()
    if lines[0].strip() != '1':
        raise RuntimeError('patched image does not carry the corrected eph')
    binary = lines[1].split()[0]
    patch = '\n'.join(lines[2:])
    ident = _sub.run(['podman', 'image', 'inspect', PATCHED_IMAGE,
                      '--format', '{{.Id}}'], capture_output=True, text=True)
    lock = _copy.deepcopy(lock)
    lock['container'] = dict(lock['container'])
    lock['container'].update(
        image=PATCHED_IMAGE, image_id=ident.stdout.strip(),
        px4_binary_sha256=binary, source_patch=patch,
        source_patch_sha256=sha256_bytes(patch.encode()),
        patched='SensorGpsSim eph 0.9 -> 0.2, matching the injected sigma; '
                'the injected noise itself is unchanged')
    lock['lock_sha256'] = report_sha256(
        {k: v for k, v in lock.items() if k != 'lock_sha256'})
    return lock


def inventory():
    files = sorted((ECHOAI / 'nexus0/flight1s').rglob('*.py'))
    files += sorted((ECHOAI / 'docs/schemas').glob('flight1s*.json'))
    files += sorted((ECHOAI / 'docs/schemas/flight1s-v2').glob('*.json'))
    files += [ECHOAI/'docs/FLIGHT1S-V3-DESIGN.md', ECHOAI/'tests/test_flight1s_v3.py']
    entries = {str(p.relative_to(ECHOAI)): sha256_bytes(p.read_bytes()) for p in files}
    return {'files': entries, 'sha256': report_sha256(entries)}


def parameters_observed(ulog, events, expected):
    if not ulog.exists():
        return {'ok': False, 'cause': 'ulog_missing'}
    u = ULog(str(ulog), message_name_filter_list=[])
    values = dict(u.initial_parameters)
    for _, name, value in u.changed_parameters:
        values[name] = value
    readbacks = {e['name']: e['value'] for e in events
                 if e.get('event') == 'param_set'}
    observed = {k: values.get(k) for k in expected}
    ok = all(k in readbacks and k in values
             and math.isclose(readbacks[k], v, abs_tol=1e-5)
             and math.isclose(values[k], v, abs_tol=1e-5)
             for k, v in expected.items())
    return {'ok': ok, 'expected': expected, 'ulog': observed,
            'readbacks': {k: readbacks.get(k) for k in expected}}


def fly(runtime, gen, p, condition, label, root, *, negative=False):
    print('start ' + label, flush=True)
    env = {'FLIGHT1S_PARAMETERS': json.dumps(p['px4_parameters'], sort_keys=True)}
    if negative:
        env['FLIGHT1S_MUTANT'] = 'noforce'
    ep = session.run_episode(runtime, gen.package, p, condition=condition,
                             label=label, ulog_dir=root / 'ulogs',
                             runner_path=RUNNER, extra_env=env)
    m = evaluate.episode_metrics(ep, p, package=gen.package)
    m.update(package_id=gen.package_id, split=gen.split, runtime=ep.metrics,
             effective_sha256=ep.effective_sha256, protocol_version=3)
    m['parameters'] = parameters_observed(root / 'ulogs' / (label+'.ulg'),
                                         ep.driver_events, p['px4_parameters'])
    m['trace'] = str((root / 'episodes' / (label+'.json')).relative_to(ECHOAI))
    dump_report(ECHOAI / m['trace'], ep.trace())
    m['trace_sha256'] = sha256_bytes((ECHOAI / m['trace']).read_bytes())
    dump_report(root / 'metrics' / (label+'.json'), m)
    failures = [k for k in ('stimulus', 'challenge', 'recovery_verdict', 'parameters')
                if not m.get(k, {}).get('ok')]
    print(f"done {label}: excursion={m.get('disturb_excursion_mm')} "
          f"recovery={m.get('recovery')} fail={failures}", flush=True)
    return m


def groups(rows, p):
    """Reuse the unchanged v2 acceptance implementation, including hygiene."""
    b = Bench(report_path=Path('/unused'), protocol_path=None, verbose=False)
    b.episodes = rows
    b.group('episodes', 'pass' if rows and all(_episode_case(m)['completed'] for m in rows) else 'fail',
            cases=[_episode_case(m) for m in rows])
    b._group_three(p)
    b._group_hygiene(p)
    cases = [dict(label=m['label'], **m['parameters']) for m in rows]
    b.group('configuration', 'pass' if all(c['ok'] for c in cases) else 'fail', cases=cases)
    return b.groups


def run_a(candidate, stage, *, attempt=1):
    if attempt < 1:
        raise ValueError('attempt must be positive')
    root = LAB / (stage + '-' + candidate + (f'-r{attempt}' if attempt > 1 else ''))
    if root.exists():
        raise FileExistsError('Campaign is immutable: ' + str(root))
    root.mkdir(parents=True)
    p = configuration(candidate)
    dump_report(root / 'configuration.json', p)
    runtime = preflight(write=False)
    runtime.require()
    if candidate in PATCHED_CANDIDATES:
        runtime.lock = patched_runtime(runtime.lock)
    inv = inventory()
    dump_report(root / 'inventory.json', inv)
    dump_report(root / 'runtime.json', runtime.lock)
    packages = generate_suite(root / 'suite', load_protocol(WORLD_PROTOCOL),
                              REHEARSAL_SECRET, rehearsal_assignment())[:4]
    repeats = 1 if stage == 'development' else 8
    seed = 20260913 if stage == 'development' else 20260914
    order = condition_order(seed, 4 * repeats)
    jobs = []
    for i, g in enumerate(packages):
        for r in range(repeats):
            slot = i * repeats + r
            for c in order[2*slot:2*slot+2]:
                jobs.append((g, c, f'{c}-{g.package_id}-r{r+1}', r+1, slot))
    start = time.monotonic()
    def one(job):
        g, c, label, repeat, slot = job
        m = fly(runtime, g, p, c, label, root)
        m.update(repeat=repeat, order_slot=slot, lock_sha256=runtime.lock['lock_sha256'],
                 protocol_sha256=report_sha256(p))
        return m
    rows = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        for start_job in range(0, len(jobs), 2):
            batch = list(ex.map(one, jobs[start_job:start_job+2]))
            rows.extend(batch)
            if any(g['status'] != 'pass' for g in groups(batch, p).values()):
                print('Candidate disqualified in A; remaining episodes not_run', flush=True)
                break
    negatives = []
    if stage == 'validation' and len(rows) == len(jobs):
        for g in packages:
            negatives.append(fly(runtime, g, p, 'perturbed', 'negative-'+g.package_id,
                                 root, negative=True))
    gs = groups(rows, p)
    gs['denominator'] = {'status':'pass' if len(rows)==len(jobs) else 'fail',
                         'planned':len(jobs), 'completed':len(rows),
                         'not_run':len(jobs)-len(rows), 'cases':[]}
    if negatives:
        cs = [dict(label=m['label'], ok=bool(m['ok'] and m['parameters']['ok']
                    and not m['stimulus']['ok']
                    and abs(m.get('impulse', {}).get('ratio_ppk', 9999)) < 500))
              for m in negatives]
        gs['negative_controls'] = {'status': 'pass' if all(c['ok'] for c in cs) else 'fail', 'cases': cs}
    gs['code_frozen'] = {'status': 'pass' if inv == inventory() else 'fail', 'cases': []}
    result = dict(candidate=candidate, stage=stage, seed=seed, workers=2,
                  configuration=p, inventory=inv, episodes=rows, negatives=negatives,
                  groups=gs, passed=all(g['status']=='pass' for g in gs.values()),
                  wall_s=round(time.monotonic()-start, 2))
    dump_report(root / 'report.json', result)
    print(json.dumps({'passed': result['passed'], 'groups': {k:v['status'] for k,v in gs.items()},
                      'report': str(root / 'report.json')}), flush=True)
    return result


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['development','validation'])
    ap.add_argument('candidate', choices=CANDIDATES)
    ap.add_argument('--attempt', type=int, default=1)
    args = ap.parse_args()
    raise SystemExit(0 if run_a(args.candidate, args.stage, attempt=args.attempt)['passed'] else 1)
