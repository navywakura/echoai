"""E4-INTEGRATE-1 «una sola vida»: ECHO's body and tribe share one CAM/T/Q.

Body: the sealed MAINTAIN physics and controller (MaintenanceEnv, MaintainControl).
Tribe: the ROLES v5 session with the annex-L liar. ECHO's tribe agent uses the
body agent's CAM, T and Q objects: one memory. Energy flows between them through
the agent's own receipts (asking costs, a verified answer pays), and the
maintenance belief is shifted by those known credits instead of being reseeded.
B and C have no bodies (amendment 2). Pause/resume is verified by reconstruction
in a fresh process against a full-state fingerprint (amendment 1).
"""
import hashlib
import json

from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.echo4.continuity import canonical
from echoai.echo4.world import Body, integer
from echoai.echo4.maintain_world import MaintenanceEnv
from echoai.echo4.maintain_control import MaintainControl
from echoai.echo4.maintain_model import MaintainStop, bands, prior
from echoai.echo4 import tribe as T
from echoai.echo4 import tribe_exam as E
from echoai.echo4 import situate as S

ARMS = ("integrated", "no_maintain", "no_self", "no_tribe_reasoning", "no_relation",
        "no_firewall", "no_continuity")
MAINT_MODE = {"no_maintain": "fixed", "no_self": "no_history"}
HORIZON, PAUSE = 256, 128
ASK_ENERGY, GAIN_ENERGY = 1, 6
FAULTS_AT = ((48, "clogged"), (176, "clogged"))
HEAT_WINDOW = (96, 144, 2)          # external heat 2 between these ticks
LIAR = (T.B, 2)                      # B lies "no" in regime 3 (ticks 192..287)
SITUATE_AT = (0, 64, 192)
UNFIREWALLED = "integrate-testimony-as-fact"


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def credit(agent, delta):
    """Apply a known energy receipt to ECHO's body and shift its maintenance belief."""
    integer(delta, -127, 127, "energy delta")
    env, model = agent.env, agent.maintenance
    h, t = env.body.h, env.body.temperature
    new = _clamp(h + delta, 1, 127)       # tribe costs never kill; they only drain
    applied = new - h
    if applied == 0:
        return 0
    env.body = Body(new, t)
    if applied > 0:
        env.resource_in += applied
    else:
        env.resource_used += -applied
    agent.H = new
    packet = agent.observation(env.cell())
    hl, hh, tl, th = bands(packet)
    shifted = []
    for a, b, c, d, fault, heat, spares in model.boxes:
        lo, hi = max(_clamp(a + applied, 1, 127), hl), min(_clamp(b + applied, 1, 127), hh)
        c2, d2 = max(c, tl), min(d, th)
        if lo <= hi and c2 <= d2:
            shifted.append((lo, hi, c2, d2, fault, heat, spares))
    if not shifted:
        model.conflicts += 1
        shifted = list(prior(packet, max(b[6] for b in model.boxes)))
    model.boxes = tuple(sorted(set(shifted)))
    model.current = packet
    # The short sensory window (2 steps) restarts at the credited observation:
    # a known receipt, not a sensed transition. T, Q and CAM are untouched.
    agent.sensation.start(packet)
    return applied


def new_body(seed, arm, *, state=None):
    body, fault, spares, heat = (Body(80, 72), "healthy", 3, 0) if state is None else state
    env = MaintenanceEnv(body, fault=fault, spares=spares, external_heat=heat)
    return MaintainControl(env, mode=MAINT_MODE.get(arm, "adaptive"))


class IntegratedTribe(E.TribeCSession):
    """ROLES v5 tribe whose ECHO shares the body agent's CAM/T/Q."""

    def __init__(self, seed, arm, body_agent):
        if arm not in ARMS:
            raise ValueError("unsupported INTEGRATE arm")
        tribe_arm = "fixed_order" if arm == "no_tribe_reasoning" else "tribe"
        super().__init__(seed, arm=tribe_arm, liar=LIAR)
        self.integrate_arm = arm
        self.unfirewalled = set()   # (topic, agent) testimonies wrongly promoted to fact
        self.attach(body_agent)

    def attach(self, body_agent):
        echo = self.agents[T.ECHO]
        echo.cam, echo.t, echo.q = body_agent.cam, body_agent.t, body_agent.q
        self.memories = (T.TribeMemory(body_agent.cam, T.ECHO), *self.memories[1:])
        self.unfirewalled = set()

    def _row_for(self, seeker):
        if seeker != T.ECHO or self.integrate_arm not in ("no_relation", "no_firewall"):
            return super()._row_for(seeker)
        rows, topic = self.memories[T.ECHO].rows, self._round["topic"]
        elim = T.eliminated(rows, self.tick, topic)
        if self.integrate_arm == "no_firewall":
            elim |= {a for (tp, a) in self.unfirewalled if tp == topic}
            suggested, _ = T.suggestion(rows, self.tick, topic, "tribe")
            if suggested in elim:
                suggested = T.leader(T.rank_counts(rows, self.tick), [a for a in range(3) if a not in elim])
        else:
            # No episodic memory of who answered: rank only.
            suggested = T.leader(T.rank_counts(rows, self.tick), [a for a in range(3) if a not in elim])
        return T.row("tribe", seeker, suggested, elim), suggested, elim

    def _event(self, seeker, target, kind):
        super()._event(seeker, target, kind)
        if self.integrate_arm == "no_firewall" and seeker == T.ECHO and kind == "said_no":
            # Ablation: the testimony "I don't know" is promoted to a FACT.
            topic = self._round["topic"]
            if (topic, target) not in self.unfirewalled:
                self.unfirewalled.add((topic, target))
                raw = pack(src=3, rel=34, dst=2, time=9, domain=9, generator=8, style=73,
                           slot=target, seq=topic)
                vertex, latency, _ = encode_event(raw)
                allocate(self.agents[T.ECHO].cam, raw, vertex, latency, (0,) * 6, has_fact=1,
                         extract=f"{T.NAMES[target]} does not know topic {topic}",
                         source=UNFIREWALLED, key=raw)


def fingerprint(life):
    """Full-state digest: CAM, T, Q, body, controller and tribe memory."""
    body, tribe = life["body"], life["tribe"]
    cam = body.cam
    # Substrate readings (pid, host) legitimately differ in a new process; SITUATE
    # re-reads them there. Everything else must match bit for bit.
    slots = [[i, s.wsp.hex(), s.has_fact, s.extract if s.source != S.SOURCE_FACT else "", s.source,
              s.flags, s.hits] for i, s in enumerate(cam.slot) if s.occupied]
    t, q, env, model = body.t, body.q, body.env, body.maintenance
    state = {"cam": slots, "t": [t.pred, t.n, t.alt, t.alt_n, t.conflicts],
             "q": [q.q, q.rem, q.z], "body": [env.body.h, env.body.temperature, body.H,
                                             body.temperature, body.episode_terminal],
             "env": env.audit_state(), "work": env.work_done,
             "model": [model.boxes, model.progress, model.steps, model.conflicts, model.attempts,
                       model.stopped, model.current.hex()],
             "tribe": [tribe.tick, list(tribe.turns), [m.rows for m in tribe.memories]],
             "carry": life["carry"]}
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


def start(seed, arm, *, body_state=None):
    body = new_body(seed, arm, state=body_state)
    tribe = IntegratedTribe(seed, arm, body)
    me = S.SelfKnowledge(body.cam)
    return {"seed": seed, "arm": arm, "body": body, "tribe": tribe, "me": me, "tick": 0,
            "carry": {"work": 0, "repairs": 0, "paid": 0, "resets": 0}, "frames": [], "ended": ""}


def situate_check(life):
    me, tribe = life["me"], life["tribe"]
    if life["tick"] == 0:
        me.observe(S.sense(tribe.agents))
        me.prove_world(S.replay_proof(life["seed"]))
    return all(S.answer(me, q)[0] == S.VERIFIED for q in (1, 2, 3, 4, 5, 6))


def wipe(life):
    """no_continuity: restart ECHO's memory from zero; the physical body carries on."""
    old = life["body"]
    env = old.env
    life["carry"]["work"] += env.work_done
    life["carry"]["repairs"] += env.repairs
    life["carry"]["paid"] += env.services_paid
    life["carry"]["resets"] += 1
    body = new_body(life["seed"], life["arm"],
                    state=(env.body, env._fault, env._spares, env._external_heat))
    tribe = life["tribe"]
    fresh = T.TribeAgent(T.Port(tribe, T.ECHO), tribe.agents[T.ECHO].tribe_arm, T.ECHO)
    tribe.agents = (fresh, *tribe.agents[1:])
    tribe.turns[T.ECHO] = 0
    tribe.attach(body)
    life["body"] = body
    life["me"] = S.SelfKnowledge(body.cam)
    life["me"].observe(S.sense(tribe.agents))
    life["me"].prove_world(S.replay_proof(life["seed"]))


def step(life):
    """One integrated tick: body turn, then tribe round, then energy receipts."""
    for hook in life.get("hooks", {}).get(life["tick"], ()):   # declared adversarial cases only
        hook(life)
    if life["ended"]:
        return None
    tick, body, tribe, env = life["tick"], life["body"], life["tribe"], life["body"].env
    for at, fault in life.get("faults", FAULTS_AT):
        if tick == at and env._fault != "seized":
            env._fault = fault
    env._external_heat = HEAT_WINDOW[2] if HEAT_WINDOW[0] <= tick < HEAT_WINDOW[1] else 0
    frame = {"tick": tick}
    if tick in SITUATE_AT:
        frame["situate_ok"] = situate_check(life)
    try:
        frame["body_action"] = body.turn(tick)
    except MaintainStop as stop:
        life["ended"] = "maintain:" + str(stop)
        return None
    except RuntimeError as stop:          # operator stop latch on the body
        life["ended"] = "operator" if env.stopped else "body:" + str(stop)[:40]
        return None
    if body.episode_terminal:
        life["ended"] = "terminal"
        return None
    try:
        r = tribe.step(veto=life.get("veto_from", HORIZON + 1) <= tick)
    except (ValueError, RuntimeError) as stop:   # corrupt fact, CAM full: stop, never guess
        life["ended"] = "tribe:" + type(stop).__name__
        return None
    frame.update(seeker=r["seeker"], topic=r["topic"], knower=r["knower"], solved=r["solved"],
                 attempts=[a["target"] for a in r["attempts"]],
                 suggestion=r["suggestions"][0] if r["suggestions"] else None,
                 first_ok=bool(r["attempts"]) and r["attempts"][0]["target"] == r["knower"])
    if r["seeker"] == T.ECHO:
        delta = GAIN_ENERGY * int(r["solved"]) - ASK_ENERGY * len(r["attempts"])
        frame["energy"] = credit(body, delta)
    frame["h"], frame["temp"] = env.body.h, env.body.temperature
    life["frames"].append(frame)
    life["tick"] += 1
    return frame


def run(seed, arm, *, until=HORIZON, pause_digest=False, pause=PAUSE, body_state=None, veto_from=None,
        faults=FAULTS_AT, hooks=None):
    life = start(seed, arm, body_state=body_state)
    life["faults"] = tuple(faults)
    life["hooks"] = hooks or {}
    if veto_from is not None:
        life["veto_from"] = veto_from
    digest = None
    while life["tick"] < until and not life["ended"]:
        if life["tick"] == pause:
            if pause_digest:
                digest = fingerprint(life)
            if arm == "no_continuity":
                wipe(life)
        if step(life) is None:
            break
    return life, digest


def false_facts(life):
    """Epistemically false facts: 'X does not know topic' promoted to fact while X knew."""
    tribe = life["tribe"]
    return sum(1 for (topic, agent) in tribe.unfirewalled if tribe.knower[topic] == agent)


def summary(life):
    f = life["frames"]
    echo = [x for x in f if x.get("seeker") == T.ECHO]
    env = life["body"].env
    known = []
    seen = {}
    for x in echo:
        if x["topic"] in seen:
            known.append(x["first_ok"])
        if x["solved"]:
            seen[x["topic"]] = x["knower"]
    pre = [x["first_ok"] for x in echo if PAUSE - 32 <= x["tick"] < PAUSE]
    post = [x["first_ok"] for x in echo if PAUSE <= x["tick"] < PAUSE + 32]
    return {"survived": len(f), "ended": life["ended"],
            "work": life["carry"]["work"] + env.work_done,
            "repairs": life["carry"]["repairs"] + env.repairs,
            "services_paid": life["carry"]["paid"] + env.services_paid,
            "echo_rounds": len(echo), "solved": sum(x["solved"] for x in echo),
            "questions": sum(len(x["attempts"]) for x in echo),
            "known_topic_first_ok": [sum(known), len(known)],
            "pre_pause_first_ok": [sum(pre), len(pre)], "post_pause_first_ok": [sum(post), len(post)],
            "false_facts": false_facts(life),
            "tribe_invariant": life["tribe"].memories[T.ECHO].invariant(),
            "cam_destroyed": life["body"].cam.destroyed,
            "situate_ok": all(x["situate_ok"] for x in f if "situate_ok" in x),
            "cortex_calls": life["body"].metrics.cortex_calls + sum(a.metrics.cortex_calls for a in life["tribe"].agents),
            "trace_sha256": hashlib.sha256(canonical(f)).hexdigest()}


def resume_in_this_process(seed, arm, expected_digest, pause=PAUSE):
    """Rebuild the life up to the pause, verify the full-state fingerprint, then continue."""
    life = start(seed, arm)
    while life["tick"] < pause and not life["ended"]:
        if step(life) is None:
            break
    if fingerprint(life) != expected_digest:
        raise ValueError("pause fingerprint mismatch: reconstruction differs")
    if arm == "no_continuity":
        wipe(life)
    while life["tick"] < HORIZON and not life["ended"]:
        if step(life) is None:
            break
    return summary(life)["trace_sha256"]


def resume_fresh_process(seed, arm, expected_digest, pause=PAUSE):
    import os
    import subprocess
    import sys
    from echoai.echo4.continuity import ROOT
    out = subprocess.run([sys.executable, "-m", "echoai.echo4.integrate", "resume", str(seed), arm, expected_digest, str(pause)],
                         cwd=ROOT.parent, capture_output=True, text=True, timeout=900,
                         env={**os.environ, "PYTHONPATH": str(ROOT.parent)})
    if out.returncode != 0:
        raise RuntimeError("resume child failed: " + out.stderr[-600:])
    return out.stdout.strip()


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 6 and sys.argv[1] == "resume":
        print(resume_in_this_process(int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5])))
