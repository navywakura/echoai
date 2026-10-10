"""S6-B3 bounded policies over v5.8's observed order/count mechanisms."""
import json
from types import FunctionType

from echo_arc import strategy as original

LIMITS = {name: original.LIMITS[name] for name in ("HOLD", "MIN_EVIDENCE", "BABBLE", "WALL_MIN")}
LIMITS.update(ENTRY_PROBE_LIMIT=(2, 16), ORDER_MIN_SUPPORT=(1, 4), COUNT_MIN_SUPPORT=(1, 4),
              ORDER_ENABLED=(0, 1), COUNT_ENABLED=(0, 1), AFTER_EFFECT_POLICY=(0, 2),
              PROBE_STRATEGY=(0, 2))
FEATURES = dict(original.FEATURES, order_known=(0, 1), count_known=(0, 1),
                temporal_open=(0, 1), entry_count=(0, 255))
EMPTY = {"defaults": {}, "rules": []}
DEFAULTS = {"HOLD": 40, "MIN_EVIDENCE": 8, "BABBLE": 2, "WALL_MIN": 3,
            "ENTRY_PROBE_LIMIT": 8, "ORDER_MIN_SUPPORT": 1, "COUNT_MIN_SUPPORT": 1,
            "ORDER_ENABLED": 1, "COUNT_ENABLED": 1, "AFTER_EFFECT_POLICY": 0,
            "PROBE_STRATEGY": 0}

# Reuse the original validator/parser with private constants; never mutate
# another campaign's globals, files, registry, agent or grammar.
validate = FunctionType(original.validate.__code__, dict(original.validate.__globals__,
                        LIMITS=LIMITS, FEATURES=FEATURES))
parse = FunctionType(original.parse.__code__, dict(original.parse.__globals__, validate=validate))
digest = FunctionType(original.digest.__code__, dict(original.digest.__globals__, validate=validate))
settings = original.settings


def agent_class(policy):
    from echo_arc.temporal_agent import Arc3EchoV58
    policy = validate(policy)
    if policy == EMPTY:
        return Arc3EchoV58

    class TemporalPolicy(Arc3EchoV58):
        def __init__(self, available, seed, boundary=True):
            super().__init__(available, seed, boundary)
            self.policy_stagnation, self.policy_last_state = 0, None
            self.policy_base = dict(DEFAULTS)
            for name in ("HOLD", "MIN_EVIDENCE", "BABBLE", "WALL_MIN"):
                self.policy_base[name] = getattr(Arc3EchoV58, name)
            self.policy_params = dict(self.policy_base)
            order_candidates = self.order_memory.candidates
            count_threshold = self.count_memory.threshold

            def supported_orders():
                return [p for p in order_candidates()
                        if self.order_memory.rules[p]["supports"] >= self.policy_params["ORDER_MIN_SUPPORT"]]

            def supported_count(kind):
                n = count_threshold(kind)
                return n if n is not None and self.count_memory.thresholds[kind][n]["supports"] >= \
                    self.policy_params["COUNT_MIN_SUPPORT"] else None
            self.order_memory.candidates = supported_orders
            self.count_memory.threshold = supported_count

        def choose(self, state):
            self.policy_stagnation = min(2000, self.policy_stagnation + 1) \
                if state == self.policy_last_state else 0
            self.policy_last_state = state
            features = {"click_only": int(6 in self.available and not self.keys_real()),
                        "body_known": int(self.me is not None), "reset_known": int(bool(self.reset_keys)),
                        "world_events": min(10000, self.events), "level": min(100, self.level),
                        "stagnation": self.policy_stagnation,
                        "order_known": int(bool(self.order_memory.candidates())),
                        "count_known": int(any(self.count_memory.threshold(k) is not None
                                              for k in self.count_memory.thresholds)),
                        "temporal_open": int(self.temporal_effect_active),
                        "entry_count": min(255, max(self.count_memory.counts.values(), default=0))}
            self.policy_params = dict(self.policy_base, **settings(policy, features))
            for name in ("HOLD", "MIN_EVIDENCE", "BABBLE", "WALL_MIN", "ORDER_ENABLED", "COUNT_ENABLED"):
                setattr(self, name, self.policy_params[name])
            self.babble = self.BABBLE
            self.MAX_PROBE = self.policy_params["ENTRY_PROBE_LIMIT"]
            return super().choose(state)

        def _make_trial(self):
            preference = self.policy_params["PROBE_STRATEGY"]
            known = self.order_memory.candidates() or any(self.count_memory.threshold(k) is not None
                                                         for k in self.count_memory.thresholds)
            if not preference or known:
                return super()._make_trial()
            order, count = self.ORDER_ENABLED, self.COUNT_ENABLED
            try:
                if preference == 1 and count:
                    self.ORDER_ENABLED = False
                elif preference == 2 and order:
                    self.COUNT_ENABLED = False
                return super()._make_trial()
            finally:
                self.ORDER_ENABLED, self.COUNT_ENABLED = order, count

        def _temporal_step(self):
            mode = self.policy_params["AFTER_EFFECT_POLICY"]
            if mode and self.temporal_effect_active and self._motor_ready() and len(self.markers) >= 2 and not self.path:
                options = []
                for pos, kind in self.markers.items():
                    route = self._walk_exact(pos)
                    if route and self.goal_colours[kind] > 0:
                        preference = (-self.goal_colours[kind], len(route)) if mode == 1 else \
                            (len(route), -self.goal_colours[kind])
                        options.append((preference, pos, route))
                if options:
                    _, pos, route = min(options)
                    self.temporal_decision = {"module": "temporal_policy", "operation": "goal_after_effect", "target": pos}
                    return route[0]
            return super()._temporal_step()

        def report(self):
            return dict(super().report(), temporal_policy=digest(policy), policy_parameters=self.policy_params)

    return TemporalPolicy


def play(env, budget, seed, policy, journal=None):
    from echo_arc import runner
    cls = agent_class(policy)
    if journal is not None:
        from echo_arc.observe import ObservedAgent
        factory = lambda name: lambda *a, **kw: ObservedAgent(cls(*a, **kw), journal)
    else:
        factory = lambda name: cls
    adapted = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=factory),
                           runner.play.__name__, runner.play.__defaults__)
    return adapted(env, budget, seed, agent_name="s6b3")
