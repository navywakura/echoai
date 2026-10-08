"""Operator configuration and private, redacted harness logs."""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def data_dir() -> Path:
    return Path(os.getenv("ECHO_NEXUS_HOME", Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "echo-nexus")).expanduser()


def state_dir() -> Path:
    return Path(os.getenv("ECHO_NEXUS_STATE", Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local/state")) / "echo-nexus")).expanduser()


def load_config() -> dict:
    path = data_dir() / "config.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("config.json debe contener un objeto JSON")
    return value


def save_config(value: dict) -> None:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = root / "config.json"
    temporary = root / "config.tmp"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    temporary.replace(path)


_secrets: set[str] = set()

def register_secret(value: str) -> None:
    if value:
        _secrets.add(value)

def redact(text: str) -> str:
    text = re.sub(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))", "", str(text))
    text = "".join(c for c in text if c in "\n\t" or ord(c) >= 32)
    for value in _secrets:
        text = text.replace(value, "[REDACTED]")
    for name, value in os.environ.items():
        if len(value) >= 8 and re.search(r"(?:KEY|TOKEN|SECRET|PASSWORD)", name, re.I):
            text = text.replace(value, "[REDACTED]")
    return re.sub(r"\b(?:sk-[\w-]{8,}|gh[pousr]_[\w]{12,})\b", "[REDACTED]", text)


class SessionLog:
    def __init__(self):
        root = state_dir() / "sessions"
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        self.path = root / f"{stamp}-{os.getpid()}.log"
        self.file = os.fdopen(os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w")

    def write(self, text):
        self.file.write(redact(text) + "\n")
        self.file.flush()

    def close(self):
        self.file.close()


def detect() -> list[dict]:
    """Detection never launches an agent, scans credentials, or changes config."""
    return [{"name": name, "path": shutil.which(name), "interface": interface}
            for name, interface in (("echoai", "ECHO CLI"), ("opencode", "CLI JSON; adviser mode"), ("claude", "MCP stdio: claude mcp serve"),
                                    ("codex", "CLI; MCP depends on installed version"),
                                    ("gemini", "CLI; supply an MCP server explicitly"),
                                    ("llama-server", "local GGUF / HTTP"))]
