"""Development and adverse witnesses. No held-out cohort execution on import."""
import random
from echoai.echo4.continuity import canonical
from echoai.echo4.other_replay import digest, replay, transcript
from echoai.echo4.interaction_social import SocialSession
from echoai.echo4.interaction_learning import ARMS, BELIEF_SOURCE

ROUNDS = 480
FORMATION = 288
DEVELOPMENT = (71, 83, 97)
COHORTS = (tuple(range(262001, 262009)), tuple(range(262101, 262109)))
MARGIN = 32


def fixture(seed):
    rng, pairs = random.Random(seed), []
    for _ in range(ROUNDS // 6):
        block = [(cue, handle) for cue in range(3) for handle in (1, 2)]
        rng.shuffle(block)
        pairs.extend(block)
    return tuple(c for c, _ in pairs), tuple(h for _, h in pairs), bool(rng.randrange(2))


def summary(frames):
    result = {key: [0, 0, 0] for key in ("paid", "output", "net")}
    private = [0, 0, 0]
    for f in frames:
        for key in result:
            result[key][0] += f[key][0]
            result[key][f["handle"]] += f[key][1]
        private[f["handle"]] += f["private_credit"]
    return {**result, "private_credit_excluded": private, "rounds": len(frames),
            "joint_net": sum(result["net"]), "joint_rounds": sum(f["joint_executed"] for f in frames),
            "incapable_attempts": sum(sum(f["incapable"]) for f in frames)}


def reconstructs(session, frames):
    for i, model in enumerate((session.observer.model, *session.peer_models)):
        selected = frames if i == 0 else [f for f in frames if f["handle"] == i]
        observer = 0 if i == 0 else 1
        expected = {"forecasts": [f["forecasts"][observer] for f in selected],
                    "predictions": [f["predictions"][observer] for f in selected], "memory_sha256": digest(model)}
        if canonical(expected) != canonical(replay(transcript(selected, observer), model.mode)):
            return False
    return True


def execute(seed, arm, *, reverse=False):
    cues, schedule, swapped = fixture(seed)
    session = SocialSession(cues, schedule, arm=arm, swapped=swapped)
    frames = [session.step(greedy=t >= FORMATION, order=(1, 0) if reverse else (0, 1))
              for t in range(ROUNDS)]
    checks = {"invariants": session.invariant(), "public_replay": reconstructs(session, frames),
              "native_step_budget": sum(a.metrics.turns for a in session.all_agents) == 1440,
              "q_learned": all(a.metrics.deltas > 0 for a in session.all_agents),
              "beliefs_not_facts": all(not s.has_fact and not s.extract for s in session.focal.cam.slot
                                       if s.occupied and s.source == BELIEF_SOURCE),
              "resource_conservation": all(session.ledger[i] + summary(frames)["paid"][i] == 4096
                                           for i in range(3))}
    return {"seed": seed, "arm": arm, "swapped": swapped, "frames": frames,
            "formation": summary(frames[:FORMATION]), "scored": summary(frames[FORMATION:]),
            "whole_life": summary(frames), "remaining": session.ledger, "checks": checks}


def cohort(seeds, *, progress=None):
    lives = []
    for seed in seeds:
        arms = {}
        for arm in ARMS:
            primary, reverse = execute(seed, arm), execute(seed, arm, reverse=True)
            primary["checks"]["order_invariant"] = canonical(primary) == canonical(reverse)
            arms[arm] = primary
        lives.append({"seed": seed, "arms": arms})
        if progress:
            progress(seed)
    totals = {arm: {"focal_net": sum(l["arms"][arm]["scored"]["net"][0] for l in lives),
                    "joint_net": sum(l["arms"][arm]["scored"]["joint_net"] for l in lives)} for arm in ARMS}
    checks = {"all_native_checks": all(all(a["checks"].values()) for l in lives for a in l["arms"].values()),
              "no_life_loses_to_solo": all(l["arms"]["identity"]["scored"]["net"][0]
                                          >= l["arms"]["solo"]["scored"]["net"][0] for l in lives)}
    for arm in ARMS[1:]:
        for measure in ("focal_net", "joint_net"):
            checks[measure + "_over_" + arm] = totals["identity"][measure] - totals[arm][measure] >= MARGIN * len(seeds)
    return {"seeds": seeds, "lives": lives, "totals": totals, "checks": checks, "passed": all(checks.values())}


def adverse():
    """Small transparent witnesses; fault injection and mutation tests also in unittest."""
    results = {}

    def store(name, session, frames, checks):
        checks.update(invariants=session.invariant(), public_replay=reconstructs(session, frames))
        results[name] = {"frames": frames, "summary": summary(frames), "native_steps": 480 + 2 * len(frames),
                         "checks": checks, "passed": all(checks.values())}

    def warm(**kwargs):
        session = SocialSession((0,) * 84, (1,) * 84, **kwargs)
        frames = [session.step(greedy=t >= 48) for t in range(72)]
        return session, frames

    s = SocialSession((0,) * 84, (1,) * 72 + (2,) * 12)
    frames = [s.step(greedy=t >= 48) for t in range(84)]
    store("new_identity", s, frames, {"no_inherited_forecast": frames[72]["forecasts"][0][1] == (None,) * 3,
                                     "unknown_belief": bytes.fromhex(frames[72]["belief"])[15] == 0})
    for name, options in (("hidden_cue", {"visible": (False, True)}),
                          ("untracked", {"tracked": False})):
        s, frames = warm()
        event = s.step(greedy=True, **options)
        frames.append(event)
        store(name, s, frames, {"unknown": event["forecasts"][0][1] == (None,) * 3,
                               "unknown_belief": bytes.fromhex(event["belief"])[15] == 0})
    s = SocialSession((0,) * 24, (1,) * 24)
    frames = [s.step(outcomes=(False, True)) for _ in range(24)]
    store("missing_receipts", s, frames, {"no_invented_wait": all(f["outcomes"][0][1] is None
                                                                 and f["forecasts"][0][1] == (None,) * 3 for f in frames)})
    s, frames = warm()
    first = s.step(greedy=True, veto=(False, True))
    frames.append(first)
    after = s.step(greedy=True)
    frames.append(after)
    store("noncompliance", s, frames, {"prior_not_rewritten": first["predictions"][0] == 0,
                                      "actual_wait": first["actions"][1] == 2 and not first["joint_executed"],
                                      "conflict_abstention": bytes.fromhex(after["belief"])[15] == 0})
    s, frames = warm()
    event = s.step(greedy=True, tracked=False, outcomes=(False, True), veto=(False, True))
    frames.append(event)
    store("absent_participation", s, frames, {"no_agreement": not event["joint_executed"],
                                             "no_peer_fact": event["contexts"][0][1] is None and event["outcomes"][0][1] is None})
    s, frames = warm()
    event = s.step(greedy=True, veto=(True, False))
    frames.append(event)
    store("operator_veto", s, frames, {"real_gate": event["proposals"][0] == 0 and event["actions"][0] == 2,
                                      "not_rewarded_as_join": event["net"][0] == 0 and not event["joint_executed"]})
    for name, cue, budget, arm in (("high_cost", 1, (8, 8, 8), "always_join"),
                                   ("exhaustion", 0, (3, 3, 3), "always_join"),
                                   ("zero_resource", 0, (0, 0, 0), "identity")):
        s = SocialSession((cue,) * 8, (1,) * 8, arm=arm, resources=budget)
        frames = [s.step() for _ in range(8)]
        store(name, s, frames, {"accounted": all(s.ledger[i] + summary(frames)["paid"][i] == budget[i] for i in range(3)),
                               "bounded": all(v >= 0 for v in s.ledger),
                               "no_free_output": all(not any(f["output"]) for f in frames if all(f["incapable"]))})
    s, frames = warm()
    s.stop()
    tick, ledgers = s.world.tick, tuple(s.ledger)
    rejected = False
    try:
        s.step()
    except RuntimeError:
        rejected = True
    # Replay is for running observers; stopped status is tested separately.
    results["stop"] = {"checks": {"rejected": rejected, "unchanged": (tick, ledgers) == (s.world.tick, tuple(s.ledger)),
                                  "all_observers_stopped": all(m.stopped for m in (s.observer, *s.peer_models))},
                       "frames": frames, "summary": summary(frames), "native_steps": 480 + 2 * len(frames)}
    results["stop"]["passed"] = all(results["stop"]["checks"].values())
    return {"cases": results, "passed": all(r["passed"] for r in results.values())}
