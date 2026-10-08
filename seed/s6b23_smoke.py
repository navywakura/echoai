"""Real baseline/replay/audit instrument check, isolated from the B23 experiment."""
import os
from pathlib import Path
import sys
import time
from seed import s6b23 as r, s6b23_build as build


def main():
    from importlib.metadata import version
    if ('.'.join(map(str,sys.version_info[:3])),version('numpy'),version('arcengine'))!=('3.12.13','2.3.2','0.9.3'):
        raise RuntimeError('use frozen actor environment')
    root=r.REPO/'lab/seed/s6b23-instrument-r1-20261007'
    if root.exists():raise RuntimeError('instrument receipt exists; inspect before retry')
    root.mkdir(parents=True);r.ROOT=root;r.INPUT=root/'input';r.INPUT.mkdir()
    os.environ.update(ECHO_B23_ROOT=str(root),ECHO_B23_INPUT=str(r.INPUT))
    fixture=build.prior_receipts();r.atomic(r.INPUT/'baseline.json',fixture)
    manifest=dict(configuration=r.config(),sources={f:r.file_sha(r.REPO/f) for f in build.closure()},
                  inputs={'baseline.json':r.file_sha(r.INPUT/'baseline.json')},
                  python='3.12.13',numpy='2.3.2',arcengine='0.9.3',
                  purpose='INSTRUMENT_ONLY: baseline parity; no candidates, models or protected cases')
    r.atomic(r.INPUT/'manifest.json',manifest)
    r.journal(root/'live/journal.jsonl',dict(kind='request',arm='instrument',request={'reason':manifest['purpose']}))
    start=time.monotonic()
    base=r.triple('s-M23','baseline',fixture['policy'],r.A);r.parity(base)
    ledger=r.read(root/'budget.json')
    for job in ledger['jobs']:
        for kind in ('started','completed'):
            receipt=r.read(root/'executions'/kind/f"{job['job_id']:06d}.json")
            if receipt['task_id']!=job['task_id']:raise RuntimeError('misplaced execution receipt')
    result=dict(valid=True,levels=base['levels'],games=r.read(root/'budget.json')['scheduled_games'],
                seconds=time.monotonic()-start,model_calls=0,proposals=0,s6_green=False,
                purpose=manifest['purpose'],profile_sha256=r.sha(manifest))
    r.atomic(root/'result.json',result)
    r.journal(root/'live/journal.jsonl',dict(kind='verdict',arm='instrument',**result))
    print(r.canonical(result),flush=True)


if __name__=='__main__':main()
