"""Integer source/sign/context authority. No reward, CAM fact or actuator API."""
from echoai.core.wsp import pack
from echoai.nexus0.cause1.core import decode as decode_motion

TTL = 250_000_000


def integer(value, low=0, high=2**63-1):
    return type(value) is int and low <= value <= high


def signal(symbol, incoming=True):
    if not integer(symbol, 0, 4) or type(incoming) is not bool:
        raise ValueError('symbol')
    return pack(src=3 if incoming else 2, rel=(16 if incoming else 15) if symbol else 14,
                dst=2 if incoming else 3, domain=9, generator=8, style=symbol).hex()


def decode_signal(packet):
    if type(packet) is not str or len(packet) != 32:
        raise ValueError('sign')
    raw = bytes.fromhex(packet)
    symbol = raw[13]
    if not 1 <= symbol <= 4 or signal(symbol) != packet:
        raise ValueError('noncanonical sign')
    return symbol


def position(value):
    return type(value) is list and len(value) == 3 and all(integer(v, -10000, 10000) for v in value)


def extract(value):
    return 'position_mm='+','.join(str(x) for x in value)


class Host:
    def __init__(self, policy='consequence'):
        if policy not in ('consequence', 'button'):
            raise ValueError('policy')
        self.policy = policy
        self.bits = [0]*512
        self.counts = [0]*512
        self.last_seq = [-1]*8
        self.pending = None
        self.last_now = -1
        self.last_comm = -1_000_000_000
        self.communication_spent = 0

    def key(self, source, sign, context):
        if not integer(source, 0, 7) or not integer(context, 0, 15):
            raise ValueError('source/context')
        symbol = decode_signal(sign)
        return source*64+(symbol-1)*16+context

    def _clock(self, now):
        if not integer(now) or now < self.last_now:
            return False
        self.last_now = now
        return True

    def _update(self, key, success):
        self.bits[key] = ((self.bits[key] << 1) | int(success)) & 255
        self.counts[key] = min(8, self.counts[key]+1)

    def authority(self, source, sign, context):
        key = self.key(source, sign, context)
        n = self.counts[key]
        hits = self.bits[key].bit_count()
        return dict(n=n, hits=hits, score=256*hits//n if n else 0,
                    trusted=n >= 4 and hits*4 >= n*3)

    def publish(self, claim, now):
        if not self._clock(now) or self.pending is not None:
            return False
        if type(claim) is not dict or set(claim) != {'source', 'sign', 'context', 'seq', 'wsp', 'target_mm', 'published_ns'}:
            return False
        try:
            key = self.key(claim['source'], claim['sign'], claim['context'])
            action = decode_motion(claim['wsp'])
        except (ValueError, TypeError, IndexError):
            return False
        if (action not in (0, 1) or not position(claim['target_mm']) or not integer(claim['seq'])
                or claim['seq'] <= self.last_seq[claim['source']] or not integer(claim['published_ns'])
                or not 0 <= now-claim['published_ns'] <= TTL):
            return False
        self.last_seq[claim['source']] = claim['seq']
        self.pending = dict(claim, target_mm=list(claim['target_mm']), key=key)
        if self.policy == 'button':
            self._update(key, True)
        return True

    def cancel(self):
        self.pending = None  # Missing outcomes are unknown, never negative rewards.

    def observe(self, receipt, now):
        if not self._clock(now) or self.pending is None:
            return dict(updated=False, outcome='unknown')
        p = self.pending
        keys = {'seq', 'wsp', 'ack_ns', 'after_ns', 'received_ns', 'accepted', 'complete', 'position_mm', 'extract'}
        if (type(receipt) is not dict or set(receipt) != keys
                or not integer(receipt['seq']) or receipt['seq'] != p['seq'] or receipt['wsp'] != p['wsp']
                or any(not integer(receipt[k]) for k in ('ack_ns', 'after_ns', 'received_ns'))
                or not p['published_ns'] < receipt['ack_ns'] < receipt['after_ns'] <= receipt['received_ns'] <= now
                or receipt['after_ns']-p['published_ns'] > 15_000_000_000
                or now-receipt['after_ns'] > TTL
                or receipt['accepted'] is not True or receipt['complete'] is not True
                or not position(receipt['position_mm']) or receipt['extract'] != extract(receipt['position_mm'])):
            return dict(updated=False, outcome='unknown')
        success = sum((a-b)**2 for a, b in zip(p['target_mm'], receipt['position_mm'])) <= 350**2
        if self.policy == 'consequence':
            self._update(p['key'], success)
        self.pending = None
        return dict(updated=self.policy == 'consequence', outcome='confirmed' if success else 'contradicted')

    def choose(self, sources, sign, context):
        if (type(sources) is not list or not 1 <= len(sources) <= 8
                or any(not integer(s, 0, 7) for s in sources) or len(set(sources)) != len(sources)):
            raise ValueError('offers')
        candidates = [(self.authority(s, sign, context), s) for s in sources]
        candidates = [(v['score'], -s, s) for v, s in candidates if v['trusted']]
        return max(candidates)[2] if candidates else None

    def communicate(self, request):
        keys = {'now_ns', 'symbol', 'opportunity', 'budget', 'reserve', 'busy', 'safe', 'flight'}
        silence = dict(channel='silence', wsp=signal(0, False), cost=0)
        if (type(request) is not dict or set(request) != keys
                or not integer(request['symbol'], 0, 4) or not integer(request['budget'])
                or not integer(request['reserve'], 40) or any(type(request[k]) is not bool for k in ('opportunity', 'busy', 'safe'))
                or not self._clock(request['now_ns'])):
            return dict(silence, reason='schema_or_clock')
        if not request['safe']:
            return dict(silence, reason='safety')
        if request['flight'] is not None:
            try:
                decode_motion(request['flight'])
            except (ValueError, TypeError, IndexError):
                return dict(silence, reason='invalid_flight')
            return dict(channel='flight_candidate', wsp=request['flight'], cost=0, reason='flight_priority')
        now = request['now_ns']
        if (request['busy'] or not request['opportunity'] or request['symbol'] == 0
                or request['budget']-self.communication_spent-request['reserve'] < 2 or now-self.last_comm < 1_000_000_000):
            return dict(silence, reason='communication_gate')
        self.last_comm = now
        self.communication_spent += 2
        return dict(channel='communication', wsp=signal(request['symbol'], False), cost=2, reason='opportunity')

    def snapshot(self):
        return dict(bits=list(self.bits), counts=list(self.counts), last_seq=list(self.last_seq),
                    pending=None if self.pending is None else dict(self.pending, target_mm=list(self.pending['target_mm'])),
                    communication_spent=self.communication_spent)
