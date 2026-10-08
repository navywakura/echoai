"""WORLD-1: bounded integer physics, independent of the agent and auditor."""
from __future__ import annotations

from dataclasses import dataclass, fields

from echoai.nexus0.constants import (
    ACTION_APPROACH, ACTION_AVOID, ACTION_WAIT, N_ACTIONS, R_THREAT,
)

CAPACITY = 127
INITIAL_H = 32
INITIAL_TEMPERATURE = 64


def integer(value: int, low: int, high: int, name: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")


@dataclass(frozen=True)
class Body:
    h: int = INITIAL_H
    temperature: int = INITIAL_TEMPERATURE

    def __post_init__(self) -> None:
        integer(self.h, 0, CAPACITY, "h")
        integer(self.temperature, 0, CAPACITY, "temperature")

    @property
    def cause(self) -> str:
        # Same priority as HEAT-1b if more than one boundary is crossed.
        if self.temperature == CAPACITY:
            return "heat"
        if self.temperature == 0:
            return "cold"
        return "energy" if self.h == 0 else ""

    @property
    def alive(self) -> bool:
        return not self.cause


@dataclass(frozen=True)
class DockRules:
    """Abstract resources, not joules or Celsius. Source is external.

    Waiting dissipates resources and heats the body: it is not free cooling.
    Zero charge input is allowed as a negative control, not a second world.
    """

    charge_input: int = 5
    charge_heat: int = 16
    cooling_cost: int = 3
    cooling_drop: int = 16
    wait_cost: int = 1
    wait_heat: int = 4

    def __post_init__(self) -> None:
        for field in fields(self):
            low = 0 if field.name == "charge_input" else 1
            integer(getattr(self, field.name), low, CAPACITY, field.name)


@dataclass(frozen=True)
class Transition:
    before: Body
    action: int
    after: Body
    resource_in: int
    resource_used: int
    resource_spill: int

    @property
    def reward(self) -> int:
        # No charge, repair or survival bonus in this feasibility slice.
        return 0 if self.after.alive else R_THREAT

    @property
    def balanced(self) -> bool:
        return (self.before.h + self.resource_in
                == self.after.h + self.resource_used + self.resource_spill)


def transition(body: Body, action: int, rules: DockRules) -> Transition:
    """Pure transition. Reject malformed commands rather than folding modulo 3."""
    if not isinstance(body, Body) or not isinstance(rules, DockRules):
        raise ValueError("transition requires Body and DockRules")
    integer(action, 0, N_ACTIONS - 1, "action")
    if not body.alive:
        raise RuntimeError("terminal bodies cannot act")
    resource_in = used = spill = 0
    if action == ACTION_APPROACH:
        resource_in = rules.charge_input
        h = min(CAPACITY, body.h + resource_in)
        spill = body.h + resource_in - h
        temperature = min(CAPACITY, body.temperature + rules.charge_heat)
    elif action == ACTION_AVOID:
        used = min(body.h, rules.cooling_cost)
        h = body.h - used
        temperature = max(0, body.temperature - rules.cooling_drop)
    else:
        assert action == ACTION_WAIT
        used = min(body.h, rules.wait_cost)
        h = body.h - used
        temperature = min(CAPACITY, body.temperature + rules.wait_heat)
    return Transition(body, action, Body(h, temperature), resource_in, used, spill)


class DockWorld:
    """One owner of physical state; resets are explicit and counted."""

    def __init__(self, rules: DockRules = DockRules(), initial: Body = Body()):
        if not isinstance(rules, DockRules) or not isinstance(initial, Body):
            raise ValueError("world requires DockRules and Body")
        if not initial.alive:
            raise ValueError("initial body must be alive")
        self.rules = rules
        self.initial = initial
        self.body = initial
        self.resets = 0
        self.total_steps = 0
        self._clear_life()

    def _clear_life(self) -> None:
        self.life_steps = 0
        self.resource_in = 0
        self.resource_used = 0
        self.resource_spill = 0
        self.last_transition: Transition | None = None

    def reset(self) -> None:
        self.body = self.initial
        self.resets += 1
        self._clear_life()

    def advance(self, action: int) -> Transition:
        result = transition(self.body, action, self.rules)
        self.body = result.after
        self.last_transition = result
        self.life_steps += 1
        self.total_steps += 1
        self.resource_in += result.resource_in
        self.resource_used += result.resource_used
        self.resource_spill += result.resource_spill
        return result

    @property
    def balanced(self) -> bool:
        return (self.initial.h + self.resource_in
                == self.body.h + self.resource_used + self.resource_spill)
