"""Fixed local storage study: no game runner, model, API or sealed exam."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import statistics
import sys
import time
import zlib

from ..memx.memory import Memory
from . import codec as c
from .memory import compare_decisions, memory_archive, restore_memory

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT/'lab/echo58/wspfiles/20261023-r1'
SESSION_ROOT = Path('lab/echo58/enjambre2/dev-20261022-r1/rounds')
SESSION_JOBS = ('honesto-none-m1', 'prudente-false_safe-m1', 'oraculo-false_remote-m3')
MEMORY_SOURCE = Path('lab/echo58/memx/memories/aprendida-m01.jsonl')
ARMS = ('wsp', 'json', 'wsp-zlib', 'json-zlib')
REPLICAS = 9
OPERATIONS = ('encode', 'decode', 'read_decode', 'read_packet', 'resident_packet')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def save(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(raw)


def save_json(path, value): save(path, c.dumps(value)+b'\n')


def event(root, kind, **fields):
    row = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'kind': kind, **fields}
    with (root/'observations.jsonl').open('ab') as f: f.write(c.dumps(row)+b'\n')
    print(json.dumps(row, ensure_ascii=False), flush=True)


def session_archive(raw, source, source_hash):
    data = c.loads(raw)
    records = []
    for pub in data['publications']:
        for role in ('original', 'sent'):
            metadata = {k: v for k, v in pub.items() if k not in ('original', 'sent')}
            metadata['packet_role'] = role
            records.append(c.Record(bytes.fromhex(pub[role]), metadata))
    return c.Archive('wsp16-session-v1',
        {'source': str(source), 'source_sha256': source_hash, 'source_array': 'publications'},
        tuple(records), {'source_round': data['round']['round'],
                         'historical_timestamps': 'absent in source'})


def signed_json(a):
    raw = c.to_json(a).encode('utf-8')
    return raw + hashlib.sha256(raw).digest()


def json_payload(raw):
    c.require(type(raw) is bytes and 32 <= len(raw) <= c.MAX_FILE, 'JSON receipt size')
    c.require(hashlib.sha256(raw[:-32]).digest() == raw[-32:], 'JSON receipt checksum')
    return raw[:-32]


def encode_arm(archive, arm):
    raw = c.encode(archive) if arm.startswith('wsp') else signed_json(archive)
    return zlib.compress(raw, 9) if arm.endswith('-zlib') else raw


def unpack_arm(raw, arm):
    return c.decompress(raw) if arm.endswith('-zlib') else raw


def decode_arm(raw, arm):
    raw = unpack_arm(raw, arm)
    return c.decode(raw) if arm.startswith('wsp') else c.from_json(json_payload(raw))


def selective_packet(raw, arm, index):
    raw = unpack_arm(raw, arm)
    if arm.startswith('wsp'): return c.packet_at(raw, index)
    # Same selective contract as binary: verify receipt, parse structure needed
    # to locate one packet, do not materialize/interpret every other packet.
    payload = json_payload(raw)
    try:
        data = json.loads(payload.decode('utf-8'), object_pairs_hook=c._pairs, parse_constant=c._constant)
        c.require(type(data) is list and len(data) == 5 and type(data[0]) is int and data[0] == 1,
                  'selective JSON version/schema')
        c.require(type(data[4]) is list and len(data[4]) <= c.MAX_RECORDS, 'selective records limit')
        c._descriptor(c.Archive(data[1], data[2], (), data[3]))
        c.require(type(index) is int and 0 <= index < len(data[4]), 'packet index bounds')
        row = data[4][index]
        c.require(type(row) is list and len(row) == 2 and type(row[0]) is str
                  and c.re.fullmatch('[0-9a-f]{32}', row[0]), 'selective packet hex')
        return bytes.fromhex(row[0])
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('selective JSON parse') from exc


def summary(samples):
    def p95(values):
        return sorted(values)[(95*len(values)+99)//100-1]
    return {metric: {'median': statistics.median(s[metric] for s in samples),
                     'p95': p95([s[metric] for s in samples])}
            for metric in ('wall_ns', 'process_ns')}


def measure(call):
    wall = time.perf_counter_ns(); cpu = time.process_time_ns()
    value = call()
    elapsed_cpu = time.process_time_ns()-cpu; elapsed_wall = time.perf_counter_ns()-wall
    return value, {'wall_ns': elapsed_wall, 'process_ns': elapsed_cpu}


def run(output=DEFAULT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    event(output, 'observation', scope='fixed development and training storage only',
          token_R2='closed red; no new tokenizer measurement')
    manifest = {'version': 1, 'replicas': REPLICAS, 'arms': list(ARMS),
                'operations': list(OPERATIONS), 'sources': [], 'code': [], 'artifacts': {},
                'environment': {'python': sys.version, 'executable': sys.executable,
                    'platform': platform.platform(), 'zlib': zlib.ZLIB_RUNTIME_VERSION},
                'timing_scope': 'warm filesystem cache; sequential local process; no cold I/O claim'}
    code_paths = sorted(Path(__file__).parent.glob('*.py')) + [
        ROOT/'tests/test_echo58_wspfiles.py', ROOT/'echo58/memx/memory.py', ROOT/'echo58/memx/agent.py',
        ROOT.parent/'navi10_wsp.py', ROOT.parent/'navi10_qn.py',
        ROOT/'ECHO-5.8/docs/WSPFILES-DESIGN-20261023.md', ROOT/'ECHO-5.8/docs/WSPFILES-PLAN-20261023.md']
    for i, source in enumerate(code_paths):
        raw = source.read_bytes(); dest = Path('sources')/f'{i:02d}-{source.name}'
        save(output/dest, raw)
        manifest['code'].append({'source': str(source), 'snapshot': str(dest), 'sha256': sha(raw)})
    archives = {}
    source_paths = [SESSION_ROOT/job/'r01.json' for job in SESSION_JOBS]+[MEMORY_SOURCE]
    for source in source_paths:
        raw = (ROOT/source).read_bytes()
        name = source.parent.name if source != MEMORY_SOURCE else 'memory-training-m01'
        dest = Path('corpus')/(name+source.suffix)
        save(output/dest, raw)
        manifest['sources'].append({'source': str(source), 'snapshot': str(dest), 'sha256': sha(raw), 'name': name})
        if source == MEMORY_SOURCE:
            memory = Memory.load(output/dest)
            archives[name] = memory_archive(memory, {'source': str(source), 'source_sha256': sha(raw),
                'source_kind': 'training memory; postcards generated at export'})
        else: archives[name] = session_archive(raw, source, sha(raw))
    save_json(output/'preflight.json', manifest)
    event(output, 'action', action='sources and contract fixed before timing',
          preflight_sha256=sha((output/'preflight.json').read_bytes()))
    results = {'version': 1, 'datasets': {}, 'integration': {}, 'replicas': REPLICAS}
    for name, a in archives.items():
        c.require(len(a.records)>0, 'fixed corpus has no packets')
        payloads = {}; paths = {}; residents = {}
        ds = {'records': len(a.records), 'json_without_receipt_bytes': len(c.to_json(a).encode()), 'arms': {}}
        for arm in ARMS:
            raw = encode_arm(a, arm)
            c.require(decode_arm(raw, arm) == a, 'lossless gate failed')
            index = len(a.records)//2
            c.require(selective_packet(raw, arm, index) == a.records[index].packet, 'selective gate failed')
            suffix = {'wsp': '.wsp', 'json': '.json.sha256', 'wsp-zlib': '.wsp.zlib', 'json-zlib': '.json.sha256.zlib'}[arm]
            dest = Path('artifacts')/(name+suffix); save(output/dest, raw)
            manifest['artifacts'][str(dest)] = {'sha256': sha(raw), 'bytes': len(raw), 'dataset': name, 'arm': arm}
            payloads[arm] = raw; paths[arm] = output/dest; residents[arm] = decode_arm(raw, arm)
            ds['arms'][arm] = {'bytes': len(raw), 'samples': {op: [] for op in OPERATIONS}}
        # One unrecorded warm-up per arm/operation, then rotating balanced order.
        def operation(arm, op):
            if op == 'encode': return encode_arm(a, arm)
            if op == 'decode': return decode_arm(payloads[arm], arm)
            if op == 'read_decode': return decode_arm(c.read_bytes(paths[arm]), arm)
            if op == 'read_packet': return selective_packet(c.read_bytes(paths[arm]), arm, index)
            return residents[arm].records[index].packet
        for op in OPERATIONS:
            for arm in ARMS: operation(arm, op)
            for replica in range(REPLICAS):
                order = ARMS[replica % 4:] + ARMS[:replica % 4]
                if replica % 2: order = tuple(reversed(order))
                for arm in order:
                    value, sample = measure(lambda: operation(arm, op))
                    if op in ('decode', 'read_decode'): c.require(value == a, 'timed decode mismatch')
                    if op in ('read_packet', 'resident_packet'): c.require(value == a.records[index].packet, 'timed packet mismatch')
                    if op == 'encode': c.require(value == payloads[arm], 'nondeterministic encoding')
                    ds['arms'][arm]['samples'][op].append({'replica': replica, **sample})
        for arm in ARMS:
            ds['arms'][arm]['timing'] = {op: summary(ds['arms'][arm]['samples'][op]) for op in OPERATIONS}
        ds['lossless'] = True
        results['datasets'][name] = ds
        event(output, 'result', dataset=name, records=len(a.records),
              bytes={arm: ds['arms'][arm]['bytes'] for arm in ARMS}, lossless=True)
    original = Memory.load(output/manifest['sources'][-1]['snapshot'])
    restored = restore_memory(c.read(output/'artifacts/memory-training-m01.wsp'))
    results['integration'] = compare_decisions(original, restored)
    c.require(results['integration']['mismatches'] == 0 and results['integration']['source_hits'] > 0,
              'Agent memory integration failed')
    save_json(output/'manifest.json', manifest)
    save_json(output/'results.json', results)
    event(output, 'result', action='existing Agent consumed reloaded .wsp memory',
          **{k: v for k, v in results['integration'].items() if k != 'probes'})
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, default=DEFAULT)
    args = p.parse_args(); run(args.output)


if __name__ == '__main__': main()
