"""SLEEP-2: consolidate repeated CAM/T transitions into compact rules.

The source of a rule is the existing memory pair: CAM supplies the WSP state
and ``World`` supplies observed transitions and their counts.  Consolidation
runs off the fast path, reads both, and writes only a bounded rule table.  It
does not delete, relabel or rewrite a CAM slot or a T row, and it never calls
the cortex.

A rule is structural rather than positional:

    (WSP with seq removed, action) -> (next WSP template, seq delta)

It survives only when at least ``MIN_ORIGINS`` distinct T rows support one
uncontradicted result.  One heavily repeated location is therefore not a
general rule.  Prediction restores the local seq into the same 16-byte WSP.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from echoai.core.qn import simhash16
from echoai.core.wsp import pack, unpack

from echoai.nexus0.constants import (
    ACTION_APPROACH,
    N_ACTIONS,
    N_SLOTS,
    UNKNOWN_NEXT,
)
from echoai.nexus0.loop import Agent
from echoai.nexus0.types import default_e


RULE_CAPACITY = 256
MIN_ORIGINS = 8
SEMANTIC_TEMPLATES = 48
LOCAL_STATES = 64
HOLDOUT_STATES = (9, 19, 29, 39, 49)
SCHOOL_STATES = tuple(
    state for state in range(1, LOCAL_STATES - 1)
    if state not in HOLDOUT_STATES
)
CAM_PRESSURE_MIN = 3 * N_SLOTS // 4
CONFLICT_STATE = 61


def packet_of(template_id: int, local_state: int) -> bytes:
    """One semantic observation at a local seq; no frame or memory id."""
    tid = int(template_id)
    state = int(local_state)
    if not 0 <= tid < SEMANTIC_TEMPLATES:
        raise ValueError("template_id outside the synthetic bank")
    if not 0 <= state < LOCAL_STATES:
        raise ValueError("local_state outside the synthetic bank")
    raw = pack(
        src=tid // 6,
        rel=14,                       # OBSERVAR
        dst=4 + tid % 6,
        time=8,                       # AHORA
        E={"V": 0, "A": 20, "D": 0, "C": 40, "U": 10, "B": 0},
        domain=0,
        generator=0x05,
        style=0,
        seq=state,
    )
    if len(raw) != 16:
        raise RuntimeError("WSP layout changed")
    return raw


def template_of(wsp: bytes) -> bytes:
    if not isinstance(wsp, bytes) or len(wsp) != 16:
        raise ValueError("rule input must be one 16-byte WSP")
    raw = bytearray(wsp)
    raw[15] = 0                       # ext.seq, fixed by the WSP ABI
    return bytes(raw)


def seq_of(wsp: bytes) -> int:
    if not isinstance(wsp, bytes) or len(wsp) != 16:
        raise ValueError("rule input must be one 16-byte WSP")
    return int(unpack(wsp)["ext"]["seq"])


def with_seq(template: bytes, seq: int) -> Optional[bytes]:
    value = int(seq)
    if not 0 <= value <= 255:
        return None
    raw = bytearray(template_of(template))
    raw[15] = value
    return bytes(raw)


def successor_state(state: int, action: int, *, conflict: bool = False) -> int:
    aa = int(action) % N_ACTIONS
    if aa == 0:
        return int(state) + (2 if conflict else 1)
    if aa == 1:
        return int(state) - 1
    return int(state)


class ConsolidatedRules:
    """Fixed-capacity, integer-only rules produced by one sleep pass."""

    def __init__(self, capacity: int = RULE_CAPACITY) -> None:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self.current: List[bytes] = [b""] * capacity
        self.action: List[int] = [0] * capacity
        self.next: List[bytes] = [b""] * capacity
        self.delta: List[int] = [0] * capacity
        self.support: List[int] = [0] * capacity
        self.evidence: List[int] = [0] * capacity
        self.size = 0
        self.dropped = 0
        self.covered_rows = 0

    def add(self, current: bytes, action: int, next_template: bytes,
            delta: int, support: int, evidence: int) -> bool:
        if self.size >= self.capacity:
            self.dropped += 1
            return False
        i = self.size
        self.size += 1
        self.current[i] = template_of(current)
        self.action[i] = int(action) % N_ACTIONS
        self.next[i] = template_of(next_template)
        self.delta[i] = int(delta)
        self.support[i] = int(support)
        self.evidence[i] = int(evidence)
        self.covered_rows += int(support)
        return True

    @property
    def compressed_knowledge(self) -> int:
        """Specific T rows represented minus stored general rules."""
        return self.covered_rows - self.size

    def predict(self, wsp: bytes, action: int) -> Optional[bytes]:
        current = template_of(wsp)
        aa = int(action) % N_ACTIONS
        found = -1
        for i in range(self.size):
            if self.current[i] == current and self.action[i] == aa:
                if found >= 0:
                    return None       # ambiguous table: fail closed
                found = i
        if found < 0:
            return None
        return with_seq(self.next[found], seq_of(wsp) + self.delta[found])

    def snapshot_hash(self) -> str:
        h = hashlib.sha256()
        for value in (self.capacity, self.size, self.dropped,
                      self.covered_rows):
            h.update(int(value).to_bytes(8, "little", signed=True))
        for i in range(self.capacity):
            h.update(self.current[i])
            h.update(self.next[i])
            for value in (self.action[i], self.delta[i], self.support[i],
                          self.evidence[i]):
                h.update(int(value).to_bytes(8, "little", signed=True))
        return h.hexdigest()


def memory_hash(agent: Agent) -> dict:
    """Hashes of all source memories SLEEP-2 promises not to modify."""
    def integer(h, value: int, *, signed: bool = True) -> None:
        h.update(int(value).to_bytes(8, "little", signed=signed))

    def blob(h, value: bytes) -> None:
        integer(h, len(value), signed=False)
        h.update(value)

    def string(h, value: str) -> None:
        blob(h, value.encode("utf-8"))

    cam = hashlib.sha256()
    for slot in agent.cam.slot:
        cam.update(bytes([int(bool(slot.occupied))]))
        blob(cam, slot.wsp)
        for value in (slot.vertex, slot.latency, slot.hits, slot.flags,
                      slot.persona, *slot.E, slot.weight, slot.has_fact):
            integer(cam, value)
        for value in (slot.extract, slot.source, slot.label, slot.kind):
            string(cam, value)
        integer(cam, len(slot.see), signed=False)
        for value in slot.see:
            integer(cam, value)
        integer(cam, len(slot.keys), signed=False)
        for value in slot.keys:
            blob(cam, value)
    integer(cam, agent.cam.used)
    integer(cam, agent.cam.destroyed)
    integer(cam, len(agent.cam.key_index), signed=False)
    for key, value in sorted(agent.cam.key_index.items()):
        blob(cam, key)
        integer(cam, value)

    world = hashlib.sha256()
    integer(world, agent.t.n_actions)
    for s in range(N_SLOTS):
        for a in range(agent.t.n_actions):
            for table in (agent.t.pred, agent.t.n, agent.t.alt, agent.t.alt_n):
                integer(world, table[s][a], signed=False)
        integer(world, len(agent.t.inv[s]), signed=False)
        for nxt, action, count in agent.t.inv[s]:
            for value in (nxt, action, count):
                integer(world, value, signed=False)
    integer(world, agent.t.conflicts, signed=False)
    integer(world, agent.t.inv_dropped, signed=False)

    q = hashlib.sha256()
    for value in (agent.q.n_actions, agent.q.trace, agent.q.explore_flat,
                  agent.q.remainder, agent.q.inherited_b):
        integer(q, value)
    for table in (agent.q.q, agent.q.rem, agent.q.z):
        integer(q, len(table), signed=False)
        for row in table:
            integer(q, len(row), signed=False)
            for value in row:
                integer(q, value)
    integer(q, len(agent.q._active), signed=False)
    for state, action in agent.q._active:
        integer(q, state)
        integer(q, action)
    return {"cam": cam.hexdigest(), "t": world.hexdigest(), "q": q.hexdigest()}


def consolidate(agent: Agent, capacity: int = RULE_CAPACITY,
                min_origins: int = MIN_ORIGINS) -> Tuple[ConsolidatedRules, dict]:
    """Read CAM/T once and emit only recurrent, uncontradicted rules."""
    if type(min_origins) is not int or min_origins <= 1:
        raise ValueError("min_origins must be an integer greater than one")
    # (template, action) -> candidate result -> distinct origin slots/evidence
    groups: Dict[
        Tuple[bytes, int],
        Dict[Tuple[bytes, int], Tuple[Set[int], int]],
    ] = {}
    source_rows = 0
    for slot_id, slot in enumerate(agent.cam.slot):
        if not slot.occupied:
            continue
        for action in range(agent.t.n_actions):
            next_slot = agent.t.pred[slot_id][action]
            count = agent.t.n[slot_id][action]
            if next_slot == UNKNOWN_NEXT or count <= 0:
                continue
            if not 0 <= next_slot < len(agent.cam.slot):
                continue
            target = agent.cam.slot[next_slot]
            if not target.occupied:
                continue
            source_rows += 1
            current_template = template_of(slot.wsp)
            next_template = template_of(target.wsp)
            delta = seq_of(target.wsp) - seq_of(slot.wsp)
            key = (current_template, action)
            result = (next_template, delta)
            candidates = groups.setdefault(key, {})
            if result not in candidates:
                candidates[result] = (set(), 0)
            origins, evidence = candidates[result]
            origins.add(slot_id)
            candidates[result] = (origins, evidence + int(count))

            # World keeps one losing alternative per row.  Consolidation
            # must read it too: otherwise a contradictory episode hidden
            # behind T's incumbent winner could become a confident rule.
            alt_slot = agent.t.alt[slot_id][action]
            alt_count = agent.t.alt_n[slot_id][action]
            if (alt_slot != UNKNOWN_NEXT and alt_count > 0
                    and 0 <= alt_slot < len(agent.cam.slot)):
                alternate = agent.cam.slot[alt_slot]
                if alternate.occupied:
                    alt_result = (
                        template_of(alternate.wsp),
                        seq_of(alternate.wsp) - seq_of(slot.wsp),
                    )
                    if alt_result not in candidates:
                        candidates[alt_result] = (set(), 0)
                    alt_origins, alt_evidence = candidates[alt_result]
                    alt_origins.add(slot_id)
                    candidates[alt_result] = (
                        alt_origins,
                        alt_evidence + int(alt_count),
                    )

    rules = ConsolidatedRules(capacity)
    ambiguous_groups = 0
    below_support = 0
    for (current, action), candidates in sorted(
            groups.items(), key=lambda item: (item[0][0], item[0][1])):
        if len(candidates) != 1:
            ambiguous_groups += 1
            continue
        (next_template, delta), (origins, evidence) = next(iter(candidates.items()))
        if len(origins) < min_origins:
            below_support += 1
            continue
        rules.add(current, action, next_template, delta,
                  len(origins), evidence)
    return rules, {
        "source_rows": source_rows,
        "candidate_groups": len(groups),
        "ambiguous_groups": ambiguous_groups,
        "below_support": below_support,
        "min_origins": min_origins,
    }


def build_day(*, contradiction: bool = False) -> Tuple[Agent, Dict[Tuple[int, int], int]]:
    """Populate 75% of CAM, then teach T while reserving exam rows."""
    agent = Agent(ask=False)
    slots: Dict[Tuple[int, int], int] = {}
    for template_id in range(SEMANTIC_TEMPLATES):
        for state in range(LOCAL_STATES):
            wsp = packet_of(template_id, state)
            slots[(template_id, state)] = agent._slot_for(
                wsp, simhash16(wsp), "", default_e(), source="sleep2-sensor"
            )
    for template_id in range(SEMANTIC_TEMPLATES):
        for state in SCHOOL_STATES:
            for action in range(N_ACTIONS):
                next_state = successor_state(state, action)
                agent.t.observe(slots[(template_id, state)], action,
                                slots[(template_id, next_state)])
                if (contradiction and action == ACTION_APPROACH
                        and state == CONFLICT_STATE):
                    alternate = successor_state(state, action, conflict=True)
                    agent.t.observe(slots[(template_id, state)], action,
                                    slots[(template_id, alternate)])
    return agent, slots


def _exam(agent: Agent, slots: Dict[Tuple[int, int], int],
          rules: ConsolidatedRules) -> dict:
    before = rules.snapshot_hash()
    rows: List[dict] = []
    total_t = total_rule = total_points = 0
    for template_id in range(SEMANTIC_TEMPLATES):
        t_hits = rule_hits = 0
        for state in HOLDOUT_STATES:
            wsp = packet_of(template_id, state)
            slot = slots[(template_id, state)]
            for action in range(N_ACTIONS):
                target_state = successor_state(state, action)
                target_slot = slots[(template_id, target_state)]
                t_pred = agent.t.predict(slot, action)
                rule_wsp = rules.predict(wsp, action)
                t_hits += int(t_pred == target_slot)
                rule_hits += int(
                    rule_wsp == packet_of(template_id, target_state)
                )
                total_points += 1
        points = len(HOLDOUT_STATES) * N_ACTIONS
        rows.append({"template": template_id, "points": points,
                     "t_hits": t_hits, "rule_hits": rule_hits})
        total_t += t_hits
        total_rule += rule_hits
    return {
        "points": total_points,
        "t_hits": total_t,
        "rule_hits": total_rule,
        "gain_over_t": total_rule - total_t,
        "rows": rows,
        "rule_hash_before": before,
        "rule_hash_after": rules.snapshot_hash(),
    }


def experiment() -> dict:
    agent, slots = build_day()
    occupied = sum(slot.occupied != 0 for slot in agent.cam.slot)
    source_before = memory_hash(agent)
    destroyed_before = agent.cam.destroyed
    rules, sleep = consolidate(agent)
    source_after_sleep = memory_hash(agent)
    exam = _exam(agent, slots, rules)
    source_after_exam = memory_hash(agent)

    conflict_agent, conflict_slots = build_day(contradiction=True)
    conflict_before = memory_hash(conflict_agent)
    conflict_rules, conflict_sleep = consolidate(conflict_agent)
    conflict_exam = _exam(conflict_agent, conflict_slots, conflict_rules)
    conflict_after = memory_hash(conflict_agent)

    return {
        "slice": "SLEEP-2",
        "cam_slots": N_SLOTS,
        "cam_occupied": occupied,
        "cam_pressure_min": CAM_PRESSURE_MIN,
        "semantic_templates": SEMANTIC_TEMPLATES,
        "local_states": LOCAL_STATES,
        "school_states": len(SCHOOL_STATES),
        "holdout_states": list(HOLDOUT_STATES),
        "rule_capacity": rules.capacity,
        "rules": rules.size,
        "covered_rows": rules.covered_rows,
        "compressed_knowledge_before": 0,
        "compressed_knowledge_after": rules.compressed_knowledge,
        "dropped_rules": rules.dropped,
        "sleep": sleep,
        "exam": exam,
        "source_hash_before": source_before,
        "source_hash_after_sleep": source_after_sleep,
        "source_hash_after": source_after_exam,
        "source_unchanged": (
            source_before == source_after_sleep == source_after_exam
        ),
        "destroyed_before": destroyed_before,
        "destroyed_after": agent.cam.destroyed,
        "cortex_calls": agent.metrics.cortex_calls,
        "conflict_control": {
            "rules": conflict_rules.size,
            "ambiguous_groups": conflict_sleep["ambiguous_groups"],
            "world_conflicts": conflict_agent.t.conflicts,
            "rule_hits": conflict_exam["rule_hits"],
            "exam": conflict_exam,
            "source_unchanged": conflict_before == conflict_after,
            "source_hash_before": conflict_before,
            "source_hash_after": conflict_after,
            "destroyed": conflict_agent.cam.destroyed,
            "cortex_calls": conflict_agent.metrics.cortex_calls,
        },
    }


def green(report: dict) -> bool:
    """Recompute headline claims from rows and reject destructive sleep."""
    try:
        if (report["slice"], report["cam_slots"], report["semantic_templates"],
                report["local_states"], report["rule_capacity"]) != (
                    "SLEEP-2", N_SLOTS, SEMANTIC_TEMPLATES,
                    LOCAL_STATES, RULE_CAPACITY):
            return False
        if report["cam_occupied"] < report["cam_pressure_min"]:
            return False
        if report["cam_pressure_min"] != CAM_PRESSURE_MIN:
            return False
        if report["rules"] != SEMANTIC_TEMPLATES * N_ACTIONS:
            return False
        if report["dropped_rules"] != 0:
            return False
        if report["covered_rows"] != report["sleep"]["source_rows"]:
            return False
        expected_compression = report["covered_rows"] - report["rules"]
        if report["compressed_knowledge_before"] != 0:
            return False
        if report["compressed_knowledge_after"] != expected_compression:
            return False
        if expected_compression <= 0:
            return False
        exam = report["exam"]
        if exam["points"] != sum(row["points"] for row in exam["rows"]):
            return False
        if exam["t_hits"] != sum(row["t_hits"] for row in exam["rows"]):
            return False
        if exam["rule_hits"] != sum(row["rule_hits"] for row in exam["rows"]):
            return False
        if exam["gain_over_t"] != exam["rule_hits"] - exam["t_hits"]:
            return False
        if exam["t_hits"] != 0 or exam["rule_hits"] != exam["points"]:
            return False
        if exam["rule_hash_before"] != exam["rule_hash_after"]:
            return False
        if report["source_unchanged"] is not True:
            return False
        if not (report["source_hash_before"]
                == report["source_hash_after_sleep"]
                == report["source_hash_after"]):
            return False
        if report["destroyed_before"] != 0 or report["destroyed_after"] != 0:
            return False
        if report["cortex_calls"] != 0:
            return False
        control = report["conflict_control"]
        if control["ambiguous_groups"] != SEMANTIC_TEMPLATES:
            return False
        if control["world_conflicts"] != SEMANTIC_TEMPLATES:
            return False
        if control["rules"] != SEMANTIC_TEMPLATES * (N_ACTIONS - 1):
            return False
        if control["source_unchanged"] is not True:
            return False
        if control["source_hash_before"] != control["source_hash_after"]:
            return False
        if control["destroyed"] != 0 or control["cortex_calls"] != 0:
            return False
        # With approach refused, only avoid+wait can hit: 2/3 of the exam.
        cexam = control["exam"]
        if cexam["rule_hits"] != SEMANTIC_TEMPLATES * len(HOLDOUT_STATES) * 2:
            return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_sleep2_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
