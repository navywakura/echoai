"""Only public claims and already observed receipts cross the existing cage wire."""
import json
import sys
sys.path.insert(0, '/agent')
from echoai.nexus0.host1.core import Host

agent = None
allowed = {'authority', 'publish', 'observe', 'choose', 'communicate', 'snapshot', 'cancel'}
for line in sys.stdin:
    if len(line) > 20000:
        raise ValueError('request size')
    message = json.loads(line)
    if set(message) == {'op', 'policy'} and message['op'] == 'init':
        agent = Host(message['policy'])
        response = dict(ready=True)
    elif agent is not None and set(message) == {'op', 'args'} and message['op'] in allowed:
        response = getattr(agent, message['op'])(*message['args'])
    else:
        raise ValueError('public schema')
    print(json.dumps(response, sort_keys=True), flush=True)
