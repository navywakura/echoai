"""echo-arc · play ARC-AGI-3 games with the ECHO agent, locally or inside the Kaggle submission.

    python -m echo_arc.runner offline ENV_DIR [--games G...] [--budget 2000] [--out DIR]
    python -m echo_arc.runner competition            (inside the Kaggle rerun: gateway at ARC_BASE_URL)

Official ARC Prize 2026 score (rules on Kaggle): per level min(human/agent, 1) squared; per game the
average weighted by level index (1-indexed); total = mean over games.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from echo_arc.agent import Arc3EchoV2, Arc3EchoV3, Arc3EchoV3b, Arc3EchoV4, Arc3EchoV41, Arc3EchoV5, Arc3EchoV51, Arc3EchoV52, Arc3EchoV53, Arc3EchoV54, Arc3EchoV55, Arc3EchoV56, Arc3EchoV57, Arc3EchoV5NoExplore, frame_hash

AGENTS = {"v2": Arc3EchoV2, "v3": Arc3EchoV3, "v3b": Arc3EchoV3b, "v4": Arc3EchoV4, "v4.1": Arc3EchoV41, "v5": Arc3EchoV5, "v5.1": Arc3EchoV51, "v5.2": Arc3EchoV52, "v5.3": Arc3EchoV53, "v5.4": Arc3EchoV54, "v5.5": Arc3EchoV55, "v5.6": Arc3EchoV56, "v5.7": Arc3EchoV57, "v5-noexplore": Arc3EchoV5NoExplore}


def agent_class(name):
    """'v5' or a variant 'v5:ATTR=INT,ATTR=INT' (class attributes only; used to tune on ARC3-GYM)."""
    if ":" not in name:
        return AGENTS[name]
    base, spec = name.split(":", 1)
    attrs = {k: int(v) for k, v in (kv.split("=") for kv in spec.split(","))}
    return type("Variant", (AGENTS[base],), attrs)


def official_game_score(actions_per_level, baseline):
    num = den = 0.0
    for i, human in enumerate(baseline, start=1):
        s = 0.0
        if i <= len(actions_per_level) and actions_per_level[i - 1]:
            s = min(human / actions_per_level[i - 1], 1.0) ** 2
        num += i * s
        den += i
    return 100.0 * num / den if den else 0.0


def _act(env, act):
    from arcengine import GameAction
    kind, value, xy = act
    if kind == "R":
        return env.reset()
    ga = GameAction.from_id(value) if hasattr(GameAction, "from_id") else GameAction(value)
    return env.step(ga, data={"x": int(xy[0]), "y": int(xy[1])}) if kind == "C" else env.step(ga)


def play(env, budget, seed, deadline=None, agent_name="v2"):
    """One game with Arc3EchoV2. Returns a record with actions, frame hashes and levels."""
    from arcengine import GameState
    obs = env.reset()
    frame = np.array(obs.frame[-1])
    agent = agent_class(agent_name)(obs.available_actions, seed, boundary=True)
    rec = {"win_levels": obs.win_levels, "actions": [], "frames": [frame_hash(frame)], "levels": [0], "resets": 0}
    levels, level_actions, per_level = 0, 0, []
    state = agent.observe_state(frame)
    agent.level_start = state
    for _ in range(budget):
        if deadline and time.time() > deadline:
            rec["stopped"] = "deadline"
            break
        act = agent.choose(state)
        obs = _act(env, act)
        if obs is None:
            break
        rec["actions"].append([act[0], act[1], list(act[2]) if act[2] else None])
        level_actions += 1
        if act[0] != "R":
            agent.level_actions.append(act)
        frame = np.array(obs.frame[-1])
        rec["frames"].append(frame_hash(frame))
        rec["levels"].append(int(obs.levels_completed))
        level_up = obs.levels_completed > levels
        game_over = obs.state is GameState.GAME_OVER
        nxt = agent.observe_state(frame)
        agent.learn(state, act, nxt, game_over, level_up)
        if level_up:
            per_level.append(level_actions)
            levels, level_actions = obs.levels_completed, 0
            agent.level_start, agent.level_actions = nxt, []
        if obs.state is GameState.WIN:
            break
        if game_over:
            obs = env.reset()
            rec["resets"] += 1
            rec["actions"].append(["R", 0, None])
            frame = np.array(obs.frame[-1])
            rec["frames"].append(frame_hash(frame))
            rec["levels"].append(int(obs.levels_completed))
            nxt = agent.observe_state(frame)
            agent.level_actions = []
        state = nxt
    rec["levels_completed"], rec["actions_per_level"] = levels, per_level
    if hasattr(agent, "report"):
        rec["model"] = agent.report()
    return rec


def seed_for(game_id, rep=0):
    """rep 0 keeps the historical seed; reps 1, 2… are extra seeds for development (luck vs skill)."""
    tag = "ECHO2" if rep == 0 else "ECHO2-r%d" % rep
    return int(hashlib.sha256((game_id + tag).encode()).hexdigest()[:8], 16)


def run_offline(env_dir, games, budget, out, agent_name="v2", rep=0):
    import arc_agi
    arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=str(env_dir))
    envs = {e.game_id: e for e in arc.get_environments()}
    total, rows = 0.0, []
    for g in games or sorted(envs):
        rec = play(arc.make(g), budget, seed_for(g, rep), agent_name=agent_name)
        rec["game"], rec["agent"], rec["rep"] = g, agent_name, rep
        rec["official_score"] = official_game_score(rec["actions_per_level"], list(envs[g].baseline_actions or []))
        total += rec["official_score"]
        rows.append({"game": g, "levels": rec["levels_completed"], "of": rec["win_levels"],
                     "score": round(rec["official_score"], 4), "actions": len(rec["actions"])})
        if out:
            Path(out).mkdir(parents=True, exist_ok=True)
            (Path(out) / (g + ".json")).write_text(json.dumps(rec))
        print(json.dumps(rows[-1]))
        sys.stdout.flush()
    print(json.dumps({"games": len(rows), "mean_official_score": round(total / max(len(rows), 1), 4),
                      "levels": sum(r["levels"] for r in rows)}))


def run_competition(budget, time_budget_s, agent_name="v2"):
    """Inside the Kaggle rerun: one pass over the gateway's games; the gateway keeps the score."""
    import arc_agi
    base = os.environ.setdefault("ARC_BASE_URL", "http://gateway:8001/")
    os.environ.setdefault("ARC_API_KEY", "test-key-123")
    arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.COMPETITION, arc_base_url=base, environments_dir="")
    games = [e.game_id for e in arc.available_environments]
    start = time.time()
    per_game = time_budget_s / max(len(games), 1)
    for i, g in enumerate(games):
        rec = play(arc.make(g), budget, seed_for(g), deadline=start + per_game * (i + 1), agent_name=agent_name)
        print(json.dumps({"game": g, "levels": rec["levels_completed"], "actions": len(rec["actions"])}))
        sys.stdout.flush()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("offline", "competition"))
    ap.add_argument("env_dir", nargs="?")
    ap.add_argument("--games", nargs="*")
    ap.add_argument("--budget", type=int, default=2000)
    ap.add_argument("--out")
    ap.add_argument("--time-budget-s", type=float, default=7.5 * 3600)
    ap.add_argument("--rep", type=int, default=0, help="extra development seed index (0 = historical)")
    ap.add_argument("--agent", default="v2", help="one of %s, or a variant like v5:MIN_EVIDENCE=4" % ", ".join(AGENTS))
    args = ap.parse_args(argv)
    if args.mode == "offline":
        run_offline(args.env_dir, args.games, args.budget, args.out, args.agent, args.rep)
    else:
        run_competition(args.budget, args.time_budget_s, args.agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
