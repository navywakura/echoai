"""Isolated consumer: observations in, one causal WSP plus diagnostics out."""
import json
import sys
sys.path.insert(0, '/agent')
from echoai.core.wsp import pack
from echoai.nexus0.compose1_v2.controller import Composer
from echoai.nexus0.compose1_v2.perception import project, grid

agent = None
energy = 240
inspection = 0
previous = None
for line in sys.stdin:
    if len(line) > 2_000_000:
        raise ValueError('message size')
    request = json.loads(line)
    if agent is None:
        if set(request) != {'model', 'goal', 'mode', 'energy'}:
            raise ValueError('initialization schema')
        energy = request.pop('energy')
        if type(energy) is not int or not 10 <= energy <= 240:
            raise ValueError('energy range')
        agent = Composer(**request)
        print(json.dumps(dict(ready=True, spatial_cells=0,
                              model_sha256=agent.model.fingerprint())), flush=True)
        continue
    if 'estimate' in request:
        if previous:
            energy -= 4 if previous[1] == 11 else 1
        frame = project(request, energy)
        if grid(request['estimate']['position_mm']) == agent.goal and not frame['station_observed']:
            agent.update(frame)
            if inspection < 4:
                w = pack(src=2, rel=14, dst=5, time=8, E={}, domain=9,
                         generator=8, style=7+inspection)
                inspection += 1
                response = dict(wsp=w.hex(), status='inspect_target', plan=[], depth=0,
                                candidates=0, model_sha256=agent.model.fingerprint())
            else:
                response = agent.output(6, [], 'target_unverified', 0)
        else:
            response = agent.decide(frame)
        response['frame'] = frame
    else:
        response = agent.decide(request)
    previous = bytes.fromhex(response['wsp'])
    print(json.dumps(response, sort_keys=True), flush=True)
