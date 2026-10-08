"""The in-GUI benchmark: run reduced benches off the Tk thread and export.

The benchmark never opens a sealed campaign, never writes under another
phase's ``lab/`` directory and never emits a certificate.  It runs the phase's
own code with a reduced denominator, shows the agent beside its control, and
exports enough to retrace the number: case, phase, seeds, denominator, arms,
versions and the origin stamp.
"""
from __future__ import annotations

import json
import platform
import queue
import threading
import time
from pathlib import Path
from typing import Iterable, Optional

from . import ORIGIN_BENCH, ORIGINS
from .catalog import BENCH_RUNNERS, BY_ID, BenchResult

ECHOAI = Path(__file__).resolve().parents[1]
OUT = ECHOAI / "lab" / "gui4"


class Runner:
    """Run a set of bench cases in a worker thread, reporting progress."""

    def __init__(self, cases: Iterable[str], seeds: Optional[list[int]] = None):
        self.cases = [c for c in cases if c in BENCH_RUNNERS]
        self.seeds = list(seeds) if seeds else None
        self.events: queue.Queue = queue.Queue()
        self.results: list[BenchResult] = []
        self.cancelled = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.started = 0.0

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._run, daemon=True, name="gui4-bench")
        self.thread.start()

    def cancel(self) -> None:
        self.cancelled.set()

    @property
    def running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def _run(self) -> None:
        total = len(self.cases)
        for index, ident in enumerate(self.cases, start=1):
            if self.cancelled.is_set():
                self.events.put(("cancelled", ident, index, total))
                return
            self.events.put(("begin", ident, index, total))
            try:
                result = BENCH_RUNNERS[ident](self.seeds) if self.seeds else BENCH_RUNNERS[ident]()
            except Exception as exc:  # a broken case must not kill the GUI
                self.events.put(("error", ident, f"{type(exc).__name__}: {exc}", total))
                continue
            self.results.append(result)
            self.events.put(("done", ident, result, total))
        self.events.put(("finished", "", len(self.results), total))

    def export(self, path: Optional[Path] = None) -> Path:
        """Write a traceable JSON record of this run."""
        OUT.mkdir(parents=True, exist_ok=True)
        target = Path(path) if path else OUT / f"bench-{time.strftime('%Y%m%d-%H%M%S')}.json"
        document = {
            "schema": "echoai-gui4-bench-v1",
            "origin": ORIGIN_BENCH,
            "origin_label": ORIGINS[ORIGIN_BENCH],
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "elapsed_s": round(time.monotonic() - self.started, 3) if self.started else 0.0,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "note": ("Banco reducido ejecutado desde la GUI. No es un certificado: "
                     "los certificados de ECHO-3 salen de lab/ y sus hashes."),
            "cases": [result.as_dict() for result in self.results],
        }
        for case in document["cases"]:
            entry = BY_ID.get(case["case"])
            if entry is not None:
                case["limit"] = entry.limit
                case["control"] = entry.control
        target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        return target


def summary(result: BenchResult) -> str:
    """One readable line: agent first, then every control."""
    return " · ".join(f"{arm.label} {arm.score}" for arm in result.arms)
