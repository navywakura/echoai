"""Build a META-WORLD-2 mesh from a world declaration.  Blender only.

    flatpak run --filesystem=<repo> org.blender.Blender --background \\
        --python echoai/metaverse1/assets/build_world.py -- \\
        --world <world>.declaration.json --out <dir> --name <name>

Three artefacts, three paths, enforced in ``custody.py``:

    <name>.declaration.json    input, never written by this script
    <name>.glb                 the mesh
    <name>.build-receipt.json  tool, parameters and hashes

Before 2026-09-21 the receipt was written to ``<name>.json`` and, when the
declaration sat in the same directory under the same name, **overwrote it**.
That is how ``wide-3x2`` lost its source.  The naming and the refusals now
live in ``custody.plan``, and the receipt is written only after the export
produced a mesh that reads back as a valid glTF container.

The declaration is plain JSON, so this script never imports echoAI: the asset
pipeline cannot pull the agent into a renderer.  Geometry follows the cells,
so the same declaration always gives the same mesh.

This writes assets.  It is not physics, not evidence, and nothing reads it
back into a decision.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy

# Blender runs this file by path, not as a package, so the sibling module is
# imported the same way — and custody.py imports nothing but the stdlib.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import custody  # noqa: E402

WALL_H = 2.5
FLOOR_T = 0.1
DECLARATION_SCHEMA = "echoai-metaverse1-world-v1"


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def cuboid(name: str, centre, size) -> None:
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centre)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)


def build(world: dict) -> None:
    cell = float(world["cell_m"])
    domain = [tuple(c) for c in world["domain"]]
    solids = {tuple(c) for c in world["solids"]}
    xs = [c[0] for c in domain]
    ys = [c[1] for c in domain]
    width = (max(xs) - min(xs) + 1) * cell
    depth = (max(ys) - min(ys) + 1) * cell
    centre_x = (min(xs) + max(xs)) / 2 * cell
    centre_y = (min(ys) + max(ys)) / 2 * cell

    cuboid("floor", (centre_x, centre_y, -FLOOR_T / 2),
           (width, depth, FLOOR_T))
    for index, (x, y, _z) in enumerate(sorted(solids)):
        cuboid(f"solid_{index:03d}", (x * cell, y * cell, WALL_H / 2),
               (cell, cell, WALL_H))

    start, goal = tuple(world["start"]), tuple(world["goal"])
    cuboid("marker_start", (start[0] * cell, start[1] * cell, 0.05),
           (cell * 0.6, cell * 0.6, 0.1))
    cuboid("marker_goal", (goal[0] * cell, goal[1] * cell, 0.05),
           (cell * 0.6, cell * 0.6, 0.1))


def reimport_check(mesh: Path) -> dict:
    """Load the exported GLB back into an empty scene.

    ``custody.inspect_glb`` reads the container; this proves Blender itself can
    import what Blender just wrote, which is the claim the receipt makes.
    """
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(mesh))
        objects = len(bpy.context.scene.objects)
    except Exception as error:               # noqa: BLE001 - reported, not raised
        return {"ok": False, "reason": f"re-import failed: {error}"}
    if objects == 0:
        return {"ok": False, "reason": "re-imported scene has no objects"}
    return {"ok": True, "reimported_objects": objects}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True,
                        help="path to <name>.declaration.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--name", default="mundo")
    parser.add_argument("--overwrite", action="store_true",
                        help="replace existing artefacts; the receipt records "
                             "the hashes of what was there before")
    parser.add_argument("--reconstruction", default=None,
                        help="note explaining that this rebuilds a world whose "
                             "original declaration was lost")
    args = parser.parse_args(argv)

    source = Path(args.world).expanduser().resolve()
    world = json.loads(source.read_text(encoding="utf-8"))
    if world.get("schema") != DECLARATION_SCHEMA:
        raise SystemExit(
            f"unexpected declaration schema: {world.get('schema')!r} "
            f"(expected {DECLARATION_SCHEMA!r}; a build receipt is not a "
            "declaration)")

    paths = custody.plan(source, args.out, args.name, overwrite=args.overwrite)

    def export(mesh: Path) -> None:
        clear_scene()
        build(world)
        mesh.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.gltf(filepath=str(mesh), export_format="GLB")

    reconstruction = None
    if args.reconstruction:
        reconstruction = {"is_reconstruction": True,
                          "reason": args.reconstruction}

    receipt = custody.build(
        paths, export,
        tool=f"blender {bpy.app.version_string}",
        parameters={"script": Path(__file__).name,
                    "wall_height_m": WALL_H, "floor_thickness_m": FLOOR_T,
                    "export_format": "GLB",
                    "solids": len(world["solids"]),
                    "regions": len(world["regions"]),
                    "size_m": world["size_m"],
                    "seed": world.get("seed"),
                    "condition": world.get("condition")},
        reconstruction=reconstruction,
        extra_validation=reimport_check)

    print("WORLD_OK", json.dumps({"mesh": str(paths.mesh),
                                  "receipt": str(paths.receipt),
                                  "mesh_sha256": receipt["mesh"]["sha256"][:16],
                                  "declaration_sha256":
                                      receipt["declaration"]["sha256"][:16],
                                  "solids": len(world["solids"])}))
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sys.exit(main(argv))
