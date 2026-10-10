"""B5: up to three observable guards, plus a bounded remaining-wait operation."""
import json
from types import FunctionType

from echo_arc import local_patch as previous

LIMITS = dict(previous.LIMITS, COOLDOWN_CAP=(0, 100))
DEFAULTS = dict(previous.DEFAULTS, COOLDOWN_CAP=100)
FEATURES = dict(previous.FEATURES, reset_pending=(0, 1), pending_effect=(0, 1),
                reset_useful=(0, 1), path_pending=(0, 1), trial_pending=(0, 1),
                pred_error=(0, 1), hold_remaining=(0, 100))
EMPTY = {"patches": []}


def validate(program):
    if type(program) is not dict or set(program) != {"patches"} or type(program["patches"]) is not list:
        raise ValueError("expected patches only")
    if len(program["patches"]) > 32:
        raise ValueError("at most 32 patches")
    for item in program["patches"]:
        if type(item) is not dict or set(item) != {"when", "set"}:
            raise ValueError("expected when and set")
        if type(item["when"]) is not dict or not 1 <= len(item["when"]) <= 3:
            raise ValueError("one to three observable guards")
        for key, test in item["when"].items():
            if key not in FEATURES or type(test) is not list or len(test) != 2 or test[0] not in ("eq", "ge", "le"):
                raise ValueError("unknown observable guard")
            lo, hi = FEATURES[key]
            if type(test[1]) is not int or not lo <= test[1] <= hi:
                raise ValueError("guard outside bounds")
        if type(item["set"]) is not dict or len(item["set"]) != 1:
            raise ValueError("one parameter per patch")
        for key, value in item["set"].items():
            if key not in LIMITS or type(value) is not int or not LIMITS[key][0] <= value <= LIMITS[key][1]:
                raise ValueError("parameter outside bounds")
    return json.loads(json.dumps(program, sort_keys=True))


parse = FunctionType(previous.parse.__code__, dict(previous.parse.__globals__, validate=validate))
digest = FunctionType(previous.digest.__code__, dict(previous.digest.__globals__, validate=validate))
append = FunctionType(previous.append.__code__, dict(previous.append.__globals__, validate=validate))
settings = previous.settings


def features(actor, stagnation=0):
    out = previous.features(actor, stagnation)
    pred = actor.pred
    out.update(reset_pending=int(bool(actor.to_try and actor.to_try[0] in actor.reset_keys and not actor.hold)),
               pending_effect=int(actor._tried_at is not None),
               reset_useful=int(bool(sum(actor.useful_colours.values()))),
               path_pending=int(bool(actor.path)), trial_pending=int(actor.pending is not None),
               pred_error=int(pred[1] > pred[0]), hold_remaining=min(100, max(0, actor.hold)))
    return out


def apply_cooldown(actor, parameters):
    if "COOLDOWN_CAP" in parameters:
        actor.hold = min(actor.hold, parameters["COOLDOWN_CAP"])


def agent_class(program):
    from echo_arc.temporal_agent import Arc3EchoV58
    program = validate(program)
    if program == EMPTY:
        return Arc3EchoV58
    # Reuse restoration, observe/learn and bounded temporal operators unchanged.
    native = FunctionType(previous.agent_class.__code__, dict(previous.agent_class.__globals__,
                          validate=validate, features=features))
    parent = native(program)

    class PrecisePatch(parent):
        def choose(self, state):
            self.patch_stagnation = min(2000, self.patch_stagnation + 1) if state == self.patch_last_state else 0
            self.patch_last_state = state
            self.patch_features = features(self, self.patch_stagnation)
            params, self.patch_matches = settings(program, self.patch_features)
            for i in self.patch_matches:
                self.patch_hits[i] += 1
            self.patch_pending = params
            with self._parameters(params):
                apply_cooldown(self, params)
                return Arc3EchoV58.choose(self, state)

    return PrecisePatch
