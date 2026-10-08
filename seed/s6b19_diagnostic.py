"""Declared post-B18 development; consumed B is never a new confirmation."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import multiprocessing
from pathlib import Path
from types import FunctionType

from seed import s6b11 as engine
from seed.game_selfimprove import canonical, sha
from echo_arc import consumption_timeline as timeline

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO/'lab/seed/s6b19-diagnostic-20261005'
INPUT = REPO/'lab/kaggle/s6b18-20261005/input/baseline.json'
SPECS = [(2,18,0,2000)] + [(3,i-40,0,2000) for i in (42,51,53,59,68,76,77)] + [(3,i,0,2000) for i in (28026,28027,28031,28039)]
VALUES = (1,2,4,8,12,16,20,24,32,40)
_play = FunctionType(engine.play_one.__code__, dict(engine.play_one.__globals__,
    ROOT=ROOT,A=SPECS,B=[],EXAM_SEEDS=(),evidence=timeline))

def worker(job):
    name, policy, spec = job
    directory = ROOT/'journals'/name/f'{spec[0]}-{spec[1]}'
    row = json.loads(canonical(_play((policy,tuple(spec),str(directory)))))
    return name, spec, row

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    base=json.loads(INPUT.read_text())['policy']
    policies={'base':base}
    guard=dict(reset_known=['eq',1],pending_effect=['eq',0],world_events=['le',16])
    for n in VALUES:
        policies[f'hold{n}']=engine.strategy(program=engine.patch.append(base['program'],{'patches':[{'when':guard,'set':{'HOLD':n}}]}))
    plan=dict(specs=SPECS,policies=policies,source=sha(Path(__file__).read_text()),origin='RETROSPECTIVE_DEVELOPMENT_AFTER_B18',exam_opened=False)
    if (ROOT/'plan.json').exists():
        assert json.loads((ROOT/'plan.json').read_text())==json.loads(canonical(plan))
    else: engine.atomic(ROOT/'plan.json',plan)
    jobs=[(name,p,s) for name,p in policies.items() for s in SPECS if not (ROOT/'rows'/name/f'{s[0]}-{s[1]}.json').exists()]
    with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn'),initializer=engine.old.worker_init) as pool:
        for n,f in enumerate(as_completed([pool.submit(worker,j) for j in jobs]),1):
            name,s,row=f.result();engine.atomic(ROOT/'rows'/name/f'{s[0]}-{s[1]}.json',row)
            record=dict(completed=132-len(jobs)+n,total=132,name=name,spec=s,levels=row['levels_completed'],score=row['score'])
            engine.atomic(ROOT/'status.json',record);print(canonical(record),flush=True)
    summary=[]
    for name in policies:
        effects=[]
        for s in SPECS:
            b=json.loads((ROOT/'rows/base'/f'{s[0]}-{s[1]}.json').read_text())
            a=json.loads((ROOT/'rows'/name/f'{s[0]}-{s[1]}.json').read_text())
            effects.append(dict(spec=s,levels=a['levels_completed']-b['levels_completed'],score=a['score']-b['score'],decisions=len(a['actions'])-a['resets'],resets=a['resets']))
        summary.append(dict(name=name,gain=sum(x['levels'] for x in effects),losses=[x for x in effects if x['levels']<0 or x['score'] < -1e-10],effects=effects))
    engine.atomic(ROOT/'result.json',dict(plan_sha256=sha(plan),summary=summary,physical_games=132,exam_opened=False,s6_green=False))
    print(canonical([dict(name=x['name'],gain=x['gain'],losses=len(x['losses'])) for x in summary]),flush=True)

if __name__=='__main__':main()
