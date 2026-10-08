"""Read-only world/observation audit. Full-state truth stays here, not in Q."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT
from echoai.echo4.viability import STATE_COUNT, Viability, analyze, indexed_body
from echoai.echo4.world import Body, CAPACITY, DockRules, transition


def observed(body: Body) -> bytes:
    return encode_cell(0, KIND_OBJECT, vitality=body.h,
                       temperature=body.temperature, temperature_bands=8)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def observation_audit(graph: Viability) -> dict:
    packets = [observed(indexed_body(i)) for i in range(STATE_COUNT)]
    groups: dict[bytes, list[int]] = {}
    for index, packet in enumerate(packets):
        groups.setdefault(packet, []).append(index)
    non_markov = 0
    mixed_viability = 0
    viable_action_aliases = 0
    for indices in groups.values():
        mixed_viability += len({graph.kernel[i] for i in indices}) > 1
        action_masks = {
            tuple(nxt >= 0 and graph.kernel[nxt] for nxt in graph.successors[i])
            for i in indices
        }
        viable_action_aliases += len(action_masks) > 1
        aliased = False
        for action in range(3):
            outcomes = set()
            for index in indices:
                nxt = graph.successors[index][action]
                if nxt >= 0:
                    outcomes.add((packets[nxt], False, 0))
                else:
                    step = transition(indexed_body(index), action, graph.rules)
                    outcomes.add((observed(step.after), True, step.reward))
            aliased |= len(outcomes) > 1
        non_markov += aliased

    terminal_packets = {
        observed(Body(h, t))
        for h in range(CAPACITY + 1)
        for t in range(CAPACITY + 1)
        if h == 0 or t in (0, CAPACITY)
    }
    live_packets = set(packets)
    return {
        "packet_bytes": 16,
        "living_packets": len(live_packets),
        "all_body_packets": len(live_packets | terminal_packets),
        "terminal_packets_aliasing_live": len(terminal_packets & live_packets),
        "non_markov_groups": non_markov,
        "groups_mixing_viable_and_doomed_states": mixed_viability,
        "groups_with_different_viable_action_sets": viable_action_aliases,
        "partial_observation_control_proven": False,
        "note": "Band aliasing is measured, not a proof that every history-based policy fails.",
    }


def world_audit(rules: DockRules = DockRules(), initial: Body = Body()) -> dict:
    graph = analyze(rules)
    witness = graph.witness(initial)
    report = {
        "schema": 1,
        "experiment": "ECHO4-WORLD1",
        "scope": "deterministic full-state feasibility; not learned maintenance",
        "rules": asdict(rules),
        "initial": asdict(initial),
        "living_states": STATE_COUNT,
        "checked_transitions": STATE_COUNT * 3,
        "kernel_states": sum(graph.kernel),
        "initial_viable": graph.contains(initial),
        "max_actions_including_terminal": graph.max_steps(initial),
        "graph_sha256": digest(graph.successors),
        "kernel_sha256": digest(graph.kernel),
        "observation": observation_audit(graph),
        "witness": None,
        "maintenance_acceptance": "not_run",
    }
    if witness is not None:
        data = asdict(witness)
        report["witness"] = {
            "valid": witness.valid(rules),
            "prefix_actions": witness.prefix_length,
            "cycle_actions": witness.cycle_length,
            "sha256": digest(data),
            "cycle_states": [asdict(s) for s in witness.states[witness.cycle_start:]],
            "cycle_action_ids": list(witness.actions[witness.cycle_start:]),
        }
    return report
