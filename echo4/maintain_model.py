"""Bounded, observation-only MAINT belief; known mechanics are an explicit prior.

Boxes are conservative hypothetical ranges, never readings of private registers.
No executor, environment instance, fault label or receipt enters the controller.
"""
from echoai.echo4.boundary import code
from echoai.echo4.self_attribution import H_CODES, T_CODES, H_STEPS, T_STEPS, _packet
from echoai.echo4.world import Body, DockRules, integer, transition
from echoai.echo4.maintain_world import SERVICE_COST, SERVICE_TICKS, DEGRADED_DROP
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT

MAX_BOXES = 512
LIMIT = 512
MODES = ("adaptive", "no_repair", "fixed", "no_history")
CONTEXT = encode_cell(0, KIND_OBJECT, vitality=64, temperature=64, temperature_bands=8)
# Built from the original transition, not another implementation of its physics.
WEAK_COOL = tuple(transition(Body(64, t), 1, DockRules(cooling_drop=DEGRADED_DROP)).after.temperature
                  if 0 < t < 127 else t for t in range(128))


class MaintainStop(RuntimeError):
    pass


def bands(packet):
    _packet(packet, CONTEXT)
    hs = [v for v in range(1, 128) if H_CODES[v] == code(packet, 8)]
    ts = [v for v in range(1, 127) if T_CODES[v] == code(packet, 9)]
    if not hs or not ts:
        raise ValueError("not a supported living observation")
    return min(hs), max(hs), min(ts), max(ts)


def prior(packet, spare_cap=3):
    integer(spare_cap, 0, 3, "spare prior bound")
    bounds = bands(packet)
    return tuple((*bounds, fault, heat, spares)
                 for fault in range(3) for heat in range(5) for spares in range(spare_cap + 1))


def project(box, action, progress):
    """One conservative rectangular image, split at the service affordability edge.

    Box = (H_low,H_high,T_low,T_high,fault,heat,spares), fault 0/1/2.
    Returning terminal bounds lets the caller reject a plan for ANY hypothesis.
    """
    hl, hh, tl, th, fault, heat, spares = box
    hl, hh = H_STEPS[action][hl], H_STEPS[action][hh]
    table = WEAK_COOL if action == 1 and fault else T_STEPS[action]
    tl, th = table[tl], table[th]
    if hl == 0 or tl == 0 or th == 127:
        # Split terminal slices before external heat/service. Do not charge or
        # repair a living subrange as if its terminal neighbour represented it.
        outputs = []
        hranges = [(hl, hh)] if hl else [(0, 0)] + ([(1, hh)] if hh else [])
        tranges = ([(0, 0)] if tl == 0 else [])
        if max(1, tl) <= min(126, th):
            tranges.append((max(1, tl), min(126, th)))
        if th == 127:
            tranges.append((127, 127))
        for a, b in hranges:
            for c, d in tranges:
                if a == 0 or c == 0 or d == 127:
                    outputs.append((a, b, c, d, fault, heat, spares))
                else:
                    outputs.extend(_service(a, b, min(127, c + heat), min(127, d + heat),
                                            fault, heat, spares, action, progress))
        return tuple(outputs)
    # The zero endpoint stays terminal even in a heated room.
    tl = min(127, tl + heat) if tl else 0
    th = min(127, th + heat) if th else 0
    return _service(hl, hh, tl, th, fault, heat, spares, action, progress)


def _service(hl, hh, tl, th, fault, heat, spares, action, progress):
    if th == 127 and tl < 127:
        return ((hl, hh, 127, 127, fault, heat, spares),
                *_service(hl, hh, tl, 126, fault, heat, spares, action, progress))
    if action != 1 or progress != SERVICE_TICKS - 1 or not spares:
        return ((hl, hh, tl, th, fault, heat, spares),)
    # Terminal boxes cannot be an authorized plan. Keep their bounds as-is.
    if hl == 0 or tl == 0 or th == 127:
        return ((hl, hh, tl, th, fault, heat, spares),)
    result = []
    if hl <= SERVICE_COST:
        result.append((hl, min(hh, SERVICE_COST), tl, th, fault, heat, spares))
    if hh > SERVICE_COST:
        result.append((max(hl, SERVICE_COST + 1) - SERVICE_COST,
                       hh - SERVICE_COST, tl, th, 0 if fault == 1 else fault, heat, spares - 1))
    return tuple(result)


def advance(boxes, action, progress):
    return tuple(sorted({out for box in boxes for out in project(box, action, progress)}))


def safe(boxes):
    return bool(boxes) and all(b[0] > 0 and b[2] > 0 and b[3] < 127 for b in boxes)


class MaintainModel:
    def __init__(self, packet, *, mode="adaptive"):
        if mode not in MODES:
            raise ValueError("unknown maintenance mode")
        self.mode = mode
        self.current = packet
        self.boxes = prior(packet)
        self.progress = self.steps = self.conflicts = self.attempts = 0
        self.pending = None
        self.stopped = ""
        self.last_choice = None
        self.predictions = 0

    def _check(self, packet):
        if self.stopped:
            raise MaintainStop(self.stopped)
        _packet(packet, self.current)
        if packet != self.current:
            raise ValueError("stale maintenance observation")
        if self.steps >= LIMIT:
            self.stopped = "budget"
            raise MaintainStop(self.stopped)

    def choose(self, packet, q_row, proposed):
        self._check(packet)
        if self.pending is not None:
            raise RuntimeError("unconsumed maintenance forecast")
        integer(proposed, 0, 2, "proposal")
        if len(q_row) != 3:
            raise ValueError("requires original three-action Q row")
        for q in q_row:
            integer(q, -127, 127, "Q")
        boxes = prior(packet) if self.mode == "no_history" else self.boxes
        fault_set = {b[4] for b in boxes}
        degraded = 0 not in fault_set
        repair_possible = any(b[4] == 1 and b[6] for b in boxes)
        want_service = (degraded and repair_possible if self.mode in ("adaptive", "no_history")
                        else self.mode == "fixed" and self.steps % 24 < 3)
        results = {a: advance(boxes, a, self.progress) for a in range(3)}
        # Faults may change before a tick without an observable announcement.
        # Safety must not trust a formerly narrow nominal thermal hypothesis.
        guard = prior(packet)
        self.predictions += 3 * (len(boxes) + len(guard))
        allowed = [a for a, r in results.items() if safe(r) and safe(advance(guard, a, self.progress))]
        # A complete service must be a deliberate choice, not incidental cooling.
        if self.progress == 2 and not want_service and 1 in allowed:
            allowed.remove(1)
        if not allowed:
            self.stopped = "no_safe_action"
            raise MaintainStop(self.stopped)
        h_low = min(b[0] for b in boxes)
        next_wait_heat = max(b[3] for b in results[2])
        preferences = {}
        for a in allowed:
            future = results[a]
            hl = min(b[0] for b in future)
            th = max(b[3] for b in future)
            tl = min(b[2] for b in future)
            work = a == 2 and tl >= 48 and th <= 80
            priority = 0
            if want_service and a == 1 and hl > 8:
                priority = 100
            elif h_low <= 64 and a == 0:
                priority = 90
            elif next_wait_heat > 80 and a == 1:
                priority = 80
            elif work and hl > 24:
                priority = 70
            elif a == 0 and th <= 96:
                priority = 60
            elif a == 1 and tl >= 32:
                priority = 50
            margin = min(hl, tl, 127 - th)
            preferences[a] = (priority, margin, q_row[a], a == proposed, a == 2, -a)
        chosen = max(preferences, key=preferences.get)
        self.last_choice = (chosen, degraded, want_service, len(boxes))
        return chosen

    def prepare(self, packet, action, gate):
        self._check(packet)
        integer(action, 0, 2, "applied")
        integer(gate, 0, 2, "gate")
        if self.pending is not None:
            raise RuntimeError("duplicate preparation")
        self.pending = (packet, action, gate, advance(self.boxes, action, self.progress))

    def observe(self, packet, action, after, terminal):
        if self.pending is None:
            raise RuntimeError("missing execution forecast")
        pending = self.pending
        integer(action, 0, 2, "applied")
        _packet(packet, self.current)
        _packet(after, self.current)
        if type(terminal) is not bool or packet != pending[0] or action != pending[1]:
            raise ValueError("execution mismatch")
        self.pending = None
        self.steps += 1
        self.progress = self.progress + 1 if action == 1 else 0
        if self.progress == 3:
            self.progress = 0
            self.attempts += 1
        self.current = after
        if terminal:
            self.progress = 0
            self.stopped = "terminal"
            return
        hl, hh, tl, th = bands(after)
        survivors = []
        for a, b, c, d, fault, heat, spares in pending[3]:
            low_h, high_h, low_t, high_t = max(a, hl), min(b, hh), max(c, tl), min(d, th)
            if low_h <= high_h and low_t <= high_t:
                survivors.append((low_h, high_h, low_t, high_t, fault, heat, spares))
        if not survivors:
            # Exogenous changes are not resets of the body or of CAM/T/Q.
            # Discard only contradicted hypotheses, reseed the declared prior.
            self.conflicts += 1
            survivors = prior(after, max(b[6] for b in pending[3]))
        self.boxes = tuple(sorted(set(survivors)))
        if len(self.boxes) > MAX_BOXES:
            # Fail closed with a bounded over-approximation, never silently
            # select a convenient subset or make an uncheckpointable halt.
            self.boxes = prior(after, max(b[6] for b in self.boxes))
            self.stopped = "hypothesis_budget"
        elif pending[2]:
            self.stopped = "gate_veto"
