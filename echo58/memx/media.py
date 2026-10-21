"""MEMORIA-X GIFs: the same exam world played with an empty and with a learned memory.

    # 1. capture frames (MiniGrid venv)
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.memx.media capture --out DIR
    # 2. compose side-by-side GIFs (PIL venv)
    PYTHONPATH=. ~/.venvs/doc/bin/python -m echoai.echo58.memx.media compose --out DIR

Each panel says which memory it started with, the step, and how the episode
ended. Run only after the exam: it replays exam seeds with frozen memories.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES = (("DynObs16", "A2", 901000), ("DistShift2", "A1", 901000),
         ("UnlockPickup", "A2", 901000), ("ShiftTest", "A1", 901000))


def capture(out: Path) -> None:
    import numpy as np
    from .agent import Agent
    from .bench import LAB
    from .memory import Memory
    from .world import make_world
    mem = Memory.load(LAB / "memories" / "aprendida-m01.jsonl")
    out.mkdir(parents=True, exist_ok=True)
    for fam, regime, seed in CASES:
        for arm, agent in (("vacia", Agent()), ("aprendida", Agent(source=mem))):
            frames: list = []
            r = agent.run(make_world(fam, seed, regime), frames=frames)
            np.savez_compressed(out / f"{fam}-{regime}-{arm}.npz", frames=np.stack(frames))
            (out / f"{fam}-{regime}-{arm}.json").write_text(json.dumps(r))
            print(fam, regime, arm, r)


def compose(out: Path) -> None:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    def font(size):
        for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"):
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    f = font(13)
    label = {"vacia": "memoria vacía", "aprendida": "memoria aprendida"}
    for fam, regime, seed in CASES:
        panels = []
        for arm in ("vacia", "aprendida"):
            fr = np.load(out / f"{fam}-{regime}-{arm}.npz")["frames"]
            res = json.loads((out / f"{fam}-{regime}-{arm}.json").read_text())
            end = "meta" if res["success"] else "daño" if res["harm"] else "sin terminar"
            panels.append((arm, fr, end))
        n = max(len(p[1]) for p in panels)
        n_show = min(n, 160)
        idx = [int(k * (n - 1) / max(n_show - 1, 1)) for k in range(n_show)]
        h = max(p[1].shape[1] for p in panels)
        w = max(p[1].shape[2] for p in panels)
        scale = max(1, 260 // max(h, w))
        frames = []
        for k in idx:
            canvas = Image.new("RGB", (2 * w * scale + 30, h * scale + 52), (18, 18, 22))
            d = ImageDraw.Draw(canvas)
            for j, (arm, fr, end) in enumerate(panels):
                t = min(k, len(fr) - 1)
                img = Image.fromarray(fr[t].astype("uint8")).resize((fr.shape[2] * scale, fr.shape[1] * scale), Image.NEAREST)
                x0 = 10 + j * (w * scale + 10)
                canvas.paste(img, (x0, 40))
                d.text((x0, 4), label[arm], fill=(235, 235, 235), font=f)
                tail = f" · {end}" if k >= len(fr) - 1 else ""
                d.text((x0, 21), f"paso {t}{tail}", fill=(170, 200, 255), font=f)
            frames.append(canvas)
        path = out / f"memx-{fam}-{regime}.gif"
        frames[0].save(path, save_all=True, append_images=frames[1:] + [frames[-1]] * 12, duration=90, loop=0)
        frames[-1].save(out / f"memx-{fam}-{regime}.png")
        print(path)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("capture", "compose"))
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    (capture if a.cmd == "capture" else compose)(a.out)


if __name__ == "__main__":
    main()
