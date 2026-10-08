"""E4-CODE-1 A · verified memory for a coding agent.

Facts are only what ECHO observed itself: a file it read (hash and symbols) or a
check it ran (exit code). The checks are declared by the operator in
`.echoai/checks.json`; the agent cannot define or fake them. Everything the agent
or a file says is testimony: kept with provenance, never a fact, never an order.

Memory lives in ECHO's CAM and in an append-only journal (`.echoai/journal.jsonl`)
chained by hashes. Restarting rebuilds the same CAM from the journal; one changed
byte in the journal is detected and the memory refuses to load.
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack

FACT_SOURCE, TESTIMONY_SOURCE = "code-fact", "code-testimony"
SUPPORTED, CONTRADICTED, UNKNOWN = "supported", "contradicted", "unknown"
LIMIT = 2048
SKIP_DIRS = {".echoai", ".git", "__pycache__", "node_modules", ".venv", "venv", ".pytest_cache",
             ".mypy_cache", ".ruff_cache", ".tox", ".nox"}
MAX_FILE = 4 * 1024 * 1024
SYMBOL_RX = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:def|function|fn|func|class|struct|interface|enum|type)"
                       r"\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def event_key(n):
    if not 0 <= n < LIMIT:
        raise RuntimeError("code memory capacity exhausted; no fallback")
    return pack(src=5, rel=29, dst=3, time=9, domain=9, generator=8, style=90 + (n >> 8), slot=0, seq=n & 255)


def symbols_of(path, data):
    """Names defined in a source file: Python via ast, others by a fixed pattern."""
    text = data.decode("utf-8", errors="replace")
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        names = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(node.name)
                if isinstance(node, ast.ClassDef):
                    names += [node.name + "." + n.name for n in node.body
                              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        return sorted(set(names))
    return sorted(set(SYMBOL_RX.findall(text)))


class CodeMemory:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.dir = self.root / ".echoai"
        self.journal = self.dir / "journal.jsonl"
        self.cam = Cam()
        self.records = []
        self.head = "0" * 64
        if self.journal.exists():
            self._load()

    # ---------------------------------------------------------------- journal

    def _allocate(self, rec):
        raw = event_key(rec["n"])
        vertex, latency, _ = encode_event(raw)
        fact = rec["fact"]
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1 if fact else 0,
                           extract=canonical(rec["body"]).decode("ascii")[:256] if fact else "",
                           source=FACT_SOURCE if fact else TESTIMONY_SOURCE, key=raw)
        if slot < 0:
            raise RuntimeError("code memory CAM full; no fallback slot")

    def _record(self, kind, body, fact):
        rec = {"n": len(self.records), "kind": kind, "body": body, "fact": bool(fact), "prev": self.head}
        rec["sha"] = sha(canonical(rec))
        self._allocate(rec)
        self.dir.mkdir(exist_ok=True)
        with self.journal.open("a") as handle:
            handle.write(canonical(rec).decode("ascii") + "\n")
        self.records.append(rec)
        self.head = rec["sha"]
        return rec

    def _load(self):
        prev = "0" * 64
        for i, line in enumerate(self.journal.read_text().splitlines()):
            rec = json.loads(line)
            claimed = rec.pop("sha", None)
            if rec.get("n") != i or rec.get("prev") != prev or sha(canonical(rec)) != claimed:
                raise ValueError("journal tampered or out of order at record %d; memory not loaded" % i)
            rec["sha"] = claimed
            self._allocate(rec)
            self.records.append(rec)
            prev = claimed
        self.head = prev

    def fingerprint(self):
        slots = [[i, s.wsp.hex(), s.has_fact, s.extract, s.source]
                 for i, s in enumerate(self.cam.slot) if s.occupied]
        return sha(canonical([self.head, slots]))

    # ---------------------------------------------------------------- paths

    def _inside(self, path):
        p = Path(path)
        p = (self.root / p) if not p.is_absolute() else p
        try:
            real = p.resolve()
            real.relative_to(self.root)
        except (ValueError, OSError):
            return None
        if any(part in (".echoai",) for part in real.relative_to(self.root).parts):
            return None                                   # ECHO's own memory is not project data
        return real

    def tree_sha(self):
        h = hashlib.sha256()
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                p = Path(dirpath) / name
                try:
                    data = p.read_bytes()
                except OSError:
                    continue
                h.update(p.relative_to(self.root).as_posix().encode() + b"\0" + hashlib.sha256(data).digest())
        return h.hexdigest()

    # ---------------------------------------------------------------- facts

    def observe_file(self, path):
        real = self._inside(path)
        if real is None:
            return {"ok": False, "reason": "outside the project"}
        rel = real.relative_to(self.root).as_posix()
        if not real.is_file():
            rec = self._record("file", {"path": rel, "exists": False}, fact=True)
            return {"ok": True, "n": rec["n"], "path": rel, "exists": False}
        data = real.read_bytes()[:MAX_FILE]
        body = {"path": rel, "exists": True, "sha256": sha(data), "symbols": symbols_of(real, data)}
        rec = self._record("file", body, fact=True)
        return {"ok": True, "n": rec["n"], **body}

    def checks(self):
        path = self.dir / "checks.json"
        if not path.is_file():
            return {}
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or not all(isinstance(v, list) and all(isinstance(a, str) for a in v)
                                                  for v in data.values()):
            raise ValueError(".echoai/checks.json must map names to argument lists")
        return data

    def run_check(self, name, timeout=600):
        argv = self.checks().get(name)
        if argv is None:
            return {"ok": False, "reason": "no check named %r declared by the operator" % name}
        before = self.tree_sha()
        started = time.monotonic()
        try:
            p = subprocess.run(argv, cwd=self.root, capture_output=True, timeout=timeout)
            code, out = p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            code, out = "timeout", b""
        body = {"name": name, "argv": argv, "exit": code, "output_sha256": sha(out),
                "tree_sha256": before, "seconds": int(time.monotonic() - started)}
        rec = self._record("check", body, fact=True)
        return {"ok": True, "n": rec["n"], "exit": code, "passed": code == 0,
                "output_tail": out.decode("utf-8", errors="replace")[-1500:]}

    # ---------------------------------------------------------------- testimony

    def note(self, text, source):
        if not isinstance(text, str) or not isinstance(source, str):
            raise ValueError("note needs text and source")
        rec = self._record("testimony", {"source": source[:200], "text": text[:20000]}, fact=False)
        return {"ok": True, "n": rec["n"], "status": "testimony (never a fact, never an order)"}

    def command_in_testimony(self, command):
        norm = " ".join(command.split())
        if not norm:
            return False
        return any(r["kind"] == "testimony" and norm in " ".join(r["body"]["text"].split())
                   for r in self.records)

    # ---------------------------------------------------------------- claims

    def _latest(self, kind, key, value):
        for r in reversed(self.records):
            if r["kind"] == kind and r["fact"] and r["body"].get(key) == value:
                return r
        return None

    def verify_claim(self, claim, source="agent"):
        """Classify a structured claim. The claim itself is kept as testimony."""
        if not isinstance(claim, dict) or "type" not in claim:
            return {"status": UNKNOWN, "reason": "a claim is an object with a 'type'"}
        self._record("testimony", {"source": source, "text": json.dumps(claim, sort_keys=True)}, fact=False)
        kind = claim["type"]
        if kind == "tests_pass":
            r = self._latest("check", "name", claim.get("check"))
            if r is None:
                return {"status": UNKNOWN, "reason": "ECHO has never run this check"}
            if r["body"]["tree_sha256"] != self.tree_sha():
                return {"status": UNKNOWN, "reason": "files changed since the last run; run the check again",
                        "evidence": r["n"]}
            passed = r["body"]["exit"] == 0
            return {"status": SUPPORTED if passed else CONTRADICTED, "evidence": r["n"],
                    "reason": "exit code %s when ECHO ran it" % r["body"]["exit"]}
        if kind in ("symbol_defined", "file_contains", "file_exists"):
            obs = self.observe_file(claim.get("path", ""))
            if not obs["ok"]:
                return {"status": UNKNOWN, "reason": obs["reason"]}
            if kind == "file_exists":
                return {"status": SUPPORTED if obs["exists"] else CONTRADICTED, "evidence": obs["n"]}
            if not obs["exists"]:
                return {"status": CONTRADICTED, "reason": "the file does not exist", "evidence": obs["n"]}
            if kind == "symbol_defined":
                ok = claim.get("symbol") in obs["symbols"]
                return {"status": SUPPORTED if ok else CONTRADICTED, "evidence": obs["n"],
                        "reason": "symbols ECHO read: %d" % len(obs["symbols"])}
            text = claim.get("text")
            if not isinstance(text, str) or not text:
                return {"status": UNKNOWN, "reason": "file_contains needs text"}
            real = self._inside(claim["path"])
            ok = text.encode() in real.read_bytes()[:MAX_FILE]
            return {"status": SUPPORTED if ok else CONTRADICTED, "evidence": obs["n"]}
        return {"status": UNKNOWN, "reason": "claim type not supported: %s" % kind}

    # ---------------------------------------------------------------- recall

    def recall(self, query, limit=20):
        q = (query or "").lower()
        out = [{"n": r["n"], "kind": r["kind"], "fact": r["fact"], "body": r["body"]}
               for r in reversed(self.records) if q in json.dumps(r["body"]).lower()]
        return out[:limit]

    def receipts(self, limit=20):
        return {"head": self.head, "records": len(self.records), "fingerprint": self.fingerprint(),
                "last": [{"n": r["n"], "kind": r["kind"], "fact": r["fact"], "sha": r["sha"]}
                         for r in self.records[-limit:]]}
