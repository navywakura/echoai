"""Offline development setup and checks, using only the Python standard library."""

import ast
import json
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".venv"
PIN = (ROOT / ".python-version").read_text().strip()


def check_environment():
    if not sys.flags.isolated:
        raise RuntimeError('Ejecuta Python con -I para excluir rutas y paquetes externos')
    if platform.python_version() != PIN:
        raise RuntimeError(f"Python requerido: {PIN}; actual: {platform.python_version()}")
    if Path(sys.prefix).resolve() != ENV.resolve() or sys.prefix == sys.base_prefix:
        raise RuntimeError("Usa la .venv de ECHO-5: ejecuta make setup y make check")
    config = (ENV / "pyvenv.cfg").read_text().lower()
    if "include-system-site-packages = false" not in config:
        raise RuntimeError("El entorno debe excluir paquetes globales")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    if project["tool"]["echo5"]["python-version"] != PIN:
        raise RuntimeError("El pin de Python no coincide con pyproject.toml")
    files = sorted(p for folder in ("src", "scripts", "tests")
                   for p in (ROOT / folder).rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(), filename=str(path))
    return {"stage": project["tool"]["echo5"]["stage"], "python": platform.python_version(),
            "environment": str(ENV), "syntax_files": len(files),
            "checks": ["pinned isolated environment", "Python syntax"],
            "capabilities_validated": False}


def main():
    command = sys.argv[1:] or ["check"]
    if command == ["setup"]:
        if platform.python_version() != PIN:
            raise RuntimeError(f"Setup requiere Python {PIN}")
        if ENV.is_symlink():
            raise RuntimeError(".venv no puede enlazar otro entorno")
        if not ENV.exists():
            venv.EnvBuilder(with_pip=False, system_site_packages=False).create(ENV)
        return subprocess.call([str(ENV / "bin" / "python"), "-I", __file__, "check"])
    if command not in (["check"], ["test"]):
        raise RuntimeError("Uso: dev.py setup|check|test")
    report = check_environment()
    if command == ["check"]:
        print(json.dumps(report, indent=2))
        return 0
    # Make the development namespace available without importing the parent project.
    sys.path.insert(0, str(ROOT / "src"))
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    if suite.countTestCases() == 0:
        print("SIN PRUEBAS: setup inicial; no hay capacidades ECHO-5 validadas.")
        return 2
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, SyntaxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
