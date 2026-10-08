"""The frozen protocol, and the only door the sweep uses before it exists.

``load`` reads the committed instance and validates it against the schema;
its SHA-256 is what every report records and what the auditor compares.

``calibration`` is the other door. Before the protocol can be frozen, the
disturbance magnitude and the bands have to be measured on split A, and
that measurement needs a runnable configuration. It returns one, marked
``dataset_kind="calibration"``, and nothing that comes out of it is
allowed into a closing report — the sweep writes its own artefact and the
bench refuses to run without a real frozen protocol file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    loads_strict,
    read_bounded,
    sha256_bytes,
)
from echoai.nexus0.sim3.pkg import _validate_schema
from echoai.nexus0.flight1s.runtime import (
    ECHOAI,
    PX4_COMMIT,
    PX4_MODELS_COMMIT,
    PX4_TAG,
)

SCHEMA = ECHOAI / "docs" / "schemas" / "flight1s-protocol.schema.json"
DEFAULT_PATH = ECHOAI / "docs" / "examples" / "flight1s" / "protocol.json"

# Structural values, identical in the calibration and in the frozen file.
STAGES = {
    "settle_ms": 2000,
    "takeoff_alt_mm": 1500,
    "takeoff_hold_ms": 12000,
    "stabilize_ms": 5000,
    "hover_ms": 10000,
    "disturb_ms": 600,
    "recover_ms": 10000,
    "land_ms": 40000,
}
TIMEOUTS = {"launch_s": 120, "estimator_s": 120, "arm_s": 60, "takeoff_s": 30,
            "land_s": 60, "episode_s": 420}
RATES = {"sample_hz": 50, "setpoint_hz": 0}
BODY = {
    "model": "x500",
    "source": "PX4-Autopilot/Tools/simulation/gz/models",
    "px4_tag": PX4_TAG,
    "px4_commit": PX4_COMMIT,
    "airframe": 4001,
    "envelope_radius_mm": 400,
    "clearance_mm": 1100,
    "column_top_mm": 2500,
}
# Not in the schema: it is a supervisor-side placement rule, not a contract
# term, and it is the same number in every world.
SPAWN_CLEARANCE_MM = 250


@dataclass(frozen=True)
class Protocol:
    sha256: str
    data: Dict
    path: Optional[Path] = None

    def __getitem__(self, key: str):
        return self.data[key]

    def get(self, key: str, default=None):
        return self.data.get(key, default)


def body_with_placement() -> Dict:
    body = dict(BODY)
    body["spawn_clearance_mm"] = SPAWN_CLEARANCE_MM
    return body


def load(path: Optional[Path] = None) -> Protocol:
    p = Path(path or DEFAULT_PATH)
    raw = read_bounded(p, code="flight_protocol")
    data = loads_strict(raw, code="flight_protocol")
    schema = loads_strict(read_bounded(SCHEMA, code="schema"), code="schema")
    _validate_schema(data, schema, "flight_protocol_schema")
    if data["body"]["px4_commit"] != PX4_COMMIT:
        raise Sim3Error("protocol_px4_commit", data["body"]["px4_commit"])
    if data["worlds"]["source"] != "sim3-rehearsal":
        raise Sim3Error("protocol_worlds", data["worlds"]["source"])
    merged = dict(data)
    merged["body"] = {**data["body"], "spawn_clearance_mm": SPAWN_CLEARANCE_MM}
    return Protocol(sha256=sha256_bytes(raw), data=merged, path=p)


def calibration(force_mn: int) -> Dict:
    """A runnable configuration for the split-A sweep. Never a certificate."""
    return {
        "schema_version": 1,
        "scope": "flight_software_in_the_loop",
        "dataset_kind": "calibration",
        "profile": "flight1s-x500-v1",
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
            "swept_on_split": "A",
        },
    }


def freeze(force_mn: int, bands: Dict, tolerances: Dict, *,
           worlds: Dict, order_seed: int, path: Optional[Path] = None) -> Path:
    """Write the frozen instance. Refuses to overwrite one that exists."""
    import json

    target = Path(path or DEFAULT_PATH)
    if target.exists():
        raise Sim3Error("protocol_exists", str(target))
    data = {
        "schema_version": 1,
        "scope": "flight_software_in_the_loop",
        "dataset_kind": "rehearsal",
        "profile": "flight1s-x500-v1",
        "units": {"length": "mm", "speed": "mm_per_s", "angle": "mdeg",
                  "angular_rate": "mdeg_per_s", "force": "mN", "time": "ms",
                  "sim_time": "ns"},
        "worlds": worlds,
        "body": {k: v for k, v in BODY.items()},
        "stages": {k: v for k, v in STAGES.items() if k != "settle_ms"}
                  | {"settle_ms": STAGES["settle_ms"]},
        "conditions": ["nominal", "perturbed"],
        "repeats": 2,
        "episodes": 48,
        "disturbance": {
            "kind": "backend_link_wrench",
            "link": "x500_0::base_link",
            "frame": "world",
            "axis": [1, 0, 0],
            "force_mn": int(force_mn),
            "swept_on_split": "A",
        },
        "bands": bands,
        "tolerances": tolerances,
        "timeouts": dict(TIMEOUTS),
        "rates": dict(RATES),
        "order_seed": int(order_seed),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return target
