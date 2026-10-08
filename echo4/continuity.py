"""CONT-A executor checkpoint, not a cognitive bus or a general deserializer.

Exact allowlisted SelfAgent/WORLD-1 profile, at complete turn boundaries.
Private body state stays in executor custody. Never export this to a cortex.
The caller supplies a trusted digest; an untrusted self-signed file is not
evidence. No pickle, dynamically imported classes or executable payloads.
"""
from __future__ import annotations

from dataclasses import fields
import hashlib
import hmac
import json
import os
from pathlib import Path
import tempfile

from echoai.core.cam import Cam, CamSlot
from echoai.echo4.adapter import DockEnv
from echoai.echo4.boundary import BoundaryMap, integer
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.self_model import Reference, SelfChangeMonitor
from echoai.echo4.sensation import SensoryHistory
from echoai.echo4.sensation_predictor import Prediction, Sensation, SensationPredictor
from echoai.echo4.world import Body, DockRules, Transition
from echoai.nexus0.pattern import PatternMemory
from echoai.nexus0.qtable import QTable
from echoai.nexus0.types import Metrics
from echoai.nexus0.world import World

SCHEMA = "echo4-continuity-a-v1"
PROFILE = "SelfAgent-WORLD1-nominal-complete-turns"
MAX_BYTES = 8 * 1024 * 1024
MAX_OBJECTS = 5000
MAX_VALUES = 500000
ROOT = Path(__file__).resolve().parents[1]

# Fail closed on source changes, including imported native representation and
# policy code. This is compatibility/custody, not a source authenticity claim.
SOURCES = (
    "echo4/continuity.py", "echo4/adapter.py", "echo4/world.py",
    "echo4/self_agent.py", "echo4/self_model.py", "echo4/boundary_agent.py",
    "echo4/boundary.py", "echo4/sensation_agent.py", "echo4/sensation.py",
    "echo4/sensation_predictor.py", "nexus0/loop.py", "nexus0/qtable.py",
    "nexus0/world.py", "nexus0/pattern.py", "nexus0/types.py",
    "nexus0/constants.py", "nexus0/gate.py", "nexus0/encoder.py",
    "nexus0/env.py", "nexus0/lex.py", "nexus0/cortex.py",
    "nexus0/cortex_turn.py", "nexus0/escalate.py", "nexus0/oracle.py",
    "nexus0/plan.py", "nexus0/thought.py", "nexus0/attend.py",
    "core/cam.py", "core/qn.py", "core/wsp.py",
    "core/spoke.py", "core/stdp.py", "core/dag.py",
)

AGENT_FIELDS = """cam n_actions q t metrics evidence_budget evidence_greedy
last_evidence_explore last_proposed_action last_gate_decision last_explore
env survival_enabled thermal_enabled temperature_bands temperature_observed
initial_h H initial_temperature temperature episode_terminal life_turns life_id
deaths last_reward sample_wsp plan_depth body_offset self_model ask_enabled
last_ask oracle cortex_enabled last_attend last_cortex_action cortex_log
thought_log escalate_enabled level_counts search_copies_q search_differs
search_strictly_better pattern_memory prev_slot conflict_attend conflict_wakes
conflict_suppressed sensation last_sensation last_sensory_prediction boundary
self_change""".split()

# Closed schema, not arbitrary __dict__ loading. Dataclass fields come only
# from these statically imported, source-pinned inert classes.
REGISTRY = {
    "agent": (SelfAgent, AGENT_FIELDS),
    "cam": (Cam, "slot used destroyed key_index".split()),
    "q": (QTable, "n_actions inherited_b q trace explore_flat remainder rem z _active".split()),
    "t": (World, "n_actions pred n alt alt_n conflicts inv inv_dropped".split()),
    "pattern": (PatternMemory, "capacity min_hits order key pred n alt alt_n size dropped conflicts observations".split()),
    "env": (DockEnv, "rules initial body resets total_steps life_steps resource_in resource_used resource_spill last_transition".split()),
    "sensation": (SensationPredictor, "history cam world memory context_capacity contexts context_dropped cam_dropped update_base frozen pending".split()),
    "history": (SensoryHistory, list(SensoryHistory.__slots__)),
    "boundary": (BoundaryMap, "cam capacity rows pairs last_identifier frozen".split()),
    "self": (SelfChangeMonitor, "boundary references sealed".split()),
}
for _cls in (CamSlot, Metrics, Body, DockRules, Transition, Reference, Prediction, Sensation):
    REGISTRY[_cls.__name__] = (_cls, [f.name for f in fields(_cls)])
TYPE_TAG = {cls: tag for tag, (cls, _) in REGISTRY.items()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def source_hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def _attributes(obj, names):
    if hasattr(obj, "__dict__") and set(vars(obj)) != set(names):
        raise ValueError("unexpected or missing state fields")
    return {name: getattr(obj, name) for name in names}


def _encode(agent):
    objects, identities, containers = [], {}, set()
    count = 0

    def encode(value, depth=0):
        nonlocal count
        count += 1
        if depth > 64 or count > MAX_VALUES:
            raise ValueError("state exceeds structural budget")
        kind = type(value)
        if value is None or kind in (bool, str):
            return value
        if kind is int:
            if value.bit_length() > 64:
                raise ValueError("integer outside checkpoint profile")
            return value
        if kind in (bytes, bytearray):
            return {kind.__name__: value.hex()}
        if kind in (list, dict):
            # No mutable container aliases in this profile; do not silently
            # duplicate them and change future behavior. Object aliases below
            # are supported (one shared CAM/T/BOUNDARY).
            if id(value) in containers:
                raise ValueError("aliased or cyclic mutable container")
            containers.add(id(value))
        if kind in (list, tuple):
            items = [encode(v, depth + 1) for v in value]
            return items if kind is list else {"tuple": items}
        if kind is dict:
            return {"map": [[encode(k, depth + 1), encode(v, depth + 1)] for k, v in value.items()]}
        if kind not in TYPE_TAG:
            raise ValueError("unsupported checkpoint type")
        if id(value) not in identities:
            if len(objects) >= MAX_OBJECTS:
                raise ValueError("too many state objects")
            index = len(objects)
            identities[id(value)] = index
            tag = TYPE_TAG[kind]
            obj = {"type": tag, "fields": {}}
            objects.append(obj)
            obj["fields"] = {k: encode(v, depth + 1)
                             for k, v in _attributes(value, REGISTRY[tag][1]).items()}
        return {"ref": identities[id(value)]}

    root = encode(agent)
    return {"root": root, "objects": objects}


def _decode(graph):
    if type(graph) is not dict or set(graph) != {"root", "objects"}:
        raise ValueError("invalid object graph")
    records = graph["objects"]
    if type(records) is not list or not 1 <= len(records) <= MAX_OBJECTS:
        raise ValueError("invalid object budget")
    objects = []
    for record in records:
        if type(record) is not dict or set(record) != {"type", "fields"}:
            raise ValueError("invalid object record")
        tag = record["type"]
        if type(tag) is not str or tag not in REGISTRY:
            raise ValueError("unknown checkpoint class")
        cls, names = REGISTRY[tag]
        if type(record["fields"]) is not dict or set(record["fields"]) != set(names):
            raise ValueError("invalid class fields")
        objects.append(object.__new__(cls))
    count = 0

    def decode(value, depth=0):
        nonlocal count
        count += 1
        if depth > 64 or count > MAX_VALUES:
            raise ValueError("state exceeds structural budget")
        kind = type(value)
        if value is None or kind in (str, bool):
            return value
        if kind is int:
            if value.bit_length() > 64:
                raise ValueError("integer outside checkpoint profile")
            return value
        if kind is list:
            return [decode(v, depth + 1) for v in value]
        if kind is not dict or len(value) != 1:
            raise ValueError("invalid value tag")
        tag, item = next(iter(value.items()))
        if tag == "ref":
            integer(item, 0, len(objects) - 1)
            return objects[item]
        if tag in ("bytes", "bytearray") and type(item) is str:
            raw = bytes.fromhex(item)
            return raw if tag == "bytes" else bytearray(raw)
        if tag == "tuple" and type(item) is list:
            return tuple(decode(v, depth + 1) for v in item)
        if tag == "map" and type(item) is list:
            result = {}
            for pair in item:
                if type(pair) is not list or len(pair) != 2:
                    raise ValueError("invalid map pair")
                key, val = (decode(v, depth + 1) for v in pair)
                if key in result:
                    raise ValueError("duplicate map key")
                result[key] = val
            return result
        raise ValueError("unknown value tag")

    for obj, record in zip(objects, records):
        for name, value in record["fields"].items():
            object.__setattr__(obj, name, decode(value))
    root = decode(graph["root"])
    # Reject hidden unreachable objects, noncanonical references and shapes.
    if _encode(root) != graph:
        raise ValueError("noncanonical object graph")
    return root


def _matrix(value, rows, columns, low, high):
    if type(value) is not list or len(value) != rows:
        raise ValueError("invalid matrix rows")
    for row in value:
        if type(row) is not list or len(row) != columns:
            raise ValueError("invalid matrix columns")
        for number in row:
            integer(number, low, high)


def validate(agent, next_turn):
    """Validate the supported runtime profile; never mutate the candidate."""
    if type(agent) is not SelfAgent or type(agent.env) is not DockEnv:
        raise ValueError("only nominal SelfAgent/DockEnv is supported in CONT-A")
    for obj, cls in ((agent.cam, Cam), (agent.q, QTable), (agent.t, World),
                     (agent.metrics, Metrics), (agent.sensation, SensationPredictor),
                     (agent.boundary, BoundaryMap), (agent.self_change, SelfChangeMonitor)):
        if type(obj) is not cls:
            raise ValueError("invalid profile component")
    for name in ("self_model", "oracle", "cortex_log", "thought_log", "pattern_memory"):
        if getattr(agent, name) is not None:
            raise ValueError("active external component or log")
    for name in ("cortex_enabled", "ask_enabled", "escalate_enabled", "conflict_attend"):
        if getattr(agent, name) is not False:
            raise ValueError("unsupported optional controller")
    if (agent.plan_depth != 0 or agent.body_offset != 0 or agent.evidence_budget != 0
            or agent.n_actions != 3 or agent.q.n_actions != 3 or agent.t.n_actions != 3
            or agent.q.trace is not False or agent.q.remainder is not True
            or agent.q.explore_flat is not True or agent.q.inherited_b != 0
            or agent.q.z != [] or agent.q._active != []):
        raise ValueError("unsupported policy profile")
    if (agent.survival_enabled is not True or agent.thermal_enabled is not True
            or agent.temperature_bands != 8 or agent.temperature_observed is not True):
        raise ValueError("unsupported physiology profile")
    world = agent.env
    if type(world.rules) is not DockRules or world.rules != DockRules():
        raise ValueError("only nominal WORLD-1 rules")
    if type(world.body) is not Body or type(world.initial) is not Body:
        raise ValueError("missing physical state")
    world.body.__post_init__()
    world.initial.__post_init__()
    integer(agent.H, 0, 127)
    integer(agent.temperature, 0, 127)
    if (world.body != Body(agent.H, agent.temperature)
            or world.initial != Body(agent.initial_h, agent.initial_temperature)
            or not world.balanced):
        raise ValueError("body or resource ledger mismatch")
    if type(agent.episode_terminal) is not bool or agent.episode_terminal != (not world.body.alive):
        raise ValueError("terminal status mismatch")
    integer(next_turn, 0, (1 << 31) - 1)
    for value in (agent.life_turns, agent.metrics.turns, world.life_steps, world.total_steps):
        integer(value, 0, (1 << 31) - 1)
        if value != next_turn:
            raise ValueError("timeline mismatch")
    if agent.life_id != 0 or world.resets != 0:
        raise ValueError("respawn is not resume")
    if any(value != 0 for value in (agent.cam.destroyed, agent.metrics.destroyed,
                                   agent.metrics.false_facts, agent.metrics.cortex_calls)):
        raise ValueError("violated baseline invariant")
    sense = agent.sensation
    if (sense.cam is not agent.cam or sense.world is not agent.t
            or agent.boundary.cam is not agent.cam
            or agent.self_change.boundary is not agent.boundary):
        raise ValueError("shared state identity lost")
    if sense.pending is not None or sense.update_base is not False:
        raise ValueError("checkpoint must be between native turns")
    if type(sense.history) is not SensoryHistory or type(sense.memory) is not PatternMemory:
        raise ValueError("unsupported sensory state")
    history = sense.history
    if history.depth not in (0, 2, 4) or type(history._buffer) is not bytearray:
        raise ValueError("invalid history shape")
    integer(history._count, 0, history.depth)
    if (history._started is not True or len(history._buffer) != 16 + 17 * history.depth
            or history.snapshot()[-16:] != agent.observation(world.cell())):
        raise ValueError("sensory history disagrees with observation")
    if len(agent.cam.slot) != 4096:
        raise ValueError("invalid CAM capacity")
    occupied = 0
    for slot in agent.cam.slot:
        if type(slot) is not CamSlot or type(slot.wsp) is not bytes or len(slot.wsp) != 16:
            raise ValueError("invalid CAM/WSP")
        integer(slot.occupied, 0, 1)
        integer(slot.has_fact, 0, 1)
        occupied += slot.occupied
        if slot.has_fact and (not slot.occupied or not slot.extract):
            raise ValueError("fact without evidence")
    if type(agent.cam.used) is not int or occupied != agent.cam.used:
        raise ValueError("CAM occupancy mismatch")
    for key, slot in agent.cam.key_index.items():
        integer(slot, 0, 4095)
        if type(key) is not bytes or key not in agent.cam.slot[slot].keys or not agent.cam.slot[slot].occupied:
            raise ValueError("invalid CAM key index")
    _matrix(agent.q.q, 4096, 3, -127, 127)
    _matrix(agent.q.rem, 4096, 3, -3, 3)
    for name in ("pred", "n", "alt", "alt_n"):
        _matrix(getattr(agent.t, name), 4096, 3, 0, 65535)
    if len(agent.t.inv) != 4096:
        raise ValueError("invalid inverse state")
    memory = sense.memory
    integer(memory.capacity, 1, 8191)
    for name in ("key", "pred", "n", "alt", "alt_n"):
        values = getattr(memory, name)
        if type(values) is not list or len(values) != memory.capacity:
            raise ValueError("invalid PATTERN shape")
    integer(sense.context_capacity, 1, 4096)
    if len(sense.contexts) > sense.context_capacity:
        raise ValueError("context capacity exceeded")
    integer(agent.boundary.capacity, 1, 128)
    if max(len(agent.boundary.rows), len(agent.self_change.references)) > agent.boundary.capacity:
        raise ValueError("reference capacity exceeded")


class ContinuityRun:
    """Executor-owned logical clock. No reset/respawn/cortex entry point."""

    def __init__(self, agent, next_turn=0):
        validate(agent, next_turn)
        self.agent, self.next_turn = agent, next_turn
        self._busy = self._failed = False

    def step(self, *, greedy=False):
        if type(greedy) is not bool:
            raise ValueError("greedy must be boolean")
        if self._busy or self._failed:
            raise RuntimeError("unfinished or failed turn")
        if self.agent.episode_terminal:
            raise RuntimeError("terminal execution cannot resume acting")
        self._busy = True
        try:
            action = self.agent.turn(self.next_turn, greedy=greedy)
            self.next_turn += 1
            return action
        except Exception:
            self._failed = True
            raise
        finally:
            self._busy = False

    def snapshot(self):
        if self._busy or self._failed:
            raise ValueError("checkpoint cannot hide an unfinished/failed turn")
        validate(self.agent, self.next_turn)
        return {"schema": SCHEMA, "profile": PROFILE, "sources": source_hashes(),
                "next_turn": self.next_turn, "state": _encode(self.agent)}

    def dumps(self):
        raw = canonical(self.snapshot())
        if len(raw) > MAX_BYTES:
            raise ValueError("checkpoint exceeds byte budget")
        return raw

    def state_hash(self):
        return hashlib.sha256(self.dumps()).hexdigest()

    def save(self, path):
        """Publish a complete file with no replacement; return custody digest."""
        raw = self.dumps()
        path = Path(path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".continuity-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(temporary, path)  # fails if destination already exists
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = val
    return result


def _no_float(_value):
    raise ValueError("float/nonfinite values are unsupported")


def loads(raw, *, expected_sha256):
    """Only accept a checkpoint pinned by an independently trusted caller."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("invalid checkpoint byte budget")
    if (type(expected_sha256) is not str or len(expected_sha256) != 64
            or not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256)):
        raise ValueError("custody digest mismatch")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_float=_no_float, parse_constant=_no_float)
        if type(value) is not dict or set(value) != {"schema", "profile", "sources", "next_turn", "state"}:
            raise ValueError("invalid checkpoint envelope")
        if value["schema"] != SCHEMA or value["profile"] != PROFILE:
            raise ValueError("unsupported checkpoint version/profile")
        if value["sources"] != source_hashes():
            raise ValueError("source version mismatch; explicit migration required")
        agent = _decode(value["state"])
        result = ContinuityRun(agent, value["next_turn"])
        if result.dumps() != raw:
            raise ValueError("checkpoint is not canonical")
        return result
    except (TypeError, KeyError, AttributeError, IndexError, RecursionError, UnicodeError) as exc:
        raise ValueError("malformed checkpoint") from exc


def load(path, *, expected_sha256):
    with Path(path).open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    return loads(raw, expected_sha256=expected_sha256)
