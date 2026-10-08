"""GUI-4 — presentation and demonstration layer for echoAI.

GUI-4 is an *observer*.  It never chooses an action, never writes CAM, T, Q or
PATTERN, and never injects an observation into an agent.  Every number it
displays carries its origin (see :mod:`echoai.gui4.catalog`):

* ``LIVE``      the real agent is running right now in this window;
* ``BENCH``     a real ECHO-3 bench runs now with a reduced denominator;
* ``EVIDENCE``  a sealed report under ``lab/`` is replayed, never recomputed.

GUI-4 emits no certificate.  ECHO-3 stays at 14/15 before and after it.

The package lives outside ``nexus0`` on purpose: ``safe1``, ``power1``,
``host1`` and ``cause1`` seal their lock inventory with ``rglob('*.py')`` over
``nexus0/``, so a new module there would break audits that currently
reproduce.  See ``docs/GUI4-DESIGN.md`` §2.
"""
from __future__ import annotations

__all__ = ["ORIGIN_LIVE", "ORIGIN_BENCH", "ORIGIN_EVIDENCE", "ORIGINS"]

ORIGIN_LIVE = "LIVE"
ORIGIN_BENCH = "BENCH"
ORIGIN_EVIDENCE = "EVIDENCE"

#: Every displayed figure must declare one of these, with its Spanish label.
ORIGINS = {
    ORIGIN_LIVE: "en vivo",
    ORIGIN_BENCH: "banco reducido",
    ORIGIN_EVIDENCE: "evidencia sellada",
}
