"""DREAM restored-probe histories. Execution is confined to collect/native."""
from __future__ import annotations

import copy
from dataclasses import replace
import json

from echoai.echo4.boundary_world import packet
from echoai.echo4.continuity import _unique_pairs, _no_float, canonical
from echoai.echo4.dream_history import digest, integer, keys, sha
from echoai.echo4.dream_policy import request_plan
from echoai.echo4.self_attribution import CATALOG, ProbeTrace, SelfAttributor, validate_trace
from echoai.echo4.self_probe_audit import calibrate, public
from echoai.echo4.self_audit import cam_hash

PROFILE = "echo4-dream-restored-self-probes-v1"
MAX_BYTES = 65536


def decode_trace(data):
    keys(data, {"token", "restored", "same_context", "packets", "proposed", "applied",
                "gates", "ticks", "terminal"})
    for field in ("packets", "proposed", "applied", "gates", "ticks", "terminal"):
        if type(data[field]) is not list or len(data[field]) > 9:
            raise ValueError("invalid trace array")
    try:
        return ProbeTrace(data["token"], data["restored"], data["same_context"],
                          tuple(bytes.fromhex(p) for p in data["packets"]),
                          *(tuple(data[k]) for k in ("proposed", "applied", "gates", "ticks", "terminal")))
    except (TypeError, AttributeError) as exc:
        raise ValueError("invalid trace encoding") from exc


class ProbeArchive:
    def __init__(self, data):
        keys(data, {"profile", "initial", "reference_sha256", "branches"})
        if data["profile"] != PROFILE:
            raise ValueError("unknown probe profile")
        digest(data["reference_sha256"])
        if type(data["initial"]) is not str or len(data["initial"]) != 32:
            raise ValueError("requires WSP16")
        initial = bytes.fromhex(data["initial"])
        if type(data["branches"]) is not list or len(data["branches"]) > 6:
            raise ValueError("branch limit")
        seen = set()
        for row in data["branches"]:
            keys(row, {"experiment", "receipt", "native_steps"})
            index = row["experiment"]
            integer(index, 0, 5)
            if index in seen:
                raise ValueError("duplicate branch")
            seen.add(index)
            receipt = decode_trace(row["receipt"])
            validate_trace(receipt, initial, CATALOG[index], 18)
            integer(row["native_steps"], len(CATALOG[index]), len(CATALOG[index]))
        self._data = copy.deepcopy(data)
        if len(self.dumps()) > MAX_BYTES:
            raise ValueError("archive too large")

    def dumps(self):
        return canonical(self._data)

    @classmethod
    def loads(cls, raw, expected_sha256):
        digest(expected_sha256)
        if type(raw) is not bytes or len(raw) > MAX_BYTES or sha(raw) != expected_sha256:
            raise ValueError("archive custody mismatch")
        try:
            return cls(json.loads(raw, object_pairs_hook=_unique_pairs,
                                  parse_float=_no_float, parse_constant=_no_float))
        except (RecursionError, UnicodeDecodeError) as exc:
            raise ValueError("invalid archive") from exc

    def replay(self):
        return ProbeReplay(self)


class ProbeReplay:
    def __init__(self, archive):
        self._data = copy.deepcopy(archive._data)
        self._used = set()
        self._revealed = []
        self.queries = self.steps = 0

    def view(self):
        return {"initial": self._data["initial"], "observed": copy.deepcopy(self._revealed),
                "queries": self.queries, "represented_steps": self.steps,
                "replay_native_steps": 0, "replay_llm_calls": 0}

    def request(self, plan):
        integer(plan.index, 0, 5)
        integer(plan.token, 18, (1 << 31) - 1)
        if plan.actions != CATALOG[plan.index]:
            raise ValueError("non-catalog request")
        if self.queries >= 6:
            raise RuntimeError("replay query limit")
        self.queries += 1
        row = next((r for r in self._data["branches"] if r["experiment"] == plan.index), None)
        if row is None or plan.index in self._used:
            return None
        self._used.add(plan.index)
        self.steps += row["native_steps"]
        self._revealed.append(copy.deepcopy(row))
        # Restored independent trials: rebind only the local correlation token.
        return replace(decode_trace(row["receipt"]), token=plan.token)


def prepare(body):
    reference, nominal = calibrate(body)
    return reference, nominal


def model_for(body, prepared):
    reference, nominal = prepared
    return SelfAttributor(reference, packet(body), nominal)


def native(body, condition, plan):
    from echoai.echo4.self_probe_world import run_probe
    hc, tc, heat = condition
    return run_probe(body, plan, h_coupled=hc, temperature_coupled=tc, heat=heat)[0]


def collect(body, condition, prepared):
    reference, _ = prepared
    before = reference.model_hash(), cam_hash(reference.boundary.cam)
    branches = []
    for index in range(6):
        model = model_for(body, prepared)
        plan = request_plan(model, index, 18)
        if plan is None:
            continue
        trace = native(body, condition, plan)
        validate_trace(trace, packet(body), CATALOG[index], 18)
        branches.append({"experiment": index, "receipt": json.loads(canonical(public(trace))),
                         "native_steps": len(trace.applied)})
    if before != (reference.model_hash(), cam_hash(reference.boundary.cam)):
        raise ValueError("reference was modified")
    return ProbeArchive({"profile": PROFILE, "initial": packet(body).hex(),
                         "reference_sha256": reference.model_hash(), "branches": branches})
