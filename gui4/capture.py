"""Screenshots and deterministic frame recording for GUI-4.

Screen capture depends on the compositor and drops frames.  GUI-4 dumps its
own frames instead: one PNG per published tick, numbered, plus a manifest
saying which task, seed and turn range produced them.  ``ffmpeg`` only
assembles the video afterwards, and when it is missing the PNGs remain.

Every recorded frame carries its origin stamp (LIVE / BENCH / EVIDENCE) so a
clip can never be mistaken for a certificate.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import ORIGINS

ECHOAI = Path(__file__).resolve().parents[1]
OUT = ECHOAI / "lab" / "gui4"
SHOTS = OUT / "shots"


def ffmpeg() -> Optional[str]:
    """Path to ffmpeg, or None.  Recording never depends on it."""
    return shutil.which("ffmpeg")


#: Fedora ships ffmpeg without libx264, so the encoder is chosen, not assumed.
ENCODERS = ("libx264", "libopenh264", "libvpx-vp9", "libsvtav1", "mpeg4")
_ENCODER: list[Optional[tuple[str, str]]] = [None]


def encoder() -> Optional[tuple[str, str]]:
    """(encoder, container suffix) this ffmpeg can actually use, or None."""
    if _ENCODER[0] is not None:
        return _ENCODER[0] or None
    binary = ffmpeg()
    if binary is None:
        return None
    try:
        listing = subprocess.run([binary, "-hide_banner", "-encoders"],
                                 capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    available = listing.stdout.decode("utf-8", "replace")
    for name in ENCODERS:
        if name in available:
            suffix = ".webm" if name.startswith("libvpx") else ".mp4"
            _ENCODER[0] = (name, suffix)
            return _ENCODER[0]
    return None


def _stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


@dataclass
class Recording:
    """A numbered PNG sequence plus the manifest that explains it."""

    directory: Path
    case: str
    origin: str
    task: str = ""
    seeds: list[int] = field(default_factory=list)
    frames: int = 0
    first_turn: Optional[int] = None
    last_turn: Optional[int] = None
    started: float = field(default_factory=time.time)
    closed: bool = False

    @property
    def origin_label(self) -> str:
        return ORIGINS.get(self.origin, self.origin)

    def add(self, image, turn: Optional[int] = None) -> Optional[Path]:
        """Write one frame.  ``image`` is anything with ``save(path)``."""
        if self.closed:
            return None
        path = self.directory / f"frame-{self.frames:06d}.png"
        try:
            image.save(path)
        except (OSError, ValueError, AttributeError):
            return None
        self.frames += 1
        if turn is not None:
            self.first_turn = turn if self.first_turn is None else self.first_turn
            self.last_turn = turn
        return path

    def manifest(self) -> dict:
        return {
            "case": self.case,
            "origin": self.origin,
            "origin_label": self.origin_label,
            "task": self.task,
            "seeds": list(self.seeds),
            "frames": self.frames,
            "first_turn": self.first_turn,
            "last_turn": self.last_turn,
            "started": self.started,
            "seconds": round(time.time() - self.started, 2),
            "note": "Los frames ilustran. El certificado sale de lab/ y sus hashes.",
        }

    def close(self) -> dict:
        """Stop recording and write ``manifest.json``.  Idempotent."""
        if not self.closed:
            self.closed = True
            try:
                (self.directory / "manifest.json").write_text(
                    json.dumps(self.manifest(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
            except OSError:
                pass
        return self.manifest()

    def encode(self, fps: int = 12) -> tuple[bool, str]:
        """Assemble an MP4 from the frames; (ok, message)."""
        binary = ffmpeg()
        if binary is None:
            return False, ("ffmpeg no está instalado: los PNG quedan en "
                           f"{self.directory}")
        if not self.frames:
            return False, "no hay frames que montar"
        choice = encoder()
        if choice is None:
            return False, (f"ffmpeg no trae codificador de vídeo usable; los PNG "
                           f"quedan en {self.directory}")
        codec, suffix = choice
        target = self.directory / f"video{suffix}"
        command = [binary, "-y", "-framerate", str(max(1, fps)),
                   "-i", str(self.directory / "frame-%06d.png"),
                   "-c:v", codec, "-pix_fmt", "yuv420p", str(target)]
        try:
            done = subprocess.run(command, capture_output=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"ffmpeg falló: {exc}"
        if done.returncode != 0:
            tail = done.stderr.decode("utf-8", "replace").strip().splitlines()
            return False, "ffmpeg falló: " + (tail[-1] if tail else "sin salida")
        return True, str(target)


def start(case: str, origin: str, task: str = "",
          seeds: Optional[list[int]] = None) -> Recording:
    """Open a new recording directory under ``lab/gui4/``."""
    directory = OUT / f"rec-{_stamp()}-{case}"
    directory.mkdir(parents=True, exist_ok=True)
    return Recording(directory, case, origin, task, list(seeds or ()))


def screenshot(image, case: str = "gui4") -> Optional[Path]:
    """Write a single PNG under ``lab/gui4/shots/``."""
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{_stamp()}-{case}.png"
    try:
        image.save(path)
    except (OSError, ValueError, AttributeError):
        return None
    return path
