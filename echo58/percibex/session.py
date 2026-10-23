"""Compose frozen flight session through temporary, restored adapter bindings."""
import hashlib
import json
import os
from pathlib import Path
import socket
import time
from echoai.nexus0.pattern1r_v4 import session as original
from .protocol import unpack
from .resources import cleanup_owned_containers


class Forwarder(original.Forwarder):
    instances = []
    live_path = None

    def __init__(self, fifo, sock, marks):
        super().__init__(fifo, sock, marks)
        self.directory = Path(fifo).parent
        self.bridge, self.last_seq = [], 0
        self.instances.append(self)

    def consume(self, buf):
        super().consume(buf)
        request = self.directory/'percibex-request.wsp'
        if not request.exists(): return
        raw = request.read_bytes()
        _, seq, _ = unpack(raw)
        if seq == self.last_seq: return
        if seq != self.last_seq+1: raise ValueError('bridge sequence')
        h = dict(v=1, source='wsp', payload_len=16, payload_sha256=hashlib.sha256(raw).hexdigest())
        hb = json.dumps(h, sort_keys=True, separators=(',', ':')).encode()
        sent = time.monotonic_ns()
        self.sock.sendall(len(hb).to_bytes(4,'big')+hb+(16).to_bytes(4,'big')+raw)
        reply = b''
        self.sock.settimeout(10)
        try:
            while len(reply) < 16:
                chunk = self.sock.recv(16-len(reply))
                if not chunk: raise ValueError('consumer closed during control')
                reply += chunk
        finally:
            self.sock.settimeout(None)
        if unpack(reply)[1] != seq: raise ValueError('bridge response sequence')
        self.bridge.append(dict(after_frames=self.frames, input=raw.hex(), output=reply.hex(),
                                sent_monotonic_ns=sent, received_monotonic_ns=time.monotonic_ns()))
        if self.live_path is not None:
            with Path(self.live_path).open('a') as live:
                live.write(json.dumps(dict(event='observed_wsp_exchange', frames=self.frames,
                                           input=raw.hex(), output=reply.hex(), decoded_reply=unpack(reply)))+'\n')
        dest = self.directory/'percibex-reply.wsp'
        temp = dest.with_suffix('.tmp')
        temp.write_bytes(reply); os.replace(temp, dest)
        self.last_seq = seq


def run_episode(flight, cage, package, config, spec, *, arm, label, root, consumer_path, tap_path):
    saved = original.CONSUMER, original.TAP, original.Forwarder, original.sandbox.spawn, original.subprocess
    cleanup_receipts = []
    def clean(reason):
        receipt = cleanup_owned_containers(reason)
        cleanup_receipts.append(receipt)
        with (root/'operational-cleanup.jsonl').open('a') as out:
            out.write(json.dumps(receipt,sort_keys=True)+'\n')
    class SubprocessProxy:
        def __getattr__(self,name): return getattr(saved[4],name)
        def run(self,*a,**kw):
            try: return saved[4].run(*a,**kw)
            except saved[4].TimeoutExpired:
                clean('flight_subprocess_timeout')
                raise
    def spawn(*a, extra_env=None, **kw):
        return saved[3](*a, extra_env=dict(extra_env or {}, PERCIBEX_ARM=arm), **kw)
    Forwarder.instances = []
    original.CONSUMER, original.TAP, original.Forwarder = consumer_path, tap_path, Forwarder
    original.sandbox.spawn = spawn
    original.subprocess = SubprocessProxy()
    try:
        ep, sensors = original.run_episode(flight, cage, package, config, spec,
                                           condition='nominal', label=label, root=root)
        failed = (not ep.ok or getattr(ep,'metrics',{}).get('container_returncode',0) != 0
                  or sensors.get('consumer_returncode',0) != 0)
        if failed and not cleanup_receipts: clean('flight_returned_failure')
        bridge = Forwarder.instances[-1].bridge if Forwarder.instances else []
        path = root/'bridge.json'
        path.write_text(json.dumps(bridge, sort_keys=True, indent=2)+'\n')
        sensors['bridge'] = str(path)
        sensors['bridge_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        sensors['new_contract'] = 'percibex-live-wsp16-duplex-v1'
        sensors['operational_cleanup'] = cleanup_receipts
        return ep, sensors
    except BaseException:
        if not cleanup_receipts: clean('flight_exception')
        raise
    finally:
        original.CONSUMER, original.TAP, original.Forwarder, original.sandbox.spawn, original.subprocess = saved
