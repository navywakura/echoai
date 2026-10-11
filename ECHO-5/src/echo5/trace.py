"""Passive adapter to the existing ARC Journal, with envelope protection."""

import hashlib
import json
from pathlib import Path

from .legacy import module

RESERVED = frozenset(('schema', 'index', 'time', 'prev', 'hash', 'agent'))


class Recorder:
    def __init__(self, path):
        self._journal = module('echo_arc.observe').Journal(path)

    def write(self, **event):
        if RESERVED.intersection(event):
            raise ValueError('journal envelope is owned by the recorder')
        if not isinstance(event.get('kind'), str) or not event['kind']:
            raise ValueError('a factual event kind is required')
        # Reject nonportable NaNs before they enter the inherited recorder.
        json.dumps(event, allow_nan=False)
        self._journal.write(agent='echo5', **event)

    def close(self):
        self._journal.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def verify_journal(path):
    previous = '0' * 64
    count = 0
    for index, line in enumerate(Path(path).read_text(encoding='utf-8').splitlines()):
        row = json.loads(line)
        claimed = row.pop('hash', None)
        if (row.get('schema') != 'echo45-arc-decisions-v1' or
                type(row.get('index')) is not int or row['index'] != index or
                row.get('prev') != previous or row.get('agent') != 'echo5'):
            raise ValueError('invalid journal envelope or chain')
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False)
        actual = hashlib.sha256(raw.encode()).hexdigest()
        if actual != claimed:
            raise ValueError('journal hash mismatch')
        previous = actual
        count += 1
    return {'events': count, 'last_hash': previous}
