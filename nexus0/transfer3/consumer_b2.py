"""Isolated B2: only gain payload, goal, safe-mode and sensor frames."""
import json
import sys
sys.path.insert(0, '/agent')
from echoai.nexus0.transfer3.calib_b2 import restore
from echoai.nexus0.transfer3.planner_b2 import Planner
from echoai.nexus0.transfer3.costs_a2 import nominal

agent = None
for line in sys.stdin:
    if len(line) > 2_000_000:
        raise ValueError('message size')
    request = json.loads(line)
    if agent is None:
        if set(request) != {'payload','goal','safe'} or type(request['safe']) is not bool:
            raise ValueError('initialization schema')
        agent = Planner(restore(request['payload']).snapshot(), request['goal'],
                        nominal(), reserve=6, safe=request['safe'])
        result = dict(ready=True, model_sha256=agent.model.fingerprint(), spatial_cells=len(agent.cells))
    elif request == {'frozen_check':True}:
        result = dict(model_sha256=agent.model.fingerprint(), learning=agent.learning)
    else:
        result = agent.decide(request)
    print(json.dumps(result,sort_keys=True),flush=True)
