"""Final grid judge: test labels are never part of the solver input."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO.parent))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def solver_input(task):
    return {"train": deepcopy(task["train"]),
            "test": [{"input": deepcopy(x["input"])} for x in task["test"]]}


def judge(task, result):
    predictions = result["predictions"]
    return result["program"] is not None and len(predictions) == len(task["test"]) > 0 and all(
        "output" in sample and prediction == sample["output"]
        for prediction, sample in zip(predictions, task["test"]))


def solve_one(job):
    task_id, public, level, concepts, prior, budget = job
    from echoai.seed import sandbox
    from echoai.seed.learn import Library, solve
    sandbox._set_level(level)
    lib = Library(concepts, prior)
    before = digest({"concepts": lib.concepts, "prior": lib.prior})
    assert all(set(x) == {"input"} for x in public["test"])
    result = solve(public, lib, max_expansions=budget, max_depth=4)
    assert result["test_ok"] is None and result["expansions"] <= budget
    assert before == digest({"concepts": lib.concepts, "prior": lib.prior})
    return {"task": task_id, "public_sha256": digest(public), "library_digest": before,
            "level": level, "budget": budget, "result": result}


def learned_state():
    root = REPO / "lab/seed/sandboxes/echo45-s2v"
    return {"level": "S2v", "concepts": json.loads((root / "library.json").read_text()),
            "prior": json.loads((root / "prior.json").read_text())}


def provenance_audit():
    from echoai.seed import gym, sandbox
    from echoai.seed.learn import Library, prior_from
    from echoai.seed import dsl
    sandbox._set_level("S2v")
    state = learned_state()
    lib = Library(state["concepts"], state["prior"])
    train = set(gym.split()["train"])
    root = REPO / "lab/seed/sandboxes/echo45-s2v"
    prev, concepts, prior_source = "0" * 64, {}, None
    for line in (root / "journal.jsonl").read_text().splitlines():
        e = json.loads(line)
        h = e.pop("hash")
        assert e["prev"] == prev and hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest() == h
        prev = h
        if e["kind"] == "concept":
            concepts[e["id"]] = e
        if e["kind"] == "prior":
            prior_source = e["source"]
    programs = sandbox.verified_programs("echo45-s2v")
    assert set(programs) <= train
    for tid, program in programs.items():
        task = gym.load(tid)
        for example in task["train"]:
            assert sandbox._run(lib, program, example["input"]) == dsl.G(example["output"]), tid
    for cid, concept in state["concepts"].items():
        assert cid in concepts and concept["steps"] == concepts[cid]["steps"]
        assert sorted(concept["tasks"]) == sorted(concepts[cid]["tasks"])
        assert len(set(concept["tasks"])) >= 2 and set(concept["tasks"]) <= set(programs)
        wanted = lib.expand(cid)
        for tid in concept["tasks"]:
            expanded = [step for item in programs[tid] for step in lib.expand(item)]
            assert any(expanded[i:i + len(wanted)] == wanted
                       for i in range(len(expanded) - len(wanted) + 1)), (cid, tid)
    # Training refreshes the prior from this sandbox's verified programs after
    # importing its initial prior. The old import event is not the final prior.
    assert prior_source and state["prior"] == prior_from(programs)
    return {"chain_tail": prev, "programs": len(programs), "concepts": len(concepts),
            "initial_prior_source": prior_source, "final_prior_source": "echo45-s2v", "valid": True}
