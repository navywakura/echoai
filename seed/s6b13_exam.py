"""B13's sealed four-arm exam. No observer, feedback or post-exam adaptation."""
import json
from types import FunctionType

from seed import s6b13 as s, s6_precise_exam


def development_one(item):
    native = s6_precise_exam.previous.development_one
    return FunctionType(native.__code__, dict(native.__globals__, s=s))(item)


development = FunctionType(s6_precise_exam.previous.development.__code__,
    dict(s6_precise_exam.previous.development.__globals__, s=s, development_one=development_one))


def eligible():
    frozen = s.integrity()
    for phase in ('pilot', 'campaign'):
        result = json.loads((s.ROOT / (phase + '.json')).read_text())
        audit = json.loads((s.ROOT / (phase + '-audit.json')).read_text())
        if result['promote'] is not True or audit['valid'] is not True \
                or audit['independent_execution'] is not True \
                or result['profile_sha256'] != s.sha(frozen) or audit['profile_sha256'] != s.sha(frozen):
            raise RuntimeError('pilot/campaign promotion and independent audits required')
    policies = json.loads((s.ROOT / 'strategies.json').read_text())
    completed = json.loads((s.ROOT / 'completed.json').read_text())
    if set(policies) != {'semilla', 'fijo', 'echo', 'sinfiltro'} or policies['semilla'] != s.strategy() \
            or completed['profile_sha256'] != s.sha(frozen) or completed['sources'] != s.hashes() \
            or completed['strategies_sha256'] != s.sha(policies):
        raise RuntimeError('four frozen policies required')
    return policies


def run():
    policies = eligible()  # Must precede environment import or construction.
    out = s.ROOT / 'exam'
    receipt = dict(strategies_sha256=s.sha(policies), sources=s.hashes())
    if (out / 'audit.json').exists():
        closed = json.loads((out / 'audit.json').read_text())
        if any(closed[k] != v for k, v in receipt.items()):
            raise RuntimeError('closed exam provenance mismatch')
        return closed
    if (out / 'opened.json').exists():
        original = json.loads((out / 'opened.json').read_text())
        if any(original[k] != v for k, v in receipt.items()):
            raise RuntimeError('interrupted exam policies changed')
    else:
        s.atomic(out / 'opened.json', dict(at=s.now(), **receipt))
    from seed import arc3gym as gym
    validation = {}
    for version in (2, 3):
        gym.VERSION = version
        validation[version] = gym.validate(list(s.EXAM_SEEDS))
    s.atomic(out / 'validation.json', validation)
    specs = [(v, seed, rep, 2000) for v in (2, 3) for seed in s.EXAM_SEEDS for rep in range(3)]
    measure = s.measurement('exam')
    totals, families, replays = {}, {}, {}
    for arm, policy in policies.items():
        s.status('EXAM', arm=arm)
        result = measure(arm, policy, specs, observed=False)
        repeat = measure(arm + '/replay', policy, [x for x in specs if x[2] == 0], observed=False, replay=True)
        replays[arm] = s.sha([r for r in result['rows'] if r['rep'] == 0]) == repeat['trace_digest']
        if not replays[arm]:
            raise RuntimeError('reserved replay differs; stop and preserve the open exam')
        totals[arm] = dict(levels=result['levels'], score=result['score'] / len(specs),
                           policy_sha256=s.Execution.digest(policy))
        families[arm] = {f: sum(r['levels_completed'] for r in result['rows'] if r['family'] == f)
                         for f in sorted({r['family'] for r in result['rows']})}
    dev, dev_replays = {}, {}
    for arm in ('semilla', 'echo'):
        # Count interrupted work conservatively. Twenty-four official episodes
        # plus a completely separate replay; no protected decision journal.
        for label in (arm, arm + '-replay'):
            folder = out / ('development-' + label)
            ticket = out / ('development-' + label + '-reserved.json')
            if not ticket.exists():
                s.reserve_games(24)
                s.atomic(ticket, {'games': 24})
            value = development(policies[arm], folder)
            if label == arm:
                dev[arm] = value
            else:
                dev_replays[arm] = value['trace_digest'] == dev[arm]['trace_digest']
                if not dev_replays[arm]:
                    raise RuntimeError('official development replay differs')
    instrument = all(replays.values()) and all(dev_replays.values()) and \
        all(v['solver_levels'] == v['levels'] == 300 for v in validation.values())
    checks = s6_precise_exam.checks(totals, dev, instrument)
    s.integrity()
    result = dict(at=s.now(), green=all(checks.values()), checks=checks, totals=totals,
                  families=families, development=dev, replays=replays, development_replays=dev_replays,
                  training_audit=True, model_payload_audit=True, cost_eur=0, **receipt)
    s.atomic(out / 'audit.json', result)
    return result
