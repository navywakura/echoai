"""ROLES-1 v4: the deduction proposes an ordered candidate list; Q decides.

Action 0 = follow the proposal, 1 = next candidate, 2 = last. Q may learn not
to trust it; no written rule forces it. World/memory are those of tribe.py.
"""
from echoai.core.dag import allocate
from echoai.core.wsp import pack
from echoai.nexus0.constants import GATE_BLOCK, SLOT_FLAG_INHIBIT
from echoai.echo4 import tribe as T

ROW_STYLE_V4 = 13


def proposal(rows, tick, topic, arm, seeker, claimants):
    """Ordered candidates and where the first one came from (0 none, 1 known, 2 rank)."""
    if arm == "fixed_order":
        return (*T.others(seeker), seeker), 0, 0
    base = "tribe" if arm == "tribe" else arm
    suggested, elim = T.suggestion(rows, tick, topic, base, claimants)
    known = T.last_knower(rows, topic)
    source = 0 if suggested is None else (1 if suggested == known else 2)
    counts = T.rank_counts(rows, tick)
    def order_key(a):
        rel = T.relative(seeker, a)
        if arm in ("tribe", "no_elimination"):
            return (-counts[a], rel)
        if arm == "claimed_rank":
            return (0 if a in claimants else 1, rel)
        return (rel,)
    rest = sorted((a for a in range(3) if a != suggested and a not in elim), key=order_key)
    dropped = sorted(elim, key=lambda a: T.relative(seeker, a))
    ordered = ([suggested] if suggested is not None else []) + rest + dropped
    return tuple(ordered), source, len(elim)


def row_v4(seeker, source, n_elim):
    return pack(src=2, rel=29, dst=3, domain=9, generator=8, style=ROW_STYLE_V4, slot=seeker,
                seq=4 * n_elim + source)


class TribeV4Agent(T.TribeAgent):
    def _slot_for(self, wsp, vertex, extract, e6, source="nexus0-env"):
        if wsp[10:14] != bytes((0, 9, 8, ROW_STYLE_V4)):
            return super()._slot_for(wsp, vertex, extract, e6, source)
        slot = self.cam.get(wsp)
        if slot < 0:
            slot, _ = allocate(self.cam, wsp, vertex, 0, e6, has_fact=0, extract="", source=T.ROW_SOURCE, key=wsp)
        if slot < 0:
            raise RuntimeError("no capacity for a non-factual tribe row")
        if self.operator_inhibit:
            self.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        return slot


class TribeV4Session(T.TribeSession):
    def __init__(self, seed, *, arm="tribe", mode="free", claimant=T.B):
        super().__init__(seed, arm=arm, mode=mode, claimant=claimant)
        self.agents = tuple(TribeV4Agent(T.Port(self, i), arm if i == T.ECHO else "tribe", i) for i in range(3))
        self.memories = tuple(T.TribeMemory(a.cam, i) for i, a in enumerate(self.agents))

    def _row_for(self, seeker):
        arm = self.arm if seeker == T.ECHO else "tribe"
        ordered, source, n_elim = proposal(self.memories[seeker].rows, self.tick, self._round["topic"], arm,
                                           seeker, frozenset(self.memories[seeker].claimants()))
        self._round["ordered"] = ordered
        return row_v4(seeker, source, n_elim), ordered[0], None

    def _commit(self, actor, action):
        state = self._round
        if state is None or actor != state["seeker"]:
            raise RuntimeError("missing tribe transaction")
        agent = self.agents[actor]
        if agent.last_gate_decision == GATE_BLOCK:
            state["resolved"] = True
            state["vetoed"] = True
            return 0, False
        T.integer(action, 0, 2, "v4 action")
        target = state["ordered"][action]
        reward, knows = self._attempt(actor, target)
        agent.attempt += 1
        state["resolved"] = knows
        more = not knows and agent.attempt < T.ATTEMPTS
        if more:
            packet, suggested, _ = self._row_for(actor)
            state["suggestions"].append(suggested)
            agent.belief_packet = packet
        return reward, more
