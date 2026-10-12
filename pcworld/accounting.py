"""Atomic, integer-only accounting for one supervisor's shared task budget.

All specialists must share the same Budget object. A process-wide lock covers
every check and mutation; this is an in-memory ledger, not a cross-process RPC.
The supervisor supplies totals including retries, failed calls and parsing work.

``reserve(request)`` spends one fuel unit *before* validation. An accepted
request's ``fuel`` is prepaid as max(1, requested fuel); other dimensions are
held at their requested maxima. Failed requests spend only the attempt's unit.
``consume_fuel(reason)`` charges controller steps which do not reserve work.
``settle(ticket, actual)`` never refunds fuel and remains possible after fuel
exhaustion or an overrun. Omitted actual dimensions cost zero, except prepaid
fuel. Actual fuel above the prepayment adds the difference. Do not include fuel
already charged separately by consume_fuel in that ticket's actual fuel.

Any actual cost above its ticket's maximum (including an unbudgeted dimension)
is fully recorded, the ticket is closed, and BudgetExceeded is raised *after*
permanently freezing reservations. Remaining balances may then be negative.
Invalid amounts raise ValueError and keep a settlement ticket open for repair.
"""

from copy import deepcopy
from threading import RLock
from uuid import uuid4


_LOCK = RLock()


class BudgetExceeded(RuntimeError):
    """Work is refused, or recorded actual usage breached its reservation."""


def _amounts(value: dict[str, int]) -> dict[str, int]:
    if type(value) is not dict:
        raise ValueError('costs must be a dict of nonnegative integers')
    result = value.copy()
    for name, amount in result.items():
        if type(name) is not str or not name:
            raise ValueError('resource names must be nonempty strings')
        if type(amount) is not int or amount < 0:
            raise ValueError(f'{name}: expected a nonnegative integer (not bool)')
    return result


class Budget:
    """One task's fixed quotas; tickets are opaque, single-use strings."""

    def __init__(self, limits: dict[str, int]):
        self._limits = _amounts(limits)
        if 'fuel' not in self._limits:
            raise ValueError('an explicit fuel limit is required')
        self._used = dict.fromkeys(self._limits, 0)
        self._reserved = dict.fromkeys(self._limits, 0)
        self._pending: dict[str, dict[str, int]] = {}
        self._frozen = False
        self._overruns: list[dict] = []
        self._identity = uuid4().hex
        self._sequence = 0

    def _burn(self) -> None:
        # Caller holds _LOCK. Exhausted attempts cannot make natural-number
        # fuel negative; actual overruns are recorded separately in settle.
        if self._used['fuel'] >= self._limits['fuel']:
            raise BudgetExceeded('fuel exhausted')
        self._used['fuel'] += 1

    def reserve(self, request: dict[str, int]) -> str:
        """Charge attempt fuel and atomically hold all requested maxima."""
        with _LOCK:
            self._burn()
            if self._frozen:
                raise BudgetExceeded('budget frozen after an actual-cost overrun')
            request = _amounts(request)
            unknown = request.keys() - self._limits.keys()
            if unknown:
                raise ValueError(f'unbudgeted resources: {sorted(unknown)}')
            fuel = max(1, request.get('fuel', 0))
            if self._used['fuel'] + fuel - 1 > self._limits['fuel']:
                raise BudgetExceeded('fuel reservation exceeds remaining budget')
            for name, amount in request.items():
                if name != 'fuel' and self._used[name] + self._reserved[name] + amount > self._limits[name]:
                    raise BudgetExceeded(f'{name} reservation exceeds remaining budget')
            request['fuel'] = fuel
            self._used['fuel'] += fuel - 1
            for name, amount in request.items():
                if name != 'fuel':
                    self._reserved[name] += amount
            self._sequence += 1
            ticket = f'{self._identity}:{self._sequence}'
            self._pending[ticket] = request
            return ticket

    def settle(self, ticket: str, actual: dict[str, int]) -> None:
        """Close a ticket and charge its entire actual cost, even on overrun."""
        with _LOCK:
            if type(ticket) is not str or ticket not in self._pending:
                raise ValueError('unknown or already settled ticket')
            actual = _amounts(actual)
            request = self._pending[ticket]
            exceeded = sorted(name for name, amount in actual.items()
                              if name not in self._limits or amount > request.get(name, 0))
            # Validate the entire input before releasing any reservation. Once
            # valid, record every dimension before raising about an overrun.
            for name, amount in request.items():
                if name != 'fuel':
                    self._reserved[name] -= amount
            for name, amount in actual.items():
                if name == 'fuel':
                    self._used[name] += max(0, amount - request['fuel'])
                else:
                    self._used[name] = self._used.get(name, 0) + amount
                    self._reserved.setdefault(name, 0)
            del self._pending[ticket]
            if exceeded:
                self._frozen = True
                self._overruns.append({'ticket': ticket, 'request': request,
                                       'actual': actual, 'resources': exceeded})
                raise BudgetExceeded(f'actual overrun recorded; budget frozen: {exceeded}')

    def consume_fuel(self, reason: str) -> None:
        """Charge a controller transition, including an invalid reason."""
        with _LOCK:
            self._burn()
            if type(reason) is not str or not reason.strip():
                raise ValueError('fuel reason must be a nonempty string')

    def report(self) -> dict:
        """Return a detached atomic snapshot.

        limits/used/reserved/remaining map resource names to ints; pending is
        the open-ticket count, frozen is bool, overruns lists recorded breaches.
        Unbudgeted actual resources have a zero effective limit in remaining.
        Fuel is charged directly in used and is always zero in reserved.
        """
        with _LOCK:
            return {
                'limits': self._limits.copy(),
                'used': self._used.copy(),
                'reserved': self._reserved.copy(),
                'remaining': {name: self._limits.get(name, 0) - used - self._reserved[name]
                              for name, used in self._used.items()},
                'pending': len(self._pending),
                'frozen': self._frozen,
                'overruns': deepcopy(self._overruns),
            }
