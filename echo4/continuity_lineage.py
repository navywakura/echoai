"""CONT-C: executor-owned lineage, not a policy or subjective identity.

Only copies virtual CONT-B state. New-body allocation is explicit and
quarantined; no resurrection, implicit permission inheritance or LLM.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import asdict, fields

from echoai.echo4 import continuity_active as b
from echoai.echo4.boundary import BoundaryMap, Pair, Trial, integer
from echoai.echo4.continuity_graph import GraphCodec
from echoai.echo4.self_model import SelfChangeMonitor
from echoai.echo4.self_recovery_world import RecoveryEnv
from echoai.echo4.self_reuse_agent import SelfReuseAgent
from echoai.echo4.world import Body

SCHEMA = "echo4-continuity-c-v1"
PROFILE = "CONT-B-virtual-lineage-supervised-body-allocation"
MAX_LINKS = 32
REGISTRY = {**b.REGISTRY, **{cls.__name__: (cls, [f.name for f in fields(cls)])
                           for cls in (Pair, Trial)}}
CODEC = GraphCodec(REGISTRY)
IDENTITY_FIELDS = {"individual", "branch", "body", "epoch", "generation"}
EDGE_FIELDS = {"kind", "token", "parent_sha256", "parent_identity", "identity",
               "parent_turns", "parent_terminal", "memory_sha256", "allocation", "receipt_sha256"}
MODEL_FIELDS = ("memory", "contexts", "context_capacity", "context_dropped", "cam_dropped")
CUMULATIVE = ("metrics", "deaths", "level_counts", "search_copies_q", "search_differs",
              "search_strictly_better", "conflict_wakes", "conflict_suppressed")


def digest(value):
    return hashlib.sha256(b.base.canonical(value)).hexdigest()


def source_hashes():
    return {**b.source_hashes(), "echo4/continuity_lineage.py":
            hashlib.sha256((b.ROOT / "echo4/continuity_lineage.py").read_bytes()).hexdigest()}


def _label(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) is None:
        raise ValueError("invalid custody label")


def _hash(value):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("invalid custody hash")


def _identity(value):
    if type(value) is not dict or set(value) != IDENTITY_FIELDS:
        raise ValueError("invalid identity fields")
    _label(value["individual"])
    _label(value["body"])
    _hash(value["branch"])
    integer(value["epoch"], 0, b.LIMIT)
    integer(value["generation"], 0, b.LIMIT)


def memory_hash(agent):
    """All transferred learned state; historical evidence is not reobserved."""
    return digest(CODEC.encode([agent.cam, agent.q, agent.t,
                               {n: getattr(agent.sensation, n) for n in MODEL_FIELDS}]))


def _branch(edge):
    return digest({k: v for k, v in edge.items() if k not in ("identity", "receipt_sha256")})


def _seal(edge):
    edge["receipt_sha256"] = digest({k: v for k, v in edge.items() if k != "receipt_sha256"})
    return edge


def _chain(chain):
    if type(chain) is not list or not 1 <= len(chain) <= MAX_LINKS:
        raise ValueError("invalid lineage length")
    previous = None
    for index, edge in enumerate(chain):
        if type(edge) is not dict or set(edge) != EDGE_FIELDS:
            raise ValueError("invalid lineage edge")
        if edge["receipt_sha256"] != digest({k: v for k, v in edge.items() if k != "receipt_sha256"}):
            raise ValueError("lineage receipt mismatch")
        _label(edge["token"])
        _hash(edge["parent_sha256"])
        _hash(edge["memory_sha256"])
        integer(edge["parent_turns"], 0, b.LIMIT)
        if type(edge["parent_terminal"]) is not bool:
            raise ValueError("invalid parent terminality")
        identity, kind = edge["identity"], edge["kind"]
        _identity(identity)
        if edge["parent_identity"] != previous:
            raise ValueError("broken identity ancestry")
        if index == 0:
            if kind != "import" or identity["epoch"] or identity["generation"]:
                raise ValueError("invalid imported root")
        elif kind == "fork":
            if any(identity[k] != previous[k] for k in IDENTITY_FIELDS - {"branch"}):
                raise ValueError("fork changed individual/body")
        elif kind in ("body", "descendant"):
            if identity["body"] == previous["body"]:
                raise ValueError("new body must have a new custody label")
            if kind == "body":
                expected = {**previous, "body": identity["body"], "epoch": previous["epoch"] + 1}
                if identity != expected or edge["parent_terminal"]:
                    raise ValueError("invalid body succession or resurrection")
            elif (identity["individual"] == previous["individual"] or identity["epoch"] != 0
                  or identity["generation"] != previous["generation"] + 1):
                raise ValueError("invalid descendant identity")
        else:
            raise ValueError("unknown lineage operation")
        if kind != "body" and identity["branch"] != _branch(edge):
            raise ValueError("invalid derived branch")
        allocation = edge["allocation"]
        if kind in ("body", "descendant"):
            if type(allocation) is not dict or set(allocation) != {"body", "hc", "tc", "heat", "external_h"}:
                raise ValueError("missing external body allocation")
            if type(allocation["body"]) is not dict or set(allocation["body"]) != {"h", "temperature"}:
                raise ValueError("invalid allocated body")
            body = Body(**allocation["body"])
            if not body.alive or type(allocation["hc"]) is not bool or type(allocation["tc"]) is not bool:
                raise ValueError("invalid allocated physiology")
            integer(allocation["heat"], -127, 127)
            integer(allocation["external_h"], 0, 127)
            if allocation["external_h"] != body.h:
                raise ValueError("unaccounted external resources")
        elif allocation is not None:
            raise ValueError("allocation is not a resume/fork operation")
        previous = identity


def _fresh_body(parent, allocation, *, keep_clock):
    """Transfer an explicit allowlist into the original agent constructor."""
    old = CODEC.decode(CODEC.encode(parent))  # isolate all mutable learned state
    body = Body(**allocation["body"])
    agent = type(old)(initial=body, depth=old.sensation.history.depth)
    agent.env = RecoveryEnv(body, h_coupled=allocation["hc"],
                            temperature_coupled=allocation["tc"], heat=allocation["heat"])
    agent.cam, agent.q, agent.t = old.cam, old.q, old.t
    agent.sensation.cam, agent.sensation.world = agent.cam, agent.t
    for name in MODEL_FIELDS:
        setattr(agent.sensation, name, getattr(old.sensation, name))
    agent.sensation.frozen = True
    agent.boundary = BoundaryMap(agent.cam)
    agent.self_change = SelfChangeMonitor(agent.boundary)
    if keep_clock:
        for name in CUMULATIVE:
            setattr(agent, name, getattr(old, name))
    return agent


class LineageRun:
    save = b.base.ContinuityRun.save
    state_hash = b.base.ContinuityRun.state_hash

    def __init__(self, *args, **kwargs):
        raise TypeError("use import_active with an independently supplied digest")

    @classmethod
    def import_active(cls, raw, *, expected_sha256, individual, body):
        _label(individual)
        _label(body)
        active = b.loads(raw, expected_sha256=expected_sha256)
        edge = {"kind": "import", "token": "root", "parent_sha256": expected_sha256,
                "parent_identity": None, "parent_turns": active.next_turn,
                "parent_terminal": active.agent.episode_terminal,
                "memory_sha256": memory_hash(active.agent), "allocation": None}
        edge["identity"] = {"individual": individual, "body": body, "epoch": 0,
                            "generation": 0, "branch": _branch(edge)}
        _seal(edge)
        result = object.__new__(cls)
        result.ancestry, result.active, result.quarantine = [edge], active, None
        result.commissioning = None
        result.snapshot()
        return result

    @property
    def agent(self):
        return self.active.agent if self.active is not None else self.quarantine

    @property
    def identity(self):
        return dict(self.ancestry[-1]["identity"])

    @property
    def scope(self):
        return digest(self.identity)

    def _scope(self, scope):
        if type(scope) is not str or not hmac.compare_digest(scope, self.scope):
            raise ValueError("receipt belongs to another body/epoch/branch")

    def _active(self):
        if self.active is None:
            raise RuntimeError("body quarantined; supervised calibration required")
        return self.active

    def choose_probe(self, token):
        return self._active().choose_probe(token)

    def queue_receipt(self, receipt, *, scope):
        self._scope(scope)
        return self._active().queue_receipt(receipt)

    def consume_receipt(self):
        return self._active().consume_receipt()

    def cancel(self):
        return self._active().cancel()

    def start_recovery(self, *, scope, restored, same_context, mode="selective"):
        self._scope(scope)
        return self._active().start_recovery(restored=restored, same_context=same_context, mode=mode)

    def arm_reuse(self, target, *, scope, **kwargs):
        self._scope(scope)
        return self._active().arm_reuse(target, **kwargs)

    def arm_exposure(self, action, *, scope, **kwargs):
        self._scope(scope)
        return self._active().arm_exposure(action, **kwargs)

    def step(self, *, greedy=False):
        return self._active().step(greedy=greedy)

    def _edge(self, kind, token, allocation=None):
        _label(token)
        if len(self.ancestry) >= MAX_LINKS:
            raise ValueError("lineage budget exhausted")
        raw = self.dumps()  # also rejects incomplete/failed native operations
        if self.active is not None and (self.active.inbox is not None or self.active.session.model.pending is not None):
            raise ValueError("finish or cancel outstanding probe before branching/rebinding")
        return {"kind": kind, "token": token, "parent_sha256": hashlib.sha256(raw).hexdigest(),
                "parent_identity": self.identity, "parent_turns": self.agent.metrics.turns,
                "parent_terminal": self.agent.episode_terminal,
                "memory_sha256": memory_hash(self.agent), "allocation": allocation}

    def fork(self, left, right):
        if left == right:
            raise ValueError("sister branches require distinct labels")
        edges = [self._edge("fork", label) for label in (left, right)]
        raw = self.dumps()
        children = []
        for edge in edges:
            child = loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
            edge["identity"] = {**self.identity, "branch": _branch(edge)}
            child.ancestry.append(_seal(edge))
            # Calibration is inherited evidence from the shared prefix, not
            # claimed as newly executed by either child.
            child.snapshot()
            children.append(child)
        return tuple(children)

    def allocate_body(self, body, *, body_id, token, individual=None,
                      hc=True, tc=True, heat=0):
        """Explicit virtual allocation; returns a quarantined successor."""
        if type(body) is not Body:
            raise ValueError("requires Body")
        _label(body_id)
        kind = "body" if individual is None else "descendant"
        allocation = {"body": asdict(body), "hc": hc, "tc": tc, "heat": heat, "external_h": body.h}
        edge = self._edge(kind, token, allocation)
        identity = {**self.identity, "body": body_id, "epoch": self.identity["epoch"] + 1}
        if individual is not None:
            _label(individual)
            identity.update(individual=individual, epoch=0, generation=identity["generation"] + 1,
                            branch=_branch(edge))
        edge["identity"] = identity
        ancestry = json.loads(b.base.canonical(self.ancestry + [_seal(edge)]))
        _chain(ancestry)  # all arguments checked before allocating or mutating
        child = object.__new__(LineageRun)
        child.ancestry, child.active, child.commissioning = ancestry, None, None
        child.quarantine = _fresh_body(self.agent, allocation, keep_clock=kind == "body")
        child.snapshot()
        return child

    def commission(self, pairs, nominal, *, scope):
        """Atomic supervised recalibration from public evidence, never physics."""
        self._scope(scope)
        if self.active is not None:
            raise RuntimeError("not a quarantined body")
        if type(nominal) is not b.ProbeTrace:
            raise ValueError("requires a new nominal receipt")
        self.snapshot()
        agent = CODEC.decode(CODEC.encode(self.quarantine))
        _calibrate(agent, pairs)
        agent.sensation.frozen = False
        active = b.ActiveRun(agent, nominal)
        evidence = {"scope": self.scope, "pairs": CODEC.encode(pairs)}
        # All fallible reconstruction happens before publishing the new state.
        candidate = object.__new__(LineageRun)
        candidate.ancestry = self.ancestry
        candidate.active, candidate.quarantine, candidate.commissioning = active, None, evidence
        candidate.snapshot()
        self.active, self.quarantine, self.commissioning = active, None, evidence

    def snapshot(self):
        if set(vars(self)) != {"ancestry", "active", "quarantine", "commissioning"}:
            raise ValueError("unexpected lineage state")
        _chain(self.ancestry)
        active, quarantine = None, None
        if self.active is not None:
            if type(self.active) is not b.ActiveRun or self.quarantine is not None:
                raise ValueError("ambiguous executor state")
            active = self.active.snapshot()
        else:
            _quarantined(self.quarantine, self.ancestry)
            quarantine = CODEC.encode(self.quarantine)
        _commissioned(self)
        return {"schema": SCHEMA, "profile": PROFILE, "sources": source_hashes(),
                "ancestry": self.ancestry, "commissioning": self.commissioning,
                "active": active, "quarantine": quarantine}

    def dumps(self):
        raw = b.base.canonical(self.snapshot())
        if len(raw) > b.base.MAX_BYTES:
            raise ValueError("checkpoint exceeds byte budget")
        return raw


def _birth(chain):
    return next((e for e in reversed(chain) if e["kind"] in ("body", "descendant")), None)


def _quarantined(agent, chain):
    birth = _birth(chain)
    if birth is None:
        raise ValueError("quarantine without body allocation")
    origin = birth["parent_turns"] if birth["kind"] == "body" else 0
    b._core_profile(agent, origin, origin)
    if (agent.recovery is not None or agent.self_model is not None or agent.life_turns
            or agent.boundary.rows or agent.boundary.pairs or agent.boundary.last_identifier
            or agent.boundary.frozen or agent.self_change.references or agent.self_change.sealed
            or agent.sensation.frozen is not True or agent.sensation.history.steps
            or agent.last_sensation is not None or agent.last_sensory_prediction is not None):
        raise ValueError("body-dependent authorization survived quarantine")
    if (agent.prev_slot is not None or agent.last_reward != 0 or agent.sample_wsp
            or agent.last_proposed_action is not None or agent.last_gate_decision is not None
            or agent.last_ask is not None or agent.last_cortex_action is not None
            or agent.last_attend != (False, 0) or agent.last_explore or agent.last_evidence_explore):
        raise ValueError("previous body turn context survived quarantine")
    if type(agent) is SelfReuseAgent and (agent.trial_phase or agent.trial_active or agent.trial_token
                                         or agent.reuse_target is not None or agent.reuse_decision is not None):
        raise ValueError("inherited trial permission")
    if memory_hash(agent) != birth["memory_sha256"]:
        raise ValueError("quarantined inheritance changed")


def _calibrate(agent, pairs):
    if type(pairs) is not tuple or len(pairs) != 16:
        raise ValueError("requires sixteen new matched calibration pairs")
    initial = agent.observation(agent.env.cell())
    for pair in pairs:
        if type(pair) is not Pair or pair.treatment.packets[0] != initial:
            raise ValueError("calibration observation mismatch")
        agent.calibrate_self_reference(pair)
    agent.seal_self_reference()


def _commissioned(run):
    birth = _birth(run.ancestry)
    if birth is None:
        if run.commissioning is not None:
            raise ValueError("unexpected commissioning evidence")
        return
    allocation = birth["allocation"]
    agent = run.agent
    if (asdict(agent.env.initial) != allocation["body"] or type(agent.env) is not RecoveryEnv
            or (agent.env._hc, agent.env._tc, agent.env._heat) != (allocation["hc"], allocation["tc"], allocation["heat"])):
        raise ValueError("body differs from allocation receipt")
    origin = birth["parent_turns"] if birth["kind"] == "body" else 0
    if agent.metrics.turns - agent.life_turns != origin:
        raise ValueError("individual versus inherited clock mismatch")
    evidence = run.commissioning
    if run.active is None:
        if evidence is not None:
            raise ValueError("commissioned quarantine")
        return
    if type(evidence) is not dict or set(evidence) != {"scope", "pairs"}:
        raise ValueError("missing recalibration evidence")
    # A later exact virtual fork can inherit this prefix. A different body
    # cannot: select only identities from the most recent body allocation on.
    start = run.ancestry.index(birth)
    scopes = {digest(e["identity"]) for e in run.ancestry[start:]}
    if evidence["scope"] not in scopes:
        raise ValueError("stale commissioning scope")
    pairs = CODEC.decode(evidence["pairs"])
    # Read-only replay: known calibration slots guarantee no CAM allocations.
    if type(pairs) is not tuple or len(pairs) != 16:
        raise ValueError("invalid calibration count")
    if any(type(p) is not Pair or agent.cam.get(p.treatment.packets[0]) < 0 for p in pairs):
        raise ValueError("missing calibration observation")
    monitor = SelfChangeMonitor(BoundaryMap(agent.cam))
    for pair in pairs:
        if pair.treatment.packets[0] != run.active.initial:
            raise ValueError("calibration origin mismatch")
        monitor.calibrate(pair)
    monitor.seal()
    if (not agent.self_change.sealed or not agent.boundary.frozen
            or monitor.model_hash() != agent.self_change.model_hash()):
        raise ValueError("reference disagrees with calibration evidence")


def loads(raw, *, expected_sha256):
    if type(raw) is not bytes or not 0 < len(raw) <= b.base.MAX_BYTES:
        raise ValueError("invalid checkpoint byte budget")
    _hash(expected_sha256)
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
        raise ValueError("custody digest mismatch")
    try:
        data = json.loads(raw, object_pairs_hook=b.base._unique_pairs,
                          parse_float=b.base._no_float, parse_constant=b.base._no_float)
        if type(data) is not dict or set(data) != {"schema", "profile", "sources", "ancestry", "commissioning", "active", "quarantine"}:
            raise ValueError("invalid lineage envelope")
        if data["schema"] != SCHEMA or data["profile"] != PROFILE or data["sources"] != source_hashes():
            raise ValueError("schema/profile/source mismatch")
        _chain(data["ancestry"])
        run = object.__new__(LineageRun)
        run.ancestry, run.commissioning = data["ancestry"], data["commissioning"]
        run.active = run.quarantine = None
        if data["active"] is not None:
            if data["quarantine"] is not None:
                raise ValueError("ambiguous executor state")
            nested = b.base.canonical(data["active"])
            run.active = b.loads(nested, expected_sha256=hashlib.sha256(nested).hexdigest())
        else:
            run.quarantine = CODEC.decode(data["quarantine"])
        if run.dumps() != raw:
            raise ValueError("noncanonical lineage checkpoint")
        return run
    except (TypeError, KeyError, AttributeError, IndexError, RuntimeError, RecursionError, UnicodeError) as exc:
        raise ValueError("malformed lineage checkpoint") from exc


def load(path, *, expected_sha256):
    with b.base.Path(path).open("rb") as handle:
        return loads(handle.read(b.base.MAX_BYTES + 1), expected_sha256=expected_sha256)
