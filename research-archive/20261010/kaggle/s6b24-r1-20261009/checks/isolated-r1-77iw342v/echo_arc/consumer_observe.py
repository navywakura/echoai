"""Development-only observations of actual wait-control consumption.

Uses the existing decision journal. Source-line tracing is passive and never
used in sealed examinations. Zero-valued assignments are observed directly,
not inferred from before/after differences or a coincidentally matching key.
"""
from collections import Counter
import hashlib
import inspect
import json
import sys

from echo_arc import precise_patch as patch
from echo_arc.repair_diagnostics import DiagnosticRecorder, compact


class ConsumptionRecorder(DiagnosticRecorder):
    def __init__(self, journal, *, origin, program):
        if origin != 'DEVELOPMENT_A':
            raise ValueError('consumer tracing is restricted to development A')
        super().__init__(journal)
        self.program = patch.validate(program)
        self.reads = []
        self.consumers = Counter()
        self.consumer_sites = {}

    def capture(self, actor, state):
        super().capture(actor, state)
        self.reads = []

    def write(self, **event):
        if event['kind'] == 'decision':
            event['parameter_consumptions'] = list(self.reads)
        super().write(**event)
        if event['kind'] == 'decision':
            for entry in self.reads:
                self.consumers[compact(dict(entry, features=self.last_features))] += 1

    def summary(self):
        return dict(super().summary(), consumer_sites=self.consumer_sites,
                    consumers=[dict(json.loads(key), count=count)
                               for key, count in sorted(self.consumers.items())])


def source_site(function, statement):
    lines, start = inspect.getsourcelines(function)
    matches = [start+i for i, line in enumerate(lines) if line.strip() == statement]
    if len(matches) != 1:
        raise RuntimeError('consumer source changed; review before tracing')
    return matches[0], hashlib.sha256(''.join(lines).encode()).hexdigest()


def traced_agent_class(program, recorder):
    from echo_arc.agent import Arc3EchoV57
    program = patch.validate(program)
    if recorder.program != program:
        raise ValueError('recorder and actor must use the same policy')
    parent = patch.agent_class(program)
    hold_line, hold_hash = source_site(Arc3EchoV57.choose, 'self.hold = self.HOLD')
    cap_line, cap_hash = source_site(patch.apply_cooldown, 'actor.hold = min(actor.hold, parameters["COOLDOWN_CAP"])')
    recorder.consumer_sites = {
        'HOLD': {'function': 'Arc3EchoV57.choose', 'line': hold_line, 'source_sha256': hold_hash},
        'COOLDOWN_CAP': {'function': 'precise_patch.apply_cooldown', 'line': cap_line, 'source_sha256': cap_hash}}

    class ObservedConsumer(parent):
        def choose(self, state):
            if sys.gettrace() is not None:
                raise RuntimeError('refusing to replace an existing trace function')

            def trace_line(frame, event, _):
                if event == 'line':
                    if frame.f_code is Arc3EchoV57.choose.__code__ and frame.f_lineno == hold_line:
                        assert frame.f_locals['self'] is self
                        recorder.reads.append({'parameter': 'HOLD', 'value': self.HOLD,
                                               'remaining_before': self.hold})
                    elif frame.f_code is patch.apply_cooldown.__code__ and frame.f_lineno == cap_line:
                        assert frame.f_locals['actor'] is self
                        recorder.reads.append({'parameter': 'COOLDOWN_CAP',
                            'value': frame.f_locals['parameters']['COOLDOWN_CAP'], 'remaining_before': self.hold})
                return trace_line

            def trace_call(frame, event, _):
                if event == 'call' and frame.f_code in (Arc3EchoV57.choose.__code__, patch.apply_cooldown.__code__):
                    return trace_line
                return None

            sys.settrace(trace_call)
            try:
                return super().choose(state)
            finally:
                sys.settrace(None)

    return ObservedConsumer


def play(env, budget, seed, program, recorder):
    """Same actor and runner; a private factory adds passive consumption reads."""
    from types import FunctionType
    from echo_arc import runner
    from echo_arc.precise_observe import PreciseObservedAgent
    actor_class = traced_agent_class(program, recorder)
    actors = []

    def factory(_):
        def make(*args, **kwargs):
            actor = actor_class(*args, **kwargs)
            actors.append(actor)
            recorder.bind_actor(actor)
            return PreciseObservedAgent(actor, recorder)
        return make

    run = FunctionType(runner.play.__code__, dict(runner.play.__globals__, agent_class=factory),
                       runner.play.__name__, runner.play.__defaults__)
    record = run(env, budget, seed, agent_name='s6b5')
    record['patch_hits'] = list(getattr(actors[0], 'patch_hits', []))
    return record


def assess(proposal, rows):
    """Counterfactual settings at recorded consumption sites; never a gain claim."""
    proposal = patch.validate(proposal)
    if len(proposal['patches']) != 1:
        raise ValueError('one proposal required')
    parameter, value = next(iter(proposal['patches'][0]['set'].items()))
    if parameter not in ('HOLD', 'COOLDOWN_CAP'):
        raise ValueError('this observer supports only wait controls')
    matching = different = 0
    for row in rows:
        if row['origin'] != 'DEVELOPMENT_A':
            raise ValueError('protected or reserved evidence forbidden')
        for entry in row['diagnostics']['consumers']:
            if entry['parameter'] != parameter or not patch.settings(proposal, entry['features'])[1]:
                continue
            matching += entry['count']
            old, new = entry['value'], value
            if parameter == 'COOLDOWN_CAP':
                old, new = min(entry['remaining_before'], old), min(entry['remaining_before'], new)
            if old != new:
                different += entry['count']
    return {'observed_matching_reads': matching, 'would_change_consumed_value': different,
            'scope': 'recorded actor paths only', 'action_improvement': 'UNMEASURED'}
