"""Development-only comparison of v5.8 and ablations, with visible decision logs.

python -m echo_arc.temporal_bench gym --agents v5.7 v5.8 --versions 3 --seeds 0 4 --reps 0
No exam split: gym seeds are restricted to training 0..39.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import platform
from pathlib import Path
import time

from echo_arc.observe import Journal, ROOT


_GAMES = {}


def _gym_env(version, seed):
    from seed import arc3gym as gym
    gym.VERSION = version
    key = (version, seed)
    if key not in _GAMES:
        env = gym.GymEnv(seed)
        _GAMES[key] = env.game
        return env
    env = gym.GymEnv.__new__(gym.GymEnv)
    env.game = _GAMES[key]
    env.game_id, env.baseline_actions = env.game.game_id, env.game.baseline
    env.level, env.s = 0, None
    return env


def measure(job):
    from echo_arc import agent, runner
    from echo_arc.temporal_runner import play
    agent._COMP_CACHE.clear()
    mode, name, version, seed, rep, budget, out, env_dir, game_id = job
    if mode == "gym":
        env = _gym_env(version, seed)
        game_id = env.game_id
        baseline = env.baseline_actions
        family = env.game.fam
    else:
        import arc_agi
        arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
        desc = {e.game_id: e for e in arc.get_environments()}[game_id]
        env = arc.make(game_id)
        baseline, family = list(desc.baseline_actions or []), "official-development"
    path = Path(out) / f"{name}-r{rep}" / game_id
    journal = Journal(path / "arc-decisions.jsonl")
    journal.write(kind="start", origin="DEVELOPMENT", agent=name, budget=budget,
                  mission="Medir memoria de orden/conteo mediante acciones y resultados observados.")
    journal.write(kind="game", game=game_id)
    try:
        rec = play(env, budget, runner.seed_for(game_id, rep), agent_name=name, journal=journal)
        score = runner.official_game_score(rec["actions_per_level"], baseline)
        rec.update(game=game_id, agent=name, rep=rep, official_score=score,
                   origin="DEVELOPMENT", baseline=baseline)
        record = path / "record.json"
        record.write_text(json.dumps(rec) + "\n")
        journal.write(kind="game_end", game=game_id, levels=rec["levels_completed"],
                      actions=len(rec["actions"]), resets=rec["resets"])
        journal.write(kind="end", status="complete")
    except BaseException as exc:
        journal.write(kind="end", status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        journal.close()
    temporal = rec.get("model", {}).get("temporal", {})
    return dict(agent=name, game=game_id, version=version, seed=seed, rep=rep,
                family=family, levels=rec["levels_completed"], of=rec["win_levels"],
                score=score, actions=len(rec["actions"]), decisions=len(rec["actions"]) - rec["resets"],
                resets=rec["resets"], temporal_steps=temporal.get("steps", 0),
                orders=temporal.get("orders", []), thresholds=temporal.get("thresholds", []),
                record=str(record.relative_to(ROOT)), record_sha256=hashlib.sha256(record.read_bytes()).hexdigest())


def summarize(rows):
    groups = {}
    for row in rows:
        key = (row["agent"], row["version"])
        g = groups.setdefault(key, dict(agent=key[0], version=key[1], games=0, levels=0,
                                      of=0, score_sum=0, decisions=0, actions=0, resets=0, families={}))
        g["games"] += 1
        for name in ("levels", "of", "decisions", "actions", "resets"):
            g[name] += row[name]
        g["score_sum"] += row["score"]
        f = g["families"].setdefault(row["family"], dict(games=0, levels=0, of=0, score_sum=0))
        f["games"] += 1
        f["levels"] += row["levels"]
        f["of"] += row["of"]
        f["score_sum"] += row["score"]
    for g in groups.values():
        g["mean_score"] = g.pop("score_sum") / g["games"]
        for f in g["families"].values():
            f["mean_score"] = f.pop("score_sum") / f["games"]
    return list(groups.values())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("gym", "offline"))
    ap.add_argument("--agents", nargs="+", default=["v5.7", "v5.8"])
    ap.add_argument("--versions", nargs="+", type=int, choices=(2, 3), default=[3])
    ap.add_argument("--seeds", nargs="+", type=int, default=list(range(40)))
    ap.add_argument("--reps", nargs="+", type=int, default=[0, 1, 2])
    ap.add_argument("--budget", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--env-dir", default=str(ROOT / "lab/arc3/environment_files"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    from echo_arc.temporal_runner import agent_class
    for name in args.agents:
        agent_class(name)
    if args.budget < 1 or args.workers < 1 or any(s not in range(40) for s in args.seeds):
        ap.error("positive budgets/workers and training seeds 0..39 required")
    if any(len(values) != len(set(values)) for values in (args.agents, args.reps, args.seeds, args.versions)):
        ap.error("duplicate agents/reps/seeds/versions would overwrite records")
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = ["echo_arc/agent.py", "echo_arc/runner.py", "seed/arc3gym.py",
               "echo_arc/temporal_memory.py", "echo_arc/temporal_agent.py", "echo_arc/temporal_runner.py",
               "echo_arc/temporal_bench.py", "echo_arc/observe.py", "observe.py", "docs/ECHO45-H1-H3-DESIGN.md"]
    import numpy as np
    profile = {"origin": "DEVELOPMENT", "started": datetime.now(timezone.utc).isoformat(),
               "python": platform.python_version(), "numpy": np.__version__,
               "configuration": vars(args), "sources": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}}
    (out / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    if args.mode == "gym":
        cases = [(v, s, None) for v in args.versions for s in args.seeds]
    else:
        import arc_agi
        arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=args.env_dir)
        cases = [(0, 0, e.game_id) for e in arc.get_environments()]
        if len(cases) != 8:
            raise ValueError("official development expects exactly the existing eight environments")
    jobs = [(args.mode, name, v, s, rep, args.budget, str(out), args.env_dir, game)
            for name in args.agents for v, s, game in cases for rep in args.reps]
    rows = []
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(measure, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps({"done": len(rows), "total": len(jobs), "agent": row["agent"],
                              "game": row["game"], "rep": row["rep"], "levels": row["levels"],
                              "score": round(row["score"], 4)}), flush=True)
    rows.sort(key=lambda r: (r["agent"], r["version"], r["seed"], r["game"], r["rep"]))
    changed = [p for p, h in profile["sources"].items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    if changed:
        raise RuntimeError(f"source changed during development comparison: {changed}")
    result = dict(origin="DEVELOPMENT", seconds=time.monotonic() - started,
                  sources_unchanged=True, summaries=summarize(rows), rows=rows)
    (out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summaries"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
