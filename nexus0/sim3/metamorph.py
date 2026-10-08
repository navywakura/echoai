"""Metamorphic pairs: two questions with known answers.

*Rename and reorder.* The same geometry written with the model names
permuted and the XML in a different order must produce the same
fingerprint, the same physics and — the part that matters — a tick
transcript the consumer cannot tell apart. If a name changed anything
visible, the boundary would be leaking identity.

*Move a wall.* Shifting one barrier by 500 mm must change the private
AABBs, change what the backend's entities report, and change what the
rig collides with — while the consumer's transcript stays identical. A
hash that changes while the simulator behaves the same would mean the
world file is decorative.

Every transformed package is validated again from scratch before it is
run, exactly like a fresh one.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.generate import Box, render_manifest, render_sdf, Layout
from echoai.nexus0.sim3.geom import Aabb
from echoai.nexus0.sim3.pkg import ROLE_BARRIER, Package, Protocol, load_package

SHIFT_MM = 500


def _boxes(package: Package) -> List[Box]:
    out: List[Box] = []
    for model in package.sdf.models:
        if model.ambient != model.diffuse:
            raise Sim3Error("metamorph_two_tone_material", model.name)
        out.append(Box(name="", pose=model.pose_mm, size=model.size_mm,
                       grey=model.ambient[0], role=package.roles[model.name]))
    return out


def _write(pkg_dir: Path, boxes: Sequence[Box], spawn_xy: Tuple[int, int],
           spawn_z: int, protocol: Protocol) -> Package:
    layout = Layout(boxes=list(boxes), spawn_xy=spawn_xy, archetype="derived")
    sdf_raw = render_sdf(layout)
    manifest_raw = render_manifest(layout, sha256_bytes(sdf_raw), protocol.sha256,
                                   spawn_z)
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "world.sdf").write_bytes(sdf_raw)
    (pkg_dir / "manifest.json").write_bytes(manifest_raw)
    return load_package(pkg_dir, protocol)


def renamed(package: Package, out_dir: Path, protocol: Protocol) -> Package:
    """Same geometry, models reversed in order and therefore renamed."""
    boxes = _boxes(package)
    if len(boxes) < 2:
        raise Sim3Error("metamorph_too_few_models", str(len(boxes)))
    reordered = list(reversed(boxes))
    spawn = package.spawn_mm
    return _write(Path(out_dir), reordered, (spawn[0], spawn[1]), spawn[2], protocol)


@dataclass
class MovedWall:
    package: Package
    barrier_index: int
    axis: int
    shift_mm: int
    drop_column_mm: Tuple[int, int]
    old_aabb: List[int]
    new_aabb: List[int]
    barrier_top_mm: int


def _column_clear(boxes: Sequence[Box], cx: int, cy: int, radius: int,
                  ignore: Optional[int] = None) -> bool:
    for i, box in enumerate(boxes):
        if i == ignore or box.role == "floor":
            continue
        aabb = Aabb.from_pose_size(box.pose, box.size)
        if aabb.intersects_xy_disc(cx, cy, radius):
            return False
    return True


def moved_wall(package: Package, out_dir: Path, protocol: Protocol,
               *, rig_radius_mm: int) -> MovedWall:
    """Shift one barrier 500 mm, keeping a drop column free in both worlds."""
    boxes = _boxes(package)
    barrier_positions = [i for i, b in enumerate(boxes) if b.role == ROLE_BARRIER]
    spawn = package.spawn_mm
    last: Optional[Sim3Error] = None
    for index in barrier_positions:
        original = boxes[index]
        for axis, sign in ((0, 1), (0, -1), (1, 1), (1, -1)):
            if original.size[axis] >= SHIFT_MM:
                # The shift has to exceed the wall's own thickness on that
                # axis, or the moved wall still overlaps the drop column
                # in the original world and the collision probe proves
                # nothing.
                continue
            pose = list(original.pose)
            pose[axis] += sign * SHIFT_MM
            moved = Box(name="", pose=tuple(pose), size=original.size,
                        grey=original.grey, role=original.role)
            candidate = list(boxes)
            candidate[index] = moved
            cx, cy = moved.pose[0], moved.pose[1]
            if not _column_clear(candidate, cx, cy, rig_radius_mm, ignore=index):
                continue
            if not _column_clear(boxes, cx, cy, rig_radius_mm):
                continue
            try:
                new_pkg = _write(Path(out_dir), candidate, (spawn[0], spawn[1]),
                                 spawn[2], protocol)
            except Sim3Error as exc:
                last = exc
                continue
            old_box = Aabb.from_pose_size(original.pose, original.size)
            new_box = Aabb.from_pose_size(moved.pose, moved.size)
            return MovedWall(
                package=new_pkg,
                barrier_index=index,
                axis=axis,
                shift_mm=sign * SHIFT_MM,
                drop_column_mm=(cx, cy),
                old_aabb=old_box.as_list(),
                new_aabb=new_box.as_list(),
                barrier_top_mm=new_box.hi[2],
            )
    raise Sim3Error("metamorph_no_movable_wall",
                    f"last={last.code if last else 'none'}")
