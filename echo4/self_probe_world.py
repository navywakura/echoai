"""Private supervised executor for longer probes; never imported by inference."""
from dataclasses import asdict

from echoai.core.wsp import E_NAMES, unpack
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_attribution import ProbePlan, ProbeTrace
from echoai.echo4.world import Body, DockRules, integer, transition
from echoai.nexus0.gate import gate


def run_probe(initial: Body, plan: ProbePlan, *, h_coupled=True, temperature_coupled=True,
              heat=0, veto_at=0, before_step=None):
    """Restore once, then genuine sequential actions. No actions after death."""
    if not isinstance(initial, Body) or not initial.alive or type(plan) is not ProbePlan:
        raise ValueError("requires live initial body and plan")
    integer(plan.token, 1, (1 << 31) - 1, "token")
    integer(heat, -127, 127, "heat")
    integer(veto_at, 0, 8, "veto_at")
    if type(h_coupled) is not bool or type(temperature_coupled) is not bool:
        raise ValueError("couplings must be boolean")
    if type(plan.actions) is not tuple or not 1 <= len(plan.actions) <= 8:
        raise ValueError("invalid plan horizon")
    for action in plan.actions:
        integer(action, 0, 2, "action")
    body, rules = initial, DockRules()
    frames, states, actions, gates, proposed = [packet(body)], [asdict(body)], [], [], []
    terminal = [False]
    for tick, action in enumerate(plan.actions, 1):
        if not body.alive:
            break
        if before_step is not None:
            before_step(tick, action)
        e = unpack(frames[-1])["E"]
        decision, applied, _ = gate(frames[-1], cam_hit=False, extract_ok=False,
                                    E=tuple(e[n] for n in E_NAMES), proposed=action,
                                    inhibit=tick == veto_at)
        active, waiting = transition(body, applied, rules), transition(body, 2, rules)
        h = active.after.h if h_coupled else waiting.after.h
        theta = active.after.temperature if temperature_coupled else waiting.after.temperature
        theta = max(0, min(127, theta + (heat if tick == 1 else 0)))
        body = Body(h, theta)
        frames.append(packet(body))
        states.append(asdict(body))
        proposed.append(action)
        actions.append(applied)
        gates.append(decision)
        terminal.append(not body.alive)
        if decision != 0:
            break  # fail closed for this probe; do not resume a vetoed plan
    receipt = ProbeTrace(plan.token, True, True, tuple(frames), tuple(proposed),
                         tuple(actions), tuple(gates), tuple(range(len(frames))), tuple(terminal))
    return receipt, {"initial": asdict(initial), "h_coupled": h_coupled,
                     "temperature_coupled": temperature_coupled, "heat": heat,
                     "states": states, "restores": 1}
