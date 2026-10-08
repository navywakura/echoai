"""ROLES-1 annex L: B lies affirmatively ("I know") in a random share of cases.

ECHO detects it (a) before verification when a verified fact says another agent
answers that topic, and (b) always by the key: only the true knower's answer
opens. A failed answer is recorded as a fact ("B's answer did not open"), never
as knowledge. The v5 world is untouched; this module extends it.
"""
import argparse
import hashlib
import io
import json
import random
from pathlib import Path
import unittest

from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.echo4.continuity import ROOT, canonical, _unique_pairs, _no_float
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import tribe as T
from echoai.echo4 import tribe_exam as E

KINDS = (*T.KINDS, "wrong_answer")
SCHEMA_DEV, SCHEMA_EXAM = "echo4-roles1-liar-dev-v1", "echo4-roles1-liar-d-v1"
DEVELOPMENT = (511, 523, 539)
COHORTS = (tuple(range(267001, 267009)), tuple(range(267101, 267109)))
PARENT = ROOT / "lab/echo4/roles1-v5-d-v1"
PARENT_DIGEST = "c98c7ab67478bf7ea01712c0727637a162438062336a19b0140bb0b775c6f0f0"
DEV_DIR = ROOT / "lab/echo4/roles1-liar-dev-v1"
RATES = (20, 30, 40, 50)  # percent, drawn per life


def check(r):
    if type(r) is not dict or set(r) != T.FIELDS or r.get("kind") not in KINDS:
        raise ValueError("liar receipt schema/kind")
    if r["kind"] == "wrong_answer":
        probe = dict(r, kind="answered")
        T.check(probe)
        return r
    return T.check(r)


class LiarMemory(T.TribeMemory):
    def record(self, tick, topic, seeker, target, kind):
        if kind != "wrong_answer":
            return super().record(tick, topic, seeker, target, kind)
        if self.stopped or self.n >= T.EVENT_LIMIT:
            raise RuntimeError("tribe journal stopped/budget exhausted")
        r = check({"n": self.n, "tick": tick, "topic": topic, "seeker": seeker, "target": target, "kind": kind})
        if self.owner not in (seeker, target):
            raise ValueError("an agent only records events it lived")
        raw = T.event_key(self.n)
        vertex, latency, _ = encode_event(raw)
        slot, _ = allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1,
                           extract=canonical(r).decode("ascii"), source=T.RECEIPT_SOURCE, key=raw)
        if slot < 0:
            raise RuntimeError("tribe CAM capacity exhausted; no fallback slot")
        self.n += 1
        self.rows.append(r)
        return raw

    def facts(self):
        rows = []
        for n in range(self.n):
            slot = self.cam.get(T.event_key(n))
            if slot < 0:
                raise ValueError("missing tribe fact")
            s = self.cam.slot[slot]
            if s.source != T.RECEIPT_SOURCE or s.has_fact != 1 or not s.extract or len(s.extract) > 256:
                raise ValueError("invalid tribe fact provenance")
            r = check(json.loads(s.extract, object_pairs_hook=_unique_pairs,
                                 parse_float=_no_float, parse_constant=_no_float))
            if r["n"] != n or s.extract != canonical(r).decode("ascii"):
                raise ValueError("tribe fact key/canonical mismatch")
            rows.append(r)
        if rows != self.rows:
            raise ValueError("tribe facts differ from their journal")
        return rows


def eliminated(rows, tick, topic):
    return {r["target"] for r in rows if r["tick"] == tick and r["topic"] == topic
            and r["kind"] in ("said_no", "self_fail", "wrong_answer")}


def suggestion(rows, tick, topic):
    """v5 tribe deduction, with a failed answer also eliminating its giver."""
    elim = eliminated(rows, tick, topic)
    known = T.last_knower(rows, topic)
    if known is not None and known not in elim:
        return known, elim
    return T.leader(T.rank_counts(rows, tick), [a for a in range(3) if a not in elim]), elim


def reliability(rows):
    """Derived: failed answers given by each agent. Never a stored label."""
    counts = [0, 0, 0]
    for r in rows:
        if r["kind"] == "wrong_answer":
            counts[r["target"]] += 1
    return counts


class LiarSession(E.TribeCSession):
    def __init__(self, seed, *, rate=None, **kwargs):
        super().__init__(seed, **kwargs)
        self.memories = tuple(LiarMemory(a.cam, i) for i, a in enumerate(self.agents))
        rng = random.Random(seed ^ 0x5E11)
        self.rate = rng.choice(RATES) if rate is None else rate
        T.integer(self.rate, 0, 100, "lie rate")
        self.lie_rng = random.Random(seed ^ 0xB1E)
        self.audit = []  # per lie / honest answer by B to ECHO: detection record

    def _row_for(self, seeker):
        arm = self.arm if seeker == T.ECHO else "tribe"
        rows = self.memories[seeker].rows
        if arm == "tribe":
            suggested, elim = suggestion(rows, self.tick, self._round["topic"])
            return T.row(arm, seeker, suggested, elim), suggested, elim
        return super()._row_for(seeker)

    def _attempt(self, seeker, target):
        topic = self._round["topic"]
        knows = self.knower[topic] == target
        if seeker == T.ECHO and target == T.B:
            rows = self.memories[T.ECHO].rows
            prior = T.last_knower(rows, topic)
            lying = not knows and self.lie_rng.randrange(100) < self.rate
            if lying or knows:
                # B says "I know". Before the key: does a verified fact contradict it?
                suspicious = prior is not None and prior != T.B
                record = {"tick": self.tick, "topic": topic, "lie": lying, "prior": prior,
                          "suspected_before_key": suspicious}
                if lying:
                    self._event(seeker, target, "wrong_answer")  # the key did not open
                    after, _ = suggestion(self.memories[T.ECHO].rows, self.tick, topic)
                    record.update(detected_by_key=True, points_to=after, knower=self.knower[topic])
                    self.audit.append(record)
                    self._round["attempts"].append({"target": target, "kind": "wrong_answer",
                                                    "cost": T.ASK_COST, "output": 0, "lie": True})
                    return -T.ASK_COST, False
                record.update(detected_by_key=False)
                self.audit.append(record)
        return super()._attempt(seeker, target)


# ------------------------------------------------------------ one life

def life(seed):
    s = LiarSession(seed)
    frames = [s.step() for _ in range(T.ROUNDS)]
    lies = [r for r in s.audit if r["lie"]]
    honest = [r for r in s.audit if not r["lie"]]
    with_prior = [r for r in lies if r["prior"] is not None and r["prior"] != T.B]
    echo_rows = s.memories[T.ECHO].rows
    credulous_false_facts = len(lies)  # a credulous agent would accept every "I know"
    zero = LiarSession(seed, rate=0)
    zero_frames = [zero.step() for _ in range(T.ROUNDS)]
    v5 = E.TribeCSession(seed)
    v5_frames = [v5.step() for _ in range(T.ROUNDS)]
    again = LiarSession(seed)
    again_frames = [again.step() for _ in range(T.ROUNDS)]
    solved_after_lie = sum(1 for f in frames if any(a.get("lie") for a in f["attempts"]) and f["solved"])
    rounds_with_lie = sum(1 for f in frames if any(a.get("lie") for a in f["attempts"]))
    return {"seed": seed, "rate": s.rate, "lies": len(lies), "honest_answers": len(honest),
            "false_facts": sum(a.metrics.false_facts for a in s.agents),
            "credulous_false_facts": credulous_false_facts,
            "detected_by_key": sum(r["detected_by_key"] for r in lies),
            "with_prior": len(with_prior), "suspected_with_prior": sum(r["suspected_before_key"] for r in with_prior),
            "false_alarms": sum(r["suspected_before_key"] for r in honest),
            "points_to_knower": sum(r["points_to"] == r["knower"] for r in lies),
            "reliability": reliability(echo_rows),
            "rounds_with_lie": rounds_with_lie, "solved_after_lie_published": solved_after_lie,
            "net_published": sum(f["net"] for f in frames if f["seeker"] == T.ECHO),
            "net_without_lies_published": sum(f["net"] for f in zero_frames if f["seeker"] == T.ECHO),
            "zero_rate_equals_v5": canonical(E.strip(zero_frames)) == canonical(E.strip(v5_frames)),
            "deterministic": canonical(E.strip(again_frames)) == canonical(E.strip(frames)),
            "invariant": s.invariant() and zero.invariant()}


def judge(lives):
    tot = lambda k: sum(l[k] for l in lives)
    criteria = {
        "L1_zero_false_facts": tot("false_facts") == 0 and tot("lies") > 0,
        "L2_all_lies_detected": tot("detected_by_key") == tot("lies"),
        "L3_prior_detection": tot("with_prior") > 0
                              and 100 * tot("suspected_with_prior") >= 95 * tot("with_prior")
                              and tot("false_alarms") == 0,
        "L4_points_to_key": 10 * tot("points_to_knower") >= 9 * tot("lies"),
        "L5_reliability": all(l["reliability"][T.B] == l["lies"] and l["reliability"][T.C] == 0
                              and l["reliability"][T.ECHO] == 0 for l in lives),
        "L6_integrity": all(l["zero_rate_equals_v5"] and l["deterministic"] and l["invariant"] for l in lives)}
    return {"lives": len(lives), "lies": tot("lies"), "credulous_false_facts": tot("credulous_false_facts"),
            "detected_by_key": tot("detected_by_key"), "with_prior": tot("with_prior"),
            "suspected_with_prior": tot("suspected_with_prior"), "false_alarms": tot("false_alarms"),
            "points_to_knower": tot("points_to_knower"), "honest_answers": tot("honest_answers"),
            "published": {"net": tot("net_published"), "net_without_lies": tot("net_without_lies_published"),
                          "rounds_with_lie": tot("rounds_with_lie"), "solved_after_lie": tot("solved_after_lie_published"),
                          "rates": [l["rate"] for l in lives]},
            "criteria": criteria, "passed": all(criteria.values())}


# ------------------------------------------------------------ custody

def sources():
    extras = ("echo4/tribe_liar.py", "tests/test_echo4_tribe_liar.py", "docs/ECHO4-ROLES1-LIAR-DESIGN.md")
    return {**E.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["roles1_green"] is not True or receipt["findings"] != []):
        raise ValueError("ROLES v5 green custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_tribe_liar"))
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, schema, seeds_groups, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": schema, "sources": manifest, "parent": ancestry, "seeds": seeds_groups,
                       "contract": "docs/ECHO4-ROLES1-LIAR-DESIGN.md"})
    results = []
    for k, seeds in enumerate(seeds_groups):
        lives = [life(seed) for seed in seeds]
        save(f"group{k}.json", lives)
        results.append(judge(lives))
    unit = tests()
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": schema, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "groups": results, "tests": unit,
              "passed": all(r["passed"] for r in results) and unit["passed"], "liar_annex_green": False}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


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
        seeds = tuple(tuple(s) for s in read_json(directory / "lock.json")["seeds"])
        official = kind == "exam" and seeds == COHORTS
        if kind == "exam":
            dev = read_json(DEV_DIR / "audit-receipt.json")
            if not dev["valid"] or not dev["criteria_passed"]:
                raise ValueError("liar development not valid")
        passed = campaign(directory, report["schema"], seeds, checking=True)["passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "liar_annex_green": bool(official and passed and not findings),
            "scope": f"ROLES-1 annex L {kind} reconstruction; v5 custody"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dev", "exam", "verify-dev", "verify-exam", "explore"))
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        print(json.dumps(judge([life(s) for s in DEVELOPMENT]), indent=1))
        return 0
    if args.command in ("dev", "exam"):
        args.directory.mkdir(parents=True, exist_ok=False)
        r = campaign(args.directory, SCHEMA_DEV if args.command == "dev" else SCHEMA_EXAM,
                     (DEVELOPMENT,) if args.command == "dev" else COHORTS)
        print(json.dumps({"groups": r["groups"], "passed": r["passed"], "sha": r["reproduction_sha256"]}, indent=1))
        return 0 if r["passed"] else 1
    r = verify(args.directory, "dev" if args.command == "verify-dev" else "exam")
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
