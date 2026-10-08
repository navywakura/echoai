"""Chain of custody for a built asset: declaration -> mesh -> receipt.

The defect this module exists to make impossible: ``build_world.py`` used to
write its receipt to ``out/<name>.json``.  When the input declaration had the
same name and lived in the same directory, **the receipt overwrote the source**
— which is what happened to ``lab/metaverse1/worlds/wide-3x2.json`` on
2026-09-20.  The mesh survived; the proof of what produced it did not.

So the three artefacts now have three fixed, different names:

    <world>.declaration.json    the immutable source
    <world>.glb                 the visual result
    <world>.build-receipt.json  tool, parameters and hashes

and every rule that keeps them apart is enforced here, not in the Blender
driver.  This module imports **nothing** outside the standard library: it is
imported from inside Blender's interpreter and from the test suite alike, and
the asset pipeline must never be able to pull echoAI into a renderer.

None of this is physics, evidence or a certificate.  It is geometry with a
paper trail.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import struct
from pathlib import Path
from typing import Callable, Optional

RECEIPT_SCHEMA = "echoai-metaverse1-build-receipt-v1"
DECLARATION_SUFFIX = ".declaration.json"
MESH_SUFFIX = ".glb"
RECEIPT_SUFFIX = ".build-receipt.json"

_GLB_MAGIC = 0x46546C67          # 'glTF'
_GLB_JSON_CHUNK = 0x4E4F534A     # 'JSON'


class CustodyError(Exception):
    """A rule that keeps source, artefact and receipt apart was broken."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


class BuildPaths:
    """The three paths of one build, already proven distinct."""

    def __init__(self, declaration: Path, mesh: Path, receipt: Path):
        self.declaration = declaration
        self.mesh = mesh
        self.receipt = receipt

    def as_dict(self) -> dict:
        return {"declaration": str(self.declaration), "mesh": str(self.mesh),
                "receipt": str(self.receipt)}


def plan(declaration: Path, out_dir: Path, name: str,
         *, overwrite: bool = False) -> BuildPaths:
    """Resolve the three paths and refuse every way they could collide."""
    source = Path(declaration).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    if not name or "/" in name or name in (".", ".."):
        raise CustodyError(f"unusable world name: {name!r}")
    if not source.is_file():
        raise CustodyError(f"declaration is not a file: {source}")

    mesh = out / f"{name}{MESH_SUFFIX}"
    receipt = out / f"{name}{RECEIPT_SUFFIX}"

    # The whole point.  Three artefacts, three paths, no exceptions — and the
    # source is never one of the outputs.
    if len({source, mesh, receipt}) != 3:
        raise CustodyError(
            "declaration, mesh and receipt must be three different paths; got "
            f"{source}, {mesh}, {receipt}")

    if not overwrite:
        for existing in (mesh, receipt):
            if existing.exists():
                raise CustodyError(
                    f"refusing to overwrite an existing artefact: {existing} "
                    "(pass --overwrite, and the receipt will record what was "
                    "there before)")
    return BuildPaths(source, mesh, receipt)


def previous_artefacts(paths: BuildPaths) -> dict:
    """Hash whatever is about to be replaced, so nothing is lost silently."""
    record = {}
    for label, path in (("mesh", paths.mesh), ("receipt", paths.receipt)):
        if path.exists():
            record[label] = {"path": str(path), "sha256": sha256_file(path)}
    return record


def inspect_glb(path: Path) -> dict:
    """Read the GLB container without Blender.

    Checking the magic, the version, the declared length and the JSON chunk is
    enough to say the file is a well-formed glTF binary rather than a truncated
    write.  A headless re-import in Blender is the stronger check and the build
    does that too; this one runs everywhere, including in the tests.
    """
    path = Path(path)
    if not path.is_file():
        return {"ok": False, "reason": "mesh file does not exist"}
    size = path.stat().st_size
    if size < 20:
        return {"ok": False, "reason": f"mesh is too small to be a GLB ({size} B)"}
    raw = path.read_bytes()
    magic, version, declared = struct.unpack_from("<III", raw, 0)
    if magic != _GLB_MAGIC:
        return {"ok": False, "reason": "missing glTF magic"}
    if version != 2:
        return {"ok": False, "reason": f"unexpected glTF version {version}"}
    if declared != size:
        return {"ok": False,
                "reason": f"declared length {declared} != file size {size}"}
    chunk_len, chunk_type = struct.unpack_from("<II", raw, 12)
    if chunk_type != _GLB_JSON_CHUNK:
        return {"ok": False, "reason": "first chunk is not JSON"}
    try:
        document = json.loads(raw[20:20 + chunk_len].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"ok": False, "reason": f"JSON chunk does not parse: {error}"}
    if "asset" not in document:
        return {"ok": False, "reason": "glTF document has no asset block"}
    return {"ok": True, "bytes": size,
            "generator": document.get("asset", {}).get("generator"),
            "meshes": len(document.get("meshes", [])),
            "nodes": len(document.get("nodes", []))}


def build(paths: BuildPaths, export: Callable[[Path], None], *,
          tool: str, parameters: dict, note: Optional[str] = None,
          reconstruction: Optional[dict] = None,
          extra_validation: Optional[Callable[[Path], dict]] = None) -> dict:
    """Run ``export``, then write the receipt — in that order, and only then.

    ``export`` receives the mesh path.  If it raises, or if it leaves no
    well-formed GLB behind, **no receipt is written at all**: a failed build
    must not leave a green-looking receipt for someone to trust later.
    """
    source_sha = sha256_file(paths.declaration)
    replaced = previous_artefacts(paths)

    export(paths.mesh)

    validation = inspect_glb(paths.mesh)
    if extra_validation is not None and validation.get("ok"):
        # Only worth running once the container itself reads back; it is the
        # caller's stronger check (Blender re-importing what Blender wrote).
        extra = extra_validation(paths.mesh)
        validation = {**validation, **extra,
                      "ok": bool(validation["ok"]) and bool(extra.get("ok"))}
    if not validation.get("ok"):
        raise CustodyError(
            f"export produced no usable mesh: {validation.get('reason')}")

    after_sha = sha256_file(paths.declaration)
    if after_sha != source_sha:
        # Belt and braces.  plan() already made this impossible; if it happens
        # anyway the build is not trustworthy and must not be recorded.
        raise CustodyError("the declaration changed during the build")

    payload = {
        "schema": RECEIPT_SCHEMA,
        "created": _dt.datetime.now(_dt.timezone.utc)
                      .replace(microsecond=0).isoformat(),
        "tool": tool,
        "parameters": parameters,
        "declaration": {"path": str(paths.declaration), "sha256": source_sha},
        "mesh": {"path": str(paths.mesh), "sha256": sha256_file(paths.mesh)},
        "receipt_path": str(paths.receipt),
        "validation": validation,
        "replaced": replaced,
        "note": note or ("Recibo de construcción. Geometría, no física: nada "
                         "de esto es evidencia ni certificado."),
    }
    if reconstruction is not None:
        payload["reconstruction"] = reconstruction

    paths.receipt.parent.mkdir(parents=True, exist_ok=True)
    paths.receipt.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")
    return payload


def verify(receipt_path: Path) -> dict:
    """Re-read a receipt and check every claim it makes against the disk."""
    receipt_path = Path(receipt_path).expanduser().resolve()
    problems: list[str] = []
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))

    if payload.get("schema") != RECEIPT_SCHEMA:
        problems.append(f"unexpected schema {payload.get('schema')!r}")

    declaration = Path(payload.get("declaration", {}).get("path", ""))
    mesh = Path(payload.get("mesh", {}).get("path", ""))

    # A receipt that points at itself is exactly the bug that lost wide-3x2.
    if declaration == receipt_path:
        problems.append("the receipt claims to be its own declaration")
    if mesh == receipt_path:
        problems.append("the receipt claims to be its own mesh")
    if declaration == mesh:
        problems.append("declaration and mesh are the same path")

    for label in ("declaration", "mesh"):
        path = Path(payload.get(label, {}).get("path", ""))
        claimed = payload.get(label, {}).get("sha256")
        if not path.is_file():
            problems.append(f"{label} is missing: {path}")
        elif sha256_file(path) != claimed:
            problems.append(f"{label} hash does not match: {path}")

    if not payload.get("validation", {}).get("ok"):
        problems.append("receipt records a failed validation")

    return {"ok": not problems, "problems": problems, "receipt": payload}
