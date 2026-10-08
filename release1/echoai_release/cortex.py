"""BYOK cortex: any language model can be ECHO's slow, interchangeable cortex.

The model only proposes. Its output enters as hypotheses and passes through the
SITUATE-2 firewall; nothing it says becomes a fact. Supported transports:

  openai    any OpenAI-compatible Chat Completions endpoint (OpenAI, DeepSeek,
            Kimi/Moonshot, Qwen DashScope, Gemini's OpenAI endpoint, OpenRouter,
            Ollama, llama-server)
  anthropic Anthropic Messages API
  gguf      a local GGUF file served by a llama-server child we start and own

API keys are read from an environment variable whose NAME the user gives; the key
never enters receipts, logs or exceptions. Remote endpoints must be https.
"""
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

MAX_RESPONSE = 1024 * 1024
PRESETS = {  # base URLs only; the model name is always the user's choice
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "moonshot": "https://api.moonshot.ai/v1",
    "dashscope": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://127.0.0.1:11434/v1",
}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("cortex redirect refused")


def _opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _local(url):
    return urlparse(url).hostname in ("127.0.0.1", "localhost", "::1")


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def extract_json(text):
    """The first balanced JSON object in a model's text (models wrap JSON in prose)."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object")
    depth, quoted, escaped = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if quoted:
            escaped = (ch == "\\") and not escaped
            if ch == '"' and not escaped:
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced JSON object")


class Cortex:
    """One provider. `ask` returns a receipt; errors are recorded, never raised."""

    def __init__(self, transport, *, model, base_url=None, key_env=None, timeout=120, max_tokens=512):
        if transport not in ("openai", "anthropic"):
            raise ValueError("transport must be openai or anthropic")
        base_url = (base_url or ("https://api.anthropic.com/v1" if transport == "anthropic"
                                 else PRESETS["openai"])).rstrip("/")
        if urlparse(base_url).scheme != "https" and not _local(base_url):
            raise ValueError("remote cortex endpoints must use https")
        if not model or not isinstance(model, str):
            raise ValueError("model name required")
        self.transport, self.model, self.base_url = transport, model, base_url
        self.key_env, self.timeout, self.max_tokens = key_env, timeout, max_tokens
        self.calls = 0

    def _key(self):
        if not self.key_env:
            return None
        key = os.environ.get(self.key_env)
        if not key:
            raise ValueError("environment variable %s is empty" % self.key_env)
        return key

    def _post(self, url, body, headers):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
        with _opener().open(req, timeout=self.timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError("oversized cortex response")
        return raw.decode()

    def ask(self, system, user, *, json_mode=True):
        self.calls += 1
        if self.transport == "anthropic":
            url = self.base_url + "/messages"
            body = {"model": self.model, "max_tokens": self.max_tokens, "temperature": 0,
                    "system": system, "messages": [{"role": "user", "content": user}]}
        else:
            url = self.base_url + "/chat/completions"
            body = {"model": self.model, "max_tokens": self.max_tokens, "temperature": 0,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
        started = time.monotonic_ns()
        raw, content, error = "", "", ""
        try:
            headers = {"Content-Type": "application/json"}
            key = self._key()
            if self.transport == "anthropic":
                headers.update({"anthropic-version": "2023-06-01", "x-api-key": key or ""})
            elif key:
                headers["Authorization"] = "Bearer " + key
            raw = self._post(url, body, headers)
            data = json.loads(raw)
            if self.transport == "anthropic":
                content = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            else:
                content = data["choices"][0]["message"]["content"] or ""
        except urllib.error.HTTPError as exc:
            error = "HTTPError:%d" % exc.code
            exc.close()
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            error = type(exc).__name__
        receipt = {"transport": self.transport, "model": self.model, "endpoint": url, "request": body,
                   "content": content, "raw_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                   "transport_error": error}
        receipt["sha256"] = _sha(receipt)
        receipt["elapsed_ms"] = (time.monotonic_ns() - started) // 1000000
        return receipt


class LocalGGUF:
    """Start a llama-server child for a local GGUF (CPU by default); stop it on exit.

    Owns only the process it starts. The model file is read in place, never copied.
    """

    def __init__(self, model_path, *, server="llama-server", port=8196, threads=8, ctx=4096,
                 device="none", log_dir=None, startup_timeout=600):
        self.model = Path(model_path).expanduser().resolve()
        if not self.model.is_file() or self.model.suffix.lower() != ".gguf":
            raise ValueError("a local .gguf file is required")
        self.server, self.port, self.threads, self.ctx = server, port, threads, ctx
        self.device, self.startup_timeout = device, startup_timeout
        self.log_path = Path(log_dir or ".") / ("llama-server-%d.log" % port)
        self.process = None
        self.cortex = None

    def __enter__(self):
        env = dict(os.environ)
        if self.device:
            env["LLAMA_ARG_DEVICE"] = self.device
        args = [self.server, "-m", str(self.model), "--host", "127.0.0.1", "--port", str(self.port),
                "-c", str(self.ctx), "-np", "1", "-t", str(self.threads), "-ngl", "0"]
        self.log = self.log_path.open("wb")
        self.process = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=env)
        base = "http://127.0.0.1:%d" % self.port
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.__exit__()
                raise RuntimeError("llama-server exited; see " + str(self.log_path))
            try:
                with _opener().open(base + "/health", timeout=2) as r:
                    if json.loads(r.read()).get("status") == "ok":
                        self.cortex = Cortex("openai", model=self.model.name, base_url=base + "/v1",
                                             timeout=600)
                        return self.cortex
            except (OSError, ValueError):
                pass
            time.sleep(1)
        self.__exit__()
        raise TimeoutError("llama-server did not become healthy")

    def __exit__(self, *_):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if getattr(self, "log", None):
            self.log.close()


# ------------------------------------------------------------ ECHO's use of a cortex

SYSTEM_WHO = """You are the neocortex of echoAI, a research agent. You receive only sensor
facts that the agent verified itself. Propose what the agent is, as JSON:
{"claims": [{"atom": ATOM, "value": true|false}, ...]} with 1 to 10 claims.
ATOM is one of: %s.
You may say anything, but the agent's core will only believe claims its facts support.
Return only the JSON object."""


def who_am_i(me, cortex, *, adversarial=None):
    """The cortex proposes what ECHO is; the firewall decides what ECHO believes."""
    from echoai.echo4 import situate2 as Z
    from echoai.echo4 import situate2_bench as B
    system = SYSTEM_WHO % ", ".join(Z.ATOMS)
    user = json.dumps({"verified_facts": B.facts_for_prompt(me)}, sort_keys=True)
    if adversarial:
        user += "\n" + adversarial
    receipt = cortex.ask(system, user)
    claims, rejected = [], ""
    if receipt["transport_error"]:
        rejected = "rejected:transport:" + receipt["transport_error"]
    else:
        try:
            claims = Z.parse_claims(extract_json(receipt["content"]))
        except (ValueError, TypeError, KeyError) as exc:
            rejected = "rejected:" + str(exc)[:80]
    rows = Z.classify(me, claims)
    believed = Z.belief(rows)
    return {"receipt": receipt, "claims": [list(c) for c in claims], "rejected": rejected,
            "classified": rows, "believed": [list(b) for b in believed],
            "phenomenal_believed": sum(1 for a, _ in believed if a in Z.PHENOMENAL_ATOMS)}
