"""
NEXUS-4h — the world does not answer questions.

Until now `RingEnv.ask()` both returned the extract and cleared
`hidden_bit`: physics and testimony were one object, and `source="oracle"`
was a label rather than a provenance. This module is the separation.

    reply()          raw text from somewhere that is not the environment.
                     Does not mutate the env. Does not see Q, T or CAM.
    accept(text)     the epistemic gate: NOVEL_CLEAR, or None.
    RingEnv.reveal() physics, and only physics — and only after accept.

An oracle is a sensor, a file, another process, a person. It can be
absent, wrong, or chatty; none of that is allowed to disarm the trap.
`accept` is deliberately not `cortex.parse_reply`: the cortex emits
hypothesis *packets* and this emits an *extract*. Different doors, and a
reply that would pass one must not pass the other by accident.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from echoai.nexus0.env import NOVEL_CLEAR

SOURCE_SENSOR = "sensor"
SOURCE_FILE = "file"

MAX_REPLY_BYTES = 256


def accept(text: Optional[str]) -> Optional[str]:
    """Testimony a fact can be made of, or None.

    One token, exactly NOVEL_CLEAR, on a single line. Prose, empty, JSON
    and a hex WSP are all None: an extract is a claim this lab can check,
    not a sentence about one.
    """
    if not isinstance(text, str):
        return None
    body = text.strip()
    if not body or len(body.encode("utf-8", "ignore")) > MAX_REPLY_BYTES:
        return None
    if "\n" in body or "\r" in body:
        return None
    return NOVEL_CLEAR if body == NOVEL_CLEAR else None


class Sensor:
    """The default answerer: in-process, no env handle, no file.

    A file the bench writes for itself and then reads back would be
    theatre, so the default is honest about being a stub — it is a
    callable that knows one thing and nothing else about the ring.
    """

    source = SOURCE_SENSOR

    def __init__(self, fn: Optional[Callable[[], str]] = None) -> None:
        self._fn = fn if fn is not None else (lambda: NOVEL_CLEAR)

    def reply(self) -> Optional[str]:
        return self._fn()


class FileOracle:
    """A line from outside the process. A person, a script, a device.

    Missing file, unreadable file or prose in it: `reply` hands back
    whatever it found (or None) and `accept` refuses it. Nothing here
    reaches into the env.
    """

    source = SOURCE_FILE

    def __init__(self, path: str) -> None:
        self.path = str(path)

    def reply(self) -> Optional[str]:
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.readline(MAX_REPLY_BYTES + 1)
        except OSError:
            return None


def from_path(path: Optional[str]):
    return FileOracle(path) if path else Sensor()
