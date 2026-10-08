"""Private experiment executor/judge. Never imported by the consumer.

Restored arms share exact initial body, coupling and external schedule;
only the intended action differs. Body and schedules stay in audit traces.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from echoai.core.wsp import E_NAMES, unpack
from echoai.echo4.boundary import ALL, MASK, Estimate, Pair, Trial
from echoai.echo4.world import Body, DockRules, transition
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT
from echoai.nexus0.gate import gate

FAMILIES = ("full", "h_only", "temperature_only", "external_only", "mixed",
            "delayed", "veto", "missing_execution", "unmatched", "stale", "subband")
INVALID = frozenset(("veto", "missing_execution", "unmatched", "stale"))


def packet(body: Body) -> bytes:
    return encode_cell(0, KIND_OBJECT, vitality=body.h,
                       temperature=body.temperature, temperature_bands=8)


@dataclass(frozen=True)
class Experiment:
    initial: Body
    action: int
    h_coupled: bool = True
    temperature_coupled: bool = True
    heat: int = 0
    delay: int = 1
    veto: bool = False
    rules: DockRules = DockRules()


def experiment(family: str, action: int, stage: str, rng) -> Experiment:
    if family not in FAMILIES or stage not in ("development", "B", "C") or action not in (0, 1):
        raise ValueError("unknown experimental condition")
    index = ("development", "B", "C").index(stage)
    return Experiment(
        Body(29 + index if action == 0 else 35, 48 + 2 * index), action,
        h_coupled=family not in ("temperature_only", "external_only"),
        temperature_coupled=family not in ("h_only", "external_only", "subband"),
        heat=rng.choice((-16, 0, 16)) if family in ("external_only", "mixed") else 0,
        delay=2 if family == "delayed" else 1, veto=family == "veto",
        rules=DockRules(charge_input=1, cooling_cost=1) if family == "subband" else DockRules(),
    )


def run_pair(spec: Experiment, identifier: int, *, reverse: bool = False,
             fault: str = "", sensation=None):
    """Prediction precedes transition. Only public WSP/actions reach SENSATION."""
    arms, private, sensations = {}, {}, []
    for name in (("reference", "treatment") if reverse else ("treatment", "reference")):
        body = spec.initial  # explicit experimental restore, not policy rescue
        frames, states, actions, decisions = [packet(body)], [asdict(body)], [], []
        intended = spec.action if name == "treatment" else 2
        # Missing execution receipt must not secretly train either consumer.
        sensory = sensation if fault != "missing_execution" else None
        if sensory is not None:
            sensory.start(frames[0])
        for tick in (1, 2):
            if not body.alive:
                raise RuntimeError("terminal experiment has no full horizon")
            proposed = intended if tick == spec.delay else 2
            e = unpack(frames[-1])["E"]
            decision, applied, _ = gate(frames[-1], cam_hit=False, extract_ok=False,
                                        E=tuple(e[n] for n in E_NAMES), proposed=proposed,
                                        inhibit=spec.veto and name == "treatment" and tick == spec.delay)
            if sensory is not None:
                sensory.anticipate(applied)
            active, waiting = transition(body, applied, spec.rules), transition(body, 2, spec.rules)
            h = active.after.h if spec.h_coupled else waiting.after.h
            theta = active.after.temperature if spec.temperature_coupled else waiting.after.temperature
            theta = max(0, min(127, theta + (spec.heat if tick == 1 else 0)))
            body = Body(h, theta)
            frames.append(packet(body))
            states.append(asdict(body))
            actions.append(applied)
            decisions.append(decision)
            if sensory is not None:
                sensations.append(asdict(sensory.observe(frames[-1])))
        arms[name] = Trial(identifier, intended, tuple(frames), (0, 1, 2),
                           tuple(actions), tuple(decisions),
                           tuple(not Body(**state).alive for state in states))
        private[name] = states
    result = Pair(identifier, True, True, arms["treatment"], arms["reference"])
    if fault == "missing_execution":
        result = replace(result, treatment=replace(result.treatment, applied=(None, None)))
    elif fault == "unmatched":
        result = replace(result, restored=False)
    elif fault == "stale":
        result = replace(result, treatment=replace(result.treatment, ticks=(0, 0, 2)))
    return result, {"spec": asdict(spec), "reverse": reverse, "states": private}, sensations


def judge(family: str, private: dict) -> Estimate:
    """Independent expected labels from restored physical outcomes, not map logic.

    Report only effects visible through the frozen encoder. This deliberately
    does not declare physically uncoupled channels from zero band contrast.
    """
    if family in INVALID:
        return Estimate()
    states = private["states"]
    # Decode signed sensory coordinates independently of boundary.code.
    encoded = {name: [unpack(packet(Body(**s)))["E"] for s in seq]
               for name, seq in states.items()}
    influence, signs, lags = 0, [0, 0], [0, 0]
    for j, name in enumerate(("U", "B")):
        for tick in (1, 2):
            difference = encoded["treatment"][tick][name] - encoded["reference"][tick][name]
            if difference:
                influence |= 1 << (8 + j)
                signs[j] = 1 if difference > 0 else -1
                lags[j] = tick
                break
    return Estimate(influence, MASK ^ influence, ALL ^ MASK, tuple(signs), tuple(lags))


def coincidence(pair: Pair) -> int:
    """Baseline: temporal change after intention, ignoring the reference/gate."""
    return sum(1 << j for j in (8, 9)
               if any(frame[j] != pair.treatment.packets[0][j] for frame in pair.treatment.packets[1:]))
