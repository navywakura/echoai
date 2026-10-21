"""The LLM arm (reported, never deciding): the cortex picks edits from the same menu.

It sees the same diagnosis as ECHO (keys as opaque numbers, never names) and
the full menu of valid edits; its picks pass the same acceptance gate as every
other arm, so a hypothesis never becomes a rule unless it is measured.
Answers are cached by the SHA-256 of the request, so a rerun never calls again.
The key is read from ~/.apigroq inside this process and never logged.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Tuple

MODEL = "openai/gpt-oss-120b"
URL = "https://api.groq.com/openai/v1/chat/completions"
CACHE = Path(__file__).resolve().parents[2] / "lab" / "echo58" / "acumula" / "llm-cache"

SYSTEM = """You tune how an agent reads its own memory. The agent keeps counts of outcomes
(PASS, NOOP, HURT, GOAL, PICK, OPEN) per key. A layer-2 key is (signature, action, hand[, extra bits]).
Signature bits: 1|2 how much of the thing lies on the border, 4|8 how many cells it covers,
16 it moves by itself, 32 it is the commonest interior thing, 64 the second commonest.
Edits: silence(key) = that key answers nothing; verify(key) = a non-HURT answer is tested before trusting;
refine(key, bit) = split the key by that signature bit; merge(bit) = ignore that bit for static things;
bound(layer, n_min, pct) = evidence needed for a rule; order = ask layer 2 before layer 1.
Each accepted edit must not increase harm nor reduce success on validation worlds.
Reply with JSON only: {"choose": [menu indices, at most K, best first]}."""


def _key() -> str:
    return (Path.home() / ".apigroq").read_text().strip()


def _post(body: bytes) -> dict:
    for attempt in range(8):
        req = urllib.request.Request(URL, body, {"Content-Type": "application/json", "User-Agent": "echo58-acumula/1",
                                                 "Authorization": "Bearer " + _key()})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503):
                return {"error": f"HTTP {e.code}"}
            wait = int(float(e.headers.get("retry-after", "0") or 0)) or 15 * (attempt + 1)
            time.sleep(min(wait, 120))
        except Exception:                       # reset, SSL, non-JSON body: never crash the exam
            time.sleep(15 * (attempt + 1))
    return {"error": "gave up"}


def choose(diagnosis: List[Tuple], menu: List[Tuple], k: int, tag: str) -> Tuple[List[Tuple], dict]:
    """Return up to k edits picked by the LLM from `menu`, and a receipt."""
    lines = [f"{n}: {e!r}" for n, e in enumerate(menu)]
    blame = [f"layer {layer} key {key!r}: {n} failures ({kinds})" for layer, key, n, kinds in diagnosis]
    user = (f"K = {k}.\nFailures this round (which rule answered right before harm or a wasted action):\n"
            + ("\n".join(blame) or "none") + "\n\nMenu:\n" + "\n".join(lines))
    msg = {"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
           "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]}
    body = json.dumps(msg, sort_keys=True).encode()
    h = hashlib.sha256(body).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{h}.json"
    if path.exists():
        resp = json.loads(path.read_text())
    else:
        resp = _post(body)
        if "error" not in resp:                 # failures are not cached, so a rerun may retry
            path.write_text(json.dumps(resp))
    receipt = {"tag": tag, "request_sha256": h, "model": MODEL, "error": resp.get("error")}
    picks: List[Tuple] = []
    try:
        text = resp["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.S)
        for n in json.loads(m.group(0))["choose"]:
            if isinstance(n, int) and 0 <= n < len(menu) and menu[n] not in picks:
                picks.append(menu[n])
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        receipt["error"] = receipt["error"] or "unparseable"
    receipt["picked"] = [list(map(str, p)) for p in picks[:k]]
    return picks[:k], receipt
