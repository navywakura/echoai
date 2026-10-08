"""Full-state feasibility oracle. Never imported by the ECHO decision path.

Remove states with no surviving successor; reverse edges make this O(S*A).
This certifies the declared finite dynamics, not partial-observation learning.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from echoai.nexus0.constants import N_ACTIONS
from echoai.echo4.world import Body, CAPACITY, DockRules, transition

TEMPERATURE_STATES = CAPACITY - 1
STATE_COUNT = CAPACITY * TEMPERATURE_STATES


def state_index(body: Body) -> int:
    if not isinstance(body, Body) or not body.alive:
        raise ValueError("only living Body states have a graph index")
    return (body.h - 1) * TEMPERATURE_STATES + body.temperature - 1


def indexed_body(index: int) -> Body:
    if type(index) is not int or not 0 <= index < STATE_COUNT:
        raise ValueError("invalid state index")
    return Body(index // TEMPERATURE_STATES + 1,
                index % TEMPERATURE_STATES + 1)


@dataclass(frozen=True)
class Witness:
    """states[k] --actions[k]--> states[k+1]; last closes cycle_start."""

    states: tuple[Body, ...]
    actions: tuple[int, ...]
    cycle_start: int

    @property
    def prefix_length(self) -> int:
        return self.cycle_start

    @property
    def cycle_length(self) -> int:
        return len(self.actions) - self.cycle_start

    def valid(self, rules: DockRules) -> bool:
        if (type(self.cycle_start) is not int
                or not self.actions
                or len(self.states) != len(self.actions) + 1
                or not 0 <= self.cycle_start < len(self.actions)):
            return False
        try:
            if (not all(state.alive for state in self.states)
                    or self.states[-1] != self.states[self.cycle_start]):
                return False
            for before, action, after in zip(
                    self.states, self.actions, self.states[1:]):
                step = transition(before, action, rules)
                if step.after != after or not step.balanced:
                    return False
        except (AttributeError, TypeError, ValueError, RuntimeError):
            return False
        return True


@dataclass(frozen=True)
class Viability:
    rules: DockRules
    successors: tuple[tuple[int, ...], ...]
    kernel: tuple[bool, ...]
    # 0 inside infinite-horizon kernel; otherwise actions including terminal.
    finite_lifetime: tuple[int, ...]

    def contains(self, body: Body) -> bool:
        return self.kernel[state_index(body)]

    def safe_actions(self, body: Body) -> tuple[int, ...]:
        return tuple(a for a, nxt in enumerate(self.successors[state_index(body)])
                     if nxt >= 0 and self.kernel[nxt])

    def max_steps(self, body: Body) -> int | None:
        index = state_index(body)
        return None if self.kernel[index] else self.finite_lifetime[index]

    def witness(self, initial: Body) -> Witness | None:
        if not self.contains(initial):
            return None
        states = [initial]
        actions: list[int] = []
        seen: dict[Body, int] = {}
        body = initial
        while body not in seen:
            seen[body] = len(actions)
            action = self.safe_actions(body)[0]
            body = indexed_body(self.successors[state_index(body)][action])
            actions.append(action)
            states.append(body)
        result = Witness(tuple(states), tuple(actions), seen[body])
        if not result.valid(self.rules):
            raise RuntimeError("invalid feasibility witness")
        return result


def analyze(rules: DockRules = DockRules()) -> Viability:
    if not isinstance(rules, DockRules):
        raise ValueError("analyze requires DockRules")
    successors: list[tuple[int, ...]] = []
    predecessors: list[list[int]] = [[] for _ in range(STATE_COUNT)]
    degree: list[int] = []
    for index in range(STATE_COUNT):
        body = indexed_body(index)
        row = []
        for action in range(N_ACTIONS):
            step = transition(body, action, rules)
            if not step.balanced:
                raise RuntimeError("resource balance violated")
            nxt = state_index(step.after) if step.after.alive else -1
            row.append(nxt)
            if nxt >= 0:
                # Keep duplicate edges: degree also counts actions, not nodes.
                predecessors[nxt].append(index)
        successors.append(tuple(row))
        degree.append(sum(nxt >= 0 for nxt in row))

    pending = deque(i for i, count in enumerate(degree) if count == 0)
    kernel = [True] * STATE_COUNT
    finite_lifetime = [0] * STATE_COUNT
    while pending:
        index = pending.popleft()
        kernel[index] = False
        finite_lifetime[index] = max(
            1 if nxt < 0 else 1 + finite_lifetime[nxt]
            for nxt in successors[index])
        for parent in predecessors[index]:
            degree[parent] -= 1
            if degree[parent] == 0:
                pending.append(parent)
    return Viability(rules, tuple(successors), tuple(kernel), tuple(finite_lifetime))
