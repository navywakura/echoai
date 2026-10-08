from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS = Path.home() / ".local/share/echo-localdev/tools"
EXCLUDED = {"lab", "old", "echo-discord", "node_modules", "__pycache__", "target",
            "dist", "build", "venv", "env", ".venv", ".git"}
EXTENSIONS = {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".c", ".cpp", ".h", ".rs",
              ".sh", ".md", ".toml", ".cfg", ".ini", ".json", ".yaml", ".yml", ".txt"}
SECRET_NAMES = {"credentials.json", "secrets.json", "kaggle.json"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def sources(root: Path) -> list[Path]:
    result = []
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith(".")
                         and not (Path(folder) / d).is_symlink())
        for name in sorted(names):
            path = Path(folder) / name
            if name.startswith(".") or name in SECRET_NAMES or path.is_symlink():
                continue
            if path.suffix in EXTENSIONS and path.stat().st_size <= 2_000_000:
                # Preserve sealed lab data; documentation corpus answers are not fixtures.
                if path.suffix == ".json" and any(x in name.lower() for x in ("exam", "corpus", "holdout")):
                    continue
                result.append(path)
    return result


def snapshot(root: Path, destination: Path) -> dict[str, str]:
    if destination.exists():
        raise ValueError("snapshot destination already exists")
    destination.mkdir(parents=True)
    receipt = {}
    total = 0
    for path in sources(root):
        data = path.read_bytes()
        total += len(data)
        if total > 150_000_000:
            raise ValueError("source snapshot exceeds 150 MB")
        relative = path.relative_to(root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        receipt[str(relative)] = digest(data)
    return receipt


def frozen_paths(root: Path) -> set[str]:
    result: set[str] = set()
    for family in ("seed", "research"):
        folder = root / "lab" / family
        if not folder.is_dir():
            continue
        for directory in folder.iterdir():
            path = directory / "profile.json"
            if directory.is_symlink() or not path.is_file() or path.stat().st_size > 4_000_000:
                continue
            try:
                value = json.loads(path.read_text()).get("sources", {})
                if isinstance(value, dict):
                    result.update(k for k in value if isinstance(k, str))
            except (ValueError, OSError):
                # A malformed profile must not silently disable custody.
                raise ValueError(f"cannot read frozen profile: {path}")
    return result


def safe_path(root: Path, name: str) -> Path:
    parts = Path(name).parts
    if not parts or Path(name).is_absolute() or any(p in (".", "..") or p.startswith(".") for p in parts):
        raise ValueError("invalid relative source path")
    if any(p in EXCLUDED for p in parts):
        raise ValueError("excluded source path")
    path = root / name
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError("symlink source path")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("source path outside workspace")
    return path
