"""ARC adapter for the existing 3E diary, evidence retrieval and suppression.

Only demonstrations can enter memory. The village's private facts are never
imported; its diary mechanism is reused with ARC receipts and measured work.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

from seed.village3_receipts import Echo
from seed.village2 import WALK
from seed.game_selfimprove import sha as diary_sha
from echoai.seed.refinement import canonical_program, execute, solver_input
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ArcMemory:
    def __init__(self, seed=45002, limit=256):
        if not 1 <= limit <= 1024:
            raise ValueError("bounded memory required")
        self.actor = Echo(seed)
        self.limit = limit
        self.payloads = {}
        self.reads = []

    def remember(self, task, program, library, source, *, work=0):
        public = solver_input(task)
        if not isinstance(work, int) or work < 0:
            raise ValueError("nonnegative measured work required")
        if not isinstance(source, str) or not source or len(source) > 160:
            raise ValueError("bounded provenance required")
        program = canonical_program(program, library)
        demonstrations = public["train"]
        expected = [p["output"] for p in demonstrations]
        actual = [execute(p["input"], program, library) for p in demonstrations]
        if actual != expected:
            raise ValueError("only exact demonstration receipts may enter memory")
        if len(self.actor.diary) >= self.limit:
            return None
        payload = {"program": program, "demonstrations": demonstrations, "source": source,
                   "features": SparsePrimitiveGuide.features(public), "work": work}
        proof = sha(payload)
        # Existing 3E remember() constructs the same hash-linked diary and valence.
        offer = {"session": "arc-development", "episode": len(self.actor.diary),
                 "agent": "ARC:"+sha(program), "said": sha(expected)}
        entry = self.actor.remember(offer, {"checked": sha(actual), "cost": WALK+work, "proof": proof}, True)
        self.payloads[entry["hash"]] = payload
        return entry["hash"]

    def verify(self, library):
        previous = "0"*64
        if len(self.actor.diary) > self.limit or len(self.payloads) != len(self.actor.diary):
            raise ValueError("memory exceeds capacity or lost receipts")
        for entry in self.actor.diary:
            body = {k: v for k, v in entry.items() if k != "hash"}
            if entry["prev"] != previous or diary_sha(body) != entry["hash"]:
                raise ValueError("broken diary chain")
            payload = self.payloads[entry["hash"]]
            if sha(payload) != entry["proof"]:
                raise ValueError("altered ARC evidence")
            expected = [p["output"] for p in payload["demonstrations"]]
            actual = [execute(tuple(map(tuple, p["input"])), payload["program"], library)
                      for p in payload["demonstrations"]]
            if sha(actual) != sha(expected) or sha(expected) != entry["checked"]:
                raise ValueError("ARC evidence no longer reproduces")
            previous = entry["hash"]
        return previous

    def candidates(self, public, limit=24):
        if not isinstance(limit, int) or not 1 <= limit <= 256:
            raise ValueError("bounded retrieval required")
        features = set(SparsePrimitiveGuide.features(public))
        ranked = []
        unique = set()
        for entry in self.actor.diary:
            # Original evidence() applies receipt presence and memory suppression.
            evidence = self.actor.evidence({k: entry[k] for k in ("session", "episode", "agent")})
            if evidence is None:
                continue
            payload = self.payloads[entry["hash"]]
            known = set(payload["features"])
            overlap = 1000*len(features & known)//max(1, len(features | known))
            trust = self.actor.trust(entry["agent"])
            ranked.append((-overlap, -trust, len(payload["program"]), entry["hash"]))
        selected = []
        for _, _, _, receipt in sorted(ranked):
            payload = self.payloads[receipt]
            key = sha(payload["program"])
            if key in unique:
                continue
            unique.add(key)
            selected.append({"program": deepcopy(payload["program"]), "receipt": receipt,
                             "source": payload["source"]})
            if len(selected) == limit:
                break
        self.reads.extend(row["receipt"] for row in selected)
        return selected

    def ablate(self, hashes):
        result = deepcopy(self)
        if not set(hashes) <= set(self.payloads):
            raise ValueError("foreign memory intervention")
        result.actor.suppressed.update(hashes)
        result.reads = []
        return result

    def state(self):
        return {"schema": 1, "limit": self.limit, "diary": deepcopy(self.actor.diary),
                "suppressed": sorted(self.actor.suppressed), "payloads": deepcopy(self.payloads)}

    def save(self, path):
        Path(path).write_text(json.dumps(self.state(), sort_keys=True)+"\n")

    @classmethod
    def restore(cls, state, library):
        if state.get("schema") != 1:
            raise ValueError("unknown memory format")
        result = cls(limit=state["limit"])
        result.actor.diary = deepcopy(state["diary"])
        result.actor.suppressed = set(state["suppressed"])
        result.payloads = deepcopy(state["payloads"])
        if not result.actor.suppressed <= set(result.payloads):
            raise ValueError("foreign suppressed record")
        result.verify(library)
        return result
