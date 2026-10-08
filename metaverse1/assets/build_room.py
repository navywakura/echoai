"""Generate a METAVERSE-1 room mesh with Blender, headless and reproducibly.

Run it through Blender, never as plain Python (``bpy`` only exists inside):

    flatpak run org.blender.Blender --background \\
        --python echoai/metaverse1/assets/build_room.py -- \\
        --out echoai/lab/metaverse1/rooms --seed 1 --name sala-01

The geometry is derived from the room description, not modelled by hand, so
the same seed gives the same mesh and the mesh can be regenerated from the
declaration alone.  Scale follows DRONE-3's certified domain: 3 m cells in a
21 x 15 m room, walls 2.5 m tall.

This writes assets.  It does not decide anything, does not touch the agent and
is not part of any certified path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

import bpy  # provided by Blender; absent from the system interpreter

CELL_M = 3.0
COLS, ROWS = 7, 5          # 21 x 15 m, the DRONE-3 domain
WALL_H = 2.5
WALL_T = 0.15


def clear_scene() -> None:
    """Start from an empty file: the default cube is not part of the room."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def cuboid(name: str, centre, size) -> "bpy.types.Object":
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centre)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = tuple(s / 1.0 for s in size)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def floor() -> None:
    cuboid("floor", (COLS * CELL_M / 2, ROWS * CELL_M / 2, -0.05),
           (COLS * CELL_M, ROWS * CELL_M, 0.1))


def perimeter() -> None:
    width, depth = COLS * CELL_M, ROWS * CELL_M
    half = WALL_H / 2
    cuboid("wall_south", (width / 2, 0, half), (width, WALL_T, WALL_H))
    cuboid("wall_north", (width / 2, depth, half), (width, WALL_T, WALL_H))
    cuboid("wall_west", (0, depth / 2, half), (WALL_T, depth, WALL_H))
    cuboid("wall_east", (width, depth / 2, half), (WALL_T, depth, WALL_H))


def obstacles(rng: random.Random, count: int) -> list[list[int]]:
    """Block whole cells, never half of one: the agent reasons in cells."""
    free = [(c, r) for c in range(COLS) for r in range(ROWS)
            if (c, r) not in {(0, 0), (COLS - 1, ROWS - 1)}]
    rng.shuffle(free)
    chosen = sorted(free[:count])
    for index, (col, row) in enumerate(chosen):
        cuboid(f"block_{index:02d}",
               ((col + 0.5) * CELL_M, (row + 0.5) * CELL_M, WALL_H / 2),
               (CELL_M * 0.8, CELL_M * 0.8, WALL_H))
    return [[col, row] for col, row in chosen]


def export(out: Path, name: str) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{name}.glb"
    bpy.ops.export_scene.gltf(filepath=str(target), export_format="GLB")
    return target


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", default="sala")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--obstacles", type=int, default=6)
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    clear_scene()
    floor()
    perimeter()
    blocked = obstacles(rng, max(0, min(args.obstacles, COLS * ROWS - 2)))
    out = Path(args.out).expanduser().resolve()
    mesh = export(out, args.name)

    declaration = {
        "schema": "echoai-metaverse1-room-v1",
        "name": args.name,
        "seed": args.seed,
        "cell_m": CELL_M,
        "cols": COLS,
        "rows": ROWS,
        "size_m": [COLS * CELL_M, ROWS * CELL_M],
        "wall_height_m": WALL_H,
        "blocked_cells": blocked,
        "start_cell": [0, 0],
        "goal_cell": [COLS - 1, ROWS - 1],
        "mesh": mesh.name,
        "mesh_sha256": hashlib.sha256(mesh.read_bytes()).hexdigest(),
        "blender": bpy.app.version_string,
        "note": ("Malla generada por script desde esta declaración. "
                 "No es física ni certificado: sólo geometría."),
    }
    (out / f"{args.name}.json").write_text(
        json.dumps(declaration, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print("ROOM_OK", json.dumps({"mesh": str(mesh),
                                 "sha256": declaration["mesh_sha256"][:16],
                                 "blocked": len(blocked)}))
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sys.exit(main(argv))
