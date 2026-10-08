"""The effective world for a flight episode, and the envelope gate.

Same discipline as SIM-3: the source ``world.sdf`` is data and its bytes
are never touched; the copy that runs carries code, and the two hashes
travel separately. What changes is the list — a body that flies needs an
IMU, a barometer and a navsat system, a georeferenced origin so the
navsat produces anything at all, and the wrench system that applies the
disturbance. The list is fixed here, identical in all twelve worlds, and
no world can ask for a different one.

The envelope gate is the other half. SIM-3 validated its worlds for a
250 mm sphere; an X500 is much larger and the disturbance moves it. A
world that cannot hold the body is reported as incompatible — it is not
quietly flown in anyway, and its committed bytes are not edited to make
it fit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.pkg import Package

RIG_FREE = "flight1s"

# The world's systems. Fixed and versioned; a world is data and cannot
# choose code. Physics/UserCommands/SceneBroadcaster are the SIM-3 three;
# UserCommands is what lets PX4 create its own model through the backend
# instead of the supervisor placing a body by hand.
WORLD_SYSTEMS: Tuple[Tuple[str, str], ...] = (
    ("gz-sim-physics-system", "gz::sim::systems::Physics"),
    ("gz-sim-user-commands-system", "gz::sim::systems::UserCommands"),
    ("gz-sim-scene-broadcaster-system", "gz::sim::systems::SceneBroadcaster"),
)

# SceneBroadcaster publishes moving poses at 60 Hz by default, which is a
# coarse ruler for a 1 kHz physics step and for a disturbance measured in
# hundreds of milliseconds. Raised here, in the fixed list, not per world.
SCENE_BROADCASTER_PARAMS = {"dynamic_pose_hz": "250", "state_hz": "30"}

# Instrumentation and body support, listed apart so the extension over the
# SIM-3 list is visible rather than folded in.
FLIGHT_SYSTEMS: Tuple[Tuple[str, str], ...] = (
    ("gz-sim-contact-system", "gz::sim::systems::Contact"),
    ("gz-sim-apply-link-wrench-system", "gz::sim::systems::ApplyLinkWrench"),
    ("gz-sim-imu-system", "gz::sim::systems::Imu"),
    ("gz-sim-air-pressure-system", "gz::sim::systems::AirPressure"),
    ("gz-sim-navsat-system", "gz::sim::systems::NavSat"),
)

# One origin for every world. A georeferenced world is what makes the
# navsat sensor produce a fix and therefore what gives EKF2 a horizontal
# position; the numbers are PX4's own SITL default, identical in A, B and
# C, and they distinguish no room from any other.
# PX4 simulates the magnetometer itself (SENS_EN_MAGSIM=1) from the world's
# declared field. A world without one leaves EKF2 with no yaw reference and
# the vehicle refuses to leave the ground with "Yaw estimate error" — found
# the hard way, on the first episode that armed and then auto-disarmed.
# These are PX4's own SITL values, identical in all twelve worlds.
MAGNETIC_FIELD = "6e-06 2.3e-05 -4.2e-05"
ATMOSPHERE = "adiabatic"

SPHERICAL_ORIGIN = {
    "surface_model": "EARTH_WGS84",
    "world_frame_orientation": "ENU",
    "latitude_deg": "47.397971057728974",
    "longitude_deg": "8.546163739800146",
    "elevation": "0",
}


def _metres(v_mm: int) -> str:
    return str(Decimal(int(v_mm)) / 1000)


@dataclass(frozen=True)
class EffectiveWorld:
    data: bytes
    sha256: str
    source_sha256: str
    systems: List[str]
    world_name: str


def build_effective(source_sdf: bytes, source_sha256: str,
                    *, world_name: str = "sim3") -> EffectiveWorld:
    """Insert the fixed systems and the common georeferenced origin."""
    marker = b"  </world>"
    idx = source_sdf.rfind(marker)
    if idx < 0:
        raise Sim3Error("effective_no_world_close", "profile-valid SDF expected")
    systems = list(WORLD_SYSTEMS) + list(FLIGHT_SYSTEMS)
    lines = []
    for fn, cls in systems:
        if cls.endswith("SceneBroadcaster"):
            lines.append(f'    <plugin filename="{fn}" name="{cls}">')
            for key, value in SCENE_BROADCASTER_PARAMS.items():
                lines.append(f"      <{key}>{value}</{key}>")
            lines.append("    </plugin>")
        else:
            lines.append(f'    <plugin filename="{fn}" name="{cls}"/>')
    lines.append(f"    <magnetic_field>{MAGNETIC_FIELD}</magnetic_field>")
    lines.append(f'    <atmosphere type="{ATMOSPHERE}"/>')
    lines.append("    <spherical_coordinates>")
    for key, value in SPHERICAL_ORIGIN.items():
        lines.append(f"      <{key}>{value}</{key}>")
    lines.append("    </spherical_coordinates>")
    block = ("\n".join(lines) + "\n").encode("utf-8")
    data = source_sdf[:idx] + block + source_sdf[idx:]
    return EffectiveWorld(
        data=data,
        sha256=sha256_bytes(data),
        source_sha256=source_sha256,
        systems=[cls for _, cls in systems],
        world_name=world_name,
    )


@dataclass(frozen=True)
class Envelope:
    ok: bool
    package_id: str
    spawn_mm: Tuple[int, int, int]
    floor_top_mm: int
    required_radius_mm: int
    column_top_mm: int
    wall_margin_mm: int
    floor_covers: bool
    blockers: List[str]

    def as_dict(self) -> Dict:
        return {
            "package_id": self.package_id,
            "ok": self.ok,
            "spawn_mm": list(self.spawn_mm),
            "floor_top_mm": self.floor_top_mm,
            "required_radius_mm": self.required_radius_mm,
            "column_top_mm": self.column_top_mm,
            "wall_margin_mm": self.wall_margin_mm,
            "floor_covers_column": self.floor_covers,
            "blockers": self.blockers,
        }


def check_envelope(package: Package, package_id: str, body: Dict) -> Envelope:
    """Does this world hold an X500 that is about to be shoved sideways?

    The required free cylinder is the body envelope plus the excursion the
    disturbance is allowed to produce, from the floor up to the declared
    column top. Barriers, the station and the domain walls all count; the
    floor has to cover the whole footprint, because a rotor over the edge
    of a 12 m floor is not a controlled experiment.
    """
    radius = int(body["envelope_radius_mm"]) + int(body["clearance_mm"])
    top = int(body["column_top_mm"])
    spawn = tuple(int(v) for v in package.spawn_mm)
    floor_box = package.aabb_of(package.floor)
    floor_top = floor_box.hi[2]

    blockers = []
    for model in package.sdf.models:
        role = package.roles[model.name]
        if role == "floor":
            continue
        if (model.aabb.intersects_xy_disc(spawn[0], spawn[1], radius)
                and model.aabb.hi[2] > floor_top
                and model.aabb.lo[2] < floor_top + top):
            blockers.append(f"{model.name}:{role}")

    floor_covers = floor_box.covers_xy_disc(spawn[0], spawn[1], radius)
    wall_margin = min(8000 - abs(spawn[0]), 8000 - abs(spawn[1])) - radius
    return Envelope(
        ok=not blockers and floor_covers and wall_margin >= 0,
        package_id=package_id,
        spawn_mm=spawn,  # type: ignore[arg-type]
        floor_top_mm=floor_top,
        required_radius_mm=radius,
        column_top_mm=top,
        wall_margin_mm=wall_margin,
        floor_covers=floor_covers,
        blockers=blockers,
    )


def spawn_pose(package: Package, body: Dict) -> Tuple[str, Tuple[int, int, int]]:
    """Where PX4 is told to create its model, in metres, rotation zero.

    The xy comes from the world's own private manifest, exactly as the
    SIM-3 rig's did, and the z from the floor it will stand on. This is an
    initial condition, not a branch: the same rule runs in all twelve
    worlds and the driver never reads it.
    """
    spawn = tuple(int(v) for v in package.spawn_mm)
    floor_top = package.aabb_of(package.floor).hi[2]
    z = floor_top + int(body["spawn_clearance_mm"])
    pose = f"{_metres(spawn[0])},{_metres(spawn[1])},{_metres(z)},0,0,0"
    return pose, (spawn[0], spawn[1], z)
