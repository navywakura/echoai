"""Isolated DRONE-3 consumer: one JSON observation in, one WSP decision out.

Runs inside the SIM-3 bubblewrap cage with only the mounted modules below.
The initialization carries the frozen COMPOSE model, the goal hypothesis, the
two C1 integers and the POWER cost table. Nothing else crosses the wire.
"""
import json
import sys
sys.path.insert(0, '/agent')
from echoai.nexus0.drone3.agent import MissionAgent

INIT = {'model', 'goal', 'offset', 'power_model', 'mode', 'power_policy'}
agent = None
for line in sys.stdin:
    if len(line) > 2_000_000:
        raise ValueError('message size')
    request = json.loads(line)
    if agent is None:
        if set(request) != INIT:
            raise ValueError('initialization schema')
        agent = MissionAgent(**request)
        print(json.dumps(dict(ready=True, model_sha256=agent.fingerprint(), offset=agent.offset),
                         sort_keys=True), flush=True)
        continue
    print(json.dumps(agent.decide(request), sort_keys=True), flush=True)
