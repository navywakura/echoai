"""B3 isolated entrypoint. Same transport schema, conditional-motion planner."""
import json
import sys
sys.path.insert(0,'/agent')
from echoai.nexus0.transfer3.calib_b2 import restore
from echoai.nexus0.transfer3.planner_b3 import Planner
from echoai.nexus0.transfer3.costs_a2 import nominal

agent=None
for line in sys.stdin:
    if len(line)>2_000_000:raise ValueError('message size')
    request=json.loads(line)
    if agent is None:
        if set(request)!={'payload','goal','safe'} or request['safe'] is not True:
            raise ValueError('initialization schema')
        agent=Planner(restore(request['payload']).snapshot(),request['goal'],nominal(),reserve=6,safe=True)
        result=dict(ready=True,model_sha256=agent.model.fingerprint(),spatial_cells=len(agent.cells))
    elif request=={'frozen_check':True}:
        result=dict(model_sha256=agent.model.fingerprint(),learning=agent.learning)
    else:
        result=agent.decide(request)
    print(json.dumps(result,sort_keys=True),flush=True)
