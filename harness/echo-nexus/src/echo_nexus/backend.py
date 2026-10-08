"""Public process boundary: read operator manifests, never import ECHO source."""
from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

MAX_LINE = 2_000_000


def read_manifest(path):
    file = Path(path).expanduser().resolve()
    if file.stat().st_size > MAX_LINE:
        raise ValueError("Manifiesto demasiado grande")
    manifest = json.loads(file.read_text())
    if not isinstance(manifest, dict) or manifest.get("schema") != "echo-nexus-backend-v1":
        raise ValueError("Se esperaba schema echo-nexus-backend-v1")
    if not isinstance(manifest.get("tests", []), list):
        raise ValueError("tests debe ser una lista")
    validate_tests(manifest.get("tests", []))
    validate_tests(manifest.get("worlds", []))
    agents = manifest.get("agents", [])
    if not isinstance(agents, list):
        raise ValueError("agents debe ser una lista")
    names = set()
    for agent in agents:
        if not isinstance(agent, dict) or not isinstance(agent.get("id"), str) or agent["id"] in names:
            raise ValueError("Agentes sin identificador único")
        names.add(agent["id"])
        validate_tests(agent.get("tests", []))
        validate_tests(agent.get("worlds", []))
    if manifest.get("default_agent") and manifest["default_agent"] not in names:
        raise ValueError("Agente predeterminado no anunciado")
    return manifest


def validate_tests(tests):
    if not isinstance(tests, list):
        raise ValueError("tests debe ser una lista")
    ids = set()
    for test in tests:
        if not isinstance(test, dict):
            raise ValueError("Cada test debe ser un objeto")
        ident = test.get("id")
        if not isinstance(ident, str) or not ident or ident in ids:
            raise ValueError("Los tests necesitan identificadores únicos")
        ids.add(ident)
        if test.get("kind") not in ("development", "evidence", "sealed"):
            raise ValueError("Tipo de test desconocido")
        argv = test.get("argv", [])
        if test["kind"] == "development" and (not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv)):
            raise ValueError("Un test de desarrollo necesita argv como lista")
        if test.get("cwd") and not Path(test["cwd"]).is_absolute():
            raise ValueError("cwd debe ser una ruta absoluta")
        if not 1 <= int(test.get("timeout", 120)) <= 3600:
            raise ValueError("timeout fuera de 1..3600 segundos")


class Runner:
    def __init__(self):
        self.process = None
        self.cancelled = False

    async def run(self, test, emit, *, continuous=False):
        if test.get("kind") != "development":
            raise ValueError("El arnés no ejecuta exámenes sellados ni informes archivados")
        if self.process is not None:
            raise RuntimeError("Ya hay una prueba activa")
        self.cancelled = False
        options = {"start_new_session": True} if os.name == "posix" else {}
        self.process = await asyncio.create_subprocess_exec(*test["argv"], cwd=test.get("cwd"),
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT, limit=MAX_LINE, **options)
        async def stream():
            while line := await self.process.stdout.readline():
                value = line.decode("utf-8", errors="replace").rstrip()
                try:
                    obj = json.loads(value)
                except ValueError:
                    obj = {"kind": "output", "text": value}
                emit(obj if isinstance(obj, dict) else {"kind": "output", "text": value})
            return await self.process.wait()
        try:
            code = await stream() if continuous else await asyncio.wait_for(stream(), timeout=test.get("timeout", 120))
            if self.cancelled:
                emit({"kind": "cancelled", "test": test["id"]})
                return -1
            emit({"kind": "process_end", "test": test["id"], "exit_code": code})
            return code
        except BaseException:
            await self.stop()
            raise
        finally:
            self.process = None

    async def stop(self):
        self.cancelled = True
        p = self.process
        if p is None:
            return
        try:
            os.killpg(p.pid, signal.SIGTERM) if os.name == "posix" else p.terminate()
            await asyncio.wait_for(p.wait(), 3)
        except asyncio.TimeoutError:
            os.killpg(p.pid, signal.SIGKILL) if os.name == "posix" else p.kill()
            await p.wait()
        except ProcessLookupError:
            pass


class Tail:
    """Incremental read-only JSONL tail. Partial writes and rotations are safe."""
    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        if not self.path.is_file():
            raise ValueError("El registro no existe")
        self.offset = 0
        self.identity = None
        self.pending = b""

    def read(self):
        stat = self.path.stat()
        identity = (stat.st_dev, stat.st_ino)
        if identity != self.identity or stat.st_size < self.offset:
            self.offset, self.pending, self.identity = 0, b"", identity
        with self.path.open("rb") as f:
            f.seek(self.offset)
            block = f.read(MAX_LINE)
            self.offset = f.tell()
        lines = (self.pending + block).split(b"\n")
        self.pending = lines.pop()
        if len(self.pending) > MAX_LINE:
            self.pending = b""
            raise ValueError("Línea JSONL demasiado grande")
        result = []
        for line in lines:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except ValueError:
                result.append({"kind": "output", "text": "Línea no JSON en el registro"})
                continue
            if isinstance(item, dict):
                result.append(item)
        return result


def demo_test():
    return {"id": "demo", "title": "Demo del visor · camino sintético, no ECHO", "kind": "development",
            "argv": [sys.executable, "-m", "echo_nexus.demo"], "timeout": 20}
