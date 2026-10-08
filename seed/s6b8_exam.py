"""B8 examination: distinct unopened cohort and unchanged scientific gates."""
import json
from types import FunctionType

from seed import s6b8 as s, s6_precise_capacity as c, s6_precise_exam as previous

measure = FunctionType(c.measure.__code__, dict(s.measure.__globals__, ROOT=s.ROOT / "exam/measurements"),
                       "measure", c.measure.__defaults__)


def development_one(item):
    worker = FunctionType(previous.previous.development_one.__code__,
                          dict(previous.previous.development_one.__globals__, s=s))
    return worker(item)


development = FunctionType(previous.previous.development.__code__,
                          dict(previous.previous.development.__globals__, s=s, development_one=development_one))
checks = previous.checks


def run():
    s.integrity()
    assert json.loads((s.ROOT / "pilot.json").read_text())["promote"]
    assert json.loads((s.ROOT / "pilot-audit.json").read_text())["valid"]
    assert json.loads((s.ROOT / "campaign-audit.json").read_text())["valid"]
    policies = json.loads((s.ROOT / "strategies.json").read_text())
    completed = json.loads((s.ROOT / "completed.json").read_text())
    assert completed["sources"] == s.hashes() and completed["strategies_sha256"] == s.sha(policies)
    assert completed["profile_sha256"] == s.sha(s.integrity())
    out = s.ROOT / "exam"
    if (out / "opened.json").exists():
        receipt = json.loads((out / "opened.json").read_text())
        assert receipt["strategies_sha256"] == s.sha(policies) and receipt["sources"] == s.hashes()
        assert not (out / "audit.json").exists(), "closed exam never reopened"
    else:
        s.atomic(out / "opened.json", {"at": s.now(), "strategies_sha256": s.sha(policies), "sources": s.hashes()})
    from seed import arc3gym as gym
    validation = {}
    for version in (2, 3):
        gym.VERSION = version
        validation[version] = gym.validate(list(s.EXAM_SEEDS))
    s.atomic(out / "validation.json", validation)
    totals, replays, families = {}, {}, {}
    specs = [(v, seed, rep, 2000) for v in (2, 3) for seed in s.EXAM_SEEDS for rep in range(3)]
    for arm, policy in policies.items():
        s.status("EXAM", arm=arm)
        result = measure(arm, policy, specs, observed=False)
        repeat = measure(arm + "-replay", policy, [spec for spec in specs if spec[2] == 0], observed=False, replay=True)
        replays[arm] = s.sha([row for row in result["rows"] if row["rep"] == 0]) == repeat["trace_digest"]
        totals[arm] = {"levels": result["levels"], "score": result["score"] / len(specs),
                       "policy_sha256": s.Execution.digest(policy)}
        families[arm] = {family: sum(row["levels_completed"] for row in result["rows"] if row["family"] == family)
                         for family in sorted({row["family"] for row in result["rows"]})}
    dev = {arm: development(policies[arm], out / ("development-" + arm)) for arm in ("semilla", "echo")}
    for stage in ["p" + str(i) for i in range(3)] + ["c" + str(i) for i in range(6)]:
        s.audit_model(stage)
    verdicts = checks(totals, dev, all(replays.values()) and
                      all(row["solver_levels"] == row["levels"] == 300 for row in validation.values()))
    s.integrity()
    s.atomic(out / "audit.json", {"at": s.now(), "green": all(verdicts.values()), "checks": verdicts,
             "totals": totals, "families": families, "development": dev, "replays": replays,
             "training_audit": True, "model_payload_audit": True,
             "strategies_sha256": s.sha(policies), "sources": s.hashes(), "cost_usd": 0})
