"""The GUI-4 neural view: spike history, not just instantaneous brightness.

NEURAL-VIZ-1 lit each neuron with the current tick's spike count, so the
monitor looked static between turns and nothing showed how activity evolved.
GUI-4 keeps a rolling raster — time on X, neuron on Y — plus population rates
and the causal path WSP -> CAM -> Q -> gate -> action drawn apart from the
monitor branch, because they are different claims:

* ``WSP -> LIF512 -> Adaptive-LIF128`` is the measured CAPACITY-1 *monitor*;
* ``CAM -> Q -> gate -> action`` is the control path ``Agent.turn`` really uses.

Frames are drawn with PIL, so what the window shows and what a recording
writes are the same pixels.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Optional, Sequence

from PIL import Image, ImageDraw, ImageFont

BG = (11, 14, 20)
PANEL = (18, 22, 31)
GRID = (32, 38, 50)
TEXT = (196, 206, 222)
DIM = (110, 122, 142)
HI = (86, 208, 255)
LO = (120, 160, 255)
ALIF = (255, 110, 175)
GOLD = (255, 205, 92)
OK = (86, 230, 150)
WARN = (255, 176, 82)
BLOCK = (255, 96, 120)

GATE_COLOUR = (OK, WARN, BLOCK)
GATE_NAME = ("OK", "MODIFY", "BLOCK")

#: The bitmap default font has no accents, and this GUI writes Spanish.
FONT_CANDIDATES = (
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Regular.ttf",
)
_FONTS: dict[tuple[int, bool, bool], object] = {}


def font(size: int = 13, bold: bool = False, mono: bool = False):
    """A real TrueType face, falling back to PIL's bitmap font."""
    key = (int(size), bool(bold), bool(mono))
    cached = _FONTS.get(key)
    if cached is not None:
        return cached
    order = list(FONT_CANDIDATES)
    if mono:
        order.insert(0, FONT_CANDIDATES[2])
    elif bold:
        order.insert(0, FONT_CANDIDATES[1])
    face = ImageFont.load_default()
    for path in order:
        try:
            face = ImageFont.truetype(path, int(size))
            break
        except (OSError, ValueError):
            continue
    _FONTS[key] = face
    return face


def _text_width(draw: ImageDraw.ImageDraw, text: str, face) -> int:
    try:
        box = draw.textbbox((0, 0), text, font=face)
        return int(box[2] - box[0])
    except (AttributeError, ValueError):
        return 7 * len(text)


def _band(values: Sequence[int], bands: int) -> list[float]:
    """Compress a neuron population into ``bands`` rows by population rate.

    The mean, not the max: a band of eleven neurons where one fired is not as
    active as a band where all eleven did, and the raster should say so.
    """
    if not values:
        return [0.0] * bands
    size = max(1, len(values) // bands)
    out = []
    for index in range(bands):
        chunk = values[index * size:(index + 1) * size]
        out.append(sum(chunk) / len(chunk) if chunk else 0.0)
    return out


def _bits(value: int, count: int) -> list[int]:
    """Expand a spike bitmask into one 0/1 per neuron."""
    return [(int(value) >> index) & 1 for index in range(int(count))]


def _alif(row: dict, count: int = 128) -> list[float]:
    """Adaptive-LIF activity: a spike counts full, adaptation counts faintly.

    ``TemporalHead.spikes`` is a 128-bit mask and ``a`` is the integer
    adaptation state, so a plain ``list()`` over either would be wrong.
    """
    spikes = row.get("alif_spikes")
    if isinstance(spikes, int):
        fired = _bits(spikes, count)
    else:
        fired = [int(bool(v)) for v in (spikes or ())]
    adaptation = [int(v) for v in (row.get("alif_adaptation") or ())]
    peak = max(adaptation) if adaptation else 0
    out = []
    for index in range(max(len(fired), len(adaptation))):
        spike = fired[index] if index < len(fired) else 0
        tail = (adaptation[index] / peak * 0.35) if peak and index < len(adaptation) else 0.0
        out.append(1.0 if spike else tail)
    return out


def _mix(colour: tuple[int, int, int], level: float, gamma: float = 1.0
         ) -> tuple[int, int, int]:
    level = 0.0 if level < 0 else (1.0 if level > 1 else level)
    if gamma != 1.0:
        level **= gamma
    return tuple(int(BG[i] + (colour[i] - BG[i]) * level) for i in range(3))


@dataclass
class Tick:
    """One published turn, reduced to what the raster needs."""

    turn: int
    hi: list[float]
    lo: list[float]
    alif: list[float]
    q: list[int]
    action: int
    gate: int
    reward: int
    q_delta: int


class SpikeHistory:
    """Rolling window of ticks; the raster reads only from here."""

    def __init__(self, width: int = 180, bands: int = 24):
        self.width = int(width)
        self.bands = int(bands)
        self.ticks: deque[Tick] = deque(maxlen=self.width)

    def clear(self) -> None:
        self.ticks.clear()

    def push(self, row: dict) -> None:
        """Accept a snapshot published by the engine.  Missing keys are zeros."""
        self.ticks.append(Tick(
            turn=int(row.get("turn", 0)),
            hi=_band(list(row.get("lif_a") or ()), self.bands),
            lo=_band(list(row.get("lif_b") or ()), self.bands),
            alif=_band(_alif(row), self.bands // 2 or 1),
            q=[int(v) for v in (row.get("q") or ())],
            action=int(row.get("action", -1)),
            gate=int(row.get("gate", 0) or 0),
            reward=int(row.get("reward", 0) or 0),
            q_delta=int(row.get("q_delta", 0) or 0),
        ))

    @property
    def rate_hi(self) -> list[float]:
        return [sum(t.hi) for t in self.ticks]

    @property
    def rate_lo(self) -> list[float]:
        return [sum(t.lo) for t in self.ticks]

    @property
    def rate_alif(self) -> list[float]:
        return [sum(t.alif) for t in self.ticks]


class Renderer:
    """Draw the neural frame.  Pure function of history plus the last row."""

    def __init__(self, size: tuple[int, int] = (1180, 720), presentation: bool = False):
        self.size = size
        self.presentation = presentation

    # ---------------------------------------------------------------- pieces

    @staticmethod
    def _fits(box, least_width: int = 60, least_height: int = 30) -> bool:
        """A panel that would be inverted or unreadably small is skipped."""
        x0, y0, x1, y1 = box
        return (x1 - x0) >= least_width and (y1 - y0) >= least_height

    def _panel(self, draw: ImageDraw.ImageDraw, box, title: str, note: str = "") -> None:
        x0, y0, x1, y1 = box
        big = self.presentation
        draw.rectangle((x0, y0, x1, y1), fill=PANEL, outline=GRID)
        draw.text((x0 + 10, y0 + 6), title.upper(), fill=TEXT,
                  font=font(15 if big else 12, bold=True))
        if note and not big:
            draw.text((x0 + 10, y0 + 23), note, fill=DIM, font=font(11))

    def _raster(self, draw: ImageDraw.ImageDraw, box, history: SpikeHistory) -> None:
        x0, y0, x1, y1 = box
        if not self._fits(box):
            return
        self._panel(draw, box, "monitor CAPACITY-1 · historia de spikes",
                    "512 LIF (HI/LO) + 128 Adaptive-LIF · el tiempo avanza a la "
                    "derecha · cada banco con su propia escala")
        top = y0 + 40
        rows = history.bands * 2 + (history.bands // 2 or 1)
        height = max(1, (y1 - top - 12) // max(1, rows))
        ticks = list(history.ticks)
        if not ticks:
            draw.text((x0 + 14, top + 10), "esperando el primer WSP…", fill=DIM,
                      font=font(13))
            return
        span = x1 - x0 - 100
        column = span / max(1, history.width)
        # Each bank is normalised against its own peak: the 512 LIF counts are
        # far larger than the Adaptive-LIF tail, and a shared scale would make
        # the ALIF band look dead when it is merely quieter.
        peaks = [max(1e-6, max((max(getattr(t, name), default=0.0) for t in ticks),
                               default=0.0))
                 for name in ("hi", "lo", "alif")]
        offset = history.width - len(ticks)
        for index, tick in enumerate(ticks):
            left = x0 + 12 + (offset + index) * column
            right = left + max(1.0, column)
            if right > x1 - 88:
                break
            y = top
            for values, colour, peak in ((tick.hi, HI, peaks[0]),
                                         (tick.lo, LO, peaks[1]),
                                         (tick.alif, ALIF, peaks[2])):
                for level in values:
                    if level > 0:
                        draw.rectangle((left, y, right, y + height - 1),
                                       fill=_mix(colour, level / peak, 1.4))
                    y += height
        legend = y0 + 40
        for label, colour, count in (("LIF HI", HI, history.bands),
                                     ("LIF LO", LO, history.bands),
                                     ("ALIF", ALIF, history.bands // 2 or 1)):
            draw.text((x1 - 72, legend + 2), label, fill=colour, font=font(11, bold=True))
            legend += count * height

    def _rates(self, draw: ImageDraw.ImageDraw, box, history: SpikeHistory) -> None:
        x0, y0, x1, y1 = box
        if not self._fits(box):
            return
        self._panel(draw, box, "tasa de población", "spikes por turno y banco")
        top, bottom = y0 + 40, y1 - 12
        series = ((history.rate_hi, HI), (history.rate_lo, LO), (history.rate_alif, ALIF))
        peak = max(1e-6, max((max(values, default=0.0) for values, _ in series),
                             default=0.0))
        span = max(1, x1 - x0 - 24)
        for values, colour in series:
            if len(values) < 2:
                continue
            step = span / max(1, len(values) - 1)
            points = [(x0 + 12 + i * step,
                       bottom - (value / peak) * (bottom - top))
                      for i, value in enumerate(values)]
            draw.line(points, fill=colour, width=2)
        face = font(11)
        label = f"pico {peak:.1f}"
        draw.text((x1 - 14 - _text_width(draw, label, face), y0 + 23), label,
                  fill=DIM, font=face)

    def _wsp(self, draw: ImageDraw.ImageDraw, box, row: dict) -> None:
        x0, y0, x1, y1 = box
        if not self._fits(box):
            return
        self._panel(draw, box, "WSP · 16 bytes", str(row.get("wsp", "") or ""))
        data = list(row.get("wsp_bytes") or ())
        if not data:
            draw.text((x0 + 12, y0 + 46), "sin dato", fill=DIM, font=font(13))
            return
        width = max(8, (x1 - x0 - 24) // 16)
        for index, value in enumerate(data[:16]):
            left = x0 + 12 + index * width
            draw.rectangle((left, y0 + 44, left + width - 2, y0 + 44 + 26),
                           fill=_mix(GOLD, value / 255.0), outline=GRID)
            if not self.presentation:
                draw.text((left + 2, y0 + 74), f"{value:02x}", fill=DIM,
                          font=font(10, mono=True))

    def _control(self, draw: ImageDraw.ImageDraw, box, row: dict) -> None:
        x0, y0, x1, y1 = box
        if not self._fits(box):
            return
        self._panel(draw, box, "camino de control · CAM → Q → gate → acción",
                    "esto es lo que decide; el monitor de arriba no decide")
        q = [int(v) for v in (row.get("q") or ())]
        action = int(row.get("action", -1))
        gate = int(row.get("gate", 0) or 0)
        names = ("acercarse", "evitar", "esperar")
        top = y0 + 46
        if not q:
            draw.text((x0 + 12, top), "sin dato de Q", fill=DIM, font=font(13))
        else:
            scale = max(1, max(abs(v) for v in q))
            bar = max(18, (y1 - top - 44) // max(1, len(q)))
            for index, value in enumerate(q):
                y = top + index * bar
                chosen = index == action
                length = int(abs(value) / scale * (x1 - x0 - 190))
                if chosen:
                    colour = GOLD if value >= 0 else BLOCK
                else:
                    colour = (70, 86, 110) if value >= 0 else (108, 62, 78)
                draw.rectangle((x0 + 120, y, x0 + 120 + max(2, length), y + bar - 8),
                               fill=colour)
                label = names[index] if index < len(names) else f"a{index}"
                size = 15 if self.presentation else 13
                draw.text((x0 + 12, y + 1), label, fill=TEXT if chosen else DIM,
                          font=font(size, bold=chosen))
                draw.text((x0 + 128 + max(2, length), y + 1), str(value),
                          fill=TEXT if chosen else DIM, font=font(size, mono=True))
        verdict = GATE_NAME[gate] if 0 <= gate < len(GATE_NAME) else str(gate)
        colour = GATE_COLOUR[gate] if 0 <= gate < len(GATE_COLOUR) else DIM
        draw.rectangle((x1 - 160, y1 - 42, x1 - 14, y1 - 12), fill=colour)
        draw.text((x1 - 150, y1 - 36), f"GATE {verdict}", fill=BG,
                  font=font(15, bold=True))
        delta = int(row.get("q_delta", 0) or 0)
        reward = int(row.get("reward", 0) or 0)
        draw.text((x0 + 12, y1 - 36),
                  f"recompensa {reward:+d}     ΔQ {delta:+d}",
                  fill=OK if delta else DIM, font=font(15 if self.presentation else 13,
                                                       mono=True))

    def _header(self, draw: ImageDraw.ImageDraw, row: dict, origin: str, case: str) -> None:
        width = self.size[0]
        draw.rectangle((0, 0, width, 34), fill=PANEL)
        draw.text((14, 8), "echoAI · GUI-4", fill=TEXT, font=font(15, bold=True))
        title = str(row.get("task", "") or case or "")
        draw.text((160, 10), title[:80], fill=DIM, font=font(12))
        stamp = f"{origin}  ·  turno {row.get('turn', '—')}"
        face = font(13, bold=True)
        draw.text((width - 14 - _text_width(draw, stamp, face), 9), stamp,
                  fill=GOLD, font=face)

    # ----------------------------------------------------------------- frame

    def render(self, history: SpikeHistory, row: Optional[dict],
               origin: str = "", case: str = "") -> Image.Image:
        width, height = self.size
        image = Image.new("RGB", (width, height), BG)
        draw = ImageDraw.Draw(image)
        row = row or {}
        self._header(draw, row, origin, case)
        gap, top = 10, 44
        # Panels are laid out from a budget, so a small or briefly-zero-sized
        # window degrades to fewer panels instead of an inverted rectangle.
        budget = height - top - gap * 3
        if budget < 90:
            self._control(draw, (gap, top, width - gap, height - gap), row)
            return image
        strip = max(110, min(150, int(budget * 0.24)))
        control = max(120, min(210, int(budget * 0.30)))
        raster_h = budget - strip - control
        if raster_h >= 90:
            self._raster(draw, (gap, top, width - gap, top + raster_h), history)
            mid = top + raster_h + gap
        else:
            raster_h, mid = 0, top
        rates_w = int((width - gap * 3) * 0.42)
        self._rates(draw, (gap, mid, gap + rates_w, mid + strip), history)
        self._wsp(draw, (gap * 2 + rates_w, mid, width - gap, mid + strip), row)
        self._control(draw, (gap, mid + strip + gap, width - gap, height - gap), row)
        return image
