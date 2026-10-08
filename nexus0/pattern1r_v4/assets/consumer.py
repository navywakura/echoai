"""PATTERN-1R v2 isolated consumer. Same sensor framing and WSP translation;
real circular beam sets, one-to-one tracks, and a 16-bit size signature.
Sighting beam provenance stays internal for evaluator reconstruction. The
learner receives only the signature, never geometry or an object label.
"""
import hashlib
import json
import math
from math import isqrt
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
# Silhouettes: a run of returns with no big jump, at least this many beams.
SEG_JUMP_MM = 300          # floor; the real limit grows with range
SEG_JUMP_DIV = 8           # ... by one eighth of it, so oblique faces stay whole
SEG_MIN_BEAMS = 3
SEG_GAP_BEAMS = 4          # beams without echo that do not end a silhouette
SEG_BUCKET_MM = 300        # one bit of the signature
SEG_FIRST_MM = 400
SEG_BUCKETS = 16
TRACK_BEAMS = 6            # a track may drift this many beams between scans
TRACK_RANGE_MM = 900
TRACK_SETTLED = 0          # scans without growth before a track says anything
EMIT_MIN_BEAMS = 4         # a fragment of a surface is not a sighting
# The body's public sensor spec, as in GROUND-1: 360 beams from -180 deg in
# 1 deg steps. The wire carries ranges only, so the geometry is a fixed
# integer table: no floating point once a scan arrives.
UNIT = 1024
COS = [int(round(math.cos(math.radians(-180 + i)) * UNIT)) for i in range(360)]
SIN = [int(round(math.sin(math.radians(-180 + i)) * UNIT)) for i in range(360)]
CHANGE_MM_S2 = 2000
WINDOW_NS = 100_000_000
BASELINE_NS = 1_000_000_000


def pack(src, rel, dst, time, E, flags=0, domain=0, generator=0, style=0, slot=0, seq=0):
    ev = [max(-100, min(100, int(E.get(k, 0)))) for k in E_NAMES]
    return struct.pack('<BBBBbbbbbbBBBBBB', src & 0xFF, rel & 0xFF, dst & 0xFF, time & 0xFF,
                       *ev, flags & 0xFF, domain & 0xFF, generator & 0xFF, style & 0xFF,
                       slot & 0xFF, seq & 0xFF)


def gray(n):
    return (n ^ (n >> 1)) & 0xFFFF


def segments(values):
    """Actual echoes in circular order, each used in at most one segment."""
    mm = [int(round(v*1000)) if math.isfinite(v) and v > 0 else None for v in values]
    ids = [i for i, r in enumerate(mm) if r is not None]
    if not ids:
        return []
    def broken(a, b):
        return ((b-a-1) % len(mm) > SEG_GAP_BEAMS or
                abs(mm[b]-mm[a]) > max(SEG_JUMP_MM, mm[a]//SEG_JUMP_DIV))
    cut = next((k for k, b in enumerate(ids) if broken(ids[k-1], b)), 0)
    ids = ids[cut:]+ids[:cut]
    runs, cur = [], []
    for i in ids:
        if cur and broken(cur[-1], i):
            if len(cur) >= SEG_MIN_BEAMS:
                runs.append(tuple(cur))
            cur = []
        cur.append(i)
    if len(cur) >= SEG_MIN_BEAMS:
        runs.append(tuple(cur))
    return runs


def width_of(values, beams):
    i, j = beams[0], beams[-1]
    a, b = int(round(values[i]*1000)), int(round(values[j]*1000))
    x0, y0 = a*COS[i]//UNIT, a*SIN[i]//UNIT
    x1, y1 = b*COS[j]//UNIT, b*SIN[j]//UNIT
    return isqrt((x1-x0)**2+(y1-y0)**2)


def silhouettes(values):
    """Compatibility view; tracking and scoring use the actual beam sets."""
    return [(b[0], len(b), width_of(values, b)) for b in segments(values)]


def signature(width_mm):
    """Thermometer code of the size: the Hamming distance between two
    signatures is the difference in buckets, which is what a Hamming-3
    memory needs to join the same object and keep two apart."""
    bucket = 0 if width_mm < SEG_FIRST_MM else min(
        SEG_BUCKETS, 1 + (width_mm - SEG_FIRST_MM) // SEG_BUCKET_MM)
    return ((1 << bucket) - 1) & 0xFFFF


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
        self.sightings = []
        self.sighting_beams = []  # internal audit provenance, never in the report
        self.held = None
        self.tracks = []           # [centre, range mm, widest mm, scans since it grew]

    def record(self, source, capture_ns, status, gap, valid, values):
        if gap > 0 or status == 'stale' or not valid:
            self.marked = True
        if source == 'imu' and valid and status == 'ok' and len(values) >= 2 \
                and math.isfinite(values[0] * 1000) and math.isfinite(values[1] * 1000):
            ax, ay = values[0], values[1]
            self.imu.append((capture_ns, int(round(ax * 1000)), int(round(ay * 1000))))
        elif source == 'lidar':
            ok = valid and status == 'ok'
            if ok and len(values) == len(COS):
                self.track(capture_ns, values)
            front = [int(round(values[i] * 1000)) for i in FRONT
                     if ok and i < len(values) and math.isfinite(values[i])]
            self.turn(capture_ns, ok, bool(front) and min(front) < NEAR_MM)

    def track(self, capture_ns, values):
        observations = []
        for beams in segments(values):
            centre = (beams[0] + ((beams[-1]-beams[0]) % len(COS))//2) % len(COS)
            near = min(int(round(values[i]*1000)) for i in beams)
            observations.append((beams, centre, near, width_of(values, beams)))
        candidates = []
        for i, (_, centre, near, _) in enumerate(observations):
            for j, old in enumerate(self.tracks):
                d = abs((centre-old[0]+180) % 360-180)
                dr = abs(near-old[1])
                if d <= TRACK_BEAMS and dr <= TRACK_RANGE_MM:
                    candidates.append((d*TRACK_RANGE_MM+dr*TRACK_BEAMS, i, j))
        assignment, used = {}, set()
        for _, i, j in sorted(candidates):
            if i not in assignment and j not in used:
                assignment[i] = j
                used.add(j)
        live = []
        for i, (beams, centre, near, width) in enumerate(observations):
            best = list(self.tracks[assignment[i]]) if i in assignment else [centre, near, 0, 0]
            best[0], best[1] = centre, near
            if width > best[2]:
                best[2], best[3] = width, 0
            else:
                best[3] += 1
            if self.mutant == 'constant_family':
                best[2] = 1000
            size = near if self.mutant == 'range_leak' else best[2]
            sig = signature(size)
            if self.mutant == 'beam_index':
                sig = ((1 << (beams[0]//24))-1) & 0xFFFF
            if self.mutant == 'replay' and self.sightings:
                sig = self.sightings[-1][1]
            if best[3] >= TRACK_SETTLED and len(beams) >= EMIT_MIN_BEAMS:
                self.sightings.append([capture_ns, sig])
                self.sighting_beams.append(beams)
            live.append(best)
        self.tracks = live

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
    out['sightings'] = ground.sightings
    if MUTANT == 'extra_channel':
        out['debug'] = dict(turns=ground.count)
    sys.stderr.write(json.dumps(out, sort_keys=True) + '\n')
    sys.stderr.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
