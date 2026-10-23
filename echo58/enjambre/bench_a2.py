"""ENJAMBRE-1 (C v1), FIRST design (A2 MiniGrid missions; closed in development, see ENJAMBRE1-DEV-NOTE.md).
(contract ENJAMBRE1-DESIGN.md).

    cd /home/user/REALRXOS/RXos
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.enjambre.bench_a2 dev --macros 1,2,3
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.enjambre.bench_a2 preflight
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.enjambre.bench_a2 exam
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

from ..acumula3 import bench as B3
from ..b3.policy import PIECES, PAgent
from .team import Board, Private, Reader, as_counts, read

W = B3.W
ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "echo58" / "enjambre"
HERE = Path(__file__).resolve().parent

FAMILIES = {
    "dev": ("DoorKey5", "LavaGapS5", "SimpleCrossingS9N2", "KeyCorridorS3R2",
            "BlockedUnlockPickup", "DistShift1", "DynObs5", "FourRooms"),
    "exam": ("DoorKey16", "SimpleCrossingS9N3", "SimpleCrossingS11N5", "MultiRoomN2S4",
             "MultiRoomN4S5", "RedBlueDoors6", "KeyCorridorS4R3", "LockedRoom"),
}
W.MINIGRID.update({
    "DoorKey5": "MiniGrid-DoorKey-5x5-v0", "LavaGapS5": "MiniGrid-LavaGapS5-v0",
    "SimpleCrossingS9N2": "MiniGrid-SimpleCrossingS9N2-v0", "KeyCorridorS3R2": "MiniGrid-KeyCorridorS3R2-v0",
    "BlockedUnlockPickup": "MiniGrid-BlockedUnlockPickup-v0", "DistShift1": "MiniGrid-DistShift1-v0",
    "DynObs5": "MiniGrid-Dynamic-Obstacles-5x5-v0", "FourRooms": "MiniGrid-FourRooms-v0",
    "DoorKey16": "MiniGrid-DoorKey-16x16-v0", "SimpleCrossingS9N3": "MiniGrid-SimpleCrossingS9N3-v0",
    "SimpleCrossingS11N5": "MiniGrid-SimpleCrossingS11N5-v0", "MultiRoomN2S4": "MiniGrid-MultiRoom-N2-S4-v0",
    "MultiRoomN4S5": "MiniGrid-MultiRoom-N4-S5-v0", "RedBlueDoors6": "MiniGrid-RedBlueDoors-6x6-v0",
    "KeyCorridorS4R3": "MiniGrid-KeyCorridorS4R3-v0", "LockedRoom": "MiniGrid-LockedRoom-v0",
})

ARMS = ("enjambre", "sin_global", "sin_ayuda", "sin_privada", "global_barajada", "aislados", "uno_solo")
FLAGS = {  # arm -> (private, global, help)
    "enjambre": (True, True, True), "sin_global": (True, False, True), "sin_ayuda": (True, True, False),
    "sin_privada": (False, True, True), "global_barajada": (True, True, True), "aislados": (True, False, False),
}
N_AGENTS, ROUNDS = 4, 30
MACROS = tuple(range(1, 21))
BASE = {"dev": 9_100_000, "exam": 9_500_000}


def mission(phase: str, m: int) -> List[Dict]:
    """Eight fixed worlds (family, seed), one per family, in a macro-specific order."""
    b = BASE[phase] + 1000 * m
    fams = list(FAMILIES[phase])
    random.Random(b).shuffle(fams)
    return [{"family": f, "seed": b + i} for i, f in enumerate(fams)]


def play(ag: PAgent, world: Dict) -> Dict:
    w = W.make_world(world["family"], world["seed"], "A2")
    r = ag.run(w)
    w.close()
    r.pop("failures", None)
    r.pop("signals", None)
    return r


def run_team(arm: str, phase: str, m: int) -> Dict:
    use_private, use_global, use_help = FLAGS[arm]
    worlds = mission(phase, m)
    solved: List[Optional[int]] = [None] * len(worlds)
    failed_eps = [0] * len(worlds)
    owner: List[Optional[int]] = [None] * len(worlds)      # who took the world first
    mine = [Private() for _ in range(N_AGENTS)]
    notes: List[Dict] = [{} for _ in range(N_AGENTS)]
    at: List[Optional[int]] = [None] * N_AGENTS
    board = Board()
    stats = {"episodes": 0, "failed": 0, "harm": 0, "postcards": 0, "notes_cards": 0, "helps": 0,
             "answers": {"private": 0, "notes": 0, "global": 0}}
    fresh = iter(range(len(worlds)))

    def assign(a: int) -> None:
        for w in fresh:
            owner[w] = a
            at[a] = w
            return
        at[a] = None
        if not use_help:
            return
        open_ = [w for w in range(len(worlds)) if solved[w] is None]
        if not open_:
            return
        w = min(open_, key=lambda x: (-failed_eps[x], x))
        at[a] = w
        stats["helps"] += 1
        got: Dict = {}
        for b in range(N_AGENTS):                          # notes of everyone who played that world
            if b == a or w not in mine[b].by_world:
                continue
            for raw in mine[b].notes_cards(b, w):
                _, _, key, o, n, total = read(raw)
                got.setdefault(key, []).append((o, n, total))
                stats["notes_cards"] += 1
        for key, entries in got.items():
            notes[a][key] = as_counts(entries)

    for a in range(N_AGENTS):
        assign(a)
    for r in range(1, ROUNDS + 1):
        if all(s is not None for s in solved):
            break
        glob = board.view(shuffle_seed=BASE[phase] * 31 + m * 97 + r if arm == "global_barajada" else None) \
            if use_global else None
        played = []
        for a in range(N_AGENTS):
            w = at[a]
            if w is None:
                continue
            p = mine[a]
            p.world = w
            reader = Reader(p.mem.cfg, p if use_private else None, glob, notes[a])
            ag = PAgent(source=reader, learn=p, pieces=frozenset(PIECES))
            res = play(ag, worlds[w])
            for k in stats["answers"]:
                stats["answers"][k] += reader.by_source[k]
            stats["episodes"] += 1
            stats["harm"] += res["harm"]
            if res["success"]:
                if solved[w] is None:
                    solved[w] = r
            else:
                stats["failed"] += 1
                failed_eps[w] += 1
            played.append(a)
        if use_global:                                     # publish at the end of the round
            for a in played:
                cards = mine[a].l2_cards(a) + (mine[a].l1_cards(a) if not use_private else [])
                for raw in cards:
                    board.post(raw)
                stats["postcards"] += len(cards)
        for a in range(N_AGENTS):
            if at[a] is None or solved[at[a]] is not None:
                assign(a)
    rounds = [s if s is not None else ROUNDS + 1 for s in solved]
    return {"arm": arm, "macro": m, "phase": phase, "worlds": worlds, "solved_round": rounds,
            "score": sum(rounds), "solved": sum(s is not None for s in solved),
            "destroyed": sum(p.destroyed for p in mine) + board.destroyed,
            "card_bytes": sorted({len(x) for x in board.log}), **stats}


def run_solo(phase: str, m: int) -> Dict:
    """One agent, world after world, with the team's whole budget (reported only)."""
    worlds = mission(phase, m)
    p = Private()
    solved: List[Optional[int]] = [None] * len(worlds)
    ep = failed = harm = 0
    w = 0
    while ep < N_AGENTS * ROUNDS and w < len(worlds):
        p.world = w
        reader = Reader(p.mem.cfg, p, None, {})
        res = play(PAgent(source=reader, learn=p, pieces=frozenset(PIECES)), worlds[w])
        ep += 1
        harm += res["harm"]
        if res["success"]:
            solved[w] = ep
            w += 1
        else:
            failed += 1
    return {"arm": "uno_solo", "macro": m, "phase": phase, "worlds": worlds,
            "solved_episode": [s if s is not None else N_AGENTS * ROUNDS + 1 for s in solved],
            "solved": sum(s is not None for s in solved), "episodes": ep, "failed": failed,
            "harm": harm, "destroyed": p.destroyed}


def job(args) -> Dict:
    arm, m, phase = args
    t = time.time()
    try:
        out = run_solo(phase, m) if arm == "uno_solo" else run_team(arm, phase, m)
    except Exception:
        import traceback
        out = {"arm": arm, "macro": m, "crash": traceback.format_exc()}
    out["secs"] = int(time.time() - t)
    return out


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_state() -> Dict:
    st = B3.frozen_state()
    st["enjambre"] = {p.name: sha(p) for p in sorted(HERE.glob("*.py"))}
    st["enjambre_contract"] = sha(ROOT / "ECHO-5.8" / "docs" / "ENJAMBRE1-DESIGN.md")
    st["enjambre_tests"] = sha(ROOT / "tests" / "test_echo58_enjambre.py")
    st["wsp"] = sha(ROOT.parent / "navi10_wsp.py")
    st["families"] = {k: W.MINIGRID[k] for k in sorted(W.MINIGRID)}
    return st


def summary(res: List[Dict]) -> None:
    for arm in ARMS:
        rows = [x for x in res if x["arm"] == arm]
        for x in rows:
            if "crash" in x:
                print(f"{arm} m{x['macro']} CRASHED:", x["crash"].splitlines()[-1])
        rows = [x for x in rows if "crash" not in x]
        if not rows:
            continue
        if arm == "uno_solo":
            print(f"{arm:16s} solved {[x['solved'] for x in rows]} episodes {[x['episodes'] for x in rows]}"
                  f" failed {sum(x['failed'] for x in rows)} harm {sum(x['harm'] for x in rows)}")
            continue
        print(f"{arm:16s} score {[x['score'] for x in rows]} solved {[x['solved'] for x in rows]}"
              f" failed {sum(x['failed'] for x in rows)} harm {sum(x['harm'] for x in rows)}"
              f" global {sum(x['answers']['global'] for x in rows)}")


def cmd_dev(a) -> None:
    LAB.mkdir(parents=True, exist_ok=True)
    macros = [int(x) for x in a.macros.split(",")]
    jobs = [(arm, m, "dev") for m in macros for arm in ARMS]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(job, jobs))
    out = LAB / f"dev-{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": res}, indent=1))
    print(out)
    summary(res)


def cmd_preflight(a) -> None:
    pf = LAB / "preflight.json"
    if pf.exists():
        raise SystemExit(f"{pf} exists: the freeze is written once")
    LAB.mkdir(parents=True, exist_ok=True)
    doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "frozen": frozen_state(),
           "arms": ARMS, "agents": N_AGENTS, "rounds": ROUNDS, "families": FAMILIES["exam"],
           "missions": {m: mission("exam", m) for m in MACROS}}
    doc["missions_sha256"] = hashlib.sha256(json.dumps(doc["missions"], sort_keys=True).encode()).hexdigest()
    pf.write_text(json.dumps(doc, indent=1, sort_keys=True))
    print(pf, doc["missions_sha256"])


def cmd_exam(a) -> None:
    pf = json.loads((LAB / "preflight.json").read_text())
    if pf["frozen"] != json.loads(json.dumps(frozen_state())):
        raise SystemExit("something frozen changed since preflight: refusing to examine")
    out = LAB / "exam"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: the exam runs once")
    out.mkdir(exist_ok=True)
    jobs = [(arm, m, "exam") for m in MACROS for arm in ARMS]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for r in ex.map(job, jobs):
            (out / f"{r['arm']}-m{r['macro']:02d}.json").write_text(json.dumps(r, indent=1))
            print("done", r["arm"], r["macro"], r["secs"], "CRASH" if "crash" in r else "", flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("dev", "preflight", "exam"))
    ap.add_argument("--jobs", type=int, default=11)
    ap.add_argument("--macros", default="1,2,3")
    a = ap.parse_args(argv)
    {"dev": cmd_dev, "preflight": cmd_preflight, "exam": cmd_exam}[a.cmd](a)


if __name__ == "__main__":
    main()
