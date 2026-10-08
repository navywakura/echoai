"""DREAM-A native discovery-history increment, not a DREAM-1 closure."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from echoai.echo4 import continuity as base
from echoai.echo4 import continuity_bench as nominal
from echoai.echo4 import continuity_final_audit as parent
from echoai.echo4.dream_history import EXPERIMENTS, PROFILE, SCHEMA, Archive, sha

ROOT = base.ROOT
PARENT = "69d57a0b03a468b3f2be7fedde5bce7edeaa2db5a2576ce9160726e2a90cec7c"
CASES = (("nominal2", 60, 46, 2, 3, 3),
         ("nominal4", 64, 55, 4, 4, 3),
         ("terminal", 32, 64, 2, 128, 3))


def sources():
    extras = ("echo4/dream_history.py", "echo4/dream_history_bench.py",
              "tests/test_echo4_dream1a.py", "docs/ECHO4-DREAM1-A-DESIGN.md")
    return {**parent.sources(), **{p: parent.file_hash(ROOT / p) for p in extras}}


def parent_binding():
    directory = ROOT / "lab/echo4/continuity1-final-v1"
    report = parent.read_json(directory / "report.json")
    receipt = parent.read_json(directory / "audit-receipt.json")
    unsigned = dict(report)
    claimed = unsigned.pop("reproduction_sha256")
    if (claimed != PARENT or sha(base.canonical(unsigned)) != PARENT
            or receipt.get("reproduction_sha256") != PARENT
            or receipt.get("valid") is not True or receipt.get("continuity1_green") is not True
            or receipt.get("findings") != [] or report["sources"] != parent.sources()
            or report["parents"] != parent.parents()
            or report["trace_sha256"] != parent.file_hash(directory / "traces.jsonl")):
        raise ValueError("CONT-D certificate/source binding failed")
    for stage, value in report["stages"].items():
        for row in value["cases"]:
            if parent.file_hash(directory / (stage + "-" + row["case"] + ".json")) != row["checkpoint_sha256"]:
                raise ValueError("CONT-D checkpoint changed")
    return {p: parent.file_hash(directory / p) for p in ("report.json", "audit-receipt.json", "traces.jsonl")}


def observation(run, action=None):
    a = run.agent
    return {"wsp": a.observation(a.env.cell()).hex(), "turn": run.next_turn,
            "action": action, "gate": None if action is None else a.last_gate_decision,
            "reward": a.last_reward, "terminal": a.episode_terminal}


def collect(spec, directory=None, *, checking=False, manifest=None):
    """Each attempt is a native Agent turn from its parent's private state."""
    name, h, temperature, depth, cut, horizon = spec
    original = nominal.prepared(h, temperature, depth, cut)
    initial_raw = original.dumps()
    snapshots, nodes, levels = [], [], []
    invariants = []

    def add(run, ancestor, experiment, action, level):
        raw = run.dumps()
        index = len(nodes)
        obs = observation(run, action)
        if directory is not None:
            path = directory / (f"{index:04d}.json")
            if checking:
                if path.read_bytes() != raw:
                    raise ValueError(name + ": checkpoint differs from native reconstruction")
            else:
                run.save(path)
        snapshots.append(raw)
        levels.append(level)
        nodes.append({"id": index, "parent": ancestor, "experiment": experiment,
                      "observation": obs, "score": obs["reward"], "checkpoint": sha(raw),
                      "cost": {"attempts": int(ancestor is not None),
                               "native_steps": int(ancestor is not None), "llm_calls": 0}})
        a = run.agent
        invariants.append(a.env.balanced and a.metrics.cortex_calls == 0
                          and a.metrics.false_facts == 0 and a.cam.destroyed == 0)

    add(original, None, None, None, 0)
    index = 0
    while index < len(nodes):
        node = nodes[index]
        if not node["observation"]["terminal"] and levels[index] < horizon:
            for experiment in EXPERIMENTS:
                run = base.loads(snapshots[index], expected_sha256=node["checkpoint"])
                action = run.step(greedy=experiment == "greedy")
                add(run, index, experiment, action, levels[index] + 1)
        index += 1
    archive = Archive({"schema": SCHEMA, "profile": PROFILE,
                       "sources": sources() if manifest is None else manifest,
                       "continuity_certificate": PARENT, "nodes": nodes})
    return archive, {"case": name, "nodes": len(nodes), "native_attempts": len(nodes) - 1,
                     "preparation": {"calibration_steps": 64, "native_prefix_steps": original.next_turn},
                     "checkpoint_bytes": sum(map(len, snapshots)),
                     "parent_unchanged": original.dumps() == initial_raw,
                     "invariants": all(invariants)}


def replay_all(archive):
    """Caller walks only revealed nodes; no private archive access here."""
    replay = archive.replay(budget=4096)
    pending, events = [0], []
    while pending:
        handle = pending.pop(0)
        results = replay.batch([(handle, name) for name in EXPERIMENTS])
        events.append({"parent": handle, "results": results})
        pending.extend(r["node"]["id"] for r in results if r["status"] == "observed")
    return {"events": events, "view": replay.view()}


def fresh_replay(path, digest):
    result = subprocess.run([sys.executable, "-m", "echoai.echo4.dream_history_bench",
                             "replay", str(path.resolve()), digest], cwd=ROOT.parent,
                            capture_output=True, text=True, timeout=120, check=True)
    return json.loads(result.stdout)


def build(directory, *, checking=False, progress=lambda value: None):
    manifest, binding = sources(), parent_binding()
    rows = []
    for spec in CASES:
        progress(spec[0])
        folder = directory / spec[0]
        if not checking:
            folder.mkdir()
        archive, row = collect(spec, folder, checking=checking, manifest=manifest)
        raw = archive.dumps()
        path = folder / "history.json"
        if checking:
            if path.read_bytes() != raw:
                raise ValueError("archive differs from native reconstruction")
        else:
            with path.open("xb") as handle:
                handle.write(raw)
        # Unlike a physical run, both these paths are read-only replay.
        public = replay_all(archive)
        restored = fresh_replay(path, sha(raw))
        data = json.loads(raw)
        expected_nodes = [{k: v for k, v in n.items() if k != "checkpoint"} for n in data["nodes"]]
        row.update(archive_sha256=sha(raw), archive_bytes=len(raw), replay=public,
                   fresh_process_equal=public == restored,
                   observed_equal=public["view"]["nodes"] == expected_nodes,
                   query_count=public["view"]["queries_used"])
        rows.append(row)
    checks = {"native_invariants": all(r["invariants"] and r["parent_unchanged"] for r in rows),
              "exact_observed_replay": all(r["observed_equal"] and r["fresh_process_equal"] for r in rows),
              "no_replay_executions": all(r["replay"]["view"]["replay_native_steps"] == 0
                  and r["replay"]["view"]["replay_llm_calls"] == 0 for r in rows),
              "represented_cost": all(r["native_attempts"] == r["replay"]["view"]["represented_native_steps"] for r in rows),
              "terminal_not_revived": rows[-1]["nodes"] == 1 and rows[-1]["native_attempts"] == 0,
              "sources_and_parent_unchanged": manifest == sources() and binding == parent_binding()}
    report = {"schema": "echo4-dream-a-development-v1", "sources": manifest, "parent_binding": binding,
              "trees": rows, "checks": checks, "development_passed": all(checks.values()),
              "dream1_green": False, "qwen_implemented": False}
    report["reproduction_sha256"] = sha(base.canonical(report))
    return report


def record(directory, *, progress=lambda value: None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    report = build(directory, progress=progress)
    with (directory / "report.json").open("xb") as handle:
        handle.write(base.canonical(report))
    return report


def verify(directory, *, progress=lambda value: None):
    findings, saved = [], {}
    try:
        directory = Path(directory)
        saved = parent.read_json(directory / "report.json")
        if type(saved) is not dict or saved.get("schema") != "echo4-dream-a-development-v1":
            raise ValueError("unknown development report")
        if saved.get("sources") != sources() or saved.get("parent_binding") != parent_binding():
            raise ValueError("source or parent mismatch")
        rebuilt = build(directory, checking=True, progress=progress)
        if base.canonical(saved) != base.canonical(rebuilt) or not rebuilt["development_passed"]:
            raise ValueError("report differs from complete reconstruction")
    except (ValueError, OSError, RuntimeError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "dream1_green": False,
            "reproduction_sha256": saved.get("reproduction_sha256") if not findings else None,
            "continuity_binding": "existing certificate and artifact integrity; not a new CONT-D replay"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("campaign", "verify"):
        sub.add_parser(name).add_argument("directory", type=Path)
    replay = sub.add_parser("replay")
    replay.add_argument("path", type=Path)
    replay.add_argument("digest")
    args = parser.parse_args()
    progress = lambda value: print(value, file=sys.stderr, flush=True)
    if args.command == "replay":
        result = replay_all(Archive.loads(args.path.read_bytes(), expected_sha256=args.digest))
    elif args.command == "verify":
        result = verify(args.directory, progress=progress)
    else:
        report = record(args.directory, progress=progress)
        result = {"development_passed": report["development_passed"], "dream1_green": False,
                  "trees": [{k: r[k] for k in ("case", "nodes", "native_attempts", "query_count")} for r in report["trees"]],
                  "reproduction_sha256": report["reproduction_sha256"]}
    print(json.dumps(result, sort_keys=True))
    if result.get("valid") is False or result.get("development_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
