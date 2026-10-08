"""Prospective learned-prediction campaign; physics stays outside learner API."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random

from echoai.core.cam import Cam
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT
from echoai.nexus0.world import World
from echoai.echo4.world import Body, DockRules, transition
from echoai.echo4.sensation_predictor import SensationPredictor
from echoai.echo4.sensation_agent import SensationAgent

TRAIN = (8192, 41001, (0, 1))
VALIDATE = (2048, 41002, (2,))
CONFIRM = (2048, 41003, (3,))
HORIZON = 24
ROOT = Path(__file__).resolve().parents[1]


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode()


def sha(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def sensor(body: Body) -> bytes:
    return encode_cell(0, KIND_OBJECT, vitality=body.h,
                       temperature=body.temperature, temperature_bands=8)


def episodes(count, seed, residues):
    rng = random.Random(seed)
    starts = [i for i in range(127 * 126) if i % 4 in residues]
    for _ in range(count):
        index = starts[rng.randrange(len(starts))]
        initial = Body(index // 126 + 1, index % 126 + 1)
        yield initial, tuple(rng.randrange(3) for _ in range(HORIZON))


def models():
    return [SensationPredictor(Cam(), World(), depth=depth) for depth in (0, 2, 4)]


def run_stage(learners, config, *, trace_sink=None):
    counts = [dict(transitions=0, known=0, correct=0, wrong=0, unknown=0,
                   high_confidence=0, high_confidence_correct=0, history_predictions=0,
                   error_sum=0, labels=[0, 0, 0, 0]) for _ in learners]
    pairing = [dict(wins=0, losses=0, ties=0, episode_wins=0,
                    episode_losses=0, episode_ties=0) for _ in learners]
    trace_hash, corpus_hash = hashlib.sha256(), hashlib.sha256()
    terminal = steps = 0
    for episode, (body, actions) in enumerate(episodes(*config)):
        corpus_hash.update(encoded([body.h, body.temperature, actions]) + b"\n")
        current = sensor(body)
        for learner in learners:
            learner.start(current)
        episode_hits = [0] * len(learners)
        for step_number, action in enumerate(actions):
            predictions = [learner.anticipate(action) for learner in learners]
            step = transition(body, action, DockRules())
            next_packet = sensor(step.after)
            results = [learner.observe(next_packet) for learner in learners]
            record = {"episode": episode, "step": step_number,
                      "before": current.hex(), "action": action,
                      "after": next_packet.hex(), "terminal": not step.after.alive,
                      "predictions": [
                          {"packet": None if p.packet is None else p.packet.hex(),
                           "confidence": p.confidence, "source": p.source,
                           "label": r.label, "error": r.error, "exact": r.exact}
                          for p, r in zip(predictions, results)]}
            line = encoded(record) + b"\n"
            trace_hash.update(line)
            if trace_sink is not None:
                trace_sink.write(line)
            for arm, (prediction, result, count) in enumerate(zip(predictions, results, counts)):
                count["transitions"] += 1
                count["known"] += int(prediction.packet is not None)
                count["unknown"] += int(prediction.packet is None)
                count["correct"] += int(result.exact)
                count["wrong"] += int(prediction.packet is not None and not result.exact)
                count["high_confidence"] += int(prediction.confidence == 3)
                count["high_confidence_correct"] += int(prediction.confidence == 3 and result.exact)
                count["history_predictions"] += int(prediction.source == "history")
                count["error_sum"] += result.error or 0
                count["labels"][result.label] += 1
                episode_hits[arm] += int(result.exact)
                if arm:
                    difference = int(result.exact) - int(results[0].exact)
                    pairing[arm]["wins" if difference > 0 else "losses" if difference < 0 else "ties"] += 1
            steps += 1
            body, current = step.after, next_packet
            if not body.alive:
                terminal += 1
                break
        for arm in range(1, len(learners)):
            difference = episode_hits[arm] - episode_hits[0]
            pairing[arm]["episode_wins" if difference > 0 else "episode_losses" if difference < 0 else "episode_ties"] += 1
    return {"episodes": config[0], "seed": config[1], "initial_residues": list(config[2]),
            "horizon": HORIZON, "transitions": steps, "terminal_episodes": terminal,
            "arms": counts, "paired_vs_t": pairing, "trace_sha256": trace_hash.hexdigest(),
            "corpus_sha256": corpus_hash.hexdigest()}


def stage_acceptance(stage):
    n = stage["transitions"]
    baseline, primary, _ = stage["arms"]
    return {
        "sample_size": n >= 10000,
        "gain_at_least_half_percentage_point": 200 * (primary["correct"] - baseline["correct"]) >= n,
        "coverage_at_least_98_percent": 100 * primary["known"] >= 98 * n,
        "high_confidence_coverage_at_least_5_percent": 100 * primary["high_confidence"] >= 5 * n,
        "high_confidence_accuracy_at_least_95_percent": 100 * primary["high_confidence_correct"] >= 95 * primary["high_confidence"],
    }


def integration_probe():
    agent = SensationAgent()
    records = []
    for life in range(4):
        if life:
            if not agent.episode_terminal:
                break
            agent.respawn()
        for turn in range(256):
            action = agent.turn(turn)
            result = agent.last_sensation
            prediction = agent.last_sensory_prediction
            records.append([life, turn, action, agent.last_gate_decision,
                            None if prediction.packet is None else prediction.packet.hex(),
                            asdict(result)])
            if agent.episode_terminal:
                break
    return {"turns": len(records), "resets": agent.env.resets,
            "false_facts": agent.metrics.false_facts, "destroyed": agent.cam.destroyed,
            "cortex_calls": agent.metrics.cortex_calls,
            "cam_shared": agent.sensation.cam is agent.cam,
            "t_shared": agent.sensation.world is agent.t,
            "prediction_count": len(records), "records_sha256": sha(records)}


def sources():
    files = ["docs/ECHO4-SENSATION1-PREDICTOR-V1.md", "echo4/sensation.py",
             "echo4/sensation_predictor.py", "echo4/sensation_campaign.py",
             "echo4/sensation_agent.py", "echo4/__main__.py", "echo4/world.py", "echo4/adapter.py",
             "tests/test_echo4_sensation_predictor.py",
             "nexus0/world.py", "nexus0/pattern.py", "nexus0/loop.py", "nexus0/encoder.py",
             "core/cam.py", "core/qn.py", "core/wsp.py"]
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def campaign(*, development=False, output_dir: Path | None = None):
    if type(development) is not bool:
        raise ValueError("development must be bool")
    frozen_sources = sources()
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=False)  # Never overwrite evidence.
    learners = models()
    configs = ((512, 40001, (0, 1)), (128, 40002, (2,)), (128, 40003, (3,))) if development else (TRAIN, VALIDATE, CONFIRM)
    reports = {}
    snapshots = {}
    for name, config in zip(("train", "B", "C"), configs):
        if name != "train":
            for learner in learners:
                learner.freeze()
            before = [learner.model_hash() for learner in learners]
        if output_dir is None:
            stage = run_stage(learners, config)
        else:
            with (output_dir / (name + ".jsonl")).open("xb") as sink:
                stage = run_stage(learners, config, trace_sink=sink)
        if name != "train":
            after = [learner.model_hash() for learner in learners]
            snapshots[name] = {"before": before, "after": after, "frozen": before == after}
            stage["criteria"] = stage_acceptance(stage)
        reports[name] = stage
    t_hashes = [sha(vars(learner.world)) for learner in learners]
    integration = integration_probe()
    invariants = {
        "same_instantaneous_t": len(set(t_hashes)) == 1,
        "frozen_exams": all(v["frozen"] for v in snapshots.values()),
        "cam_destroyed_zero": all(l.cam.destroyed == 0 for l in learners),
        "no_predictor_facts": all(not s.has_fact for l in learners for s in l.cam.slot),
        "bounded_memory": all(len(l.contexts) <= l.context_capacity and l.memory.size <= l.memory.capacity and l.cam.used <= 4096 for l in learners),
        "integration_shared": integration["cam_shared"] and integration["t_shared"],
        "integration_invariants": (integration["false_facts"], integration["destroyed"], integration["cortex_calls"]) == (0, 0, 0),
    }
    green = not development and all(invariants.values()) and all(
        all(reports[name]["criteria"].values()) for name in ("B", "C"))
    result = {"schema": 1, "experiment": "E4-SENSATION-1-PREDICTOR-V1",
              "development": development, "primary_history_steps": 2,
              "depths": [0, 2, 4], "stages": reports, "model_snapshots": snapshots,
              "instantaneous_t_hashes": t_hashes, "invariants": invariants,
              "resources": [l.resources() for l in learners], "integration": integration,
              "sources": frozen_sources, "sensation_predictive_green": green,
              "scope": "nominal WORLD-1 next-WSP prediction, not survival or causal attribution"}
    if sources() != frozen_sources:
        raise RuntimeError("campaign sources changed during execution; evidence is incomplete")
    # Interpreter-dependent object-size estimates are diagnostic, not certified.
    canonical = dict(result, resources=[{k: v for k, v in r.items() if k != "python_model_bytes"}
                                       for r in result["resources"]])
    result["certificate_sha256"] = sha(canonical)
    if output_dir is not None:
        with (output_dir / "report.json").open("x", encoding="utf-8") as sink:
            json.dump(result, sink, sort_keys=True, indent=2)
            sink.write("\n")
    return result


def audit_evidence(directory: Path) -> dict:
    claimed = json.loads((directory / "report.json").read_text())
    if type(claimed) is not dict or type(claimed.get("development")) is not bool:
        raise ValueError("invalid evidence schema")
    expected = campaign(development=claimed["development"])
    findings = []
    # Compare every semantic field, not just a self-reported green or digest.
    for report in (claimed, expected):
        for resource in report["resources"]:
            resource.pop("python_model_bytes", None)
    if claimed != expected:
        findings.append("report_does_not_reproduce")
    for name in ("train", "B", "C"):
        path = directory / (name + ".jsonl")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected["stages"][name]["trace_sha256"]:
            findings.append(name + "_trace_does_not_reproduce")
    return {"valid": not findings, "findings": findings,
            "certificate_sha256": expected["certificate_sha256"],
            "sensation_predictive_green": expected["sensation_predictive_green"] and not findings}
