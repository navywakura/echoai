"""Release identity: the compiled core has no source files to hash.

In the lab, ECHO knows which program it is by hashing its own source (SITUATE,
CONTINUITY) and the benches pin their sources the same way. The compiled
distribution ships binaries instead. Its identity is the build manifest: the
SHA-256 of every audited source file, bound to the SHA-256 of every compiled
binary. At activation the binaries are hashed; if any differs, no identity is
granted and every identity-dependent read fails closed (FileNotFoundError), as
it would with a missing source. Sealed code is not modified: only the hashing
functions are redirected, and only for files that are absent and listed.
"""
import hashlib
import importlib.util
import json
import sys
from importlib import resources
from pathlib import Path

MANIFEST_NAME = "build_manifest.json"
_state = {"active": False, "manifest": None, "site": None, "binaries_ok": None,
          "mismatch": [], "virtual_reads": 0}


def manifest():
    if _state["manifest"] is None:
        _state["manifest"] = json.loads(resources.files(__package__).joinpath(MANIFEST_NAME).read_text())
    return _state["manifest"]


def real_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def site():
    if _state["site"] is None:
        spec = importlib.util.find_spec("echoai")
        origin = Path(spec.origin).resolve()
        # A compiled package reports .../echoai/__init__.py; the binary sits beside that folder.
        _state["site"] = origin.parent.parent if origin.name == "__init__.py" else origin.parent
    return _state["site"]


def check_binaries():
    bad = []
    for rel, digest in manifest()["binaries"].items():
        path = site() / rel
        if not path.is_file() or real_hash(path) != digest:
            bad.append(rel)
    return bad


def virtual_hash(path):
    """Real hash if the file exists; the manifest hash for an absent audited source."""
    path = Path(path)
    if path.exists():
        return real_hash(path)
    if _state["binaries_ok"]:
        try:
            rel = Path(*path.resolve().parts).relative_to(site()).as_posix()
        except ValueError:
            rel = None
        digest = manifest()["sources"].get(rel) if rel else None
        if digest is not None:
            _state["virtual_reads"] += 1
            return digest
    raise FileNotFoundError(str(path))


def _self_source_factory(situate):
    def self_source(root=None):
        root = Path(situate.ROOT if root is None else root)
        h = hashlib.sha256()
        for rel in situate.SELF_FILES:
            h.update(rel.encode() + b"\0" + bytes.fromhex(virtual_hash(root / rel)))
        return h.hexdigest()
    return self_source


def activate():
    """Called once, right after `echoai` is imported (see _hook)."""
    if _state["active"]:
        return status()
    _state["active"] = True
    _state["mismatch"] = check_binaries()
    _state["binaries_ok"] = not _state["mismatch"]
    if not _state["binaries_ok"]:
        return status()   # another program: no identity, identity reads fail closed
    from echoai.echo4 import continuity_final_audit as cfa, self_final_audit as sfa
    from echoai.echo4 import situate as S, continuity as C, continuity_active as CA
    from echoai.echo4 import continuity_lineage as CL, maintain_continuity as MC
    swaps = {}

    def file_hash(path):
        return virtual_hash(path)
    swaps[cfa.file_hash] = file_hash
    swaps[sfa.file_hash] = file_hash
    swaps[S.self_source] = _self_source_factory(S)

    def c_sources():
        return {name: virtual_hash(C.ROOT / name) for name in C.SOURCES}
    swaps[C.source_hashes] = c_sources

    def ca_sources():
        return {**CA.base.source_hashes(), **{p: virtual_hash(CA.ROOT / p) for p in CA.EXTRA_SOURCES}}
    swaps[CA.source_hashes] = ca_sources

    def cl_sources():
        return {**CL.b.source_hashes(),
                "echo4/continuity_lineage.py": virtual_hash(CL.b.ROOT / "echo4/continuity_lineage.py")}
    swaps[CL.source_hashes] = cl_sources

    mc_original = MC.source_hashes
    def mc_sources():
        extra = ("echo4/continuity_graph.py", "echo4/maintain_world.py", "echo4/maintain_agent.py",
                 "echo4/maintain_model.py", "echo4/maintain_control.py", "echo4/maintain_continuity.py",
                 "echo4/self_attribution.py")
        return {**MC.base.source_hashes(), **{p: virtual_hash(MC.base.ROOT / p) for p in extra}}
    swaps[mc_original] = mc_sources

    # CONTINUITY benches in the custody chain of later phases (found by instrumenting
    # integrate_exam.sources() in source mode): same composition, virtual hashes.
    from echoai.echo4 import continuity_bench as CB, continuity_active_bench as CAB
    from echoai.echo4 import continuity_lineage_bench as CLB

    def cb_sources():
        extra = ("echo4/continuity_bench.py", "echo4/boundary_world.py",
                 "tests/test_echo4_continuity1.py", "docs/ECHO4-CONTINUITY1-DESIGN.md")
        return {**CB.source_hashes(), **{name: virtual_hash(CB.ROOT / name) for name in extra}}
    swaps[CB.bench_sources] = cb_sources

    def cab_sources():
        extras = ("echo4/continuity_active_bench.py", "echo4/self_probe_world.py",
                  "echo4/boundary_world.py", "echo4/self_recovery_audit.py", "echo4/self_reuse_audit.py",
                  "tests/test_echo4_continuity1b.py", "docs/ECHO4-CONTINUITY1-B-DESIGN.md")
        return {**CAB.c.source_hashes(), **{p: virtual_hash(CAB.c.ROOT / p) for p in extras}}
    swaps[CAB.sources] = cab_sources

    def clb_sources():
        extras = ("echo4/continuity_lineage_bench.py", "tests/test_echo4_continuity1c.py",
                  "docs/ECHO4-CONTINUITY1-C-DESIGN.md")
        return {**CLB.previous.sources(), **CLB.c.source_hashes(),
                **{p: virtual_hash(CLB.c.b.ROOT / p) for p in extras}}
    swaps[CLB.sources] = clb_sources
    # Older benches (BOUNDARY, SELF, SENSATION) hash sources inline inside their
    # own sources(): their custody is reproduced from source only (declared).
    _sweep(swaps)
    return status()


def _sweep(swaps):
    """Replace every binding of an original function, in every loaded echoai module."""
    for name, module in list(sys.modules.items()):
        if not (name == "echoai" or name.startswith("echoai.")) or module is None:
            continue
        for attr, value in list(vars(module).items()):
            try:
                replacement = swaps.get(value)
            except TypeError:
                continue
            if replacement is not None:
                setattr(module, attr, replacement)


def status():
    m = _state["manifest"] or {}
    return {"active": _state["active"], "binaries_ok": _state["binaries_ok"],
            "mismatch": list(_state["mismatch"]), "version": m.get("version"),
            "sources": len(m.get("sources", {})), "binaries": sorted(m.get("binaries", {})),
            "virtual_reads": _state["virtual_reads"]}
