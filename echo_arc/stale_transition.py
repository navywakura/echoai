"""Candidate bounded repair: revise a predicted move after observed no-ops.

Development only until independently verified. Facts/journals are untouched;
the learned transition prediction and queued plan can be revised. No access
to simulator state, task identifiers, reserve or a solver.
"""
from types import FunctionType
from echo_arc import precise_patch as previous

LIMITS = dict(previous.LIMITS, REVALIDATE_NOOP=(0, 8))
DEFAULTS = dict(previous.DEFAULTS, REVALIDATE_NOOP=0)
FEATURES, EMPTY = previous.FEATURES, previous.EMPTY
validate = FunctionType(previous.validate.__code__, dict(previous.validate.__globals__, LIMITS=LIMITS))
parse = FunctionType(previous.parse.__code__, dict(previous.parse.__globals__, validate=validate))
digest = FunctionType(previous.digest.__code__, dict(previous.digest.__globals__, validate=validate))
append = FunctionType(previous.append.__code__, dict(previous.append.__globals__, validate=validate))
settings = previous.settings


def revise(actor, evidence, limit, state, action, next_state, predicted, game_over, level_up):
    """Return an actual revision receipt or None; inputs are observed transitions."""
    key = (state, action)
    if not limit or game_over or level_up:
        evidence.clear()
        return None
    if next_state != state or predicted in (None, state):
        evidence.pop(key, None)
        return None
    evidence[key] = min(8, evidence.get(key, 0) + 1)
    if evidence[key] < limit:
        return None
    count = evidence.pop(key)
    # A self-loop records the observation. It does not mark the action unsafe
    # or disable it forever; a later changing transition can replace it again.
    actor.T[key] = state
    actor.adj.setdefault(state, {})[action] = state
    actor.path.clear()
    return {'state': state, 'action': list(action), 'old_prediction': predicted,
            'observed_next': next_state, 'observations': count}


def agent_class(program):
    program = validate(program)
    factory = FunctionType(previous.agent_class.__code__, dict(previous.agent_class.__globals__, validate=validate))
    parent = factory(program)
    if program == EMPTY:
        return parent

    class Revalidated(parent):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.noop_evidence = {}
            self.noop_revisions = []

        def learn(self, state, action, next_state, game_over, level_up):
            predicted = self.T.get((state, action))
            limit = self.patch_pending.get('REVALIDATE_NOOP', 0)
            super().learn(state, action, next_state, game_over, level_up)
            receipt = revise(self, self.noop_evidence, limit, state, action, next_state,
                             predicted, game_over, level_up)
            if receipt is not None:
                self.noop_revisions.append(receipt)

    return Revalidated
