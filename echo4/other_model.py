"""OTHER: bounded observer on the agent's existing CAM/T, no private peer API.

Observational conditional predictions, NOT causal control or mental-state facts.
Only actual sensor packets can acquire an extract; derived pooled keys cannot.
"""
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.echo4.sensation import checked_packet
from echoai.echo4.world import integer

MODES = ("identity", "pooled", "self_copy", "no_history")
RELS = (11, 18, 14)
LIMIT = 512
MIN_HITS = 3


def context(subject, cue):
    integer(subject, 0, 2, "subject")
    if cue is not None:
        integer(cue, 0, 2, "cue")
    return pack(src=2 if subject == 0 else 3, rel=14, dst=4 if cue is not None else 41,
                domain=9, generator=8, style=0, slot=subject, seq=255 if cue is None else cue)


def outcome(subject, cue, action):
    integer(subject, 0, 2, "subject")
    if cue is not None:
        integer(cue, 0, 2, "cue")
    integer(action, 0, 2, "action")
    return pack(src=2 if subject == 0 else 3, rel=RELS[action], dst=3,
                domain=9, generator=8, style=1, slot=subject, seq=255 if cue is None else cue)


def decode(raw, *, action=False):
    checked_packet(raw)
    subject, cue = raw[14], None if raw[15] == 255 else raw[15]
    if action:
        if raw[1] not in RELS:
            raise ValueError("unsupported public action")
        executed = RELS.index(raw[1])
        expected = outcome(subject, cue, executed)
    else:
        executed = None
        expected = context(subject, cue)
    if expected != raw:
        raise ValueError("noncanonical public observation")
    return subject, cue, executed


class OtherModel:
    def __init__(self, cam, world, *, mode="identity"):
        if mode not in MODES:
            raise ValueError("unsupported other-model mode")
        self.cam, self.world, self.mode = cam, world, mode
        self.last_tick = -1
        self.count = self.capacity_drops = 0
        self.pending = None
        self.stopped = False

    def _key(self, raw):
        if self.mode != "pooled":
            return raw
        key = bytearray(raw)
        key[0], key[14], key[13] = 3, 255, raw[13] + 2
        return bytes(key)  # A derived index, never a factual sensor packet.

    def _slot(self, raw, *, factual):
        found = self.cam.get(raw)
        if found >= 0:
            return found
        vertex, latency, _ = encode_event(raw)
        extract = "observed_wsp=" + raw.hex() if factual else ""
        found, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6,
                            has_fact=int(factual), extract=extract,
                            source="other1-sensor" if factual else "other1-derived-index",
                            key=raw)
        if found < 0:
            self.capacity_drops += 1
        return found

    def _lookup(self, raw, action):
        slot = self.cam.get(self._key(raw))
        if slot < 0:
            return None
        target = self.world.predict(slot, action)
        if (target is None or self.world.n[slot][action] < MIN_HITS
                or self.world.alt_n[slot][action] != 0):
            return None
        value = self.cam.slot[target].wsp
        # All T destinations in these namespaced rows were observed outcomes.
        if value[13] != (3 if self.mode == "pooled" else 1) or value[1] not in RELS:
            return None
        result = RELS.index(value[1])
        subject, cue, _ = decode(raw)
        if value != self._key(outcome(subject, cue, result)):
            return None
        return result

    def _predict(self, raw, own_action):
        subject, cue, _ = decode(raw)
        if cue is None or self.mode == "no_history":
            return None
        if self.mode == "self_copy" and subject:
            values = {self._lookup(context(0, cue), a) for a in range(3)} - {None}
            return next(iter(values)) if len(values) == 1 else None
        return self._lookup(raw, own_action)

    def begin(self, tick, packets):
        integer(tick, 0, 1000000, "observation tick")
        if self.stopped or self.count >= LIMIT:
            raise RuntimeError("other observer stopped/budget exhausted")
        if self.pending is not None or tick <= self.last_tick:
            raise ValueError("pending or stale public observation")
        if type(packets) is not tuple or len(packets) != 2:
            raise ValueError("requires own and optional peer context")
        for index, raw in enumerate(packets):
            if raw is None:
                if index == 0:
                    raise ValueError("own context required")
                continue
            subject, _, _ = decode(raw)
            if (index == 0) != (subject == 0):
                raise ValueError("self/other source mismatch")
        # Prediction before any current outcome is accepted or recorded.
        predictions = tuple(tuple(self._predict(raw, a) if raw is not None else None
                                  for a in range(3)) for raw in packets)
        self.pending = (tick, packets, predictions)
        return predictions

    def finish(self, tick, own_action, packets):
        integer(own_action, 0, 2, "own executed action")
        integer(tick, 0, 1000000, "receipt tick")
        if self.stopped or self.pending is None or tick != self.pending[0]:
            raise ValueError("missing/mismatched observation receipt")
        if type(packets) is not tuple or len(packets) != 2:
            raise ValueError("requires own and optional peer outcome")
        contexts = self.pending[1]
        for index, raw in enumerate(packets):
            if raw is None:
                if index == 0:
                    raise ValueError("own execution confirmation required")
                continue
            if contexts[index] is None:
                raise ValueError("outcome without a tracked context")
            subject, cue, action = decode(raw, action=True)
            if (subject, cue) != decode(contexts[index])[:2] or index == 0 and action != own_action:
                raise ValueError("receipt identity/context/execution mismatch")
        prediction = self.pending[2][1][own_action]
        for before, after in zip(contexts, packets):
            if before is None:
                continue
            # Literal observations are facts, including visible unknown cues.
            self._slot(before, factual=True)
            if after is None:
                continue
            self._slot(after, factual=True)
            if decode(before)[1] is None or self.mode == "no_history":
                continue
            s = self._slot(self._key(before), factual=self.mode != "pooled")
            nxt = self._slot(self._key(after), factual=self.mode != "pooled")
            if s >= 0 and nxt >= 0:
                self.world.observe(s, own_action, nxt)
        self.last_tick = tick
        self.count += 1
        self.pending = None
        return prediction

    def stop(self):
        self.pending = None
        self.stopped = True
