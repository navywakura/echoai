"""GROUND-1 consumer: runs in the SIM-3 cage, checks what SENSOR-1S sends and
translates it into WSP. Trusts nothing it reads.

stdin is the one wire. The framing and every check are SENSOR-1S v1's
consumer: schema, payload hash, seq chain, capture order, declared gaps,
stale and invalid counts. On top of that, every delivered LiDAR scan becomes
one 16-byte WSP packet, computed only from records already received:

    rel  CAMBIAR      horizontal acceleration left its median of the last
                      second by more than 2 m/s^2 in the last 100 ms
         DESCONOCIDO  this scan is stale or invalid
         OBSERVAR     otherwise
    dst  ALLI         some valid beam within 30 deg of the nose is < 4 m
         FUERA        none is
    E    C 100, or 40 if any record since the last packet had a gap, was
         stale or was invalid; U 40 near / 0 far; A 80 with CAMBIAR / 10

seq, slot, style and flags are 0: neither a counter nor a place. Sensor
floats are quantised to integers (mm, mm/s^2) before any decision. The only
output is one JSON report on stderr: SENSOR-1S's tally plus the packets.

Stdlib only; mounted read-only at /probe/probe.py by the cage. The evaluator
loads this same file to recompute the packets from the private raw samples.
"""
import hashlib
import json
import math
import os
import struct
import sys

KEYS = {'v', 'source', 'seq', 'capture_ns', 'delivered_ns', 'gap', 'status',
        'noise_ref', 'shape', 'format', 'payload_len', 'payload_sha256'}
SOURCES = ('imu', 'rgb', 'depth', 'lidar')
MAX_HEADER = 512
MAX_PAYLOAD = 256 * 1024
MUTANT = os.environ.get('GROUND1_MUTANT', '')

# echoai.core.wsp atoms and the 16-byte layout ("<BBBBbbbbbbBBBBBB"); tests assert identity.
YO, AHORA, CAMBIAR, OBSERVAR, DESCONOCIDO, ALLI, FUERA = 2, 8, 13, 14, 31, 5, 7
DOMAIN_PHYSICAL, GENERATOR_GROUND = 7, 0x06
E_NAMES = ('V', 'A', 'D', 'C', 'U', 'B')

# The body's public sensor spec, not world truth: 360 beams from -180 deg in
# 1 deg steps, beam 180 on the nose.
FRONT = range(150, 211)
NEAR_MM = 4000
CHANGE_MM_S2 = 2000
WINDOW_NS = 100_000_000
BASELINE_NS = 1_000_000_000


def pack(src, rel, dst, time, E, flags=0, domain=0, generator=0, style=0, slot=0, seq=0):
    ev = [max(-100, min(100, int(E.get(k, 0)))) for k in E_NAMES]
    return struct.pack('<BBBBbbbbbbBBBBBB', src & 0xFF, rel & 0xFF, dst & 0xFF, time & 0xFF,
                       *ev, flags & 0xFF, domain & 0xFF, generator & 0xFF, style & 0xFF,
                       slot & 0xFF, seq & 0xFF)


def median(xs):
    xs = sorted(xs)
    return xs[(len(xs) - 1) // 2]


class Ground:
    """Decoded records in, packets out. Pure: the evaluator feeds it the same
    records rebuilt from the private samples and must get the same bytes."""

    def __init__(self, mutant=''):
        self.mutant = mutant
        self.imu = []
        self.marked = False
        self.count = 0
        self.packets = []
        self.held = None

    def record(self, source, capture_ns, status, gap, valid, values):
        if gap > 0 or status == 'stale' or not valid:
            self.marked = True
        if source == 'imu' and valid and status == 'ok' and len(values) >= 2 \
                and math.isfinite(values[0] * 1000) and math.isfinite(values[1] * 1000):
            ax, ay = values[0], values[1]
            self.imu.append((capture_ns, int(round(ax * 1000)), int(round(ay * 1000))))
        elif source == 'lidar':
            ok = valid and status == 'ok'
            front = [int(round(values[i] * 1000)) for i in FRONT
                     if ok and i < len(values) and math.isfinite(values[i])]
            self.turn(capture_ns, ok, bool(front) and min(front) < NEAR_MM)

    def turn(self, t, lidar_ok, near):
        base = [s for s in self.imu if t - BASELINE_NS - WINDOW_NS <= s[0] < t - WINDOW_NS]
        now = [s for s in self.imu if t - WINDOW_NS <= s[0] <= t]
        change = False
        if base and now:
            bx, by = median([s[1] for s in base]), median([s[2] for s in base])
            change = any((s[1]-bx)**2 + (s[2]-by)**2 > CHANGE_MM_S2**2 for s in now)
        self.imu = [s for s in self.imu if s[0] >= t - BASELINE_NS - WINDOW_NS]
        if self.mutant == 'imu_blind':
            change = False
        if self.mutant == 'constant_percept':
            near = False
        if self.mutant == 'lookahead':
            # Emits each turn with the next scan's distance: a future the cage
            # had not been sent yet. Same count as honest (close() flushes the
            # last turn), so only the lookahead itself differs.
            held, self.held = self.held, (t, lidar_ok, near, change, self.marked)
            self.marked = False
            if held is None:
                return
            t, lidar_ok, _, change, marked = held
            self.emit(lidar_ok, near, change, marked)
            return
        self.emit(lidar_ok, near, change, self.marked)
        self.marked = False

    def close(self):
        """End of stream. Only the lookahead mutant still holds a turn."""
        if self.held is not None:
            _, lidar_ok, near, change, marked = self.held
            self.held = None
            self.emit(lidar_ok, near, change, marked)

    def emit(self, lidar_ok, near, change, marked):
        if not lidar_ok:
            rel = dst = DESCONOCIDO
        else:
            rel = CAMBIAR if change else OBSERVAR
            dst = ALLI if near else FUERA
        c = 100 if (not marked or self.mutant == 'certainty_lie') else 40
        e = dict(C=c, U=40 if dst == ALLI else 0, A=80 if rel == CAMBIAR else 10)
        seq = self.count & 0xFF if self.mutant == 'seq_counter' else 0
        self.packets.append(pack(YO, rel, dst, AHORA, e, domain=DOMAIN_PHYSICAL,
                                 generator=GENERATOR_GROUND, seq=seq).hex())
        self.count += 1


def decode(source, payload):
    if source == 'imu' and len(payload) == 48:
        return struct.unpack('<6d', payload)
    if source == 'lidar' and len(payload) % 4 == 0:
        return struct.unpack('<%df' % (len(payload) // 4), payload)
    return ()


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
    ground = Ground(MUTANT)
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
        if not isinstance(s, str) or s not in per:
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
        valid = hashlib.sha256(payload).hexdigest() == h['payload_sha256']
        if not valid:
            p['invalid'] += 1
        if p['last_capture'] is not None and h['capture_ns'] < p['last_capture']:
            p['non_monotonic'] += 1
        p['last_capture'] = h['capture_ns']
        p['latencies'].append(h['delivered_ns'] - h['capture_ns'])
        ground.record(s, h['capture_ns'], h['status'], h['gap'], valid,
                      decode(s, payload) if valid else ())
    out = dict(frames=frames, schema_errors=schema_errors, unknown_source=unknown_source,
               truncated=truncated, header_digest=digest.hexdigest(), sources={})
    for s, p in per.items():
        lat = p.pop('latencies')
        p.pop('last_seq'); p.pop('last_capture')
        p.update(negative_latency=sum(x < 0 for x in lat),
                 latency_p50_ns=percentile(lat, 50), latency_p99_ns=percentile(lat, 99),
                 latency_max_ns=max(lat) if lat else None)
        out['sources'][s] = p
    ground.close()
    out['wsp'] = ground.packets
    if MUTANT == 'extra_channel':
        out['debug'] = dict(turns=ground.count)
    sys.stderr.write(json.dumps(out, sort_keys=True) + '\n')
    sys.stderr.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
