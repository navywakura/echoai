"""ENJAMBRE-1 (C v1, redesign) bench: four ECHO agents solve a mission of eight shared worlds
(coop.py) with a private memory each, a global memory of WSP postcards and help between them.

    cd /home/user/REALRXOS/RXos
    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.enjambre.bench dev --macros 1,2,3
    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.enjambre.bench preflight
    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.enjambre.bench exam
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
from .cagent import CAgent
from .coop import KINDS, CoopWorld, language, play_together
from .team import RM, Board, Private, Reader, as_counts, read

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "echo58" / "enjambre"
HERE = Path(__file__).resolve().parent

ARMS = ("enjambre", "sin_global", "sin_ayuda", "sin_privada", "global_barajada", "aislados", "uno_solo")
FLAGS = {  # arm -> (private, global, help)
    "enjambre": (True, True, True), "sin_global": (True, False, True), "sin_ayuda": (True, True, False),
    "sin_privada": (False, True, True), "global_barajada": (True, True, True), "aislados": (True, False, False),
}
N_AGENTS, ROUNDS, PER_KIND = 4, 30, 2
MACROS = tuple(range(1, 21))
BASE = {"dev": 9_100_000, "exam": 9_500_000}
IDS = language()


def mission(phase: str, m: int) -> List[Dict]:
    """Eight shared worlds, two of each kind, in a macro-specific order."""
    b = BASE[phase] + 1000 * m
    kinds = [k for k in KINDS for _ in range(PER_KIND)]
    random.Random(b).shuffle(kinds)
    return [{"kind": k, "seed": b + i} for i, k in enumerate(kinds)]


def run_team(arm: str, phase: str, m: int) -> Dict:
    use_private, use_global, use_help = FLAGS[arm]
    worlds = mission(phase, m)
    n = len(worlds)
    solved: List[Optional[int]] = [None] * n
    failed_eps = [0] * n
    needs = [False] * n
    mine = [Private() for _ in range(N_AGENTS)]
    notes: List[Dict] = [{} for _ in range(N_AGENTS)]
    at: List[Optional[int]] = [None] * N_AGENTS
    board = Board()
    st = {"episodes": 0, "failed": 0, "harm": 0, "postcards": 0, "notes_cards": 0, "helps": 0,
          "asked": 0, "held": 0, "answers": {"here": 0, "private": 0, "notes": 0, "global": 0},
          "by_kind": {k: {"harm": 0, "episodes": 0} for k in KINDS}}
    fresh = iter(range(n))

    def assign(a: int) -> None:
        for w in fresh:
            at[a] = w
            return
        at[a] = None
        open_ = [w for w in range(n) if solved[w] is None]
        if not use_help or not open_:
            return
        w = min(open_, key=lambda x: (not needs[x], -failed_eps[x], x))
        at[a] = w
        st["helps"] += 1
        notes[a] = {}                                      # only the notes of this world (review 21/10)
        got: Dict = {}
        for b in range(N_AGENTS):                          # notes of everyone who played that world
            if b == a:
                continue
            for raw in mine[b].notes_cards(b, w):
                layer, _, key, o, k, total = read(raw)
                got.setdefault((RM, key) if layer == RM else key, []).append((o, k, total))
                st["notes_cards"] += 1
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
        for w in range(n):
            team = [a for a in range(N_AGENTS) if at[a] == w]
            if not team:
                continue
            cw = CoopWorld(worlds[w]["kind"], worlds[w]["seed"], len(team), IDS)
            agents, readers = [], []
            for slot, a in enumerate(team):
                p = mine[a]
                p.world = w
                rd = Reader(p.mem.cfg, p if use_private else None, glob, notes[a], world=w)
                readers.append(rd)
                agents.append(CAgent(source=rd, learn=p, me=slot, private=p))
            res = play_together(cw, agents)
            win = cw.solved_by is not None
            if win and solved[w] is None:
                solved[w] = r
            needs[w] = needs[w] or cw.needs_help
            for a, rd, x in zip(team, readers, res):
                for k in st["answers"]:
                    st["answers"][k] += rd.by_source[k]
                st["episodes"] += 1
                st["harm"] += x["harm"]
                st["asked"] += x["asked"]
                st["held"] += x["held"]
                st["by_kind"][worlds[w]["kind"]]["harm"] += x["harm"]
                st["by_kind"][worlds[w]["kind"]]["episodes"] += 1
                if not win:
                    st["failed"] += 1
                    failed_eps[w] += 1
                played.append(a)
        if use_global:                                     # publish at the end of the round
            for a in played:
                cards = mine[a].l2_cards(a) + mine[a].l1_cards(a) + mine[a].remote_cards(a)
                for raw in cards:
                    board.post(raw)
                st["postcards"] += len(cards)
        for a in range(N_AGENTS):
            if at[a] is None or solved[at[a]] is not None:
                assign(a)
    rounds = [s if s is not None else ROUNDS + 1 for s in solved]
    return {"arm": arm, "macro": m, "phase": phase, "worlds": worlds, "solved_round": rounds,
            "score": sum(rounds), "solved": sum(s is not None for s in solved),
            "destroyed": sum(p.destroyed for p in mine) + board.destroyed,
            "card_bytes": sorted({len(x) for x in board.log}), **st}


def run_solo(phase: str, m: int) -> Dict:
    """One agent, world after world, with the team's whole budget (reported only)."""
    worlds = mission(phase, m)
    p = Private()
    solved: List[Optional[int]] = [None] * len(worlds)
    ep = failed = harm = here = 0
    w = 0
    while ep < N_AGENTS * ROUNDS and w < len(worlds):
        p.world = w
        cw = CoopWorld(worlds[w]["kind"], worlds[w]["seed"], 1, IDS)
        x = play_together(cw, [CAgent(source=Reader(p.mem.cfg, p, None, {}, world=w), learn=p, private=p)])[0]
        ep += 1
        here += 1
        harm += x["harm"]
        if cw.solved_by is not None:
            solved[w] = ep
            w, here = w + 1, 0
        else:
            failed += 1
            if here >= ROUNDS:                             # at most 30 episodes per world
                w, here = w + 1, 0
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
    st["language"] = sorted(IDS.values())
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
            print(f"{arm:16s} solved {sum(x['solved'] for x in rows):3d} episodes {sum(x['episodes'] for x in rows)}"
                  f" failed {sum(x['failed'] for x in rows)} harm {sum(x['harm'] for x in rows)}")
            continue
        kh = {k: sum(x["by_kind"][k]["harm"] for x in rows) for k in KINDS}
        print(f"{arm:16s} score {sum(x['score'] for x in rows):4d} solved {sum(x['solved'] for x in rows):3d}"
              f" failed {sum(x['failed'] for x in rows):4d} harm {sum(x['harm'] for x in rows):4d} {kh}"
              f" asked {sum(x['asked'] for x in rows)} held {sum(x['held'] for x in rows)}")


def cmd_dev(a) -> None:
    LAB.mkdir(parents=True, exist_ok=True)
    macros = [int(x) for x in a.macros.split(",")]
    jobs = [(arm, m, "dev") for m in macros for arm in ARMS]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(job, jobs))
    out = LAB / f"dev2-{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": res}, indent=1))
    print(out)
    summary(res)


def cmd_preflight(a) -> None:
    pf = LAB / "preflight.json"
    if pf.exists():
        raise SystemExit(f"{pf} exists: the freeze is written once")
    LAB.mkdir(parents=True, exist_ok=True)
    doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "frozen": frozen_state(),
           "arms": ARMS, "agents": N_AGENTS, "rounds": ROUNDS, "missions": {m: mission("exam", m) for m in MACROS}}
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
