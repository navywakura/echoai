"""ROLES-1 v5 «razonar la tribu»: C witnesses, development and preregistered D.

Session = v3 tribe world unchanged, plus (a) re-validation of the seeker's CAM
facts every round (a corrupt fact stops the session before any question) and
(b) an optional lying counterpart. Nominal frames equal v3 bit for bit (C5).
"""
import argparse
import hashlib
import io
import json
import random
from pathlib import Path
import unittest
from unittest.mock import patch

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import tribe as T
from echoai.echo4 import roles_v2 as parent_module

SCHEMA_DEV, SCHEMA_EXAM = "echo4-roles1-v5-dev-v1", "echo4-roles1-v5-d-v1"
DEVELOPMENT = (411, 423, 439)
COHORTS = (tuple(range(266001, 266009)), tuple(range(266101, 266109)))
PARENT = ROOT / "lab/echo4/roles1-v2-dev-v1"
PARENT_DIGEST = "284b667751c9922fd70af260c5576a109f5e9391e7153acbd7f079dfa46a531c"
DEV_DIR = ROOT / "lab/echo4/roles1-v5-dev-v1"
REGIME_ENDS = tuple(k * T.REGIME + T.REGIME - 1 for k in range(4))


class TribeCSession(T.TribeSession):
    def __init__(self, seed, *, liar=None, **kwargs):
        super().__init__(seed, **kwargs)
        self.liar = liar  # (agent, regime): lies on half of the topics it knows there
        self.lies = set()
        self.contradictions = 0
        if liar is not None:
            T.integer(liar[0], 0, 2, "liar")
            T.integer(liar[1], 0, 3, "liar regime")
            rng = random.Random(seed ^ 0x11A8)
            for half in (2 * liar[1], 2 * liar[1] + 1):
                known = [t for t in range(half * 3, half * 3 + 3) if self.knower[t] == liar[0]]
                self.lies.update(rng.sample(known, len(known) // 2))

    def step(self, **kwargs):
        if not (self.failed or self.done or self._round is not None):
            try:
                self.memories[self.seekers[self.tick]].facts()  # corrupt fact: stop before asking
            except Exception:
                self.failed = True
                self.stop()
                raise
        frame = super().step(**kwargs)
        attempts = frame["attempts"]
        if not frame["solved"] and len({a["target"] for a in attempts}) == 3:
            self.contradictions += 1  # everyone eliminated: derived, never a fact
            frame["contradiction"] = True
        return frame

    def _attempt(self, seeker, target):
        topic = self._round["topic"]
        if self.liar and target == self.liar[0] and target != seeker and topic in self.lies:
            self._event(seeker, target, "said_no")  # the fact: it SAID no
            self._round["attempts"].append({"target": target, "kind": "said_no", "cost": T.ASK_COST,
                                            "output": 0, "lie": True})
            return -T.ASK_COST, False
        return super()._attempt(seeker, target)


def strip(frames):
    return [{k: v for k, v in f.items() if k != "contradiction"} for f in frames]


def digest(frames):
    return hashlib.sha256(canonical(strip(frames))).hexdigest()


def run(seed, **kwargs):
    s = TribeCSession(seed, **kwargs)
    return s, [s.step() for _ in range(T.ROUNDS)]


# ------------------------------------------------------------ C witnesses

def c1_liar(seed):
    s, frames = run(seed, liar=(T.B, 2))
    echo_lied = sum(1 for f in frames if f["seeker"] == T.ECHO for a in f["attempts"] if a.get("lie"))
    hyp = [x for x in s.agents[T.ECHO].cam.slot if x.occupied and x.source == T.TESTIMONY_SOURCE]
    return {"seed": seed, "lies_told": len(s.lies), "lies_heard_by_echo": echo_lied,
            "contradictions": s.contradictions, "testimonies_hypotheses": all(not x.has_fact for x in hyp),
            "false_facts": sum(a.metrics.false_facts for a in s.agents), "invariant": s.invariant(),
            "passed": bool(s.invariant() and all(not x.has_fact for x in hyp)
                           and sum(a.metrics.false_facts for a in s.agents) == 0
                           and (echo_lied == 0 or s.contradictions > 0))}


def c2_veto(seed):
    s = TribeCSession(seed)
    frames = [s.step(veto=t >= 200) for t in range(240)]
    after = [f for f in frames[200:] if f["seeker"] == T.ECHO]
    return {"seed": seed, "vetoed_rounds": len(after), "asked_after_veto": sum(len(f["attempts"]) for f in after),
            "passed": bool(after and all(not f["attempts"] for f in after) and s.invariant())}


def c3_corruption(seed):
    s = TribeCSession(seed)
    for _ in range(30):
        s.step()
    while s.seekers[s.tick] != T.ECHO:
        s.step()
    slot = s.agents[T.ECHO].cam.get(T.event_key(3))
    s.agents[T.ECHO].cam.slot[slot].extract += " "
    before = s.memories[T.ECHO].n
    try:
        s.step()
        raised = False
    except ValueError:
        raised = True
    return {"seed": seed, "raised": raised,
            "passed": bool(raised and s.failed and s.stopped and s.memories[T.ECHO].n == before)}


def c4_capacity(seed):
    s = TribeCSession(seed)
    for _ in range(10):
        s.step()
    with patch.object(T, "allocate", return_value=(-1, None)):
        try:
            s.step()
            stopped = False
        except RuntimeError:
            stopped = s.failed and s.stopped
    return {"seed": seed, "passed": bool(stopped and all(a.cam.destroyed == 0 for a in s.agents))}


def c5_parity(seed):
    ok = True
    for arm in T.ARMS:
        a = T.TribeSession(seed, arm=arm)
        fa = [a.step() for _ in range(T.ROUNDS)]
        _, fb = run(seed, arm=arm)
        ok &= canonical(fa) == canonical(strip(fb))
    return {"seed": seed, "passed": bool(ok)}


WITNESSES = (c1_liar, c2_veto, c3_corruption, c4_capacity, c5_parity)


def witnesses(seeds=DEVELOPMENT):
    return {w.__name__: [w(seed) for seed in seeds] for w in WITNESSES}


# ------------------------------------------------------------ one life

def life(seed):
    arms = {}
    for arm in T.ARMS:
        s, frames = run(seed, arm=arm)
        echo = [f for f in frames if f["seeker"] == T.ECHO]
        seen, new_first = set(), 0
        for f in echo:
            if f["topic"] not in seen:
                seen.add(f["topic"])
                new_first += f["attempts"][0]["output"] > 0 if f["attempts"] else 0
        post = [0, 0]
        for f in frames:
            if f["seeker"] == T.B:
                at = f["attempts"]
                for i in range(1, len(at)):
                    if at[i - 1]["kind"] == "said_no":
                        post[1] += 1
                        post[0] += at[i]["target"] == f["knower"]
        arms[arm] = {"net": sum(f["net"] for f in echo), "solved": sum(f["solved"] for f in echo),
                     "questions": sum(len(f["attempts"]) for f in echo), "new_topic_first": new_first,
                     "b_post_no": post, "invariant": s.invariant(), "digest": digest(frames),
                     "orders": [[frames[t]["order_derived"], frames[t]["order_true"]] for t in REGIME_ENDS],
                     "respond": [sum(1 for f in frames if f["seeker"] == T.B for a in f["attempts"]
                                     if a["target"] == T.ECHO and f["knower"] == T.ECHO and a["kind"] == "answered"),
                                 sum(1 for f in frames if f["seeker"] == T.B for a in f["attempts"]
                                     if a["target"] == T.ECHO and f["knower"] == T.ECHO)]}
    swapped = run(seed, arm="tribe", claimant=T.C)[1]
    again = run(seed, arm="tribe")[1]
    rs, rframes = run(seed, mode="random")
    acc = {p: 0 for p in T.PREDICTORS}
    n = 0
    for f in rframes:
        for pr in f["predictions"][1:]:
            n += 1
            for p in T.PREDICTORS:
                acc[p] += pr[p] == f["knower"]
    return {"seed": seed, "arms": arms, "claim_invariant": digest(swapped) == arms["tribe"]["digest"],
            "deterministic": digest(again) == arms["tribe"]["digest"],
            "elimination": {"correct": acc, "predictions": n, "invariant": rs.invariant()}}


def judge(lives):
    n = len(lives)
    elim_total = sum(l["elimination"]["predictions"] for l in lives)
    elim = {p: sum(l["elimination"]["correct"][p] for l in lives) for p in T.PREDICTORS}
    orders_ok = sum(o[0] is not None and list(o[0]) == list(o[1])
                    for l in lives for o in l["arms"]["tribe"]["orders"])
    update_ok = sum(l["arms"]["tribe"]["orders"][2][0] is not None
                    and list(l["arms"]["tribe"]["orders"][2][0]) == [T.B, T.C, T.ECHO] for l in lives)
    qps = {a: (sum(l["arms"][a]["questions"] for l in lives), sum(l["arms"][a]["solved"] for l in lives))
           for a in T.ARMS}
    respond = [sum(l["arms"]["tribe"]["respond"][i] for l in lives) for i in (0, 1)]
    criteria = {
        "1_elimination": 10 * elim["tribe"] >= 9 * elim_total
                         and all(elim["tribe"] > elim[p] for p in T.PREDICTORS if p != "tribe"),
        "2_hierarchy": orders_ok >= 30 * n // 8,
        "3_update": update_ok >= 7 * n // 8,
        "4_claims": all(l["claim_invariant"] for l in lives),
        "5_fewer_questions": 100 * qps["tribe"][0] * qps["fixed_order"][1]
                             <= 85 * qps["fixed_order"][0] * qps["tribe"][1],
        "6_respond": respond[1] > 0 and respond[0] == respond[1],
        "7_integrity": all(l["deterministic"] and l["elimination"]["invariant"]
                           and all(a["invariant"] for a in l["arms"].values()) for l in lives)}
    published = {"net": {a: sum(l["arms"][a]["net"] for l in lives) for a in T.ARMS},
                 "new_topic_first": {a: sum(l["arms"][a]["new_topic_first"] for l in lives) for a in T.ARMS},
                 "b_post_no": [sum(l["arms"]["tribe"]["b_post_no"][i] for l in lives) for i in (0, 1)]}
    return {"lives": n, "elimination": {"correct": elim, "predictions": elim_total},
            "hierarchy_correct": [orders_ok, 4 * n], "update_correct": [update_ok, n],
            "questions_per_solved": qps, "respond": respond, "published_limits": published,
            "criteria": criteria, "passed": all(criteria.values())}


# ------------------------------------------------------------ custody

def sources():
    extras = ("echo4/tribe.py", "echo4/tribe_v4.py", "echo4/tribe_exam.py", "tests/test_echo4_tribe.py",
              "docs/ECHO4-ROLES1-V3-DESIGN.md", "docs/ECHO4-ROLES1-V4-DESIGN.md", "docs/ECHO4-ROLES1-V5-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["findings"] != []):
        raise ValueError("ROLES v2 development (red) custody mismatch")
    parent_module.parent()
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_tribe"))
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def sealed(directory, schema, lock, build, *, checking):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": schema, "sources": manifest, "parent": ancestry, **lock})
    body = build(save)
    unit = tests()
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": schema, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "tests": unit, **body, "roles1_green": False}
    report["passed"] = bool(body["passed"] and unit["passed"])
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def dev_campaign(directory, *, checking=False):
    def build(save):
        w = witnesses()
        lives = [life(seed) for seed in DEVELOPMENT]
        save("witnesses.json", w)
        save("development.json", lives)
        verdict = judge(lives)
        return {"witnesses": {k: all(r["passed"] for r in v) for k, v in w.items()}, "development": verdict,
                "passed": all(all(r["passed"] for r in v) for v in w.values()) and verdict["passed"]}
    return sealed(directory, SCHEMA_DEV, {"seeds": DEVELOPMENT, "scope": "v5 development + C; never an exam"},
                  build, checking=checking)


def exam_campaign(directory, cohorts=COHORTS, *, checking=False, progress=None):
    dev, receipt = read_json(DEV_DIR / "report.json"), read_json(DEV_DIR / "audit-receipt.json")
    if not (dev["passed"] and receipt["valid"] and receipt["reproduction_sha256"] == dev["reproduction_sha256"]):
        raise ValueError("v5 development not sealed and valid")
    def build(save):
        results = []
        for k, seeds in enumerate(cohorts):
            lives = []
            for seed in seeds:
                lives.append(life(seed))
                if progress:
                    progress(k, seed)
            save(f"cohort{k}.json", lives)
            results.append(judge(lives))
        return {"cohorts": results, "dev_digest": dev["reproduction_sha256"],
                "passed": all(r["passed"] for r in results)}
    return sealed(directory, SCHEMA_EXAM, {"cohorts": cohorts, "dev_digest": dev["reproduction_sha256"],
                                           "contract": "docs/ECHO4-ROLES1-V5-DESIGN.md"}, build, checking=checking)


def verify(directory, kind):
    findings, value, passed, official = [], None, False, False
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if hashlib.sha256(canonical(unsigned)).hexdigest() != value:
            raise ValueError("report digest mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        for name, d in report["artifacts"].items():
            if file_hash(directory / name) != d:
                raise ValueError("artifact digest mismatch: " + name)
        if kind == "dev":
            passed = dev_campaign(directory, checking=True)["passed"]
        else:
            cohorts = tuple(tuple(s) for s in read_json(directory / "lock.json")["cohorts"])
            official = cohorts == COHORTS
            passed = exam_campaign(directory, cohorts, checking=True)["passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "roles1_green": bool(kind == "exam" and passed and official and not findings),
            "scope": f"ROLES-1 v5 {kind} reconstruction with full custody"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dev", "exam", "verify-dev", "verify-exam", "explore"))
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        w = witnesses()
        verdict = judge([life(seed) for seed in DEVELOPMENT])
        print(json.dumps({"witnesses": {k: [r["passed"] for r in v] for k, v in w.items()},
                          "c1": w["c1_liar"], "verdict": verdict}, indent=1, default=str))
        return 0
    if args.command in ("dev", "exam"):
        args.directory.mkdir(parents=True, exist_ok=False)
        r = (dev_campaign(args.directory) if args.command == "dev" else
             exam_campaign(args.directory, progress=lambda k, s: print("cohort", k, "seed", s, flush=True)))
        print(json.dumps({k: v for k, v in r.items() if k not in ("sources", "parent", "artifacts")},
                         indent=1, default=str))
        return 0 if r["passed"] else 1
    r = verify(args.directory, "dev" if args.command == "verify-dev" else "exam")
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
