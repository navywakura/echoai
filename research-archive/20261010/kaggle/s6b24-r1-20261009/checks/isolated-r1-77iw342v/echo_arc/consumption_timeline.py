"""Passive development control reads with explicit decision/outcome alignment."""
from collections import Counter
import copy

from echo_arc import contrastive_evidence as legacy
from echo_arc.feasible_grammar import canonical


class Recorder(legacy.Recorder):
    def __init__(self, journal, *, origin, program):
        super().__init__(journal, origin=origin, program=program)
        self.control_reads = []
        self.decision_count = 0
        self.pending_reads = []

    def write(self, **event):
        super().write(**event)
        if event['kind'] == 'decision':
            self.pending_reads = []
            for reading in self.reads:
                item = dict(reading, decision_index=self.decision_count,
                            features=dict(self.last_features))
                self.control_reads.append(item)
                self.pending_reads.append(item)
            self.decision_count += 1
        elif event['kind'] == 'result':
            for item in self.pending_reads:
                item['immediate_outcome'] = {k:bool(event[k]) for k in ('changed','game_over','level_up')}
            self.pending_reads = []

    def summary(self):
        return dict(super().summary(), control_timeline=dict(version=1,
            indexing='agent decisions before automatic reset alignment', reads=copy.deepcopy(self.control_reads)))


def align_steps(row):
    legacy.align_steps(row)
    timeline = row['diagnostics']['control_timeline']
    actual = [i for i in range(len(row['actions'])) if i not in set(row['automatic_reset_indices'])]
    for entry in timeline['reads']:
        entry['action_index'] = actual[entry['decision_index']]
    timeline['indexing'] = 'zero-based decision_index and zero-based action_index including runner resets'
    validate(row)


def validate(row):
    legacy.require_development([row])
    trace = row['diagnostics']['trajectory']
    timeline = row['diagnostics']['control_timeline']
    if timeline['version'] != 1:
        raise ValueError('unknown control timeline version')
    found = Counter()
    for entry in timeline['reads']:
        index = entry['action_index']
        if not 0 <= index < len(row['actions']) or trace['steps'][index] is None:
            raise ValueError('control read aligned to absent decision')
        point = trace['steps'][index]
        if entry['features'] != dict(zip(trace['features'],point['f'],strict=True)):
            raise ValueError('control read is not its actual pre-decision observation')
        if list(entry['immediate_outcome'][k] for k in ('changed','game_over','level_up')) != point['outcome']:
            raise ValueError('control read outcome is not aligned')
        found[canonical({k:entry[k] for k in ('parameter','value','remaining_before','features')})] += 1
    expected=Counter()
    for entry in row['diagnostics']['consumers']:
        expected[canonical({k:entry[k] for k in ('parameter','value','remaining_before','features')})] += entry['count']
    if found != expected:
        raise ValueError('control timeline disagrees with existing aggregate readings')


def links(before, after, parameter):
    """One common-prefix intervention per case; final outcomes are associations.

    Compare readings before the first action divergence, where observed action
    histories are still equal. A read is never marked causal for a final loss.
    """
    legacy.require_development(before['rows']+after['rows'])
    result=[]
    for i,(base,candidate) in enumerate(zip(before['rows'],after['rows'],strict=True)):
        a=base['actions']; b=candidate['actions']
        divergence=next((j for j in range(min(len(a),len(b))) if a[j]!=b[j]),
                        min(len(a),len(b)) if len(a)!=len(b) else None)
        limit=divergence if divergence is not None else len(a)-1
        lookup={(x['action_index'],x['parameter']):x for x in candidate['diagnostics']['control_timeline']['reads']}
        for old in base['diagnostics']['control_timeline']['reads']:
            if old['parameter']!=parameter or old['action_index']>limit:
                continue
            new=lookup.get((old['action_index'],parameter))
            if new is None or new['features']!=old['features']:
                continue
            if old['value']==new['value']:
                continue
            result.append(dict(case_index=i,parameter=parameter,read_action_index=old['action_index'],
                features=dict(old['features']),consumed_values=[old['value'],new['value']],
                immediate_outcomes=[old['immediate_outcome'],new['immediate_outcome']],
                first_action_divergence=divergence,
                steps_until_action_divergence=None if divergence is None else divergence-old['action_index'],
                levels=[base['levels_completed'],candidate['levels_completed']],
                score=[base['score'],candidate['score']],causal_status='observed common-prefix intervention; final outcome association only'))
            break
    return result


def legacy_rows(rows):
    result=copy.deepcopy(rows)
    for row in result:
        row['diagnostics'].pop('control_timeline',None)
    return result
