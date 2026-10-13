"""Authenticated restartable accounting above the existing integer Budget.

The supervisor serializes a whole episode (one owner/file lock). Pending usage
is held across restart; it is never silently refunded or assigned a new ID.
"""
from copy import deepcopy
from ..pcworld.accounting import Budget

LIMITS=dict(fuel=400,tokens=25000,llm_calls=24,tools=80,output_tokens=80000,
            patches=8,tests=10,critic_calls=6,cpu_us=1200000000)
STATE=('_limits','_used','_reserved','_pending','_frozen','_overruns','_identity','_sequence')


class DurableBudget(Budget):
    def __init__(self,receipts,limits):
        super().__init__(limits);self.receipts=receipts;self.bindings={}
        records=[r['body'] for r in receipts.records if r['body'].get('event')=='repoworld.budget']
        if records:
            last=records[-1]
            if last['state']['_limits']!=limits: raise ValueError('cannot reassign episode budget')
            for k in STATE: setattr(self,k,deepcopy(last['state'][k]))
            self.bindings=deepcopy(last['bindings'])
        else: self._save('initialize')

    def _save(self,action):
        self.receipts.append(dict(event='repoworld.budget',action=action,
            state={k:deepcopy(getattr(self,k)) for k in STATE},bindings=deepcopy(self.bindings)))

    def reserve(self,request):
        try: return super().reserve(request)
        finally: self._save('reserve')

    def reserve_for(self,key,request):
        if key in self.bindings:
            item=self.bindings[key]
            if item['request']!=request: raise ValueError('request ID reused with different costs')
            if item['ticket'] not in self._pending: raise ValueError('request already settled')
            return item['ticket']
        try:
            ticket=super().reserve(request)
            self.bindings[key]=dict(request=deepcopy(request),ticket=ticket)
            return ticket
        finally: self._save('reserve-bound')

    def settle(self,ticket,actual):
        try: return super().settle(ticket,actual)
        finally: self._save('settle')

    def consume_fuel(self,reason):
        try: return super().consume_fuel(reason)
        finally: self._save('fuel')

    def close_unknown(self,ticket):
        """Charge the reservation after irrecoverable ambiguous local execution."""
        if ticket in self._pending: self.settle(ticket,deepcopy(self._pending[ticket]))

