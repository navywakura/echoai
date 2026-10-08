"""MAINT-C private custody using the existing CONT graph codec and validator.

Snapshots are complete-operation checkpoints, NOT repair operations. No pickle,
class imports from data, rejuvenation, replenishment or continuation after stop.
"""
from dataclasses import fields
import hashlib
import hmac
import json

from echoai.echo4 import continuity as base
from echoai.echo4.continuity_graph import GraphCodec
from echoai.echo4.maintain_control import MaintainControl
from echoai.echo4.maintain_model import MaintainModel, MaintainStop, MODES, MAX_BOXES, LIMIT, bands
from echoai.echo4.maintain_world import MaintenanceEnv, ServiceReceipt, FAULTS, SERVICE_COST
from echoai.echo4.world import integer
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.nexus0.types import default_e
from echoai.core.spoke import encode_event

SCHEMA = "echo4-maintain-continuity-v1"
MODEL_FIELDS = "mode current boxes progress steps conflicts attempts pending stopped last_choice predictions".split()
ENV_FIELDS = base.REGISTRY["env"][1] + (
    "_fault _spares _initial_spares _external_heat _progress _stopped service_attempts "
    "services_paid repairs service_resource_used work_done last_service").split()
REGISTRY = {**base.REGISTRY,
            "maintain_agent": (MaintainControl, base.AGENT_FIELDS + ["maintenance"]),
            "maintain_model": (MaintainModel, MODEL_FIELDS),
            "maintain_env": (MaintenanceEnv, ENV_FIELDS),
            "service_receipt": (ServiceReceipt, [f.name for f in fields(ServiceReceipt)])}
CODEC = GraphCodec(REGISTRY)


def source_hashes():
    extra = ("echo4/continuity_graph.py", "echo4/maintain_world.py", "echo4/maintain_agent.py",
             "echo4/maintain_model.py", "echo4/maintain_control.py", "echo4/maintain_continuity.py",
             "echo4/self_attribution.py")
    return {**base.source_hashes(), **{p: hashlib.sha256((base.ROOT / p).read_bytes()).hexdigest() for p in extra}}


def checked_events(events):
    if type(events) is not tuple or len(events) > 8:
        raise ValueError("bounded tuple of private fault events required")
    previous = -1
    for item in events:
        if type(item) is not tuple or len(item) != 2:
            raise ValueError("invalid fault event")
        tick, fault = item
        integer(tick, 0, LIMIT - 1, "fault tick")
        if tick <= previous or fault not in ("clogged", "seized"):
            raise ValueError("unordered event or external repair")
        previous = tick


def validate(agent, next_turn):
    if type(agent) is not MaintainControl or type(agent.env) is not MaintenanceEnv:
        raise ValueError("unsupported maintenance profile")
    env, model = agent.env, agent.maintenance
    if type(model) is not MaintainModel:
        raise ValueError("unsupported controller")
    for obj, names in ((agent, REGISTRY["maintain_agent"][1]), (env, ENV_FIELDS), (model, MODEL_FIELDS)):
        base._attributes(obj, names)
    # Read-only schema view, never executed or passed to any action selector.
    view, world = object.__new__(base.SelfAgent), object.__new__(base.DockEnv)
    for name in base.AGENT_FIELDS:
        setattr(view, name, getattr(agent, name))
    for name in base.REGISTRY["env"][1]:
        setattr(world, name, getattr(env, name))
    view.env = world
    base.validate(view, next_turn)
    integer(next_turn, 0, LIMIT, "maintenance clock")
    if type(env._fault) is not str or env._fault not in FAULTS:
        raise ValueError("invalid component")
    if type(env._stopped) is not bool:
        raise ValueError("invalid stop latch")
    for value, upper, name in ((env._spares, 3, "spares"), (env._initial_spares, 3, "initial spares"),
                               (env._external_heat, 4, "heat"), (env._progress, 2, "progress")):
        integer(value, 0, upper, name)
    for name in ("service_attempts", "services_paid", "repairs", "service_resource_used", "work_done",
                 "resource_in", "resource_used", "resource_spill"):
        integer(getattr(env, name), 0, LIMIT * 127, name)
    if (not env.spares_balanced or env.services_paid > env.service_attempts
            or env.repairs > env.services_paid or env.service_attempts * 3 > next_turn
            or env.service_resource_used != SERVICE_COST * env.services_paid
            or env.service_resource_used > env.resource_used or env.work_done > next_turn):
        raise ValueError("invalid maintenance ledger")
    if env.total_steps == 0:
        if env.last_service is not None or env.last_transition is not None:
            raise ValueError("unexecuted receipt")
    else:
        r, tr = env.last_service, env.last_transition
        if type(r) is not ServiceReceipt or type(tr) is not base.Transition:
            raise ValueError("missing last receipt")
        if (r.tick != next_turn or tr.after != env.body or not tr.balanced
                or r.spares_after != env._spares
                or not env.stopped and r.progress_after != env._progress
                or r.service not in ("none", "terminal", "no_spare", "insufficient_energy",
                                     "repaired", "unnecessary", "ineffective")):
            raise ValueError("receipt disagrees with physical state")
        integer(r.tick, 1, LIMIT, "receipt clock")
        for name in ("fault_before", "fault_after"):
            if type(getattr(r, name)) is not str or getattr(r, name) not in FAULTS:
                raise ValueError("invalid receipt fault")
        for name in ("progress_before", "progress_after"):
            integer(getattr(r, name), 0, 2, name)
        for name in ("spares_before", "spares_after"):
            integer(getattr(r, name), 0, 3, name)
        integer(r.work, 0, 1, "work receipt")
        integer(r.service_cost, 0, SERVICE_COST, "service cost")
        if (r.service_cost not in (0, SERVICE_COST)
                or r.spares_before - r.spares_after != int(r.service_cost == SERVICE_COST)):
            raise ValueError("invalid last service payment")
        # Reconstruct only the last physical operation with the sealed A
        # implementation. This private validator is never a controller input.
        witness = MaintenanceEnv(tr.before, fault=r.fault_before,
                                 spares=r.spares_before, external_heat=env._external_heat)
        witness._progress = r.progress_before
        witness.total_steps = next_turn - 1
        if witness.advance(tr.action) != tr or witness.last_service != r:
            raise ValueError("last operation disagrees with native mechanics")
    if model.mode not in MODES or type(model.stopped) is not str or model.stopped not in (
            "", "budget", "no_safe_action", "terminal", "hypothesis_budget", "gate_veto", "operator"):
        raise ValueError("invalid maintenance mode/stop")
    for name in ("steps", "conflicts", "attempts", "predictions"):
        integer(getattr(model, name), 0, LIMIT * MAX_BOXES * 8, name)
    integer(model.progress, 0, 2, "controller progress")
    if (model.pending is not None or model.steps != next_turn or model.progress != env._progress
            or model.attempts != env.service_attempts or model.conflicts > next_turn
            or model.current != agent.observation(env.cell())
            or env.stopped and model.stopped != "operator"
            or agent.episode_terminal and model.stopped != "terminal"):
        raise ValueError("controller clock, permission or observation mismatch")
    if type(model.boxes) is not tuple or not 1 <= len(model.boxes) <= MAX_BOXES:
        raise ValueError("hypothesis budget")
    for b in model.boxes:
        if type(b) is not tuple or len(b) != 7:
            raise ValueError("invalid hypothesis")
        for i, (low, high) in enumerate(((1,127), (1,127), (1,126), (1,126), (0,2), (0,4), (0,3))):
            integer(b[i], low, high, "hypothesis component")
        if b[0] > b[1] or b[2] > b[3]:
            raise ValueError("empty hypothesis")
    if model.boxes != tuple(sorted(set(model.boxes))):
        raise ValueError("noncanonical hypotheses")
    if not agent.episode_terminal:
        hl, hh, tl, th = bands(model.current)
        if any(not (hl <= b[0] <= b[1] <= hh and tl <= b[2] <= b[3] <= th) for b in model.boxes):
            raise ValueError("belief contradicts observed bands")
    if model.last_choice is not None:
        value = model.last_choice
        if type(value) is not tuple or len(value) != 4 or type(value[1]) is not bool or type(value[2]) is not bool:
            raise ValueError("invalid decision record")
        integer(value[0], 0, 2, "decision")
        integer(value[3], 1, MAX_BOXES, "decision budget")


class MaintainRun:
    def __init__(self, agent, *, events=(), veto_at=0):
        checked_events(events)
        integer(veto_at, 0, LIMIT, "veto tick")
        validate(agent, 0)
        self.agent = agent
        self.events, self.cursor, self.veto_at = events, 0, veto_at
        self.next_turn = 0
        self._busy = self._failed = False

    def step(self):
        a, env = self.agent, self.agent.env
        if self._busy or self._failed:
            raise RuntimeError("unfinished or failed maintenance operation")
        if a.maintenance.stopped or env.stopped or a.episode_terminal:
            raise MaintainStop(a.maintenance.stopped or "operator")
        self._busy = True
        try:
            # Fault onset is controlled by the experiment, never the agent.
            # No schedule, label or receipt is passed to the belief/controller.
            if self.cursor < len(self.events) and self.events[self.cursor][0] == self.next_turn:
                fault = self.events[self.cursor][1]
                if env._fault == "seized" and fault != "seized":
                    raise ValueError("fault injection cannot repair an irreparable component")
                env._fault = fault
                self.cursor += 1
            if self.veto_at == self.next_turn + 1:
                cell = env.cell()
                wsp = a.observation(cell)
                slot = a.cam.get(wsp)
                if slot < 0:
                    # Private test injection at an unseen origin: allocate
                    # its actual observation through the native entry point.
                    # No fault, schedule or repair assertion is written.
                    vertex, _, _ = encode_event(wsp)
                    thermal = wsp[9] - 256 if wsp[9] >= 128 else wsp[9]
                    slot = a._slot_for(wsp, vertex, cell.extract,
                                       (*default_e()[:4], wsp[8], thermal))
                a.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
            try:
                action = a.turn(self.next_turn)
            except MaintainStop:
                # Decision abstention occurs before any native physical tick.
                return {"event": "stop", "tick": self.next_turn, "reason": a.maintenance.stopped}
            self.next_turn += 1
            return {"event": "step", "tick": self.next_turn, "proposed": a.last_proposed_action,
                    "applied": action, "gate": a.last_gate_decision, "reward": a.last_reward,
                    "wsp": a.observation(env.cell()).hex(), "body": (env.body.h, env.body.temperature),
                    "ledger": env.audit_state(), "belief_sha256": hashlib.sha256(base.canonical(a.maintenance.boxes)).hexdigest(),
                    "choice": a.maintenance.last_choice, "stop": a.maintenance.stopped}
        except Exception:
            self._failed = True
            raise
        finally:
            self._busy = False

    def stop(self):
        if self._busy:
            raise RuntimeError("operator stop must be between complete operations")
        if self.agent.episode_terminal:
            return
        self.agent.operator_stop()
        self.agent.maintenance.progress = 0
        self.agent.maintenance.stopped = "operator"

    def snapshot(self):
        if self._busy or self._failed:
            raise ValueError("cannot checkpoint an unfinished/failed operation")
        validate(self.agent, self.next_turn)
        checked_events(self.events)
        integer(self.cursor, 0, len(self.events), "event cursor")
        integer(self.veto_at, 0, LIMIT, "veto")
        for index, (tick, _) in enumerate(self.events):
            if (index < self.cursor and tick > self.next_turn
                    or index < self.cursor and tick == self.next_turn and not self.agent.maintenance.stopped
                    or index >= self.cursor and tick < self.next_turn):
                raise ValueError("fault cursor mismatch")
        last = self.agent.env.last_service
        if last is not None and last.fault_after != self.agent.env._fault:
            if not (self.cursor and self.events[self.cursor - 1] == (self.next_turn, self.agent.env._fault)
                    and self.agent.maintenance.stopped):
                raise ValueError("unrecorded fault after last physical step")
        return {"schema": SCHEMA, "sources": source_hashes(), "next_turn": self.next_turn,
                "events": self.events, "cursor": self.cursor, "veto_at": self.veto_at,
                "state": CODEC.encode(self.agent)}

    def dumps(self):
        raw = base.canonical(self.snapshot())
        if len(raw) > base.MAX_BYTES:
            raise ValueError("checkpoint byte budget")
        return raw

    def save(self, path):
        # Reuse CONT-A's atomic no-replacement file publication, not its profile.
        return base.ContinuityRun.save(self, path)


def loads(raw, *, expected_sha256):
    if type(raw) is not bytes or len(raw) > base.MAX_BYTES:
        raise ValueError("checkpoint byte budget/type")
    if type(expected_sha256) is not str or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
        raise ValueError("external custody mismatch")
    data = json.loads(raw, object_pairs_hook=base._unique_pairs,
                      parse_float=base._no_float, parse_constant=base._no_float)
    if type(data) is not dict or set(data) != {"schema", "sources", "next_turn", "events", "cursor", "veto_at", "state"}:
        raise ValueError("checkpoint shape")
    if data["schema"] != SCHEMA or data["sources"] != source_hashes():
        raise ValueError("checkpoint source/profile mismatch")
    run = object.__new__(MaintainRun)
    run.agent = CODEC.decode(data["state"])
    if type(data["events"]) is not list or any(type(e) is not list for e in data["events"]):
        raise ValueError("invalid event encoding")
    run.events = tuple(tuple(e) for e in data["events"])
    run.next_turn, run.cursor, run.veto_at = data["next_turn"], data["cursor"], data["veto_at"]
    run._busy = run._failed = False
    if run.dumps() != raw:
        raise ValueError("noncanonical checkpoint")
    return run
