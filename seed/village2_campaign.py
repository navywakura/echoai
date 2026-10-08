"""Development, one frozen village examination and a fresh-process full audit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from seed import village2 as v
from seed.game_selfimprove import atomic, canonical, sha, journal

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "lab/seed/village2-exam-20260928"
DEV = REPO / "lab/seed/village2-dev/attempt3"
SEEDS = tuple(range(31000, 31016))
SOURCES = ("seed/village.py", "seed/village2.py", "seed/village2_campaign.py",
           "tests/test_village2.py", "docs/ECHO45-EGO-MEMORIA2-DESIGN.md")


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def config():
    return {"seeds": list(SEEDS), "episodes": v.EPISODES, "first": v.FIRST, "last": v.LAST,
            "walk": v.WALK, "verify": v.VERIFY, "write": v.WRITE, "claim": v.CLAIM_COST,
            "criteria": "M1-M5 per seed; M6 independent exact replay", "cost_usd": 0}


def integrity(root=ROOT):
    p = json.loads((root / "profile.json").read_text())
    assert p["sources"] == hashes() and p["configuration"] == config(), "village sources/configuration changed"
    return p


def checks(record):
    c = record["cases"]
    d, n, nd, nv = (c[k] for k in ("debt", "no_debt", "no_diary", "no_verify"))
    first, late = d["first"], d["last"]
    nf, nl = n["first"], n["last"]
    a = record["ablations"]
    growth_w = late["write_pm"] - first["write_pm"]
    growth_v = late["verify_pm"] - first["verify_pm"]
    q_preserved = all(x["probe"]["final"]["q"] == d["final"]["q"] for x in a.values())
    citations = all(all(h in {e["hash"] for e in c[name]["final"]["diary"]}
                        for item in c[name]["description"].values() for h in item["because"])
                    for name in ("debt", "honest"))
    policy = lambda x: {agent: (item["context"], item["action"]) for agent, item in x.items()}
    return {"M1": growth_w >= 25 and growth_w > nl["write_pm"] - nf["write_pm"] and
                  nl["write_pm"] <= 100 and late["false_write_pm"] >= 800 and
                  late["true_write_pm"] < late["false_write_pm"],
            "M2": all(late[k] < nd["last"][k] for k in ("cost", "paid_false", "repeat_errors")) and
                  nv["last"]["rejected"] == 0,
            "M3": record["ablation_matched"] and a["formative"]["removed"] == a["other_same_count"]["removed"] and
                  a["formative"]["verify_target_pm"] < a["intact"]["verify_target_pm"] ==
                  a["other_same_count"]["verify_target_pm"] and q_preserved,
            "M4": d["initial_sha256"] == c["honest"]["initial_sha256"] and citations and
                  policy(d["description"]) != policy(c["honest"]["description"]) and
                  all(x["stable"] and x["q_unchanged"] for x in record["stability"].values()),
            "M5": growth_v >= 200 and growth_v - (nl["verify_pm"] - nf["verify_pm"]) >= 200 and
                  nl["verify_pm"] <= 100 and late["false_verify_pm"] >= 800}


def diary_valid(record):
    prev = "0" * 64
    for entry in record["final"]["diary"]:
        body = {k: value for k, value in entry.items() if k != "hash"}
        assert body["prev"] == prev and sha(body) == entry["hash"], "invalid memory chain"
        assert entry["interpretation"] is None or entry["interpretation"]["status"] == "HYPOTHESIS"
        prev = entry["hash"]
    assert all(tuple(cell) == tuple(int(x) for x in cell)
               for cells in record["final"]["q"].values() for cell in cells)


def observe(record):
    # Reuse the existing campaign journal; selected real decisions are visible,
    # while every decision remains in the complete development receipt.
    p = REPO / "lab/seed/village2-live/journal.jsonl"
    for row in record["cases"]["debt"]["rows"][::80]:
        journal(p, {"kind": "village_decision", "origin": "DEVELOPMENT", "seed": record["seed"],
                    "episode": row["episode"], "agent": row["offer"]["agent"],
                    "context": row["context"], "q_values": row["q_values"],
                    "verified": row["verified"], "wrote": row["wrote"], "cost": row["cost"],
                    "claims": row["claims"], "entry_hash": row["entry_hash"]})


def develop():
    DEV.mkdir(parents=True, exist_ok=True)
    initial_sources = hashes()
    source_receipt = DEV / "sources.json"
    if source_receipt.exists():
        assert json.loads(source_receipt.read_text()) == initial_sources, "development receipts belong to another source revision"
    else:
        atomic(source_receipt, initial_sources)
    summaries = {}
    for seed in range(1, 9):
        p = DEV / f"seed-{seed}.json"
        r = json.loads(p.read_text()) if p.exists() else v.experiment(seed)
        atomic(p, r)
        observe(r)
        summaries[str(seed)] = checks(r)
        print(canonical({"development_seed": seed, "checks": summaries[str(seed)]}), flush=True)
    assert initial_sources == hashes()
    out = {"sources": initial_sources, "configuration": config(), "seeds": summaries,
           "passed": all(all(c.values()) for c in summaries.values()), "closed": datetime.now(timezone.utc).isoformat()}
    atomic(DEV / "summary.json", out)
    return out


def prepare():
    development = json.loads((DEV / "summary.json").read_text())
    assert development["passed"] and development["sources"] == hashes(), "development not certified for these sources"
    ROOT.mkdir(parents=True, exist_ok=True)
    profile = {"sources": hashes(), "configuration": config()}
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == profile
    else:
        atomic(ROOT / "profile.json", profile)
        for p in SOURCES:
            target = ROOT / "source-archive" / p
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / p).read_bytes())
    return integrity()


def examine():
    profile = prepare()
    assert not (ROOT / "opened.json").exists(), "examination already opened"
    atomic(ROOT / "opened.json", {"sources": profile["sources"], "opened": datetime.now(timezone.utc).isoformat()})
    for i, seed in enumerate(SEEDS):
        atomic(ROOT / f"seed-{seed}.json", v.experiment(seed))
        integrity()
        print(canonical({"recorded": i + 1, "of": len(SEEDS)}), flush=True)
    # The audit must use a new interpreter, not cached objects from measurement.
    subprocess.run([sys.executable, "-m", "seed.village2_campaign", "audit"], cwd=REPO, check=True)


def audit():
    integrity()
    assert (ROOT / "opened.json").exists()
    reports = {}
    for seed in SEEDS:
        recorded = json.loads((ROOT / f"seed-{seed}.json").read_text())
        rebuilt = v.experiment(seed)
        assert sha(recorded) == sha(rebuilt), f"replay mismatch in {seed}"
        for case in recorded["cases"].values():
            diary_valid(case)
            assert case["first"] == v.metrics(case["rows"][:v.FIRST])
            assert case["last"] == v.metrics(case["rows"][-v.LAST:])
        for case in (*recorded["ablations"].values(), *recorded["stability"].values()):
            diary_valid(case["probe"])
        reports[str(seed)] = checks(recorded)
    integrity()
    green = all(all(x.values()) for x in reports.values())
    result = {"green": green, "M6": True, "checks": reports, "sources": hashes(),
              "configuration": config(), "audit_pid": os.getpid(),
              "closed": datetime.now(timezone.utc).isoformat(), "cost_usd": 0}
    atomic(ROOT / "audit.json", result)
    lines = ["# EGO-MEMORIA-2 · resultado reservado", "", "**" + ("VERDE" if green else "ROJO") +
             "**. Dieciséis semillas nuevas; auditoría íntegra en proceso separado.", "",
             "| Prueba | Semillas que pasan /16 |", "|---|---:|"]
    for key in ("M1", "M2", "M3", "M4", "M5"):
        lines.append(f"| {key} | {sum(r[key] for r in reports.values())} |")
    lines.extend(["| M6: reconstrucción exacta | 16 |", "",
                  "Esta es la segunda condición de aldea, con costes y reclamaciones declarados.",
                  "No demuestra conciencia, integración en NEXUS-0 ni transferencia a ARC.",
                  "El experimento original y los resultados ARC/S6 permanecen intactos.", "",
                  "[Contrato](ECHO45-EGO-MEMORIA2-DESIGN.md) ·",
                  "[Auditoría](../lab/seed/village2-exam-20260928/audit.json).", ""])
    (REPO / "docs/ECHO45-EGO-MEMORIA2-RESULTS.md").write_text("\n".join(lines))
    print(canonical({"village2_green": green, "M6": True, "seed_checks": reports}), flush=True)


def main():
    assert __debug__
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("dev", "prepare", "exam", "audit"))
    args = ap.parse_args()
    return {"dev": develop, "prepare": prepare, "exam": examine, "audit": audit}[args.command]()


if __name__ == "__main__":
    main()
