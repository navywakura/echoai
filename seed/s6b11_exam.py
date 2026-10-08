"""B11 four-arm reserved evaluation; unchanged B1--B5, no instrumentation."""
import json
from types import FunctionType
from seed import s6b11 as s, s6_precise_exam

measure = FunctionType(s.measure.__code__, dict(s.measure.__globals__, ROOT=s.ROOT / 'exam/measurements'),
                       'measure', s.measure.__defaults__)


def development_one(item):
    native = s6_precise_exam.previous.development_one
    return FunctionType(native.__code__, dict(native.__globals__, s=s))(item)


development = FunctionType(s6_precise_exam.previous.development.__code__,
    dict(s6_precise_exam.previous.development.__globals__, s=s, development_one=development_one))


def run():
    s.integrity()
    for phase in ('pilot', 'campaign'):
        assert json.loads((s.ROOT / (phase + '.json')).read_text())['promote']
        audit = json.loads((s.ROOT / (phase + '-audit.json')).read_text())
        assert audit['valid'] and audit['profile_sha256'] == s.sha(s.integrity())
    policies = json.loads((s.ROOT / 'strategies.json').read_text())
    completed = json.loads((s.ROOT / 'completed.json').read_text())
    assert completed['sources'] == s.hashes() and completed['strategies_sha256'] == s.sha(policies)
    assert completed['profile_sha256'] == s.sha(s.integrity())
    assert policies['semilla'] == s.strategy()
    out = s.ROOT / 'exam'
    receipt = {'strategies_sha256': s.sha(policies), 'sources': s.hashes()}
    if (out / 'opened.json').exists():
        saved = json.loads((out / 'opened.json').read_text())
        assert all(saved[k] == v for k, v in receipt.items())
        assert not (out / 'audit.json').exists(), 'closed exam never reopened'
    else:
        s.atomic(out / 'opened.json', dict(at=s.now(), **receipt))
    from seed import arc3gym as gym
    validation = {}
    for version in (2, 3):
        gym.VERSION = version
        validation[version] = gym.validate(list(s.EXAM_SEEDS))
    s.atomic(out / 'validation.json', validation)
    totals, replays, families = {}, {}, {}
    specs = [(v, seed, rep, 2000) for v in (2, 3) for seed in s.EXAM_SEEDS for rep in range(3)]
    for arm, policy in policies.items():
        s.status('EXAM', arm=arm)
        result = measure(arm, policy, specs, observed=False)
        repeat = measure(arm + '-replay', policy, [x for x in specs if x[2] == 0], observed=False, replay=True)
        replays[arm] = s.sha([r for r in result['rows'] if r['rep'] == 0]) == repeat['trace_digest']
        totals[arm] = {'levels': result['levels'], 'score': result['score'] / len(specs),
                       'policy_sha256': s.Execution.digest(policy)}
        families[arm] = {f: sum(r['levels_completed'] for r in result['rows'] if r['family'] == f)
                         for f in sorted({r['family'] for r in result['rows']})}
    dev = {arm: development(policies[arm], out / ('development-' + arm)) for arm in ('semilla', 'echo')}
    for phase, prefix in (('pilot', 'p'), ('campaign', 'c')):
        for i in range(s.phase_shape(phase)[0]):
            s.audit_model(prefix + str(i))
    checks = s6_precise_exam.checks(totals, dev, all(replays.values()) and
        all(r['solver_levels'] == r['levels'] == 300 for r in validation.values()))
    s.integrity()
    s.atomic(out / 'audit.json', {'at': s.now(), 'green': all(checks.values()), 'checks': checks,
        'totals': totals, 'families': families, 'development': dev, 'replays': replays,
        'training_audit': True, 'model_payload_audit': True, 'strategies_sha256': s.sha(policies),
        'sources': s.hashes(), 'cost_usd': 0})
