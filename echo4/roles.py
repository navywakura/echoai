"""E4-ROLES-1 A/B: who executes each task type, from observed recent competence.

Competence is private simulator state with declared drift. The learner only
sees its own factual receipts. A counterpart's rank claim is a hypothesis with
provenance and never a fact or competence evidence. Native Agent/Q/gate choose.
"""
import json
import random

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.nexus0.env import Cell, KIND_OBJECT
from echoai.nexus0.loop import Agent
from echoai.nexus0.constants import SLOT_FLAG_INHIBIT
from echoai.echo4.world import integer
from echoai.echo4.continuity import canonical, _unique_pairs, _no_float
from echoai.echo4.other_model import LIMIT
from echoai.echo4.interaction_learning import BeliefAgent
from echoai.echo4.interaction_social import settled

ARMS = ("competence", "cumulative", "static_role", "claimed_rank", "rank_follow", "self_only")
SELF = 2                 # action index: 0 -> counterpart 1, 1 -> counterpart 2, 2 -> self
PERIOD = 96
DELEGATE = (1, 9)        # learner coordination cost, product when competent executes
SELF_COST = 2
EXEC_COST = 2
OUTPUT = 9
ACCEPT = 0
ACCEPT_INCENTIVE = 16
PRIVATE_STEPS = 120
PRIVATE_OFFSET = 2048
ROW_STYLE = 10
CLAIM_STYLE = 11
ROW_SOURCE = "roles1-derived-row"
RECEIPT_SOURCE = "roles1-receipt"
CLAIM_SOURCE = "roles1-rank-claim"
RECEIPT_FIELDS = {"tick", "type", "assignee", "executed", "paid", "output"}
UNKNOWN = 3
NO_ATTEMPT = 6   # competence evidence: assignee (0..2) or assignee + 3 on failure


# ---------------------------------------------------------------- world (A)

def schedule(seed, rounds):
    """Balanced task types and competence regimes with declared drift."""
    integer(seed, 0, (1 << 31) - 1, "seed")
    integer(rounds, 3, LIMIT, "rounds")
    if rounds % 3:
        raise ValueError("rounds must fill balanced blocks")
    rng = random.Random(seed)
    types = []
    for _ in range(rounds // 3):
        block = [0, 1, 2]
        rng.shuffle(block)
        types.extend(block)
    perms = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
    regimes = [rng.choice(perms)]
    for _ in range((rounds - 1) // PERIOD):
        regimes.append(rng.choice([p for p in perms if p != regimes[-1]]))
    return tuple(types), tuple(regimes)


def competent(regimes, tick, task):
    integer(tick, 0, LIMIT - 1, "tick")
    integer(task, 0, 2, "task type")
    return regimes[tick // PERIOD][task]


def settle(assignee, accepted, is_competent, resources):
    """Pure ROLES physics for (learner, counterpart 1, counterpart 2)."""
    integer(assignee, 0, 2, "assignee")
    if type(is_competent) is not bool:
        raise ValueError("competence flag")
    if type(resources) is not tuple or len(resources) != 3:
        raise ValueError("three ledgers required")
    for v in resources:
        integer(v, 0, 8192, "resource")
    paid, output, executed = [0, 0, 0], [0, 0, 0], False
    incapable = [False, False, False]
    if assignee == SELF:
        if accepted is not None:
            raise ValueError("self execution has no acceptance")
        if resources[0] >= SELF_COST:
            executed = True
            paid[0] = SELF_COST
            output[0] = OUTPUT if is_competent else 0
        else:
            incapable[0] = True
    else:
        if resources[0] < DELEGATE[0]:
            if accepted is not None:
                raise ValueError("unreached counterpart cannot act")
            incapable[0] = True
        else:
            if type(accepted) is not bool:
                raise ValueError("delegation requires the counterpart's decision")
            paid[0] = DELEGATE[0]
            peer = assignee + 1
            if accepted and resources[peer] >= EXEC_COST:
                executed = True
                paid[peer] = EXEC_COST
                output[0] = DELEGATE[1] if is_competent else 0
            elif accepted:
                incapable[peer] = True
    return {"assignee": assignee, "accepted": accepted, "executed": executed,
            "paid": tuple(paid), "output": tuple(output),
            "net": tuple(output[i] - paid[i] for i in range(3)), "incapable": tuple(incapable)}


# ------------------------------------------------------- receipts in own CAM

def receipt_key(tick):
    integer(tick, 0, LIMIT - 1, "receipt tick")
    return pack(src=2, rel=23, dst=3, time=9, domain=9, generator=8,
                style=34 + (tick >> 8), slot=0, seq=tick & 255)


def claim_key(tick, handle):
    integer(tick, 0, LIMIT - 1, "claim tick")
    integer(handle, 1, 2, "claimant")
    return pack(src=3, rel=24, dst=2, time=9, domain=9, generator=8,
                style=CLAIM_STYLE + 2 * (tick >> 8), slot=handle, seq=tick & 255)


def check_receipt(r):
    if type(r) is not dict or set(r) != RECEIPT_FIELDS:
        raise ValueError("receipt schema")
    integer(r["tick"], 0, LIMIT - 1, "tick")
    integer(r["type"], 0, 2, "type")
    integer(r["assignee"], 0, 2, "assignee")
    if type(r["executed"]) is not bool:
        raise ValueError("executed flag")
    integer(r["paid"], 0, SELF_COST, "own cost")
    integer(r["output"], 0, OUTPUT, "own output")
    own = SELF_COST if r["assignee"] == SELF else DELEGATE[0]
    allowed = {(False, 0, 0), (True, own, 0), (True, own, OUTPUT)}
    if r["assignee"] != SELF:
        allowed.add((False, own, 0))  # delegated, not executed
    if (r["executed"], r["paid"], r["output"]) not in allowed:
        raise ValueError("receipt inconsistent with ROLES physics")
    return r


class RoleMemory:
    """Bounded factual receipts and non-factual rank claims in the learner CAM."""

    def __init__(self, cam):
        if not isinstance(cam, Cam) or any(s.occupied and s.source in (RECEIPT_SOURCE, CLAIM_SOURCE)
                                           for s in cam.slot):
            raise ValueError("requires own CAM without a ROLES journal")
        self.cam = cam
        self.count = self.claims = 0
        self.last_tick = -1
        self.stopped = False

    def record(self, receipt):
        if self.stopped or self.count >= LIMIT:
            raise RuntimeError("receipt journal stopped/budget exhausted")
        r = check_receipt(dict(receipt))
        if r["tick"] <= self.last_tick:
            raise ValueError("duplicate or backwards receipt")
        raw = receipt_key(r["tick"])
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1,
                           extract=canonical(r).decode("ascii"), source=RECEIPT_SOURCE, key=raw)
        if slot < 0:
            raise RuntimeError("ROLES CAM capacity exhausted; no fallback slot")
        self.last_tick = r["tick"]
        self.count += 1
        return raw

    def claim(self, tick, handle):
        """A claimed rank is stored as a hypothesis with provenance, never a fact."""
        if self.stopped:
            raise RuntimeError("journal stopped")
        raw = claim_key(tick, handle)
        if self.cam.get(raw) >= 0:
            raise ValueError("claim already recorded")
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=0,
                           extract="", source=CLAIM_SOURCE, key=raw)
        if slot < 0:
            raise RuntimeError("ROLES CAM capacity exhausted; no fallback slot")
        self.claims += 1
        return raw

    def receipts(self):
        rows = []
        for tick in range(self.last_tick + 1):
            slot = self.cam.get(receipt_key(tick))
            if slot < 0:
                continue
            s = self.cam.slot[slot]
            if s.source != RECEIPT_SOURCE or s.has_fact != 1 or not s.extract or len(s.extract) > 512:
                raise ValueError("invalid receipt provenance")
            r = json.loads(s.extract, object_pairs_hook=_unique_pairs, parse_float=_no_float,
                           parse_constant=_no_float)
            check_receipt(r)
            if r["tick"] != tick or s.extract != canonical(r).decode("ascii"):
                raise ValueError("receipt key/canonical mismatch")
            rows.append(r)
        if len(rows) != self.count:
            raise ValueError("receipt count mismatch")
        return rows

    def claimants(self):
        """Handles that asserted high rank. Hypotheses only: never evidence."""
        found = set()
        for s in self.cam.slot:
            if s.occupied and s.source == CLAIM_SOURCE:
                if s.has_fact or s.extract:
                    raise ValueError("rank claim became a fact")
                found.add(s.wsp[14])
        return found

    def invariant(self):
        try:
            self.receipts()
            self.claimants()
            return bool(self.cam.destroyed == 0
                        and self.count == sum(s.occupied and s.source == RECEIPT_SOURCE for s in self.cam.slot)
                        and self.claims == sum(s.occupied and s.source == CLAIM_SOURCE for s in self.cam.slot))
        except (ValueError, TypeError, KeyError):
            return False

    def stop(self):
        self.stopped = True


def last_attempt(receipts, task):
    """Amendment 1: last executed attempt at this type, who and whether it produced."""
    for r in reversed(receipts):
        if r["type"] == task and r["executed"]:
            return r["assignee"] + (0 if r["output"] > 0 else 3)
    return NO_ATTEMPT


def cumulative_success(receipts, task):
    counts = [0, 0, 0]
    for r in receipts:
        if r["type"] == task and r["executed"] and r["output"] > 0:
            counts[r["assignee"]] += 1
    best = max(counts)
    return UNKNOWN if best == 0 or counts.count(best) > 1 else counts.index(best)


def row(arm, task, resource, *, evidence=UNKNOWN):
    if arm not in ARMS:
        raise ValueError("unsupported ROLES arm")
    integer(task, 0, 2, "task type")
    integer(resource, 0, 8192, "own resource")
    integer(evidence, 0, NO_ATTEMPT, "row evidence")
    if arm == "competence":
        seq = 32 + evidence          # type-free (amendment 1)
    elif arm == "cumulative":
        if evidence > UNKNOWN:
            raise ValueError("cumulative evidence")
        seq = 48 + evidence          # type-free, same structure (amendment 1)
    elif arm == "claimed_rank":
        if evidence > UNKNOWN:
            raise ValueError("claim evidence")
        seq = 4 * task + evidence
    else:
        seq = 4 * task
    return pack(src=2, rel=29, dst=3, domain=9, generator=8, style=ROW_STYLE,
                slot=min(5, resource), seq=seq)


# ------------------------------------------------------------ agents (B)

class RolesAgent(BeliefAgent):
    def __init__(self, env, arm):
        if arm not in ARMS:
            raise ValueError("unsupported ROLES arm")
        super().__init__(env, "identity")
        self.roles_arm = arm

    def _slot_for(self, wsp, vertex, extract, e6, source="nexus0-env"):
        if wsp[10:14] != bytes((0, 9, 8, ROW_STYLE)):
            return super()._slot_for(wsp, vertex, extract, e6, source)
        slot = self.cam.get(wsp)
        if slot < 0:
            slot, _ = allocate(self.cam, wsp, vertex, 0, e6, has_fact=0,
                               extract="", source=ROW_SOURCE, key=wsp)
        if slot < 0:
            raise RuntimeError("no capacity for a non-factual ROLES row")
        if self.operator_inhibit:
            self.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        return slot

    def _propose(self, slot, turn_i, greedy=False):
        if self.roles_arm == "self_only":
            return SELF
        if self.roles_arm == "rank_follow":
            return self.rank_leader
        return super()._propose(slot, turn_i, greedy=greedy)


class Port:
    kind = (KIND_OBJECT,) * 7

    def __init__(self, session, actor, index=0):
        self._session, self._actor, self.i = session, actor, index

    def cell(self):
        return Cell(self.i, KIND_OBJECT, extract_text=f"roles context={self.i}")

    def step(self, action):
        return self._session._commit(self._actor, action), settled()


class AcceptTraining:
    """Private counterpart training: +16 for accepting an assignment (excluded)."""
    kind = (KIND_OBJECT,) * 7

    def __init__(self, cells):
        self._cells, self.steps = cells, 0

    @property
    def i(self):
        return self._cells[min(self.steps, len(self._cells) - 1)]

    def cell(self):
        return Cell(self.i, KIND_OBJECT, extract_text=f"private assignment type={self.i - 4}")

    def step(self, action):
        integer(action, 0, 2, "native action")
        if self.steps >= len(self._cells):
            raise RuntimeError("private training exhausted")
        self.steps += 1
        reward = ACCEPT_INCENTIVE - EXEC_COST if action == ACCEPT else -ACCEPT_INCENTIVE
        return reward, settled()


def counterpart(seed):
    rng = random.Random(seed)
    agent = Agent(env=AcceptTraining(tuple(4 + rng.randrange(3) for _ in range(PRIVATE_STEPS))),
                  ask=False, cortex=False, plan_depth=0, remainder=True,
                  explore_flat=True, evidence_budget=4)
    agent.thought_log = None
    for step in range(PRIVATE_STEPS):
        agent.turn(PRIVATE_OFFSET + step)
    return agent


class RolesSession:
    def __init__(self, seed, rounds, *, arm="competence", resources=(4096, 4096, 4096), claimant=2):
        if arm not in ARMS:
            raise ValueError("unsupported ROLES arm")
        integer(claimant, 1, 2, "claimant")
        if type(resources) is not tuple or len(resources) != 3:
            raise ValueError("three ledgers")
        for v in resources:
            integer(v, 0, 8192, "resource")
        self.seed, self.arm, self.claimant = seed, arm, claimant
        self.types, self.regimes = schedule(seed, rounds)
        self.ledger = list(resources)
        self.focal = RolesAgent(Port(self, 0), arm)
        self.focal.rank_leader = claimant - 1
        self.partners = tuple(counterpart(seed * 4 + i) for i in (1, 2))
        for p in self.partners:
            p.env = Port(self, 1)
        self.all_agents = (self.focal, *self.partners)
        self.memory = RoleMemory(self.focal.cam)
        self.tick = 0
        self.turns = [0, PRIVATE_STEPS, PRIVATE_STEPS]
        self.failed = self.stopped = False
        self._active = False
        self._state = None
        self.private_credit = [0, 0, 0]

    @property
    def done(self):
        return self.stopped or self.tick >= len(self.types)

    def evidence(self, task):
        receipts = self.memory.receipts()  # prior rounds only
        if self.arm == "competence":
            return last_attempt(receipts, task)
        if self.arm == "cumulative":
            return cumulative_success(receipts, task)
        if self.arm in ("claimed_rank",):
            leaders = sorted(self.memory.claimants())
            return leaders[0] - 1 if len(leaders) == 1 else UNKNOWN
        return UNKNOWN

    def step(self, *, greedy=False, veto=(False, False, False)):
        if self.failed or self.done or self._active:
            raise RuntimeError("roles session stopped/exhausted/in flight")
        if type(greedy) is not bool or type(veto) is not tuple or len(veto) != 3 \
                or any(type(v) is not bool for v in veto):
            raise ValueError("greedy/veto")
        tick, task = self.tick, self.types[self.tick]
        self._active = True
        try:
            # The claim arrives every round, in every arm, as a hypothesis.
            self.memory.claim(tick, self.claimant)
            evidence = self.evidence(task)
            packet = row(self.arm, task, self.ledger[0], evidence=evidence)
            self._state = {"tick": tick, "task": task, "veto": veto, "event": None, "partner_action": None}
            self.focal.belief_packet = packet
            if veto[0]:
                self.focal.operator_inhibit = True
            action = self.focal.turn(tick, greedy=greedy)
            self.turns[0] += 1
            event = self._state["event"]
            if event is None or event["assignee"] != action:
                raise RuntimeError("ROLES execution receipt mismatch")
            receipt = {"tick": tick, "type": task, "assignee": action, "executed": event["executed"],
                       "paid": event["paid"][0], "output": event["output"][0]}
            self.memory.record(receipt)
            self.tick += 1
            return {"tick": tick, "type": task, "competent": competent(self.regimes, tick, task),
                    "row": packet.hex(), "evidence": evidence, "proposal": self.focal.last_proposed_action,
                    "gate": self.focal.last_gate_decision, "partner_action": self._state["partner_action"],
                    **event, "ledger": tuple(self.ledger)}
        except Exception:
            self.failed = True
            self.stop()
            raise
        finally:
            self._active = False

    def _commit(self, actor, action):
        state = self._state
        integer(action, 0, 2, "action")
        if not self._active or state is None:
            raise RuntimeError("missing ROLES transaction")
        if actor == 1:
            state["partner_action"] = action
            return (ACCEPT_INCENTIVE - EXEC_COST) if action == ACCEPT else -ACCEPT_INCENTIVE
        if state["event"] is not None:
            raise RuntimeError("duplicate ROLES commit")
        tick, task = state["tick"], state["task"]
        accepted = None
        if action != SELF and self.ledger[0] >= DELEGATE[0]:
            partner = self.partners[action]
            partner.env = Port(self, 1, 4 + task)
            if state["veto"][action + 1]:
                slot = partner.cam.get(partner.observation(partner.env.cell()))
                if slot < 0:
                    raise ValueError("counterpart veto requires an observed context")
                partner.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
            decision = partner.turn(PRIVATE_OFFSET + PRIVATE_STEPS + tick, greedy=True)
            self.turns[action + 1] += 1
            if state["partner_action"] != decision:
                raise RuntimeError("counterpart receipt mismatch")
            accepted = decision == ACCEPT
            self.private_credit[action + 1] += ACCEPT_INCENTIVE if accepted else -ACCEPT_INCENTIVE
        event = settle(action, accepted, competent(self.regimes, tick, task) == action,
                       tuple(self.ledger))
        for i in range(3):
            self.ledger[i] -= event["paid"][i]
        state["event"] = event
        return event["net"][0]

    def stop(self):
        self.stopped = True
        self.memory.stop()

    def invariant(self):
        agents = self.all_agents
        isolated = all(len({id(getattr(a, k)) for a in agents}) == 3 for k in ("cam", "t", "q"))
        return bool(isolated and not self._active and self.memory.invariant()
                    and self.memory.count == self.tick
                    and all(a.metrics.turns == n for a, n in zip(agents, self.turns))
                    and all(a.metrics.false_facts == 0 and a.cam.destroyed == 0
                            and a.metrics.cortex_calls == 0 and not a.cortex_enabled
                            and all(len(s.wsp) == 16 and (not s.has_fact or bool(s.extract))
                                    and (s.source not in (ROW_SOURCE, CLAIM_SOURCE)
                                         or not s.has_fact and not s.extract)
                                    for s in a.cam.slot if s.occupied)
                            for a in agents)
                    and all(v >= 0 for v in self.ledger))
