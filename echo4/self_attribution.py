"""SELF-B: finite, model-conditional diagnosis from public observations.

The pure WORLD-1 equations are a declared prior, NOT learned physics or
access to the executor. Actual body/coupling/heat never enter this API.
"""
from __future__ import annotations

from dataclasses import dataclass

from echoai.echo4.boundary import MASK, code, integer
from echoai.echo4.self_model import SelfChangeMonitor
from echoai.echo4.sensation import checked_packet
from echoai.echo4.world import Body, DockRules, transition
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT

HEAT_PRIOR = (-16, -4, 0, 4, 16)
CATALOG = ((2,) * 8, (1,) + (2,) * 7, (0, 2, 2, 2),
           (2, 2, 1, 2, 2, 2, 2, 2), (0, 1) * 4, (2,) * 4 + (0, 1) * 2)
LABELS = ("nominal", "own", "external", "mixed")


def _tables():
    """Finite constant prior, tabulated from original code instead of cloning it."""
    h_codes, t_codes = [], []
    for value in range(128):
        h_codes.append(code(encode_cell(0, KIND_OBJECT, vitality=value, temperature=64, temperature_bands=8), 8))
        t_codes.append(code(encode_cell(0, KIND_OBJECT, vitality=64, temperature=value, temperature_bands=8), 9))
    h_steps, t_steps = [], []
    for action in range(3):
        h_steps.append(tuple(transition(Body(v, 64), action, DockRules()).after.h if v else 0 for v in range(128)))
        t_steps.append(tuple(transition(Body(64, v), action, DockRules()).after.temperature if 0 < v < 127 else v
                             for v in range(128)))
    return tuple(h_codes), tuple(t_codes), tuple(h_steps), tuple(t_steps)


H_CODES, T_CODES, H_STEPS, T_STEPS = _tables()


@dataclass(frozen=True)
class ProbeTrace:
    token: int
    restored: bool
    same_context: bool
    packets: tuple[bytes, ...]
    proposed: tuple[int, ...]
    applied: tuple[int | None, ...]
    gates: tuple[int, ...]
    ticks: tuple[int, ...]
    terminal: tuple[bool, ...]


@dataclass(frozen=True)
class ProbePlan:
    token: int
    index: int
    actions: tuple[int, ...]
    worst_classes: int
    worst_states: int


def _packet(packet: bytes, initial: bytes):
    checked_packet(packet)
    if any(not -100 <= code(packet, j) <= 100 for j in range(4, 10)):
        raise ValueError("invalid WSP E range")
    if any(packet[j] != initial[j] for j in range(16) if j not in (8, 9)):
        raise ValueError("unsupported semantic context")


def validate_trace(trace: ProbeTrace, initial: bytes, actions: tuple[int, ...], token: int):
    if type(trace) is not ProbeTrace:
        raise ValueError("requires ProbeTrace")
    integer(trace.token, 1, (1 << 31) - 1)
    if trace.token != token or trace.restored is not True or trace.same_context is not True:
        raise ValueError("unmatched restoration/context receipt")
    n = len(actions)
    if not 1 <= n <= 8:
        raise ValueError("invalid horizon")
    for values, length in ((trace.packets, n + 1), (trace.proposed, n), (trace.applied, n),
                           (trace.gates, n), (trace.ticks, n + 1), (trace.terminal, n + 1)):
        if type(values) is not tuple or len(values) != length:
            raise ValueError("invalid receipt shape")
    for values in (trace.proposed, trace.applied, trace.gates):
        for value in values:
            integer(value, 0, 2)
    for tick in trace.ticks:
        integer(tick, 0, 8)
    if trace.proposed != actions or trace.applied != actions or any(trace.gates):
        raise ValueError("veto, modification or missing execution")
    if trace.ticks != tuple(range(n + 1)):
        raise ValueError("stale capture")
    if any(type(v) is not bool for v in trace.terminal) or any(trace.terminal):
        raise ValueError("terminal/invalid trial")
    for packet in trace.packets:
        _packet(packet, initial)
    if trace.packets[0] != initial:
        raise ValueError("initial observation mismatch")


def forecast(candidate, actions, *, thermal):
    """Return code trajectory or None if this hypothesis reaches terminality."""
    value, coupled = candidate[:2]
    heat = candidate[2] if thermal else 0
    table, codes = (T_STEPS, T_CODES) if thermal else (H_STEPS, H_CODES)
    result = []
    for tick, action in enumerate(actions):
        value = table[action if coupled else 2][value]
        if thermal and tick == 0:
            value = max(0, min(127, value + heat))
        if value == 0 or thermal and value == 127:
            return None
        result.append(codes[value])
    return tuple(result)


def _nominal_signature(value: int, action: int, thermal: bool):
    codes = T_CODES if thermal else H_CODES
    candidate = (value, True, 0) if thermal else (value, True)
    treatment = forecast(candidate, (action, 2), thermal=thermal)
    reference = forecast(candidate, (2, 2), thermal=thermal)
    if treatment is None or reference is None:
        return None
    return (reference[0] - codes[value], reference[1] - codes[value],
            treatment[0] - reference[0], treatment[1] - reference[1])


def possible_labels(h_candidates, t_candidates):
    h_modes = {c[1] for c in h_candidates}
    t_modes = {(c[1], c[2] != 0) for c in t_candidates}
    indices = {(not (hc and tc)) + 2 * external for hc in h_modes for tc, external in t_modes}
    return tuple(LABELS[i] for i in sorted(indices))


class SelfAttributor:
    """Read-only reference + bounded version space, no learned table writes.

    Candidate tuples contain hypothetical initial values, not body readings.
    Each new probe restores those hypothetical initials while retaining the
    exclusions established by previous probes. Factorization is a prior.
    """

    def __init__(self, reference: SelfChangeMonitor, initial: bytes, nominal: ProbeTrace | None):
        checked_packet(initial)
        _packet(initial, initial)
        if not isinstance(reference, SelfChangeMonitor) or not reference.sealed or not reference.boundary.frozen:
            raise ValueError("requires sealed SELF-A reference")
        slot = reference.boundary.cam.get(initial)
        rows = []
        for action in (0, 1):
            row = reference.references.get((slot, action))
            if (row is None or row.samples < 8 or row.conflicting or row.applied_at != 1
                    or reference.boundary.estimate(initial, action).unknown & MASK):
                raise ValueError("insufficient nominal reference")
            rows.append(row)
        if nominal is not None:
            if type(nominal) is not ProbeTrace:
                raise ValueError("requires a nominal probe receipt")
            validate_trace(nominal, initial, CATALOG[0], nominal.token)
        factors = []
        for thermal, channel in ((False, 8), (True, 9)):
            codes = T_CODES if thermal else H_CODES
            offset = 1 if thermal else 0
            values = []
            for value in range(1, 127 if thermal else 128):
                if codes[value] != code(initial, channel):
                    continue
                if any(_nominal_signature(value, action, thermal)
                       != tuple(row.signature[i] for i in (offset, offset + 2, offset + 4, offset + 6))
                       for action, row in enumerate(rows)):
                    continue
                candidate = (value, True, 0) if thermal else (value, True)
                if nominal is not None and forecast(candidate, CATALOG[0], thermal=thermal) != tuple(code(p, channel) for p in nominal.packets[1:]):
                    continue
                values.append(value)
            factors.append(values)
        self.initial = initial
        self.h_candidates = tuple((v, c) for v in factors[0] for c in (True, False))
        self.t_candidates = tuple((v, c, heat) for v in factors[1] for c in (True, False) for heat in HEAT_PRIOR)
        if len(self.h_candidates) > 64 or len(self.t_candidates) > 160:
            raise RuntimeError("factor budget violated")
        self.used: set[int] = set()
        self.last_token = nominal.token if nominal is not None else 0
        self.pending = None
        self.executed_ticks = 0
        self.invalid_reason = "" if self.h_candidates and self.t_candidates else "nominal_model_mismatch"

    def diagnosis(self) -> dict:
        labels = possible_labels(self.h_candidates, self.t_candidates) if not self.invalid_reason else ()
        return {"label": labels[0] if len(labels) == 1 else "unknown", "possible": labels,
                "reason": self.invalid_reason or ("unanimous_in_prior" if len(labels) == 1 else "ambiguous"),
                "h_candidates": len(self.h_candidates), "t_candidates": len(self.t_candidates),
                "probes": len(self.used), "executed_ticks": self.executed_ticks}

    def _prediction(self, index):
        actions = CATALOG[index]
        h = tuple((c, forecast(c, actions, thermal=False)) for c in self.h_candidates)
        t = tuple((c, forecast(c, actions, thermal=True)) for c in self.t_candidates)
        if any(f is None for _, f in h + t):
            return None
        h_groups, t_groups = {}, {}
        for candidate, seq in h:
            h_groups.setdefault(seq, []).append(candidate)
        for candidate, seq in t:
            t_groups.setdefault(seq, []).append(candidate)
        worst_classes = worst_states = 0
        for hs in h_groups.values():
            for ts in t_groups.values():
                worst_classes = max(worst_classes, len(possible_labels(hs, ts)))
                worst_states = max(worst_states, len(hs) * len(ts))
        return (worst_classes, worst_states, len(actions), index), h, t

    def choose(self, token: int, *, mode="active") -> ProbePlan | None:
        integer(token, 1, (1 << 31) - 1)
        if mode not in ("active", "fixed", "wait_only"):
            raise ValueError("unknown diagnostic selector")
        if self.pending is not None:
            raise RuntimeError("consume the pending probe first")
        if token <= self.last_token:
            raise ValueError("non-increasing probe token")
        if self.invalid_reason or self.diagnosis()["label"] != "unknown" or len(self.used) >= len(CATALOG):
            return None
        predictions = []
        for index in range(1 if mode == "wait_only" else len(CATALOG)):
            if index in self.used:
                continue
            prediction = self._prediction(index)
            if prediction is not None:
                predictions.append(prediction)
                if mode != "active":
                    break
        if not predictions:
            return None
        score, hs, ts = min(predictions, key=lambda p: p[0])
        plan = ProbePlan(token, score[3], CATALOG[score[3]], score[0], score[1])
        self.pending = (plan, hs, ts)  # full forecasts recorded BEFORE execution
        self.used.add(plan.index)
        self.last_token = token
        return plan

    def consume(self, trace: ProbeTrace) -> dict:
        if self.pending is None:
            raise RuntimeError("no pending probe")
        plan, hs, ts = self.pending
        try:
            validate_trace(trace, self.initial, plan.actions, plan.token)
        except ValueError:
            self.invalid_reason = "invalid_execution_receipt"
            self.pending = None
            return self.diagnosis()
        h_seen = tuple(code(p, 8) for p in trace.packets[1:])
        t_seen = tuple(code(p, 9) for p in trace.packets[1:])
        self.h_candidates = tuple(c for c, predicted in hs if predicted == h_seen)
        self.t_candidates = tuple(c for c, predicted in ts if predicted == t_seen)
        self.executed_ticks += len(plan.actions)
        self.pending = None
        if not self.h_candidates or not self.t_candidates:
            self.invalid_reason = "model_contradiction"
        return self.diagnosis()

    def resources(self):
        return {"h_candidates": len(self.h_candidates), "h_capacity": 64,
                "t_candidates": len(self.t_candidates), "t_capacity": 160,
                "pending_forecast_codes": 0 if self.pending is None else
                len(self.pending[0].actions) * (len(self.pending[1]) + len(self.pending[2])),
                "pending_code_capacity": 8 * (64 + 160), "probe_capacity": len(CATALOG),
                "used_probes": len(self.used), "retained_traces": 0}
