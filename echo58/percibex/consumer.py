"""Caged reader: updates happen between frame read and next frame read."""
import hashlib
import json
import os
import sys
from echoai.nexus0.pattern1r_v4.assets import consumer as G
from .online import Online

CONTROL_KEYS = {'v', 'source', 'payload_len', 'payload_sha256'}


def main():
    ground, online = G.Ground(''), Online(os.environ.get('PERCIBEX_ARM', 'MEMX'))
    stream = sys.stdin.buffer
    frames = errors = invalid = 0
    digest = hashlib.sha256()
    while True:
        raw = G.read_exact(stream, 4)
        if raw is None: break
        if len(raw) != 4: raise ValueError('truncated prefix')
        n = int.from_bytes(raw, 'big')
        if not 1 <= n <= G.MAX_HEADER: raise ValueError('header limit')
        hb, plen = G.read_exact(stream, n), G.read_exact(stream, 4)
        if not hb or not plen or len(plen) != 4: raise ValueError('truncated header')
        np = int.from_bytes(plen, 'big')
        if np > G.MAX_PAYLOAD: raise ValueError('payload limit')
        payload = G.read_exact(stream, np) if np else b''
        if payload is None or len(payload) != np: raise ValueError('truncated payload')
        h = json.loads(hb)
        if set(h) == CONTROL_KEYS and h['v'] == 1 and h['source'] == 'wsp':
            if np != 16 or h['payload_len'] != 16 or hashlib.sha256(payload).hexdigest() != h['payload_sha256']:
                raise ValueError('control payload')
            os.write(sys.stdout.fileno(), online.control(payload))
            continue
        frames += 1
        digest.update(raw+hb)
        if set(h) != G.KEYS or h['v'] != 2 or h['source'] not in G.SOURCES:
            errors += 1; continue
        if not all(type(h[k]) is int and h[k] >= 0 for k in ('seq','capture_ns','delivered_ns','gap','payload_len')):
            errors += 1; continue
        if h['status'] not in ('ok','stale') or h['payload_len'] != np:
            errors += 1; continue
        valid = hashlib.sha256(payload).hexdigest() == h['payload_sha256']
        invalid += not valid
        online.now = max(online.now, h['capture_ns'])
        before = len(ground.sightings)
        ground.record(h['source'], h['capture_ns'], h['status'], h['gap'], valid,
                      G.decode(h['source'], payload) if valid else ())
        for capture, signature in ground.sightings[before:]:
            online.sighting(capture, signature, frames)
    ground.close()
    out = dict(transport=dict(frames=frames, schema_errors=errors, invalid=invalid,
                              header_digest=digest.hexdigest()),
               wsp=ground.packets, sightings=ground.sightings, online=online.report())
    sys.stderr.write(json.dumps(out, sort_keys=True)+'\n'); sys.stderr.flush()
    return 0


if __name__ == '__main__': raise SystemExit(main())
