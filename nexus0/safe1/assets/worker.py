"""Experimental intention fixture, with explicit process/IPC fault variants."""
import json
import os
import signal
import sys
import time

mode = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    if mode == 'exit':
        sys.exit(7)
    if mode == 'hang':
        os.kill(os.getpid(), signal.SIGSTOP)
    if mode == 'partial':
        sys.stdout.write('{')
        sys.stdout.flush()
        time.sleep(60)
    elif mode == 'oversize':
        print('x'*5000, flush=True)
    else:
        if mode == 'bad':
            request['wsp'] = 'ff'*16
        if mode == 'sequence':
            request['seq'] += 1
        print(json.dumps(request), flush=True)
