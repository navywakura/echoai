"""Public-only consumer. Mounted code contains no world, labels or seeds."""
import json
import sys
sys.path.insert(0, '/agent')
from echoai.nexus0.cause1.core import prepare, attribute
from echoai.nexus0.cause1.perception import project

pending = None
for line in sys.stdin:
    if len(line) > 500_000:
        raise ValueError('request too large')
    request = json.loads(line)
    if pending is None:
        if set(request) != {'intention', 'before'}:
            raise ValueError('prepare schema')
        before = project(request['before'])
        prepared = prepare(request['intention'], before)
        pending = request['intention'], before, prepared
        response = prepared
    else:
        if set(request) != {'execution', 'after'}:
            raise ValueError('consequence schema')
        response = attribute(*pending, request['execution'], project(request['after']))
        pending = None
    print(json.dumps(response, sort_keys=True), flush=True)
