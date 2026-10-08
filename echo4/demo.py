"""Bounded single-life integration smoke; learning stays on, never a certificate."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from echoai.nexus0.constants import N_SLOTS
from echoai.echo4.adapter import new_agent
from echoai.echo4.world import Body, DockRules, integer

MAX_TURNS = 10_000


def run_demo(turns: int = 256, *, greedy: bool = False,
             include_trace: bool = False, rules: DockRules = DockRules(),
             initial: Body = Body()) -> dict:
    integer(turns, 1, MAX_TURNS, "turns")
    if type(greedy) is not bool or type(include_trace) is not bool:
        raise ValueError("greedy and include_trace must be bool")
    agent = new_agent(rules, initial)
    world = agent.env
    trace = []
    for turn in range(turns):
        if agent.episode_terminal:
            break
        # Fail closed before the historical allocator's full-pool fallback.
        # This tiny vocabulary cannot exhaust a fresh CAM in this run.
        if agent.cam.used > N_SLOTS - 2:
            raise RuntimeError("CAM capacity guard: insufficient headroom")
        packet = agent.observation(world.cell())
        action = agent.turn(turn, greedy=greedy)
        step = world.last_transition
        if step is None or action != step.action or not world.balanced:
            raise RuntimeError("agent/world transition mismatch")
        if (agent.H, agent.temperature) != (world.body.h, world.body.temperature):
            raise RuntimeError("agent/world physiology mismatch")
        trace.append({
            "turn": turn,
            "wsp_before": packet.hex(),
            "wsp_after": agent.observation(world.cell()).hex(),
            "proposed_action": agent.last_proposed_action,
            "executed_action": action,
            "gate_decision": agent.last_gate_decision,
            "before": asdict(step.before),
            "after": asdict(step.after),
            "resource_in": step.resource_in,
            "resource_used": step.resource_used,
            "resource_spill": step.resource_spill,
            "reward": step.reward,
            "terminal": not step.after.alive,
            "cause": step.after.cause,
        })
    metrics = agent.metrics
    report = {
        "schema": 1,
        "experiment": "ECHO4-WORLD1",
        "mode": "single_life_online_learning",
        "greedy": greedy,
        "learning_frozen": False,
        "rules": asdict(rules),
        "initial": asdict(initial),
        "requested_turns": turns,
        "executed_turns": world.life_steps,
        "terminal": agent.episode_terminal,
        "stop_reason": world.body.cause or "horizon",
        "final": asdict(world.body),
        "resets": world.resets,
        "deaths": agent.deaths,
        "resource_in": world.resource_in,
        "resource_used": world.resource_used,
        "resource_spill": world.resource_spill,
        "resource_balance_ok": world.balanced,
        "cam_used": agent.cam.used,
        "destroyed": agent.cam.destroyed,
        "false_facts": metrics.false_facts,
        "cortex_calls": metrics.cortex_calls,
        "q_nonzero": sum(value != 0 for row in agent.q.q for value in row),
        "trace_sha256": hashlib.sha256(json.dumps(
            trace, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest(),
        "maintenance_acceptance": "not_run",
    }
    if include_trace:
        report["trace"] = trace
    return report
