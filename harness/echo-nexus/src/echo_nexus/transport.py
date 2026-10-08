"""Optional neocortex and MCP transports. Never invoke tools from model text."""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import tempfile
import urllib.parse
from pathlib import Path

import httpx

from .config import state_dir, register_secret, redact


def endpoint(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if parts.username or parts.password or parts.query or parts.fragment or not parts.hostname:
        raise ValueError("Usa una URL base sin credenciales, parámetros ni fragmento")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost", "::1")):
        raise ValueError("La API necesita HTTPS; HTTP solo se permite en localhost")
    base = url.rstrip("/")
    if parts.hostname == "openrouter.ai":
        if parts.scheme != "https":
            raise ValueError("OpenRouter requiere HTTPS")
        if parts.path.rstrip("/") in ("", "/api", "/api/v1", "/api/v1/chat/completions"):
            return "https://openrouter.ai/api/v1"
    return base


async def model_catalog(url="https://openrouter.ai/api/v1", *, free_only=True):
    """Public discovery. No credential is opened or sent to the model catalog."""
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False) as client:
            response = await client.get(endpoint(url) + "/models")
            response.raise_for_status()
            if len(response.content) > 8_000_000:
                raise ValueError("Catálogo demasiado grande")
            rows = response.json().get("data", [])
    except httpx.HTTPError:
        raise RuntimeError("No se pudo consultar el catálogo HTTPS. Revisa la red y usa /models free para reintentar.") from None
    def free(row):
        try:
            price = row["pricing"]
            return float(price["prompt"]) == 0 and float(price["completion"]) == 0
        except (KeyError, ValueError, TypeError):
            return False
    return [r for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)
            and (not free_only or free(r))]


def api_error(status, payload=None, retry_after=None):
    """Provider metadata and raw bodies may contain prompts or credentials."""
    error = payload.get("error", {}) if isinstance(payload, dict) else {}
    message = error.get("message", "") if isinstance(error, dict) else ""
    detail = redact(message)[:350] if isinstance(message, str) else ""
    advice = {401: "Comprueba el archivo o variable de clave.",
              402: "La cuenta o clave no tiene saldo para esta solicitud.",
              403: "Revisa los permisos y filtros del proveedor.",
              404: "Modelo o endpoint no disponible. /models free; /connect openrouter free.",
              429: "Límite temporal del proveedor; espera antes de reintentar.",
              503: "No hay proveedor disponible para esta petición."}.get(status, "Revisa URL y modelo.")
    if retry_after and str(retry_after).isdigit():
        advice += f" Reintento recomendado en {retry_after} s."
    return f"API HTTP {status}" + (" · " + detail if detail else "") + "\n" + advice


SYSTEM = ("Eres el neocórtex lingüístico opcional de echo-nexus. Tus respuestas son propuestas, "
          "no hechos verificados por ECHO. No afirmes haber ejecutado pruebas, observado neuronas "
          "o cambiado el motor. No tienes herramientas ni acceso automático a archivos. "
          "Explica de forma concisa y separa observaciones proporcionadas e hipótesis.")


class Cortex:
    def __init__(self, url: str, model: str, key_env: str | None = None, protocol="openai", *, key_file=None, timeout=90, max_tokens=1024):
        self.url = endpoint(url)
        if not model or protocol not in ("openai", "anthropic"):
            raise ValueError("Modelo o protocolo no válido")
        if key_env and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_env):
            raise ValueError("Indica el NOMBRE de una variable de entorno, no la clave")
        if key_env and key_file:
            raise ValueError("Elige una variable o un archivo de clave")
        self.key_file = str(Path(key_file).expanduser().resolve()) if key_file else None
        self.timeout, self.max_tokens = timeout, max_tokens
        self.model, self.key_env, self.protocol = model, key_env, protocol
        self.history = []

    async def ask(self, prompt, *, progress=None, on_delta=None):
        if progress:
            progress("Preparando solicitud")
        headers = {"Content-Type": "application/json"}
        key = os.getenv(self.key_env, "") if self.key_env else ""
        if self.key_env and not key:
            raise ValueError(f"Falta la variable de entorno {self.key_env}")
        if self.key_file:
            try:
                with Path(self.key_file).open() as source:
                    key = source.read(16385).strip()
            except OSError:
                raise ValueError("No se puede abrir el archivo de clave configurado") from None
            if len(key) > 16384 or not key or "\n" in key or "\r" in key:
                raise ValueError("El archivo de clave debe contener una sola clave o asignación")
            # Parse a single assignment without ever executing shell syntax.
            assignment = re.fullmatch(r"(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=\s*(.*)", key)
            if assignment:
                key = assignment[1].strip()
            if len(key) > 1 and key[0] in ("'", '"') and key[-1] == key[0]:
                key = key[1:-1]
            if not key or any(c.isspace() for c in key):
                raise ValueError("Formato de archivo de clave no válido")
        register_secret(key)
        history = self.history[-10:] + [{"role": "user", "content": prompt[:24000]}]
        if self.protocol == "anthropic":
            if key:
                headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
            body = {"model": self.model, "system": SYSTEM, "messages": history, "max_tokens": self.max_tokens, "stream": bool(on_delta)}
            route = "/messages"
        else:
            if key:
                headers["Authorization"] = "Bearer " + key
            body = {"model": self.model, "messages": [{"role": "system", "content": SYSTEM}] + history,
                    "stream": bool(on_delta), "max_tokens": self.max_tokens}
            route = "/chat/completions"
        if progress:
            progress("Solicitud enviada · esperando al modelo")
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False, trust_env=False) as client:
                async with client.stream("POST", self.url + route, json=body, headers=headers) as response:
                    if not 200 <= response.status_code < 300:
                        data = bytearray()
                        async for chunk in response.aiter_bytes():
                            data.extend(chunk)
                            if len(data) > 32768:
                                break
                        try:
                            payload = json.loads(data) if len(data) <= 32768 else {}
                        except ValueError:
                            payload = {}
                        raise RuntimeError(api_error(response.status_code, payload, response.headers.get("Retry-After")))
                    if "text/event-stream" in response.headers.get("content-type", ""):
                        text = await public_stream(response, self.protocol, on_delta, progress)
                    else:
                        raw = bytearray()
                        async for chunk in response.aiter_bytes():
                            raw.extend(chunk)
                            if len(raw) > 2_000_000:
                                raise ValueError("Respuesta demasiado grande")
                        result = json.loads(raw)
                        if result.get("error"):
                            raise RuntimeError(api_error(response.status_code, result))
                        if self.protocol == "anthropic":
                            text = "\n".join(p.get("text", "") for p in result.get("content", []) if p.get("type") == "text")
                        else:
                            text = result["choices"][0]["message"].get("content")
                        if on_delta and isinstance(text, str):
                            if progress:
                                progress("Respuesta recibida")
                            on_delta(text)
        except httpx.HTTPError:
            raise RuntimeError("No se pudo conectar con la API; revisa red, URL y tiempo de espera") from None
        if not isinstance(text, str) or not text.strip():
            raise ValueError("El proveedor no devolvió texto público. Puede haber agotado el presupuesto de salida "
                             "en razonamiento o solicitado herramientas. Prueba otro modelo con /models free; "
                             "este conector no ejecuta tool calls.")
        self.history = (history + [{"role": "assistant", "content": text[:24000]}])[-12:]
        if progress:
            progress("Respuesta completada")
        return text


async def public_stream(response, protocol, on_delta, progress):
    """Render only public answer deltas; ignore provider reasoning and tool events."""
    fragments, data = [], []
    size, done = 0, False
    async for line in response.aiter_lines():
        size += len(line.encode("utf-8"))
        if size > 2_000_000:
            raise ValueError("Respuesta demasiado grande")
        if line.startswith("data:"):
            data.append(line[5:].lstrip())
        elif not line and data:
            payload = "\n".join(data)
            data = []
            if payload == "[DONE]":
                done = True
                break
            event = json.loads(payload)
            if event.get("error") or event.get("type") == "error":
                raise RuntimeError("El proveedor interrumpió la generación; consulta su estado")
            if protocol == "anthropic":
                if event.get("type") == "message_stop":
                    done = True
                    break
                delta = event.get("delta", {})
                chunk = delta.get("text", "") if delta.get("type") == "text_delta" else ""
            else:
                choices = event.get("choices", [])
                chunk = choices[0].get("delta", {}).get("content", "") if choices else ""
            if isinstance(chunk, str) and chunk:
                if not fragments and progress:
                    progress("Generando respuesta · texto recibido")
                fragments.append(chunk)
                if on_delta:
                    on_delta(chunk)
    if not done:
        raise RuntimeError("La respuesta se interrumpió antes de completarse; vuelve a intentarlo")
    return "".join(fragments)

class LocalModel:
    def __init__(self):
        self.process = None
        self.log = None

    async def start(self, path, *, server=None, progress=None, timeout=300):
        file = Path(path).expanduser().resolve()
        if not file.is_file() or file.suffix.lower() != ".gguf":
            raise ValueError("Indica un archivo .gguf existente")
        with file.open("rb") as f:
            if f.read(4) != b"GGUF":
                raise ValueError("El archivo no tiene la cabecera GGUF")
        binary = shutil.which(server or os.getenv("ECHO_NEXUS_LLAMA_SERVER", "llama-server"))
        if not binary:
            raise ValueError("Instala llama-server para cargar modelos GGUF")
        await self.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        root = state_dir()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.log_path = root / f"llama-{os.getpid()}-{time.time_ns()}.log"
        self.log = os.fdopen(os.open(self.log_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w")
        # Zero GPU layers alone still permits HIP/CUDA host-operation offload.
        child_env = dict(os.environ, HIP_VISIBLE_DEVICES="", ROCR_VISIBLE_DEVICES="", CUDA_VISIBLE_DEVICES="")
        self.process = await asyncio.create_subprocess_exec(
            binary, "--model", str(file), "--alias", "echo-local", "--host", "127.0.0.1", "--port", str(port),
            "--ctx-size", "2048", "--threads", "4", "--threads-batch", "4",
            "--batch-size", "256", "--ubatch-size", "64", "--n-gpu-layers", "0",
            "--device", "none", "--no-op-offload", env=child_env, stdout=self.log, stderr=self.log)
        started = time.monotonic()
        next_notice = 0
        try:
            async with httpx.AsyncClient(timeout=1, trust_env=False) as client:
                while time.monotonic() - started < timeout:
                    elapsed = time.monotonic() - started
                    if self.process.returncode is not None:
                        code = self.process.returncode
                        detail = f"señal {-code}" if code < 0 else f"código {code}"
                        raise RuntimeError(f"llama-server terminó ({detail}); consulta {self.log_path}")
                    if progress and elapsed >= next_notice:
                        progress(f"CPU · cargando {elapsed:.0f} s / {timeout} s · log: {self.log_path}")
                        next_notice = elapsed + 10
                    try:
                        response = await client.get(f"http://127.0.0.1:{port}/health")
                        if response.status_code == 200:
                            if progress:
                                progress(f"Modelo listo en {time.monotonic() - started:.1f} s · CPU")
                            return Cortex(f"http://127.0.0.1:{port}/v1", "echo-local", timeout=300, max_tokens=256)
                    except httpx.HTTPError:
                        pass
                    await asyncio.sleep(1)
            raise TimeoutError(f"Carga GGUF agotó {timeout} s; consulta {self.log_path}")
        except BaseException:
            await self.close()
            raise

    async def close(self):
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), 4)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.log:
            self.log.close()
        self.process = self.log = None


class MCP:
    """MCP stdio client; tool execution requires an explicit operator command."""
    def __init__(self):
        self.process = None
        self.next_id = 0
        self.lock = asyncio.Lock()
        self.tools = []

    async def connect(self, argv: list[str], cwd=None):
        if not argv:
            raise ValueError("Falta el comando MCP")
        self.process = await asyncio.create_subprocess_exec(*argv, cwd=cwd, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, limit=2_000_000,
            **({"start_new_session": True} if os.name == "posix" else {}))
        try:
            result = await self.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "echo-nexus", "version": "1.5.1"}})
            if result.get("protocolVersion") not in ("2025-06-18", "2025-03-26", "2024-11-05", "2025-11-25"):
                raise ValueError("Versión MCP no compatible")
            self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            cursor = None
            for _ in range(20):
                page = await self.request("tools/list", {"cursor": cursor} if cursor else {})
                self.tools.extend(page.get("tools", []))
                cursor = page.get("nextCursor")
                if not cursor:
                    break
            else:
                raise ValueError("El catálogo MCP excede 20 páginas")
            return result
        except BaseException:
            await self.close()
            raise

    def send(self, message):
        self.process.stdin.write((json.dumps(message, ensure_ascii=False) + "\n").encode())

    async def request(self, method, params, timeout=30):
        async with self.lock:
            self.next_id += 1
            mid = self.next_id
            self.send({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
            await self.process.stdin.drain()
            async def receive():
                while True:
                    line = await self.process.stdout.readline()
                    if not line:
                        raise RuntimeError("El servidor MCP cerró la conexión")
                    response = json.loads(line)
                    if "method" in response and "id" in response:
                        self.send({"jsonrpc": "2.0", "id": response["id"], "error": {
                            "code": -32601, "message": "Client capabilities not supported"}})
                    elif response.get("id") == mid:
                        if "error" in response:
                            raise RuntimeError("MCP: " + str(response["error"].get("message", "error")))
                        return response.get("result", {})
            return await asyncio.wait_for(receive(), timeout)

    async def call(self, name, arguments):
        if name not in {t["name"] for t in self.tools}:
            raise ValueError("Herramienta no anunciada por el servidor")
        return await self.request("tools/call", {"name": name, "arguments": arguments}, timeout=120)

    async def close(self):
        if self.process:
            try:
                os.killpg(self.process.pid, signal.SIGTERM) if os.name == "posix" else self.process.terminate()
                await asyncio.wait_for(self.process.wait(), 3)
            except asyncio.TimeoutError:
                os.killpg(self.process.pid, signal.SIGKILL) if os.name == "posix" else self.process.kill()
                await self.process.wait()
            except ProcessLookupError:
                pass
        self.process = None
        self.tools = []


class OpenCodeCortex:
    """Explicit CLI adviser. Tools denied; public text events only."""
    def __init__(self, model, *, executable="opencode", timeout=120):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[^\s]+", model):
            raise ValueError("OpenCode model: provider/model")
        self.model, self.executable, self.timeout = model, executable, timeout
        self.history = []

    async def ask(self, prompt, *, progress=None, on_delta=None):
        exe = shutil.which(self.executable)
        if not exe:
            raise ValueError("OpenCode no está instalado. Usa /connect api o instala su CLI por separado.")
        if progress: progress("OpenCode · asesor sin herramientas")
        messages = self.history[-10:] + [{"role":"user", "content":prompt[:24000]}]
        text_prompt = SYSTEM + "\n" + "\n".join(m["role"]+": "+m["content"] for m in messages)
        with tempfile.TemporaryDirectory(prefix="echo-neocortex-") as folder:
            config = {"$schema":"https://opencode.ai/config.json", "permission":{"*":"deny"},
                      "agent":{"echo-adviser":{"mode":"primary", "prompt":SYSTEM,
                      "permission":{"*":"deny"}}}, "plugin":[], "mcp":{}}
            config_file = Path(folder)/"opencode.json"
            config_file.write_text(json.dumps(config))
            env = os.environ.copy()
            env.update(OPENCODE_CONFIG=str(config_file), OPENCODE_CONFIG_CONTENT=json.dumps(config),
                       XDG_CONFIG_HOME=str(Path(folder)/"config"), OPENCODE_CONFIG_DIR=str(Path(folder)/"config"))
            argv = [exe,"run","--pure","--format","json","--model",self.model,"--agent","echo-adviser",text_prompt]
            process = await asyncio.create_subprocess_exec(*argv,cwd=folder,env=env,
                       stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT,
                       start_new_session=(os.name!="nt"),limit=2_000_001)
            fragments=[]
            async def receive():
                size=0
                async for line in process.stdout:
                    size+=len(line)
                    if size>2_000_000: raise RuntimeError("OpenCode: salida demasiado grande")
                    try: event=json.loads(line)
                    except (ValueError,UnicodeError): continue
                    if event.get("type")=="error":raise RuntimeError("OpenCode informó un error; consulta su configuración de proveedor.")
                    if event.get("type")!="text":continue
                    part=event.get("part",{});text=part.get("text") if isinstance(part,dict) else None
                    if isinstance(text,str):
                        fragments.append(text)
                        if on_delta:on_delta(text)
                        if progress:progress("OpenCode · respuesta pública")
                code=await process.wait()
                if code:raise RuntimeError(f"OpenCode terminó con código {code}; revisa autenticación y modelo.")
            try:
                await asyncio.wait_for(receive(),timeout=self.timeout)
            except asyncio.TimeoutError:
                raise RuntimeError("OpenCode agotó el tiempo de respuesta") from None
            finally:
                if process.returncode is None:
                    if os.name!="nt":os.killpg(process.pid,signal.SIGTERM)
                    else:process.terminate()
                    try:await asyncio.wait_for(process.wait(),timeout=3)
                    except asyncio.TimeoutError:
                        if os.name!="nt":os.killpg(process.pid,signal.SIGKILL)
                        else:process.kill()
                        await process.wait()
        text="".join(fragments)
        if not text.strip():raise RuntimeError("OpenCode no devolvió texto público")
        self.history=(messages+[{"role":"assistant","content":text[:24000]}])[-12:]
        if progress:progress("Respuesta completada")
        return text
