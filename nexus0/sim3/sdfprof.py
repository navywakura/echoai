"""The ``sim3-boxes-v1`` SDF profile: a closed grammar, not a filter.

Two properties matter more than convenience here.

*Closed*: anything the profile does not name is refused. Not ignored, not
stripped — refused, with a cause. An SDF that smuggles a ``<plugin>`` or
an ``<include>`` past a lenient reader would let a world choose its own
code, and the whole point of SIM-3 is that the world is data.

*Exact*: geometry is read as decimal millimetres (see ``geom.mm``), so
the AABB this module returns is the same integer on every machine, and a
hash over it means something.

libsdformat is consulted as well (see ``runtime.check_sdf``), because a
file this module accepts must also be a file Gazebo accepts. Neither
check substitutes for the other: ours is stricter, theirs is the truth
about what the backend will load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET
from xml.parsers import expat

from echoai.nexus0.sim3.canon import Sim3Error, read_bounded, sha256_bytes
from echoai.nexus0.sim3.geom import Aabb, Vec3, pose6, rgba, triple

SDF_VERSION = "1.8"
WORLD_NAME = "sim3"
GRAVITY = "0 0 -9.81"
MAX_STEP_SIZE_MM = 1          # 0.001 m
REAL_TIME_FACTOR = "1"
PHYSICS_TYPE = "ignored"
LINK_NAME = "body"
COLLISION_NAME = "solid"
VISUAL_NAME = "shape"
MIN_MODELS = 3
MAX_MODELS = 64


@dataclass(frozen=True)
class SdfModel:
    name: str
    pose_mm: Vec3
    size_mm: Vec3
    aabb: Aabb
    ambient: Tuple[int, int, int, int]
    diffuse: Tuple[int, int, int, int]


@dataclass
class SdfWorld:
    sha256: str
    n_bytes: int
    models: List[SdfModel] = field(default_factory=list)

    def by_name(self, name: str) -> Optional[SdfModel]:
        for m in self.models:
            if m.name == name:
                return m
        return None

    def aabbs(self) -> List[Aabb]:
        return [m.aabb for m in self.models]


def _parse_tree(data: bytes) -> ET.Element:
    """Build a tree with expat's doctype and entity machinery disarmed.

    ``ET.XMLParser`` no longer exposes its expat handle, so the handlers
    are wired here directly. A DOCTYPE, an entity declaration, an
    external entity reference or a processing instruction each raise
    rather than being parsed and then noticed later.
    """
    builder = ET.TreeBuilder()
    parser = expat.ParserCreate()

    def _doctype(*_args, **_kw):
        raise Sim3Error("sdf_doctype", "DOCTYPE declarations are refused")

    def _entity(*_args, **_kw):
        raise Sim3Error("sdf_entity", "entity declarations are refused")

    def _external(*_args, **_kw):
        raise Sim3Error("sdf_external_entity", "external entities are refused")

    def _pi(*_args, **_kw):
        raise Sim3Error("sdf_processing_instruction", "PIs are refused")

    parser.StartDoctypeDeclHandler = _doctype
    parser.EntityDeclHandler = _entity
    parser.UnparsedEntityDeclHandler = _entity
    parser.ExternalEntityRefHandler = _external
    parser.ProcessingInstructionHandler = _pi
    parser.StartElementHandler = lambda name, attrs: builder.start(name, attrs)
    parser.EndElementHandler = lambda name: builder.end(name)
    parser.CharacterDataHandler = builder.data
    parser.buffer_text = True
    try:
        parser.Parse(data, True)
    except Sim3Error:
        raise
    except expat.ExpatError as exc:
        raise Sim3Error("sdf_malformed", expat.errors.messages.get(
            exc.code, str(exc))) from None
    return builder.close()


def _children(elem: ET.Element, allowed: Dict[str, Tuple[int, int]],
              where: str) -> Dict[str, List[ET.Element]]:
    """Exact-set child check. Unknown tags are an error, not a shrug."""
    found: Dict[str, List[ET.Element]] = {}
    for child in elem:
        tag = child.tag
        if not isinstance(tag, str):
            raise Sim3Error("sdf_non_element", f"{where}: {tag!r}")
        if tag not in allowed:
            raise Sim3Error("sdf_unsupported_element", f"{where}/{tag}")
        found.setdefault(tag, []).append(child)
    for tag, (lo, hi) in allowed.items():
        n = len(found.get(tag, ()))
        if not lo <= n <= hi:
            raise Sim3Error("sdf_child_count", f"{where}/{tag}: {n} not in [{lo},{hi}]")
    if elem.text and elem.text.strip() and allowed:
        raise Sim3Error("sdf_mixed_content", where)
    for child in elem:
        if child.tail and child.tail.strip():
            raise Sim3Error("sdf_mixed_content", f"{where}/{child.tag}")
    return found


def _attrs(elem: ET.Element, allowed: Tuple[str, ...], where: str) -> None:
    for key in elem.attrib:
        if key not in allowed:
            raise Sim3Error("sdf_unsupported_attribute", f"{where}@{key}")
    for key in allowed:
        if key not in elem.attrib:
            raise Sim3Error("sdf_missing_attribute", f"{where}@{key}")


def _text(elem: ET.Element, where: str) -> str:
    if len(elem):
        raise Sim3Error("sdf_unexpected_children", where)
    return (elem.text or "").strip()


def parse_bytes(data: bytes) -> SdfWorld:
    """Parse and validate a world against the profile. Raises Sim3Error."""
    if data[:1] != b"<":
        raise Sim3Error("sdf_not_xml", "does not start with '<'")
    root = _parse_tree(data)

    if root.tag != "sdf":
        raise Sim3Error("sdf_root", root.tag)
    _attrs(root, ("version",), "sdf")
    if root.attrib["version"] != SDF_VERSION:
        raise Sim3Error("sdf_version", root.attrib["version"])
    world_children = _children(root, {"world": (1, 1)}, "sdf")
    world = world_children["world"][0]
    _attrs(world, ("name",), "sdf/world")
    if world.attrib["name"] != WORLD_NAME:
        raise Sim3Error("sdf_world_name", world.attrib["name"])

    wc = _children(
        world,
        {"gravity": (1, 1), "physics": (1, 1), "model": (MIN_MODELS, MAX_MODELS)},
        "world",
    )
    if _text(wc["gravity"][0], "world/gravity") != GRAVITY:
        raise Sim3Error("sdf_gravity", _text(wc["gravity"][0], "world/gravity"))
    _check_physics(wc["physics"][0])

    models = [_model(m) for m in wc["model"]]
    names = [m.name for m in models]
    if len(set(names)) != len(names):
        raise Sim3Error("sdf_duplicate_model_name", ",".join(sorted(names)))
    for m in models:
        if not m.aabb.in_domain():
            raise Sim3Error("sdf_aabb_out_of_domain", f"{m.name}:{m.aabb.as_list()}")

    return SdfWorld(sha256=sha256_bytes(data), n_bytes=len(data), models=models)


def _check_physics(elem: ET.Element) -> None:
    _attrs(elem, ("name", "type"), "world/physics")
    if elem.attrib["type"] != PHYSICS_TYPE:
        raise Sim3Error("sdf_physics_type", elem.attrib["type"])
    pc = _children(elem, {"max_step_size": (1, 1), "real_time_factor": (1, 1)},
                   "world/physics")
    from echoai.nexus0.sim3.geom import mm as _mm

    step = _mm(_text(pc["max_step_size"][0], "max_step_size"), code="sdf_step")
    if step != MAX_STEP_SIZE_MM:
        raise Sim3Error("sdf_max_step_size", str(step))
    if _text(pc["real_time_factor"][0], "real_time_factor") != REAL_TIME_FACTOR:
        raise Sim3Error("sdf_real_time_factor",
                        _text(pc["real_time_factor"][0], "rtf"))


def _model(elem: ET.Element) -> SdfModel:
    _attrs(elem, ("name",), "world/model")
    name = elem.attrib["name"]
    if not (name.startswith("m") and 1 <= len(name) - 1 <= 3
            and name[1:].isdigit() and name[1:].isascii()):
        raise Sim3Error("sdf_model_name", name)
    where = f"world/model[{name}]"
    mc = _children(elem, {"static": (1, 1), "pose": (1, 1), "link": (1, 1)}, where)
    if _text(mc["static"][0], where + "/static") != "true":
        raise Sim3Error("sdf_model_not_static", name)
    pose = pose6(_text(mc["pose"][0], where + "/pose"), code="sdf_pose")

    link = mc["link"][0]
    _attrs(link, ("name",), where + "/link")
    if link.attrib["name"] != LINK_NAME:
        raise Sim3Error("sdf_link_name", link.attrib["name"])
    lc = _children(link, {"collision": (1, 1), "visual": (1, 1)}, where + "/link")

    collision = lc["collision"][0]
    _attrs(collision, ("name",), where + "/link/collision")
    if collision.attrib["name"] != COLLISION_NAME:
        raise Sim3Error("sdf_collision_name", collision.attrib["name"])
    cc = _children(collision, {"geometry": (1, 1)}, where + "/link/collision")
    csize = _box_size(cc["geometry"][0], where + "/link/collision/geometry")

    visual = lc["visual"][0]
    _attrs(visual, ("name",), where + "/link/visual")
    if visual.attrib["name"] != VISUAL_NAME:
        raise Sim3Error("sdf_visual_name", visual.attrib["name"])
    vc = _children(visual, {"geometry": (1, 1), "material": (1, 1)},
                   where + "/link/visual")
    vsize = _box_size(vc["geometry"][0], where + "/link/visual/geometry")
    if vsize != csize:
        raise Sim3Error("sdf_visual_collision_mismatch", f"{name}:{vsize}!={csize}")

    material = vc["material"][0]
    _attrs(material, (), where + "/link/visual/material")
    mat = _children(material, {"ambient": (1, 1), "diffuse": (1, 1)},
                    where + "/link/visual/material")
    ambient = rgba(_text(mat["ambient"][0], "ambient"), code="sdf_ambient")
    diffuse = rgba(_text(mat["diffuse"][0], "diffuse"), code="sdf_diffuse")

    return SdfModel(
        name=name,
        pose_mm=pose,
        size_mm=csize,
        aabb=Aabb.from_pose_size(pose, csize),
        ambient=ambient,
        diffuse=diffuse,
    )


def _box_size(geometry: ET.Element, where: str) -> Vec3:
    _attrs(geometry, (), where)
    gc = _children(geometry, {"box": (1, 1)}, where)
    box = gc["box"][0]
    _attrs(box, (), where + "/box")
    bc = _children(box, {"size": (1, 1)}, where + "/box")
    return triple(_text(bc["size"][0], where + "/box/size"), code="sdf_size")


def parse_file(path: Path) -> SdfWorld:
    return parse_bytes(read_bounded(Path(path), code="sdf"))
