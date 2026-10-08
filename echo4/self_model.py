"""SELF-A: observed change is not yet self/world attribution.

Only public WSP/BOUNDARY receipts enter here. The calibrated reference is
immutable during queries; ambiguous surprise is not spent on CAM/T/Q.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from echoai.echo4.boundary import ALL, MASK, BoundaryMap, Pair, code, validate


@dataclass(frozen=True)
class Reference:
    signature: tuple[int, ...]
    applied_at: int
    samples: int
    conflicting: bool


@dataclass(frozen=True)
class Change:
    reference_changed: int = 0
    action_effect_changed: int = 0
    known: int = 0
    unknown: int = ALL
    reason: str = "insufficient_reference"
    attribution: str = "unknown"


def signature(pair: Pair) -> tuple[int, tuple[int, ...]]:
    """Reference drift and difference-in-differences in signed U/B codes."""
    applied_at = validate(pair)
    initial = pair.treatment.packets[0]
    for arm in (pair.treatment, pair.reference):
        for packet in arm.packets:
            if any(not -100 <= code(packet, j) <= 100 for j in range(4, 10)):
                raise ValueError("invalid WSP E component")
            if any(packet[j] != initial[j] for j in range(16) if j not in (8, 9)):
                raise ValueError("unsupported semantic change outside U/B")
    drift, effect = [], []
    for tick in (1, 2):
        for channel in (8, 9):
            t, r = pair.treatment.packets, pair.reference.packets
            rd = code(r[tick], channel) - code(r[0], channel)
            td = code(t[tick], channel) - code(t[0], channel)
            drift.append(rd)
            effect.append(td - rd if tick >= applied_at else 0)
    return applied_at, tuple(drift + effect)


class SelfChangeMonitor:
    """At most 128 reference rows; not a second CAM or a physical-cause model.

    Calibration feeds the same BoundaryMap once. Its 4096-pair budget and
    monotonically increasing IDs bound support and reject duplicate evidence.
    Querying never teaches the model what it was about to predict.
    """

    def __init__(self, boundary: BoundaryMap):
        if not isinstance(boundary, BoundaryMap) or boundary.frozen:
            raise ValueError("requires an unfrozen existing BoundaryMap")
        self.boundary = boundary
        self.references: dict[tuple[int, int], Reference] = {}
        self.sealed = False

    def calibrate(self, pair: Pair) -> None:
        applied_at, values = signature(pair)  # all validation before mutation
        if self.sealed:
            raise RuntimeError("self reference is sealed")
        cam = self.boundary.cam
        key = (cam.get(pair.treatment.packets[0]), pair.treatment.intended)
        if key not in self.references and len(self.references) >= self.boundary.capacity:
            raise OverflowError("reference capacity exhausted")
        old = self.references.get(key)
        # Compute the complete immutable row before committing the observation.
        new = (Reference(values, applied_at, 1, False) if old is None else
               Reference(old.signature, old.applied_at, old.samples + 1,
                         old.conflicting or old.signature != values or old.applied_at != applied_at))
        self.boundary.observe(pair)  # existing API checks IDs/budget/CAM capacity
        key = (cam.get(pair.treatment.packets[0]), pair.treatment.intended)
        self.references[key] = new

    def seal(self) -> None:
        self.boundary.freeze()
        self.sealed = True

    def compare(self, pair: Pair) -> Change:
        """A single observation discrepancy, never a replicated physical cause.

        Invalid receipts return unknown and do not consume IDs or mutate a
        reference. No equality of WSP is treated as hidden-state identity.
        """
        if not self.sealed:
            raise RuntimeError("seal the nominal reference before comparison")
        try:
            applied_at, values = signature(pair)
        except ValueError:
            return Change(reason="invalid_or_unsupported_receipt")
        key = (self.boundary.cam.get(pair.treatment.packets[0]), pair.treatment.intended)
        reference = self.references.get(key)
        if reference is None or reference.samples < 8:
            return Change()
        if reference.conflicting:
            return Change(reason="conflicting_reference")
        if applied_at != reference.applied_at:
            return Change(reason="different_execution_timing")
        influence = self.boundary.estimate(pair.treatment.packets[0], pair.treatment.intended)
        if influence.unknown & MASK:
            return Change(reason="uncertain_boundary")
        drift = effect = 0
        for j, channel in enumerate((8, 9)):
            if any(values[i] != reference.signature[i] for i in (j, j + 2)):
                drift |= 1 << channel
            if any(values[i] != reference.signature[i] for i in (j + 4, j + 6)):
                effect |= 1 << channel
        return Change(drift, effect, MASK, ALL ^ MASK,
                      "observed_change" if drift or effect else "matches_reference")

    def model_hash(self) -> str:
        rows = [(key, row.signature, row.applied_at, row.samples, row.conflicting)
                for key, row in sorted(self.references.items())]
        data = {"rows": rows, "boundary": self.boundary.model_hash(), "sealed": self.sealed}
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def resources(self) -> dict:
        return {"rows": len(self.references), "capacity": self.boundary.capacity,
                "signature_integers": 8 * len(self.references),
                "signature_integer_capacity": 8 * self.boundary.capacity,
                "shared_cam": True, "retained_pairs": 0,
                "boundary": self.boundary.resources()}
