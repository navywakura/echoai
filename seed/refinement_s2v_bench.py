"""Additive development check using ECHO's learned S2v library; preserves S0 run."""
import hashlib
import json
import sys
from types import FunctionType

from seed import refinement_bench as previous
from echoai.seed import refinement as r
from echoai.seed.final_eval import learned_state
from echoai.seed.learn import Library
from seed.game_selfimprove import atomic, canonical, sha

REPO = previous.REPO
ROOT = REPO / "lab/seed/refinement-s2v-dev-20260928"
DATA, ARMS = previous.DATA, previous.ARMS
SOURCES = previous.SOURCES + ("seed/refinement_s2v_bench.py", "seed/final_eval.py",
    "docs/ECHO45-REFINEMENT-S2V-DESIGN.md", "lab/seed/sandboxes/echo45-s2v/library.json",
    "lab/seed/sandboxes/echo45-s2v/prior.json", "lab/seed/sandboxes/echo45-s2v/manifest.json",
    "lab/seed/sandboxes/echo45-s2v/journal.jsonl")


def configuration():
    return dict(previous.configuration(), base="S2v", learned_library=learned_state())


def hashes():
    return {p: hashlib.sha256((REPO / p).read_bytes()).hexdigest() for p in SOURCES}


def integrity():
    profile = json.loads((ROOT / "profile.json").read_text())
    assert profile["sources"] == hashes()
    assert profile["configuration"] == json.loads(canonical(configuration()))
    assert profile["python"] == sys.version
    for name, digest in profile["inputs"].items():
        assert hashlib.sha256((DATA / (name + ".json")).read_bytes()).hexdigest() == digest
    previous.integrity()
    return profile


def prepare():
    cfg = configuration()
    profile = {"sources": hashes(), "configuration": cfg, "python": sys.version,
               "inputs": {name: hashlib.sha256((DATA / (name + ".json")).read_bytes()).hexdigest() for name in cfg["tasks"]}}
    if (ROOT / "profile.json").exists():
        assert json.loads((ROOT / "profile.json").read_text()) == json.loads(canonical(profile))
    else:
        for source in SOURCES:
            target = ROOT / "source-archive" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as f:
                f.write((REPO / source).read_bytes())
        atomic(ROOT / "profile.json", profile)
    return integrity()


def one(item):
    # Each worker owns its imported registry; no running agent or frozen source changes.
    r.dsl.enable_s2v()
    state = learned_state()
    library = lambda: Library(state["concepts"], state["prior"])
    relation_library = lambda: r.RefinementLibrary(state["concepts"], state["prior"])
    from types import SimpleNamespace
    namespace = SimpleNamespace(**{name: getattr(r, name) for name in ("solver_input", "solve", "execute", "grid")},
                                RefinementLibrary=relation_library)
    worker = FunctionType(previous.one.__code__, dict(previous.one.__globals__, ROOT=ROOT,
                          r=namespace, Library=library), previous.one.__name__, previous.one.__defaults__)
    return worker(item)


def run():
    # Preserve the first result document; the imported writer receives its own destination.
    report = ROOT / "report/docs"
    report.mkdir(parents=True, exist_ok=True)
    execute = FunctionType(previous.run.__code__, dict(previous.run.__globals__, ROOT=ROOT,
                           integrity=integrity, one=one, REPO=ROOT / "report"),
                           previous.run.__name__, previous.run.__defaults__)
    execute()
    summary = json.loads((ROOT / "summary.json").read_text())
    text = (report / "ECHO45-REFINEMENT-RESULTS.md").read_text()
    text = text.replace("# Bucle de refinamiento: desarrollo ARC-2", "# Refinamiento con la biblioteca aprendida S2v")
    text = text.replace("[Contrato](ECHO45-REFINEMENT-DESIGN.md)", "[Contrato](ECHO45-REFINEMENT-S2V-DESIGN.md)")
    text = text.replace("refinement-dev-20260928/summary.json", "refinement-s2v-dev-20260928/summary.json")
    text += "\nTodos los brazos parten de S2v: 84 primitivas y tres conceptos aprendidos con prioridad por frecuencias.\n"
    (REPO / "docs/ECHO45-REFINEMENT-S2V-RESULTS.md").write_text(text)
    return summary


if __name__ == "__main__":
    if sys.argv[1:] == ["prepare"]:
        prepare()
    elif sys.argv[1:] == ["run"]:
        try:
            run()
        except Exception as exc:
            atomic(ROOT / "status.json", {"stage": "FAILED", "error": type(exc).__name__, "message": str(exc)})
            raise
    else:
        raise SystemExit("use prepare or run")
