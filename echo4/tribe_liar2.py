"""ROLES-1 annex L v2: metaknowledge, "and what if I have it?".

ECHO gets a private, noisy (90 % both ways) feeling-of-knowing signal per
topic. It is a hypothesis, never a fact; only a self_ok receipt makes it one.
Deduction order: verified knower > own signal (if still a candidate) > rank.
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
from echoai.core.wsp import pack
from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import tribe as T
from echoai.echo4 import tribe_exam as E
from echoai.echo4 import tribe_liar as L

META_ACCURACY = 90  # percent, both directions; fixed before any run
META_SOURCE = "tribe-metaknowledge"
SCHEMA_DEV, SCHEMA_EXAM = "echo4-roles1-liar2-dev-v1", "echo4-roles1-liar2-d-v1"
DEVELOPMENT = (611, 623, 639)
COHORTS = (tuple(range(268001, 268009)), tuple(range(268101, 268109)))
PARENT = ROOT / "lab/echo4/roles1-liar-dev-v1"
PARENT_DIGEST = "c77b31cde330f83bd9c861c070a500e882eb9aa73721962e828827025b2a8ad4"
DEV_DIR = ROOT / "lab/echo4/roles1-liar2-dev-v1"


def suggestion_meta(rows, tick, topic, feels):
    """Verified knower first; then ECHO's own feeling; then rank among the rest."""
    elim = L.eliminated(rows, tick, topic)
    known = T.last_knower(rows, topic)
    if known is not None and known not in elim:
        return known, elim
    candidates = [a for a in range(3) if a not in elim]
    if T.ECHO in candidates:
        if feels:
            return T.ECHO, elim
        candidates = [a for a in candidates if a != T.ECHO]
    return T.leader(T.rank_counts(rows, tick), candidates), elim


class MetaSession(L.LiarSession):
    def __init__(self, seed, *, meta=True, **kwargs):
        super().__init__(seed, **kwargs)
        if type(meta) is not bool:
            raise ValueError("meta flag")
        self.meta = meta
        rng = random.Random(seed ^ 0x3E7A)
        # Private noisy signal per topic, drawn once; the agent never sees knower.
        self.feels = {t: (self.knower[t] == T.ECHO) != (rng.randrange(100) >= META_ACCURACY)
                      for t in sorted(self.knower)}
        self.meta_seen = set()
        self.meta_refuted = 0

    def _feel(self, topic):
        """ECHO consults its own feeling; recorded once as a hypothesis."""
        if topic not in self.meta_seen:
            self.meta_seen.add(topic)
            raw = pack(src=2, rel=30, dst=2, time=9, domain=9, generator=8, style=62,
                       slot=int(self.feels[topic]), seq=topic)
            vertex, latency, _ = encode_event(raw)
            slot, _ = allocate(self.agents[T.ECHO].cam, raw, vertex, latency, (0,) * 6, has_fact=0,
                               extract="", source=META_SOURCE, key=raw)
            if slot < 0:
                raise RuntimeError("no capacity for a metaknowledge hypothesis")
        return self.feels[topic]

    def _suggest(self, seeker, rows, topic):
        if self.meta and seeker == T.ECHO:
            return suggestion_meta(rows, self.tick, topic, self._feel(topic))
        return L.suggestion(rows, self.tick, topic)

    def _row_for(self, seeker):
        arm = self.arm if seeker == T.ECHO else "tribe"
        if arm == "tribe":
            suggested, elim = self._suggest(seeker, self.memories[seeker].rows, self._round["topic"])
            return T.row(arm, seeker, suggested, elim), suggested, elim
        return super()._row_for(seeker)

    def _attempt(self, seeker, target):
        topic = self._round["topic"]
        if seeker == T.ECHO and target == T.ECHO and self.meta and self.feels.get(topic) \
                and self.knower[topic] != T.ECHO:
            self.meta_refuted += 1  # the feeling was wrong; a self_fail fact refutes it
        reward, knows = super()._attempt(seeker, target)
        if self.audit and self.audit[-1].get("tick") == self.tick and self.audit[-1].get("lie") \
                and "points_to_meta" not in self.audit[-1]:
            rows = self.memories[T.ECHO].rows
            self.audit[-1]["points_to_meta"] = suggestion_meta(rows, self.tick, topic, self._feel(topic))[0]
        return reward, knows


def life(seed):
    s = MetaSession(seed)
    frames = [s.step() for _ in range(T.ROUNDS)]
    lies = [r for r in s.audit if r["lie"]]
    honest = [r for r in s.audit if not r["lie"]]
    with_prior = [r for r in lies if r["prior"] is not None and r["prior"] != T.B]
    off = MetaSession(seed, meta=False, rate=0)
    off_frames = [off.step() for _ in range(T.ROUNDS)]
    v5 = E.TribeCSession(seed)
    v5_frames = [v5.step() for _ in range(T.ROUNDS)]
    again = MetaSession(seed)
    again_frames = [again.step() for _ in range(T.ROUNDS)]
    zero = MetaSession(seed, rate=0)
    zero_frames = [zero.step() for _ in range(T.ROUNDS)]
    echo_cam = s.agents[T.ECHO].cam
    meta_rows = [x for x in echo_cam.slot if x.occupied and x.source == META_SOURCE]
    self_fails = sum(1 for r in s.memories[T.ECHO].rows if r["kind"] == "self_fail")
    return {"seed": seed, "rate": s.rate, "lies": len(lies), "honest_answers": len(honest),
            "false_facts": sum(a.metrics.false_facts for a in s.agents), "credulous_false_facts": len(lies),
            "detected_by_key": sum(r["detected_by_key"] for r in lies),
            "with_prior": len(with_prior), "suspected_with_prior": sum(r["suspected_before_key"] for r in with_prior),
            "false_alarms": sum(r["suspected_before_key"] for r in honest),
            "points_to_knower": sum(r["points_to_meta"] == r["knower"] for r in lies),
            "control_points_to_knower": sum(r["points_to"] == r["knower"] for r in lies),
            "reliability": L.reliability(s.memories[T.ECHO].rows),
            "meta_hypotheses": len(meta_rows), "meta_never_fact": all(not x.has_fact and not x.extract for x in meta_rows),
            "meta_refuted": s.meta_refuted, "self_fail_receipts": self_fails,
            "net_published": sum(f["net"] for f in frames if f["seeker"] == T.ECHO),
            "net_without_lies_published": sum(f["net"] for f in zero_frames if f["seeker"] == T.ECHO),
            "off_equals_v5": canonical(E.strip(off_frames)) == canonical(E.strip(v5_frames)),
            "deterministic": canonical(E.strip(again_frames)) == canonical(E.strip(frames)),
            "invariant": s.invariant() and off.invariant()}


def judge(lives):
    tot = lambda k: sum(l[k] for l in lives)
    criteria = {
        "L1_zero_false_facts": tot("false_facts") == 0 and tot("lies") > 0,
        "L2_all_lies_detected": tot("detected_by_key") == tot("lies"),
        "L3_prior_detection": tot("with_prior") > 0 and 100 * tot("suspected_with_prior") >= 95 * tot("with_prior")
                              and tot("false_alarms") == 0,
        "L4_points_to_key": 10 * tot("points_to_knower") >= 9 * tot("lies"),
        "L5_reliability": all(l["reliability"][T.B] == l["lies"] and l["reliability"][T.C] == 0
                              and l["reliability"][T.ECHO] == 0 for l in lives),
        "L6_integrity": all(l["off_equals_v5"] and l["deterministic"] and l["invariant"] for l in lives),
        "L7_meta_hypothesis": all(l["meta_never_fact"] and l["meta_hypotheses"] > 0
                                  and l["meta_refuted"] <= l["self_fail_receipts"] for l in lives)}
    return {"lives": len(lives), "lies": tot("lies"), "points_to_knower": tot("points_to_knower"),
            "control_points_to_knower": tot("control_points_to_knower"), "with_prior": tot("with_prior"),
            "suspected_with_prior": tot("suspected_with_prior"), "false_alarms": tot("false_alarms"),
            "detected_by_key": tot("detected_by_key"), "credulous_false_facts": tot("credulous_false_facts"),
            "published": {"net": tot("net_published"), "net_without_lies": tot("net_without_lies_published"),
                          "meta_refuted": tot("meta_refuted"), "rates": [l["rate"] for l in lives]},
            "criteria": criteria, "passed": all(criteria.values())}


def sources():
    extras = ("echo4/tribe_liar2.py", "tests/test_echo4_tribe_liar2.py", "docs/ECHO4-ROLES1-LIAR-V2-DESIGN.md")
    return {**L.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["findings"] != []):
        raise ValueError("annex L v1 (red) custody mismatch")
    L.parent()
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_tribe_liar2"))
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, schema, groups, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": schema, "sources": manifest, "parent": ancestry, "seeds": groups,
                       "meta_accuracy": META_ACCURACY, "contract": "docs/ECHO4-ROLES1-LIAR-V2-DESIGN.md"})
    results = []
    for k, seeds in enumerate(groups):
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
        groups = tuple(tuple(s) for s in read_json(directory / "lock.json")["seeds"])
        if kind == "exam":
            dev = read_json(DEV_DIR / "audit-receipt.json")
            if not (dev["valid"] and dev["criteria_passed"]):
                raise ValueError("annex L v2 development not valid")
            official = groups == COHORTS
        passed = campaign(directory, report["schema"], groups, checking=True)["passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "liar_annex_green": bool(official and passed and not findings),
            "scope": f"ROLES-1 annex L v2 {kind} reconstruction"}


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
