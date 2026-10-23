"""A provisional alarm is testimony, never a new private fact."""
from ..enjambre2.memory import Reader as C2Reader
from ..enjambre2.transport import BAD
from ..enjambre.team import RM, L1, L2
from ..memx.memory import OUTCOMES


def variant(arm):
    if arm.startswith(('v3_n', 'sin_alarma_n', 'sin_liberacion_n')):
        n = int(arm.rsplit('n', 1)[1])
        if n not in (1, 2, 3):
            raise ValueError('unregistered candidate threshold')
        return n
    return None


class Reader(C2Reader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_min = variant(self.arm)
        self.provisional_requests = set()

    def entries(self, layer, key, remove_altered=False):
        entries = self._sources(layer, key, remove_altered)
        return {a: c for a, c in entries.items() if a != self.me
                and c[1] >= self.n_min and c[1] * 100 >= 85 * c[2]
                and self.trust.credible(a)}

    def provisional(self, layer, key, remove_altered=False):
        if self.n_min is None or layer == RM:
            return False
        entries = self.entries(layer, key, remove_altered)
        return sum(OUTCOMES[c[0]] in BAD for c in entries.values()) == 1

    def resolve(self, layer, key, remove_altered=False):
        if self.n_min is None:
            return super().resolve(layer, key, remove_altered)
        entries = self.entries(layer, key, remove_altered)
        if not entries:
            return None
        if layer == RM:
            return 'LINK' if len(entries) >= 2 else None
        outcomes = {OUTCOMES[c[0]] for c in entries.values()}
        if outcomes & BAD:
            if self.arm.startswith('sin_alarma_') and self.provisional(layer, key, remove_altered):
                return None
            return 'HURT'
        return next(iter(outcomes)) if len(outcomes) == 1 else None

    def recall(self, ident, sig, act, hand):
        before = self.by_source['global']
        out = super().recall(ident, sig, act, hand)
        request = (ident, act, hand)
        self.provisional_requests.discard(request)
        if (out == 'HURT' and self.by_source['global'] > before
                and self.n_min is not None and not self.arm.startswith('sin_liberacion_')):
            memory_layer, key = self.last
            layer = L1 if memory_layer == 1 else L2
            if self.provisional(layer, key):
                self.provisional_requests.add(request)
        return out
