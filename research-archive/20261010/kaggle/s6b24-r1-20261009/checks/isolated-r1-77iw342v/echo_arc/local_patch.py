"""B4: guarded one-parameter repairs, leaving native controls in place elsewhere."""
import json
from contextlib import contextmanager
from types import FunctionType

from echo_arc import temporal_policy as previous

LIMITS = dict(previous.LIMITS)
FEATURES = dict(previous.FEATURES, motor_ready=(0, 1), marker_count=(0, 8), goal_evidence=(0, 1))
DEFAULTS = dict(previous.DEFAULTS)
EMPTY = {"patches": []}


def validate(program):
    if type(program) is not dict or set(program) != {"patches"} or type(program["patches"]) is not list:
        raise ValueError("expected patches only")
    if len(program["patches"]) > 32:
        raise ValueError("at most 32 guarded patches")
    for item in program["patches"]:
        if type(item) is not dict or set(item) != {"when", "set"}:
            raise ValueError("expected when and set")
        if type(item["when"]) is not dict or not 1 <= len(item["when"]) <= 2:
            raise ValueError("one or two observable conditions")
        for k, test in item["when"].items():
            if k not in FEATURES or type(test) is not list or len(test) != 2 or test[0] not in ("eq", "ge", "le"):
                raise ValueError("unknown condition")
            lo, hi = FEATURES[k]
            if type(test[1]) is not int or not lo <= test[1] <= hi:
                raise ValueError("condition out of bounds")
        if type(item["set"]) is not dict or len(item["set"]) != 1:
            raise ValueError("exactly one parameter per patch")
        for k, value in item["set"].items():
            if k not in LIMITS or type(value) is not int or not LIMITS[k][0] <= value <= LIMITS[k][1]:
                raise ValueError("parameter out of bounds")
    return json.loads(json.dumps(program, sort_keys=True))


parse = FunctionType(previous.parse.__code__, dict(previous.parse.__globals__, validate=validate))
digest = FunctionType(previous.digest.__code__, dict(previous.digest.__globals__, validate=validate))


def append(current, proposal):
    current, proposal = validate(current), validate(proposal)
    if len(proposal["patches"]) != 1:
        raise ValueError("one proposal patch required")
    return validate({"patches": current["patches"] + proposal["patches"]})


def features(actor, stagnation=0):
    return {"click_only": int(6 in actor.available and not actor.keys_real()),
            "body_known": int(actor.me is not None), "reset_known": int(bool(actor.reset_keys)),
            "world_events": min(10000, actor.events), "level": min(100, actor.level),
            "stagnation": stagnation, "order_known": int(bool(actor.order_memory.candidates())),
            "count_known": int(any(actor.count_memory.threshold(k) is not None for k in actor.count_memory.thresholds)),
            "temporal_open": int(actor.temporal_effect_active),
            "entry_count": min(255, max(actor.count_memory.counts.values(), default=0)),
            "motor_ready": int(bool(actor._motor_ready())), "marker_count": min(8, len(actor.markers)),
            "goal_evidence": int(any(v > 0 for v in actor.goal_colours.values()))}


def settings(program, observed):
    out, matched = {}, []
    for i, item in enumerate(program["patches"]):
        if all(observed[k] == n if op == "eq" else observed[k] >= n if op == "ge" else observed[k] <= n
               for k, (op, n) in item["when"].items()):
            out.update(item["set"])
            matched.append(i)
    return out, matched


def agent_class(program):
    from echo_arc.temporal_agent import Arc3EchoV58
    program = validate(program)
    if program == EMPTY:
        return Arc3EchoV58
    # Reuse B3's bounded temporal operations, not a second implementation.
    parent = previous.agent_class({"defaults": {}, "rules": [{"when": {"level": ["ge", 100]}, "set": {}}]})

    class LocalPatch(parent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.patch_last_state = None
            self.patch_stagnation = 0
            self.patch_matches = []
            self.patch_hits = [0] * len(program["patches"])
            self.patch_pending = {}

        @contextmanager
        def _parameters(self, params):
            self.policy_params = dict(self.policy_base, **params)
            overrides = {k: v for k, v in params.items() if k in ("HOLD", "MIN_EVIDENCE", "BABBLE", "WALL_MIN",
                         "ORDER_ENABLED", "COUNT_ENABLED")}
            if "BABBLE" in params:
                overrides["babble"] = params["BABBLE"]
            if "ENTRY_PROBE_LIMIT" in params:
                overrides["MAX_PROBE"] = params["ENTRY_PROBE_LIMIT"]
            saved = {k: (k in vars(self), getattr(self, k)) for k in overrides}
            try:
                for k, v in overrides.items():
                    setattr(self, k, v)
                yield
            finally:
                for k, (owned, value) in saved.items():
                    if owned:
                        setattr(self, k, value)
                    else:
                        delattr(self, k)
                self.policy_params = dict(self.policy_base)

        def choose(self, state):
            self.patch_stagnation = min(2000, self.patch_stagnation + 1) if state == self.patch_last_state else 0
            self.patch_last_state = state
            self.patch_features = features(self, self.patch_stagnation)
            params, self.patch_matches = settings(program, self.patch_features)
            for i in self.patch_matches:
                self.patch_hits[i] += 1
            self.patch_pending = params
            with self._parameters(params):
                return Arc3EchoV58.choose(self, state)

        def observe_state(self, frame):
            with self._parameters(self.patch_pending):
                return Arc3EchoV58.observe_state(self, frame)

        def learn(self, *args):
            with self._parameters(self.patch_pending):
                return Arc3EchoV58.learn(self, *args)

        def report(self):
            return Arc3EchoV58.report(self)

    return LocalPatch


def play(env, budget, seed, program, journal=None):
    from echo_arc import runner
    cls = agent_class(program)
    actors = []

    def factory(_):
        def create(*args, **kwargs):
            actor = cls(*args, **kwargs)
            actors.append(actor)
            if journal is None:
                return actor
            if hasattr(journal, "bind_actor"):
                journal.bind_actor(actor)
            from echo_arc.observe import ObservedAgent
            return ObservedAgent(actor, journal)
        return create
    adapted = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=factory),
                           runner.play.__name__, runner.play.__defaults__)
    record = adapted(env, budget, seed, agent_name="s6b4")
    if program != EMPTY:
        record["patch_hits"] = actors[0].patch_hits
    return record
