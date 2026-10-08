"""Executable negative controls, never connected to an actuator."""
import json
from pathlib import Path
import shutil
import tempfile
from .functional import episode, fixture
from .evaluate import audit


def mutants(model):
    source = (Path(__file__).parent/'core.py').read_text()
    variants = {
        'sensor_ttl': ("not 0 <= now-health['sensor_ns'] <= TTL", "False", 'sensor_stale'),
        'link_health': ("not telemetry(frame, now)", "False", 'network_stale'),
        'process_health': ("if not health['worker_alive']:", "if False:", 'process_dead'),
        'power_veto': ("if (type(energy) is not dict", "if False and (type(energy) is not dict", 'low_energy'),
        'latch': ("self.tripped = True", "self.tripped = False", 'process_timeout'),
        'unconditional_heartbeat': ("return not self.revoked", "return True", None),
    }
    results = {}
    for name, (old, new, case) in variants.items():
        if source.count(old) != 1:
            raise ValueError('mutation anchor '+name)
        namespace = {}
        exec(compile(source.replace(old, new), '<safe1-mutant-'+name+'>', 'exec'), namespace)
        if name == 'link_health':
            health = fixture(20263401)[0]
            health['frame']['received_ns'] -= 250_000_001
            # Continuous idle supervision, before Gateway has a pending goal.
            detected = namespace['Supervisor'](model).check(health)
        elif case:
            detected = not episode(model, 20263401, case, namespace['Supervisor'])['ok']
        else:
            lease = namespace['Lease']()
            lease.renew(0)
            detected = lease.allowed(500_000_000)
        results[name] = bool(detected)
    return results


def corruptions(root):
    results = {}
    for name in ('health', 'permission', 'ulog', 'outcome'):
        with tempfile.TemporaryDirectory(prefix='safe1-audit-') as directory:
            target = Path(directory)/'session'
            shutil.copytree(root, target, symlinks=True)
            trace = target/'out/trace.jsonl'
            rows = [json.loads(line) for line in trace.read_text().splitlines()]
            if name == 'health':
                next(r for r in rows if r['kind'] == 'check')['health']['frame']['position_mm'][0] += 1500
            elif name == 'permission':
                next(r for r in rows if r['kind'] == 'proposal')['decision']['allowed'] ^= True
            elif name == 'ulog':
                path = next(target.rglob('*.ulg'))
                with path.open('ab') as output:
                    output.write(b'corrupted')
            else:
                path = target/'out/result.json'
                value = json.loads(path.read_text())
                value['ok'] = False
                path.write_text(json.dumps(value))
            trace.write_text(''.join(json.dumps(r, sort_keys=True)+'\n' for r in rows))
            results[name] = not audit(target)['valid']
    return results
