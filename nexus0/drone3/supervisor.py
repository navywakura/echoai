"""SAFE-1's supervisor over the cell gateway, with the two DRONE-3 gates.

SAFE-1's `check`, `trip` and `acknowledge` run unchanged: LiDAR freshness, the
agent's liveness, PX4 link/authority/failsafe, execution faults and the latch.
Only construction and submission differ: the gateway is the cell adapter and
every translation must first pass the epistemic and energy gates, computed
here from the recorded public inputs. Any refusal latches: the agent proposes
only admitted, affordable goals, so a refusal means something is wrong.
There is no recovery path and no direct actuator authority.
"""
from echoai.nexus0.safe1.core import Lease, Supervisor
from . import contract as c
from . import gates
from .gateway import CellGateway

__all__ = ['Lease', 'MissionSupervisor']


class MissionSupervisor(Supervisor):
    def __init__(self, model_snapshot, offset, home, system=1, component=1, *, mutant=''):
        if mutant not in ('', 'no_latch', 'no_epistemic', 'no_energy', 'no_liveness'):
            raise ValueError('mutant')
        self.gateway = CellGateway(system, component)
        self.power = None
        self.tripped = False
        self.reason = None
        self.last_now = -1
        self.model = model_snapshot
        self.offset = list(offset)
        self.home = tuple(home)
        self.visited = [tuple(home)]
        self.mutant = mutant

    def trip(self, reason):
        if self.mutant == 'no_latch':
            self.reason = reason
            return False
        return super().trip(reason)

    def check(self, health):
        if self.mutant == 'no_liveness' and type(health) is dict:
            health = dict(health, worker_alive=True)
        ok = super().check(health)
        if self.mutant == 'no_latch':
            self.tripped = False
        return ok

    def occupied(self, cell):
        cell = tuple(cell)
        if cell not in self.visited:
            self.visited.append(cell)

    def submit(self, request, health, evidence):
        """Returns the gateway decision plus every gate's record, in order."""
        record = dict(health=None, epistemic=None, energy=None, gateway=None)
        if not self.check(health):
            record['health'] = dict(allowed=False, reason=self.reason)
            return dict(allowed=False, reason=self.reason, gates=record)
        record['health'] = dict(allowed=True)
        now = health['now_ns']
        try:
            kind, style = c.intention(request['wsp'])
            position = health['frame']['position_mm']
            cell = c.grid(position)
            target = (cell[0]+c.VECTORS[style][0], cell[1]+c.VECTORS[style][1]) if kind == 'move' else cell
        except (ValueError, KeyError, TypeError):
            self.trip('proposal_rejected')
            return dict(allowed=False, reason=self.reason, gates=record)
        record['epistemic'] = gates.epistemic(evidence['frame'], kind, target, now, self.offset,
                                              mutant='admit_unknown' if self.mutant == 'no_epistemic' else '')
        if not record['epistemic']['allowed']:
            self.trip('epistemic_block')
            return dict(allowed=False, reason=self.reason, gates=record)
        if self.mutant == 'no_energy':
            record['energy'] = dict(allowed=True, reason='mutant_no_energy')
        else:
            record['energy'] = gates.energy(self.model, evidence['battery'], now, self.visited,
                                            target, self.home)
        if not record['energy']['allowed']:
            self.trip('energy_block')
            return dict(allowed=False, reason=self.reason, gates=record)
        decision = self.gateway.propose(request, health['frame'], now)
        record['gateway'] = decision
        if not decision['allowed']:
            self.trip('proposal_rejected')
            return dict(allowed=False, reason=self.reason, gates=record)
        return dict(decision, gates=record)
