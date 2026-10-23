"""Run the original ECHO policy with a .wsp memory in a development world."""
import argparse
import hashlib
import json
from pathlib import Path

from ..memx.agent import Agent
from ..memx.world import Obs,make_world
from .memory import load_memory


def value(x):return json.loads(json.dumps(vars(x)))


class RecordingWorld:
    def __init__(self,world):self.world=world;self.records=[]
    def __getattr__(self,key):return getattr(self.world,key)
    def reset(self):
        obs=self.world.reset();self.records.append(dict(event='reset',observation=value(obs)));return obs
    def step(self,action):
        obs=self.world.step(action);self.records.append(dict(event='step',action=action,observation=value(obs)));return obs


class ReplayWorld:
    def __init__(self,receipt):
        self.records=iter(receipt['trace']);self.absolute=receipt['absolute'];self.acts=tuple(receipt['acts'])
    def _take(self,event,action=None):
        row=next(self.records);assert row['event']==event
        if action is not None:assert row['action']==action,'policy changed action'
        data=dict(row['observation']);data['grid']=tuple(tuple(x) for x in data['grid']);data['pos']=tuple(data['pos'])
        return Obs(**data)
    def reset(self):return self._take('reset')
    def step(self,action):return self._take('step',action)
    def exhausted(self):return next(self.records,None) is None


def episode(memory,family,seed,regime):
    world=RecordingWorld(make_world(family,seed,regime))
    before=memory.head if memory else None
    try:
        result=Agent(source=memory).run(world)
        return dict(family=family,seed=seed,regime=regime,result=result,trace=world.records,
                    absolute=world.absolute,acts=list(world.acts),memory_head=before,
                    memory_unchanged=(memory.head==before) if memory else True,
                    source_queries=memory.queries if memory else 0,source_hits=memory.hits if memory else 0)
    finally:world.close()


def audit_episode(receipt,memory):
    replay=ReplayWorld(receipt);result=Agent(source=memory).run(replay)
    assert result==receipt['result'] and replay.exhausted(),'policy replay differs'
    assert receipt['memory_unchanged'] and (memory is None or memory.head==receipt['memory_head']),'memory altered'
    return True


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('memory',type=Path)
    p.add_argument('--family',choices=('LavaGapS7','DoorKey6','DynObs6'),default='DynObs6')
    p.add_argument('--seed',type=int,default=202610230);p.add_argument('--regime',choices=('A1','A2'),default='A2')
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    receipt=episode(load_memory(a.memory),a.family,a.seed,a.regime)
    receipt.update(memory_file=str(a.memory),memory_sha256=hashlib.sha256(a.memory.read_bytes()).hexdigest())
    with a.output.open('x') as out:json.dump(receipt,out,sort_keys=True);out.write('\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='trace'},sort_keys=True))
