"""Full R4 replay with a frozen, explicit correction of JSON representation comparison."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from seed import final_campaign as original
from seed.final_eval import digest

REPO, ROOT = original.REPO, original.ROOT
OUT = ROOT / "audit-recovery"
SOURCES = ("seed/final_audit_recovery.py", "tests/test_final_audit_recovery.py",
           "docs/ECHO45-FINAL-AUDIT-RECOVERY.md")


def now():
    return datetime.now(timezone.utc).isoformat()


def source_hashes():
    return {p: original.hash_file(REPO / p) for p in SOURCES}


def measured_hashes():
    paths = sorted((ROOT / "grid").glob("*/*/*.json")) + sorted((ROOT / "arc").glob("*/*.json"))
    assert sum("grid" in p.relative_to(ROOT).parts for p in paths) == 1040
    assert sum("arc" in p.relative_to(ROOT).parts for p in paths) == 32
    paths += [ROOT / n for n in ("grid-results.json", "arc-results.json", "profile.json", "opened.json", "exit.json")]
    return {str(p.relative_to(ROOT)): original.hash_file(p) for p in paths}


def prepare():
    frozen = original.integrity()
    assert original.read(ROOT / "exit.json")["exit_code"] == 1
    assert not (ROOT / "audit.json").exists(), "original audit already closed"
    expected = {"sources": source_hashes(), "native_source_digest": digest(frozen),
                "measured_hashes": measured_hashes(), "comparison": "complete canonical JSON",
                "criteria_unchanged": True}
    path = OUT / "profile.json"
    if path.exists():
        assert original.read(path) == expected
    else:
        original.save(path, expected)
        for p in SOURCES:
            dst = OUT / "source-archive" / p
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((REPO / p).read_bytes())
        original.save(OUT / "prepared.json", {"at": now(), "digest": digest(expected)})
    return integrity()


def integrity():
    p = original.read(OUT / "profile.json")
    assert p["sources"] == source_hashes(), "recovery audit sources changed"
    assert p["measured_hashes"] == measured_hashes(), "measured receipts changed"
    assert p["native_source_digest"] == digest(original.integrity())
    return p


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def compare(rebuilt, recorded):
    # JSON stores Python tuples as arrays. Check every serialized value, with
    # no exclusions or numeric rounding. True and 1 have different JSON.
    assert canonical_json(rebuilt) == canonical_json(recorded), "full JSON replay mismatch"


def grid():
    integrity()
    from seed.final_eval import provenance_audit
    provenance = provenance_audit()
    frozen = original.integrity()
    result = {}
    for name in original.DATASETS:
        original.save(OUT / "grid-status.json", {"stage": "REPLAY_GRID", "exam": name, "at": now()})
        result[name] = original.measure_grid(name, frozen, audit=True)
    assert result == original.read(ROOT / "grid-results.json")
    integrity()
    original.save(OUT / "grid-audit.json", {"valid": True, "result": result, "provenance": provenance,
                  "records": 1040, "recovery_digest": digest(integrity()), "closed": now()})


def arc():
    from seed.final_arc import one, accounting, protocol_check
    integrity()
    frozen = original.integrity()
    actors, results = {}, {}
    for arm, actor in frozen["actors"].items():
        actor_digest = digest(actor)
        if actor_digest in actors:
            previous = actors[actor_digest]
            results[arm] = dict(results[previous], alias_of=previous, reason="identical frozen actor")
            continue
        actors[actor_digest] = arm
        records = []
        for game in frozen["games"]:
            saved = original.read(ROOT / "arc" / arm / (game + ".json"))
            rebuilt = one(game, actor, original.CONFIG["arc_decisions"])
            rebuilt["source_digest"] = digest(frozen)
            compare(rebuilt, saved)
            assert saved["accounting"] == accounting(saved) and saved["sdk_counter_verified"] and protocol_check(saved)
            original.save(OUT / "replayed-arc" / arm / (game + ".json"), rebuilt)
            records.append(saved)
            original.save(OUT / "arc-status.json", {"stage": "REPLAY_ARC3", "arm": arm, "game": game,
                         "completed": len(records), "of": 16, "at": now()})
        assert sum(r["win_levels"] for r in records) == 112
        results[arm] = {"levels": sum(r["levels_completed"] for r in records), "of": 112,
                       "historical_score": sum(r["historical_score"] for r in records) / 16,
                       "contract_score": sum(r["contract_score"] for r in records) / 16,
                       "decisions": sum(r["accounting"]["decisions"] for r in records),
                       "automatic_resets": sum(r["resets"] for r in records), "records_digest": digest(records)}
    assert results == original.read(ROOT / "arc-results.json")
    integrity()
    original.save(OUT / "arc-audit.json", {"valid": True, "result": results, "records": 32,
                  "recovery_digest": digest(integrity()), "closed": now()})


def close():
    p = integrity()
    ga, aa = (original.read(OUT / name) for name in ("grid-audit.json", "arc-audit.json"))
    assert all(r["valid"] and r["recovery_digest"] == digest(p) for r in (ga, aa))
    frozen = original.integrity()
    grid_results, arc_results = ga["result"], aa["result"]
    assert grid_results == original.read(ROOT / "grid-results.json")
    assert arc_results == original.read(ROOT / "arc-results.json")
    criteria = {name: grid_results[name]["con_s6"]["solved"] > grid_results[name]["semilla"]["solved"] and
                grid_results[name]["con_s6"]["solved"] > 0 for name in original.DATASETS}
    criteria.update(R3=arc_results["con_s6"]["levels"] >= original.CONFIG["R3_min_levels"], R4=True)
    result = {"criteria": criteria, "green": all(criteria.values()), "grid": grid_results, "arc": arc_results,
              "provenance": ga["provenance"], "source_digest": digest(frozen), "closed": now(),
              "audit_pid": os.getpid(), "audit_extension_digest": digest(p), "original_failure_preserved": True}
    original.save(ROOT / "audit.json", result)
    original.publish(result, frozen)
    report = REPO / "docs/ECHO45-FINAL-EXAM-RESULTS.md"
    with report.open("a") as f:
        f.write("\nR4 se cerró con una extensión explícita del comparador JSON; fuentes y registros\n"
                "originales intactos. Se repitieron 1040 soluciones y 32 partidas completas.\n"
                "[Adenda](ECHO45-FINAL-AUDIT-RECOVERY.md) · "
                "[Custodia](../lab/final/echo45-20260928/audit-recovery/profile.json).\n")
    original.save(OUT / "exit.json", {"exit_code": 0, "closed": now(), "green": result["green"], "criteria": criteria})


def watch():
    p = prepare()
    commands = {"grid": ["/usr/bin/python3", "-u", "-m", "seed.final_audit_recovery", "grid"],
                "arc": [str(original.ARC_PYTHON), "-u", "-m", "seed.final_audit_recovery", "arc"]}
    procs, logs = {}, {}
    try:
        for name, command in commands.items():
            if (OUT / (name + "-audit.json")).exists():
                r = original.read(OUT / (name + "-audit.json"))
                assert r["valid"] and r["recovery_digest"] == digest(p)
                continue
            logs[name] = (OUT / (name + ".log")).open("a")
            procs[name] = subprocess.Popen(command, cwd=REPO, stdin=subprocess.DEVNULL,
                stdout=logs[name], stderr=subprocess.STDOUT,
                env=dict(os.environ, MPLCONFIGDIR=str(OUT / "matplotlib")))
        while any(proc.poll() is None for proc in procs.values()):
            original.save(OUT / "running.json", {"supervisor_pid": os.getpid(), "updated": now(),
                         "processes": {name: {"pid": proc.pid, "exit_code": proc.poll()} for name, proc in procs.items()}})
            time.sleep(15)
        codes = {name: proc.wait() for name, proc in procs.items()}
        if any(codes.values()):
            original.save(OUT / "exit.json", {"exit_code": 1, "processes": codes, "finished": now()})
            raise RuntimeError("recovery replay failed; preserve receipts")
        close()
    finally:
        for log in logs.values():
            log.close()


if __name__ == "__main__":
    assert __debug__
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "grid", "arc", "close", "watch"))
    {"prepare": prepare, "grid": grid, "arc": arc, "close": close, "watch": watch}[parser.parse_args().stage]()
