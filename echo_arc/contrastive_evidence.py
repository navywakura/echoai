"""B11: passive development trajectories and paired, allowlisted feedback.

These are observations, not an inner monologue or causal explanations. No
protected trajectory may enter this module's feedback interface.
"""
from itertools import zip_longest

from echo_arc import stale_transition as patch
from echo_arc.feasible_grammar import public_features
from echo_arc.transition_evidence import Recorder as Previous
from seed.game_selfimprove import sha

FEATURE_ORDER = tuple(sorted(patch.FEATURES))
BEHAVIOR = ('actions', 'frames', 'levels_completed', 'actions_per_level', 'resets', 'score')


class Recorder(Previous):
    def __init__(self, journal, *, origin, program):
        super().__init__(journal, origin=origin, program=program)
        self.steps = []

    def write(self, **event):
        super().write(**event)
        if event['kind'] == 'decision':
            features = public_features(self.last_features)
            self.steps.append({'f': [features[k] for k in FEATURE_ORDER]})
        elif event['kind'] == 'result':
            self.steps[-1]['outcome'] = [bool(event[k]) for k in ('changed', 'game_over', 'level_up')]

    def summary(self):
        return dict(super().summary(), trajectory={'features': list(FEATURE_ORDER), 'steps': self.steps})


def require_development(rows):
    if any(r.get('origin') != 'DEVELOPMENT_A' for r in rows):
        raise ValueError('only development trajectories may enter model evidence')


def behavior_digest(rows):
    require_development(rows)
    return sha([{k: row[k] for k in BEHAVIOR} for row in rows])


def align_steps(row):
    """Account for runner resets, which have no agent decision/features."""
    trace = row['diagnostics']['trajectory']
    automatic = set(row['automatic_reset_indices'])
    if len(automatic) != row['resets'] or len(trace['steps']) + len(automatic) != len(row['actions']):
        raise ValueError('unpaired decision/reset accounting')
    decisions = iter(trace['steps'])
    trace['steps'] = [None if i in automatic else next(decisions) for i in range(len(row['actions']))]


def step(row, index):
    """No coordinates, state hashes, task names, seeds, family or private data."""
    trace = row['diagnostics']['trajectory']
    if trace['features'] != list(FEATURE_ORDER):
        raise ValueError('unknown development trajectory format')
    if not 0 <= index < len(trace['steps']):
        return None
    event = trace['steps'][index]
    action = row['actions'][index]
    if event is None:
        return {'automatic_reset': True, 'action': {'kind': 'R', 'key': None}}
    return {'features': public_features(dict(zip(FEATURE_ORDER, event['f'], strict=True))),
            'action': {'kind': action[0], 'key': action[1] if action[0] == 'K' else None},
            'outcome': dict(zip(('changed', 'game_over', 'level_up'), event['outcome'], strict=True))}


def comparison(before, after):
    """Full behavior fingerprint and up to three measured positive/negative cases."""
    require_development(before['rows'] + after['rows'])
    identity = lambda r: tuple(r[k] for k in ('version', 'seed', 'rep', 'budget'))
    if list(map(identity, before['rows'])) != list(map(identity, after['rows'])):
        raise ValueError('unpaired development measurements')
    losses, gains, changed = [], [], []
    for i, (b, a) in enumerate(zip(before['rows'], after['rows'], strict=True)):
        if a['levels_completed'] < b['levels_completed'] or a['score'] + 1e-10 < b['score']:
            losses.append(i)
        elif a['levels_completed'] > b['levels_completed'] or a['score'] > b['score'] + 1e-10:
            gains.append(i)
        if b['actions'] != a['actions']:
            changed.append(i)
    # Include both signs when they exist, even with many losses.
    selected = list(dict.fromkeys(losses[:1] + gains[:1] + losses[1:2] + changed))[:3]
    contrasts = []
    for i in selected:
        b, a = before['rows'][i], after['rows'][i]
        first = next((n for n, (x, y) in enumerate(zip_longest(b['actions'], a['actions'])) if x != y), None)
        item = {'case_index': i, 'effect': 'loss' if i in losses else 'gain' if i in gains else 'changed',
                'levels': [b['levels_completed'], a['levels_completed']], 'score': [b['score'], a['score']],
                'actions_per_level': [b['actions_per_level'], a['actions_per_level']],
                'first_different_action': first, 'sequence': []}
        if first is not None:
            item['sequence'] = [{'before': step(b, n), 'candidate': step(a, n)}
                                for n in range(max(0, first - 1), first + 1)]
        contrasts.append(item)
    return {'origin': 'DEVELOPMENT_A', 'behavior_sha256': behavior_digest(after['rows']),
            'baseline_behavior_sha256': behavior_digest(before['rows']),
            'before_trace_sha256': before['trace_digest'], 'after_trace_sha256': after['trace_digest'],
            'losses': len(losses), 'gains': len(gains), 'changed_games': len(changed),
            'contrasts': contrasts}


def feedback(history):
    output = []
    for index, event in enumerate(history[-6:]):
        observed = event.get('development')
        entry = {'proposal': patch.validate(event['proposal']) if event.get('proposal') else None,
                 'verdict': event['verdict'], 'protected_rejection': event['verdict'] == 'V4',
                 'gain': event.get('A', {}).get('gain', 0)}
        if observed:
            if observed['origin'] != 'DEVELOPMENT_A':
                raise ValueError('protected feedback forbidden')
            entry['behavior'] = observed['behavior_sha256']
            entry['same_behavior_as_own_calls'] = event.get('equivalent_calls', [])
            entry.update({k: observed[k] for k in ('losses', 'gains', 'changed_games')})
            if index >= len(history[-6:]) - 2:
                entry['contrasts'] = [{k: c[k] for k in ('effect', 'levels', 'score', 'actions_per_level',
                                                       'first_different_action', 'sequence')}
                                      for c in observed['contrasts']]
        output.append(entry)
    return output
