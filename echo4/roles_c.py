"""ROLES-C: refusal, intermediary relay, new member, absence, and a veto fix.

Sealed A/B sources are untouched; this subclass restates step/_commit with
explicit hooks. Defect found after A/B sealing: a gate BLOCK yields the native
WAIT action (2), which in ROLES means "do it yourself", so a vetoed learner
executed and paid. Here a learner BLOCK is a no-op round with no cost. The
nominal A/B bench never vetoes, so its numbers are unaffected (witness C0).
"""
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack
from echoai.nexus0.constants import GATE_BLOCK, SLOT_FLAG_INHIBIT
from echoai.echo4.world import integer
from echoai.echo4.other_model import LIMIT
from echoai.echo4 import roles as R

RELAY_SOURCE = "roles1-relayed-receipt"
RELAYER = 1  # counterpart 1 relays what counterpart 2 did


def relay_key(tick, relayer, produced):
    integer(tick, 0, LIMIT - 1, "relay tick")
    integer(relayer, 1, 2, "relayer")
    if type(produced) is not bool:
        raise ValueError("relayed outcome flag")
    return pack(src=3, rel=25 + int(produced), dst=2, time=9, domain=9, generator=8,
                style=40 + (tick >> 8), slot=relayer, seq=tick & 255)


def noop(assignee):
    return {"assignee": assignee, "accepted": None, "executed": False, "paid": (0, 0, 0),
            "output": (0, 0, 0), "net": (0, 0, 0), "incapable": (False, False, False)}


def window(plan, rounds):
    if plan is None:
        return None
    if type(plan) is not tuple or len(plan) != 3:
        raise ValueError("plan (counterpart, first, last)")
    integer(plan[0], 0, 1, "counterpart")
    integer(plan[1], 0, rounds, "first")
    integer(plan[2], plan[1], rounds, "last")
    return plan


class RolesCSession(R.RolesSession):
    def __init__(self, seed, rounds, *, relay=False, absent=None, declines=None, member=None, **kwargs):
        super().__init__(seed, rounds, **kwargs)
        if type(relay) is not bool:
            raise ValueError("relay flag")
        if member is not None:
            integer(member[0], 1, rounds - 1, "member tick")
            integer(member[1], 0, 1, "replaced counterpart")
            integer(member[2], 0, 2, "competence swap partner")
            if member[1] == member[2]:
                raise ValueError("swap with another candidate")
        self.relay = relay
        self.absent, self.declines = window(absent, rounds), window(declines, rounds)
        self.member = member
        self.relayed = self.skipped = self.declined_rounds = 0

    def _within(self, plan, index, tick):
        return plan is not None and plan[0] == index and plan[1] <= tick < plan[2]

    def competent_now(self, tick, task):
        who = R.competent(self.regimes, tick, task)
        if self.member and tick >= self.member[0]:
            a, b = self.member[1], self.member[2]
            who = b if who == a else a if who == b else who
        return who

    def _replace_member(self):
        i = self.member[1]
        body = R.counterpart(self.seed * 4 + 7)
        body.env = R.Port(self, 1)
        self.partners = tuple(body if j == i else p for j, p in enumerate(self.partners))
        self.all_agents = (self.focal, *self.partners)
        self.turns[i + 1] = R.PRIVATE_STEPS

    def step(self, *, greedy=False, veto=(False, False, False)):
        if self.failed or self.done or self._active:
            raise RuntimeError("roles session stopped/exhausted/in flight")
        if type(greedy) is not bool or type(veto) is not tuple or len(veto) != 3 \
                or any(type(v) is not bool for v in veto):
            raise ValueError("greedy/veto")
        tick, task = self.tick, self.types[self.tick]
        if self.member and tick == self.member[0]:
            self._replace_member()
        flagged = []
        self._active = True
        try:
            if self.declines and self._within(self.declines, self.declines[0], tick):
                partner = self.partners[self.declines[0]]
                for index in (4, 5, 6):  # its real gate refuses, only inside the window
                    slot = partner.cam.get(partner.observation(R.Port(self, 1, index).cell()))
                    if slot >= 0 and not partner.cam.slot[slot].flags & SLOT_FLAG_INHIBIT:
                        partner.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
                        flagged.append((partner, slot))
            self.memory.claim(tick, self.claimant)
            evidence = self.evidence(task)
            packet = R.row(self.arm, task, self.ledger[0], evidence=evidence)
            self._state = {"tick": tick, "task": task, "veto": veto, "event": None,
                           "partner_action": None, "absent": False}
            self.focal.belief_packet = packet
            if veto[0]:
                self.focal.operator_inhibit = True
            action = self.focal.turn(tick, greedy=greedy)
            self.turns[0] += 1
            event = self._state["event"]
            if event is None or event["assignee"] != action:
                raise RuntimeError("ROLES execution receipt mismatch")
            self._record(tick, task, action, event)
            self.tick += 1
            return {"tick": tick, "type": task, "competent": self.competent_now(tick, task),
                    "row": packet.hex(), "evidence": evidence, "proposal": self.focal.last_proposed_action,
                    "gate": self.focal.last_gate_decision, "partner_action": self._state["partner_action"],
                    "absent": self._state["absent"], **event, "ledger": tuple(self.ledger)}
        except Exception:
            self.failed = True
            self.stop()
            raise
        finally:
            for partner, slot in flagged:
                partner.cam.slot[slot].flags &= ~SLOT_FLAG_INHIBIT
            self._active = False

    def _record(self, tick, task, action, event):
        if self._state["absent"]:
            self.skipped += 1  # nothing arrived: no receipt is invented
            self.memory.last_tick = tick
            return
        receipt = {"tick": tick, "type": task, "assignee": action, "executed": event["executed"],
                   "paid": event["paid"][0], "output": event["output"][0]}
        if self.relay and action == 1 and event["executed"]:
            # The learner did not see it: counterpart 1 relays. Hypothesis only.
            raw = relay_key(tick, RELAYER, event["output"][0] > 0)
            vertex, latency, _ = encode_event(raw)
            slot, _ = allocate(self.focal.cam, raw, vertex, latency, (0,) * 6, has_fact=0,
                               extract="", source=RELAY_SOURCE, key=raw)
            if slot < 0:
                raise RuntimeError("no capacity for a relayed hypothesis")
            self.relayed += 1
            self.memory.last_tick = tick
            return
        self.memory.record(receipt)

    def _commit(self, actor, action):
        state = self._state
        integer(action, 0, 2, "action")
        if not self._active or state is None:
            raise RuntimeError("missing ROLES transaction")
        if actor == 1:
            state["partner_action"] = action
            return (R.ACCEPT_INCENTIVE - R.EXEC_COST) if action == R.ACCEPT else -R.ACCEPT_INCENTIVE
        if state["event"] is not None:
            raise RuntimeError("duplicate ROLES commit")
        if self.focal.last_gate_decision == GATE_BLOCK:
            state["event"] = noop(action)  # veto: nothing happens, no cost
            return 0
        tick, task = state["tick"], state["task"]
        if action != R.SELF and self._within(self.absent, action, tick):
            state["event"] = noop(action)
            state["absent"] = True
            return 0
        accepted = None
        if action != R.SELF and self.ledger[0] >= R.DELEGATE[0]:
            partner = self.partners[action]
            partner.env = R.Port(self, 1, 4 + task)
            if state["veto"][action + 1]:
                slot = partner.cam.get(partner.observation(partner.env.cell()))
                if slot < 0:
                    raise ValueError("counterpart veto requires an observed context")
                partner.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
            decision = partner.turn(R.PRIVATE_OFFSET + R.PRIVATE_STEPS + tick, greedy=True)
            self.turns[action + 1] += 1
            if state["partner_action"] != decision:
                raise RuntimeError("counterpart receipt mismatch")
            accepted = decision == R.ACCEPT
            if self.declines and self._within(self.declines, action, tick):
                self.declined_rounds += 1
            self.private_credit[action + 1] += R.ACCEPT_INCENTIVE if accepted else -R.ACCEPT_INCENTIVE
        event = R.settle(action, accepted, self.competent_now(tick, task) == action, tuple(self.ledger))
        for i in range(3):
            self.ledger[i] -= event["paid"][i]
        state["event"] = event
        return event["net"][0]

    def invariant(self):
        relayed = [s for s in self.focal.cam.slot if s.occupied and s.source == RELAY_SOURCE]
        agents = self.all_agents
        isolated = all(len({id(getattr(a, k)) for a in agents}) == 3 for k in ("cam", "t", "q"))
        return bool(isolated and not self._active and self.memory.invariant()
                    and self.memory.count + self.relayed + self.skipped == self.tick
                    and len(relayed) == self.relayed
                    and all(not s.has_fact and not s.extract for s in relayed)
                    and all(a.metrics.turns == n for a, n in zip(agents, self.turns))
                    and all(a.metrics.false_facts == 0 and a.cam.destroyed == 0
                            and a.metrics.cortex_calls == 0 and not a.cortex_enabled
                            and all(len(s.wsp) == 16 and (not s.has_fact or bool(s.extract))
                                    and (s.source not in (R.ROW_SOURCE, R.CLAIM_SOURCE)
                                         or not s.has_fact and not s.extract)
                                    for s in a.cam.slot if s.occupied)
                            for a in agents)
                    and all(v >= 0 for v in self.ledger))
