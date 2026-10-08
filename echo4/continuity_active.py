"""CONT-B executor custody for the existing SELF session and active agents.

No migration of CONT-A, no new policy, no LLM. The diagnostic journal is
executor evidence, never input to the acting policy. Mid-turn capture fails.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import fields, replace

from echoai.echo4 import continuity as base
from echoai.echo4.boundary import code, integer
from echoai.echo4.continuity_graph import GraphCodec
from echoai.echo4.self_attribution import (
    CATALOG,
    H_CODES,
    HEAT_PRIOR,
    T_CODES,
    ProbePlan,
    ProbeTrace,
    SelfAttributor,
)
from echoai.echo4.self_final import SelfSession
from echoai.echo4.self_recovery import MODES, RecoveryBelief, RecoveryStop
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent, _LearningPermission
from echoai.echo4.self_recovery_world import RecoveryEnv
from echoai.echo4.self_reuse import ReuseDecision, validate_target
from echoai.echo4.self_reuse_agent import SelfReuseAgent, _FrozenLearning

SCHEMA = "echo4-continuity-b-v1"
PROFILE = "SELF-session-active-complete-operations"
LIMIT = (1 << 31) - 1
ROOT = base.ROOT
EXTRA_SOURCES = (
    "echo4/continuity_graph.py", "echo4/continuity_active.py",
    "echo4/self_probe_agent.py", "echo4/self_attribution.py", "echo4/self_final.py",
    "echo4/self_recovery.py", "echo4/self_recovery_agent.py",
    "echo4/self_recovery_world.py", "echo4/self_reuse.py", "echo4/self_reuse_agent.py",
)
REUSE_FIELDS = ["trial_phase", "trial_active", "trial_token", "scripted_action", "reuse_target", "reuse_use_t", "reuse_decision"]
RUN_FIELDS = ["agent", "session", "initial", "nominal", "events", "inbox", "next_turn", "life_origin", "phase"]
REGISTRY = {
    **base.REGISTRY,
    "recovery_agent": (SelfRecoveryAgent, base.AGENT_FIELDS + ["recovery"]),
    "reuse_agent": (SelfReuseAgent, base.AGENT_FIELDS + ["recovery"] + REUSE_FIELDS),
    "recovery_env": (RecoveryEnv, base.REGISTRY["env"][1] + ["_hc", "_tc", "_heat"]),
    "session": (SelfSession, ["model", "finished", "challenge_probes"]),
    "diagnosis": (SelfAttributor, ["initial", "h_candidates", "t_candidates", "used", "last_token", "pending", "executed_ticks", "invalid_reason"]),
    "recovery": (RecoveryBelief, ["h", "t", "current", "mode", "steps", "pending", "stopped", "allowed", "held", "last"]),
    "permission": (_LearningPermission, ["agent"]),
    "frozen_permission": (_FrozenLearning, []),
}
for cls in (ProbePlan, ProbeTrace, ReuseDecision):
    REGISTRY[cls.__name__] = (cls, [f.name for f in fields(cls)])
CODEC = GraphCodec(REGISTRY)


def source_hashes():
    return {**base.source_hashes(), **{
        p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in EXTRA_SOURCES}}


def _receipt(receipt):
    """Bound even rejected public receipts; don't turn bad evidence into good."""
    if type(receipt) is not ProbeTrace:
        raise ValueError("requires an inert ProbeTrace")
    integer(receipt.token, 1, LIMIT)
    if type(receipt.restored) is not bool or type(receipt.same_context) is not bool:
        raise ValueError("invalid receipt flags")
    for name in ("packets", "proposed", "applied", "gates", "ticks", "terminal"):
        seq = getattr(receipt, name)
        if type(seq) is not tuple or len(seq) > 9:
            raise ValueError("receipt exceeds horizon")
        for item in seq:
            if name == "packets":
                if type(item) is not bytes or len(item) != 16:
                    raise ValueError("invalid receipt WSP")
            elif name == "terminal":
                if type(item) is not bool:
                    raise ValueError("invalid receipt terminal")
            elif name == "applied" and item is None:
                pass  # an invalid execution receipt must remain invalid
            else:
                integer(item, 0, 8 if name == "ticks" else 2)


def _core_profile(agent, next_turn, life_origin):
    if type(agent) not in (SelfRecoveryAgent, SelfReuseAgent):
        raise ValueError("unsupported active agent")
    if type(agent.env) not in (base.DockEnv, RecoveryEnv):
        raise ValueError("unsupported active world")
    for obj in (agent, agent.env):
        base._attributes(obj, REGISTRY[CODEC.tags[type(obj)]][1])
    for value in (next_turn, life_origin, agent.metrics.turns, agent.life_turns):
        integer(value, 0, LIMIT)
    if agent.metrics.turns != next_turn or next_turn - life_origin != agent.life_turns:
        raise ValueError("global/life clock mismatch")
    if type(agent.env) is RecoveryEnv:
        if type(agent.env._hc) is not bool or type(agent.env._tc) is not bool:
            raise ValueError("invalid private coupling")
        integer(agent.env._heat, -127, 127)
    # A read-only schema view reuses CONT-A's structural checks. It is never
    # executed, serialized or handed to a policy. Original clocks/environment
    # remain in the graph; only this view normalizes the separate life clock.
    view = object.__new__(base.SelfAgent)
    for name in base.AGENT_FIELDS:
        setattr(view, name, getattr(agent, name))
    view.self_model = None  # exact allowed hooks are checked below
    view.metrics = replace(agent.metrics, turns=agent.life_turns)
    world = object.__new__(base.DockEnv)
    for name in base.REGISTRY["env"][1]:
        setattr(world, name, getattr(agent.env, name))
    view.env = world
    base.validate(view, agent.life_turns)


def _belief(agent):
    belief = agent.recovery
    if type(belief) is not RecoveryBelief or type(agent.self_model) is not _LearningPermission:
        raise ValueError("invalid recovery/learning hook")
    if agent.self_model.agent is not agent:
        raise ValueError("learning permission references another agent")
    if belief.pending is not None:
        raise ValueError("physical forecast pending")
    if belief.mode not in MODES or type(belief.stopped) is not str:
        raise ValueError("invalid recovery mode/stop")
    if belief.stopped not in ("", "no_safe_action", "gate_veto", "model_contradiction", "invalid_execution"):
        raise ValueError("unsupported stop")
    for value in (belief.steps, belief.allowed, belief.held):
        integer(value, 0, LIMIT)
    if belief.steps != agent.life_turns or belief.allowed + belief.held != belief.steps:
        raise ValueError("recovery clock/count mismatch")
    if belief.current != agent.observation(agent.env.cell()):
        raise ValueError("recovery observation mismatch")
    for values, thermal, capacity in ((belief.h, False, 64), (belief.t, True, 160)):
        if type(values) is not tuple or len(values) > capacity:
            raise ValueError("invalid recovery candidate budget")
        if not values and belief.stopped not in ("model_contradiction", "invalid_execution"):
            raise ValueError("empty unstopped belief")
        for candidate in values:
            if type(candidate) is not tuple or len(candidate) != (3 if thermal else 2):
                raise ValueError("invalid recovery candidate")
            integer(candidate[0], 0, 127)
            if thermal:
                integer(candidate[2], -127, 127)
            if type(candidate[1]) is not bool or thermal and candidate[2] not in HEAT_PRIOR:
                raise ValueError("invalid recovery hypothesis")
            if (T_CODES if thermal else H_CODES)[candidate[0]] != code(belief.current, 9 if thermal else 8):
                raise ValueError("candidate contradicts current observation")
    if belief.steps == 0:
        if belief.last is not None:
            raise ValueError("observation before first recovery step")
    elif type(belief.last) is not dict or type(belief.last.get("allowed")) is not bool:
        raise ValueError("missing learning decision")


class ActiveRun:
    """One diagnostic session followed by one experimental life/trial.

Physical probe execution belongs to the caller, outside this synchronous
wrapper. Queue only its completed receipt; no replay of physical effects at
load. This API does not restore bodies, respawn or arm a second trial.
"""
    # Reuse atomic, non-overwriting publication and hashing, not CONT-A schema.
    save = base.ContinuityRun.save
    state_hash = base.ContinuityRun.state_hash

    def __init__(self, agent, nominal=None):
        if type(agent) not in (SelfRecoveryAgent, SelfReuseAgent):
            raise ValueError("requires existing SELF active-capable agent")
        if agent.recovery is not None or agent.self_model is not None or agent.life_turns:
            raise ValueError("attach before a fresh experimental life")
        if type(agent) is SelfReuseAgent and (agent.trial_active or agent.trial_phase not in ("", "school")):
            raise ValueError("attach before active exposure/reuse")
        self.agent = agent
        self.initial = agent.observation(agent.env.cell())
        self.nominal = nominal
        self.session = SelfSession(agent.new_self_diagnosis(self.initial, nominal))
        self.events, self.inbox = [], None
        self.next_turn = self.life_origin = agent.metrics.turns
        self.phase = "diagnostic"
        self._busy = self._failed = False
        validate(self)

    def _available(self):
        if self._busy or self._failed:
            raise RuntimeError("unfinished/failed operation")

    def _operation(self, callback):
        self._available()
        self._busy = True
        try:
            return callback()
        except BaseException:
            self._failed = True
            raise
        finally:
            self._busy = False

    def choose_probe(self, token):
        self._available()
        integer(token, 1, LIMIT)
        if (self.phase != "diagnostic" or self.inbox is not None or self.session.finished
                or self.session.model.pending is not None or token <= self.session.model.last_token):
            raise ValueError("diagnostic choice out of order")
        def operation():
            plan = self.session.choose(token)
            self.events.append(("choose", token))
            return plan
        return self._operation(operation)

    def queue_receipt(self, receipt):
        self._available()
        _receipt(receipt)
        if self.phase != "diagnostic" or self.inbox is not None or self.session.model.pending is None:
            raise ValueError("no empty pending-probe inbox")
        self.inbox = receipt

    def consume_receipt(self):
        self._available()
        if self.phase != "diagnostic" or self.inbox is None or self.session.model.pending is None:
            raise ValueError("no receipt to consume")
        def operation():
            receipt = self.inbox
            result = self.session.consume(receipt)
            self.events.append(("consume", receipt))
            self.inbox = None
            return result
        return self._operation(operation)

    def cancel(self):
        self._available()
        if self.phase != "diagnostic" or self.session.finished or self.inbox is not None:
            raise ValueError("consume queued evidence before cancellation")
        self.session.cancel()
        self.events.append(("cancel", None))

    def _ready(self, cls):
        self._available()
        if self.phase != "diagnostic" or type(self.agent) is not cls or self.inbox is not None:
            raise ValueError("cannot arm this phase")
        self.session.authorized_model()
        if self.agent.life_turns:
            raise ValueError("not a fresh life")

    def start_recovery(self, *, restored, same_context, mode="selective"):
        self._ready(SelfRecoveryAgent)
        # Native methods validate external receipts before changing anything.
        self.agent.start_recovery(self.session.authorized_model(), restored=restored,
                                  same_context=same_context, mode=mode)
        self.phase = "recovery"

    def arm_exposure(self, action, *, mode, token, restored, same_context):
        self._ready(SelfReuseAgent)
        self.agent.arm_exposure(self.session.authorized_model(), action, mode=mode,
                                token=token, restored=restored, same_context=same_context)
        self.phase = "exposure"

    def arm_reuse(self, target, *, token, restored, nominal_body_confirmed, use_t=True):
        self._ready(SelfReuseAgent)
        self.agent.arm_reuse(target, token=token, restored=restored,
                             nominal_body_confirmed=nominal_body_confirmed, use_t=use_t)
        self.phase = "reuse"

    def step(self, *, greedy=False):
        self._available()
        if type(greedy) is not bool:
            raise ValueError("greedy must be boolean")
        if self.phase == "diagnostic" or self.agent.episode_terminal:
            raise RuntimeError("no authorized physical turn")
        if self.agent.recovery is not None and self.agent.recovery.stopped:
            raise RecoveryStop(self.agent.recovery.stopped)
        if type(self.agent) is SelfReuseAgent and not self.agent.trial_active:
            raise RuntimeError("trial already completed")
        self._busy = True
        try:
            action = self.agent.turn(self.next_turn, greedy=greedy)
            self.next_turn += 1
            return action
        except RecoveryStop:
            # A normal no-safe-action stop occurs before a physical turn.
            # Anything partially executed still fails closed under validation.
            self._failed = True
            if self.agent.recovery is None or not self.agent.recovery.stopped:
                raise
            validate(self)
            self._failed = False
            raise
        except BaseException:
            self._failed = True
            raise
        finally:
            self._busy = False

    def diagnostic_clock(self):
        receipts = [value for tag, value in self.events if tag == "consume"]
        if self.inbox is not None:
            receipts.append(self.inbox)
        # Declared public receipts, not independent physical measurement. A
        # malformed receipt is not promoted into a verified action count.
        return {"received": len(receipts), "consumed": len(receipts) - (self.inbox is not None),
                "reported_ticks": sum(len(r.applied) for r in receipts),
                "nominal_reported_ticks": 0 if self.nominal is None else len(self.nominal.applied)}

    def snapshot(self):
        if self._busy or self._failed:
            raise ValueError("unfinished/failed operation cannot be checkpointed")
        if set(vars(self)) != set(RUN_FIELDS) | {"_busy", "_failed"}:
            raise ValueError("unexpected executor fields")
        validate(self)
        return {"schema": SCHEMA, "profile": PROFILE, "sources": source_hashes(),
                "diagnostic_clock": self.diagnostic_clock(),
                "state": CODEC.encode({name: getattr(self, name) for name in RUN_FIELDS})}

    def dumps(self):
        raw = base.canonical(self.snapshot())
        if len(raw) > base.MAX_BYTES:
            raise ValueError("checkpoint exceeds byte budget")
        return raw


def validate(run):
    agent = run.agent
    _core_profile(agent, run.next_turn, run.life_origin)
    if run.phase not in ("diagnostic", "recovery", "exposure", "reuse"):
        raise ValueError("unsupported operation phase")
    if type(run.session) is not SelfSession or type(run.session.model) is not SelfAttributor:
        raise ValueError("unsupported diagnostic session")
    if type(run.initial) is not bytes or len(run.initial) != 16:
        raise ValueError("invalid diagnostic origin")
    if run.nominal is not None:
        _receipt(run.nominal)
    if type(run.events) is not list or len(run.events) > 14:
        raise ValueError("diagnostic journal exceeds budget")
    # Re-run inference only, from recorded public inputs and existing sealed
    # references. No private body/coupling data enter this reconstruction.
    expected = SelfSession(agent.new_self_diagnosis(run.initial, run.nominal))
    for event in run.events:
        if type(event) is not tuple or len(event) != 2 or expected.finished:
            raise ValueError("invalid diagnostic event order")
        tag, value = event
        if tag == "choose":
            expected.choose(value)
        elif tag == "consume":
            _receipt(value)
            expected.consume(value)
        elif tag == "cancel" and value is None:
            expected.cancel()
        else:
            raise ValueError("unsupported diagnostic event")
    if CODEC.encode(expected) != CODEC.encode(run.session):
        raise ValueError("session disagrees with public diagnostic journal")
    if run.inbox is not None:
        _receipt(run.inbox)
        if expected.model.pending is None or expected.finished:
            raise ValueError("orphan receipt")
    if run.diagnostic_clock()["received"] > len(CATALOG):
        raise ValueError("too many probe receipts")
    if run.phase == "diagnostic":
        if agent.recovery is not None or agent.self_model is not None or agent.life_turns:
            raise ValueError("unauthorized action/learning during diagnosis")
        if run.initial != agent.observation(agent.env.cell()):
            raise ValueError("diagnostic body changed")
    else:
        expected.authorized_model()
        if run.inbox is not None:
            raise ValueError("unconsumed evidence at authorization")
    if run.phase in ("recovery", "exposure"):
        _belief(agent)
        if agent.recovery.steps == 0 and (
                agent.recovery.h != expected.model.h_candidates
                or agent.recovery.t != expected.model.t_candidates
                or agent.recovery.current != run.initial):
            raise ValueError("recovery not derived from confirmed diagnosis")
    if type(agent) is SelfRecoveryAgent:
        if run.phase not in ("diagnostic", "recovery"):
            raise ValueError("reuse phase on wrong agent")
    else:
        if run.phase == "recovery":
            raise ValueError("unsupported continuous reuse agent life")
        if type(agent.trial_active) is not bool or type(agent.reuse_use_t) is not bool:
            raise ValueError("invalid trial flags")
        integer(agent.trial_token, 0, LIMIT)
        if run.phase == "diagnostic":
            if agent.trial_active or agent.trial_phase not in ("", "school"):
                raise ValueError("trial armed during diagnosis")
        else:
            if agent.trial_phase != run.phase or agent.trial_token == 0:
                raise ValueError("trial phase/token mismatch")
            if agent.life_turns not in (0, 1) or agent.trial_active != (agent.life_turns == 0):
                raise ValueError("single-step trial boundary mismatch")
        if run.phase == "exposure":
            integer(agent.scripted_action, 0, 2)
            if agent.reuse_target is not None or agent.reuse_decision is not None:
                raise ValueError("reuse state in exposure")
        if run.phase == "reuse":
            if agent.recovery is not None or type(agent.self_model) is not _FrozenLearning:
                raise ValueError("invalid frozen learning hook")
            if agent.sensation.frozen is not True or agent.scripted_action is not None:
                raise ValueError("reuse learning must remain frozen")
            validate_target(agent.reuse_target)
            if (agent.life_turns == 0 and agent.reuse_decision is not None
                    or agent.life_turns == 1 and type(agent.reuse_decision) is not ReuseDecision):
                raise ValueError("reuse decision/clock mismatch")


def loads(raw, *, expected_sha256):
    if type(raw) is not bytes or not 0 < len(raw) <= base.MAX_BYTES:
        raise ValueError("invalid checkpoint byte budget")
    if (type(expected_sha256) is not str or len(expected_sha256) != 64
            or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256)):
        raise ValueError("custody digest mismatch")
    try:
        data = json.loads(raw, object_pairs_hook=base._unique_pairs,
                          parse_float=base._no_float, parse_constant=base._no_float)
        if type(data) is not dict or set(data) != {"schema", "profile", "sources", "diagnostic_clock", "state"}:
            raise ValueError("invalid active envelope")
        if data["schema"] != SCHEMA or data["profile"] != PROFILE or data["sources"] != source_hashes():
            raise ValueError("schema/profile/source mismatch; no implicit migration")
        state = CODEC.decode(data["state"])
        if type(state) is not dict or set(state) != set(RUN_FIELDS):
            raise ValueError("invalid executor state")
        run = object.__new__(ActiveRun)
        for key, value in state.items():
            setattr(run, key, value)
        run._busy = run._failed = False
        validate(run)
        if data["diagnostic_clock"] != run.diagnostic_clock() or run.dumps() != raw:
            raise ValueError("noncanonical checkpoint/diagnostic clock")
        return run
    except (TypeError, KeyError, AttributeError, IndexError, RuntimeError, RecursionError, UnicodeError) as exc:
        raise ValueError("malformed active checkpoint") from exc


def load(path, *, expected_sha256):
    with base.Path(path).open("rb") as handle:
        raw = handle.read(base.MAX_BYTES + 1)
    return loads(raw, expected_sha256=expected_sha256)
