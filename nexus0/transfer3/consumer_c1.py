"""Isolated Plan C1 consumer. Frames in; one causal WSP, admitted cells out.

Mounted read-only with the agent's own modules only. It cannot import the
camera world, the school or the bench, because they are never copied in. The
camera calibration arrives frozen and nothing here can change it.
"""
import json
import sys

sys.path.insert(0, '/agent')

from echoai.nexus0.transfer3.planner_c1 import CalibratedPlanner

agent = None
for line in sys.stdin:
    if len(line) > 2_000_000:
        raise ValueError('message size')
    request = json.loads(line)
    if agent is None:
        if set(request) != {'model', 'goal', 'camera', 'reserve'}:
            raise ValueError('initialization schema')
        agent = CalibratedPlanner(request['model'], request['goal'], request['camera'],
                                  reserve=request['reserve'])
        print(json.dumps(dict(ready=True, offset=list(agent.offset),
                              model_sha256=agent.model.fingerprint()), sort_keys=True), flush=True)
        continue
    if 'frozen_check' in request:
        print(json.dumps(dict(offset=list(agent.offset), model_sha256=agent.model.fingerprint(),
                              learning=agent.learning), sort_keys=True), flush=True)
        continue
    decision = agent.decide(request)
    decision['admitted'] = agent.admitted()
    print(json.dumps(decision, sort_keys=True), flush=True)
