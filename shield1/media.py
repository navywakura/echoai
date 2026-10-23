"""SHIELD-1 GIFs: the same world played by two policies, side by side.

    PYTHONPATH=. ~/.venvs/shield1/bin/python -m echoai.shield1.media gym --out DIR
    PYTHONPATH=.:~/src/ai-safety-gridworlds ~/.venvs/asg/bin/python -m echoai.shield1.media grid --out DIR

Each panel carries the policy, the step, the cost (or harms) so far and the
gate's verdict on that step, so a viewer sees where the gate acted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

GYM_SEED = 4000                      # first eval world
GRID_SEED = 500                      # first eval training seed


def _font(size: int):
    for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


COLORS = {"OK": (60, 170, 90), "MODIFY": (230, 160, 30), "BLOCK": (210, 50, 50), None: (120, 120, 120)}


def panel(img: np.ndarray, title: str, line: str, verdict: Optional[str], scale: int = 1) -> Image.Image:
    im = Image.fromarray(img).convert("RGB")
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    w, h = im.size
    out = Image.new("RGB", (w, h + 56), (20, 22, 26))
    out.paste(im, (0, 56))
    d = ImageDraw.Draw(out)
    d.text((8, 4), title, fill=(240, 240, 240), font=_font(17))
    d.text((8, 30), line, fill=(200, 200, 200), font=_font(13))
    if verdict:
        tw = d.textlength(verdict, font=_font(14))
        d.rectangle((w - tw - 18, 28, w - 4, 50), fill=COLORS.get(verdict, (120, 120, 120)))
        d.text((w - tw - 11, 30), verdict, fill=(255, 255, 255), font=_font(14))
    return out


def save_gif(frames: List[Image.Image], path: Path, ms: int) -> None:
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=True)


def side_by_side(a: List[Image.Image], b: List[Image.Image]) -> List[Image.Image]:
    n = max(len(a), len(b))
    a = a + [a[-1]] * (n - len(a))
    b = b + [b[-1]] * (n - len(b))
    out = []
    for x, y in zip(a, b):
        im = Image.new("RGB", (x.width + y.width + 8, max(x.height, y.height)), (20, 22, 26))
        im.paste(x, (0, 0))
        im.paste(y, (x.width + 8, 0))
        out.append(im)
    return out


# ---------------------------------------------------------------- Safety-Gymnasium
def gym(out: Path, tasks: Tuple[str, ...], every: int = 8) -> List[dict]:
    from echoai.shield1.bench import TRAIN, load_ppo
    from echoai.shield1.run import VERDICTS, episode, make, train
    rec = []
    for task in tasks:
        gate, _ = train(task, TRAIN)
        env = make(task, render=True)
        runs = {}
        for pol, g, actor in (("SEEK", None, None), ("ECHO-L", gate, None), ("PPO-Lag", None, load_ppo(task)[0])):
            if pol == "PPO-Lag" and actor is None:
                continue
            fr: list = []
            res = episode(env, task, pol, GYM_SEED, g, fr, every, actor)
            runs[pol] = (res, [panel(img, f"{pol} · {task.replace('Safety', '').replace('-v0', '')}",
                                     f"paso {t:4d}   coste {c:3d}   metas {gl}", VERDICTS.get(v))
                               for img, t, c, v, gl in fr])
        env.close()
        name = task.replace("Safety", "").replace("-v0", "").lower()
        save_gif(side_by_side(runs["SEEK"][1], runs["ECHO-L"][1]), out / f"gym-{name}-seek-vs-echo.gif", 80)
        if "PPO-Lag" in runs:
            save_gif(side_by_side(runs["PPO-Lag"][1], runs["ECHO-L"][1]), out / f"gym-{name}-ppolag-vs-echo.gif", 80)
        rec.append({"task": task, "seed": GYM_SEED, **{p: r[0] for p, r in runs.items()}})
    return rec


# ---------------------------------------------------------------- AI Safety Gridworlds
def _grid_img(img: np.ndarray) -> np.ndarray:
    return np.asarray(img).transpose(1, 2, 0) if np.asarray(img).shape[0] == 3 else np.asarray(img)


def grid(out: Path, envs: Tuple[str, ...], learn_eps: int = 8, test_eps: int = 3) -> List[dict]:
    """First learn_eps training episodes (where safe exploration shows), then
    test_eps test episodes after 1000 training episodes. Same seeds both sides."""
    from echoai.shield1 import grid as G
    rec = []
    for name in envs:
        train_kw, test_kw, terrain = G.ENVS[name]
        runs = {}
        for kind in ("Q", "ECHO-L"):
            env = G.make(name, train_kw)
            codes = G._codes(env)
            tc = {codes[c] for c in set(terrain) if c in codes}
            agent = G.Agent(kind, GRID_SEED)
            agent.wall = codes.get("#")
            frames: list = []
            harms = 0
            for i in range(G.EPISODES):
                fr = [] if i < learn_eps else None
                e = G.episode(env, agent, codes, tc, GRID_SEED * 100000 + i, fr)
                if fr is not None:
                    frames.append([])
                    for img, t, ret, v, h in fr:
                        frames[-1].append(panel(_grid_img(img), kind,
                                            f"aprende {i + 1} · paso {t} · daños {harms + h}",
                                            v, scale=40))
                harms += e["harms"]
            learn_harms = harms
            agent.learning = False
            tenv = G.make(name, test_kw) if test_kw != train_kw else env
            res = []
            for i in range(test_eps):
                fr = []
                res.append(G.episode(tenv, agent, codes, tc, 10 ** 7 + GRID_SEED * 1000 + i, fr))
                frames.append([])
                for img, t, ret, v, h in fr:
                    frames[-1].append(panel(_grid_img(img), kind, f"prueba {i + 1} · paso {t} · R {ret:g}",
                                        v, scale=40))
            runs[kind] = (res, frames, learn_harms)
        both = [f for qa, qb in zip(runs["Q"][1], runs["ECHO-L"][1]) for f in side_by_side(qa, qb)]
        save_gif(both, out / f"grid-{name}-q-vs-echo.gif", 200)
        rec.append({"env": name, "train_seed": GRID_SEED, "learn_episodes_shown": learn_eps,
                    "train_harms_1000": {k: r[2] for k, r in runs.items()},
                    **{k: [{x: e[x] for x in ("return", "hidden", "harms", "steps")} for e in r[0]]
                       for k, r in runs.items()}})
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("gym", "grid"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.what == "gym":
        from echoai.shield1.bench import TASKS
        rec = gym(out, tuple(a.only or TASKS))
    else:
        from echoai.shield1.grid import ENVS
        rec = grid(out, tuple(a.only or ENVS))
    (out / f"{a.what}-gifs.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
