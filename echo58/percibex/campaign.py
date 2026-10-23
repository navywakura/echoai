"""Only new rehearsal flights; fixed manifests, local images and no network."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import shutil

from echoai.nexus0.flight1s.runtime import Runtime
from echoai.nexus0.sim3 import runtime as simruntime, sandbox
from echoai.nexus0.sim3.generate import generate_suite
from echoai.nexus0.sim3.pkg import load_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.sensor1s import model, contract as sensor
from echoai.nexus0.pattern1r_v4 import contract
from echoai.nexus0.flight1s.v3.campaign import WORLD_PROTOCOL
from echoai.echo58.memx.memory import Memory
from echoai.echo58.wspfiles.codec import Archive, Record, write, read
from echoai.echo58.wspfiles.memory import export_memory, load_memory
from . import session
from .bundle import build, ROOT, FROZEN, FLIGHT
from .audit import LAB, save, sha, inspect
from .resources import active, supervisor_limits, wait_for_memory

CONTRACT_FILES = (
    'ECHO-5.8/docs/PERCIBEX-DESIGN-20261023.md',
    'ECHO-5.8/docs/PERCIBEX-PLAN-20261023.md',
)
PREMEASUREMENT_REVIEWS = (
    'lab/echo58/percibex/20261023-r1/reboot-recovery-record.json',
    'lab/echo58/percibex/20261023-r1/recovery-candidate/review.json',
    'lab/echo58/percibex/20261023-r1/resource-cleanup-review.json',
    'lab/echo58/closure-20261023/recovery-oom/p-container-cleanup-preflight.json',
    'lab/echo58/percibex/20261023-r1/contract-freeze-review.json',
)


def inventory():
    names = sorted((ROOT/'echo58/percibex').glob('*.py'))
    names += [ROOT/p for p in set(FROZEN.values()) | set(FLIGHT.values())]
    names += [ROOT/'nexus0/pattern1r_v4/session.py', ROOT/'nexus0/pattern1r_v4/contract.py',
              ROOT/'nexus0/sim3/sandbox.py', ROOT/'nexus0/sensor1s/model.py',
              ROOT/'lab/flight1s-v6/lock.json', ROOT/'lab/echo3_pattern1r_v4_report.json',
              ROOT/'docs/examples/sim3-families/pattern1r-v1.json',
              ROOT/'tests/test_echo58_percibex.py']
    names += [ROOT/p for p in CONTRACT_FILES+PREMEASUREMENT_REVIEWS]
    return {str(p.relative_to(ROOT)):sha(p) for p in names}


def prepare(stage):
    if (LAB/(stage+'-plan.json')).exists(): raise FileExistsError('stage already planned')
    LAB.mkdir(parents=True, exist_ok=True)
    if stage == 'development':
        flights = [dict(label='dev-w'+str(w), arm='MEMX', world=w, index=410+w, seed=2026102301+w) for w in range(2)]
    elif stage == 'development-recovery1':
        prior = json.loads((LAB/'development-plan.json').read_text())
        if (LAB/'development-summary.json').exists(): raise ValueError('original development already closed')
        if any((LAB/'development'/f['label']/'episode.json').exists() for f in prior['flights']):
            raise ValueError('partial results require explicit recovery review')
        flights = [dict(f, label=f['label']+'-recovery1') for f in prior['flights']]
    else:
        recovered = LAB/'development-recovery1-summary.json'
        dev = json.loads((recovered if recovered.exists() else LAB/'development-summary.json').read_text())
        if not dev['evidence_valid']: raise RuntimeError('invalid development evidence')
        flights = [dict(label='val-w'+str(w)+'-'+arm.lower(), arm=arm, world=w,
                        index=420+w, seed=2026102311+w) for w in range(2) for arm in ('MEMX','EMPTY','VISITS')]
    config = contract.configuration()
    config['candidate'] = 'percibex-r1-live-identity-inspection'
    config['profile'] = 'percibex-live-wsp16-duplex-v1'
    config['timeouts']['episode_s'] = 1500
    plan = dict(stage=stage, flights=flights, source_inventory=inventory(), configuration=config,
                max_development_flights=3, planned_development_flights=2, validation_flights=6,
                min_hits=32, memory_min=3, memory_pct=85, inspected_yaw_urad=400000,
                observed_yaw_min_urad=280000, returned_yaw_max_urad=120000,
                world_family=contract.FAMILY_PATH, rehearsal=True, old_exams_opened=False)
    save(LAB/(stage+'-plan.json'), plan)
    bundles = LAB/(stage+'-bundles'); bundles.mkdir()
    original_manifest_path = LAB/'development-bundles/manifest.json'
    if stage != 'development' and original_manifest_path.exists():
        prior_manifest = json.loads(original_manifest_path.read_text())
        shutil.copyfile(LAB/'development-bundles/consumer.pyz', bundles/'consumer.pyz')
        consumer_manifest = dict(prior_manifest['consumer'], path=str(bundles/'consumer.pyz'))
    else:
        consumer_manifest = build(bundles/'consumer.pyz')
    manifests = dict(consumer=consumer_manifest, flight=build(bundles/'flight.pyz', flight=True))
    if stage == 'development-recovery1':
        prior_manifest = json.loads((LAB/'development-bundles/manifest.json').read_text())
        required = ['echoai/echo58/percibex/'+n+'.py' for n in ('consumer','online','protocol')]+list(FROZEN)
        if manifests['consumer']['sha256'] != prior_manifest['consumer']['sha256'] or any(
            manifests['flight']['files'][k] != prior_manifest['flight']['files'][k] for k in required):
            raise ValueError('recovery changes frozen consumer or learner modules')
        save(LAB/'development-recovery1-custody.json', dict(
            original_plan_sha256=sha(LAB/'development-plan.json'),
            consumer_bundle_identical=True, learner_modules_identical=True,
            original_flight_bundle_sha256=prior_manifest['flight']['sha256'],
            corrected_flight_bundle_sha256=manifests['flight']['sha256'],
            flight_change='premeasurement correction: relative NED heading command and independent relative ENU measurement',
            interrupted_attempts=1, recovery_attempts=2,
            total_development_attempts=3, original_evidence_preserved=True,
            resource_change='explicit Podman limits, inherited cage limits and threads=1'))
    save(bundles/'manifest.json', manifests)
    return plan, bundles


def exports(path, sensors, label):
    m = Memory()
    for row in sensors['consumer']['online']['memory_records']:
        m.observe(row['i'], row['s'], row['a'], row['h'], row['o'])
        if m.records[-1] != row: raise ValueError('memory export chain')
    export_memory(m, path/'memory.wsp', provenance=dict(experiment='PERCIBE-X-r1', label=label,
        interpretation='TOGGLE=bounded-yaw-inspection; PASS=observed-success'))
    restored = load_memory(path/'memory.wsp')
    if restored.records != m.records or restored.head != m.head: raise ValueError('memory reload')
    packets = [Record(bytes.fromhex(p), dict(kind='sensor_ground', index=i))
               for i,p in enumerate(sensors['consumer']['wsp'])]
    bridge = json.loads((path/'bridge.json').read_text())
    for b in bridge:
        for direction in ('input','output'):
            packets.append(Record(bytes.fromhex(b[direction]), dict(kind='control', direction=direction,
                                                                   after_frames=b['after_frames'])))
    a = Archive('wsp16-session-v1', dict(experiment='PERCIBE-X-r1', label=label), tuple(packets),
                dict(ground_packets=len(sensors['consumer']['wsp']), control_exchanges=len(bridge)))
    write(path/'session.wsp', a)
    if read(path/'session.wsp') != a: raise ValueError('session reload')
    save(path/'wsp-reload.json', dict(memory_records=len(m.records), memory_head=m.head,
                                    memory_reloaded=True, session_packets=len(packets), session_reloaded=True))


def run(stage, bounded_cage_path, resource_details):
    plan, bundles = prepare(stage)
    runtime_lock = json.loads((ROOT/'lab/flight1s-v6/lock.json').read_text())
    flight = Runtime(available=True, lock=runtime_lock['runtime'])
    cage = simruntime.preflight(write=False)
    cage.require()
    cage.lock['sandbox']['path'] = bounded_cage_path
    isolation = sandbox.self_test(cage)
    if not isolation['ok'] or not model.check()['ok']: raise RuntimeError('isolation/model preflight')
    save(LAB/(stage+'-runtime.json'), dict(cage=cage.lock, isolation=isolation, model=model.check(),
                                         flight=runtime_lock['runtime'], resource_limits=resource_details,
                                         boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
    if stage.startswith('development'):
        live = LAB/(stage+'-live.log')
        live.touch(exist_ok=False)
        session.Forwarder.live_path = live
        launched = subprocess.Popen(['xfce4-terminal', '--disable-server', '--geometry=105x28',
            '--title=PERCIBE-X: WSP observados en vivo', '-e', 'tail -F '+str(live)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        save(LAB/(stage+'-mini-terminal.json'), dict(command='tail -F '+str(live), launcher_pid=launched.pid,
                                           read_only=True))
    else:
        session.Forwarder.live_path = None
    assignments = list(dict.fromkeys(('B',f['index'],f['seed']) for f in plan['flights']))
    generated = generate_suite(LAB/(stage+'-worlds'), load_protocol(WORLD_PROTOCOL), REHEARSAL_SECRET,
                               assignments, family_path=ROOT/contract.FAMILY_PATH)
    packages = {g.index:g for g in generated}
    results, errors = [], []
    for f in plan['flights']:
        resource_availability = wait_for_memory()
        label = f['label']; path = LAB/stage/label; path.mkdir(parents=True)
        g = packages[f['index']]
        save(path/'meta.json', dict(f, package_path=str(g.path), package_sha256=g.package.package_sha256,
                                   resource_availability=resource_availability))
        spec = contract.spec(sensor.schedule(f['seed'], False))
        print(json.dumps(dict(event='flight_start', stage=stage, **f)), flush=True)
        t0 = time.monotonic()
        try:
            ep, sensors = session.run_episode(flight, cage, g, plan['configuration'], spec,
                arm=f['arm'], label=label, root=path, consumer_path=bundles/'consumer.pyz', tap_path=bundles/'flight.pyz')
            save(path/'episode.json', ep.trace()); save(path/'sensors.json', dict(sensors, spec=spec))
            if any(not r.get('ok',False) for r in sensors.get('operational_cleanup',[])):
                raise RuntimeError('operational cleanup uncertain; stop stage before another container')
            exports(path, sensors, label)
            result = inspect(path)
            save(path/'evaluation.json', result); results.append(result)
            print(json.dumps(dict(event='flight_end', label=label, evidence_valid=result['evidence_valid'],
                recognition=result['recognition'], physical=result['physical']['phases'],
                wall_s=round(time.monotonic()-t0,2))), flush=True)
        except Exception as exc:
            error = dict(label=label, error=type(exc).__name__+': '+str(exc))
            save(path/'error.json', error); errors.append(error)
            print(json.dumps(dict(event='flight_error', **error)), flush=True)
            break
    unchanged = inventory() == plan['source_inventory']
    summary = dict(stage=stage, results=results, errors=errors, source_unchanged=unchanged,
                   evidence_valid=not errors and unchanged and len(results)==len(plan['flights']) and all(r['evidence_valid'] for r in results))
    summary['artifact_inventory'] = {str(p):sha(p) for p in sorted((LAB/stage).rglob('*')) if p.is_file()}
    save(LAB/(stage+'-summary.json'), summary)
    print(json.dumps({k:v for k,v in summary.items() if k != 'results'}, sort_keys=True), flush=True)
    return 0 if summary['evidence_valid'] else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('dev','recover-dev','validate'))
    args = parser.parse_args()
    stage = {'dev':'development', 'recover-dev':'development-recovery1', 'validate':'validation'}[args.stage]
    host = supervisor_limits()
    if not host['bounded']:
        raise RuntimeError('supervisor requires cgroup MemoryMax<=2G and MemoryHigh<=1536M before preflight')
    base = simruntime.Runtime(available=True, lock={'sandbox':{'path':shutil.which('bwrap')}})
    wait_for_memory()
    with active(base, LAB/'resource-bin-v2', LAB/'resource-launches.jsonl') as (bounded, details):
        details['supervisor'] = host
        return run(stage, bounded.lock['sandbox']['path'], details)


if __name__ == '__main__': raise SystemExit(main())
