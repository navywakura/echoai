"""The trusted rig, and the systems the supervisor is allowed to add.

A world in SIM-3 is data: it cannot ask for code. Systems come from the
fixed, versioned list below and are written into a *copy* of the world —
the effective SDF — which is hashed separately from the source. Confusing
the two hashes would let a world be certified by one file and run as
another, so both travel through the report side by side.

The rig itself is a sphere of known radius and mass with a contact
sensor. It is inserted from here, identically in every world, at the
private spawn column. It is instrumentation: it is not an agent, it is
not controlled, and dropping it proves gravity and collision — nothing
about aerodynamics.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.generate import metres

RIG_MODEL = "sim3_rig"
RIG_LINK = "body"
RIG_COLLISION = "solid"
RIG_SENSOR = "rig_contact"

# The world's own systems. SIM3-DESIGN.md §4 names exactly these three.
WORLD_SYSTEMS: Tuple[Tuple[str, str], ...] = (
    ("gz-sim-physics-system", "gz::sim::systems::Physics"),
    ("gz-sim-user-commands-system", "gz::sim::systems::UserCommands"),
    ("gz-sim-scene-broadcaster-system", "gz::sim::systems::SceneBroadcaster"),
)

# Instrumentation for the rig, listed apart on purpose. The bench must
# *observe* contact rather than infer it from a resting height, and the
# contact sensor needs its system. This is an extension of the fixed
# list, recorded as such in the lock and the report.
RIG_SYSTEMS: Tuple[Tuple[str, str], ...] = (
    ("gz-sim-contact-system", "gz::sim::systems::Contact"),
)

CONTACT_TOPIC = (
    f"/world/sim3/model/{RIG_MODEL}/link/{RIG_LINK}/sensor/{RIG_SENSOR}/contact"
)


def _inertia(mass_g: int, radius_mm: int) -> str:
    """Solid sphere, 2/5 m r^2, in exact decimal."""
    mass = Decimal(mass_g) / 1000
    radius = Decimal(radius_mm) / 1000
    i = (Decimal(2) / 5) * mass * radius * radius
    return str(i.normalize())


def rig_sdf(centre_mm: Sequence[int], radius_mm: int, mass_g: int) -> str:
    pose = " ".join(metres(v) for v in centre_mm) + " 0 0 0"
    radius = metres(radius_mm)
    mass = metres(mass_g)
    i = _inertia(mass_g, radius_mm)
    return "\n".join([
        f'    <model name="{RIG_MODEL}">',
        f"      <pose>{pose}</pose>",
        f'      <link name="{RIG_LINK}">',
        "        <inertial>",
        f"          <mass>{mass}</mass>",
        f"          <inertia><ixx>{i}</ixx><iyy>{i}</iyy><izz>{i}</izz>"
        "<ixy>0</ixy><ixz>0</ixz><iyz>0</iyz></inertia>",
        "        </inertial>",
        f'        <collision name="{RIG_COLLISION}">',
        f"          <geometry><sphere><radius>{radius}</radius></sphere></geometry>",
        "        </collision>",
        '        <visual name="shape">',
        f"          <geometry><sphere><radius>{radius}</radius></sphere></geometry>",
        "        </visual>",
        f'        <sensor name="{RIG_SENSOR}" type="contact">',
        f"          <contact><collision>{RIG_COLLISION}</collision></contact>",
        "          <update_rate>1000</update_rate>",
        "          <always_on>1</always_on>",
        "        </sensor>",
        "      </link>",
        "    </model>",
    ])


@dataclass(frozen=True)
class Effective:
    data: bytes
    sha256: str
    source_sha256: str
    systems: List[str]


def build_effective(source_sdf: bytes, source_sha256: str,
                    centre_mm: Sequence[int], radius_mm: int, mass_g: int,
                    *, scene_broadcaster: bool = True) -> Effective:
    """Insert the fixed systems and the rig into a copy of the world."""
    marker = b"  </world>"
    idx = source_sdf.rfind(marker)
    if idx < 0:
        raise Sim3Error("effective_no_world_close", "profile-valid SDF expected")
    systems = [s for s in WORLD_SYSTEMS
               if scene_broadcaster or "scene-broadcaster" not in s[0]]
    systems += list(RIG_SYSTEMS)
    plugin_lines = "\n".join(
        f'    <plugin filename="{fn}" name="{cls}"/>' for fn, cls in systems
    )
    block = (plugin_lines + "\n"
             + rig_sdf(centre_mm, radius_mm, mass_g) + "\n").encode("utf-8")
    data = source_sdf[:idx] + block + source_sdf[idx:]
    return Effective(
        data=data,
        sha256=sha256_bytes(data),
        source_sha256=source_sha256,
        systems=[cls for _, cls in systems],
    )
