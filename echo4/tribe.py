"""E4-ROLES-1 v3 «la tribu»: elimination, derived rank, role reversal.

Three native learners with the same class and private CAM/T/Q. Who knows each
topic is private simulator state; hierarchy is never stored as a label but
derived from each agent's own verified receipts. A testimony ("I don't know")
is a fact that it was said and only a hypothesis about knowledge. Rank claims
are hypotheses with provenance. Responders answer by knowledge (honest in the
nominal world). All learners use native periodic exploration (lesson of v2).
"""
import json
import random

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT, GATE_BLOCK
from echoai.echo4.world import integer
from echoai.echo4.continuity import canonical, _unique_pairs, _no_float
from echoai.echo4.interaction_learning import BeliefAgent
from echoai.echo4.interaction_social import settled

ECHO, B, C = 0, 1, 2
NAMES = ("ECHO", "B", "C")
ARMS = ("tribe", "no_elimination", "no_rank", "claimed_rank", "fixed_order")
PREDICTORS = ("tribe", "no_elimination", "no_rank", "claimed_rank")
REGIME, HALF, ROUNDS = 96, 48, 384
ATTEMPTS = 3
ASK_COST, SELF_COST, ANSWER = 1, 2, 9
WINDOW = 96
EVENT_LIMIT = 2048
KINDS = ("answered", "said_no", "self_ok", "self_fail")
ROW_STYLE = 12
ROW_SOURCE, RECEIPT_SOURCE = "tribe-row", "tribe-receipt"
TESTIMONY_SOURCE, CLAIM_SOURCE = "tribe-testimony", "tribe-rank-claim"
FIELDS = {"n", "tick", "topic", "seeker", "target", "kind"}
UNKNOWN = 3
# Topic counts per regime, (ECHO, B, C). Hierarchy is real but never declared.
DISTRIBUTION = ((1, 0, 2), (1, 0, 2), (0, 2, 1), (1, 0, 2))


# ------------------------------------------------------------------ world

def schedule(seed):
    integer(seed, 0, (1 << 31) - 1, "seed")
    rng = random.Random(seed)
    topics, knower, seekers = [], {}, []
    for half in range(ROUNDS // HALF):
        ids = [half * 3 + k for k in range(3)]
        owners = [a for a in range(3) for _ in range(DISTRIBUTION[half // 2][a])]
        rng.shuffle(owners)
        knower.update(zip(ids, owners))
        for _ in range(HALF // 3):
            block = list(ids)
            rng.shuffle(block)
            topics.extend(block)
    for _ in range(ROUNDS // 3):
        block = [ECHO, ECHO, B]
        rng.shuffle(block)
        seekers.extend(block)
    return tuple(topics), knower, tuple(seekers)


def true_order(tick):
    counts = DISTRIBUTION[tick // REGIME]
    return tuple(sorted(range(3), key=lambda a: -counts[a]))


def others(seeker):
    return tuple(a for a in range(3) if a != seeker)


def absolute(seeker, rel):
    integer(rel, 0, 2, "relative action")
    return seeker if rel == 2 else others(seeker)[rel]


def relative(seeker, agent):
    if agent is None:
        return UNKNOWN
    return 2 if agent == seeker else others(seeker).index(agent)


# --------------------------------------------------------- memory in own CAM

def event_key(n):
    integer(n, 0, EVENT_LIMIT - 1, "event")
    return pack(src=2, rel=27, dst=3, time=9, domain=9, generator=8,
                style=50 + (n >> 8), slot=0, seq=n & 255)


def check(r):
    if type(r) is not dict or set(r) != FIELDS:
        raise ValueError("tribe receipt schema")
    integer(r["n"], 0, EVENT_LIMIT - 1, "n")
    integer(r["tick"], 0, ROUNDS - 1, "tick")
    integer(r["topic"], 0, 3 * ROUNDS // HALF - 1, "topic")
    integer(r["seeker"], 0, 2, "seeker")
    integer(r["target"], 0, 2, "target")
    if r["kind"] not in KINDS:
        raise ValueError("receipt kind")
    if (r["kind"] in ("self_ok", "self_fail")) != (r["seeker"] == r["target"]):
        raise ValueError("self kind must target self")
    return r


class TribeMemory:
    """Facts: events this agent lived. Hypotheses: testimonies, rank claims."""

    def __init__(self, cam, owner):
        if not isinstance(cam, Cam):
            raise ValueError("own CAM required")
        integer(owner, 0, 2, "owner")
        self.cam, self.owner = cam, owner
        self.n = 0
        self.rows = []  # derived cache of validated facts, rebuilt by facts()
        self.stopped = False

    def record(self, tick, topic, seeker, target, kind):
        if self.stopped or self.n >= EVENT_LIMIT:
            raise RuntimeError("tribe journal stopped/budget exhausted")
        r = check({"n": self.n, "tick": tick, "topic": topic, "seeker": seeker,
                   "target": target, "kind": kind})
        if self.owner not in (seeker, target):
            raise ValueError("an agent only records events it lived")
        raw = event_key(self.n)
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1,
                           extract=canonical(r).decode("ascii"), source=RECEIPT_SOURCE, key=raw)
        if slot < 0:
            raise RuntimeError("tribe CAM capacity exhausted; no fallback slot")
        self.n += 1
        self.rows.append(r)
        if kind == "said_no" and seeker == self.owner:
            self._hypothesis(TESTIMONY_SOURCE, 28, target, r["n"])
        return raw

    def claim(self, tick, claimant):
        if self.stopped:
            raise RuntimeError("journal stopped")
        integer(claimant, 0, 2, "claimant")
        self._hypothesis(CLAIM_SOURCE, 24, claimant, tick, style=60)

    def _hypothesis(self, source, rel, subject, n, style=58):
        raw = pack(src=3, rel=rel, dst=2, time=9, domain=9, generator=8,
                   style=style + (n >> 8), slot=subject, seq=n & 255)
        if self.cam.get(raw) >= 0:
            raise ValueError("hypothesis already recorded")
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=0,
                           extract="", source=source, key=raw)
        if slot < 0:
            raise RuntimeError("tribe CAM capacity exhausted; no fallback slot")

    def facts(self):
        """Re-read every fact from CAM and validate it; never trust the cache."""
        rows = []
        for n in range(self.n):
            slot = self.cam.get(event_key(n))
            if slot < 0:
                raise ValueError("missing tribe fact")
            s = self.cam.slot[slot]
            if s.source != RECEIPT_SOURCE or s.has_fact != 1 or not s.extract or len(s.extract) > 256:
                raise ValueError("invalid tribe fact provenance")
            r = check(json.loads(s.extract, object_pairs_hook=_unique_pairs,
                                 parse_float=_no_float, parse_constant=_no_float))
            if r["n"] != n or s.extract != canonical(r).decode("ascii"):
                raise ValueError("tribe fact key/canonical mismatch")
            rows.append(r)
        if rows != self.rows:
            raise ValueError("tribe facts differ from their journal")
        return rows

    def claimants(self):
        found = set()
        for s in self.cam.slot:
            if s.occupied and s.source == CLAIM_SOURCE:
                if s.has_fact or s.extract:
                    raise ValueError("rank claim became a fact")
                found.add(s.wsp[14])
        return found

    def invariant(self):
        try:
            self.facts()
            self.claimants()
            hyp = [s for s in self.cam.slot if s.occupied and s.source in (TESTIMONY_SOURCE, CLAIM_SOURCE)]
            return bool(all(not s.has_fact and not s.extract for s in hyp) and self.cam.destroyed == 0
                        and self.n == sum(s.occupied and s.source == RECEIPT_SOURCE for s in self.cam.slot))
        except (ValueError, TypeError, KeyError):
            return False

    def stop(self):
        self.stopped = True


# ------------------------------------------------------ derived queries

def last_knower(rows, topic):
    for r in reversed(rows):
        if r["topic"] == topic and r["kind"] in ("answered", "self_ok"):
            return r["target"]
    return None


def eliminated(rows, tick, topic):
    return {r["target"] for r in rows
            if r["tick"] == tick and r["topic"] == topic and r["kind"] in ("said_no", "self_fail")}


def rank_counts(rows, tick):
    """Derived rank: verified answers given by each agent in the recent window."""
    counts = [0, 0, 0]
    for r in rows:
        if tick - WINDOW < r["tick"] <= tick and r["kind"] in ("answered", "self_ok"):
            counts[r["target"]] += 1
    return counts


def derived_order(rows, tick):
    counts = rank_counts(rows, tick)
    if len(set(counts)) < 3:
        return None  # ties: no strict order is claimed
    return tuple(sorted(range(3), key=lambda a: -counts[a]))


def leader(counts, candidates):
    if not candidates:
        return None
    best = max(counts[a] for a in candidates)
    top = [a for a in candidates if counts[a] == best]
    return top[0] if len(top) == 1 and best > 0 else None


def suggestion(rows, tick, topic, arm, claimants=frozenset()):
    elim = set() if arm == "no_elimination" else eliminated(rows, tick, topic)
    known = last_knower(rows, topic)
    if known is not None and known not in elim:
        return known, elim
    candidates = [a for a in range(3) if a not in elim]
    if arm in ("tribe", "no_elimination"):
        return leader(rank_counts(rows, tick), candidates), elim
    if arm == "claimed_rank":
        claimed = [a for a in sorted(claimants) if a in candidates]
        return (claimed[0] if len(claimed) == 1 else None), elim
    return None, elim


def row(arm, seeker, suggested, elim):
    if arm not in ARMS:
        raise ValueError("unsupported tribe arm")
    mask = 0 if arm == "no_elimination" else sum(1 << relative(seeker, a) for a in elim)
    seq = 4 * mask + relative(seeker, suggested)
    return pack(src=2, rel=29, dst=3, domain=9, generator=8, style=ROW_STYLE, slot=seeker, seq=seq)


# ----------------------------------------------------------------- agents

class TribeAgent(BeliefAgent):
    def __init__(self, env, arm, index):
        if arm not in ARMS:
            raise ValueError("unsupported tribe arm")
        super().__init__(env, "identity")
        self.evidence_greedy = False  # native periodic exploration, same for all
        self.tribe_arm, self.index, self.attempt = arm, index, 0

    def _slot_for(self, wsp, vertex, extract, e6, source="nexus0-env"):
        if wsp[10:14] != bytes((0, 9, 8, ROW_STYLE)):
            return super()._slot_for(wsp, vertex, extract, e6, source)
        slot = self.cam.get(wsp)
        if slot < 0:
            slot, _ = allocate(self.cam, wsp, vertex, 0, e6, has_fact=0, extract="", source=ROW_SOURCE, key=wsp)
        if slot < 0:
            raise RuntimeError("no capacity for a non-factual tribe row")
        if self.operator_inhibit:
            self.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        return slot

    def _propose(self, slot, turn_i, greedy=False):
        if self.tribe_arm == "fixed_order":
            return self.attempt  # B/others first, then the other, then self
        return super()._propose(slot, turn_i, greedy=greedy)


class Port:
    kind = (KIND_OBJECT,) * 4

    def __init__(self, session, actor):
        self._session, self._actor = session, actor

    def cell(self):
        return Cell(0, KIND_OBJECT, extract_text="tribe question pending")

    def step(self, action):
        reward, more = self._session._commit(self._actor, action)
        return reward, (self.cell() if more else settled())


class TribeSession:
    def __init__(self, seed, *, arm="tribe", mode="free", claimant=B):
        if arm not in ARMS or mode not in ("free", "random"):
            raise ValueError("arm/mode")
        integer(claimant, 0, 2, "claimant")
        self.seed, self.arm, self.mode, self.claimant = seed, arm, mode, claimant
        self.topics, self.knower, self.seekers = schedule(seed)
        self.agents = tuple(TribeAgent(Port(self, i), arm if i == ECHO else "tribe", i) for i in range(3))
        self.memories = tuple(TribeMemory(a.cam, i) for i, a in enumerate(self.agents))
        self.rng = random.Random(seed ^ 0x7B1BE)
        self.tick = 0
        self.turns = [0, 0, 0]
        self.failed = self.stopped = False
        self._round = None

    @property
    def done(self):
        return self.stopped or self.tick >= ROUNDS

    def _row_for(self, seeker):
        rows = self.memories[seeker].rows
        arm = self.arm if seeker == ECHO else "tribe"
        suggested, elim = suggestion(rows, self.tick, self._round["topic"], arm,
                                     frozenset(self.memories[seeker].claimants()))
        return row(arm, seeker, suggested, elim), suggested, elim

    def _event(self, seeker, target, kind):
        t, topic = self.tick, self._round["topic"]
        self.memories[seeker].record(t, topic, seeker, target, kind)
        if target != seeker:
            self.memories[target].record(t, topic, seeker, target, kind)

    def _attempt(self, seeker, target):
        topic = self._round["topic"]
        knows = self.knower[topic] == target
        if target == seeker:
            kind, cost = ("self_ok" if knows else "self_fail"), SELF_COST
        else:
            kind, cost = ("answered" if knows else "said_no"), ASK_COST
        self._event(seeker, target, kind)
        output = ANSWER if knows else 0
        self._round["attempts"].append({"target": target, "kind": kind, "cost": cost, "output": output})
        return output - cost, knows

    def step(self, *, veto=False):
        if self.failed or self.done or self._round is not None:
            raise RuntimeError("tribe session stopped/exhausted/in flight")
        if type(veto) is not bool:
            raise ValueError("veto flag")
        tick, topic, seeker = self.tick, self.topics[self.tick], self.seekers[self.tick]
        self._round = {"tick": tick, "topic": topic, "seeker": seeker, "attempts": [], "predictions": [],
                       "suggestions": []}
        try:
            for listener in (a for a in range(3) if a != self.claimant):
                self.memories[listener].claim(tick, self.claimant)
            if self.mode == "random" and seeker == ECHO:
                self._random_round()
            else:
                agent = self.agents[seeker]
                agent.attempt = 0
                packet, suggested, _ = self._row_for(seeker)
                self._round["suggestions"].append(suggested)
                agent.belief_packet = packet
                if veto and seeker == ECHO:
                    agent.operator_inhibit = True
                self._round["resolved"] = False
                while True:
                    agent.turn(4096 * seeker + self.turns[seeker], greedy=False)
                    self.turns[seeker] += 1
                    if self._round["resolved"] or agent.attempt >= ATTEMPTS:
                        break
            frame = dict(self._round)
            frame["net"] = sum(a["output"] - a["cost"] for a in frame["attempts"])
            frame["solved"] = any(a["output"] for a in frame["attempts"])
            frame["knower"] = self.knower[topic]
            frame["order_true"] = true_order(tick)
            frame["order_derived"] = derived_order(self.memories[ECHO].rows, tick)
            self.tick += 1
            return frame
        except Exception:
            self.failed = True
            self.stop()
            raise
        finally:
            self._round = None

    def _commit(self, actor, rel):
        state = self._round
        if state is None or actor != state["seeker"]:
            raise RuntimeError("missing tribe transaction")
        agent = self.agents[actor]
        if agent.last_gate_decision == GATE_BLOCK:
            state["resolved"] = True
            state["vetoed"] = True
            return 0, False  # veto: nothing is asked, nothing costs
        target = absolute(actor, rel)
        reward, knows = self._attempt(actor, target)
        agent.attempt += 1
        state["resolved"] = knows
        more = not knows and agent.attempt < ATTEMPTS
        if more:
            packet, suggested, _ = self._row_for(actor)
            state["suggestions"].append(suggested)
            agent.belief_packet = packet
        return reward, more

    def _random_round(self):
        """Mode 1: the responder is drawn at random; ECHO only predicts."""
        order = list(others(ECHO))
        self.rng.shuffle(order)
        rows = self.memories[ECHO].rows
        claim = frozenset(self.memories[ECHO].claimants())
        for target in (*order, ECHO):
            self._round["predictions"].append(
                {p: suggestion(rows, self.tick, self._round["topic"], p, claim)[0] for p in PREDICTORS})
            _, knows = self._attempt(ECHO, target)
            if knows:
                break

    def stop(self):
        self.stopped = True
        for m in self.memories:
            m.stop()

    def invariant(self):
        agents = self.agents
        isolated = all(len({id(getattr(a, k)) for a in agents}) == 3 for k in ("cam", "t", "q"))
        return bool(isolated and self._round is None and all(m.invariant() for m in self.memories)
                    and all(a.metrics.turns == n for a, n in zip(agents, self.turns))
                    and all(a.metrics.false_facts == 0 and a.cam.destroyed == 0
                            and a.metrics.cortex_calls == 0 and not a.cortex_enabled
                            and all(len(s.wsp) == 16 and (not s.has_fact or bool(s.extract))
                                    and (s.source not in (ROW_SOURCE, TESTIMONY_SOURCE, CLAIM_SOURCE)
                                         or not s.has_fact and not s.extract)
                                    for s in a.cam.slot if s.occupied)
                            for a in agents))
