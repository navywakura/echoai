"""Audit instrument recovery: compare canonical JSON, preserve frozen execution."""
import hashlib
import json
from pathlib import Path
from types import FunctionType

from seed import s6probe1_audit as audit

ROOT = audit.ROOT / 'instrument-recovery1'


def profile():
    return {'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'original_instrument_profile_sha256': audit.sha(audit.integrity()),
            'normalization': 'serialize measurement with canonical JSON and reload before comparing',
            'execution_changed': False, 'V3_changed': False, 'sample_changed': False,
            'cache': str((audit.ROOT / 'cache').resolve()), 'max_games': audit.MAX_GAMES}


def measure(*args, **kwargs):
    result = audit.measure(*args, **kwargs)
    normalized = json.loads(audit.p1.canonical(result))
    if audit.sha(result) != audit.sha(normalized):
        raise RuntimeError('canonical normalization changed measurement digest')
    return normalized


def atomic(path, value):
    if path == audit.ROOT / 'audit.json':
        saved = json.loads((ROOT / 'profile.json').read_text())
        if saved != profile():
            raise RuntimeError('instrument recovery source changed')
        value = dict(value, instrument_recovery_sha256=audit.sha(saved),
                     instrument_recovery=str(ROOT / 'profile.json'))
    audit.atomic(path, value)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    if not (ROOT / 'profile.json').exists():
        audit.atomic(ROOT / 'profile.json', profile())
        audit.atomic(ROOT / 'prior-status.json', json.loads((audit.ROOT / 'status.json').read_text()))
        audit.atomic(ROOT / 'prior-budget.json', json.loads((audit.ROOT / 'budget.json').read_text()))
    if json.loads((ROOT / 'profile.json').read_text()) != profile():
        raise RuntimeError('instrument recovery profile changed')
    run = FunctionType(audit.run.__code__, dict(audit.run.__globals__, measure=measure, atomic=atomic))
    run()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        audit.status('BLOCKED', error=type(exc).__name__, message=str(exc))
        raise
