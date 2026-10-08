"""DREAM-A private archive and public partial replay; no environment execution.

The archive belongs to the trusted laboratory. Only Replay.view/expand/batch
results may be exported to a later proposal model. This is an API boundary,
not isolation from hostile Python sharing the process.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

from echoai.echo4.continuity import _no_float, _unique_pairs, canonical

SCHEMA = "echo4-dream-history-v1"
PROFILE = "SelfAgent-WORLD1-native-or-greedy-v1"
EXPERIMENTS = ("native", "greedy")
MAX_NODES = 1024
MAX_BYTES = 4 * 1024 * 1024
OBSERVATION = {"wsp", "turn", "action", "gate", "reward", "terminal"}
NODE = {"id", "parent", "experiment", "observation", "score", "cost", "checkpoint"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def integer(value, lo, hi):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError("integer outside history profile")


def keys(value, expected):
    if type(value) is not dict or set(value) != expected:
        raise ValueError("unexpected or missing history fields")


def digest(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("invalid custody digest")


def validate(data):
    keys(data, {"schema", "profile", "sources", "continuity_certificate", "nodes"})
    if data["schema"] != SCHEMA or data["profile"] != PROFILE:
        raise ValueError("unknown history version/profile")
    digest(data["continuity_certificate"])
    sources = data["sources"]
    if type(sources) is not dict or not 1 <= len(sources) <= 256:
        raise ValueError("invalid source manifest")
    for path, value in sources.items():
        if type(path) is not str or not 1 <= len(path) <= 256:
            raise ValueError("invalid source name")
        digest(value)
    nodes = data["nodes"]
    if type(nodes) is not list or not 1 <= len(nodes) <= MAX_NODES:
        raise ValueError("invalid node count")
    for index, node in enumerate(nodes):
        keys(node, NODE)
        integer(node["id"], index, index)
        digest(node["checkpoint"])
        obs = node["observation"]
        keys(obs, OBSERVATION)
        if type(obs["wsp"]) is not str or re.fullmatch(r"[0-9a-f]{32}", obs["wsp"]) is None:
            raise ValueError("observation requires a WSP16")
        integer(obs["turn"], 0, (1 << 31) - 1)
        integer(obs["reward"], -127, 127)
        integer(node["score"], -127, 127)
        if node["score"] != obs["reward"] or type(obs["terminal"]) is not bool:
            raise ValueError("invalid fixed score or terminal flag")
        keys(node["cost"], {"attempts", "native_steps", "llm_calls"})
        for field, expected in (("attempts", int(index > 0)), ("native_steps", int(index > 0)), ("llm_calls", 0)):
            integer(node["cost"][field], expected, expected)
        if index == 0:
            if any(node[k] is not None for k in ("parent", "experiment")) or any(obs[k] is not None for k in ("action", "gate")):
                raise ValueError("invalid root")
        else:
            integer(node["parent"], 0, index - 1)
            parent = nodes[node["parent"]]["observation"]
            if parent["terminal"] or obs["turn"] != parent["turn"] + 1:
                raise ValueError("invalid causal clock or terminal continuation")
            if node["experiment"] not in EXPERIMENTS:
                raise ValueError("unknown experiment")
            integer(obs["action"], 0, 2)
            integer(obs["gate"], 0, 2)
    return data


class Archive:
    """Bounded, copied evidence; hash is supplied separately by its custodian."""
    def __init__(self, data):
        self._data = copy.deepcopy(validate(data))
        if len(self.dumps()) > MAX_BYTES:
            raise ValueError("history exceeds byte limit")

    def dumps(self):
        return canonical(self._data)

    @classmethod
    def loads(cls, raw, *, expected_sha256):
        digest(expected_sha256)
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES or sha(raw) != expected_sha256:
            raise ValueError("history size or digest mismatch")
        try:
            data = json.loads(raw, object_pairs_hook=_unique_pairs,
                              parse_float=_no_float, parse_constant=_no_float)
        except (UnicodeDecodeError, RecursionError) as exc:
            raise ValueError("malformed history") from exc
        return cls(data)

    def replay(self, *, budget=64, batch_limit=4):
        return Replay(self, budget=budget, batch_limit=batch_limit)


class Replay:
    """Reveals executed samples, never predicts or executes missing branches."""
    def __init__(self, archive, *, budget, batch_limit):
        if type(archive) is not Archive:
            raise ValueError("requires validated archive")
        integer(budget, 0, 100000)
        integer(batch_limit, 1, 8)
        self._nodes = copy.deepcopy(archive._data["nodes"])
        self._handles = {0: 0}  # storage index -> public handle, assigned on reveal
        self._seen = [0]  # public handle -> storage index
        self.budget, self.batch_limit = budget, batch_limit
        self.queries = self.represented_steps = 0

    def _public(self, index):
        node = self._nodes[index]
        return {"id": self._handles[index],
                "parent": None if index == 0 else self._handles[node["parent"]],
                "experiment": node["experiment"],
                **copy.deepcopy({k: node[k] for k in ("observation", "score", "cost")})}

    def view(self):
        return {"schema": "echo4-dream-view-v1", "profile": PROFILE,
                "experiments": list(EXPERIMENTS),
                "nodes": [self._public(i) for i in self._seen],
                "queries_used": self.queries, "queries_remaining": self.budget - self.queries,
                "represented_native_steps": self.represented_steps,
                "replay_native_steps": 0, "replay_llm_calls": 0}

    def expand(self, parent, experiment):
        return self.batch([(parent, experiment)])[0]

    def batch(self, requests):
        if type(requests) not in (list, tuple) or len(requests) > self.batch_limit:
            raise ValueError("invalid batch width")
        pairs = []
        for request in requests:
            if type(request) not in (list, tuple) or len(request) != 2:
                raise ValueError("invalid request")
            parent, experiment = request
            integer(parent, 0, len(self._seen) - 1)
            if type(experiment) is not str or experiment not in EXPERIMENTS:
                raise ValueError("unknown experiment")
            pairs.append((parent, experiment))
        if len(set(pairs)) != len(pairs):
            raise ValueError("duplicate request in batch")
        if self.queries + len(pairs) > self.budget:
            raise RuntimeError("replay query budget exhausted")
        results = []
        for parent, experiment in pairs:
            self.queries += 1
            index = self._seen[parent]
            status = "terminal" if self._nodes[index]["observation"]["terminal"] else "unknown"
            child = next((n for n in self._nodes[1:] if n["parent"] == index
                          and n["experiment"] == experiment and n["id"] not in self._handles), None)
            if child is None:
                results.append({"status": status, "parent": parent, "experiment": experiment})
                continue
            identifier = child["id"]
            self._handles[identifier] = len(self._seen)
            self._seen.append(identifier)
            self.represented_steps += child["cost"]["native_steps"]
            results.append({"status": "observed", "node": self._public(identifier)})
        return results
