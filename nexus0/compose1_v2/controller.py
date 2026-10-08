"""Composition compares terminal consequences rather than cheap prefixes."""
import heapq
import hashlib
import json
from collections import deque

from echoai.nexus0.compose1.controller import Composer as Original, add, distance
from echoai.nexus0.fusion1.core import EvidenceMemory, packet, unpack


class Composer(Original):
    def decide(self, frame):
        # A proposed sequence is conditional on the preceding observation.
        # New evidence may reveal a better access while the old next step is
        # still physically admissible. Recompute before every causal action.
        self.pending = []
        return super().decide(frame)

    def update(self, frame):
        if not frame.get('physical', False):
            return super().update(frame)
        if set(frame) != {'physical', 'now_ns', 'odometry', 'energy', 'station_observed', 'cells'}:
            raise ValueError('unexpected physical frame field')
        # Use the original scalar/schema validation without relabelling source
        # captures as query time. Provenance below retains original timestamps.
        base = {k: v for k, v in frame.items() if k != 'physical'}
        base['cells'] = []
        super().update(base)
        for cell in frame['cells']:
            if set(cell) != {'position', 'sources'}:
                raise ValueError('physical cell schema')
            p = tuple(cell['position'])
            if len(p) != 3 or any(type(v) is not int for v in p):
                raise ValueError('cell coordinates')
            if p not in self.cells:
                if len(self.cells) >= 256:
                    raise ValueError('spatial capacity')
                self.refs[p] = len(self.cells)
                self.cells[p] = EvidenceMemory('no_expiry' if self.mode == 'no_expiry' else '')
            mem = self.cells[p]
            for record in sorted(cell['sources'], key=lambda r: r['delivered_ns']):
                if set(record) != {'source', 'wsp', 'capture_ns', 'delivered_ns', 'raw_sha256'}:
                    raise ValueError('provenance schema')
                value, certainty, _, _, _ = unpack(bytes.fromhex(record['wsp']))
                w = packet(value, certainty, region=self.refs[p])
                extract = json.dumps(dict(record, position=list(p)), sort_keys=True)
                # Memory's query clock may be newer than transport arrival.
                # Ingest at this processing instant; original delivery remains
                # in the signed extract, capture time never changes.
                valid = 0 <= record['capture_ns'] <= record['delivered_ns'] <= self.now
                mem.ingest(w, source=record['source'], capture_ns=record['capture_ns'],
                           delivered_ns=self.now, valid=valid, extract=extract,
                           extract_sha256=hashlib.sha256(extract.encode()).hexdigest())
        self.beliefs = {p: m.resolve(now_ns=self.now, region=self.refs[p])
                        for p, m in self.cells.items()}

    def route_home(self, p):
        # Occupied body positions are direct odometry history, not fake votes
        # from two ranging sensors at zero distance.
        known = set(self.visits)
        known.update(cell for cell, m in self.cells.items() if m.records and
                     unpack(bytes.fromhex(m.records[-1]['wsp']))[0] == 0)
        queue = deque([(p, [])])
        seen = {p}
        while queue:
            node, path = queue.popleft()
            if node == self.home:
                return path
            for action in range(6):
                delta = self.model.predict(action)
                if delta is None:
                    continue
                nxt = add(node, delta)
                if nxt in known and nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path+[action]))
        return None

    def search(self, target):
        before = self.model.fingerprint()
        qvalues = self.model.values(self.feature())
        if self.mode == 'conventional':
            qvalues = [0] * 7
        frontier = [(0, 0, self.pos, [], 0)]
        seen = {self.pos}
        generated = 1
        terminals = []
        while frontier:
            _, depth, node, path, visits = heapq.heappop(frontier)
            children = []
            if depth < self.max_depth and node != target:
                for action in range(6):
                    delta = self.model.predict(action)
                    if delta is None:
                        continue
                    nxt = add(node, delta)
                    if nxt in seen or not self.free(nxt):
                        continue
                    if generated >= self.budget:
                        break
                    generated += 1
                    seen.add(nxt)
                    cost = visits + self.visits.get(nxt, 0) * 20
                    children.append((distance(nxt, target), depth + 1, nxt,
                                     path + [action], cost))
            if path and (not children or node == target):
                score = (-10000 + depth if node == target else
                         distance(node, target) * 10 + depth + visits)
                terminals.append((score, -depth, -qvalues[path[0]], path))
            for child in children:
                heapq.heappush(frontier, child)
        self.imagined_writes += before != self.model.fingerprint()
        return (min(terminals)[3] if terminals else []), generated
