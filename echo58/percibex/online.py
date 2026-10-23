"""Live integer recognition and identity-indexed inspection memory.

No pose, world, object label or route enters these interfaces.
"""
from echoai.nexus0.pattern1r_v4.memory import AbstainingPatternMemory
from echoai.echo58.memx.memory import Memory
from .protocol import SCHOOL, FREEZE, TICK, RECEIPT, ACK, ACTION, INSPECT, packet, unpack, family_key


class Online:
    def __init__(self, arm='MEMX', min_hits=32):
        if arm not in ('MEMX', 'EMPTY', 'VISITS'): raise ValueError('arm')
        self.arm = arm
        self.pattern = AbstainingPatternMemory(min_hits=min_hits)
        self.memory = Memory()
        self.mode = 'idle'
        self.last_seq = self.tick_n = 0
        self.now = 0
        self.visible = {}
        self.visits = {}
        self.pending = None
        self.events, self.controls, self.decisions = [], [], []
        self.frozen_pattern = self.frozen_memory = None

    def sighting(self, capture_ns, signature, frame=0):
        self.now = max(self.now, capture_ns)
        trained = self.mode == 'school'
        if trained: self.pattern.observe(signature, 0)
        pred = self.pattern.predict(signature)
        family = pred[0] if pred else None
        if family is not None: self.visible[family] = capture_ns
        self.events.append(dict(frame=frame, capture=capture_ns, signature=signature,
                                family=family, trained=trained, observations=self.pattern.observations))

    def control(self, raw):
        op, seq, value = unpack(raw)
        if seq != self.last_seq+1: raise ValueError('nonconsecutive control')
        reply = packet(ACK, seq)
        if op == SCHOOL:
            if self.mode != 'idle' or self.pending: raise ValueError('school phase')
            self.mode = 'school'
        elif op == FREEZE:
            if self.mode != 'school' or self.pending: raise ValueError('freeze phase')
            self.mode = 'exam'
            self.frozen_pattern = self.pattern.snapshot_hash()
            self.frozen_memory = self.memory.head
        elif op == TICK:
            if self.mode == 'idle' or self.pending: raise ValueError('opportunity')
            families = sorted(f for f, t in self.visible.items() if self.now-t <= 1_000_000_000)
            f = families[self.tick_n % len(families)] if families else None
            self.tick_n += 1
            key = family_key(f) if f is not None else None
            recall = self.memory.recall(*key, 'TOGGLE', 0) if key else None
            visits = self.visits.get(f, 0)
            inspect = f is not None and not ((self.arm == 'MEMX' and recall == 'PASS') or
                                             (self.arm == 'VISITS' and visits >= 3))
            if inspect:
                self.pending = f
                self.visits[f] = visits+1
            reply = packet(ACTION, seq, int(inspect))
            self.decisions.append(dict(seq=seq, mode=self.mode, family=f, key=list(key) if key else None,
                                       recall=recall, visits=visits, action=int(inspect),
                                       observations=self.pattern.observations, memory_head=self.memory.head))
        elif op == RECEIPT:
            if self.pending is None: raise ValueError('unsolicited receipt')
            if self.mode == 'school':
                self.memory.observe(*family_key(self.pending), 'TOGGLE', 0, 'PASS' if value else 'NOOP')
            self.pending = None
        else:
            raise ValueError('input opcode')
        self.last_seq = seq
        self.controls.append(dict(input=raw.hex(), output=reply.hex(), events=len(self.events),
                                  observations=self.pattern.observations, mode=self.mode))
        return reply

    def report(self):
        return dict(arm=self.arm, mode=self.mode, events=self.events, controls=self.controls,
                    decisions=self.decisions, pattern_hash=self.pattern.snapshot_hash(),
                    frozen_pattern=self.frozen_pattern, memory_head=self.memory.head,
                    frozen_memory=self.frozen_memory, memory_records=self.memory.records,
                    prototype=self.pattern.prototype[:self.pattern.size],
                    hits=self.pattern.hits[:self.pattern.size], observations=self.pattern.observations,
                    destroyed=self.memory.destroyed, cortex_calls=0, pending=self.pending)
