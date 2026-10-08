"""SENSOR-1S consumer: runs in the SIM-3 cage and trusts nothing it reads.

stdin is the one wire. Each frame is a 4-byte big-endian header length, a
JSON header, a 4-byte big-endian payload length and the payload. The
consumer checks the schema, recomputes the payload hash, checks the seq
chain and capture-time order per source, adds up the declared gaps and
counts stale and invalid records. At EOF it writes one JSON tally to
stderr, the one-way report. It never writes back down the wire.

Stdlib only; mounted read-only at /probe/probe.py by the cage.
"""
import hashlib
import json
import sys

KEYS = {'v', 'source', 'seq', 'capture_ns', 'delivered_ns', 'gap', 'status',
        'noise_ref', 'shape', 'format', 'payload_len', 'payload_sha256'}
SOURCES = ('imu', 'rgb', 'depth', 'lidar')
MAX_HEADER = 512
MAX_PAYLOAD = 256 * 1024


def read_exact(stream, n):
    buf = b''
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            return None if not buf else b''
        buf += chunk
    return buf


def percentile(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, (len(xs) * q) // 100)]


def main():
    stream = sys.stdin.buffer
    per = {s: dict(n=0, seq_breaks=0, gap_sum=0, stale=0, invalid=0,
                   non_monotonic=0, latencies=[], last_seq=None, last_capture=None)
           for s in SOURCES}
    schema_errors, frames, unknown_source = 0, 0, 0
    digest = hashlib.sha256()
    truncated = False
    while True:
        raw = read_exact(stream, 4)
        if raw is None:
            break
        if len(raw) < 4:
            truncated = True
            break
        hlen = int.from_bytes(raw, 'big')
        if hlen > MAX_HEADER:
            schema_errors += 1
            truncated = True
            break
        header_bytes = read_exact(stream, hlen)
        plen_raw = read_exact(stream, 4)
        if not header_bytes or not plen_raw or len(plen_raw) < 4:
            truncated = True
            break
        plen = int.from_bytes(plen_raw, 'big')
        if plen > MAX_PAYLOAD:
            schema_errors += 1
            truncated = True
            break
        payload = read_exact(stream, plen) if plen else b''
        if payload is None or len(payload) != plen:
            truncated = True
            break
        frames += 1
        digest.update(raw + header_bytes)
        try:
            h = json.loads(header_bytes)
        except ValueError:
            schema_errors += 1
            continue
        if not isinstance(h, dict) or set(h) != KEYS or h.get('v') != 2:
            schema_errors += 1
            continue
        s = h['source']
        if s not in per:
            unknown_source += 1
            continue
        p = per[s]
        ints = all(isinstance(h[k], int) and not isinstance(h[k], bool) and h[k] >= 0
                   for k in ('seq', 'capture_ns', 'delivered_ns', 'gap', 'payload_len'))
        if not ints or h['status'] not in ('ok', 'stale') or h['payload_len'] != plen:
            schema_errors += 1
            continue
        p['n'] += 1
        if p['last_seq'] is not None and h['seq'] != p['last_seq'] + 1:
            p['seq_breaks'] += 1
        p['last_seq'] = h['seq']
        p['gap_sum'] += h['gap']
        if h['status'] == 'stale':
            p['stale'] += 1
        if hashlib.sha256(payload).hexdigest() != h['payload_sha256']:
            p['invalid'] += 1
        if p['last_capture'] is not None and h['capture_ns'] < p['last_capture']:
            p['non_monotonic'] += 1
        p['last_capture'] = h['capture_ns']
        p['latencies'].append(h['delivered_ns'] - h['capture_ns'])
    out = dict(frames=frames, schema_errors=schema_errors, unknown_source=unknown_source,
               truncated=truncated, header_digest=digest.hexdigest(), sources={})
    for s, p in per.items():
        lat = p.pop('latencies')
        p.pop('last_seq'); p.pop('last_capture')
        p.update(negative_latency=sum(x < 0 for x in lat),
                 latency_p50_ns=percentile(lat, 50), latency_p99_ns=percentile(lat, 99),
                 latency_max_ns=max(lat) if lat else None)
        out['sources'][s] = p
    sys.stderr.write(json.dumps(out, sort_keys=True) + '\n')
    sys.stderr.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
