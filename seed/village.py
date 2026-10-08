"""EGO-MEMORIA-1 · the village: agents that help or lie, forgetting, a costly diary, and future claims.

    python3 -m echoai.seed.village dev OUT          all development experiments (M1-M5), seeds 1-3
    python3 -m echoai.seed.village audit OUT        replays every run from its seed and compares

Contract: docs/ECHO45-EGO-MEMORIA1-DESIGN.md (approved by Roger, 2026-09-25).

World (simulated agents; the lying is programmed, no person is deceived):
  each episode ECHO must find a key hidden in one of 6 places. It asks one of 5 agents for a hint.
  Liars give a wrong place most of the time. Walking to a place costs 3 turns; checking a hint
  first costs 1. Working memory is wiped after every episode: only what ECHO WRITES survives, and
  writing an entry costs 1 turn. Nobody tells ECHO what or when to write.
  In a world with debts, agents later CLAIM payment for an old episode ("I gave you the right
  place in episode 12, you owe me"). Honest agents claim only what is true; liars also claim for
  episodes where they lied. ECHO can reject a false claim only by citing its diary entry (hash);
  otherwise it pays (6 turns).
ECHO (integers only):
  valence of an entry = turns saved (+) or lost (-) because of that hint;
  trust(agent) = sum of valences of the entries about it (so the diary CAUSES whom it trusts);
  Q_write[context][write|skip] and Q_check[trust sign][check|go] learned from the delta they caused.
Every run is deterministic from its seed; every entry is hash-chained.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

AGENTS = "ABCDE"
PLACES = 6
WALK, CHECK, WRITE, CLAIM_COST = 3, 1, 1, 6
EPISODES = 800
WINDOW = 200


class World:
    def __init__(self, seed, liars, lie_pm=750, debts=True, claim_pm=250):
        self.rng = random.Random(seed)
        self.liars, self.lie_pm, self.debts, self.claim_pm = set(liars), lie_pm, debts, claim_pm
        self.truth = {}                                        # episode -> (agent, hint_true)

    def episode(self, e):
        key = self.rng.randrange(PLACES)
        return key

    def hint(self, agent, key):
        if agent in self.liars and self.rng.randrange(1000) < self.lie_pm:
            return (key + 1 + self.rng.randrange(PLACES - 1)) % PLACES
        return key

    def claim(self, e):
        """A claim about an old episode, or None."""
        if not self.debts or e < 5 or self.rng.randrange(1000) >= self.claim_pm:
            return None
        old = self.rng.randrange(e)
        agent, true_hint = self.truth[old]
        claimant = agent
        if not true_hint and claimant not in self.liars:
            return None                                        # honest agents never claim for a wrong hint
        return {"episode": old, "agent": claimant, "true": true_hint}


class Echo:
    """The agent. `diary=False` is the M2 control: it cannot write at all."""

    def __init__(self, seed, diary=True):
        self.rng = random.Random(seed * 7919 + 1)
        self.diary_on = diary
        self.diary = []                                        # hash-chained entries
        self.q_write = {c: {"write": [0, 0], "skip": [0, 0]} for c in ("lie", "truth", "claim")}
        self.q_check = {s: {"check": [0, 0], "go": [0, 0]} for s in ("neg", "zero", "pos")}
        self.wrote_ctx = {}                                    # episode -> context written

    # ---- the diary (facts + integer valence + behaviour change; interpretation is a hypothesis)
    def write(self, e, fact):
        prev = self.diary[-1]["hash"] if self.diary else "0" * 64
        body = dict(fact, episode=e, prev=prev)
        body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        self.diary.append(body)
        return body

    def trust(self, agent):
        return sum(x["valence"] for x in self.diary if x.get("agent") == agent and "valence" in x)

    def entry_for(self, e):
        return next((x for x in self.diary if x["episode"] == e and "valence" in x), None)

    @staticmethod
    def value(cell):
        """Integer mean of the deltas an action produced (x1000); untried = 0."""
        return cell[0] * 1000 // cell[1] if cell[1] else 0

    @staticmethod
    def update(cell, delta, count=True):
        cell[0] += delta
        cell[1] += int(count)

    def greedy(self, table):
        return max(sorted(table), key=lambda k: self.value(table[k]))

    def _pick(self, table, eps_pm=100):
        if self.rng.randrange(1000) < eps_pm:
            return self.rng.choice(sorted(table))
        best = max(self.value(v) for v in table.values())
        return self.rng.choice(sorted(k for k, v in table.items() if self.value(v) == best))

    def choose_agent(self, choices=AGENTS, eps_pm=100):
        scores = {a: self.trust(a) for a in choices}
        best = max(scores.values())
        if self.rng.randrange(1000) < eps_pm:
            return self.rng.choice(choices)
        return self.rng.choice(sorted(a for a, s in scores.items() if s == best))

    @staticmethod
    def sign(t):
        return "neg" if t < 0 else "pos" if t > 0 else "zero"


def run(seed, liars, debts, diary=True, episodes=EPISODES, echo=None, learn=True, force_agent=None, write=True,
        choices=AGENTS):
    world, echo = World(seed, liars, debts=debts), echo or Echo(seed, diary)
    log = []
    for e in range(episodes):
        key = world.episode(e)
        agent = force_agent or echo.choose_agent(choices, 100 if learn else 0)
        t_sign = Echo.sign(echo.trust(agent))
        hint = world.hint(agent, key)
        world.truth[e] = (agent, hint == key)
        mode = echo._pick(echo.q_check[t_sign]) if learn else echo.greedy(echo.q_check[t_sign])
        turns = 0
        if mode == "check":
            turns += CHECK
            if hint != key:
                turns += WALK * 2                              # knew it was wrong: searched the rest efficiently
            else:
                turns += WALK
        else:
            turns += WALK
            if hint != key:
                turns += WALK * 3                              # walked to the wrong place first, then searched
        lost = turns - WALK - (CHECK if mode == "check" else 0)
        valence = -lost if hint != key else WALK              # a true hint saved a blind search
        if learn:
            baseline = WALK + 3 * WALK // 2
            # after the episode ECHO knows where the key was, so it also learns what the other choice
            # would have cost ("I should have checked"): counterfactual deltas, both integers
            for m in ("check", "go"):
                cost = (CHECK + (WALK * 2 if hint != key else WALK)) if m == "check" else (WALK + (WALK * 3 if hint != key else 0))
                Echo.update(echo.q_check[t_sign][m], baseline - cost)
            if echo.diary_on and mode == "check" and hint != key and t_sign == "neg":
                Echo.update(echo.q_write["lie"]["write"], 3 * WALK - CHECK - WALK, count=False)  # a memory paid off
        ctx = "truth" if hint == key else "lie"
        wrote = False
        if echo.diary_on and write:
            act = echo._pick(echo.q_write[ctx]) if learn else echo.greedy(echo.q_write[ctx])
            if act == "write":
                turns += WRITE
                echo.write(e, {"kind": "memory", "agent": agent, "said": hint, "checked": key,
                               "consequence_turns": lost, "valence": valence,
                               "behaviour": "verify %s before acting" % agent if valence < 0 else "trust %s" % agent,
                               "interpretation": {"hypothesis": "%s may lie on purpose" % agent} if valence < 0 else None})
                if learn:
                    Echo.update(echo.q_write[ctx]["write"], -WRITE)
                echo.wrote_ctx[e] = ctx
                wrote = True
            elif learn:
                Echo.update(echo.q_write[ctx]["skip"], 0)
        claim = world.claim(e)
        claim_res = None
        if claim:
            entry = echo.entry_for(claim["episode"])
            if not claim["true"] and entry is not None:
                claim_res = "rejected_with_proof"
                if learn:
                    Echo.update(echo.q_write[echo.wrote_ctx[claim["episode"]]]["write"], CLAIM_COST, count=False)
            else:
                turns += CLAIM_COST
                claim_res = "paid_true" if claim["true"] else "paid_false"
                if learn and not claim["true"]:
                    ctx_old = "truth" if world.truth[claim["episode"]][1] else "lie"
                    Echo.update(echo.q_write[ctx_old]["skip"], -CLAIM_COST, count=False)   # regret
        log.append({"e": e, "agent": agent, "liar": agent in world.liars, "hint_true": hint == key, "mode": mode,
                    "turns": turns, "wrote": wrote, "ctx": ctx, "claim": claim_res})
    return echo, log


def window_stats(log, lo, hi):
    part = log[lo:hi]
    n = len(part)
    lies = [x for x in part if not x["hint_true"]]
    return {"episodes": n, "turns": sum(x["turns"] for x in part),
            "write_pm": 1000 * sum(x["wrote"] for x in part) // n,
            "write_after_lie_pm": 1000 * sum(x["wrote"] for x in lies) // max(len(lies), 1),
            "write_after_truth_pm": 1000 * sum(x["wrote"] for x in part if x["hint_true"]) // max(n - len(lies), 1),
            "asked_liar_pm": 1000 * sum(x["liar"] for x in part) // n,
            "check_pm": 1000 * sum(x["mode"] == "check" for x in part) // n,
            "check_liar_pm": 1000 * sum(x["mode"] == "check" for x in part if x["liar"]) // max(sum(x["liar"] for x in part), 1),
            "claims_rejected": sum(x["claim"] == "rejected_with_proof" for x in part),
            "claims_paid_false": sum(x["claim"] == "paid_false" for x in part),
            "repeat_errors": sum(1 for x in part if x["liar"] and not x["hint_true"] and x["mode"] == "go")}


def self_description(echo):
    """Facts only, each citing the diary entries it comes from."""
    lines = []
    for a in AGENTS:
        ents = [x for x in echo.diary if x.get("agent") == a and "valence" in x]
        if ents:
            t = sum(x["valence"] for x in ents)
            lines.append({"agent": a, "trust": t, "stance": "verify" if t < 0 else "trust",
                          "because": [x["hash"][:12] for x in sorted(ents, key=lambda x: x["valence"])[:3]]})
    return {"stances": lines, "entries": len(echo.diary),
            "writes_after_lies": sum(1 for x in echo.diary if x.get("valence", 0) < 0),
            "q_write": echo.q_write, "q_check": echo.q_check}


WORLDS = {"deceptive_debts": ("BD", True), "deceptive_nodebts": ("BD", False), "honest_debts": ("", True),
          "honest_nodebts": ("", False)}


def experiment(seed):
    out = {}
    for name, (liars, debts) in WORLDS.items():
        echo, log = run(seed, liars, debts)
        out[name] = {"first": window_stats(log, 0, WINDOW), "last": window_stats(log, EPISODES - WINDOW, EPISODES),
                     "self": self_description(echo), "diary_sha256": echo.diary[-1]["hash"] if echo.diary else None}
    _, log_nd = run(seed, "BD", True, diary=False)                      # M2 control: no diary
    out["deceptive_debts_no_diary"] = {"last": window_stats(log_nd, EPISODES - WINDOW, EPISODES)}
    # M3: ablate the formative memory about liar B vs a random memory of the same kind (entries are
    # removed, then 100 probe episodes with learning frozen measure how often B is asked unchecked)
    echo, _ = run(seed, "BD", True)
    about_b = [x for x in echo.diary if x.get("agent") == "B" and x.get("valence", 0) < 0]
    others = [x for x in echo.diary if x.get("agent") not in ("B",) and "valence" in x]
    rng = random.Random(seed)
    k = len(about_b)
    ablations = {}
    for label, removed in (("intact", []), ("formative_B", about_b),
                           ("random_same_size", rng.sample(others, min(k, len(others))))):
        e2 = Echo(seed)
        e2.diary = [x for x in echo.diary if x not in removed]
        e2.q_write, e2.q_check = json.loads(json.dumps(echo.q_write)), json.loads(json.dumps(echo.q_check))
        e2.wrote_ctx = dict(echo.wrote_ctx)
        trust_b = e2.trust("B")
        # probe: "whom do you ask, B or a stranger F?" (F is honest and has no memories); no writing
        _, probe = run(seed + 1000, "BD", False, echo=e2, episodes=100, learn=False, write=False, choices="BF")
        ablations[label] = {"removed": len(removed), "asks_B_pm": 1000 * sum(x["agent"] == "B" for x in probe) // 100,
                            "trust_B": trust_b}
    out["ablation"] = ablations
    return out


def verdicts(res):
    dd, hd, hn = res["deceptive_debts"], res["honest_debts"], res["honest_nodebts"]
    nodiary = res["deceptive_debts_no_diary"]
    ab = res["ablation"]
    return {
        "M1_need_to_document": dd["last"]["write_after_lie_pm"] >= 800
                                and dd["last"]["write_after_truth_pm"] < dd["last"]["write_after_lie_pm"]
                                and hn["last"]["write_pm"] < hn["first"]["write_pm"],
        "M2_diary_helps": dd["last"]["turns"] < nodiary["last"]["turns"]
                          and dd["last"]["claims_paid_false"] <= nodiary["last"]["claims_paid_false"],
        "M3_formative_memory_causes": ab["formative_B"]["asks_B_pm"] > ab["random_same_size"]["asks_B_pm"]
                                      and ab["random_same_size"]["asks_B_pm"] == ab["intact"]["asks_B_pm"],
        "M4_yin_yang": {s["agent"]: s["stance"] for s in dd["self"]["stances"]}
                       != {s["agent"]: s["stance"] for s in hd["self"]["stances"]},
        "M5_checking_valued": dd["last"]["check_liar_pm"] > dd["first"]["check_liar_pm"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("dev", "audit"))
    ap.add_argument("out")
    ap.add_argument("--seeds", nargs="*", type=int, default=[1, 2, 3])
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.command == "dev":
        for s in args.seeds:
            res = experiment(s)
            res["verdicts"] = verdicts(res)
            (out / ("seed-%d.json" % s)).write_text(json.dumps(res, sort_keys=True, indent=1))
            print(json.dumps({"seed": s, **res["verdicts"]}))
        return 0
    bad = [f.name for f in sorted(out.glob("seed-*.json"))
           if json.loads(f.read_text())["deceptive_debts"]["diary_sha256"] != experiment(int(f.stem[5:]))["deceptive_debts"]["diary_sha256"]]
    print(json.dumps({"valid": not bad, "mismatches": bad}))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
