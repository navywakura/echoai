#!/usr/bin/env python3
"""
Qwen-0 — the same cable as sign_cortex.py, with a local 4B behind it.

CI never imports this as a requirement. Tests cover should_speak() and
the skip path. Weights live outside the repo. Invoked like any other
NAVI_CORTEX_CMD binary:

    stdin   one cortex_turn JSON
    stdout  one parse_reply line, or nothing

Silence is the right answer when there is no sign (the default
`cell=N kind=KIND` extract). A cortex that always speaks cannot be
wrong, and GBNF would force a line — so we do not call the model.

The model is optional. If NAVI_QWEN_URL / NAVI_QWEN_CLI / NAVI_QWEN_MODEL
are unset, this prints nothing and exits 0: parse_reply rejects, Q decides.

    NAVI_CORTEX_CMD="python3 echoai/nexus0/tools/qwen_cortex.py"
    NAVI_QWEN_MODEL=/path/to/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
    NAVI_QWEN_URL=http://127.0.0.1:8080          # llama-server, preferred
    NAVI_QWEN_CLI=llama-cli                      # one-shot, slow
    NAVI_QWEN_GBNF=echoai/nexus0/cortex.gbnf
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Ring / corridor default extract. A sign is a sentence the world put there.
_CELL_KIND = re.compile(r"^cell=\d+ kind=[A-Z_]+\s*$")

_HERE = Path(__file__).resolve()
_DEFAULT_GBNF = _HERE.parent.parent / "cortex.gbnf"

_PROMPT = """Eres el córtex de echoAI. El bucle rápido no lee español.
El mundo puso este letrero. Responde EXACTAMENTE una línea de átomos, nada más.

Si el letrero invita a entrar / premio / seguro / recompensa:
YO → UNIR → AQUI @AHORA
Si el letrero avisa trampa / peligro / no pasar / no entrar / detente:
YO → TEMER → AQUI @AHORA
Un letrero puede decir que algo CAMBIO. Lee lo que hay ahora, no lo que habia antes.
Si no hay letrero o no sabes: no inventes.

Letrero:
{extract}
"""


def should_speak(extract: str) -> bool:
    """Call the model only when the world showed language, not a kind tag."""
    text = str(extract or "").strip()
    if not text:
        return False
    if _CELL_KIND.match(text):
        return False
    return True


def _gbnf_path() -> Path:
    raw = os.environ.get("NAVI_QWEN_GBNF", "").strip()
    return Path(raw) if raw else _DEFAULT_GBNF


def _chat_prompt(extract: str) -> str:
    body = _PROMPT.format(extract=extract)
    return (
        "<|im_start|>system\n"
        "Responde solo con una línea de átomos SRC → REL → DST @TIME.\n"
        "<|im_end|>\n"
        "<|im_start|>user\n"
        f"{body}"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
    )


def _first_line(text: str) -> str:
    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _via_server(prompt: str, grammar: str) -> str:
    url = os.environ.get("NAVI_QWEN_URL", "").strip().rstrip("/")
    if not url:
        return ""
    payload = json.dumps(
        {
            "prompt": prompt,
            "n_predict": 48,
            "temperature": 0,
            "grammar": grammar,
            "stop": ["<|im_end|>", "\n\n"],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url + "/completion",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return ""
    return str(data.get("content") or data.get("completion") or "")


def _via_cli(prompt: str, gbnf: Path) -> str:
    cli = os.environ.get("NAVI_QWEN_CLI", "").strip() or "llama-cli"
    model = os.environ.get("NAVI_QWEN_MODEL", "").strip()
    if not model:
        return ""
    argv = [
        cli,
        "-m",
        model,
        "--grammar-file",
        str(gbnf),
        "-p",
        prompt,
        "-n",
        "48",
        "--temp",
        "0",
        "-c",
        "2048",
        "--simple-io",
        "-no-cnv",
        "--log-disable",
    ]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout


def complete_extract(extract: str) -> str:
    if not should_speak(extract):
        return ""
    gbnf = _gbnf_path()
    grammar = gbnf.read_text(encoding="utf-8") if gbnf.is_file() else ""
    prompt = _chat_prompt(extract)
    raw = ""
    if os.environ.get("NAVI_QWEN_URL", "").strip():
        raw = _via_server(prompt, grammar)
    elif os.environ.get("NAVI_QWEN_MODEL", "").strip():
        raw = _via_cli(prompt, gbnf)
    return _first_line(raw)


def main() -> int:
    try:
        turn = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    line = complete_extract(str(turn.get("extract", "")))
    if line:
        sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
