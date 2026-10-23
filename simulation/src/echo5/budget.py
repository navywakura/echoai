"""Deterministic logical work ledger; reservations precede the operation."""


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, limit):
        if type(limit) is not int or limit < 0:
            raise ValueError('limit must be a nonnegative integer')
        self.limit = limit
        self.used = 0
        self.counts = {}

    @property
    def remaining(self):
        return self.limit - self.used

    def consume(self, kind, amount=1):
        if not isinstance(kind, str) or not kind or type(amount) is not int or amount < 0:
            raise ValueError('work requires a name and nonnegative integer units')
        if amount > self.remaining:
            raise BudgetExceeded(f'{kind}: {amount} requested, {self.remaining} remaining')
        self.used += amount
        self.counts[kind] = self.counts.get(kind, 0) + amount

    add = consume

    def snapshot(self):
        return {'limit': self.limit, 'used': self.used, 'remaining': self.remaining,
                'counts': dict(sorted(self.counts.items()))}
