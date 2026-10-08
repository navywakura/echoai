"""SELF-C: bounded public-observation belief and selective learning permission.

Known physics is inherited from SELF-B, not learned or read from the executor.
No physical registers, evaluator labels, environment or second T enter here.
"""
from echoai.echo4.boundary import code, integer
from echoai.echo4.self_attribution import (
    H_CODES, T_CODES, H_STEPS, T_STEPS, SelfAttributor, _packet,
)

MODES = ("selective", "no_protection", "no_attribution", "all_external", "all_self")
LIMIT = (1 << 31) - 1


class RecoveryStop(RuntimeError):
    """An experiment stop request, never an additional physical action."""


def advance(candidate, action, *, thermal, first, nominal=False):
    value, coupled = candidate[:2]
    table = T_STEPS if thermal else H_STEPS
    value = table[action if coupled or nominal else 2][value]
    if thermal and first:
        value = max(0, min(127, value + candidate[2]))
    return (value, *candidate[1:])


class RecoveryBelief:
    def __init__(self, diagnosis: SelfAttributor, *, restored: bool, same_context: bool,
                 mode="selective"):
        if type(diagnosis) is not SelfAttributor or diagnosis.pending is not None:
            raise ValueError("requires completed SELF-B diagnosis")
        if restored is not True or same_context is not True or mode not in MODES:
            raise ValueError("requires trusted restoration, context and valid mode")
        if diagnosis.diagnosis()["label"] == "unknown":
            raise ValueError("unknown diagnosis cannot authorize recovery")
        self.h = tuple(diagnosis.h_candidates)
        self.t = tuple(diagnosis.t_candidates)
        if not self.h or not self.t or len(self.h) > 64 or len(self.t) > 160:
            raise ValueError("invalid hypothesis budget")
        self.current = diagnosis.initial
        self.mode = mode
        self.steps = 0
        self.pending = None
        self.stopped = ""
        self.allowed = self.held = 0
        self.last = None

    def _check(self, packet):
        if self.stopped:
            raise RecoveryStop(self.stopped)
        _packet(packet, self.current)
        if packet != self.current:
            raise ValueError("stale observation")
        if self.steps >= LIMIT:
            raise RecoveryStop("step budget exhausted")

    def _decision_candidates(self, thermal):
        values = self.t if thermal else self.h
        if self.mode in ("selective", "no_protection"):
            return values
        coupled = self.mode != "all_self"
        if thermal:
            return tuple((v, coupled, heat if self.mode == "all_external" else 0)
                         for v, _, heat in values)
        return tuple((v, coupled) for v, _ in values)

    def choose(self, packet, q_row, proposed):
        self._check(packet)
        if self.pending is not None:
            raise RuntimeError("unconsumed forecast")
        integer(proposed, 0, 2)
        if len(q_row) != 3:
            raise ValueError("three Q values required")
        for value in q_row:
            integer(value, -127, 127)
        scores = []
        for action in range(3):
            hs = [advance(c, action, thermal=False, first=self.steps == 0)[0]
                  for c in self._decision_candidates(False)]
            ts = [advance(c, action, thermal=True, first=self.steps == 0)[0]
                  for c in self._decision_candidates(True)]
            margin = min(min(hs), min(ts), 127 - max(ts))
            if margin > 0:
                scores.append(((margin, q_row[action], action == proposed, action == 2, -action), action))
        if not scores:
            self.stopped = "no_safe_action"
            raise RecoveryStop(self.stopped)
        return max(scores)[1]

    def prepare(self, before, action, decision):
        self._check(before)
        integer(action, 0, 2)
        integer(decision, 0, 2)
        if self.pending is not None:
            raise RuntimeError("unconsumed forecast")
        forecasts = []
        for thermal, values in ((False, self.h), (True, self.t)):
            forecasts.append(tuple((advance(c, action, thermal=thermal, first=self.steps == 0),
                                    advance(c, action, thermal=thermal, first=self.steps == 0, nominal=True)[0])
                                   for c in values))
        self.pending = (before, action, decision, *forecasts)

    def observe(self, before, action, after):
        if self.pending is None:
            raise RuntimeError("observation requires a previous forecast")
        pending, self.pending = self.pending, None
        try:
            integer(action, 0, 2)
            _packet(before, self.current)
            _packet(after, before)
            if before != pending[0] or action != pending[1]:
                raise ValueError("execution mismatch")
        except ValueError:
            self.stopped = "invalid_execution"
            self.held = min(LIMIT, self.held + 1)
            self.last = {"allowed": False, "reason": self.stopped}
            return False
        survivors = []
        for channel, codes, forecasts in ((8, H_CODES, pending[3]), (9, T_CODES, pending[4])):
            survivors.append(tuple((c, nominal) for c, nominal in forecasts if codes[c[0]] == code(after, channel)))
        intact_equivalent = all(survivors) and all(
            codes[nominal] == code(after, channel)
            for channel, codes, values in ((8, H_CODES, survivors[0]), (9, T_CODES, survivors[1]))
            for _, nominal in values)
        self.h = tuple(sorted({c for c, _ in survivors[0]}))
        self.t = tuple(sorted({c for c, _ in survivors[1]}))
        self.current = after
        self.steps += 1
        if not all(survivors):
            self.stopped = "model_contradiction"
        elif pending[2] != 0:
            self.stopped = "gate_veto"
        allowed = not self.stopped and (intact_equivalent if self.mode == "selective" else self.mode != "all_self")
        self.allowed = min(LIMIT, self.allowed + allowed)
        self.held = min(LIMIT, self.held + (not allowed))
        self.last = {"allowed": bool(allowed), "reason": self.stopped or
                     ("nominal_body_equivalent" if intact_equivalent else "body_effect_or_ambiguity"),
                     "intact_equivalent": bool(intact_equivalent)}
        return bool(allowed)

    def resources(self):
        return {"h_candidates": len(self.h), "t_candidates": len(self.t),
                "h_capacity": 64, "t_capacity": 160, "retained_traces": 0,
                "pending_candidates": 0 if self.pending is None else len(self.pending[3]) + len(self.pending[4])}
