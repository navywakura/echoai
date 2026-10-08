"""Isolated Plan A2 consumer: frames in, one causal WSP plus diagnostics out.

Runs inside bubblewrap with a read-only mount of the agent's own modules and
nothing else. It cannot import `space_a2`, `body_a1` or any simulator, because
those are never copied into the cage: cost arithmetic lives in `costs_a2`, which
knows nothing about worlds. Calibration arrives frozen and is never updated here.
"""
import json
import sys

sys.path.insert(0, '/agent')

from echoai.nexus0.transfer3.planner_a2 import CostPlanner

agent = None
for line in sys.stdin:
    if len(line) > 2_000_000:
        raise ValueError('message size')
    request = json.loads(line)
    if agent is None:
        if set(request) != {'model', 'goal', 'calibration', 'reserve'}:
            raise ValueError('initialization schema')
        agent = CostPlanner(request['model'], request['goal'], request['calibration'],
                            learning=False, reserve=request['reserve'])
        print(json.dumps(dict(ready=True, model_sha256=agent.model.fingerprint(),
                              calibration=list(agent.frozen()[0])+[agent.frozen()[1]]),
                         sort_keys=True), flush=True)
        continue
    if 'frozen_check' in request:
        print(json.dumps(dict(calibration=list(agent.frozen()[0])+[agent.frozen()[1]],
                              observations=agent.observations,
                              model_sha256=agent.model.fingerprint()),
                         sort_keys=True), flush=True)
        continue
    print(json.dumps(agent.decide(request), sort_keys=True), flush=True)
