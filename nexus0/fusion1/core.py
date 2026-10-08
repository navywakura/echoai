"""Integer evidence reducer. This file also runs alone in the SIM-3 cage.

Records are an external provenance ledger referenced by WSP, not a second
policy bus. No world names, geometry oracle, network, LLM or motor control.
"""
import hashlib
import json
import struct

UNKNOWN, ABSENT, PRESENT = -1, 0, 1
BARRIER, VISIBLE = 1, 2
TTL = 250_000_000
SKEW = 100_000_000
CAPACITY = 512
FAMILIES = {'depth': 'camera', 'rgb': 'camera', 'lidar': 'lidar', 'host': 'host'}
SENSOR_FAMILIES = {'camera', 'lidar'}
MUTANTS = ('last_writer', 'no_expiry', 'duplicate_votes', 'ignore_predicate',
           'ignore_region', 'erase_conflict', 'constant_confidence', 'unsafe_gate')


def integer(n, low=0, high=2**63-1):
    return type(n) is int and low <= n <= high


def packet(value, certainty, predicate=BARRIER, region=0, epoch=0):
    if value not in (UNKNOWN, ABSENT, PRESENT) or not integer(certainty, 0, 100):
        raise ValueError('value/certainty')
    if predicate not in (BARRIER, VISIBLE) or not integer(region, 0, 255) or not integer(epoch, 0, 255):
        raise ValueError('predicate/frame')
    rel, dst = (31, 31) if value == UNKNOWN else (14, 5 if value else 7)
    return struct.pack('<BBBBbbbbbbBBBBBB', 2, rel, dst, 8,
                       0, 10, 0, certainty, 0, 0, 0, 8, 7, predicate, region, epoch)


def unpack(w):
    if not isinstance(w, bytes) or len(w) != 16:
        raise ValueError('WSP must be 16 bytes')
    a = struct.unpack('<BBBBbbbbbbBBBBBB', w)
    value = UNKNOWN if a[1:3] == (31, 31) else PRESENT if a[1:3] == (14, 5) else ABSENT if a[1:3] == (14, 7) else None
    if value is None or w != packet(value, a[7], a[13], a[14], a[15]):
        raise ValueError('noncanonical perception')
    return value, a[7], a[13], a[14], a[15]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class EvidenceMemory:
    def __init__(self, mutant=''):
        if mutant and mutant not in MUTANTS:
            raise ValueError('mutant')
        self.mutant = mutant
        self.records = []
        self.seen = set()
        self.overflow = False
        self.clock = 0
        self.last = None

    def ingest(self, wsp, *, source, capture_ns, delivered_ns, valid, extract, extract_sha256):
        value, _, predicate, region, epoch = unpack(wsp)
        if source not in FAMILIES or not integer(capture_ns) or not integer(delivered_ns) \
                or type(valid) is not bool or not isinstance(extract, str) or len(extract) > 2048:
            raise ValueError('malformed provenance')
        if delivered_ns < self.clock:
            raise ValueError('arrival clock regression')
        self.clock = delivered_ns
        valid = valid and capture_ns <= delivered_ns and bool(extract) \
            and hashlib.sha256(extract.encode()).hexdigest() == extract_sha256
        rec = dict(wsp=wsp.hex(), source=source, capture_ns=capture_ns,
                   delivered_ns=delivered_ns, valid=valid, extract=extract,
                   extract_sha256=extract_sha256, value=value,
                   predicate=predicate, region=region, epoch=epoch)
        key = digest({k:v for k,v in rec.items() if k != 'delivered_ns'})
        if key in self.seen and self.mutant != 'duplicate_votes':
            return False
        if len(self.records) >= CAPACITY:
            self.overflow = True
            return False
        self.seen.add(key)
        self.records.append(rec)
        return True

    def resolve(self, *, now_ns, predicate=BARRIER, region=0, epoch=0):
        if not integer(now_ns) or now_ns < self.clock:
            raise ValueError('query clock regression')
        self.clock = now_ns
        # Constructing the packet validates the requested address as well.
        packet(UNKNOWN, 0, predicate, region, epoch)
        candidates = [(i,r) for i,r in enumerate(self.records)
                      if (r['predicate'] == predicate or self.mutant == 'ignore_predicate')
                      and (r['region'] == region or self.mutant == 'ignore_region')
                      and r['epoch'] == epoch and r['capture_ns'] <= r['delivered_ns']]
        latest = {}
        for i,r in candidates:
            old = latest.get(r['source'])
            if old is None or (r['capture_ns'], i) > (old[1]['capture_ns'], old[0]):
                latest[r['source']] = (i,r)
        pool = candidates if self.mutant == 'duplicate_votes' else list(latest.values())
        fresh = [(i,r) for i,r in pool if r['valid'] and r['value'] != UNKNOWN
                 and 0 <= now_ns-r['capture_ns']
                 and (now_ns-r['capture_ns'] <= TTL or self.mutant == 'no_expiry')
                 and FAMILIES[r['source']] in SENSOR_FAMILIES]
        if fresh:
            anchor = max(r['capture_ns'] for _,r in fresh)
            fresh = [(i,r) for i,r in fresh if anchor-r['capture_ns'] <= SKEW]
        by_family = {}
        for i,r in fresh:
            family = str(i) if self.mutant == 'duplicate_votes' else FAMILIES[r['source']]
            by_family.setdefault(family, set()).add(r['value'])
        values = set().union(*by_family.values()) if by_family else set()
        conflict = len(values) > 1 and len(by_family) >= 2
        value = next(iter(values)) if len(values) == 1 else UNKNOWN
        certainty = (80 if len(by_family) >= 2 else 40) if value != UNKNOWN else 0
        reason = 'conflict' if conflict else 'agreement' if certainty == 80 else 'single_source' if certainty else 'no_evidence'
        if self.mutant == 'last_writer' and fresh:
            value = max(fresh, key=lambda x: (x[1]['capture_ns'], x[0]))[1]['value']
            certainty, reason = 80, 'last_writer'
        if self.mutant == 'erase_conflict' and conflict:
            self.records.clear()
        if self.overflow:
            value, certainty, reason = UNKNOWN, 0, 'capacity'
        if self.mutant == 'constant_confidence':
            certainty = 80
        wsp = packet(value, certainty, predicate, region, epoch)
        allow = predicate == BARRIER and value == ABSENT and certainty >= 80
        if self.mutant == 'unsafe_gate':
            allow = True
        self.last = dict(wsp=wsp.hex(), reason=reason, attend=conflict,
                         allow_advance=allow, refs=[i for i,_ in fresh],
                         history_n=len(self.records), overflow=self.overflow)
        return wsp


def run_commands(commands, mutant=''):
    mem = EvidenceMemory(mutant)
    out = []
    for c in commands:
        if c.get('op') == 'observe' and set(c) == {'op','wsp','source','capture_ns','delivered_ns','valid','extract','extract_sha256'}:
            kw = {k:v for k,v in c.items() if k not in ('op','wsp')}
            mem.ingest(bytes.fromhex(c['wsp']), **kw)
        elif c.get('op') == 'query' and set(c) == {'op','now_ns','predicate','region','epoch'}:
            mem.resolve(**{k:v for k,v in c.items() if k != 'op'})
            out.append(dict(mem.last))
        else:
            raise ValueError('unknown command/extra channel')
    return dict(decisions=out, history=mem.records, history_sha256=digest(mem.records), overflow=mem.overflow)


if __name__ == '__main__':
    import sys
    for line in sys.stdin:
        if len(line) > 2_000_000:
            raise ValueError('oversize episode')
        request = json.loads(line)
        if set(request) != {'commands', 'mutant'}:
            raise ValueError('request schema')
        print(json.dumps(run_commands(request['commands'], request['mutant']), sort_keys=True), flush=True)
