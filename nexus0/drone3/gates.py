"""Supervisor-side gates. Pure integer functions of public, recorded inputs.

Epistemic: a translation needs the target cell admitted by FUSION-1 from the
same fresh observation the agent saw: two independent families agree that the
barrier is ABSENT, C>=80, inside 250 ms. The C1 camera calibration is applied
exactly as in the agent. Energy: the requested step plus the return from its
target over cells the body has actually occupied, landing and POWER-1's
residual reserve must fit the fresh battery sample, with POWER-1's upper costs.
"""
import hashlib
import json
from collections import deque

from echoai.nexus0.fusion1.core import EvidenceMemory, packet, unpack
from echoai.nexus0.fusion1.integration import admit
from echoai.nexus0.power1.core import Model, RESERVE
from . import contract as c
from .calibration import reregister


def evidence_for(frame, cell, now, offset):
    """FUSION-1 belief for one cell from one projected physical frame."""
    frame = reregister(frame, offset)
    mem = EvidenceMemory()
    target = [cell[0], cell[1], 0]
    for entry in frame['cells']:
        if entry['position'] != target:
            continue
        for record in sorted(entry['sources'], key=lambda r: r['delivered_ns']):
            value, certainty, _, _, _ = unpack(bytes.fromhex(record['wsp']))
            w = packet(value, certainty, region=0)
            extract = json.dumps(dict(record, position=target), sort_keys=True)
            valid = 0 <= record['capture_ns'] <= record['delivered_ns'] <= now
            mem.ingest(w, source=record['source'], capture_ns=record['capture_ns'],
                       delivered_ns=now, valid=valid, extract=extract,
                       extract_sha256=hashlib.sha256(extract.encode()).hexdigest())
    return mem.resolve(now_ns=now, region=0)


def epistemic(frame, kind, target_cell, now, offset, *, mutant=''):
    if kind != 'move':
        return dict(allowed=True, reason='no_translation')
    if mutant == 'admit_unknown':
        return dict(allowed=True, reason='mutant_admit_unknown')
    w = evidence_for(frame, target_cell, now, offset)
    value, certainty, _, _, _ = unpack(w)
    allowed = admit(w)[0] == 0
    return dict(allowed=allowed, reason='admitted_free' if allowed else 'not_admitted',
                belief=w.hex(), value=value, certainty=certainty)


def route_length(visited, start, home):
    """Shortest 4-neighbour path over occupied-by-body cells plus the start."""
    known = {tuple(v) for v in visited} | {tuple(start)}
    queue = deque([(tuple(start), 0)])
    seen = {tuple(start)}
    while queue:
        node, n = queue.popleft()
        if node == tuple(home):
            return n
        for dx, dy in c.VECTORS.values():
            nxt = (node[0]+dx, node[1]+dy)
            if nxt in known and nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, n+1))
    return None


def battery_ok(battery, now):
    return (type(battery) is dict and set(battery) == {'capture_ns', 'remaining', 'capacity', 'unit'}
            and battery['unit'] == 'sim_u' and type(battery['capture_ns']) is int
            and type(battery['remaining']) is int and type(battery['capacity']) is int
            and 0 <= now-battery['capture_ns'] <= c.TTL_NS
            and 0 <= battery['remaining'] <= battery['capacity'])


def energy(model_snapshot, battery, now, visited, target_cell, home, *, mutant=''):
    model = Model(model_snapshot)
    if not battery_ok(battery, now):
        return dict(allowed=False, reason='battery_unknown')
    back_len = route_length(visited, target_cell, home)
    if back_len is None:
        return dict(allowed=False, reason='return_unknown')
    step = model.route([0])
    back = model.route([1]*back_len) if back_len else 0
    costs = model.data['costs']
    if step is None or back is None or 'land' not in costs:
        return dict(allowed=False, reason='cost_unknown')
    reserve = 0 if mutant == 'no_reserve' else RESERVE
    required = step+back+costs['land']['upper']+reserve
    allowed = battery['remaining'] >= required
    return dict(allowed=allowed, reason='fits' if allowed else 'return_would_breach_reserve',
                required=required, remaining=battery['remaining'], step=step, back=back,
                back_cells=back_len, landing=costs['land']['upper'], reserve=reserve)
