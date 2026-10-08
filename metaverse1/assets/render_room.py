"""Render a preview PNG of a generated room.  Blender only, headless.

    flatpak run --filesystem=<repo> org.blender.Blender --background \\
        --python echoai/metaverse1/assets/render_room.py -- \\
        --glb <room>.glb --out <preview>.png

The preview is for looking at, nothing else: it is not evidence, it is not a
measurement, and no decision reads it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy


def aim(camera, target) -> None:
    """Point the camera with a Track To constraint.

    Hand-rolled Euler angles are easy to get subtly wrong and the failure mode
    is a blank frame, which is exactly what happened the first time.
    """
    bpy.ops.object.empty_add(location=target)
    focus = bpy.context.active_object
    focus.name = "focus"
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = focus
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"
    bpy.context.view_layer.update()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--glb", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args(argv)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.glb).resolve()))

    # Frame whatever was imported, so one previewer serves every world size.
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    xs = [v[0] for o in meshes for v in o.bound_box]
    ys = [v[1] for o in meshes for v in o.bound_box]
    corners = [o.matrix_world @ o.matrix_world.inverted() @ o.location for o in meshes]
    px = [o.location[0] for o in meshes] or [0.0]
    py = [o.location[1] for o in meshes] or [0.0]
    centre = ((min(px) + max(px)) / 2, (min(py) + max(py)) / 2, 0.0)
    reach = max(max(px) - min(px), max(py) - min(py), 10.0)
    bpy.ops.object.camera_add(
        location=(centre[0] - reach * 0.75, centre[1] - reach * 0.95, reach * 0.8))
    camera = bpy.context.active_object
    aim(camera, (centre[0], centre[1], 1.0))
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="SUN", location=(centre[0], centre[1], 25))
    bpy.context.active_object.data.energy = 4.0

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.film_transparent = False
    scene.render.filepath = str(Path(args.out).resolve())
    bpy.ops.render.render(write_still=True)
    print("RENDER_OK", scene.render.filepath)
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    sys.exit(main(argv))
