"""Isolated public battery/routes consumer; no world, seed or oracle access."""
import json
import sys
sys.path.insert(0, '/agent')
from echoai.nexus0.power1.core import Guard

agent = None
for line in sys.stdin:
    if len(line) > 100_000:
        raise ValueError('message size')
    request = json.loads(line)
    if set(request) == {'model', 'policy'}:
        agent = Guard(request['model'], request['policy'])
        response = dict(ready=True)
    elif agent is not None:
        response = agent.decide(request)
    else:
        raise ValueError('initialization required')
    print(json.dumps(response, sort_keys=True), flush=True)
