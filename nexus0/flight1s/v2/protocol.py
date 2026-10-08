"""The v2 protocol: load, calibrate, freeze.

The rules that decide the calibrated numbers are written here, before the
calibration runs, so that choosing them is mechanical:

* ``recovery.radius_mm`` = ``max(v1's 200, ceil(the nominal horizontal
  envelope measured on A-v2, 50))``. Never smaller than v1's, so v2
  cannot be a quieter band wearing a new name.
* ``challenge.exit_margin_mm`` comes from measurement resolution alone —
  how far the body can travel between two samples at the declared rate,
  plus the standard error of the hover reference — and never from an
  observed minimum.
* ``stimulus.min_impulse_ratio_ppk`` = ``max(500, mean + 6 sigma of the
  negative controls, rounded up to 10)``. The floor can only move away
  from the controls, never toward them.
* ``stimulus.max_impulse_ratio_ppk`` = 1500, fixed: a symmetric bound
  that catches a unit error, an accumulated wrench or a wrong window.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    loads_strict,
    read_bounded,
    sha256_bytes,
)
from echoai.nexus0.sim3.pkg import _validate_schema
from echoai.nexus0.flight1s.runtime import ECHOAI, PX4_COMMIT, PX4_MODELS_COMMIT
from echoai.nexus0.flight1s.v2 import (
    V1_PROTOCOL_SHA256,
    V1_REPORT_SHA256,
)

SCHEMA = (ECHOAI / "docs" / "schemas" / "flight1s-v2"
          / "flight1s-protocol-v2.schema.json")
DEFAULT_PATH = ECHOAI / "docs" / "examples" / "flight1s-v2" / "protocol.json"

MASS_G = 2064
FORCE_MN = 5000
DISTURB_MS = 600
SPAWN_CLEARANCE_MM = 250

# --- rules fixed before the calibration runs -------------------------------

V1_RECOVERY_RADIUS_MM = 200          # the floor v2 may raise but never lower
RADIUS_ROUNDING_MM = 50
IMPULSE_FLOOR_PPK = 500
IMPULSE_CEILING_PPK = 1500
NEGATIVE_SIGMA = 6                   # how far the floor must clear the controls

# Margin derivation. Declared quantities only.
SPEED_CEILING_MM_S = 1500            # above the free delta-v of 1453 mm/s
SAMPLE_INTERVAL_CEILING_MS = 25      # above 1/50 Hz, and above the 21.3 ms seen
REFERENCE_ERROR_MM = 10              # hover band 200 mm over ~400 samples
MARGIN_ROUNDING_MM = 10

STAGES = {
    "settle_ms": 2000, "takeoff_alt_mm": 1500, "takeoff_hold_ms": 12000,
    "stabilize_ms": 5000, "hover_ms": 10000, "disturb_ms": DISTURB_MS,
    "recover_ms": 10000, "land_ms": 40000,
}
TIMEOUTS = {"launch_s": 120, "estimator_s": 120, "arm_s": 60, "takeoff_s": 30,
            "land_s": 60, "episode_s": 420}
RATES = {"sample_hz": 50, "setpoint_hz": 0}
BODY = {
    "model": "x500",
    "source": "PX4-Autopilot/Tools/simulation/gz/models",
    "px4_tag": "v1.15.4",
    "px4_commit": PX4_COMMIT,
    "px4_models_commit": PX4_MODELS_COMMIT,
    "airframe": 4001,
    "mass_g": MASS_G,
    "envelope_radius_mm": 400,
    "clearance_mm": 1100,
    "column_top_mm": 2500,
}
UNITS = {"length": "mm", "speed": "mm_per_s", "angle": "mdeg",
         "angular_rate": "mdeg_per_s", "force": "mN", "impulse": "mN_s",
         "time": "ms", "sim_time": "ns", "ratio": "ppk"}
MEASUREMENT_NOTE = (
    "finite difference of the backend pose stream; not an independent "
    "velocity sensor, and the net momentum change also reflects PX4's reaction")


def commanded_impulse_mn_s(force_mn: int = FORCE_MN,
                           duration_ms: int = DISTURB_MS) -> int:
    """F*dt in mN*s. What was ordered, not what survived the controller."""
    return int(round(force_mn * duration_ms / 1000))


def free_delta_v_mm_s(force_mn: int = FORCE_MN, duration_ms: int = DISTURB_MS,
                      mass_g: int = MASS_G) -> int:
    """The speed change an unopposed body of this mass would take."""
    return int(round(commanded_impulse_mn_s(force_mn, duration_ms) / mass_g
                     * 1000))


def exit_margin_mm() -> Dict:
    """Resolution, sampling rate and reference error. Nothing observed."""
    blind = math.ceil(SPEED_CEILING_MM_S * SAMPLE_INTERVAL_CEILING_MS / 1000)
    raw = blind + REFERENCE_ERROR_MM
    margin = int(math.ceil(raw / MARGIN_ROUNDING_MM) * MARGIN_ROUNDING_MM)
    return {
        "exit_margin_mm": margin,
        "derivation": {
            "speed_ceiling_mm_s": SPEED_CEILING_MM_S,
            "sample_interval_ceiling_ms": SAMPLE_INTERVAL_CEILING_MS,
            "blind_spot_mm": blind,
            "reference_error_mm": REFERENCE_ERROR_MM,
            "rounding_mm": MARGIN_ROUNDING_MM,
        },
    }


def recovery_radius_mm(nominal_envelope_mm: float) -> int:
    """Never below v1's band; raised if A-v2 says the body wanders more."""
    grown = int(math.ceil(nominal_envelope_mm / RADIUS_ROUNDING_MM)
                * RADIUS_ROUNDING_MM)
    return max(V1_RECOVERY_RADIUS_MM, grown)


def impulse_floor_ppk(negative_ratios: Sequence[float]) -> Dict:
    """The floor moves away from the negative controls, never toward them."""
    if not negative_ratios:
        return {"min_impulse_ratio_ppk": IMPULSE_FLOOR_PPK,
                "from_controls": None, "n_controls": 0,
                "rule": f"max({IMPULSE_FLOOR_PPK}, mean + {NEGATIVE_SIGMA}"
                        f" sigma of the negative controls)"}
    n = len(negative_ratios)
    mean = sum(negative_ratios) / n
    var = sum((r - mean) ** 2 for r in negative_ratios) / n if n > 1 else 0.0
    bound = mean + NEGATIVE_SIGMA * math.sqrt(var)
    from_controls = int(math.ceil(bound / 10) * 10)
    return {
        "min_impulse_ratio_ppk": max(IMPULSE_FLOOR_PPK, from_controls),
        "from_controls": from_controls,
        "control_mean_ppk": round(mean, 2),
        "control_sd_ppk": round(math.sqrt(var), 2),
        "n_controls": n,
        "rule": f"max({IMPULSE_FLOOR_PPK}, mean + {NEGATIVE_SIGMA} sigma, "
                f"rounded up to 10)",
    }


@dataclass(frozen=True)
class Protocol:
    sha256: str
    data: Dict
    path: Optional[Path] = None

    def __getitem__(self, key: str):
        return self.data[key]

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    @property
    def version(self) -> int:
        return int(self.data["schema_version"])


def body_with_placement() -> Dict:
    body = dict(BODY)
    body["spawn_clearance_mm"] = SPAWN_CLEARANCE_MM
    return body


def load(path: Optional[Path] = None) -> Protocol:
    p = Path(path or DEFAULT_PATH)
    raw = read_bounded(p, code="flight_protocol_v2")
    data = loads_strict(raw, code="flight_protocol_v2")
    if int(data.get("schema_version", 0)) != 2:
        raise Sim3Error("protocol_not_v2", str(data.get("schema_version")))
    schema = loads_strict(read_bounded(SCHEMA, code="schema"), code="schema")
    _validate_schema(data, schema, "flight_protocol_v2_schema")

    # Semantics JSON Schema cannot state.
    if data["body"]["px4_commit"] != PX4_COMMIT:
        raise Sim3Error("protocol_px4_commit", data["body"]["px4_commit"])
    if data["body"]["px4_models_commit"] != PX4_MODELS_COMMIT:
        raise Sim3Error("protocol_px4_models_commit",
                        data["body"]["px4_models_commit"])
    if data["supersedes"]["protocol_sha256"] != V1_PROTOCOL_SHA256:
        raise Sim3Error("protocol_supersedes_wrong_v1",
                        data["supersedes"]["protocol_sha256"])
    if data["supersedes"]["report_sha256"] != V1_REPORT_SHA256:
        raise Sim3Error("protocol_supersedes_wrong_report",
                        data["supersedes"]["report_sha256"])
    if data["challenge"]["recovery_radius_mm"] != data["recovery"]["radius_mm"]:
        raise Sim3Error("protocol_radius_disagreement",
                        f"{data['challenge']['recovery_radius_mm']} != "
                        f"{data['recovery']['radius_mm']}")
    if data["recovery"]["radius_mm"] < V1_RECOVERY_RADIUS_MM:
        raise Sim3Error("protocol_radius_below_v1",
                        str(data["recovery"]["radius_mm"]))
    if data["stimulus"]["min_impulse_ratio_ppk"] < IMPULSE_FLOOR_PPK:
        raise Sim3Error("protocol_impulse_floor_lowered",
                        str(data["stimulus"]["min_impulse_ratio_ppk"]))
    if data["stimulus"]["commanded_impulse_mn_s"] != commanded_impulse_mn_s(
            data["disturbance"]["force_mn"], data["stages"]["disturb_ms"]):
        raise Sim3Error("protocol_impulse_arithmetic",
                        str(data["stimulus"]["commanded_impulse_mn_s"]))
    expected = exit_margin_mm()
    if data["challenge"]["exit_margin_mm"] != expected["exit_margin_mm"]:
        raise Sim3Error("protocol_margin_not_derived",
                        f"{data['challenge']['exit_margin_mm']} != "
                        f"{expected['exit_margin_mm']}")

    merged = dict(data)
    merged["body"] = {**data["body"], "spawn_clearance_mm": SPAWN_CLEARANCE_MM}
    return Protocol(sha256=sha256_bytes(raw), data=merged, path=p)


def load_from_dict(data: Dict) -> Protocol:
    """Validate an in-memory instance. Used to prove a rule is enforced.

    The loader merges a placement field into ``body`` that the schema does
    not know about, so it is stripped again before re-validating.
    """
    clone = json.loads(json.dumps(data))
    clone.get("body", {}).pop("spawn_clearance_mm", None)
    raw = json.dumps(clone, sort_keys=True).encode("utf-8")
    schema = loads_strict(read_bounded(SCHEMA, code="schema"), code="schema")
    _validate_schema(clone, schema, "flight_protocol_v2_schema")
    if clone["challenge"]["recovery_radius_mm"] != clone["recovery"]["radius_mm"]:
        raise Sim3Error("protocol_radius_disagreement", "in-memory instance")
    return Protocol(sha256=sha256_bytes(raw), data=clone, path=None)


def calibration(force_mn: int = FORCE_MN) -> Dict:
    """A runnable configuration for the A-v2 calibration. Never a certificate."""
    return {
        "schema_version": 2,
        "scope": SCOPE_CAL,
        "dataset_kind": "calibration",
        "profile": PROFILE_CAL,
        "body": body_with_placement(),
        "stages": dict(STAGES),
        "timeouts": dict(TIMEOUTS),
        "rates": dict(RATES),
        "disturbance": {
            "kind": "backend_link_wrench",
            "link": "x500_0::base_link",
            "frame": "world",
            "axis": [1, 0, 0],
            "force_mn": int(force_mn),
            "publications": 1,
            "require_clear": True,
            "swept_on_split": "A",
        },
    }


SCOPE_CAL = "flight_software_in_the_loop"
PROFILE_CAL = "flight1s-x500-v2"


def freeze(*, force_mn: int, radius_mm: int, margin: Dict, stimulus: Dict,
           hover_bands: Dict, tolerances: Dict, worlds: Dict,
           order_seed: int, defect: str,
           path: Optional[Path] = None) -> Path:
    """Write the frozen v2 instance. Refuses to overwrite one that exists."""
    target = Path(path or DEFAULT_PATH)
    if target.exists():
        raise Sim3Error("protocol_v2_exists", str(target))
    data = {
        "schema_version": 2,
        "scope": SCOPE_CAL,
        "dataset_kind": "rehearsal",
        "profile": PROFILE_CAL,
        "supersedes": {
            "version": 1,
            "protocol_sha256": V1_PROTOCOL_SHA256,
            "report_sha256": V1_REPORT_SHA256,
            "verdict": "red",
            "defect": defect,
        },
        "units": dict(UNITS),
        "worlds": worlds,
        "body": dict(BODY),
        "stages": dict(STAGES),
        "conditions": ["nominal", "perturbed"],
        "repeats": 2,
        "episodes": 48,
        "disturbance": {
            "kind": "backend_link_wrench",
            "link": "x500_0::base_link",
            "frame": "world",
            "axis": [1, 0, 0],
            "force_mn": int(force_mn),
            "publications": 1,
            "require_clear": True,
            "swept_on_split": "A",
        },
        "stimulus": {
            "min_impulse_ratio_ppk": int(stimulus["min_impulse_ratio_ppk"]),
            "max_impulse_ratio_ppk": IMPULSE_CEILING_PPK,
            "commanded_impulse_mn_s": commanded_impulse_mn_s(
                force_mn, STAGES["disturb_ms"]),
            "free_delta_v_mm_s": free_delta_v_mm_s(force_mn,
                                                   STAGES["disturb_ms"]),
            "measurement": MEASUREMENT_NOTE,
        },
        "challenge": {
            "recovery_radius_mm": int(radius_mm),
            "exit_margin_mm": int(margin["exit_margin_mm"]),
            "margin_derivation": margin["derivation"],
        },
        "recovery": {
            "radius_mm": int(radius_mm),
            "hold_ms": 3000,
            "timeout_ms": 10000,
            "measured_from": "end_of_disturb_window",
        },
        "hover_bands": hover_bands,
        "tolerances": tolerances,
        "timeouts": dict(TIMEOUTS),
        "rates": dict(RATES),
        "order_seed": int(order_seed),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return target
