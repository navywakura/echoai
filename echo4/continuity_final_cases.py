"""CONT-D fixed recipes and negative controls; imports sealed A/B/C runtimes."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict

from echoai.core.qn import SLOT_FLAG_INHIBIT

from echoai.echo4 import continuity as a
from echoai.echo4 import continuity_active as b
from echoai.echo4 import continuity_active_bench as bb
from echoai.echo4 import continuity_bench as ab
from echoai.echo4 import continuity_lineage as c
from echoai.echo4 import continuity_lineage_bench as cb
from echoai.echo4 import self_recovery_audit as school
from echoai.echo4 import self_reuse_audit as reuse
from echoai.echo4.self_recovery import RecoveryStop
from echoai.echo4.self_recovery_world import RecoveryEnv
from echoai.echo4.world import Body

SCOPE = "CONT-A-B-C-synchronous-WORLD1-virtual-custody-v1"
STAGES = {"A": (((52, 44), (68, 58)), 3, 5),
          "B": (((53, 45), (69, 59)), 4, 6),
          "C": (((54, 47), (70, 61)), 5, 7)}
CASES = ("nominal0", "nominal2", "nominal4", "nominal_terminal",
         "pending", "inbox", "confirmed", "cancelled", "selective", "unprotected",
         "veto", "stopped", "terminal", "reuse", "fork_left", "fork_right",
         "body_quarantine", "descendant_quarantine", "body_active", "descendant_active",
         "reuse_body_active", "terminal_fork", "ambiguous")
MUTANTS = ("clock", "body", "schema", "sources", "digest", "permission", "confirmation",
           "epoch", "allocation", "receipt_scope")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def kind(run):
    return {a.ContinuityRun: "A", b.ActiveRun: "B", c.LineageRun: "C"}[type(run)]


def module(profile):
    return {"A": a, "B": b, "C": c}[profile]


def clone(run):
    raw = run.dumps()
    return module(kind(run)).loads(raw, expected_sha256=sha(raw))


def prepared(stage, case):
    if stage not in STAGES or case not in CASES:
        raise ValueError("unknown frozen recipe")
    bodies, cut, _ = STAGES[stage]
    index = CASES.index("fork_left" if case == "fork_right" else case) % 2
    if not case.startswith("nominal"):
        index = 0 if case in ("pending", "inbox", "cancelled", "ambiguous") else 1
    body = Body(*bodies[index])
    cost = {"school_steps": 0, "native_prefix_turns": 0, "diagnostic_steps": 0,
            "calibration_steps": 0, "allocated_bodies": 0}
    if case.startswith("nominal"):
        depth = 2 if case == "nominal_terminal" else int(case[-1])
        run = ab.prepared(body.h, body.temperature, depth, 128 if case == "nominal_terminal" else cut)
        cost.update(school_steps=64, native_prefix_turns=run.next_turn)
        if case == "nominal_terminal" and not run.agent.episode_terminal:
            raise AssertionError("missing native terminal witness")
        return run, cost
    is_reuse = case in ("reuse", "reuse_body_active")
    if is_reuse:
        agent, nominal, _ = reuse.school(body)
        reuse.restore_trial(agent, body)
    else:
        agent, nominal = school.school(body)
        agent.env = RecoveryEnv(body, h_coupled=False)
    cost["school_steps"] = 96 if is_reuse else 72
    run = b.ActiveRun(agent, nominal)
    if case in ("pending", "inbox", "cancelled"):
        run.choose_probe(18)
        if case == "inbox":
            receipt = bb.physical_receipt(run)
            run.queue_receipt(receipt)
            cost["diagnostic_steps"] += len(receipt.applied)
        if case == "cancelled":
            run.cancel()
        return run, cost
    bb.finish_diagnosis(run)
    cost["diagnostic_steps"] += run.diagnostic_clock()["reported_ticks"]
    if case == "ambiguous":
        if run.session.diagnosis()["confirmed"]:
            raise AssertionError("missing ambiguous witness")
        return run, cost
    if not run.session.diagnosis()["confirmed"]:
        raise AssertionError("recipe lacks confirmed reference")
    if case == "confirmed":
        return run, cost
    if case in ("terminal", "terminal_fork"):
        # Real out-of-prior negative witness, not a fabricated terminal flag.
        run.agent.env = RecoveryEnv(body, h_coupled=False, heat=-127)
    if is_reuse:
        target = cb.packet(cb.physical_step(body, 0, True, True, 0))
        run.arm_reuse(target, token=agent.trial_token + 1, restored=True, nominal_body_confirmed=True)
    else:
        run.start_recovery(restored=True, same_context=True,
                           mode="no_protection" if case == "unprotected" else "selective")
    if case == "reuse":
        return run, cost
    if case == "veto":
        agent.cam.slot[agent.cam.get(run.initial)].flags |= SLOT_FLAG_INHIBIT
    limit = 128 if case == "stopped" else 1 if is_reuse or case in ("veto", "terminal", "terminal_fork") else cut
    for _ in range(limit):
        if agent.episode_terminal:
            break
        try:
            run.step(greedy=True)
        except RecoveryStop:
            break
    cost["native_prefix_turns"] = agent.life_turns
    if case == "stopped" and agent.recovery.stopped != "no_safe_action":
        raise AssertionError("missing genuine stopped witness")
    if case in ("terminal", "terminal_fork") and not agent.episode_terminal:
        raise AssertionError("missing genuine terminal witness")
    if case in ("selective", "unprotected", "veto", "stopped", "terminal"):
        return run, cost
    parent = cb.wrap(run)
    if case in ("fork_left", "fork_right", "terminal_fork"):
        return parent.fork("left", "right")[case == "fork_right"], cost
    fresh = Body(bodies[1][0], bodies[0][1])
    child = parent.allocate_body(fresh, body_id="body-2", token="allocation-" + stage,
                                 individual="echo-2" if case.startswith("descendant") else None)
    cost["allocated_bodies"] = 1
    if case.endswith("quarantine"):
        return child, cost
    cb.commission(child)
    cost["calibration_steps"] = 72
    cb.finish_diagnosis(child)
    cost["diagnostic_steps"] += child.active.diagnostic_clock()["reported_ticks"]
    cb.authorize(child)
    return child, cost


def trajectory(run, horizon):
    result = {"A": ab.trajectory, "B": bb.trajectory, "C": cb.trajectory}[kind(run)](run, horizon)
    if "steps" in result:
        result["events"] = result.pop("steps")
    return result


def physical(result):
    return [{k: v for k, v in row.items() if k != "state_sha256"} for row in result["events"]]


def controls(stage):
    """Real history-loss continuation and a separately labelled Q microprobe."""
    run, cost = prepared(stage, "nominal2")
    baseline, lost = clone(run), clone(run)
    lost.agent.sensation.start(lost.agent.observation(lost.agent.env.cell()))
    before = baseline.state_hash() != lost.state_hash()
    rows = []
    native_nonzero = sum(v != 0 for row in run.agent.q.rem for v in row)
    for i in range(3):
        actions = [r.step(greedy=i == 2) for r in (baseline, lost)]
        rows.append({"actions": actions,
                     "predictions": [asdict(r.agent.last_sensory_prediction) for r in (baseline, lost)],
                     "pattern_observations": [r.agent.sensation.memory.observations for r in (baseline, lost)],
                     "state_sha256": [r.state_hash() for r in (baseline, lost)]})
    # Encode any WSP prediction bytes explicitly, not an opaque str(object).
    for row in rows:
        for prediction in row["predictions"]:
            if prediction["packet"] is not None:
                prediction["packet"] = prediction["packet"].hex()
    history_changed = any(r["pattern_observations"][0] != r["pattern_observations"][1] for r in rows)
    # WORLD-1 supplies no positive live reward. Synthetic credit is declared
    # only for this arithmetic witness, not injected into an agent trajectory.
    original = copy.deepcopy(run.agent.q)
    slot = run.agent.cam.get(run.agent.observation(run.agent.env.cell()))
    original.update(slot, 0, 1, slot)
    resumed = b.CODEC.decode(b.CODEC.encode(original))
    missing = b.CODEC.decode(b.CODEC.encode(original))
    missing.rem = [[0] * 3 for _ in range(4096)]
    arithmetic = []
    direct_q, direct_rem = original.get(slot, 0), original.rem[slot][0]
    for _ in range(4):
        backed = 7 * max(original.row(slot)) // 8
        delta = 1 + backed - direct_q
        owed = direct_rem + delta
        change = (abs(owed) // 4) * (-1 if owed < 0 else 1)
        direct_q += change
        direct_rem = owed - 4 * change
        for table in (original, resumed, missing):
            table.update(slot, 0, 1, slot)
        arithmetic.append({"kept": [original.get(slot, 0), original.rem[slot][0]],
                           "resumed": [resumed.get(slot, 0), resumed.rem[slot][0]],
                           "missing": [missing.get(slot, 0), missing.rem[slot][0]],
                           "direct": [direct_q, direct_rem]})
    checks = {"history_state_loss_detected": before,
              "history_learning_loss_detected": history_changed,
              "remainder_exact": all(r["kept"] == r["resumed"] == r["direct"] for r in arithmetic),
              "remainder_update_loss_detected": any(r["kept"][0] != r["missing"][0] for r in arithmetic)}
    return {"history": {"preparation_cost": cost, "native_turns_per_arm": 3, "rows": rows,
                         "action_differences": sum(r["actions"][0] != r["actions"][1] for r in rows),
                         "prediction_differences": sum(r["predictions"][0] != r["predictions"][1] for r in rows)},
            "remainder": {"native_nonzero_entries": native_nonzero, "synthetic_reward": 1,
                           "prefix_updates": 1, "rows": arithmetic, "not_world_reward": True},
            "checks": checks, "passed": all(checks.values())}


def mutant_suite(stage):
    nominal, _ = prepared(stage, "nominal2")
    recovery, _ = prepared(stage, "selective")
    quarantine, _ = prepared(stage, "body_quarantine")
    sources = {"A": nominal.dumps(), "B": recovery.dumps(), "C": quarantine.dumps()}
    rejected = {}
    for name in MUTANTS:
        profile = "B" if name in ("permission", "confirmation") else "C" if name in ("epoch", "allocation", "receipt_scope") else "A"
        raw = sources[profile]
        data = json.loads(raw)
        if name == "receipt_scope":
            before = quarantine.dumps()
            try:
                quarantine.start_recovery(scope="0" * 64, restored=True, same_context=True)
            except ValueError:
                rejected[name] = quarantine.dumps() == before
            else:
                rejected[name] = False
            continue
        if name == "clock":
            data["next_turn"] += 1
        elif name == "body":
            next(r for r in data["state"]["objects"] if r["type"] == "agent")["fields"]["H"] = 0
        elif name == "schema":
            data["schema"] = "invalid"
        elif name == "sources":
            data["sources"] = {}
        elif name == "permission":
            next(r for r in data["state"]["objects"] if r["type"] == "recovery_agent")["fields"]["self_model"] = None
        elif name == "confirmation":
            next(r for r in data["state"]["objects"] if r["type"] == "session")["fields"]["finished"] = False
        elif name == "epoch":
            data["ancestry"][-1]["identity"]["epoch"] = 0
            c._seal(data["ancestry"][-1])
        elif name == "allocation":
            data["ancestry"][-1]["allocation"]["external_h"] += 1
            c._seal(data["ancestry"][-1])
        candidate = a.canonical(data)
        try:
            module(profile).loads(candidate, expected_sha256="0" * 64 if name == "digest" else sha(candidate))
        except ValueError:
            rejected[name] = True
        else:
            rejected[name] = False
    unchanged = all(run.dumps() == sources[kind(run)] for run in (nominal, recovery, quarantine))
    return {"rejected": rejected, "origins_unchanged": unchanged,
            "passed": unchanged and set(rejected) == set(MUTANTS) and all(rejected.values())}
