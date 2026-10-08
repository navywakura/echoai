"""PATTERN-1: invariant families from binary perception and consequences.

This is the software-side experiment before a camera, a 3-D renderer or an
Akida front-end exists.  The learner receives only a 16-bit perceptual
signature.  Object ids, positions, views, contexts and human category names
exist in the harness so the exam can be scored, but none of them cross the
learner API.

During school a physical consequence is available.  Nearby signatures are
allowed to join a family only when that consequence is compatible.  During
the frozen exam ``predict(signature)`` receives no consequence: it returns an
anonymous family P0, P1, ... and that family's learned outcome.  This is a
small bridge from exact PATTERN-0 contexts to future event-camera/spike
features; it does not claim visual object recognition.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SIGNATURE_BITS = 16
SIGNATURE_MASK = (1 << SIGNATURE_BITS) - 1
FAMILY_CAPACITY = 64
MAX_HAMMING = 3
MIN_HITS = 4
EMPTY_OUTCOME = 128              # outside the signed int8 consequence band
SATURATE = 65535


def hamming16(a: int, b: int) -> int:
    return ((int(a) ^ int(b)) & SIGNATURE_MASK).bit_count()


class InvariantPatternMemory:
    """Fixed-capacity integer families over 16-bit signatures.

    ``observe`` is the complete learning boundary.  ``predict`` deliberately
    has one argument, so an exam cannot leak object identity, pose, context or
    the answer into recognition.
    """

    def __init__(self, capacity: int = FAMILY_CAPACITY,
                 max_hamming: int = MAX_HAMMING,
                 min_hits: int = MIN_HITS) -> None:
        if type(capacity) is not int or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if type(max_hamming) is not int or not 0 <= max_hamming <= SIGNATURE_BITS:
            raise ValueError("max_hamming must be in 0..16")
        if type(min_hits) is not int or min_hits <= 0:
            raise ValueError("min_hits must be a positive integer")
        self.capacity = capacity
        self.max_hamming = max_hamming
        self.min_hits = min_hits
        self.prototype: List[int] = [0] * capacity
        self.outcome: List[int] = [EMPTY_OUTCOME] * capacity
        self.hits: List[int] = [0] * capacity
        # Fixed 64 x 16 integer counters.  They let the prototype follow the
        # majority of observed bits without floats or unbounded samples.
        self.ones: List[List[int]] = [
            [0] * SIGNATURE_BITS for _ in range(capacity)
        ]
        self.size = 0
        self.observations = 0
        self.dropped = 0
        self.incompatible_near = 0

    @staticmethod
    def _signature(value: int) -> int:
        if type(value) is not int or not 0 <= value <= SIGNATURE_MASK:
            raise ValueError("signature must be an integer in 0..65535")
        return value

    @staticmethod
    def _outcome(value: int) -> int:
        if type(value) is not int or not -127 <= value <= 127:
            raise ValueError("outcome must be an integer in -127..127")
        return value

    def _nearest(self, signature: int, *, outcome: Optional[int] = None,
                 mature: bool = False) -> Tuple[int, int, bool]:
        best = -1
        best_d = SIGNATURE_BITS + 1
        tied = False
        for i in range(self.size):
            if outcome is not None and self.outcome[i] != outcome:
                continue
            if mature and self.hits[i] < self.min_hits:
                continue
            d = hamming16(signature, self.prototype[i])
            if d < best_d:
                best, best_d, tied = i, d, False
            elif d == best_d:
                tied = True
        return best, best_d, tied

    def _update_prototype(self, family: int, signature: int) -> None:
        count = self.hits[family]
        proto = self.prototype[family]
        for bit in range(SIGNATURE_BITS):
            if signature & (1 << bit) and self.ones[family][bit] < SATURATE:
                self.ones[family][bit] += 1
            ones = self.ones[family][bit]
            # A tie keeps the previous bit.  The first observation is thus
            # stable while repeated evidence can still move the prototype.
            if ones * 2 > count:
                proto |= 1 << bit
            elif ones * 2 < count:
                proto &= ~(1 << bit)
        self.prototype[family] = proto & SIGNATURE_MASK

    def observe(self, signature: int, outcome: int) -> Optional[int]:
        signature = self._signature(signature)
        outcome = self._outcome(outcome)
        self.observations += 1

        family, distance, tied = self._nearest(signature, outcome=outcome)
        if family >= 0 and distance <= self.max_hamming and not tied:
            if self.hits[family] < SATURATE:
                self.hits[family] += 1
            self._update_prototype(family, signature)
            return family

        # Count nearby but dynamically incompatible evidence.  It becomes a
        # separate family; visual similarity alone may not erase consequence.
        near, near_d, _ = self._nearest(signature)
        if near >= 0 and near_d <= self.max_hamming:
            self.incompatible_near += 1

        if self.size >= self.capacity:
            self.dropped += 1
            return None
        family = self.size
        self.size += 1
        self.prototype[family] = signature
        self.outcome[family] = outcome
        self.hits[family] = 1
        for bit in range(SIGNATURE_BITS):
            self.ones[family][bit] = int(bool(signature & (1 << bit)))
        return family

    def predict(self, signature: int) -> Optional[Tuple[int, int, int]]:
        """Return ``(family, learned_outcome, distance)`` or ``None``.

        Recognition is refused on equal-distance ambiguity.  This method is
        read-only and has no access to the physical consequence.
        """
        signature = self._signature(signature)
        family, distance, tied = self._nearest(signature, mature=True)
        if family < 0 or distance > self.max_hamming or tied:
            return None
        return family, self.outcome[family], distance

    def snapshot_hash(self) -> str:
        h = hashlib.sha256()
        for value in (self.capacity, self.max_hamming, self.min_hits,
                      self.size, self.observations, self.dropped,
                      self.incompatible_near):
            h.update(int(value).to_bytes(8, "little", signed=True))
        for i in range(self.capacity):
            for value in (self.prototype[i], self.outcome[i], self.hits[i]):
                h.update(int(value).to_bytes(8, "little", signed=True))
            for value in self.ones[i]:
                h.update(int(value).to_bytes(8, "little", signed=True))
        return h.hexdigest()


# Synthetic sensor families.  Names and object ids are scoring metadata only.
# The fourth family is deliberately only three bits from ``resource`` but has
# the opposite consequence: it catches a learner that equates Hamming-near
# with functionally equivalent.
CATEGORIES: Tuple[Tuple[str, int, int], ...] = (
    ("resource", 0xF0C3, 16),
    ("hazard", 0x0FCC, -16),
    ("neutral", 0x113F, 0),
    ("mimic_hazard", 0xF0C3 ^ 0x400C, -16),
)
TRAIN_OBJECT_MASKS = (0, 1 << 12)
EXAM_OBJECT_MASKS = (1 << 1,)
TRAIN_VIEWS = (0, 1 << 4, 1 << 6)
EXAM_VIEWS = (1 << 5, 1 << 7)
TRAIN_CONTEXTS = (0, 1 << 8)
EXAM_CONTEXTS = (1 << 9, 1 << 11)
TRAIN_POSITIONS = (3, 27, 61)
EXAM_POSITIONS = (109, 233)


def signature_of(base: int, object_mask: int, view_mask: int,
                 context_mask: int) -> int:
    """Synthetic front-end output.  Position and object id are absent."""
    return (int(base) ^ int(object_mask) ^ int(view_mask)
            ^ int(context_mask)) & SIGNATURE_MASK


def _rows(train: bool) -> List[dict]:
    object_masks = TRAIN_OBJECT_MASKS if train else EXAM_OBJECT_MASKS
    views = TRAIN_VIEWS if train else EXAM_VIEWS
    contexts = TRAIN_CONTEXTS if train else EXAM_CONTEXTS
    positions = TRAIN_POSITIONS if train else EXAM_POSITIONS
    rows: List[dict] = []
    for category, base, outcome in CATEGORIES:
        for object_number, object_mask in enumerate(object_masks):
            object_id = f"{category}-{object_number + (0 if train else 100)}"
            for view_number, view_mask in enumerate(views):
                for context_number, context_mask in enumerate(contexts):
                    for position in positions:
                        rows.append({
                            "category": category,
                            "object_id": object_id,
                            "position": position,
                            "view": view_number,
                            "context": context_number,
                            "signature": signature_of(
                                base, object_mask, view_mask, context_mask),
                            "outcome": outcome,
                        })
    return rows


def experiment() -> dict:
    memory = InvariantPatternMemory()
    train = _rows(True)
    category_family: Dict[str, int] = {}
    for row in train:
        family = memory.observe(row["signature"], row["outcome"])
        if family is not None:
            category_family.setdefault(row["category"], family)

    exact: Dict[int, int] = {}
    for row in train:
        exact.setdefault(row["signature"], row["outcome"])

    before_hash = memory.snapshot_hash()
    before_observations = memory.observations
    exam: List[dict] = []
    for row in _rows(False):
        prediction = memory.predict(row["signature"])
        family = None if prediction is None else prediction[0]
        predicted_outcome = None if prediction is None else prediction[1]
        distance = None if prediction is None else prediction[2]
        exam.append(dict(
            **row,
            family=family,
            predicted_outcome=predicted_outcome,
            distance=distance,
            expected_family=category_family.get(row["category"]),
            exact_outcome=exact.get(row["signature"]),
        ))

    outcome_hits = sum(r["predicted_outcome"] == r["outcome"] for r in exam)
    family_hits = sum(r["family"] == r["expected_family"] for r in exam)
    exact_hits = sum(r["exact_outcome"] == r["outcome"] for r in exam)
    recognized = sum(r["family"] is not None for r in exam)
    resource_family = category_family.get("resource")
    mimic_family = category_family.get("mimic_hazard")
    return {
        "slice": "PATTERN-1",
        "representation": "binary16",
        "capacity": memory.capacity,
        "max_hamming": memory.max_hamming,
        "min_hits": memory.min_hits,
        "train_samples": len(train),
        "exam_samples": len(exam),
        "families": memory.size,
        "category_family": category_family,
        "recognized": recognized,
        "outcome_hits": outcome_hits,
        "family_hits": family_hits,
        "exact_hits": exact_hits,
        "gain_over_exact": outcome_hits - exact_hits,
        "incompatible_near": memory.incompatible_near,
        "incompatible_split": resource_family is not None
                              and mimic_family is not None
                              and resource_family != mimic_family,
        "dropped": memory.dropped,
        "observations_before_exam": before_observations,
        "observations_after_exam": memory.observations,
        "hash_before_exam": before_hash,
        "hash_after_exam": memory.snapshot_hash(),
        "learner_inputs": ["signature", "outcome_during_school"],
        "exam_inputs": ["signature"],
        "object_id_used_by_learner": False,
        "position_used_by_learner": False,
        "context_used_by_learner": False,
        "cortex_calls": 0,
        "destroyed": 0,
        "exam": exam,
    }


def green(report: dict) -> bool:
    """Fail closed and recompute every headline count from exam rows."""
    try:
        if (report["slice"], report["representation"], report["capacity"],
                report["max_hamming"], report["min_hits"]) != (
                    "PATTERN-1", "binary16", FAMILY_CAPACITY,
                    MAX_HAMMING, MIN_HITS):
            return False
        if report["learner_inputs"] != ["signature", "outcome_during_school"]:
            return False
        if report["exam_inputs"] != ["signature"]:
            return False
        if any(report[k] is not False for k in (
                "object_id_used_by_learner", "position_used_by_learner",
                "context_used_by_learner")):
            return False
        if report["cortex_calls"] != 0 or report["destroyed"] != 0:
            return False
        exam = report["exam"]
        if not isinstance(exam, list) or len(exam) != report["exam_samples"]:
            return False
        if report["train_samples"] != len(_rows(True)) or len(exam) != len(_rows(False)):
            return False
        recognized = sum(r["family"] is not None for r in exam)
        outcome_hits = sum(r["predicted_outcome"] == r["outcome"] for r in exam)
        family_hits = sum(r["family"] == r["expected_family"] for r in exam)
        exact_hits = sum(r["exact_outcome"] == r["outcome"] for r in exam)
        if (recognized, outcome_hits, family_hits, exact_hits) != (
                report["recognized"], report["outcome_hits"],
                report["family_hits"], report["exact_hits"]):
            return False
        if report["gain_over_exact"] != outcome_hits - exact_hits:
            return False
        if outcome_hits != len(exam) or family_hits != len(exam):
            return False
        if outcome_hits <= exact_hits or report["gain_over_exact"] <= 0:
            return False
        if report["families"] != len(CATEGORIES) or report["dropped"] != 0:
            return False
        if report["incompatible_near"] <= 0 or report["incompatible_split"] is not True:
            return False
        if len(set(report["category_family"].values())) != len(CATEGORIES):
            return False
        if report["observations_before_exam"] != report["observations_after_exam"]:
            return False
        if report["hash_before_exam"] != report["hash_after_exam"]:
            return False
        # Every evaluated object is unseen, in held-out positions, views and
        # contexts; the exact-signature baseline must therefore know none.
        if any(r["object_id"].split("-")[-1] != "100" for r in exam):
            return False
        if {r["position"] for r in exam} != set(EXAM_POSITIONS):
            return False
        if any(r["distance"] is None or not 0 <= r["distance"] <= MAX_HAMMING
               for r in exam):
            return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def main(argv=None) -> int:
    report = experiment()
    report["green"] = green(report)
    path = Path(__file__).resolve().parents[1] / "lab" / "echo2_pattern1_report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["green"] else 1


if __name__ == "__main__":
    sys.exit(main())
