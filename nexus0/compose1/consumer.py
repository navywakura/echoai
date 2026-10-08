"""Interactive WSP/control experiment in the SIM-3 cage."""
import json
import sys
sys.path.insert(0,'/agent')
from echoai.nexus0.compose1.controller import Composer

agent=None
for line in sys.stdin:
    if len(line)>2_000_000:raise ValueError('message size')
    request=json.loads(line)
    if agent is None:
        if set(request)!={'model','goal','mode'}:raise ValueError('initialization schema')
        agent=Composer(**request)
        print(json.dumps(dict(ready=True,spatial_cells=len(agent.cells),model_sha256=agent.model.fingerprint())),flush=True)
    else:
        print(json.dumps(agent.decide(request),sort_keys=True),flush=True)
