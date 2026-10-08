"""Declared B16 recovery: canonicalize calibration parity, never outcomes."""
import json
import sys

from seed import s6b16 as r
from echo_arc.contrastive_evidence import BEHAVIOR

ROOT = r.ROOT / 'recovery1'
SOURCES = ('seed/s6b16_recovery1.py', 'tests/test_s6b16_recovery1.py',
           'docs/ECHO45-S6-B16-RECOVERY1.md')
LABELS = frozenset(('micro/baseline/A', 'micro/baseline/A/replay'))
ORIGINAL_MEASUREMENT = r.measurement


def canonical_baseline(value):
    normalized = json.loads(r.b.canonical(value))
    if value['trace_digest'] != r.b.sha(value['rows']) \
            or normalized['trace_digest'] != r.b.sha(normalized['rows']):
        raise RuntimeError('baseline canonicalization cannot repair a digest mismatch')
    for live, saved in zip(value['rows'], normalized['rows']):
        for field in BEHAVIOR:
            if live[field] != saved[field]:
                raise RuntimeError('baseline canonicalization changed behavior: ' + field)
    return normalized


def measurement(namespace='primary'):
    original = ORIGINAL_MEASUREMENT(namespace)
    def measure(label, policy, specs, **kwargs):
        value = original(label, policy, specs, **kwargs)
        return canonical_baseline(value) if label in LABELS else value
    return measure


def prepare():
    if (ROOT / 'receipt.json').exists():
        return verify()
    frozen = r.b.integrity()
    blocked = json.loads((ROOT / 'blocked.json').read_text())
    if blocked.get('stage') != 'BLOCKED_INSTRUMENT' \
            or blocked.get('reason') != 'RuntimeError: micro base/replay does not reproduce B14 378 exactly':
        raise RuntimeError('unexpected original blocking condition')
    if (r.ROOT / 'model-budget.json').exists() or list((r.ROOT / 'calls').glob('**/result.json')):
        raise RuntimeError('recovery must be declared before the first model call')
    from seed import s6b16_micro as micro
    _, reference, _ = micro.reference()
    files = ['primary/measurements/micro/baseline/A.json',
             'primary/measurements/micro/baseline/A/replay.json']
    for name in files:
        measured = json.loads((r.ROOT / name).read_text())
        if canonical_baseline(measured) != reference or measured['levels'] != 378:
            raise RuntimeError('persisted full baseline/replay is not exactly B14')
    diagnostics = [json.loads((ROOT / name).read_text())
                   for name in ('diagnostic.json', 'diagnostic2.json')]
    if any(not d['canonical_matches_saved'] or not d['behavior_fields_unchanged'] for d in diagnostics) \
            or diagnostics[1]['raw_matches_saved'] or not diagnostics[1]['type_differences']:
        raise RuntimeError('serialization diagnosis is not supported')
    budget = json.loads((r.ROOT / 'budget.json').read_text())
    if budget['scheduled_games'] != 162 or sum(d['new_games'] for d in diagnostics) != 2:
        raise RuntimeError('unexpected pre-recovery game accounting')
    artifacts = files + ['run-process.log', 'recovery1/blocked.json',
        'recovery1/budget-before.json', 'recovery1/diagnostic.json',
        'recovery1/diagnostic2.json', 'recovery1/diagnostic-record.json',
        'recovery1/diagnostic2-record.json', 'recovery1/tests.log']
    receipt = dict(valid=True, at=r.b.now(), profile_sha256=r.b.sha(frozen),
        scope='JSON materialization of the two micro baseline comparison objects only',
        scientific_condition_changed=False, frozen_sources_changed=False,
        original_failure_preserved=True, model_calls_before_recovery=0,
        baseline_games=160, diagnostic_games=2, scheduled_games_before_recovery=162,
        new_protected_games=0, new_exam_games=0, baseline_levels=378,
        baseline_trace_digest=reference['trace_digest'],
        sources={name:r.model.digest_file(r.REPO/name) for name in SOURCES},
        artifacts={name:r.model.digest_file(r.ROOT/name) for name in artifacts})
    archive=ROOT/'frozen'
    for name in SOURCES:
        dest=archive/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes((r.REPO/name).read_bytes())
    r.b.atomic(ROOT/'receipt.json',receipt)
    return verify()


def verify():
    receipt=json.loads((ROOT/'receipt.json').read_text())
    if receipt.get('valid') is not True or receipt['profile_sha256']!=r.b.sha(r.b.integrity()):
        raise RuntimeError('recovery profile custody mismatch')
    for name,digest in receipt['sources'].items():
        if r.model.digest_file(r.REPO/name)!=digest \
                or r.model.digest_file(ROOT/'frozen'/name)!=digest:
            raise RuntimeError('frozen recovery source changed: '+name)
    for name,digest in receipt['artifacts'].items():
        if r.model.digest_file(r.ROOT/name)!=digest:
            raise RuntimeError('recovery evidence changed: '+name)
    return receipt


def main(args):
    if args==['prepare']:
        result=prepare()
        print(r.b.canonical({k:result[k] for k in ('valid','at','profile_sha256','scheduled_games_before_recovery')}))
    elif args==['follow']:
        receipt=verify()
        r.measurement=measurement
        r.b.measurement=measurement
        r.b.atomic(ROOT/'resume.json',dict(at=r.b.now(),receipt_sha256=r.b.sha(receipt)))
        r.main(['follow'])
    else:
        raise SystemExit('use prepare or follow')


if __name__=='__main__':
    main(sys.argv[1:])
