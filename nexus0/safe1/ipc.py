"""A single bounded request/reply, including partial lines and blocked writes."""
import json
import os
import select
import subprocess
import time


class ChannelError(RuntimeError):
    pass


class Channel:
    def __init__(self, argv):
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, bufsize=0)
        os.set_blocking(self.process.stdin.fileno(), False)
        os.set_blocking(self.process.stdout.fileno(), False)
        self.sequence = 0
        self.failed = False

    def call(self, wsp):
        if self.failed:
            raise ChannelError('channel_closed')
        if type(wsp) is not str or len(wsp) != 32:
            self.failed = True
            raise ChannelError('request_size')
        self.sequence += 1
        payload = json.dumps(dict(seq=self.sequence, wsp=wsp)).encode()+b'\n'
        deadline = time.monotonic_ns()+200_000_000
        received = bytearray()
        try:
            while payload or b'\n' not in received:
                remaining = deadline-time.monotonic_ns()
                if remaining <= 0:
                    raise ChannelError('timeout')
                readable, writable, _ = select.select(
                    [] if payload else [self.process.stdout], [self.process.stdin] if payload else [], [], remaining/1e9)
                if writable:
                    payload = payload[os.write(self.process.stdin.fileno(), payload):]
                if readable:
                    data = os.read(self.process.stdout.fileno(), 4097-len(received))
                    if not data:
                        raise ChannelError('eof')
                    received.extend(data)
                    if len(received) > 4096:
                        raise ChannelError('oversize')
            if time.monotonic_ns() > deadline:
                raise ChannelError('timeout')
            value = json.loads(received)
            if (type(value) is not dict or set(value) != {'seq', 'wsp'}
                    or type(value['seq']) is not int or value['seq'] != self.sequence
                    or type(value['wsp']) is not str or len(value['wsp']) != 32):
                raise ChannelError('reply_schema')
            return value
        except (OSError, ValueError, ChannelError) as exc:
            self.failed = True
            raise ChannelError(str(exc)) from exc

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()
