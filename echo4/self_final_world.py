"""Private falsification mechanisms. Never imported by SelfSession/readout."""
from dataclasses import asdict

from echoai.core.wsp import E_NAMES, unpack
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_attribution import ProbePlan, ProbeTrace
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.world import Body, DockRules, integer, transition
from echoai.nexus0.gate import gate

MECHANISMS = ("persistent_heat", "delayed_heat", "reversed_cooling", "external_mimic")


def novel_probe(initial, plan, mechanism):
    """Same WSP/actions/gate; altered dynamics exist only in the evaluator."""
    if mechanism not in MECHANISMS or type(plan) is not ProbePlan or not isinstance(initial, Body):
        raise ValueError("unknown physical falsification trial")
    if not initial.alive or type(plan.actions) is not tuple or not 1 <= len(plan.actions) <= 8:
        raise ValueError("invalid physical trial")
    for action in plan.actions:
        integer(action, 0, 2, "action")
    body, rules = initial, DockRules()
    frames, states, applied, gates, proposed = [packet(body)], [asdict(body)], [], [], []
    terminal, ledgers = [False], []
    for tick, action in enumerate(plan.actions, 1):
        if not body.alive:
            break
        e = unpack(frames[-1])["E"]
        decision, actual, _ = gate(frames[-1], cam_hit=False, extract_ok=False,
                                   E=tuple(e[n] for n in E_NAMES), proposed=action)
        result = transition(body, actual, rules)
        after_h, after_t = result.after.h, result.after.temperature
        external_resource = 0
        if mechanism == "persistent_heat":
            after_t += 2
        elif mechanism == "delayed_heat" and tick == 3:
            after_t += 16
        elif mechanism == "reversed_cooling" and actual == 1:
            after_t = body.temperature + 12
        elif mechanism == "external_mimic":
            # Intact actuator + an action-dependent force cancelling its net
            # effect. Explicit signed external resource flow, not free energy.
            waiting = transition(body, 2, rules)
            external_resource = waiting.after.h - after_h
            after_h, after_t = waiting.after.h, waiting.after.temperature
        balanced = (body.h + result.resource_in + external_resource
                    == after_h + result.resource_used + result.resource_spill)
        ledgers.append({"balanced": balanced, "in": result.resource_in,
                        "used": result.resource_used, "spill": result.resource_spill,
                        "external_signed": external_resource})
        body = Body(after_h, max(0, min(127, after_t)))
        frames.append(packet(body))
        states.append(asdict(body))
        applied.append(actual)
        gates.append(decision)
        proposed.append(action)
        terminal.append(not body.alive)
        if decision:
            break
    receipt = ProbeTrace(plan.token, True, True, tuple(frames), tuple(proposed),
                         tuple(applied), tuple(gates), tuple(range(len(frames))), tuple(terminal))
    return receipt, {"initial": asdict(initial), "mechanism": mechanism, "states": states,
                     "restores": 1, "resource_ledger": ledgers}
