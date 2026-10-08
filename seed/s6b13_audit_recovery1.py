"""Transport-only recovery of the completed, non-promoting B13-R1 pilot."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

from seed import s6b13_runtime1 as r

ROOT = r.ROOT / 'audit-launch-recovery1'
SOURCES = ('seed/s6b13_audit_recovery1.py', 'tests/test_s6b13_audit_recovery1.py',
           'docs/ECHO45-S6-B13-AUDIT-LAUNCH-RECOVERY.md')
INPUTS = ('profile.json', 'pilot.json', 'pilot-process.json', 'preflight.json', 'model-budget.json')


def identity():
    frozen = r.b.integrity()
    pilot = json.loads((r.ROOT / 'pilot.json').read_text())
    if pilot['promote'] is not False or pilot['model_calls'] != 36 or len(pilot['verdicts']) != 54:
        raise RuntimeError('this recovery is limited to the completed, non-promoting pilot')
    if (r.ROOT / 'exam/opened.json').exists() or (r.ROOT / 'campaign.json').exists():
        raise RuntimeError('unexpected later phase')
    return dict(profile_sha256=r.b.sha(frozen),
                sources={name: r.m.digest_file(r.REPO / name) for name in SOURCES},
                inputs={name: r.m.digest_file(r.ROOT / name) for name in INPUTS})


def prepare():
    value = identity()
    receipt = ROOT / 'prepared.json'
    if receipt.exists():
        saved = json.loads(receipt.read_text())
        if saved['identity'] != value:
            raise RuntimeError('recovery source or completed pilot changed')
        return saved
    blocked = json.loads((r.ROOT / 'status.json').read_text())
    if blocked['stage'] != 'BLOCKED_INSTRUMENT' or blocked['reason'] != (
            "AttributeError: 'types.SimpleNamespace' object has no attribute 'STDOUT'"):
        raise RuntimeError('unexpected original failure')
    if list((r.ROOT / 'pilot-independent/cache').rglob('*.json')):
        raise RuntimeError('initial audit cache must be empty')
    for name in SOURCES:
        target = ROOT / 'source-archive' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((r.REPO / name).read_bytes())
    saved = dict(at=r.b.now(), identity=value, original_blocked_status=blocked,
                 original_budget=json.loads((r.ROOT / 'budget.json').read_text()),
                 operation='supply subprocess.STDOUT; resume frozen follow and independent audit',
                 new_model_calls=0, scientific_changes=False)
    r.b.atomic(receipt, saved)
    return saved


def install_transport():
    # Frozen follow evaluates both .run and .STDOUT on this transport object.
    # The child entry point and all scientific functions remain the R1 versions.
    r.b.subprocess = SimpleNamespace(run=r.audit_dispatch, STDOUT=subprocess.STDOUT)


def follow():
    prepare()
    install_transport()
    r.b.main(['follow'])
    prepare()  # Scientific inputs, model-call ledger and recovery sources unchanged.


if __name__ == '__main__':
    follow()
