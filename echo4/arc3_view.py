"""See what ECHO saw and did in an ARC-AGI-3 game: replay a recorded game and draw every frame.

    (ARC venv) python -m echoai.echo4.arc3_view RECORD.json OUT.gif [--every 1] [--max 600] [--scale 6]

The record is any of our game records (exam-v1/v2, llm-exam, echo-arc offline_records): it holds the
action sequence and the hash of every frame. The game is deterministic, so replaying the actions
regenerates the exact frames; each regenerated frame is checked against its recorded hash.
Each GIF frame shows: the grid (ARC palette), the step, the action (key or click), a cross where it
clicked, the levels completed, and RESET / GAME OVER / LEVEL UP marks.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from echoai.echo4.arc3_agent import _act, arcade, frame_hash

PALETTE = ["#000000", "#0074D9", "#FF4136", "#2ECC40", "#FFDC00", "#AAAAAA", "#F012BE", "#FF851B",
           "#7FDBFF", "#870C25", "#39CCCC", "#01FF70", "#85144b", "#B10DC9", "#FFFFFF", "#3D9970"]
RGB = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in PALETTE], dtype=np.uint8)
NAMES = {1: "ACTION1 (up?)", 2: "ACTION2 (down?)", 3: "ACTION3 (left?)", 4: "ACTION4 (right?)",
         5: "ACTION5", 7: "ACTION7"}


def render(frame, scale, caption, click=None, banner=None):
    img = Image.fromarray(RGB[np.asarray(frame) & 15]).resize((64 * scale, 64 * scale), Image.NEAREST)
    canvas = Image.new("RGB", (img.width, img.height + 34), "white")
    canvas.paste(img, (0, 34))
    d = ImageDraw.Draw(canvas)
    d.text((6, 4), caption, fill="black")
    if banner:
        d.text((6, 18), banner, fill="red")
    if click:
        x, y = click
        cx, cy = x * scale + scale // 2, 34 + y * scale + scale // 2
        d.line((cx - 8, cy, cx + 8, cy), fill="lime", width=3)
        d.line((cx, cy - 8, cx, cy + 8), fill="lime", width=3)
    return canvas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record")
    ap.add_argument("out")
    ap.add_argument("--every", type=int, default=1, help="keep one frame of every N")
    ap.add_argument("--max", type=int, default=600, help="at most N steps")
    ap.add_argument("--scale", type=int, default=6)
    ap.add_argument("--ms", type=int, default=120)
    args = ap.parse_args(argv)
    rec = json.loads(Path(args.record).read_text())
    arc = arcade()
    env = arc.make(rec["game"])
    obs = env.reset()
    frame = np.array(obs.frame[-1])
    frames = [render(frame, args.scale, "%s  step 0  levels 0/%s" % (rec["game"][:4], rec.get("win_levels", "?")))]
    mismatches = 0 if frame_hash(frame) == rec["frames"][0] else 1
    level = 0
    for i, (kind, value, xy) in enumerate(rec["actions"][: args.max], start=1):
        obs = _act(env, (kind, value, tuple(xy) if xy else None))
        frame = np.array(obs.frame[-1])
        if i < len(rec["frames"]) and frame_hash(frame) != rec["frames"][i]:
            mismatches += 1
        new_level = int(obs.levels_completed)
        banner = "LEVEL UP -> %d" % new_level if new_level > level else ("RESET" if kind == "R" else
                  ("GAME OVER" if obs.state.name == "GAME_OVER" else None))
        level = new_level
        label = "RESET" if kind == "R" else ("CLICK x=%d y=%d" % tuple(xy) if kind == "C" else NAMES.get(value, "ACTION%d" % value))
        if i % args.every == 0 or banner:
            frames.append(render(frame, args.scale, "%s  step %d  %s  levels %d/%s" %
                                 (rec["game"][:4], i, label, level, rec.get("win_levels", "?")),
                                 click=tuple(xy) if kind == "C" else None, banner=banner))
            if banner:
                frames += [frames[-1]] * 6                    # hold important moments
    frames[0].save(args.out, save_all=True, append_images=frames[1:], duration=args.ms, loop=0, optimize=True)
    print(json.dumps({"gif": args.out, "frames": len(frames), "steps": min(len(rec["actions"]), args.max),
                      "hash_mismatches": mismatches}))


if __name__ == "__main__":
    raise SystemExit(main())
