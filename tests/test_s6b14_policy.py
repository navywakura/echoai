import copy
import json
import unittest
from unittest.mock import patch as mock

from echo_arc import repair_memory as mem
from echo_arc.feasible_grammar import matches
from seed import s6b14_prompt as prompt
from seed import s6b13 as engine
from tests.test_s6b13 import row, event


def measured_row(index=0, contradictions=1, hold=True):
    value = row()
    value.update(version=2, seed=index, rep=0, budget=10, actions=[['K', 1, None]])
    features = value['diagnostics']['consumers'][0]['features']
    value['diagnostics']['counts']['contradictory_noop'] = contradictions
    if not contradictions:
        value['diagnostics']['contradiction_features'] = []
    if not hold:
        value['diagnostics']['consumers'] = []
        features['hold_remaining'] = 0
    value['diagnostics']['trajectory'] = dict(features=list(mem.FEATURES),
        steps=[{'f': [features[k] for k in mem.FEATURES]}])
    return value


def observed_event(current, index=0, kind='CONTRADICTION', gain=4, verdict='V3'):
    value = event(current, index)
    value.update(type=kind, verdict=verdict, target_id=None, equivalent_calls=[])
    value['A']['gain'] = gain
    value['candidate'] = engine.strategy(program=engine.patch.append(current['program'], value['proposal']))
    return value


class SelectionTests(unittest.TestCase):
    def test_rotate_only_cases_with_signal(self):
        rows = [measured_row(i, contradictions=int(i < 2)) for i in range(8)]
        current = engine.strategy()
        history = [observed_event(current, i, kind=k, gain=0)
                   for i, k in enumerate(mem.KINDS)]
        history[0]['verdict'], history[0]['A']['gain'] = 'accepted', 100
        for index in (3, 6, 12):
            selected, focus, target, stats = mem.select(rows, 'echo', current, history, index)
            self.assertEqual(focus, 'CONTRADICTION')
            self.assertEqual(set(selected), {0, 1})

    def test_exploration_is_guaranteed_despite_large_first_gain(self):
        current, rows = engine.strategy(), [measured_row()]
        history = [observed_event(current, 0, gain=80, verdict='accepted')]
        self.assertEqual(mem.select(rows, 'echo', current, history, 1)[1], 'WAIT')
        history.append(observed_event(current, 1, kind='WAIT', gain=0))
        self.assertEqual(mem.select(rows, 'echo', current, history, 2)[1], 'GENERALIZE')

    def test_unavailable_mechanism_is_not_selected(self):
        rows = [measured_row(hold=False)]
        history = [observed_event(engine.strategy(), verdict='accepted')]
        self.assertEqual(mem.select(rows, 'echo', engine.strategy(), history, 1)[1], 'GENERALIZE')

    def test_rejected_positive_attempts_and_refinements_count(self):
        current = engine.strategy()
        root = observed_event(current, 0)
        child = observed_event(current, 1, kind='REFINE', gain=0)
        child.update(target_id=0, equivalent_calls=[0])
        stats = mem.statistics([root, child])['CONTRADICTION']
        self.assertEqual(stats, dict(trials=2, accepted_gain=0, repeated=1))

    def test_refinement_descendant_does_not_restart_expired_target(self):
        current = engine.strategy()
        history = [observed_event(current)]
        for i in (1, 2, 3):
            child = observed_event(current, i, kind='REFINE')
            child['target_id'] = 0
            history.append(child)
        self.assertIsNone(mem.target_for(current, history))

    def test_measured_repeat_pauses_value_for_one_call_not_other_values(self):
        current = engine.strategy()
        first, second = observed_event(current, 0), observed_event(current, 1)
        second['equivalent_calls'] = [0]
        schema = dict(version=11, origin='DEVELOPMENT_A', excluded=[], groups=[
            dict(parameter='HOLD', value=v, guards=[{'reset_known': ['eq', 1]}]) for v in (1, 2)])
        paused = mem.apply_cooldown(schema, current, [first, second])
        self.assertEqual([g['value'] for g in paused['groups']], [2])
        third = observed_event(current, 2)
        third['proposal']['patches'][0]['set']['HOLD'] = 2
        self.assertEqual(mem.cooldown(current, [first, second, third]), [])

    def test_repeat_of_target_attempt_ends_refinement_streak(self):
        current = engine.strategy()
        root = observed_event(current, 0)
        first, second = [observed_event(current, i, kind='REFINE') for i in (1, 2)]
        for child in (first, second):
            child['target_id'] = 0
        self.assertIsNone(mem.target_for(current, [root, first, second]))

    def test_cooldown_never_empties_the_only_available_control(self):
        current = engine.strategy()
        history = [observed_event(current, i) for i in (0, 1)]
        schema = dict(version=11, origin='DEVELOPMENT_A', excluded=[], groups=[
            dict(parameter='HOLD', value=1, guards=[{'reset_known': ['eq', 1]}])])
        result = mem.apply_cooldown(schema, current, history)
        self.assertEqual(result['groups'], schema['groups'])
        self.assertEqual(result['cooldown_exclusions'], 0)


class PromptTests(unittest.TestCase):
    def test_every_variant_preserves_latest_V4_and_target(self):
        current = engine.strategy()
        history = [observed_event(current, i, kind=k, gain=0) for i, k in enumerate(mem.KINDS)]
        root = observed_event(current, 3)
        child = observed_event(current, 4, kind='REFINE', gain=8, verdict='V4')
        child['target_id'] = 3
        child['development']['behavior_sha256'] = 'new-outcome-not-a-repeat'
        history += [root, child]
        result = prompt.context('echo', 5, current, {'rows': [measured_row()]}, history)
        self.assertEqual(result['type'], 'REFINE')
        for text in result['prompt_variants']:
            payload = json.loads(text.split('DATA=', 1)[1].split('\nJSON only.', 1)[0])
            self.assertEqual(payload['target']['attempt'], 3)
            self.assertEqual(payload['latest_attempt']['attempt'], 4)
            self.assertEqual(payload['latest_target_attempt']['verdict'], 'V4')
            self.assertTrue(payload['latest_attempt']['protected_rejection'])
            self.assertNotIn('PRIVATE_SECRET', text)
            self.assertNotIn('case_index', text)
            self.assertNotIn('seed', payload)

    def test_latest_outcome_changes_even_shortest_prompt(self):
        current, rows = engine.strategy(), {'rows': [measured_row()]}
        first = [observed_event(current)]
        second = first + [observed_event(current, 1, gain=0)]
        for arm in ('echo', 'fijo'):
            a = prompt.context(arm, 1, current, rows, first)['prompt_variants'][-1]
            b = prompt.context(arm, 2, current, rows, second)['prompt_variants'][-1]
            self.assertNotEqual(a, b)
            self.assertIn('"attempt":1', b)

    def test_policy_encoding_is_reversible(self):
        raw = observed_event(engine.strategy())['proposal']
        compact = prompt.program(raw)
        decoded = {'patches': [{'set': {prompt.PARAMETERS[p]: value},
                               'when': {prompt.FEATURES[k]: [prompt.OPS[op], n] for k, op, n in guards}}
                              for p, value, guards in compact]}
        self.assertEqual(decoded, raw)

    def test_protected_rows_and_evidence_are_rejected(self):
        protected = dict(measured_row(), origin='PROTECTED_B')
        with self.assertRaises(ValueError):
            prompt.context('echo', 0, engine.strategy(), {'rows': [protected]}, [])
        bad = observed_event(engine.strategy())
        bad['development']['origin'] = 'PROTECTED_B'
        with self.assertRaises(ValueError):
            mem.receipt(bad)


class EquivalenceTests(unittest.TestCase):
    def fixture(self):
        current = engine.strategy()
        rows = [measured_row(i) for i in range(2)]
        event = observed_event(current, gain=0)
        event['decision_certificate'] = mem.certificate(rows, current, event['candidate'])
        a = event['proposal']['patches'][0]['when']
        redundant = dict(a, body_known=['eq', 1])
        distinct = dict(a, body_known=['eq', 0])
        schema = dict(version=11, origin='DEVELOPMENT_A', excluded=[], groups=[
            dict(parameter='HOLD', value=1, guards=[redundant, distinct])])
        return current, rows, event, schema, distinct

    def test_same_full_candidate_decisions_remove_repeated_A_failure(self):
        current, rows, event, schema, distinct = self.fixture()
        result = mem.prune_repeated_failures(schema, rows, current, [event])
        self.assertEqual(result['equivalent_V3_exclusions'], 1)
        self.assertEqual(result['groups'][0]['guards'], [distinct])

    def test_V4_equivalent_remains_available_to_fix_protected_behavior(self):
        current, rows, event, schema, distinct = self.fixture()
        event['verdict'] = 'V4'
        result = mem.prune_repeated_failures(schema, rows, current, [event])
        self.assertEqual(result['equivalent_V3_exclusions'], 0)

    def test_whole_candidate_trace_matters_not_just_base_opportunities(self):
        current, rows, event, schema, distinct = self.fixture()
        # A later candidate decision differs from the initial/base opportunity.
        # Omitting it would wrongly call the extra body_known guard redundant.
        later = copy.deepcopy(rows[0]['diagnostics']['trajectory']['steps'][0])
        later['f'][mem.FEATURES.index('body_known')] = 0
        rows[0]['actions'].append(['K', 2, None])
        rows[0]['diagnostics']['trajectory']['steps'].append(later)
        event['decision_certificate'] = mem.certificate(rows, current, event['candidate'])
        result = mem.prune_repeated_failures(schema, rows, current, [event])
        self.assertEqual(result['equivalent_V3_exclusions'], 0)

    def test_certificate_from_another_base_is_not_used(self):
        current, rows, event, schema, distinct = self.fixture()
        event['base_sha256'] = 'different'
        self.assertEqual(mem.prune_repeated_failures(schema, rows, current, [event])['equivalent_V3_exclusions'], 0)

    def test_certificate_tampering_stops_instead_of_pruning(self):
        current, rows, event, schema, distinct = self.fixture()
        event['decision_certificate']['decisions'] += 1
        with self.assertRaisesRegex(ValueError, 'certificate'):
            mem.prune_repeated_failures(schema, rows, current, [event])

    def test_quantization_preserves_every_guard_at_boundary_values(self):
        cuts = mem.cutpoints()
        from bisect import bisect_right
        for guard in mem.conditions():
            for key, (_, threshold) in guard.items():
                lo, hi = mem.patch.FEATURES[key]
                for value in (lo, hi, max(lo, threshold-1), threshold, min(hi, threshold+1)):
                    raw = {k: mem.patch.FEATURES[k][0] for k in mem.FEATURES}
                    raw[key] = value
                    quantized = {k: cuts[k][bisect_right(cuts[k], v)-1] for k, v in raw.items()}
                    self.assertEqual(matches(guard, raw), matches(guard, quantized))


if __name__ == '__main__':
    unittest.main()
