"""Recompute development receipts from records and chained observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from echo_arc.observe import ROOT


def verify_row(row):
    record = ROOT / row["record"]
    raw = record.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == row["record_sha256"], str(record)
    rec = json.loads(raw)
    frames, actions, per_level = [], [], []
    resets = decisions = level_actions = levels = 0
    prev, index = "0" * 64, 0
    for line in record.with_name("arc-decisions.jsonl").open():
        r = json.loads(line)
        digest = r.pop("hash")
        payload = json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        assert hashlib.sha256(payload.encode()).hexdigest() == digest, (record, index)
        assert r["prev"] == prev and r["index"] == index, (record, index)
        prev, index = digest, index + 1
        if r["kind"] == "observation":
            frames.append(r["frame"])
        elif r["kind"] == "decision":
            actions.append(r["action"])
            decisions += 1
            level_actions += 1
        elif r["kind"] == "result":
            assert r["action"] == actions[-1]
            if r["level_up"]:
                levels += 1
                per_level.append(level_actions)
                level_actions = 0
            if r["game_over"]:
                resets += 1
                actions.append(["R", 0, None])
    assert frames == rec["frames"] and actions == rec["actions"], str(record)
    assert per_level == rec["actions_per_level"] and levels == rec["levels_completed"]
    assert resets == rec["resets"] and decisions == len(actions) - resets
    assert len(frames) == len(actions) + 1
    assert row["levels"] == levels and row["resets"] == resets and row["decisions"] == decisions
    assert row["actions"] == len(actions) and row["agent"] == rec["agent"] and row["rep"] == rec["rep"]
    assert row["game"] == rec["game"] and row["of"] == rec["win_levels"]
    num = den = 0
    for i, human in enumerate(rec["baseline"], 1):
        score = min(human / per_level[i - 1], 1) ** 2 if i <= len(per_level) and per_level[i - 1] else 0
        num += i * score
        den += i
    computed = 100 * num / den if den else 0
    assert abs(computed - rec["official_score"]) < 1e-10
    assert abs(computed - row["score"]) < 1e-10
    return index


def replay_row(row, env_dir, budget):
    from echo_arc import agent, runner
    from echo_arc.temporal_runner import play
    old_version = None
    try:
        if row["version"]:
            from seed import arc3gym as gym
            old_version = gym.VERSION
            gym.VERSION = row["version"]
            env = gym.GymEnv(row["seed"])
        else:
            import arc_agi
            arc = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
            env = arc.make(row["game"])
        original = json.loads((ROOT / row["record"]).read_text())
        agent._COMP_CACHE.clear()
        replay = play(env, budget,
                      runner.seed_for(row["game"], row["rep"]), agent_name=row["agent"])
        # The stored format converts nested hypothesis tuples to JSON arrays.
        replay = json.loads(json.dumps(replay))
        expected = {k: original[k] for k in replay}
        assert replay == expected, f"replay differs: {row['record']}"
    finally:
        if old_version is not None:
            gym.VERSION = old_version


def main(argv=None):
    if not __debug__:
        raise RuntimeError("audit requires Python assertions enabled")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory")
    ap.add_argument("--replays", type=int, default=0)
    args = ap.parse_args(argv)
    if args.replays < 0:
        ap.error("replays must be nonnegative")
    base = Path(args.directory).resolve()
    summary = json.loads((base / "summary.json").read_text())
    profile = json.loads((base / "profile.json").read_text())
    hashes = profile["sources"]
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in hashes.items())
    rows = summary["rows"]
    cfg = profile["configuration"]
    expected = len(cfg["agents"]) * len(cfg["reps"]) * (len(cfg["seeds"]) * len(cfg["versions"]) if cfg["mode"] == "gym" else 8)
    assert len(rows) == expected
    assert len({r["record"] for r in rows}) == len(rows)
    if cfg["mode"] == "gym":
        planned = {(a, v, s, rep) for a in cfg["agents"] for v in cfg["versions"]
                   for s in cfg["seeds"] for rep in cfg["reps"]}
        assert {(r["agent"], r["version"], r["seed"], r["rep"]) for r in rows} == planned
    for group in summary["summaries"]:
        members = [r for r in rows if (r["agent"], r["version"]) == (group["agent"], group["version"])]
        assert group["games"] == len(members)
        for k in ("levels", "of", "actions", "decisions", "resets"):
            assert group[k] == sum(r[k] for r in members)
        assert abs(group["mean_score"] - sum(r["score"] for r in members) / len(members)) < 1e-10
        for family, f in group["families"].items():
            cases = [r for r in members if r["family"] == family]
            assert f["games"] == len(cases) and f["levels"] == sum(r["levels"] for r in cases)
            assert f["of"] == sum(r["of"] for r in cases)
            assert abs(f["mean_score"] - sum(r["score"] for r in cases) / len(cases)) < 1e-10
    events = sum(verify_row(row) for row in rows)
    chosen = []
    for row in rows:
        key = (row["agent"], row["family"])
        if row["rep"] == 0 and key not in {(r["agent"], r["family"]) for r in chosen}:
            chosen.append(row)
    chosen.sort(key=lambda row: (row["family"], row["agent"]))
    replayed = chosen[:args.replays]
    for row in replayed:
        replay_row(row, cfg["env_dir"], cfg["budget"])
    result = dict(origin="DEVELOPMENT", verified=datetime.now(timezone.utc).isoformat(),
                  auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  records=len(rows), chained_events=events, sources_unchanged=True,
                  actions_frames_counters_scores_match=True, exact_replays=[r["record"] for r in replayed])
    with (base / "audit.json").open("x") as f:
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
