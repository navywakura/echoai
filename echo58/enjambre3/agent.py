"""Common action receipts; the only policy change is verify of a provisional alarm."""
from ..enjambre.cagent import CAgent


class Agent(CAgent):
    def run(self, *args, **kwargs):
        self.action_receipts = []
        self.release_queries = 0
        out = super().run(*args, **kwargs)
        out['actions'] = self.action_receipts
        out['release_queries'] = self.release_queries
        return out

    def _believed(self, ident, act, hand, verify):
        out = super()._believed(ident, act, hand, verify)
        key = (ident, act, hand)
        if (verify and out == 'HURT' and key not in self.E
                and key in self.source.provisional_requests):
            self.release_queries += 1
            return None
        return out

    def _outcome(self, old, new, intent):
        act, cell, ident, hand, sig = intent
        prior = self.belief(ident, act, hand)
        provisional = (prior == 'HURT' and (ident, act, hand) not in self.E
                       and (ident, act, hand) in self.source.provisional_requests)
        out = super()._outcome(old, new, intent)
        self.action_receipts.append({'step': self.steps_n, 'act': act, 'cell': list(cell),
            'ident': ident, 'sig': sig, 'hand': hand, 'prior': prior,
            'provisional_alarm': provisional, 'outcome': out})
        return out
