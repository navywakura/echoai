"""External exhaustive temporal audit. Never imported by the agent.

Compatible physical states and viable actions are evaluator-only ground
truth, not a learned predictor, deployable filter or action-selection input.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from echoai.echo4.audit import digest, observed
from echoai.echo4.sensation import HISTORY_STEPS, RECORD_BYTES, SensoryHistory
from echoai.echo4.viability import STATE_COUNT, analyze, indexed_body, state_index
from echoai.echo4.world import Body, DockRules, transition


@dataclass
class _Group:
    # Unbounded evaluator storage, NOT the runtime memory budget.
    states: int = 0
    prefixes: int = 0


def _indices(bits: int):
    while bits:
        low = bits & -bits
        yield low.bit_length() - 1
        bits ^= low


def _summarize(groups, packets, outcomes, viable_masks):
    report = {
        "groups": len(groups), "prefixes": 0,
        "ambiguous_observation_groups": 0,
        "ambiguous_terminal_groups": 0,
        "ambiguous_joint_groups": 0,
        "prefixes_with_observation_ambiguity": 0,
        "prefixes_with_terminal_ambiguity": 0,
        "prefixes_with_joint_ambiguity": 0,
        "different_viable_action_sets": 0,
        "mixed_viable_doomed_groups": 0,
        "all_doomed_groups": 0,
        "incompatible_viable_groups": 0,
        "prefixes_with_incompatible_viable_actions": 0,
        "max_compatible_states": 0,
        "ambiguity_witness": None,
    }
    for history, group in sorted(groups.items()):
        indices = tuple(_indices(group.states))
        report["prefixes"] += group.prefixes
        report["max_compatible_states"] = max(report["max_compatible_states"], len(indices))
        masks = {viable_masks[i] for i in indices}
        intersection = 7
        for mask in masks:
            intersection &= mask
        all_viable = 0 not in masks
        report["different_viable_action_sets"] += int(len(masks) > 1)
        report["mixed_viable_doomed_groups"] += int(0 in masks and len(masks) > 1)
        report["all_doomed_groups"] += int(masks == {0})
        incompatible = all_viable and intersection == 0
        report["incompatible_viable_groups"] += int(incompatible)
        report["prefixes_with_incompatible_viable_actions"] += group.prefixes if incompatible else 0
        observation_ambiguous = terminal_ambiguous = False
        for action in range(3):
            possibilities = {outcomes[i][action] for i in indices}
            observation_ambiguous |= len({p for p, _ in possibilities}) > 1
            terminal_ambiguous |= len({t for _, t in possibilities}) > 1
            if len(possibilities) > 1 and report["ambiguity_witness"] is None:
                first = indices[0]
                second = next(i for i in indices if outcomes[i][action] != outcomes[first][action])
                report["ambiguity_witness"] = {
                    "history_hex": history.hex(), "executed_action_to_probe": action,
                    "compatible_final_bodies": [
                        [indexed_body(i).h, indexed_body(i).temperature]
                        for i in (first, second)
                    ],
                    "current_wsp_hex": packets[first].hex(),
                    "next_outcomes": [
                        {"wsp_hex": outcomes[i][action][0].hex(),
                         "terminal": outcomes[i][action][1]}
                        for i in (first, second)
                    ],
                }
        joint = observation_ambiguous or terminal_ambiguous
        for kind, flag in (("observation", observation_ambiguous),
                           ("terminal", terminal_ambiguous), ("joint", joint)):
            report[f"ambiguous_{kind}_groups"] += int(flag)
            report[f"prefixes_with_{kind}_ambiguity"] += group.prefixes if flag else 0
    return report


def temporal_audit(*, max_depth: int = 4,
                   initial_states: tuple[Body, ...] | None = None) -> dict:
    """Fixed nominal WORLD-1. Smaller explicit domains support reference tests.

    No training/exam split: this is exhaustive public development evidence.
    Every arm sees the same surviving prefixes, projected to a shorter suffix.
    """
    if type(max_depth) is not int or max_depth not in HISTORY_STEPS:
        raise ValueError("max_depth must be 0, 2 or 4")
    if initial_states is not None:
        if (type(initial_states) is not tuple or not initial_states
                or any(type(s) is not Body or not s.alive for s in initial_states)
                or len(set(initial_states)) != len(initial_states)):
            raise ValueError("initial_states must be a nonempty tuple of distinct living bodies")
    starts = (tuple(range(STATE_COUNT)) if initial_states is None
              else tuple(sorted(state_index(s) for s in initial_states)))
    graph = analyze()
    rules = DockRules()
    packets = tuple(observed(indexed_body(i)) for i in range(STATE_COUNT))
    outcomes = tuple(tuple(
        (observed(step.after), not step.after.alive)
        for action in range(3)
        for step in (transition(indexed_body(i), action, rules),)
    ) for i in range(STATE_COUNT))
    viable_masks = tuple(sum(
        1 << action for action, nxt in enumerate(row) if nxt >= 0 and graph.kernel[nxt]
    ) for row in graph.successors)
    depths = tuple(d for d in HISTORY_STEPS if d <= max_depth)
    groups = {d: {} for d in depths}
    ended = [0] * (max_depth + 1)
    completed = 0

    def visit(index, history, depth):
        nonlocal completed
        if depth == max_depth:
            completed += 1
            for retained in depths:
                key = history[-(16 + RECORD_BYTES * retained):]
                group = groups[retained].get(key)
                if group is None:
                    group = groups[retained][key] = _Group()
                group.states |= 1 << index
                group.prefixes += 1
            return
        for action, nxt in enumerate(graph.successors[index]):
            if nxt < 0:
                ended[depth + 1] += 1
            else:
                visit(nxt, history + bytes((action,)) + packets[nxt], depth + 1)

    for start in starts:
        visit(start, packets[start], 0)

    arms = []
    for depth in depths:
        summary = _summarize(groups[depth], packets, outcomes, viable_masks)
        summary.update({"history_steps": depth,
                        "history_payload_bytes": SensoryHistory(depth).payload_bytes,
                        "compatible_sets_sha256": digest([
                            [key.hex(), hex(value.states), value.prefixes]
                            for key, value in sorted(groups[depth].items())
                        ])})
        arms.append(summary)

    # Original instantaneous domain is separate from the matched comparison.
    original = {}
    for i, packet in enumerate(packets):
        group = original.setdefault(packet, _Group())
        group.states |= 1 << i
        group.prefixes += 1
    monotonic = all(
        all(later[f"prefixes_with_{kind}_ambiguity"] <= earlier[f"prefixes_with_{kind}_ambiguity"]
            for kind in ("observation", "terminal", "joint"))
        for earlier, later in zip(arms, arms[1:])
    )
    accounted = completed + sum(
        count * 3 ** (max_depth - depth) for depth, count in enumerate(ended)
    )
    report = {
        "schema": 1, "experiment": "E4-SENSATION-1-TEMPORAL-AUDIT",
        "scope": "exhaustive observability audit; not learned prediction or control",
        "initial_states": len(starts), "max_history_steps": max_depth,
        "initial_state_indices_sha256": digest(starts),
        "complete_surviving_prefixes": completed,
        "terminal_prefixes_by_depth": ended,
        "potential_action_strings": len(starts) * 3 ** max_depth,
        "accounted_action_strings": accounted,
        "same_population_in_all_arms": all(a["prefixes"] == completed for a in arms),
        "ambiguity_nonincreasing": monotonic,
        "original_full_domain": _summarize(original, packets, outcomes, viable_masks),
        "arms": arms,
        "runtime_input": "WSP packets and executed actions only",
        "runtime_connected_to_policy": False,
        "learned_prediction_evaluation": "not_run",
        "sensation_phase_closed": False,
        "boundary_acceptance": "not_run",
    }
    root = Path(__file__).resolve().parents[1]
    report["source_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("echo4/sensation.py", "echo4/sensation_audit.py",
                     "echo4/world.py", "echo4/viability.py", "echo4/audit.py",
                     "nexus0/encoder.py", "docs/ECHO4-SENSATION1-DESIGN.md")
    }
    report["report_sha256"] = digest(report)
    if accounted != report["potential_action_strings"] or not monotonic or not report["same_population_in_all_arms"]:
        raise RuntimeError("temporal audit accounting/refinement invariant failed")
    return report
