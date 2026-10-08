"""Bounded observed encounter history in the agent's existing CAM.

No policy, other-mind access or parallel episodic store. Facts are receipts;
summaries are derived queries and never promoted to factual predictions.
"""
import hashlib
import json

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.echo4.continuity import canonical, _unique_pairs, _no_float
from echoai.echo4.other_model import decode, LIMIT
from echoai.echo4.interaction_world import JOIN_COST, JOIN_OUTPUT
from echoai.echo4.world import integer

SOURCE = "relation1-observed-episode"
OBSERVATION_FIELDS = {"tick", "contexts", "outcomes", "paid", "output"}


def episode_key(tick, peer):
    integer(tick, 0, LIMIT - 1, "episode tick")
    integer(peer, 0, 2, "tracked peer")
    return pack(src=2, rel=19, dst=3, time=9, domain=9, generator=8,
                style=32 + (tick >> 8), slot=peer, seq=tick & 255)


def observation(tick, contexts, outcomes, paid, output):
    integer(tick, 0, LIMIT - 1, "episode tick")
    integer(paid, 0, 5, "own cost")
    integer(output, 0, 10, "own output")
    if any(type(v) is not tuple or len(v) != 2 for v in (contexts, outcomes)):
        raise ValueError("own and optional peer observations required")
    if contexts[0] is None or outcomes[0] is None:
        raise ValueError("own context and executed action required")
    own, cue, _ = decode(contexts[0])
    if own != 0 or cue is None:
        raise ValueError("known own task context required")
    action = decode(outcomes[0], action=True)
    if action[:2] != (0, cue):
        raise ValueError("own execution/context mismatch")
    peer = 0
    peer_action = None
    if contexts[1] is not None:
        peer, _, _ = decode(contexts[1])
        if peer == 0:
            raise ValueError("self is not a counterpart")
    if outcomes[1] is not None:
        if contexts[1] is None:
            raise ValueError("unattributed peer action")
        remote = decode(outcomes[1], action=True)
        if remote[:2] != decode(contexts[1])[:2]:
            raise ValueError("peer execution/context mismatch")
        peer_action = remote[2]
    own_action = action[2]
    allowed = ({(0, 0), (JOIN_COST[cue], 0), (JOIN_COST[cue], JOIN_OUTPUT[cue])}
               if own_action == 0 else {(0, 0), (1, 5)} if own_action == 1 else {(0, 0)})
    if (paid, output) not in allowed or (own_action == 0 and output > 0 and peer_action not in (None, 0)):
        raise ValueError("own cost/output inconsistent with observed A execution")
    record = {"tick": tick, "contexts": [p.hex() if p is not None else None for p in contexts],
              "outcomes": [p.hex() if p is not None else None for p in outcomes], "paid": paid, "output": output}
    return record, peer


def parse_observation(record):
    if type(record) is not dict or set(record) != OBSERVATION_FIELDS:
        raise ValueError("observation schema")
    packets = []
    for field in ("contexts", "outcomes"):
        values = record[field]
        if type(values) is not list or len(values) != 2:
            raise ValueError("packet list")
        if any(v is not None and (type(v) is not str or len(v) != 32) for v in values):
            raise ValueError("packet hex")
        packets.append(tuple(bytes.fromhex(v) if v is not None else None for v in values))
    checked, peer = observation(record["tick"], *packets, record["paid"], record["output"])
    if checked != record:
        raise ValueError("noncanonical observation")
    return checked, peer


class RelationMemory:
    def __init__(self, cam):
        if not isinstance(cam, Cam) or any(s.occupied and s.source == SOURCE for s in cam.slot):
            raise ValueError("requires own CAM without an existing relation journal")
        self.cam = cam
        self.count, self.last_tick, self.head = 0, -1, -1
        self.peer_heads = [-1, -1, -1]  # 0 = unidentified, never identity 1/2.
        self.stopped = False

    def _key_at(self, slot):
        return None if slot == -1 else self.cam.slot[slot].wsp.hex()

    def append(self, tick, contexts, outcomes, paid, output):
        if self.stopped or self.count >= LIMIT:
            raise RuntimeError("relation journal stopped/budget exhausted")
        record, peer = observation(tick, contexts, outcomes, paid, output)
        if tick <= self.last_tick:
            raise ValueError("duplicate or backwards episode")
        raw = episode_key(tick, peer)
        if self.cam.get(raw) >= 0:
            raise ValueError("episode already exists; no overwrite")
        links = {"previous": self._key_at(self.head), "pair_previous": self._key_at(self.peer_heads[peer])}
        entry = {"observation": record, **links}
        edges = list(dict.fromkeys(s for s in (self.head, self.peer_heads[peer]) if s >= 0))
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1,
                           extract=canonical(entry).decode("ascii"), source=SOURCE, key=raw, see=edges)
        if slot < 0:
            raise RuntimeError("relation CAM capacity exhausted; no fallback slot")
        self.head = slot
        if peer:
            self.peer_heads[peer] = slot
        self.last_tick = tick
        self.count += 1
        return raw

    def _entry(self, slot):
        integer(slot, 0, len(self.cam.slot) - 1, "episode slot")
        row = self.cam.slot[slot]
        if not row.occupied or row.source != SOURCE or row.has_fact != 1 or not row.extract:
            raise ValueError("invalid episode provenance")
        if len(row.extract) > 2048:
            raise ValueError("episode extract exceeds budget")
        entry = json.loads(row.extract, object_pairs_hook=_unique_pairs, parse_float=_no_float, parse_constant=_no_float)
        if type(entry) is not dict or set(entry) != {"observation", "previous", "pair_previous"}:
            raise ValueError("episode schema")
        record, peer = parse_observation(entry["observation"])
        if row.wsp != episode_key(record["tick"], peer) or row.extract != canonical(entry).decode("ascii"):
            raise ValueError("episode key/canonical extract mismatch")
        edges = []
        for field in ("previous", "pair_previous"):
            key = entry[field]
            if key is None:
                continue
            if type(key) is not str or len(key) != 32:
                raise ValueError("episode predecessor encoding")
            raw = bytes.fromhex(key)
            target = self.cam.get(raw)
            # Structural check here; full linked traversal checks contents too.
            if target < 0 or raw[11:14] not in (bytes((9, 8, 32)), bytes((9, 8, 33))):
                raise ValueError("missing relation predecessor")
            prior_tick = (raw[13] - 32) * 256 + raw[15]
            if prior_tick >= record["tick"] or field == "pair_previous" and raw[14] != peer:
                raise ValueError("invalid predecessor order/identity")
            if target not in edges:
                edges.append(target)
        if row.see != edges:
            raise ValueError("CAM links differ from episode receipt")
        return {"wsp": row.wsp.hex(), **entry}

    def history(self, peer=None):
        if peer is not None:
            integer(peer, 0, 2, "history peer")
        if peer == 0:
            # An unidentified bucket is NOT a stable dyad or a new identity.
            return [e for e in self.history() if bytes.fromhex(e["wsp"])[14] == 0]
        slot = self.head if peer is None else self.peer_heads[peer]
        field = "previous" if peer is None else "pair_previous"
        entries = []
        while slot >= 0:
            if len(entries) >= LIMIT:
                raise ValueError("episode traversal budget exceeded")
            entry = self._entry(slot)
            if peer is not None and bytes.fromhex(entry["wsp"])[14] != peer:
                raise ValueError("peer head mismatch")
            entries.append(entry)
            key = entry[field]
            slot = -1 if key is None else self.cam.get(bytes.fromhex(key))
        if peer is None and len(entries) != self.count:
            raise ValueError("episode chain count mismatch")
        return list(reversed(entries))

    def summary(self, peer):
        integer(peer, 0, 2, "summary peer")
        rows = self.history(peer)
        result = {"encounters": len(rows), "paid": 0, "output": 0, "net": 0,
                  "peer_action_unknown": 0, "observed_joint_attempts": 0, "confirmed_joint_successes": 0,
                  "last_tick": -1}
        for entry in rows:
            r = entry["observation"]
            own = decode(bytes.fromhex(r["outcomes"][0]), action=True)[2]
            other = None if r["outcomes"][1] is None else decode(bytes.fromhex(r["outcomes"][1]), action=True)[2]
            result["paid"] += r["paid"]
            result["output"] += r["output"]
            result["net"] += r["output"] - r["paid"]
            result["peer_action_unknown"] += int(other is None)
            result["observed_joint_attempts"] += int(own == other == 0)
            result["confirmed_joint_successes"] += int(own == other == 0 and r["output"] > 0)
            result["last_tick"] = r["tick"]
        return result

    def digest(self):
        state = {"history": self.history(), "count": self.count, "last_tick": self.last_tick,
                 "head": self._key_at(self.head), "peer_heads": [self._key_at(s) for s in self.peer_heads],
                 "stopped": self.stopped}
        return hashlib.sha256(canonical(state)).hexdigest()

    def invariant(self):
        try:
            integer(self.count, 0, LIMIT, "episode count")
            integer(self.last_tick, -1, LIMIT - 1, "last episode tick")
            integer(self.head, -1, len(self.cam.slot) - 1, "global head")
            if type(self.peer_heads) is not list or len(self.peer_heads) != 3 or type(self.stopped) is not bool:
                return False
            for head in self.peer_heads:
                integer(head, -1, len(self.cam.slot) - 1, "peer head")
            history = self.history()
            partition = [self.history(p) for p in range(3)]
            return bool(self.peer_heads[0] == -1 and sum(map(len, partition)) == self.count
                        and {e["wsp"] for group in partition for e in group} == {e["wsp"] for e in history}
                        and self.last_tick == (history[-1]["observation"]["tick"] if history else -1)
                        and self.count == sum(s.occupied and s.source == SOURCE for s in self.cam.slot)
                        and self.cam.destroyed == 0)
        except (ValueError, TypeError, KeyError, IndexError):
            return False

    def stop(self):
        self.stopped = True


def replay(records):
    if type(records) is not list or len(records) > LIMIT:
        raise ValueError("bounded relation transcript required")
    memory = RelationMemory(Cam())
    for record in records:
        checked, _ = parse_observation(record)
        packets = [tuple(bytes.fromhex(p) if p is not None else None for p in checked[field])
                   for field in ("contexts", "outcomes")]
        memory.append(checked["tick"], *packets, checked["paid"], checked["output"])
    return {"history": memory.history(), "summaries": [memory.summary(p) for p in range(3)],
            "memory_sha256": memory.digest(), "valid": memory.invariant()}
