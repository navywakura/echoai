"""Second development hypothesis, with its own freeze, receipts and exam."""
from types import FunctionType
from seed import village3_campaign as previous, village3_settled as revision

# Reuse record formats, all original M1--M5, and full independent replay.
namespace = dict(vars(previous), v=revision, ROOT=previous.REPO / "lab/seed/village3-settled-20260929",
                 SOURCES=previous.SOURCES + ("seed/village3_factorized.py",
                 "seed/village3_factorized_campaign.py", "tests/test_village3_factorized.py",
                 "docs/ECHO45-EGO-MEMORIA3B-DESIGN.md", "seed/village3_settled.py",
                 "seed/village3_settled_campaign.py", "tests/test_village3_settled.py",
                 "docs/ECHO45-EGO-MEMORIA3C-DESIGN.md"))
for name in ("sources", "save", "read", "summary", "observe", "development", "integrity", "audit"):
    original = getattr(previous, name)
    namespace[name] = FunctionType(original.__code__, namespace, name, original.__defaults__)
globals().update({name: namespace[name] for name in ("sources", "read", "summary", "development", "integrity", "audit")})
ROOT = namespace["ROOT"]


def examine():
    import json
    import os
    import subprocess
    import sys
    from datetime import datetime, timezone
    from seed.game_selfimprove import atomic, sha
    for other in ("village3-20260928", "village3-factorized-20260928"):
        assert not (previous.REPO / "lab/seed" / other / "opened.json").exists(), "cohort already opened elsewhere"
    dev = json.loads((ROOT / "development/summary.json").read_text())
    assert dev["promote"] and dev["sources"] == sources(), "development not promoted"
    assert not (ROOT / "opened.json").exists(), "exam already opened"
    atomic(ROOT / "profile.json", {"sources": sources(), "seeds": previous.SEEDS,
           "horizon": revision.HORIZON, "development_sha256": sha(dev)})
    for name in sources():
        target = ROOT / "source-archive" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write((previous.REPO / name).read_bytes())
    atomic(ROOT / "opened.json", {"at": datetime.now(timezone.utc).isoformat(), "pid": os.getpid()})
    for seed in previous.SEEDS:
        namespace["save"](ROOT / f"exam-{seed}.json.gz", revision.experiment(seed))
        integrity()
        print(json.dumps({"recorded": seed, "of": 16}), flush=True)
    subprocess.run([sys.executable, "-m", "seed.village3_settled_campaign", "audit"],
                   cwd=previous.REPO, check=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("dev", "exam", "audit"))
    {"dev": development, "exam": examine, "audit": audit}[ap.parse_args().command]()
