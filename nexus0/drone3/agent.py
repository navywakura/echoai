"""The caged DRONE-3 agent: public observations in, one WSP plus a published
prediction and its reasons out. No simulator, world, seed, map or name.

Composition is COMPOSE-1 v4's frozen controller (compose1_v3). Perception is its
frozen projection; FUSION-1 keeps the evidence; the C1 calibration re-registers
the camera; POWER-1's Guard decides continue/return/land from the simulated
battery, and the same energy arithmetic the supervisor uses bounds each step.
COMPOSE's own abstract energy counter is neutralised (constant 240): energy is
POWER's job here. Returning follows cells the body has occupied, re-verified
by fresh evidence at every step. Attributions are hypotheses: no CAM writes.
"""
from echoai.nexus0.compose1_v3.controller import Composer
from echoai.nexus0.compose1_v3.perception import project
from echoai.nexus0.fusion1.core import unpack
from echoai.nexus0.fusion1.integration import admit
from echoai.nexus0.power1.core import Guard
from . import contract as c
from . import gates
from .calibration import check_offset, reregister
from .energy import battery_sample, guard_frame

NEUTRAL_ENERGY = 240
RAW_KEYS = {'now_ns', 'estimate', 'lidar', 'depth', 'rgb', 'battery'}
MODES = ('echo32', 'one_step', 'q', 'ignore_evidence')


class MissionAgent:
    def __init__(self, model, goal, offset, power_model, mode='echo32', power_policy='cost'):
        if mode not in MODES:
            raise ValueError('mode')
        self.composer = Composer(model, goal, mode)
        self.goal = tuple(self.composer.goal)
        self.offset = check_offset(list(offset))
        self.power_model = power_model
        self.guard = Guard(power_model, power_policy)
        self.home = None
        self.visited = []
        self.reached = False
        self.returning = False
        self.return_reason = None
        self.stopped = None
        self.inspections = 0
        self.previous = None
        self.previous_values = {}
        self.admitted = set()
        self.turn = 0

    # -- helpers -----------------------------------------------------------
    def fingerprint(self):
        return self.composer.model.fingerprint()

    def values(self):
        return {p: unpack(w)[0] for p, w in self.composer.beliefs.items()}

    def admitted_now(self):
        return {p for p, w in self.composer.beliefs.items() if admit(w)[0] == 0}

    def attribution(self, pos, values, lost=()):
        if self.previous is None:
            return dict(label='none', own='no_prior_act', external_cells=[], lost_admission=[],
                        has_fact=False, cam_writes=0)
        kind, predicted, before = self.previous
        if kind == 'move':
            own = 'confirmed' if pos == predicted else 'not_confirmed'
        elif kind == 'inspect':
            own = 'held' if pos == before else 'displaced'
        else:
            own = 'none'
        external = sorted([list(p) for p, v in values.items()
                           if p in self.previous_values and v != -1 and self.previous_values[p] != -1
                           and v != self.previous_values[p] and p[:2] not in (pos[:2], before[:2])])
        lost = sorted([list(p) for p in lost if p[:2] not in (pos[:2], before[:2])])
        moved = own == 'confirmed'
        changed = bool(external or lost)
        label = ('both' if moved and changed else 'self' if moved else
                 'external' if changed else 'none')
        return dict(label=label, own=own, external_cells=external, lost_admission=lost,
                    has_fact=False, cam_writes=0)

    def respond(self, wsp, prediction, status, kind, **extra):
        self.previous = (kind, tuple(prediction), tuple(self.pos))
        a = self.composer
        return dict(wsp=wsp, prediction=list(prediction), status=status, turn=self.turn,
                    model_sha256=self.fingerprint(), imagined_writes=a.imagined_writes,
                    revisions=a.revisions, prediction_errors=a.prediction_errors,
                    plan_invalidations=a.plan_invalidations, spatial_cells=len(a.cells),
                    cam_used=a.model.cam.used, cam_destroyed=a.model.cam.destroyed,
                    reached=self.reached, returning=self.returning,
                    return_reason=self.return_reason, **extra)

    def stop(self, status, **extra):
        self.stopped = status
        out = self.composer.output(6, [], status, 0)
        return self.respond(out['wsp'], self.pos, status, 'stop', **extra)

    def back_route(self):
        """First action and length of the shortest route home over occupied cells."""
        from collections import deque
        known = {tuple(v) for v in self.visited}
        start, home = tuple(self.pos[:2]), tuple(self.home[:2])
        queue, seen = deque([(start, [])]), {start}
        while queue:
            node, path = queue.popleft()
            if node == home:
                return path
            for action, (dx, dy) in c.VECTORS.items():
                nxt = (node[0]+dx, node[1]+dy)
                if nxt in known and nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, path+[action]))
        return None

    def begin_return(self, reason):
        if not self.returning:
            self.returning = True
            self.return_reason = reason
            self.composer.pending = []

    # -- one observation -----------------------------------------------------
    def decide(self, raw):
        if type(raw) is not dict or set(raw) != RAW_KEYS:
            raise ValueError('private or missing raw field')
        self.turn += 1
        battery = battery_sample(raw['battery'])
        frame = project({k: v for k, v in raw.items() if k != 'battery'}, NEUTRAL_ENERGY)
        frame = reregister(frame, self.offset)
        now = frame['now_ns']
        self.pos = tuple(frame['odometry'])
        if self.home is None:
            self.home = self.pos
        cell = self.pos[:2]
        if cell not in self.visited:
            self.visited.append(cell)
        if self.stopped:
            self.composer.update(frame)
            return self.stop(self.stopped, power=None, energy_check=None,
                             attribution=self.attribution(self.pos, self.values()))
        before_admitted = self.admitted
        self.composer.update(frame)
        self.composer.turns += 1
        values = self.values()
        self.admitted = self.admitted_now()
        in_view = {tuple(cell['position']) for cell in frame['cells']}
        lost = [p for p in before_admitted if p in in_view and p not in self.admitted]
        attribution = self.attribution(self.pos, values, lost)
        self.previous_values = values
        route = self.back_route()
        power = None
        if battery is None:
            return self.stop('battery_unknown', power=None, energy_check=None, attribution=attribution)
        power = self.guard.decide(guard_frame(now, battery, cell, self.goal[:2], self.home[:2],
                                              None if route is None else len(route), self.reached))
        common = dict(power=power, attribution=attribution)
        if power['reason'] in ('land_home', 'land_local'):
            return self.stop(power['reason'], energy_check=None, **common)
        if power['reason'] not in ('continue', 'return'):
            return self.stop('power_'+power['reason'], energy_check=None, **common)
        if power['reason'] == 'return' and not self.reached:
            self.begin_return('power_mission_infeasible')
        if not self.returning:
            if cell == self.goal[:2]:
                if frame['station_observed']:
                    self.reached = True
                    self.begin_return('goal_reached')
                elif self.inspections < 4:
                    check = gates.energy(self.power_model, battery, now, self.visited, cell, self.home[:2])
                    if not check['allowed']:
                        self.begin_return('return_reserve')
                    else:
                        wsp = c.inspect_wsp(self.inspections)
                        self.inspections += 1
                        self.composer.last_prediction = self.pos
                        return self.respond(wsp, self.pos, 'inspect_target', 'inspect',
                                            energy_check=check, plan=[], candidates=0, **common)
                else:
                    self.begin_return('target_unverified')
            else:
                proposal = self._compose(frame)
                status = proposal['status']
                if status == 'moving':
                    nxt = tuple(proposal['prediction'][:2])
                    check = gates.energy(self.power_model, battery, now, self.visited, nxt, self.home[:2])
                    if check['allowed']:
                        return self.respond(proposal['wsp'], proposal['prediction'], 'moving', 'move',
                                            energy_check=check, plan=proposal['plan'],
                                            candidates=proposal['candidates'], **common)
                    self.begin_return('return_reserve')
                else:
                    self.begin_return('compose_'+status)
        # Returning: occupied cells only, each step re-verified and bounded.
        if cell == self.home[:2]:
            return self.stop('home_after_goal' if self.reached else 'aborted_home', energy_check=None, **common)
        if route is None or not route:
            return self.stop('return_route_unknown', energy_check=None, **common)
        action = route[0]
        dx, dy = c.VECTORS[action]
        nxt = (cell[0]+dx, cell[1]+dy)
        if not self.composer.free((nxt[0], nxt[1], 0)):
            return self.stop('return_not_admitted', energy_check=None, **common)
        check = gates.energy(self.power_model, battery, now, self.visited, nxt, self.home[:2])
        if not check['allowed']:
            return self.stop('land_local_reserve', energy_check=check, **common)
        out = self.composer.output(action, route, 'returning', 0)
        return self.respond(out['wsp'], out['prediction'], 'returning', 'move', energy_check=check,
                            plan=route[:4], candidates=0, **common)

    def _compose(self, frame):
        """COMPOSE's decision for this already-ingested frame, without ingesting twice."""
        a = self.composer
        a.update = lambda _frame: None      # instance shadow; removed below
        turns = a.turns
        try:
            out = a.decide(frame)
        finally:
            del a.update
            a.turns = turns
        return out
