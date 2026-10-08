"""SDF emission for META-WORLD-2, with visual detail separated from collision.

The criterion the contract fixes is that raising visual fidelity must not
change trajectories, events or scoring.  Making that checkable means keeping
the two kinds of geometry apart in the emitted world:

* **collision** geometry comes from the cells alone.  It is identical at every
  detail level, and :func:`collision_digest` proves it.
* **visual** geometry — trim, lights, floor patterning, region colouring —
  only ever adds ``<visual>`` elements and never a ``<collision>``.

Physics settings are inherited from the frozen FLIGHT-1S world, not invented
here.  Only declarative models are emitted; no world systems, no plugins.
"""
from __future__ import annotations

import hashlib
import re

CELL_M = 3.0
WALL_H_M = 4.0

#: Region tint is decoration.  The simulator ids it produces never reach the
#: policy: they exist in the SDF and in the log, not in Q, CAM or T.
TEMPLATE_COLOUR = {
    "room": "0.70 0.70 0.70 1",
    "hall": "0.62 0.66 0.72 1",
}

_COLLISION = re.compile(r"<collision\b.*?</collision>", re.S)


def _box_visual(size: str, colour: str) -> str:
    geometry = f"<geometry><box><size>{size}</size></box></geometry>"
    return (f"<visual name=\"visual\">{geometry}<material>"
            f"<ambient>{colour}</ambient><diffuse>{colour}</diffuse>"
            f"</material></visual>")


def _box(name: str, pose: str, size: str, colour: str, *, solid: bool = True) -> str:
    geometry = f"<geometry><box><size>{size}</size></box></geometry>"
    collision = f"<collision name=\"collision\">{geometry}</collision>" if solid else ""
    return (f'    <model name="{name}"><static>true</static><pose>{pose}</pose>'
            f'<link name="link">{collision}{_box_visual(size, colour)}</link></model>')


def source_sdf(space, *, detail: int = 0, empty: bool = False) -> bytes:
    """Emit the world.  ``detail`` adds visuals only, never collision."""
    if not isinstance(detail, int) or not 0 <= detail <= 2:
        raise ValueError("detail must be 0, 1 or 2")
    width, height = space.blocks.size
    span = max(width, height) * CELL_M * 2

    lines = ['<?xml version="1.0"?><sdf version="1.9"><world name="sim3">',
             '    <physics name="physics" type="ignored">'
             '<max_step_size>0.001</max_step_size>'
             '<real_time_factor>1</real_time_factor></physics>',
             '    <gravity>0 0 -9.80665</gravity>',
             '    <light name="sun" type="directional"><pose>0 0 10 0 0 0</pose>'
             '<diffuse>1 1 1 1</diffuse><direction>0.2 0.3 -1</direction></light>']

    lines.append(_box("floor", "0 0 -0.1 0 0 0", f"{span} {span} 0.2",
                      "0.35 0.35 0.35 1"))

    if not empty:
        for index, cell in enumerate(sorted(space.solids)):
            x, y, _ = cell
            try:
                region = space.blocks.region_of(space.unrotate(cell))
                colour = TEMPLATE_COLOUR.get(region.template, "0.7 0.7 0.7 1")
            except Exception:
                colour = "0.7 0.7 0.7 1"
            lines.append(_box(f"barrier_{index}", f"{x * CELL_M} {y * CELL_M} 2 0 0 0",
                              f"{CELL_M} {CELL_M} {WALL_H_M}",
                              colour if detail else "0.7 0.7 0.7 1"))
        # A marker on the enclosing wall identifies the station's approach
        # area. It does not occupy the cell where the body must arrive.
        dx, dy, _ = space.rotate((1, 0, 0))
        x, y, _ = space.goal
        size = "0.02 1 1" if dx else "1 0.02 1"
        lines.append(_box("station_beacon",
                          f"{x * CELL_M + dx * 1.49} {y * CELL_M + dy * 1.49} 2.5 0 0 0",
                          size, "0 1 0 1"))

    if detail >= 1:
        lines.extend(_trim(space))
    if detail >= 2:
        lines.extend(_fixtures(space))

    lines.append("  </world></sdf>")
    return ("\n".join(lines) + "\n").encode()


def _trim(space) -> list[str]:
    """Level 1: floor markings per region.  Visual only, flat on the ground."""
    out = []
    for region in space.blocks.regions:
        cx = (region.origin[0] + region.width / 2 - 0.5) * CELL_M
        cy = (region.origin[1] + region.height / 2 - 0.5) * CELL_M
        x, y, _ = space.rotate((cx / CELL_M, cy / CELL_M, 0))
        out.append(_box(f"trim_{region.ident}",
                        f"{x * CELL_M} {y * CELL_M} 0.01 0 0 0",
                        f"{(region.width - 1) * CELL_M} {(region.height - 1) * CELL_M} 0.02",
                        TEMPLATE_COLOUR.get(region.template, "0.5 0.5 0.5 1"),
                        solid=False))
    return out


def _fixtures(space) -> list[str]:
    """Level 2: ceiling lights.  Visual only, above the flight envelope."""
    out = []
    for region in space.blocks.regions:
        cx = region.origin[0] + region.width // 2
        cy = region.origin[1] + region.height // 2
        x, y, _ = space.rotate((cx, cy, 0))
        out.append(_box(f"lamp_{region.ident}",
                        f"{x * CELL_M} {y * CELL_M} {WALL_H_M + 0.4} 0 0 0",
                        "1.2 0.2 0.1", "1 0.97 0.86 1", solid=False))
    return out


def collision_digest(document: bytes) -> str:
    """sha256 over the collision geometry alone.

    Two worlds with the same digest are the same world as far as physics is
    concerned, whatever their visual detail.
    """
    text = document.decode("utf-8")
    models = re.findall(r'<model name="([^"]+)"[^>]*><static>[^<]*</static>'
                        r'<pose>([^<]*)</pose><link name="link">(.*?)</link>',
                        text, re.S)
    payload = []
    for name, pose, body in models:
        collisions = _COLLISION.findall(body)
        if collisions:
            payload.append(name + "|" + pose.strip() + "|" + "".join(collisions))
    return hashlib.sha256("\n".join(sorted(payload)).encode()).hexdigest()


def visual_count(document: bytes) -> int:
    return document.decode("utf-8").count("<visual ")
