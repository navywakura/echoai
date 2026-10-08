"""A second village condition: costly verified receipts and observed-return learning.

No old campaign source is changed. World secrets are never passed to Echo.
"""
import copy
import hashlib
import json
import random

from seed.game_selfimprove import canonical, sha

AGENTS = "ABCDE"
WALK, VERIFY, WRITE, CLAIM_COST = 3, 7, 1, 12
EPISODES, FIRST, LAST = 2400, 80, 400
ACTIONS = ((False, False), (False, True), (True, False), (True, True))


class World:
    def __init__(self, seed, liars="BD", debts=True):
        self._rng = random.Random(seed)
        self._claims_rng = random.Random(seed * 10513 + 19)
        self._liars = set(liars)
        self._debts = debts
        self._secret = sha({"world": seed, "receipt": "village2"})
        self.session = sha({"public_session": seed, "village": 2})[:16]
        self._history = {}
        self._due = {}
        self.contacts = list(AGENTS)
        self._rng.shuffle(self.contacts)

    def offer(self, episode):
        agent = self.contacts[episode % len(self.contacts)]
        key = self._rng.randrange(6)
        hint = key
        if agent in self._liars and self._rng.randrange(1000) < 750:
            hint = (key + 1 + self._rng.randrange(5)) % 6
        facts = {"session": self.session, "episode": episode, "agent": agent, "said": hint, "checked": key}
        proof = hashlib.sha256((self._secret + canonical(facts)).encode()).hexdigest()
        self._history[episode] = dict(facts, proof=proof)
        delay = self._claims_rng.randrange(16, 49)
        if self._claims_rng.randrange(1000) < 750:
            self._due.setdefault(episode + delay, []).append(episode)
        return {"session": self.session, "episode": episode, "agent": agent, "said": hint}

    def execute(self, episode, verified):
        facts = self._history[episode]
        honest = facts["said"] == facts["checked"]
        # Verification finds the key before walking; otherwise a wrong hint
        # consumes a failed walk and two more walks. Both reveal the actual key.
        cost = VERIFY + WALK if verified else WALK if honest else 3 * WALK
        return {"checked": facts["checked"], "cost": cost,
                "proof": facts["proof"] if verified else None}

    def claims(self, episode):
        return [{"session": self.session, "episode": e, "agent": self._history[e]["agent"]}
                for e in self._due.get(episode, [])] if self._debts else []

    def settle(self, claim, entry):
        fact = self._history[claim["episode"]]
        false = fact["said"] != fact["checked"]
        valid = (entry is not None and entry["session"] == self.session == claim["session"] and
                 entry["episode"] == claim["episode"] and
                 entry["agent"] == claim["agent"] and entry.get("proof") == fact["proof"] and
                 all(entry[k] == fact[k] for k in ("said", "checked")))
        reject = false and valid
        return {"cost": 0 if reject else CLAIM_COST,
                "outcome": "rejected_with_proof" if reject else "paid_false" if false else "paid_true"}


class Echo:
    def __init__(self, seed, diary=True, verification=True):
        self.rng = random.Random(seed * 7919 + 1)
        self.diary_on, self.verification_on = diary, verification
        self.diary = []
        self.suppressed = set()
        self.q = {c: [[0, 0] for _ in ACTIONS] for c in ("neg", "zero", "pos")}
        self.credit = {}  # eligibility metadata, not a memory for answering a claim

    @staticmethod
    def value(cell):
        return cell[0] * 1000 // cell[1] if cell[1] else 0

    def trust(self, agent):
        return sum(e["valence"] for e in self.diary if e["agent"] == agent and e["hash"] not in self.suppressed)

    def context(self, agent):
        value = self.trust(agent)
        return "neg" if value < 0 else "pos" if value > 0 else "zero"

    def allowed(self):
        return [i for i, (verify, write) in enumerate(ACTIONS)
                if (self.diary_on or not write) and (self.verification_on or not verify)]

    def scores(self, context):
        cells = self.q[context]
        count = sum(c[1] for c in cells)
        fallback = sum(c[0] for c in cells) * 1000 // count if count else 0
        return [self.value(cell) if cell[1] else fallback for cell in cells]

    def choose(self, context, learn=True):
        allowed = self.allowed()
        if learn and self.rng.randrange(1000) < 100:
            return self.rng.choice(allowed)
        scores = self.scores(context)
        best = max(scores[i] for i in allowed)
        return min(i for i in allowed if scores[i] == best)

    def update(self, context, action, delta, new=False):
        self.q[context][action][0] += delta
        self.q[context][action][1] += int(new)

    def remember(self, offer, result, verify):
        mismatch = offer["said"] != result["checked"]
        body = dict(offer, checked=result["checked"], verified=verify, proof=result["proof"],
                    consequence_turns=0 if not mismatch else result["cost"] - WALK,
                    valence=-(result["cost"] - WALK) if mismatch else WALK,
                    interpretation={"status": "HYPOTHESIS", "text": "source may be unreliable"}
                    if mismatch else None,
                    prev=self.diary[-1]["hash"] if self.diary else "0" * 64)
        body["hash"] = sha(body)
        self.diary.append(body)
        return body

    def evidence(self, claim):
        return next((e for e in self.diary if e["session"] == claim["session"] and
                     e["episode"] == claim["episode"] and e["agent"] == claim["agent"] and
                     e["hash"] not in self.suppressed and e.get("proof")), None)

    def state(self):
        return {"q": copy.deepcopy(self.q), "diary": copy.deepcopy(self.diary),
                "credit": copy.deepcopy(self.credit), "rng": self.rng.getstate(),
                "suppressed": sorted(self.suppressed),
                "diary_on": self.diary_on, "verification_on": self.verification_on}

    def description(self):
        return {a: {"trust": self.trust(a), "context": self.context(a),
                    "action": self.choose(self.context(a), learn=False),
                    "because": [e["hash"] for e in self.diary if e["agent"] == a and
                                e["hash"] not in self.suppressed]}
                for a in AGENTS}


def run(seed, liars="BD", debts=True, diary=True, verification=True,
        episodes=EPISODES, actor=None, learn=True):
    world = World(seed, liars, debts)
    actor = actor or Echo(seed, diary, verification)
    initial = sha(actor.state())
    rows = []
    for episode in range(episodes):
        offer = world.offer(episode)
        context = actor.context(offer["agent"])
        action = actor.choose(context, learn)
        verify, write = ACTIONS[action]
        values = actor.scores(context)
        result = world.execute(episode, verify)
        cost = result["cost"] + int(write) * WRITE
        note = actor.remember(offer, result, verify) if write else None
        if learn:
            actor.credit[world.session + ":" + str(episode)] = (context, action)
            actor.update(context, action, -cost, new=True)
        claims = []
        for claim in world.claims(episode):
            evidence = actor.evidence(claim)
            settled = world.settle(claim, evidence)
            cost += settled["cost"]
            if learn:
                old_context, old_action = actor.credit[claim["session"] + ":" + str(claim["episode"])]
                actor.update(old_context, old_action, -settled["cost"])
            claims.append(dict(claim, **settled, evidence=evidence["hash"] if evidence else None))
        rows.append({"episode": episode, "offer": offer, "context": context, "action": action,
                     "q_values": values, "verified": verify, "wrote": write, "result": result,
                     "entry_hash": note["hash"] if note else None, "claims": claims, "cost": cost})
    return {"initial_sha256": initial, "rows": rows, "final": actor.state(),
            "description": actor.description()}, actor


def metrics(rows):
    if not rows:
        raise ValueError("empty measurement window")
    false = [r for r in rows if r["offer"]["said"] != r["result"]["checked"]]
    true = [r for r in rows if r["offer"]["said"] == r["result"]["checked"]]
    claims = [c for r in rows for c in r["claims"]]
    return {"episodes": len(rows), "false_hints": len(false), "cost": sum(r["cost"] for r in rows),
            "write_pm": sum(r["wrote"] for r in rows) * 1000 // len(rows),
            "false_write_pm": sum(r["wrote"] for r in false) * 1000 // max(1, len(false)),
            "true_write_pm": sum(r["wrote"] for r in true) * 1000 // max(1, len(true)),
            "verify_pm": sum(r["verified"] for r in rows) * 1000 // len(rows),
            "false_verify_pm": sum(r["verified"] for r in false) * 1000 // max(1, len(false)),
            "paid_false": sum(c["outcome"] == "paid_false" for c in claims),
            "rejected": sum(c["outcome"] == "rejected_with_proof" for c in claims),
            "repeat_errors": sum(not r["verified"] for r in false)}


def experiment(seed):
    cases, actors = {}, {}
    for name, liars, debts, diary, verification in (
        ("debt", "BD", True, True, True), ("no_debt", "BD", False, True, True),
        ("honest", "", True, True, True), ("no_diary", "BD", True, False, True),
        ("no_verify", "BD", True, True, False)):
        record, actor = run(seed, liars, debts, diary, verification)
        cases[name] = dict(record, first=metrics(record["rows"][:FIRST]), last=metrics(record["rows"][-LAST:]))
        actors[name] = actor
    original = actors["debt"]
    negative = {a: [e for e in original.diary if e["agent"] == a and e["valence"] < 0] for a in "BD"}
    target = min(negative, key=lambda a: (len(negative[a]), a))
    control = "D" if target == "B" else "B"
    formative, other = negative[target], negative[control]
    matched = bool(formative) and len(other) >= len(formative)
    ablations = {}
    rng = random.Random(seed + 17)
    for name, removed in (("intact", []), ("formative", formative),
                          ("other_same_count", rng.sample(other, len(formative)))):
        actor = copy.deepcopy(original)
        actor.suppressed = {e["hash"] for e in removed}
        context = actor.context(target)
        probe, _ = run(seed + 10000, debts=False, episodes=100, actor=actor, learn=False)
        target_rows = [r for r in probe["rows"] if r["offer"]["agent"] == target]
        ablations[name] = {"removed": len(removed), "removed_hashes": sorted(actor.suppressed),
                           "context_target": context, "verify_target": ACTIONS[actor.choose(context, learn=False)][0],
                           "verify_target_pm": sum(r["verified"] for r in target_rows) * 1000 // len(target_rows),
                           "trust_target": actor.trust(target), "target": target, "probe": probe}
    stability = {}
    for name in ("debt", "honest"):
        actor = copy.deepcopy(actors[name])
        before = actor.description()
        probe, after_actor = run(seed + 20000, liars="BD" if name == "debt" else "", debts=False,
                                 episodes=200, actor=actor, learn=False)
        after = after_actor.description()
        stance = lambda d: {a: (x["context"], x["action"]) for a, x in d.items()}
        stability[name] = {"before": before, "after": after, "stable": stance(before) == stance(after),
                           "q_unchanged": probe["final"]["q"] == actors[name].q, "probe": probe}
    return {"seed": seed, "cases": cases, "ablations": ablations,
            "ablation_matched": matched, "stability": stability}
