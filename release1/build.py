"""E4-RELEASE-1 · REL-A build: compiled core + open layer as one wheel.

    python3 echoai/release1/build.py OUT_DIR --nuitka ~/.cache/echoai-release-build/bin/python

1. Stage the audited sources (echoai/echo4, echoai/nexus0, echoai/tests, navi10 core).
2. Check that every staged file pinned by the INTEGRATE-1 exam receipt has the pinned hash.
3. Compile `echoai` (one extension) and each navi10 module with Nuitka (no source shipped).
4. Write the build manifest (source hashes bound to binary hashes) and the evidence index.
5. Assemble a deterministic wheel: binaries + data + open `echoai_release` + contracts + receipts.
The repository is read only; everything is written under OUT_DIR.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECHOAI = HERE.parent
REPO = ECHOAI.parent
VERSION = "4.0.0rc2"
DIST = "echoai"
NAVI = ("echoai.core.cam", "echoai.core.dag", "echoai.core.qn", "echoai.core.spoke", "echoai.core.stdp", "echoai.core.wsp")
PACKAGES = ("echo4", "nexus0", "tests")
DATA_GLOBS = ("nexus0/bank/*.json", "nexus0/*.gbnf", "nexus0/tools/*_cortex.py")  # stub cortices run as scripts (open fixtures)
INTEGRATE_EXAM = ECHOAI / "lab/echo4/integrate1-d-v1"
INTEGRATE_DIGEST = "e1492e22131fc755f3f11bf47c3747edb42640c004fe3be479cd71c2c8952a05"
EVIDENCE_DIRS = ("integrate1-dev-v1",)          # parents the reproduction reads in full
EVIDENCE_REPORTS = ("integrate1-d-v1",)         # sealed report only (artifact digests)
# ECHO-4 milestone receipts (report + audit receipt), in program order.
MILESTONES = (
    ("E4-SENSATION-1", "sensation1-predictor-v1", "sensation_predictive_green"),
    ("E4-BOUNDARY-1", "boundary1-v1", "closure_eligible"),
    ("E4-SELF-1", "self1-final-v1", "self1_green"),
    ("E4-CONTINUITY-1", "continuity1-final-v1", "continuity1_green"),
    ("E4-DREAM-1", "dream1-d-v3", "dream1_green"),
    ("E4-MAINTAIN-1", "maintain1-final-v1", "maintain1_green"),
    ("E4-OTHER-1", "other1-v1", "other1_green"),
    ("E4-INTERACTION-1", "interaction1-bcd-v1", "interaction1_green"),
    ("E4-RELATION-1", "relation1-d-v1", "relation1_green"),
    ("E4-ROLES-1", "roles1-v5-d-v1", "roles1_green"),
    ("E4-ROLES-1 anexo L", "roles1-liar2-d-v1", "liar_annex_green"),
    ("E4-SITUATE-1", "situate1-d-v1", "situate1_green"),
    ("E4-SITUATE-2", "situate2-d-v1", "situate2_green"),
    ("E4-INTEGRATE-1", "integrate1-d-v1", "integrate1_green"),
)
FIXED_TIME = (2026, 9, 24, 0, 0, 0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage(src):
    """Copy the audited sources, without caches, into src/ (repo untouched)."""
    files = {}
    (src / "echoai").mkdir(parents=True)
    shutil.copy2(ECHOAI / "__init__.py", src / "echoai/__init__.py")
    files["echoai/__init__.py"] = sha(ECHOAI / "__init__.py")
    for pkg in PACKAGES:
        for path in sorted((ECHOAI / pkg).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(REPO).as_posix()
            (src / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, src / rel)
            files[rel] = sha(path)
    for name in NAVI:
        shutil.copy2(REPO / (name + ".py"), src / (name + ".py"))
        files[name + ".py"] = sha(REPO / (name + ".py"))
    return files


def main_blocks(src):
    """The top-level `if __name__ == "__main__":` block of each module (CLI glue), as text.

    Compiled modules have no code object for `python -m`; the release hook runs this
    block on top of the compiled module. Nothing else of the core ships as text.
    """
    import ast
    blocks = {}
    for path in sorted(src.rglob("*.py")):
        text = path.read_text()
        for node in ast.parse(text).body:
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                    and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
                rel = path.relative_to(src).with_suffix("")
                name = ".".join(rel.parts)
                blocks[name] = ast.get_source_segment(text, node)
    return blocks


def check_pins(files):
    """Every source pinned by the sealed INTEGRATE exam must be staged with its pinned hash."""
    report = json.loads((INTEGRATE_EXAM / "report.json").read_text())
    if report["reproduction_sha256"] != INTEGRATE_DIGEST:
        raise SystemExit("sealed INTEGRATE report digest mismatch")
    rows, bad = 0, []
    for rel, digest in report["sources"].items():
        key = Path(os.path.normpath("echoai/" + rel)).as_posix()
        if rel.endswith(".py"):
            rows += 1
            if files.get(key) != digest:
                bad.append(key)
        elif sha(ECHOAI / rel) != digest:
            bad.append(rel)
    if bad:
        raise SystemExit("audited sources differ from the sealed pins: " + ", ".join(bad[:10]))
    return {"pinned_py": rows, "pinned_docs": len(report["sources"]) - rows, "mismatches": 0}


def compile_all(src, build, python):
    build.mkdir(parents=True)
    base = [python, "-m", "nuitka", "--nofollow-imports", "--jobs=%d" % max(1, (os.cpu_count() or 2) - 2),
            "--assume-yes-for-downloads", "--quiet", "--output-dir=" + str(build)]
    jobs = [base + ["--module", "echoai", "--include-package=echoai"]]
    jobs += [base + ["--module", name + ".py"] for name in NAVI]
    for argv in jobs:
        log = build / (argv[-1].replace("/", "_") + ".log")
        with log.open("wb") as handle:
            if subprocess.run(argv, cwd=src, stdout=handle, stderr=subprocess.STDOUT).returncode != 0:
                raise SystemExit("nuitka failed: see " + str(log))
    suffix = sysconfig.get_config_var("EXT_SUFFIX")
    binaries = ["echoai" + suffix] + [name + suffix for name in NAVI]
    for b in binaries:
        if not (build / b).is_file():
            raise SystemExit("missing binary " + b)
    return binaries


def evidence_index():
    rows = []
    for name, directory, key in MILESTONES:
        d = ECHOAI / "lab/echo4" / directory
        receipt = json.loads((d / "audit-receipt.json").read_text())
        rows.append({"milestone": name, "directory": "lab/echo4/" + directory,
                     "report_sha256": sha(d / "report.json"),
                     "reproduction_sha256": receipt.get("reproduction_sha256") or receipt.get("certificate") or receipt.get("certificate_sha256"),
                     "valid": receipt.get("valid"),
                     "green": bool(receipt.get(key)) if key else bool(receipt.get("valid")),
                     "green_key": key})
    return rows


def tree(out, build, binaries, files, pins, blocks):
    """The installable tree (what the wheel contains)."""
    root = out / "tree"
    root.mkdir(parents=True)
    for b in binaries:
        shutil.copy2(build / b, root / b)
    data = root / "echoai"
    for pattern in DATA_GLOBS:
        for path in sorted(ECHOAI.glob(pattern)):
            (data / path.relative_to(ECHOAI)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, data / path.relative_to(ECHOAI))
    report = json.loads((INTEGRATE_EXAM / "report.json").read_text())
    for rel in sorted(r for r in report["sources"] if not r.endswith(".py")):
        (data / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ECHOAI / rel, data / rel)
    for directory in EVIDENCE_DIRS:
        shutil.copytree(ECHOAI / "lab/echo4" / directory, data / "lab/echo4" / directory)
    for directory in EVIDENCE_REPORTS:
        (data / "lab/echo4" / directory).mkdir(parents=True)
        for name in ("report.json", "audit-receipt.json"):
            shutil.copy2(ECHOAI / "lab/echo4" / directory / name, data / "lab/echo4" / directory / name)
    receipts = data / "receipts"
    for _, directory, _ in MILESTONES:
        (receipts / directory).mkdir(parents=True, exist_ok=True)
        shutil.copy2(ECHOAI / "lab/echo4" / directory / "audit-receipt.json",
                     receipts / directory / "audit-receipt.json")
    shutil.copytree(HERE / "echoai_release", root / "echoai_release",
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(HERE / "LICENSES", root / "echoai_release" / "LICENSES")
    for extra in ("SYSTEM_CARD.md", "CHANGELOG.md"):
        shutil.copy2(HERE / extra, root / "echoai_release" / extra)
    manifest = {"version": VERSION, "sources": files, "pins": pins, "main_blocks": blocks,
                "binaries": {b: sha(root / b) for b in binaries}, "core_binary": binaries[0],
                "test_modules": sorted("echoai.tests." + Path(k).stem for k in files
                                       if k.startswith("echoai/tests/test_")),
                "python": sys.version.split()[0], "ext_suffix": sysconfig.get_config_var("EXT_SUFFIX")}
    (root / "echoai_release/build_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    (root / "echoai_release/evidence_index.json").write_text(json.dumps(evidence_index(), indent=1))
    (root / "echoai_release.pth").write_text("import echoai_release._hook\n")
    return root, manifest


def wheel(out, root):
    tag = "cp%d%d-cp%d%d-linux_x86_64" % (sys.version_info[:2] * 2)
    name = "%s-%s-%s.whl" % (DIST, VERSION, tag)
    info = "%s-%s.dist-info" % (DIST, VERSION)
    meta = {
        info + "/METADATA": (
            "Metadata-Version: 2.1\nName: %s\nVersion: %s\nSummary: echoAI-4, a cognitive agent whose "
            "core works with the language model off; any LLM can be plugged in as a hypothesis-only cortex.\n"
            "Requires-Python: ==%d.%d.*\nLicense: see echoai_release/LICENSES (open layer PolyForm-Noncommercial-1.0.0; "
            "compiled core proprietary EULA, draft pending legal review)\n\n"
            "Compiled core (Nuitka) plus open release tooling. Not a certification of consciousness.\n"
            % ((DIST, VERSION) + sys.version_info[:2])),
        info + "/WHEEL": "Wheel-Version: 1.0\nGenerator: echoai.release1.build\nRoot-Is-Purelib: false\nTag: %s\n" % tag,
        info + "/entry_points.txt": "[console_scripts]\nechoai = echoai_release.cli:main\n",
        info + "/top_level.txt": "echoai\nechoai_release\n" + "".join(n + "\n" for n in NAVI),
    }
    entries = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        entries[path.relative_to(root).as_posix()] = path.read_bytes()
    for k, v in meta.items():
        entries[k] = v.encode()
    record = io.StringIO()
    writer = csv.writer(record, lineterminator="\n")
    for k in sorted(entries):
        digest = base64.urlsafe_b64encode(hashlib.sha256(entries[k]).digest()).rstrip(b"=").decode()
        writer.writerow([k, "sha256=" + digest, len(entries[k])])
    writer.writerow([info + "/RECORD", "", ""])
    entries[info + "/RECORD"] = record.getvalue().encode()
    path = out / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for k in sorted(entries):
            zi = zipfile.ZipInfo(k, FIXED_TIME)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, entries[k])
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out")
    parser.add_argument("--nuitka", default=sys.executable, help="python that has nuitka installed")
    parser.add_argument("--reuse-build", help="previous OUT_DIR: reuse its binaries if its sources are identical")
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    files = stage(out / "src")
    pins = check_pins(files)
    nuitka = subprocess.run([args.nuitka, "-m", "nuitka", "--version"], capture_output=True, text=True)
    if args.reuse_build:
        prev = Path(args.reuse_build).resolve()
        prev_manifest = json.loads((prev / "tree/echoai_release/build_manifest.json").read_text())
        if prev_manifest["sources"] != files:
            raise SystemExit("cannot reuse: sources differ from the previous build")
        (out / "build").mkdir()
        binaries = sorted(prev_manifest["binaries"], key=lambda b: (not b.startswith("echoai."), b))
        for b in binaries:
            if sha(prev / "tree" / b) != prev_manifest["binaries"][b]:
                raise SystemExit("cannot reuse: previous binary changed: " + b)
            shutil.copy2(prev / "tree" / b, out / "build" / b)
    else:
        binaries = compile_all(out / "src", out / "build", args.nuitka)
    root, manifest = tree(out, out / "build", binaries, files, pins, main_blocks(out / "src"))
    whl = wheel(out, root)
    receipt = {"schema": "e4-release1-build-v1", "version": VERSION, "wheel": whl.name,
               "wheel_sha256": sha(whl), "wheel_bytes": whl.stat().st_size,
               "sources": len(files), "pins": pins, "binaries": manifest["binaries"],
               "nuitka": nuitka.stdout.splitlines()[:1], "python": sys.version.split()[0],
               "compiler": subprocess.run(["gcc", "--version"], capture_output=True, text=True).stdout.splitlines()[0],
               "source_shipped": False, "reused_binaries_from": args.reuse_build}
    (out / "build-receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True))
    shutil.rmtree(out / "src")
    print(json.dumps(receipt, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
