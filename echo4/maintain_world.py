"""MAINT-A private physical fixture; original WORLD-1 transition is reused.

Faults and accounting receipts are experimental truth, never policy input.
Service is a costed sequence of the existing three actions, not a fourth gear.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from echoai.echo4.adapter import DockEnv
from echoai.echo4.world import Body, Transition, integer, transition
from echoai.nexus0.constants import ACTION_AVOID, ACTION_WAIT, R_SUCCESS

FAULTS = ("healthy", "clogged", "seized")
SERVICE_TICKS = 3
SERVICE_COST = 6
DEGRADED_DROP = 4
WORK_LOW, WORK_HIGH = 48, 80


@dataclass(frozen=True)
class ServiceReceipt:
    """Private physical accounting, not a new thought-bus packet."""

    tick: int
    fault_before: str
    fault_after: str
    progress_before: int
    progress_after: int
    spares_before: int
    spares_after: int
    service: str
    service_cost: int
    work: int


class MaintenanceEnv(DockEnv):
    def __init__(self, initial: Body = Body(), *, fault: str = "healthy",
                 spares: int = 1, external_heat: int = 0):
        if type(fault) is not str or fault not in FAULTS:
            raise ValueError("unknown maintenance fault")
        integer(spares, 0, 3, "spares")
        integer(external_heat, 0, 4, "external_heat")
        super().__init__(initial=initial)
        self._fault = fault
        self._spares = self._initial_spares = spares
        self._external_heat = external_heat
        self._progress = 0
        self._stopped = False
        self.service_attempts = self.services_paid = self.repairs = 0
        self.service_resource_used = self.work_done = 0
        self.last_service: ServiceReceipt | None = None

    def reset(self) -> None:
        raise RuntimeError("no reset or body restoration inside MAINTAIN")

    def stop(self) -> None:
        """Operator latch. Never restores the body, spares, clocks or memory."""
        self._stopped = True
        self._progress = 0

    @property
    def stopped(self) -> bool:
        return self._stopped

    def advance(self, action: int) -> Transition:
        integer(action, 0, 2, "action")
        if self._stopped:
            raise RuntimeError("MAINTAIN stopped by operator")
        # transition itself rejects terminal bodies before any mutation.
        effective = (self.rules if self._fault == "healthy" else
                     replace(self.rules, cooling_drop=DEGRADED_DROP))
        native = transition(self.body, action, effective)
        after = native.after
        if after.alive:
            after = Body(after.h, min(127, after.temperature + self._external_heat))

        old_fault, old_spares, old_progress = self._fault, self._spares, self._progress
        progress = self._progress + 1 if action == ACTION_AVOID else 0
        due = progress == SERVICE_TICKS
        service, cost = "none", 0
        if due:
            progress = 0
            self.service_attempts += 1
            if not after.alive:
                service = "terminal"
            elif not self._spares:
                service = "no_spare"
            elif after.h <= SERVICE_COST:
                service = "insufficient_energy"
            else:
                cost = SERVICE_COST
                after = Body(after.h - cost, after.temperature)
                self._spares -= 1
                self.services_paid += 1
                self.service_resource_used += cost
                if self._fault == "clogged":
                    self._fault = "healthy"
                    self.repairs += 1
                    service = "repaired"
                else:
                    service = "unnecessary" if self._fault == "healthy" else "ineffective"
        if not after.alive:
            progress = 0

        work = int(action == ACTION_WAIT and after.alive
                   and WORK_LOW <= after.temperature <= WORK_HIGH)
        result = Transition(native.before, action, after, native.resource_in,
                            native.resource_used + cost, native.resource_spill)
        self.body = after
        self._progress = progress
        self.last_transition = result
        self.life_steps += 1
        self.total_steps += 1
        self.resource_in += result.resource_in
        self.resource_used += result.resource_used
        self.resource_spill += result.resource_spill
        self.work_done += work
        self.last_service = ServiceReceipt(
            self.total_steps, old_fault, self._fault, old_progress, progress,
            old_spares, self._spares, service, cost, work,
        )
        return result

    def step_homeostatic(self, action: int, h: int, temperature: int):
        if Body(h, temperature) != self.body:
            raise ValueError("agent physiology disagrees with the world")
        result = self.advance(action)
        reward = result.reward if not self.body.alive else R_SUCCESS * self.last_service.work
        return reward, self.cell(), self.body.h, self.body.temperature

    @property
    def spares_balanced(self) -> bool:
        return self._initial_spares == self._spares + self.services_paid

    def audit_state(self) -> dict:
        """Private harness access, explicitly excluded from the agent readout."""
        return {
            "fault": self._fault, "spares": self._spares,
            "external_heat": self._external_heat, "progress": self._progress,
            "stopped": self._stopped, "steps": self.total_steps,
            "resets": self.resets, "service_attempts": self.service_attempts,
            "services_paid": self.services_paid, "repairs": self.repairs,
            "service_resource_used": self.service_resource_used,
            "work_done": self.work_done, "resource_in": self.resource_in,
            "resource_used": self.resource_used, "resource_spill": self.resource_spill,
            "balanced": self.balanced, "spares_balanced": self.spares_balanced,
        }
