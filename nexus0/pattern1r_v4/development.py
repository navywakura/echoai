"""Complete the six declared development worlds; never replace a flight."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import campaign as cp
from .inspect_dev import inspect


def main():
    manifest = cp.ROOT/(cp.DEVELOPMENT_NAME+'-plan.json')
    if manifest.exists():
        raise FileExistsError('development batch already started')
    names = cp.CANDIDATE_FILES
    def code():
        return {name:cp.sha256_bytes((cp.HERE/name).read_bytes()) for name in names}
    before = code()
    cp.save(manifest, cp.seal(dict(worlds=list(range(6)), seeds=list(range(20261621,20261627)),
                                  workers=2, condition='perturbed', faults=False,
                                  first_pilot_already_flown=False, candidate=cp.DEVELOPMENT_NAME, code=before)))
    def one(index):
        label = f'{cp.DEVELOPMENT_NAME}-w{index}'
        root = cp.ROOT/'dev'/label
        if root.exists():
            raise FileExistsError(root)
        log = cp.ROOT/f'{label}.log'
        with open(log,'x') as out:
            run = subprocess.run([sys.executable,'-u','-m','echoai.nexus0.pattern1r_v4.dev',label,
                                  '--world',str(index),'--seed',str(20261621+index)],
                                 cwd=cp.c.ECHOAI,env=dict(os.environ,PYTHONPATH=str(cp.c.ECHOAI.parent)),
                                 stdout=out,stderr=subprocess.STDOUT)
        if run.returncode:
            return dict(label=label,passed=False,error=f'dev exit {run.returncode}')
        result = inspect(label)
        print(json.dumps(dict(label=label,passed=result['passed'],
                              red=[k for k,v in result['groups'].items() if v['status']!='pass'])),flush=True)
        return result
    def guarded(index):
        try:
            return one(index)
        except Exception as exc:
            result = dict(label=f'{cp.DEVELOPMENT_NAME}-w{index}', passed=False,
                          error=type(exc).__name__+': '+str(exc)[:300])
            print(json.dumps(result), flush=True)
            return result
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(guarded, range(6)))
    result = cp.seal(dict(kind='development', passed=code()==before and all(r['passed'] for r in results),
                          code_unchanged=code()==before, results=results))
    cp.save(cp.ROOT/(cp.DEVELOPMENT_NAME+'-report.json'),result)
    print(json.dumps(dict(passed=result['passed'],worlds=len(results))),flush=True)
    return result['passed']


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
