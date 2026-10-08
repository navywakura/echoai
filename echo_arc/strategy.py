"""S6-B bounded, observable control strategies; model output is data, never code."""
import hashlib
import json

LIMITS = {
    "HOLD": (0, 100), "MIN_EVIDENCE": (2, 16), "WALL_MIN": (2, 8),
    "MARGIN": (0, 6), "BABBLE": (1, 8), "TEST_WINDOW": (1, 20),
    "WINDOW": (4, 32), "MAX_PER_TARGET": (10, 120),
    "MIN_CLICK_EVIDENCE": (1, 6), "MAX_UNITS": (8, 16), "EXPLORE": (0, 1),
}
FEATURES = {"click_only": (0, 1), "body_known": (0, 1), "reset_known": (0, 1),
            "world_events": (0, 10000), "level": (0, 100), "stagnation": (0, 2000)}
EMPTY = {"defaults": {}, "rules": []}


def validate(policy):
    if type(policy) is not dict or set(policy) != {"defaults", "rules"}:
        raise ValueError("expected exactly defaults and rules")
    def parameters(params):
        if type(params) is not dict or not set(params) <= LIMITS.keys():
            raise ValueError("unknown parameter")
        for name, value in params.items():
            lo, hi = LIMITS[name]
            if type(value) is not int or not lo <= value <= hi:
                raise ValueError("parameter out of bounds: " + name)
    parameters(policy["defaults"])
    rules = policy["rules"]
    if type(rules) is not list or len(rules) > 8:
        raise ValueError("at most eight rules")
    for rule in rules:
        if type(rule) is not dict or set(rule) != {"when", "set"}:
            raise ValueError("expected when and set")
        parameters(rule["set"])
        when = rule["when"]
        if type(when) is not dict or not when or not set(when) <= FEATURES.keys():
            raise ValueError("unknown or empty observable condition")
        for name, test in when.items():
            lo, hi = FEATURES[name]
            if type(test) is not list or len(test) != 2 or test[0] not in ("eq", "ge", "le") \
                    or type(test[1]) is not int or not lo <= test[1] <= hi:
                raise ValueError("invalid condition")
    return json.loads(json.dumps(policy, sort_keys=True))


def parse(answer):
    if not isinstance(answer, str) or len(answer) > 16000:
        raise ValueError("missing/oversized answer")
    text = answer.strip()
    if text.startswith("```json\n") and text.endswith("```"):
        text = text[8:-3].strip()
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out
    return validate(json.loads(text, object_pairs_hook=unique))


def digest(policy):
    return hashlib.sha256(json.dumps(validate(policy), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def settings(policy, features):
    out = dict(policy["defaults"])
    for rule in policy["rules"]:
        if all((features[name] == value if op == "eq" else features[name] >= value if op == "ge"
                else features[name] <= value) for name, (op, value) in rule["when"].items()):
            out.update(rule["set"])
    return out


def agent_class(policy):
    from echo_arc.agent import Arc3EchoV57
    policy = validate(policy)
    class Strategy(Arc3EchoV57):
        def __init__(self, available, seed, boundary=True):
            super().__init__(available, seed, boundary)
            self.strategy_stagnation = 0
            self.strategy_last_state = None
            self.strategy_base = {name: getattr(Arc3EchoV57, name) for name in LIMITS}

        def choose(self, state):
            self.strategy_stagnation = min(2000, self.strategy_stagnation + 1) \
                if state == self.strategy_last_state else 0
            self.strategy_last_state = state
            features = {"click_only": int(6 in self.available and not self.keys_real()),
                        "body_known": int(self.me is not None), "reset_known": int(bool(self.reset_keys)),
                        "world_events": min(10000, self.events), "level": min(100, self.level),
                        "stagnation": self.strategy_stagnation}
            params = dict(self.strategy_base)
            params.update(settings(policy, features))
            for name, value in params.items():
                setattr(self, name, value)
            self.babble = self.BABBLE
            return super().choose(state)
    return Strategy
