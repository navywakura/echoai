"""Terminal image rendering and actual telemetry, with honest missing values."""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from rich.style import Style
from rich.text import Text
from rich.tree import Tree

PALETTE = ["#08080c", "#1974e8", "#ed474a", "#43c56e", "#f4d858", "#8a8a9b", "#de68ca",
           "#ee9a44", "#61dce6", "#91334f", "#ffffff", "#ba91ff", "#516373", "#8874ad", "#37413d", "#ddd6f3"]


def grid_text(grid, width=36, height=14):
    if not isinstance(grid, list) or not grid or not isinstance(grid[0], list) or not grid[0]:
        raise ValueError("Se esperaba una rejilla rectangular")
    w, h = len(grid[0]), len(grid)
    if w > 1024 or h > 1024 or any(len(row) != w for row in grid):
        raise ValueError("Rejilla inválida o demasiado grande")
    width, height = max(1, width), max(1, height)
    cols = min(w, width)
    rows = min(h, height * 2)
    out = Text()
    for y in range(0, rows, 2):
        for x in range(cols):
            a = int(grid[min(h - 1, y * h // rows)][x * w // cols])
            b = int(grid[min(h - 1, (y + 1) * h // rows)][x * w // cols])
            out.append("▀", Style(color=PALETTE[a % len(PALETTE)], bgcolor=PALETTE[b % len(PALETTE)]))
        if y + 2 < rows:
            out.append("\n")
    return out


def image_text(path, width=40, height=15):
    file = Path(path).expanduser()
    if file.stat().st_size > 32_000_000:
        raise ValueError("Imagen demasiado grande (máximo 32 MB)")
    with Image.open(file) as source:
        source.thumbnail((max(1, width), max(2, height * 2)))
        img = source.convert("RGB")
        out = Text()
        for y in range(0, img.height, 2):
            for x in range(img.width):
                a, b = img.getpixel((x, y)), img.getpixel((x, min(y + 1, img.height - 1)))
                out.append("▀", Style(color="#%02x%02x%02x" % a, bgcolor="#%02x%02x%02x" % b))
            if y + 2 < img.height:
                out.append("\n")
        return out


def telemetry_tree(row=None, cortex=False, decisions=None, activity=None):
    row = row or {}
    def value(*keys):
        for k in keys:
            if k in row and row[k] is not None:
                return str(row[k])[:78]
        return "sin muestra"
    root = Tree(Text("ECHO / telemetría", style="bold #ba91ff"), guide_style="#574071")
    if decisions is not None:
        observed = root.add(Text("Últimas decisiones · fuente externa", style="#cfb1ff"))
        for line in decisions.lines():
            observed.add(Text(line[:180]))
    if activity:
        process = root.add(Text(activity["kind"] + " / actividad", style="#ffffff"))
        process.add(Text(activity["stage"]))
        if activity["kind"] == "NEOCÓRTEX":
            process.add(Text("Estado de la petición · sin monólogo interno", style="#82758e"))
    core = root.add(Text("Control observado", style="#ffffff"))
    core.add(Text("WSP   " + value("wsp", "frame")))
    memory = core.add(Text("CAM / memoria   " + value("cam_used", "beliefs")))
    memory.add(Text("Q   " + value("q", "q_row")))
    memory.add(Text("T   " + value("t_pred")))
    core.add(Text("VERIFY / gate   " + value("gate", "gate_decision")))
    core.add(Text("Acción   " + value("action_name", "action")))
    monitor = root.add(Text("Monitor neuronal · no es la política", style="#c8b6df"))
    for key, title in (("lif_a", "LIF A"), ("lif_b", "LIF B"), ("alif_spikes", "Adaptive LIF")):
        values = row.get(key)
        if isinstance(values, list) and values:
            chunks = [values[i:i + max(1, len(values) // 20)] for i in range(0, len(values), max(1, len(values) // 20))]
            rates = [sum(v) / len(v) for v in chunks]
            peak = max(rates) or 1
            raster = "".join("▁▂▃▄▅▆▇█"[min(7, int(v / peak * 7))] for v in rates)
            monitor.add(Text(f"{title} {len(values)} · {raster}", style="#ba91ff"))
        else:
            monitor.add(Text(title + " · sin muestra", style="#82758e"))
    root.add(Text("Neocórtex lingüístico · " + ("conectado / propuestas" if cortex else "desconectado")))
    return root
